"""Managed current-user-input capture and admission for the EV-1 apply slice."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from relaylm.evidence_capture_attempt import (
    CaptureAttemptLog,
    build_managed_conversation_route_snapshot,
    validate_route_snapshot_for_capture,
)
from relaylm.evidence_common import AuthorityChangeSetRef, dedupe
from relaylm.evidence_governance import (
    build_least_privilege_grant,
    initialize_admitted_governance,
)
from relaylm.evidence_manifest import (
    build_canonical_source_manifest,
    build_managed_runtime_provenance,
    build_private_direct_audience,
    build_protected_text_part,
    build_source_occurrence_time,
)
from relaylm.evidence_response_binding import build_payload_binding_attestation
from relaylm.evidence_source_event import (
    SOURCE_EVENT_SCHEMA,
    SourceEvent,
    SourceReplayIdentityNone,
    build_admitted_admission_decision,
    build_valid_validation_bundle,
)
from relaylm.evidence_space import (
    EvidenceSpaceDescriptor,
    build_bootstrap_evidence_space_descriptor,
    derive_evidence_space_id,
    derive_participant_principal,
)
from relaylm.evidence_store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.evidence_validation_artifacts import (
    build_validation_artifact_events,
    build_validation_artifact_identities,
)
from relaylm.evidence_streams import (
    CaptureSequenceLog,
    SourceCaptureStreamDescriptor,
    build_capture_stream_descriptor,
    compute_coverage_checkpoint,
    derive_participant_change_partition_id,
    reserve_and_complete_authority_change_set,
)

_MAX_TEXT_CHARS = 32_768
_WORKSPACE_REF = "relaylm-local"
_STREAM_KEY = "managed_user_input"


def _derive_id(prefix: str, operation_idempotency_key: str, salt: str) -> str:
    digest = hashlib.sha256(
        f"{operation_idempotency_key}\0{salt}".encode("utf-8")
    ).hexdigest()
    return f"{prefix}_{digest}"


@dataclass(frozen=True)
class EvidenceUserInputCaptureResult:
    status: str
    blocked_reasons: tuple[str, ...] = ()
    evidence_space_id: str | None = None
    source_event_id: str | None = None
    capture_attempt_id: str | None = None
    admission_decision_id: str | None = None
    admission_outcome: str | None = None
    capture_stream_id: str | None = None
    capture_sequence: int | None = None
    persisted: bool = False

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": "relaylm.evidence_user_input_capture_result.v0",
            "diagnostics_only": True,
            "content_free": True,
            "status": self.status,
            "blocked_reason_ids": list(self.blocked_reasons),
            "evidence_space_id_present": self.evidence_space_id is not None,
            "source_event_id_present": self.source_event_id is not None,
            "admission_outcome": self.admission_outcome,
            "persisted": self.persisted,
        }


def capture_managed_user_input(
    *,
    store: EvidenceRecordStore | None,
    apply_enabled: bool,
    character_id: str | None,
    memory_namespace: str | None,
    session_id: str | None,
    current_user_text: str | None,
    fail_closed_reasons: tuple[str, ...],
    operation_idempotency_key: str,
    route_snapshot_payload: dict[str, object] | None = None,
    now: datetime | None = None,
) -> EvidenceUserInputCaptureResult:
    if fail_closed_reasons:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(fail_closed_reasons)
        )
    reasons: list[str] = []
    if type(character_id) is not str or not character_id:
        reasons.append("evidence_character_id_required")
    if type(memory_namespace) is not str or not memory_namespace:
        reasons.append("evidence_memory_namespace_required")
    if type(session_id) is not str or not session_id:
        reasons.append("evidence_session_id_required")
    if (
        type(current_user_text) is not str
        or not current_user_text
        or len(current_user_text) > _MAX_TEXT_CHARS
    ):
        reasons.append("evidence_current_user_text_invalid")
    if reasons:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(reasons)
        )

    assert character_id is not None
    assert memory_namespace is not None
    assert session_id is not None
    assert current_user_text is not None
    current_time = now or datetime.now(timezone.utc)
    recorded_at = current_time.isoformat()
    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref=_WORKSPACE_REF,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
    )
    if apply_enabled and store is None:
        return EvidenceUserInputCaptureResult(
            status="fail_closed",
            blocked_reasons=("evidence_store_required_for_apply",),
            evidence_space_id=evidence_space_id,
        )
    if apply_enabled and store is not None:
        try:
            with store.transaction(evidence_space_id) as tx:
                return _capture(
                    tx=tx,
                    persisted=True,
                    character_id=character_id,
                    memory_namespace=memory_namespace,
                    session_id=session_id,
                    current_user_text=current_user_text,
                    operation_idempotency_key=operation_idempotency_key,
                    route_snapshot_payload=route_snapshot_payload,
                    current_time=current_time,
                    recorded_at=recorded_at,
                )
        except RuntimeError as exc:
            return EvidenceUserInputCaptureResult(
                status="integrity_conflict",
                blocked_reasons=(str(exc),),
                evidence_space_id=evidence_space_id,
            )
    return _capture(
        tx=None,
        persisted=False,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
        current_user_text=current_user_text,
        operation_idempotency_key=operation_idempotency_key,
        route_snapshot_payload=route_snapshot_payload,
        current_time=current_time,
        recorded_at=recorded_at,
    )


def _capture(
    *,
    tx: EvidenceStoreTransaction | None,
    persisted: bool,
    character_id: str,
    memory_namespace: str,
    session_id: str,
    current_user_text: str,
    operation_idempotency_key: str,
    route_snapshot_payload: dict[str, object] | None,
    current_time: datetime,
    recorded_at: str,
) -> EvidenceUserInputCaptureResult:
    descriptor = _resolve_descriptor(
        tx=tx,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
        recorded_at=recorded_at,
    )
    if descriptor is None:
        return EvidenceUserInputCaptureResult(
            status="fail_closed",
            blocked_reasons=("evidence_space_descriptor_invalid",),
        )
    source_event_id = _derive_id(
        "sourceevent", operation_idempotency_key, "source_event"
    )
    existing_source = (
        tx.read_record(record_kind="source_event", record_id=source_event_id)
        if tx is not None
        else None
    )
    candidate_part, part_reasons = build_protected_text_part(
        current_user_text,
        part_origin="participant_authored",
        part_derivation_class="direct_occurrence",
    )
    if candidate_part is None:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(part_reasons)
        )
    candidate_manifest, manifest_reasons = build_canonical_source_manifest(
        occurrence_kind="message", parts=(candidate_part,)
    )
    if candidate_manifest is None:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(manifest_reasons)
        )
    manifest_digest = candidate_manifest.digest()
    if existing_source is not None:
        if existing_source.get("canonical_source_manifest_digest") != manifest_digest:
            return EvidenceUserInputCaptureResult(
                status="integrity_conflict",
                blocked_reasons=("source_event_integrity_conflict",),
                evidence_space_id=descriptor.evidence_space_id,
                source_event_id=source_event_id,
                capture_attempt_id=str(existing_source.get("capture_attempt_id")),
            )
        return EvidenceUserInputCaptureResult(
            status="admitted",
            evidence_space_id=descriptor.evidence_space_id,
            source_event_id=source_event_id,
            capture_attempt_id=str(existing_source.get("capture_attempt_id")),
            admission_outcome="admitted",
            capture_stream_id=None,
            capture_sequence=int(existing_source.get("capture_sequence", 0)),
            persisted=True,
        )

    route_snapshot, route_reasons = build_managed_conversation_route_snapshot(
        snapshot_payload=route_snapshot_payload,
        evidence_space_id=descriptor.evidence_space_id,
        capture_profile="managed_user_input",
    )
    if route_snapshot is None:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(route_reasons)
        )
    snapshot_reasons = validate_route_snapshot_for_capture(
        route_snapshot,
        evidence_space_id=descriptor.evidence_space_id,
        capture_profile="managed_user_input",
        capture_channel="managed_text",
    )
    if snapshot_reasons:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(snapshot_reasons)
        )

    stream_descriptor, sequence_log, previous_coverage = _load_stream(
        tx=tx,
        evidence_space_id=descriptor.evidence_space_id,
        recorded_at=recorded_at,
    )
    capture_attempt_id = _derive_id(
        "captureattempt", operation_idempotency_key, "capture_attempt"
    )
    sequence, sequence_reasons = sequence_log.reserve(
        capture_attempt_id=capture_attempt_id,
        recorded_at=recorded_at,
        operation_idempotency_key=operation_idempotency_key,
    )
    if sequence is None:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(sequence_reasons)
        )
    attempt = CaptureAttemptLog(
        evidence_space_id=descriptor.evidence_space_id,
        capture_stream_epoch_id=stream_descriptor.capture_stream_epoch_id,
        capture_sequence=sequence,
        route_capture_grant_snapshot_ref=route_snapshot.route_binding_id,
        capture_channel="managed_text",
        source_role="user_input",
        capture_attempt_id=capture_attempt_id,
    )
    ok, attempt_reasons = attempt.reserve(
        capture_stream_kind="managed_user_input",
        stream_direction="inbound",
        recorded_at=recorded_at,
        operation_idempotency_key=operation_idempotency_key,
    )
    if not ok:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(attempt_reasons)
        )

    admission_decision_id = _derive_id(
        "admdecision", operation_idempotency_key, "admission"
    )
    governance_event_id = _derive_id(
        "governanceevent", operation_idempotency_key, "governance"
    )
    validation_identities = build_validation_artifact_identities(
        operation_idempotency_key=operation_idempotency_key,
        gate_kinds=("canonicalization", "integrity"),
    )
    validation_bundle = build_valid_validation_bundle(
        validation_bundle_id=_derive_id(
            "valbundle", operation_idempotency_key, "validation_bundle"
        ),
        validation_bundle_revision_id=_derive_id(
            "valbundlerev",
            operation_idempotency_key,
            "validation_bundle_revision",
        ),
        capture_attempt_id=capture_attempt_id,
        source_event_id=source_event_id,
        evidence_space_id=descriptor.evidence_space_id,
        recorded_at=recorded_at,
        gate_kinds=tuple(item.gate_kind for item in validation_identities),
        gate_artifact_refs=tuple(
            (item.gate_kind, item.derived_artifact_id)
            for item in validation_identities
        ),
    )
    ok, finalize_reasons = attempt.finalize_candidate(
        preallocated_source_event_id=source_event_id,
        canonical_source_manifest=candidate_manifest.to_dict(),
        canonical_source_manifest_digest=manifest_digest,
        validation_bundle_id=validation_bundle.validation_bundle_id,
        validation_bundle_revision=validation_bundle.bundle_revision,
        recorded_at=recorded_at,
        operation_idempotency_key=operation_idempotency_key,
    )
    if not ok:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(finalize_reasons)
        )

    change_partition_id = derive_participant_change_partition_id(
        evidence_space_id=descriptor.evidence_space_id,
        participant_ref=descriptor.controller_principal_ref,
    )
    projection_log = (
        tx.read_log(log_kind="change_projection", key=change_partition_id) or []
        if tx is not None
        else []
    )
    previous_change_coverage = (
        tx.read_log(
            log_kind="change_coverage_checkpoint", key=change_partition_id
        )
        or []
        if tx is not None
        else []
    )
    authoritative_mutation_refs = [
        {
            "record_kind": "source_event",
            "record_id": source_event_id,
            "record_revision_or_null": None,
        },
        {
            "record_kind": "admission_decision",
            "record_id": admission_decision_id,
            "record_revision_or_null": None,
        },
        {
            "record_kind": "governance_event",
            "record_id": governance_event_id,
            "record_revision_or_null": 1,
        },
    ]
    authoritative_mutation_refs.extend(
        {
            "record_kind": "source_derived_artifact_event",
            "record_id": item.artifact_event_id,
            "record_revision_or_null": 1,
        }
        for item in validation_identities
    )
    change_result, change_reasons = reserve_and_complete_authority_change_set(
        change_set_id=_derive_id(
            "changeset", operation_idempotency_key, "change_set"
        ),
        change_kind="source_admitted",
        evidence_space_id=descriptor.evidence_space_id,
        participant_ref=descriptor.controller_principal_ref,
        authoritative_mutation_refs=tuple(authoritative_mutation_refs),
        recorded_at=recorded_at,
        partition_sequence=len(projection_log),
        change_coverage_revision=len(previous_change_coverage) + 1,
        expected_previous_change_coverage_revision_or_null=(
            len(previous_change_coverage) if previous_change_coverage else None
        ),
        partition_descriptor_issued_at=descriptor.created_at,
        existing_projection_events=tuple(projection_log),
    )
    if change_result is None:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(change_reasons)
        )
    authority_change_set_ref = AuthorityChangeSetRef(
        change_set_id=change_result.change_set_id,
        change_projection_plan_digest=(
            change_result.change_projection_plan_digest
        ),
    )
    validation_artifacts = build_validation_artifact_events(
        identities=validation_identities,
        evidence_space_id=descriptor.evidence_space_id,
        source_event_id=source_event_id,
        canonical_manifest_digest=manifest_digest,
        assistant_response_binding_id_or_null=None,
        assistant_response_binding_digest_or_null=None,
        authority_change_set_ref=authority_change_set_ref,
        recorded_at=recorded_at,
        operation_idempotency_key=operation_idempotency_key,
    )

    participant_ref = derive_participant_principal(
        workspace_or_tenant_ref=_WORKSPACE_REF, session_id=session_id
    )
    audience, audience_reasons = build_private_direct_audience(
        participant_refs=(participant_ref,)
    )
    occurrence_time, occurrence_reasons = build_source_occurrence_time(
        parsed_instant=recorded_at
    )
    provenance, provenance_reasons = build_managed_runtime_provenance(
        source_material_class="personal_source"
    )
    if audience is None or occurrence_time is None or provenance is None:
        return EvidenceUserInputCaptureResult(
            status="fail_closed",
            blocked_reasons=dedupe(
                (*audience_reasons, *occurrence_reasons, *provenance_reasons)
            ),
        )

    payload_binding_attestation_id = _derive_id(
        "payloadbinding", operation_idempotency_key, "payload_binding"
    )
    storage_binding_ref = _derive_id(
        "storagebinding", operation_idempotency_key, "payload_storage"
    )
    attestation = build_payload_binding_attestation(
        payload_binding_attestation_id=payload_binding_attestation_id,
        source_event_id=source_event_id,
        part_id=candidate_part.part_id,
        content_digest=str(candidate_part.content_digest_or_null),
        storage_binding_ref=storage_binding_ref,
        evidence_space_id=descriptor.evidence_space_id,
        attested_at=recorded_at,
    )
    source_event = SourceEvent(
        schema=SOURCE_EVENT_SCHEMA,
        source_event_id=source_event_id,
        evidence_space_id=descriptor.evidence_space_id,
        evidence_space_descriptor_revision=descriptor.descriptor_revision,
        capture_attempt_id=capture_attempt_id,
        capture_stream_epoch_id=stream_descriptor.capture_stream_epoch_id,
        capture_sequence=sequence,
        route_capture_grant_snapshot_ref=route_snapshot.route_binding_id,
        received_at=recorded_at,
        observed_at=recorded_at,
        capture_channel="managed_text",
        source_role="user_input",
        origin_kind="participant",
        producer_principal_ref=participant_ref,
        authenticated_account_ref_or_null=None,
        represented_speaker_ref_or_null=participant_ref,
        speaker_identity_status="verified",
        source_occurrence_time=occurrence_time,
        configured_occurrence_audience=audience,
        scene_occurrence_ref_or_null=None,
        conversation_ref_or_null=session_id,
        canonical_source_manifest=candidate_manifest,
        canonical_source_manifest_digest=manifest_digest,
        protected_payload_binding_attestation_ids=(
            payload_binding_attestation_id,
        ),
        source_replay_identity=SourceReplayIdentityNone(),
        assistant_response_binding_ref_or_null=None,
        provenance_snapshot=provenance,
        authority_change_set_ref=authority_change_set_ref,
    )
    admission_decision = build_admitted_admission_decision(
        admission_decision_id=admission_decision_id,
        capture_attempt_id=capture_attempt_id,
        evidence_space_id=descriptor.evidence_space_id,
        operation_idempotency_key=operation_idempotency_key,
        route_capture_grant_snapshot_ref=route_snapshot.route_binding_id,
        decided_at=recorded_at,
        manifest_digest=manifest_digest,
        validation_bundle=validation_bundle,
        source_event_id=source_event_id,
        initial_governance_event_id=governance_event_id,
        authority_change_set_ref=authority_change_set_ref,
    )
    ok, bind_reasons = attempt.bind_admission(
        admission_decision_id=admission_decision_id,
        recorded_at=recorded_at,
        operation_idempotency_key=operation_idempotency_key,
    )
    if not ok:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(bind_reasons)
        )

    grants = []
    for purpose in ("relayctx_evidence_read", "shared_assessment_read"):
        grant, grant_reasons = build_least_privilege_grant(
            grant_id=_derive_id(
                "accessgrant", operation_idempotency_key, f"grant:{purpose}"
            ),
            source_event_id=source_event_id,
            evidence_space_id=descriptor.evidence_space_id,
            purpose=purpose,
            admission_decision_id=admission_decision_id,
            validation_bundle_revision=validation_bundle.bundle_revision,
            issued_at=recorded_at,
        )
        if grant is None:
            return EvidenceUserInputCaptureResult(
                status="fail_closed", blocked_reasons=dedupe(grant_reasons)
            )
        grants.append(grant)
    access_until_epoch = current_time.timestamp() + 30 * 24 * 60 * 60
    purge_due_epoch = access_until_epoch + 7 * 24 * 60 * 60
    _governance_state, governance_event = initialize_admitted_governance(
        governance_event_id=governance_event_id,
        source_event_id=source_event_id,
        evidence_space_id=descriptor.evidence_space_id,
        part_ids=(candidate_part.part_id,),
        grants=tuple(grants),
        access_until=datetime.fromtimestamp(
            access_until_epoch, tz=timezone.utc
        ).isoformat(),
        purge_due_at=datetime.fromtimestamp(
            purge_due_epoch, tz=timezone.utc
        ).isoformat(),
        authority_change_set_ref=authority_change_set_ref,
        recorded_at=recorded_at,
        operation_idempotency_key=operation_idempotency_key,
    )
    ok, terminal_reasons = sequence_log.terminalize_admission(
        sequence=sequence,
        capture_attempt_id=capture_attempt_id,
        admission_decision_id=admission_decision_id,
        terminal_outcome="admitted",
        recorded_at=recorded_at,
        operation_idempotency_key=operation_idempotency_key,
    )
    if not ok:
        return EvidenceUserInputCaptureResult(
            status="fail_closed", blocked_reasons=dedupe(terminal_reasons)
        )
    coverage = compute_coverage_checkpoint(
        stream_descriptor,
        sequence_log.events,
        updated_at=recorded_at,
        operation_idempotency_key=operation_idempotency_key,
        previous_checkpoint=previous_coverage,
    )

    if tx is not None:
        records = [
            ("evidence_space_descriptor", "revision-1", descriptor.to_dict()),
            (
                "route_capture_grant_snapshot",
                route_snapshot.route_binding_id,
                route_snapshot.to_dict(),
            ),
            ("stream_descriptor", _STREAM_KEY, stream_descriptor.to_dict()),
            (
                "payload_binding_attestation",
                payload_binding_attestation_id,
                attestation,
            ),
            ("source_event", source_event_id, source_event.to_dict()),
            (
                "admission_decision",
                admission_decision_id,
                admission_decision.to_dict(),
            ),
            (
                "validation_bundle",
                validation_bundle.validation_bundle_id,
                validation_bundle.to_dict(),
            ),
            *(
                (
                    "source_derived_artifact_event",
                    str(event["artifact_event_id"]),
                    event,
                )
                for event in validation_artifacts
            ),
            (
                "governance_event",
                governance_event_id,
                governance_event.to_dict(),
            ),
            (
                "change_partition_descriptor",
                str(change_result.partition_descriptor["change_partition_id"]),
                change_result.partition_descriptor,
            ),
            (
                "change_projection_event",
                str(change_result.projection_event["projection_event_id"]),
                change_result.projection_event,
            ),
            (
                "source_projection_registry_event",
                str(change_result.registry_event["registry_event_id"]),
                change_result.registry_event,
            ),
        ]
        records.extend(
            ("access_grant", grant.grant_id, grant.to_dict())
            for grant in grants
        )
        logs = [
            ("capture_sequence", _STREAM_KEY, sequence_log.events),
            ("capture_attempt", capture_attempt_id, attempt.events),
            (
                "change_set",
                change_result.change_set_id,
                [change_result.plan_event, change_result.mark_complete_event],
            ),
            (
                "coverage_checkpoint",
                _STREAM_KEY,
                [
                    *([previous_coverage] if previous_coverage else []),
                    coverage.to_dict(),
                ],
            ),
            (
                "change_projection",
                change_partition_id,
                [*projection_log, change_result.projection_event],
            ),
            (
                "change_coverage_checkpoint",
                change_partition_id,
                [
                    *previous_change_coverage,
                    change_result.change_coverage_checkpoint,
                ],
            ),
        ]
        commit = tx.commit(
            transaction_id=_derive_id(
                "evidencetx", operation_idempotency_key, "user_input_commit"
            ),
            records=records,
            logs=logs,
            payloads=(
                (
                    storage_binding_ref,
                    {
                        "content_digest": candidate_part.content_digest_or_null,
                        "media_type": candidate_part.media_type,
                        "text": current_user_text,
                    },
                ),
            ),
        )
        if commit.status == "collision":
            return EvidenceUserInputCaptureResult(
                status="integrity_conflict",
                blocked_reasons=commit.reasons,
                evidence_space_id=descriptor.evidence_space_id,
                source_event_id=source_event_id,
                capture_attempt_id=capture_attempt_id,
            )
        if commit.status not in {"created", "duplicate_existing"}:
            return EvidenceUserInputCaptureResult(
                status="fail_closed",
                blocked_reasons=commit.reasons,
                evidence_space_id=descriptor.evidence_space_id,
            )

    return EvidenceUserInputCaptureResult(
        status="admitted" if persisted else "dry_run_ready",
        evidence_space_id=descriptor.evidence_space_id,
        source_event_id=source_event_id,
        capture_attempt_id=capture_attempt_id,
        admission_decision_id=admission_decision_id,
        admission_outcome="admitted",
        capture_stream_id=stream_descriptor.capture_stream_id,
        capture_sequence=sequence,
        persisted=persisted,
    )


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
    descriptor, _reasons = build_bootstrap_evidence_space_descriptor(
        workspace_or_tenant_ref=_WORKSPACE_REF,
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
) -> tuple[
    SourceCaptureStreamDescriptor,
    CaptureSequenceLog,
    dict[str, object] | None,
]:
    persisted_descriptor = (
        tx.read_record(record_kind="stream_descriptor", record_id=_STREAM_KEY)
        if tx is not None
        else None
    )
    if persisted_descriptor is None:
        descriptor, reasons = build_capture_stream_descriptor(
            evidence_space_id=evidence_space_id,
            capture_stream_kind=_STREAM_KEY,
            stream_direction="inbound",
            created_at=recorded_at,
        )
        if descriptor is None or reasons:
            raise RuntimeError("capture_stream_descriptor_invalid")
        events: list[dict] = []
    else:
        descriptor = SourceCaptureStreamDescriptor.from_dict(persisted_descriptor)
        events = (
            tx.read_log(log_kind="capture_sequence", key=_STREAM_KEY) or []
        )  # type: ignore[union-attr]
    checkpoints = (
        tx.read_log(log_kind="coverage_checkpoint", key=_STREAM_KEY) or []
        if tx is not None
        else []
    )
    previous = checkpoints[-1] if checkpoints else None
    return descriptor, CaptureSequenceLog.from_events(descriptor, events), previous


__all__ = ["EvidenceUserInputCaptureResult", "capture_managed_user_input"]
