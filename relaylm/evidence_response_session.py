"""Contract 1E reservation and write-ahead canonical-output observation."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from relaylm.evidence_capture_attempt import (
    CaptureAttemptLog,
    RouteCaptureGrantSnapshot,
    build_managed_conversation_route_snapshot,
    validate_route_snapshot_for_capture,
)
from relaylm.evidence_common import canonical_digest, dedupe
from relaylm.evidence_manifest import build_private_direct_audience
from relaylm.evidence_response_binding import ResponseCaptureLog, build_response_capture_reservation
from relaylm.evidence_space import (
    EvidenceSpaceDescriptor,
    build_bootstrap_evidence_space_descriptor,
    derive_evidence_space_id,
    derive_participant_principal,
)
from relaylm.evidence_store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.evidence_streams import (
    CaptureSequenceLog,
    SourceCaptureStreamDescriptor,
    build_capture_stream_descriptor,
)

WORKSPACE_REF = "relaylm-local"
STREAM_KEY = "managed_assistant_output"
MAX_ASSISTANT_TEXT_CHARS = 1_000_000


def derive_id(prefix: str, operation_idempotency_key: str, salt: str) -> str:
    digest = hashlib.sha256(f"{operation_idempotency_key}\0{salt}".encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


@dataclass
class PreparedResponseCapture:
    store: EvidenceRecordStore | None
    apply_enabled: bool
    descriptor: EvidenceSpaceDescriptor
    route_snapshot: RouteCaptureGrantSnapshot
    stream_descriptor: SourceCaptureStreamDescriptor
    capture_attempt_id: str
    capture_sequence: int
    response_capture_reservation_id: str
    response_id: str
    delivery_cohort_id: str
    request_source_event_ids: tuple[str, ...]
    operation_idempotency_key: str
    session_id: str
    reserved_at: str
    accepted_parts: list[str] = field(default_factory=list)
    accepted_ranges: list[tuple[int, int]] = field(default_factory=list)
    byte_count: int = 0
    first_output_accepted_at: str | None = None
    invalid_reason: str | None = None

    @property
    def accepted_text(self) -> str | None:
        return "".join(self.accepted_parts) if self.accepted_parts else None

    def observe(self, text: str, observed_at: str) -> tuple[bool, tuple[str, ...]]:
        if self.invalid_reason is not None:
            return False, (self.invalid_reason,)
        if not text:
            return True, ()
        if sum(len(part) for part in self.accepted_parts) + len(text) > MAX_ASSISTANT_TEXT_CHARS:
            self.invalid_reason = "assistant_output_capture_limit_exceeded"
            self.abandon(self.invalid_reason, observed_at)
            return False, (self.invalid_reason,)
        encoded = text.encode("utf-8", errors="strict")
        start = self.byte_count
        end = start + len(encoded)
        unit_sequence = len(self.accepted_ranges)
        buffer_ref = derive_id(
            "outputbuffer", self.operation_idempotency_key, f"unit:{unit_sequence}"
        )
        if self.apply_enabled and self.store is not None:
            try:
                with self.store.transaction(self.descriptor.evidence_space_id) as tx:
                    reservation = tx.read_record(
                        record_kind="response_capture_reservation",
                        record_id=self.response_capture_reservation_id,
                    )
                    if reservation is None:
                        return False, ("assistant_response_reservation_missing",)
                    events = tx.read_log(
                        log_kind="response_capture",
                        key=self.response_capture_reservation_id,
                    ) or []
                    if any(event.get("operation") in {"finalize", "terminal_no_output"} for event in events):
                        return False, ("assistant_response_capture_already_terminal",)
                    log = ResponseCaptureLog(reservation, list(events))
                    if not any(event.get("operation") == "emission_begin" for event in events):
                        log.emission_begin(
                            first_output_accepted_at=observed_at,
                            protected_output_buffer_ref=buffer_ref,
                            operation_idempotency_key=self.operation_idempotency_key,
                        )
                    log.output_observed(
                        output_unit_sequence=unit_sequence,
                        start_byte=start,
                        end_byte=end,
                        observed_at=observed_at,
                        protected_output_buffer_ref=buffer_ref,
                        operation_idempotency_key=self.operation_idempotency_key,
                    )
                    result = tx.commit(
                        transaction_id=derive_id(
                            "evidencetx",
                            self.operation_idempotency_key,
                            f"response-observe:{unit_sequence}",
                        ),
                        records=(),
                        logs=(("response_capture", self.response_capture_reservation_id, log.events),),
                        payloads=((buffer_ref, {
                            "media_type": "text/plain; charset=utf-8",
                            "text": text,
                            "accepted_range": [start, end],
                        }),),
                    )
                    if result.status not in {"created", "duplicate_existing"}:
                        return False, result.reasons
            except RuntimeError as exc:
                return False, (str(exc),)
        self.accepted_parts.append(text)
        self.accepted_ranges.append((start, end))
        self.byte_count = end
        if self.first_output_accepted_at is None:
            self.first_output_accepted_at = observed_at
        return True, ()

    def abandon(self, reason: str, recorded_at: str) -> tuple[bool, tuple[str, ...]]:
        self.invalid_reason = reason
        if not self.apply_enabled or self.store is None:
            return True, ()
        try:
            with self.store.transaction(self.descriptor.evidence_space_id) as tx:
                reservation = tx.read_record(
                    record_kind="response_capture_reservation",
                    record_id=self.response_capture_reservation_id,
                )
                if reservation is None:
                    return False, ("assistant_response_reservation_missing",)
                events = tx.read_log(
                    log_kind="response_capture", key=self.response_capture_reservation_id
                ) or []
                if any(event.get("operation") in {"finalize", "terminal_no_output"} for event in events):
                    return False, ("assistant_response_capture_already_terminal",)
                if not any(event.get("operation") == "mark_abandoned" for event in events):
                    log = ResponseCaptureLog(reservation, list(events))
                    log.mark_abandoned(
                        abandon_reason=reason,
                        last_known_output_unit_sequence_or_null=(
                            len(self.accepted_ranges) - 1 if self.accepted_ranges else None
                        ),
                        recovery_case_ref=derive_id(
                            "recoverycase", self.operation_idempotency_key, "response"
                        ),
                        recorded_at=recorded_at,
                        operation_idempotency_key=self.operation_idempotency_key,
                    )
                    result = tx.commit(
                        transaction_id=derive_id(
                            "evidencetx", self.operation_idempotency_key, "response-abandon"
                        ),
                        records=(),
                        logs=(("response_capture", self.response_capture_reservation_id, log.events),),
                    )
                    if result.status not in {"created", "duplicate_existing"}:
                        return False, result.reasons
        except RuntimeError as exc:
            return False, (str(exc),)
        return True, ()


def prepare_response_capture(
    *,
    store: EvidenceRecordStore | None,
    apply_enabled: bool,
    character_id: str | None,
    memory_namespace: str | None,
    session_id: str | None,
    response_id: str,
    delivery_cohort_id: str,
    request_source_event_ids: tuple[str, ...],
    operation_idempotency_key: str,
    route_snapshot_payload: dict[str, object] | None = None,
    now: datetime | None = None,
) -> tuple[PreparedResponseCapture | None, tuple[str, ...]]:
    reasons: list[str] = []
    for name, value in (
        ("character_id", character_id),
        ("memory_namespace", memory_namespace),
        ("session_id", session_id),
        ("response_id", response_id),
        ("delivery_cohort_id", delivery_cohort_id),
        ("operation_idempotency_key", operation_idempotency_key),
    ):
        if not isinstance(value, str) or not value:
            reasons.append(f"evidence_{name}_required")
    if apply_enabled and store is None:
        reasons.append("evidence_store_required_for_apply")
    if reasons:
        return None, dedupe(reasons)
    assert isinstance(character_id, str)
    assert isinstance(memory_namespace, str)
    assert isinstance(session_id, str)
    recorded_at = (now or datetime.now(timezone.utc)).isoformat()
    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref=WORKSPACE_REF,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
    )
    if apply_enabled and store is not None:
        try:
            with store.transaction(evidence_space_id) as tx:
                return _prepare_locked(
                    tx=tx,
                    store=store,
                    character_id=character_id,
                    memory_namespace=memory_namespace,
                    session_id=session_id,
                    response_id=response_id,
                    delivery_cohort_id=delivery_cohort_id,
                    request_source_event_ids=request_source_event_ids,
                    operation_idempotency_key=operation_idempotency_key,
                    route_snapshot_payload=route_snapshot_payload,
                    recorded_at=recorded_at,
                )
        except RuntimeError as exc:
            return None, (str(exc),)
    return _prepare_locked(
        tx=None,
        store=None,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
        response_id=response_id,
        delivery_cohort_id=delivery_cohort_id,
        request_source_event_ids=request_source_event_ids,
        operation_idempotency_key=operation_idempotency_key,
        route_snapshot_payload=route_snapshot_payload,
        recorded_at=recorded_at,
    )


def _prepare_locked(
    *,
    tx: EvidenceStoreTransaction | None,
    store: EvidenceRecordStore | None,
    character_id: str,
    memory_namespace: str,
    session_id: str,
    response_id: str,
    delivery_cohort_id: str,
    request_source_event_ids: tuple[str, ...],
    operation_idempotency_key: str,
    route_snapshot_payload: dict[str, object] | None,
    recorded_at: str,
) -> tuple[PreparedResponseCapture | None, tuple[str, ...]]:
    descriptor = _resolve_descriptor(
        tx=tx,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
        recorded_at=recorded_at,
    )
    if descriptor is None:
        return None, ("evidence_space_descriptor_invalid",)
    route_snapshot, route_reasons = build_managed_conversation_route_snapshot(
        snapshot_payload=route_snapshot_payload,
        evidence_space_id=descriptor.evidence_space_id,
        capture_profile="managed_assistant_response",
    )
    if route_snapshot is None:
        return None, dedupe(route_reasons)
    snapshot_reasons = validate_route_snapshot_for_capture(
        route_snapshot,
        evidence_space_id=descriptor.evidence_space_id,
        capture_profile="managed_assistant_response",
        capture_channel="managed_assistant_text",
    )
    if snapshot_reasons:
        return None, dedupe(snapshot_reasons)
    stream_descriptor, sequence_log = _load_stream(
        tx=tx, evidence_space_id=descriptor.evidence_space_id, recorded_at=recorded_at
    )
    capture_attempt_id = derive_id(
        "captureattempt", operation_idempotency_key, "capture_attempt"
    )
    reservation_id = derive_id(
        "responsereservation", operation_idempotency_key, "response_reservation"
    )
    if tx is not None:
        existing = tx.read_record(
            record_kind="response_capture_reservation", record_id=reservation_id
        )
        if existing is not None:
            return _restore(
                tx=tx,
                store=store,
                descriptor=descriptor,
                route_snapshot=route_snapshot,
                stream_descriptor=stream_descriptor,
                sequence_log=sequence_log,
                reservation=existing,
                capture_attempt_id=capture_attempt_id,
                response_id=response_id,
                delivery_cohort_id=delivery_cohort_id,
                request_source_event_ids=request_source_event_ids,
                operation_idempotency_key=operation_idempotency_key,
                session_id=session_id,
            )
    sequence, sequence_reasons = sequence_log.reserve(
        capture_attempt_id=capture_attempt_id,
        recorded_at=recorded_at,
        operation_idempotency_key=operation_idempotency_key,
    )
    if sequence is None:
        return None, dedupe(sequence_reasons)
    attempt = CaptureAttemptLog(
        evidence_space_id=descriptor.evidence_space_id,
        capture_stream_epoch_id=stream_descriptor.capture_stream_epoch_id,
        capture_sequence=sequence,
        route_capture_grant_snapshot_ref=route_snapshot.route_binding_id,
        capture_channel="managed_assistant_text",
        source_role="assistant_response",
        capture_attempt_id=capture_attempt_id,
    )
    ok, attempt_reasons = attempt.reserve(
        capture_stream_kind="managed_assistant_output",
        stream_direction="outbound",
        recorded_at=recorded_at,
        operation_idempotency_key=operation_idempotency_key,
        response_capture_reservation_ref_or_null=reservation_id,
    )
    if not ok:
        return None, dedupe(attempt_reasons)
    participant = derive_participant_principal(
        workspace_or_tenant_ref=WORKSPACE_REF, session_id=session_id
    )
    audience, audience_reasons = build_private_direct_audience(
        participant_refs=(participant,)
    )
    if audience is None:
        return None, dedupe(audience_reasons)
    reservation = build_response_capture_reservation(
        response_capture_reservation_id=reservation_id,
        response_id=response_id,
        run_id=operation_idempotency_key.split(":", 1)[0],
        turn_id_or_null=operation_idempotency_key.split(":", 1)[0],
        evidence_space_id=descriptor.evidence_space_id,
        route_capture_grant_snapshot_ref=route_snapshot.route_binding_id,
        capture_stream_id=stream_descriptor.capture_stream_id,
        capture_stream_epoch_id=stream_descriptor.capture_stream_epoch_id,
        capture_sequence=sequence,
        delivery_cohort_id=delivery_cohort_id,
        audience=audience,
        request_source_event_ids=request_source_event_ids,
        reserved_at=recorded_at,
        operation_idempotency_key=operation_idempotency_key,
    )
    if tx is not None:
        commit = tx.commit(
            transaction_id=derive_id(
                "evidencetx", operation_idempotency_key, "response-reserve"
            ),
            records=(
                ("evidence_space_descriptor", "revision-1", descriptor.to_dict()),
                ("route_capture_grant_snapshot", route_snapshot.route_binding_id, route_snapshot.to_dict()),
                ("stream_descriptor", STREAM_KEY, stream_descriptor.to_dict()),
                ("response_capture_reservation", reservation_id, reservation),
            ),
            logs=(
                ("capture_sequence", STREAM_KEY, sequence_log.events),
                ("capture_attempt", capture_attempt_id, attempt.events),
                ("response_capture", reservation_id, ()),
            ),
        )
        if commit.status not in {"created", "duplicate_existing"}:
            return None, commit.reasons
    return PreparedResponseCapture(
        store=store,
        apply_enabled=tx is not None,
        descriptor=descriptor,
        route_snapshot=route_snapshot,
        stream_descriptor=stream_descriptor,
        capture_attempt_id=capture_attempt_id,
        capture_sequence=sequence,
        response_capture_reservation_id=reservation_id,
        response_id=response_id,
        delivery_cohort_id=delivery_cohort_id,
        request_source_event_ids=request_source_event_ids,
        operation_idempotency_key=operation_idempotency_key,
        session_id=session_id,
        reserved_at=recorded_at,
    ), ()


def _restore(
    *,
    tx: EvidenceStoreTransaction,
    store: EvidenceRecordStore | None,
    descriptor: EvidenceSpaceDescriptor,
    route_snapshot: RouteCaptureGrantSnapshot,
    stream_descriptor: SourceCaptureStreamDescriptor,
    sequence_log: CaptureSequenceLog,
    reservation: dict[str, object],
    capture_attempt_id: str,
    response_id: str,
    delivery_cohort_id: str,
    request_source_event_ids: tuple[str, ...],
    operation_idempotency_key: str,
    session_id: str,
) -> tuple[PreparedResponseCapture | None, tuple[str, ...]]:
    expected = {
        "response_id": response_id,
        "delivery_cohort_id": delivery_cohort_id,
        "evidence_space_id": descriptor.evidence_space_id,
        "route_capture_grant_snapshot_ref": route_snapshot.route_binding_id,
        "capture_stream_id": stream_descriptor.capture_stream_id,
        "capture_stream_epoch_id": stream_descriptor.capture_stream_epoch_id,
    }
    if any(reservation.get(key) != value for key, value in expected.items()):
        return None, ("assistant_response_reservation_integrity_conflict",)
    try:
        sequence = int(reservation["capture_sequence"])
    except (KeyError, TypeError, ValueError):
        return None, ("assistant_response_reservation_shape_invalid",)
    if sequence_log.find_reservation_for_attempt(capture_attempt_id) != sequence:
        return None, ("assistant_response_reservation_sequence_mismatch",)
    prepared = PreparedResponseCapture(
        store=store,
        apply_enabled=True,
        descriptor=descriptor,
        route_snapshot=route_snapshot,
        stream_descriptor=stream_descriptor,
        capture_attempt_id=capture_attempt_id,
        capture_sequence=sequence,
        response_capture_reservation_id=str(reservation["response_capture_reservation_id"]),
        response_id=response_id,
        delivery_cohort_id=delivery_cohort_id,
        request_source_event_ids=request_source_event_ids,
        operation_idempotency_key=operation_idempotency_key,
        session_id=session_id,
        reserved_at=str(reservation.get("reserved_at", "")),
    )
    events = tx.read_log(
        log_kind="response_capture", key=prepared.response_capture_reservation_id
    ) or []
    if any(event.get("operation") in {"finalize", "terminal_no_output"} for event in events):
        return prepared, ()
    if any(event.get("operation") == "mark_abandoned" for event in events):
        prepared.invalid_reason = "assistant_response_capture_abandoned"
    for event in events:
        if event.get("operation") == "emission_begin":
            prepared.first_output_accepted_at = str(
                event.get("operation_payload", {}).get("first_output_accepted_at", "")
            ) or None
        if event.get("operation") != "output_observed":
            continue
        payload = event.get("operation_payload", {})
        accepted_range = payload.get("accepted_range", {})
        buffer_ref = payload.get("protected_output_buffer_ref")
        if not isinstance(accepted_range, dict) or not isinstance(buffer_ref, str):
            return None, ("assistant_response_recovery_record_invalid",)
        protected = tx.read_payload(payload_id=buffer_ref)
        if protected is None or not isinstance(protected.get("text"), str):
            return None, ("assistant_response_recovery_buffer_missing",)
        try:
            start = int(accepted_range["start_inclusive"])
            end = int(accepted_range["end_exclusive"])
        except (KeyError, TypeError, ValueError):
            return None, ("assistant_response_recovery_range_invalid",)
        text = str(protected["text"])
        if start != prepared.byte_count or end - start != len(text.encode("utf-8")):
            return None, ("assistant_response_recovery_range_conflict",)
        prepared.accepted_parts.append(text)
        prepared.accepted_ranges.append((start, end))
        prepared.byte_count = end
    return prepared, ()


def _resolve_descriptor(
    *,
    tx: EvidenceStoreTransaction | None,
    character_id: str,
    memory_namespace: str,
    session_id: str,
    recorded_at: str,
) -> EvidenceSpaceDescriptor | None:
    if tx is not None:
        persisted = tx.read_record(
            record_kind="evidence_space_descriptor", record_id="revision-1"
        )
        if persisted is not None:
            try:
                return EvidenceSpaceDescriptor.from_dict(persisted)
            except (TypeError, KeyError, ValueError):
                return None
    descriptor, _ = build_bootstrap_evidence_space_descriptor(
        workspace_or_tenant_ref=WORKSPACE_REF,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
        created_at=recorded_at,
    )
    return descriptor


def _load_stream(
    *,
    tx: EvidenceStoreTransaction | None,
    evidence_space_id: str,
    recorded_at: str,
) -> tuple[SourceCaptureStreamDescriptor, CaptureSequenceLog]:
    persisted = (
        tx.read_record(record_kind="stream_descriptor", record_id=STREAM_KEY)
        if tx is not None
        else None
    )
    if persisted is None:
        descriptor, reasons = build_capture_stream_descriptor(
            evidence_space_id=evidence_space_id,
            capture_stream_kind=STREAM_KEY,
            stream_direction="outbound",
            created_at=recorded_at,
        )
        if descriptor is None or reasons:
            raise RuntimeError("capture_stream_descriptor_invalid")
        events: list[dict] = []
    else:
        descriptor = SourceCaptureStreamDescriptor.from_dict(persisted)
        events = tx.read_log(log_kind="capture_sequence", key=STREAM_KEY) or []  # type: ignore[union-attr]
    return descriptor, CaptureSequenceLog.from_events(descriptor, events)


__all__ = [
    "MAX_ASSISTANT_TEXT_CHARS",
    "PreparedResponseCapture",
    "STREAM_KEY",
    "WORKSPACE_REF",
    "derive_id",
    "prepare_response_capture",
]
