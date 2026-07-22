"""Contract 1D EV-1 capture streams, coverage, and bounded change feed."""
from __future__ import annotations

from dataclasses import dataclass, field

from relaylm.evidence_common import (
    AuthorityScope,
    PolicySnapshotRef,
    PrincipalRef,
    build_runtime_authority,
    canonical_digest,
    ev1_policy_snapshot_ref,
    new_opaque_id,
)

STREAM_DESCRIPTOR_SCHEMA = "relaylm.source_capture_stream_descriptor.v1"
SEQUENCE_EVENT_SCHEMA = "relaylm.capture_sequence_event.v1"
COVERAGE_CHECKPOINT_SCHEMA = "relaylm.source_capture_coverage_checkpoint.v1"
CHANGE_SET_SCHEMA = "relaylm.evidence_authority_change_set_event.v1"
CHANGE_PARTITION_SCHEMA = "relaylm.evidence_change_partition_descriptor.v1"
CHANGE_PROJECTION_SCHEMA = "relaylm.evidence_authority_change_projection_event.v1"
SOURCE_REGISTRY_SCHEMA = "relaylm.source_projection_registry_event.v1"
CHANGE_COVERAGE_SCHEMA = "relaylm.evidence_change_coverage_checkpoint.v1"

CAPTURE_STREAM_KINDS = frozenset(
    {
        "managed_user_input",
        "managed_assistant_output",
        "tool_transaction",
        "sensor_input",
        "authorized_import",
        "governed_system_event",
        "pass_through_opt_in",
    }
)
TERMINAL_OUTCOMES = frozenset(
    {"admitted", "quarantined", "ephemeral", "rejected", "duplicate_replay"}
)
_EV1_CHANGE_KINDS = frozenset({"source_admitted"})


@dataclass(frozen=True)
class SourceCaptureStreamDescriptor:
    schema: str
    capture_stream_id: str
    evidence_space_id: str
    capture_stream_kind: str
    stream_direction: str
    stream_generation: int
    capture_stream_epoch_id: str
    start_sequence: int
    stream_status: str
    descriptor_revision: int
    issuer_principal_ref: PrincipalRef
    issuer_authority_scope: AuthorityScope
    policy_snapshot_ref: PolicySnapshotRef
    created_at: str
    sealed_at_or_null: str | None = None
    retired_at_or_null: str | None = None
    expected_previous_descriptor_revision_or_null: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "capture_stream_id": self.capture_stream_id,
            "evidence_space_id": self.evidence_space_id,
            "capture_stream_kind": self.capture_stream_kind,
            "stream_direction": self.stream_direction,
            "stream_generation": self.stream_generation,
            "capture_stream_epoch_id": self.capture_stream_epoch_id,
            "start_sequence": self.start_sequence,
            "stream_status": self.stream_status,
            "descriptor_revision": self.descriptor_revision,
            "expected_previous_descriptor_revision_or_null": (
                self.expected_previous_descriptor_revision_or_null
            ),
            "created_at": self.created_at,
            "sealed_at_or_null": self.sealed_at_or_null,
            "retired_at_or_null": self.retired_at_or_null,
            "issuer_principal_ref": self.issuer_principal_ref.to_dict(),
            "issuer_authority_scope": self.issuer_authority_scope.to_dict(),
            "policy_snapshot_ref": self.policy_snapshot_ref.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "SourceCaptureStreamDescriptor":
        from relaylm.evidence_space import _authority_scope_from_dict

        return cls(
            schema=str(payload["schema"]),
            capture_stream_id=str(payload["capture_stream_id"]),
            evidence_space_id=str(payload["evidence_space_id"]),
            capture_stream_kind=str(payload["capture_stream_kind"]),
            stream_direction=str(payload["stream_direction"]),
            stream_generation=int(payload["stream_generation"]),
            capture_stream_epoch_id=str(payload["capture_stream_epoch_id"]),
            start_sequence=int(payload["start_sequence"]),
            stream_status=str(payload["stream_status"]),
            descriptor_revision=int(payload["descriptor_revision"]),
            issuer_principal_ref=PrincipalRef(**payload["issuer_principal_ref"]),  # type: ignore[arg-type]
            issuer_authority_scope=_authority_scope_from_dict(
                payload["issuer_authority_scope"]  # type: ignore[arg-type]
            ),
            policy_snapshot_ref=PolicySnapshotRef(**payload["policy_snapshot_ref"]),  # type: ignore[arg-type]
            created_at=str(payload["created_at"]),
            sealed_at_or_null=payload["sealed_at_or_null"],  # type: ignore[assignment]
            retired_at_or_null=payload["retired_at_or_null"],  # type: ignore[assignment]
            expected_previous_descriptor_revision_or_null=payload[
                "expected_previous_descriptor_revision_or_null"
            ],  # type: ignore[assignment]
        )


def build_capture_stream_descriptor(
    *,
    evidence_space_id: str,
    capture_stream_kind: str,
    stream_direction: str,
    created_at: str,
) -> tuple[SourceCaptureStreamDescriptor | None, tuple[str, ...]]:
    if capture_stream_kind not in CAPTURE_STREAM_KINDS:
        return None, ("capture_stream_kind_invalid",)
    if stream_direction not in {"inbound", "outbound", "internal", "import"}:
        return None, ("capture_stream_direction_invalid",)
    principal, scope = build_runtime_authority(
        scope_kind="capture_stream_authority",
        allowed_operations=("capture_stream_create",),
        evidence_space_id=evidence_space_id,
        issued_at=created_at,
    )
    stable = canonical_digest(
        {
            "evidence_space_id": evidence_space_id,
            "capture_stream_kind": capture_stream_kind,
            "stream_direction": stream_direction,
        }
    )
    return (
        SourceCaptureStreamDescriptor(
            schema=STREAM_DESCRIPTOR_SCHEMA,
            capture_stream_id=f"capturestream_{stable}",
            evidence_space_id=evidence_space_id,
            capture_stream_kind=capture_stream_kind,
            stream_direction=stream_direction,
            stream_generation=1,
            capture_stream_epoch_id=f"epoch_{stable}",
            start_sequence=0,
            stream_status="open",
            descriptor_revision=1,
            issuer_principal_ref=principal,
            issuer_authority_scope=scope,
            policy_snapshot_ref=ev1_policy_snapshot_ref(),
            created_at=created_at,
        ),
        (),
    )


@dataclass
class CaptureSequenceLog:
    descriptor: SourceCaptureStreamDescriptor
    events: list[dict[str, object]] = field(default_factory=list)
    _next_sequence: int = field(default=0, init=False)
    _unverifiable: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self._rebuild()

    @classmethod
    def from_events(
        cls, descriptor: SourceCaptureStreamDescriptor, events: list[dict[str, object]]
    ) -> "CaptureSequenceLog":
        return cls(descriptor=descriptor, events=list(events))

    @property
    def unverifiable(self) -> bool:
        return self._unverifiable

    def _rebuild(self) -> None:
        by_sequence: dict[int, list[dict[str, object]]] = {}
        for event in self.events:
            try:
                sequence = int(event["capture_sequence"])
            except (KeyError, TypeError, ValueError):
                self._unverifiable = True
                continue
            by_sequence.setdefault(sequence, []).append(event)
            self._next_sequence = max(self._next_sequence, sequence + 1)
        for sequence, chain in by_sequence.items():
            reserves = [e for e in chain if e.get("operation") == "reserve"]
            terminals = [
                e
                for e in chain
                if e.get("operation")
                in {"terminalize_admission", "terminalize_no_source"}
            ]
            if len(reserves) != 1 or len(terminals) > 1:
                self._unverifiable = True
                continue
            if terminals:
                reserve_attempt = reserves[0].get("operation_payload", {}).get(
                    "capture_attempt_id"
                )
                terminal_attempt = terminals[0].get("operation_payload", {}).get(
                    "capture_attempt_id"
                )
                if reserve_attempt != terminal_attempt:
                    self._unverifiable = True
            revisions = sorted(int(e.get("sequence_revision", 0)) for e in chain)
            if revisions != ([1] if not terminals else [1, 2]):
                self._unverifiable = True
            if sequence < self.descriptor.start_sequence:
                self._unverifiable = True

    def find_reservation_for_attempt(self, capture_attempt_id: str) -> int | None:
        for event in self.events:
            if (
                event.get("operation") == "reserve"
                and event.get("operation_payload", {}).get("capture_attempt_id")
                == capture_attempt_id
            ):
                return int(event["capture_sequence"])
        return None

    def _issuer(
        self, operation: str, recorded_at: str
    ) -> tuple[dict[str, object], dict[str, object]]:
        principal, scope = build_runtime_authority(
            scope_kind="capture_stream_authority",
            allowed_operations=(operation,),
            evidence_space_id=self.descriptor.evidence_space_id,
            issued_at=recorded_at,
        )
        return principal.to_dict(), scope.to_dict()

    def reserve(
        self,
        *,
        capture_attempt_id: str,
        recorded_at: str,
        operation_idempotency_key: str,
    ) -> tuple[int | None, tuple[str, ...]]:
        if self._unverifiable:
            return None, ("capture_stream_epoch_unverifiable",)
        existing = self.find_reservation_for_attempt(capture_attempt_id)
        if existing is not None:
            return existing, ()
        if self.descriptor.stream_status != "open":
            return None, ("capture_stream_not_open",)
        sequence = self._next_sequence
        self._next_sequence += 1
        principal, scope = self._issuer("capture_sequence_reserve", recorded_at)
        self.events.append(
            {
                "schema": SEQUENCE_EVENT_SCHEMA,
                "capture_sequence_event_id": new_opaque_id("captureseqevent"),
                "capture_stream_id": self.descriptor.capture_stream_id,
                "capture_stream_epoch_id": self.descriptor.capture_stream_epoch_id,
                "capture_sequence": sequence,
                "sequence_revision": 1,
                "expected_previous_sequence_revision_or_null": None,
                "operation": "reserve",
                "operation_payload": {
                    "capture_attempt_id": capture_attempt_id,
                    "reservation_basis_ref": "relaylm-managed-runtime",
                    "reserved_at": recorded_at,
                },
                "operation_idempotency_key": (
                    f"{operation_idempotency_key}:reserve"
                ),
                "recorded_at": recorded_at,
                "issuer_principal_ref": principal,
                "issuer_authority_scope": scope,
            }
        )
        return sequence, ()

    def _reserve_event(self, sequence: int) -> dict[str, object] | None:
        for event in self.events:
            if (
                event.get("capture_sequence") == sequence
                and event.get("operation") == "reserve"
            ):
                return event
        return None

    def _terminal_event(self, sequence: int) -> dict[str, object] | None:
        for event in self.events:
            if (
                event.get("capture_sequence") == sequence
                and event.get("operation")
                in {"terminalize_admission", "terminalize_no_source"}
            ):
                return event
        return None

    def terminalize_admission(
        self,
        *,
        sequence: int,
        capture_attempt_id: str,
        admission_decision_id: str,
        terminal_outcome: str,
        recorded_at: str,
        operation_idempotency_key: str,
        capture_attempt_terminal_event_id: str | None = None,
    ) -> tuple[bool, tuple[str, ...]]:
        del capture_attempt_terminal_event_id
        if self._unverifiable:
            return False, ("capture_stream_epoch_unverifiable",)
        if terminal_outcome not in TERMINAL_OUTCOMES:
            return False, ("capture_sequence_terminal_outcome_invalid",)
        reserve = self._reserve_event(sequence)
        if reserve is None:
            return False, ("capture_sequence_not_reserved",)
        if reserve["operation_payload"].get("capture_attempt_id") != capture_attempt_id:
            self._unverifiable = True
            return False, ("capture_sequence_attempt_mismatch",)
        existing = self._terminal_event(sequence)
        if existing is not None:
            payload = existing["operation_payload"]
            if (
                existing.get("operation") == "terminalize_admission"
                and payload.get("capture_attempt_id") == capture_attempt_id
                and payload.get("admission_decision_id") == admission_decision_id
                and payload.get("terminal_outcome") == terminal_outcome
            ):
                return True, ()
            self._unverifiable = True
            return False, ("capture_sequence_terminal_conflict",)
        principal, scope = self._issuer(
            "capture_sequence_terminalize_admission", recorded_at
        )
        self.events.append(
            {
                "schema": SEQUENCE_EVENT_SCHEMA,
                "capture_sequence_event_id": new_opaque_id("captureseqevent"),
                "capture_stream_id": self.descriptor.capture_stream_id,
                "capture_stream_epoch_id": self.descriptor.capture_stream_epoch_id,
                "capture_sequence": sequence,
                "sequence_revision": 2,
                "expected_previous_sequence_revision_or_null": 1,
                "operation": "terminalize_admission",
                "operation_payload": {
                    "capture_attempt_id": capture_attempt_id,
                    "admission_decision_id": admission_decision_id,
                    "terminal_outcome": terminal_outcome,
                },
                "operation_idempotency_key": (
                    f"{operation_idempotency_key}:terminalize"
                ),
                "recorded_at": recorded_at,
                "issuer_principal_ref": principal,
                "issuer_authority_scope": scope,
            }
        )
        return True, ()

    def terminalize_no_source(
        self,
        *,
        sequence: int,
        capture_attempt_id: str,
        terminal_reason: str,
        recorded_at: str,
        operation_idempotency_key: str,
        capture_attempt_terminal_event_id: str | None = None,
    ) -> tuple[bool, tuple[str, ...]]:
        if self._unverifiable:
            return False, ("capture_stream_epoch_unverifiable",)
        reserve = self._reserve_event(sequence)
        if reserve is None:
            return False, ("capture_sequence_not_reserved",)
        if reserve["operation_payload"].get("capture_attempt_id") != capture_attempt_id:
            self._unverifiable = True
            return False, ("capture_sequence_attempt_mismatch",)
        existing = self._terminal_event(sequence)
        terminal_event_id = capture_attempt_terminal_event_id or (
            "captureevent_"
            + canonical_digest(
                {
                    "capture_attempt_id": capture_attempt_id,
                    "operation": "terminal_no_source",
                }
            )
        )
        if existing is not None:
            payload = existing["operation_payload"]
            if (
                existing.get("operation") == "terminalize_no_source"
                and payload.get("capture_attempt_id") == capture_attempt_id
                and payload.get("terminal_reason") == terminal_reason
            ):
                return True, ()
            self._unverifiable = True
            return False, ("capture_sequence_terminal_conflict",)
        principal, scope = self._issuer(
            "capture_sequence_terminalize_no_source", recorded_at
        )
        self.events.append(
            {
                "schema": SEQUENCE_EVENT_SCHEMA,
                "capture_sequence_event_id": new_opaque_id("captureseqevent"),
                "capture_stream_id": self.descriptor.capture_stream_id,
                "capture_stream_epoch_id": self.descriptor.capture_stream_epoch_id,
                "capture_sequence": sequence,
                "sequence_revision": 2,
                "expected_previous_sequence_revision_or_null": 1,
                "operation": "terminalize_no_source",
                "operation_payload": {
                    "capture_attempt_id": capture_attempt_id,
                    "capture_attempt_terminal_event_id": terminal_event_id,
                    "terminal_reason": terminal_reason,
                },
                "operation_idempotency_key": (
                    f"{operation_idempotency_key}:terminalize"
                ),
                "recorded_at": recorded_at,
                "issuer_principal_ref": principal,
                "issuer_authority_scope": scope,
            }
        )
        return True, ()


@dataclass(frozen=True)
class SourceCaptureCoverageCheckpoint:
    schema: str
    coverage_checkpoint_id: str
    capture_stream_id: str
    capture_stream_epoch_id: str
    coverage_revision: int
    start_sequence: int
    highest_seen_sequence_or_null: int | None
    highest_contiguous_terminal_sequence_or_null: int | None
    missing_sequence_ranges: tuple[tuple[int, int], ...]
    nonterminal_sequence_ranges: tuple[tuple[int, int], ...]
    stream_status: str
    derived_coverage_status: str
    terminal_basis_digest_or_null: str | None
    updated_at: str
    issuer_principal_ref: PrincipalRef
    issuer_authority_scope: AuthorityScope
    operation_idempotency_key: str
    expected_previous_coverage_revision_or_null: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "coverage_checkpoint_id": self.coverage_checkpoint_id,
            "capture_stream_id": self.capture_stream_id,
            "capture_stream_epoch_id": self.capture_stream_epoch_id,
            "coverage_revision": self.coverage_revision,
            "expected_previous_coverage_revision_or_null": (
                self.expected_previous_coverage_revision_or_null
            ),
            "start_sequence": self.start_sequence,
            "highest_seen_sequence_or_null": self.highest_seen_sequence_or_null,
            "highest_contiguous_terminal_sequence_or_null": (
                self.highest_contiguous_terminal_sequence_or_null
            ),
            "missing_sequence_ranges": [
                list(item) for item in self.missing_sequence_ranges
            ],
            "nonterminal_sequence_ranges": [
                list(item) for item in self.nonterminal_sequence_ranges
            ],
            "stream_status": self.stream_status,
            "derived_coverage_status": self.derived_coverage_status,
            "terminal_basis_digest_or_null": self.terminal_basis_digest_or_null,
            "updated_at": self.updated_at,
            "issuer_principal_ref": self.issuer_principal_ref.to_dict(),
            "issuer_authority_scope": self.issuer_authority_scope.to_dict(),
            "operation_idempotency_key": self.operation_idempotency_key,
        }


def compute_coverage_checkpoint(
    descriptor: SourceCaptureStreamDescriptor,
    events: list[dict[str, object]],
    *,
    updated_at: str,
    operation_idempotency_key: str,
    coverage_revision: int = 1,
    previous_checkpoint: dict[str, object] | None = None,
) -> SourceCaptureCoverageCheckpoint:
    if previous_checkpoint is not None:
        previous_revision = int(previous_checkpoint.get("coverage_revision", 0))
        coverage_revision = previous_revision + 1
        expected_previous = previous_revision
    else:
        expected_previous = coverage_revision - 1 if coverage_revision > 1 else None
    log = CaptureSequenceLog.from_events(descriptor, events)
    principal, scope = build_runtime_authority(
        scope_kind="capture_stream_authority",
        allowed_operations=("capture_coverage_advance",),
        evidence_space_id=descriptor.evidence_space_id,
        issued_at=updated_at,
    )
    reserved: dict[int, str] = {}
    terminal: dict[int, str] = {}
    for event in events:
        sequence = int(event.get("capture_sequence", -1))
        if event.get("operation") == "reserve":
            reserved[sequence] = str(event.get("capture_sequence_event_id"))
        elif event.get("operation") in {
            "terminalize_admission",
            "terminalize_no_source",
        }:
            terminal[sequence] = str(event.get("capture_sequence_event_id"))
    if not reserved:
        status = "unverifiable" if log.unverifiable else "empty_open"
        return SourceCaptureCoverageCheckpoint(
            schema=COVERAGE_CHECKPOINT_SCHEMA,
            coverage_checkpoint_id=new_opaque_id("coveragecp"),
            capture_stream_id=descriptor.capture_stream_id,
            capture_stream_epoch_id=descriptor.capture_stream_epoch_id,
            coverage_revision=coverage_revision,
            expected_previous_coverage_revision_or_null=expected_previous,
            start_sequence=descriptor.start_sequence,
            highest_seen_sequence_or_null=None,
            highest_contiguous_terminal_sequence_or_null=None,
            missing_sequence_ranges=(),
            nonterminal_sequence_ranges=(),
            stream_status=descriptor.stream_status,
            derived_coverage_status=status,
            terminal_basis_digest_or_null=None,
            updated_at=updated_at,
            issuer_principal_ref=principal,
            issuer_authority_scope=scope,
            operation_idempotency_key=(
                f"{operation_idempotency_key}:coverage:{coverage_revision}"
            ),
        )
    highest_seen = max(reserved)
    missing: list[tuple[int, int]] = []
    nonterminal: list[tuple[int, int]] = []
    run_kind: str | None = None
    run_start: int | None = None
    for sequence in range(descriptor.start_sequence, highest_seen + 1):
        kind = (
            "missing"
            if sequence not in reserved
            else ("nonterminal" if sequence not in terminal else None)
        )
        if kind != run_kind:
            if run_kind is not None and run_start is not None:
                (missing if run_kind == "missing" else nonterminal).append(
                    (run_start, sequence - 1)
                )
            run_kind = kind
            run_start = sequence if kind is not None else None
    if run_kind is not None and run_start is not None:
        (missing if run_kind == "missing" else nonterminal).append(
            (run_start, highest_seen)
        )
    highest_contiguous = None
    for sequence in range(descriptor.start_sequence, highest_seen + 1):
        if sequence not in terminal:
            break
        highest_contiguous = sequence
    terminal_digest = None
    if highest_contiguous is not None:
        terminal_digest = canonical_digest(
            {
                "pairs": [
                    [sequence, terminal[sequence]]
                    for sequence in range(
                        descriptor.start_sequence, highest_contiguous + 1
                    )
                ]
            }
        )
    if log.unverifiable:
        status = "unverifiable"
    elif descriptor.stream_status == "sealed":
        status = (
            "sealed_complete"
            if not missing and not nonterminal
            else "sealed_incomplete"
        )
    else:
        status = (
            "open_contiguous"
            if not missing and not nonterminal
            else "open_incomplete"
        )
    return SourceCaptureCoverageCheckpoint(
        schema=COVERAGE_CHECKPOINT_SCHEMA,
        coverage_checkpoint_id=new_opaque_id("coveragecp"),
        capture_stream_id=descriptor.capture_stream_id,
        capture_stream_epoch_id=descriptor.capture_stream_epoch_id,
        coverage_revision=coverage_revision,
        expected_previous_coverage_revision_or_null=expected_previous,
        start_sequence=descriptor.start_sequence,
        highest_seen_sequence_or_null=highest_seen,
        highest_contiguous_terminal_sequence_or_null=highest_contiguous,
        missing_sequence_ranges=tuple(missing),
        nonterminal_sequence_ranges=tuple(nonterminal),
        stream_status=descriptor.stream_status,
        derived_coverage_status=status,
        terminal_basis_digest_or_null=terminal_digest,
        updated_at=updated_at,
        issuer_principal_ref=principal,
        issuer_authority_scope=scope,
        operation_idempotency_key=(
            f"{operation_idempotency_key}:coverage:{coverage_revision}"
        ),
    )


@dataclass(frozen=True)
class AuthorityChangeSetRefResult:
    change_set_id: str
    change_projection_plan_digest: str
    plan_event: dict[str, object]
    projection_event: dict[str, object]
    mark_complete_event: dict[str, object]
    partition_descriptor: dict[str, object]
    registry_event: dict[str, object]
    change_coverage_checkpoint: dict[str, object]


def derive_participant_change_partition_id(
    *, evidence_space_id: str, participant_ref: PrincipalRef
) -> str:
    seed = canonical_digest(
        {
            "evidence_space_id": evidence_space_id,
            "kind": "participant",
            "participant_ref": participant_ref.to_dict(),
        }
    )
    return f"partition_{seed}"


def reserve_and_complete_authority_change_set(
    *,
    change_set_id: str,
    change_kind: str,
    evidence_space_id: str,
    authoritative_mutation_refs: tuple[dict[str, object], ...],
    recorded_at: str,
    participant_ref: PrincipalRef | None = None,
    partition_sequence: int = 0,
    change_coverage_revision: int = 1,
    expected_previous_change_coverage_revision_or_null: int | None = None,
    partition_descriptor_issued_at: str | None = None,
    existing_projection_events: tuple[dict[str, object], ...] = (),
) -> tuple[AuthorityChangeSetRefResult | None, tuple[str, ...]]:
    if change_kind not in _EV1_CHANGE_KINDS:
        return None, ("evidence_change_kind_unsupported_in_ev1",)
    if change_kind == "source_admitted" and participant_ref is None:
        return None, ("evidence_change_participant_ref_required",)
    assert participant_ref is not None
    if type(partition_sequence) is not int or partition_sequence < 0:
        return None, ("evidence_change_partition_sequence_invalid",)

    refs = tuple(
        {
            "record_kind": str(ref.get("record_kind")),
            "record_id": str(ref.get("record_id")),
            "record_revision_or_null": ref.get("record_revision_or_null"),
        }
        for ref in authoritative_mutation_refs
    )
    participant_payload = participant_ref.to_dict()
    partition_id = derive_participant_change_partition_id(
        evidence_space_id=evidence_space_id, participant_ref=participant_ref
    )
    partition_seed = partition_id.removeprefix("partition_")
    epoch_id = f"partitionepoch_{partition_seed}"
    source_refs = sorted(
        str(ref["record_id"])
        for ref in refs
        if ref["record_kind"] == "source_event"
    )
    if not source_refs:
        return None, ("evidence_change_source_event_ref_required",)

    plan_entry = {
        "change_partition_ref": partition_id,
        "projection_visibility": "normal_consumer",
        "consumer_effect": "candidate_available",
        "authorized_source_event_refs": source_refs,
        "authorized_control_ref_classes": [],
    }
    plan_digest = canonical_digest(
        {
            "change_kind": change_kind,
            "authoritative_mutation_refs": list(refs),
            "projection_plan": [plan_entry],
        }
    )
    plan_principal, plan_scope = build_runtime_authority(
        scope_kind="change_feed_authority",
        allowed_operations=("change_set_plan",),
        evidence_space_id=evidence_space_id,
        issued_at=recorded_at,
    )
    plan_event = {
        "schema": CHANGE_SET_SCHEMA,
        "change_set_event_id": new_opaque_id("changesetevent"),
        "change_set_id": change_set_id,
        "change_set_revision": 1,
        "expected_previous_change_set_revision_or_null": None,
        "evidence_space_id": evidence_space_id,
        "operation": "plan",
        "operation_payload": {
            "authoritative_mutation_refs": list(refs),
            "change_kind": change_kind,
            "projection_plan": [plan_entry],
            "projection_plan_digest": plan_digest,
        },
        "recorded_at": recorded_at,
        "issuer_principal_ref": plan_principal.to_dict(),
        "issuer_authority_scope": plan_scope.to_dict(),
        "operation_idempotency_key": f"{change_set_id}:plan",
    }
    partition_principal, partition_scope = build_runtime_authority(
        scope_kind="change_feed_authority",
        allowed_operations=("change_partition_create",),
        evidence_space_id=evidence_space_id,
        issued_at=partition_descriptor_issued_at or recorded_at,
    )
    partition_descriptor = {
        "schema": CHANGE_PARTITION_SCHEMA,
        "change_partition_id": partition_id,
        "evidence_space_id": evidence_space_id,
        "partition_kind": "participant",
        "participant_ref_or_null": participant_payload,
        "relationship_ref_or_null": None,
        "room_ref_or_null": None,
        "shared_scene_ref_or_null": None,
        "partition_reader_selector": {
            "kind": "exact_principals",
            "principal_refs": [participant_payload],
        },
        "partition_epoch_id": epoch_id,
        "start_sequence": 0,
        "partition_status": "open",
        "descriptor_revision": 1,
        "expected_previous_descriptor_revision_or_null": None,
        "policy_snapshot_ref": ev1_policy_snapshot_ref().to_dict(),
        "issuer_principal_ref": partition_principal.to_dict(),
        "issuer_authority_scope": partition_scope.to_dict(),
    }
    projection_event_id = "changeprojection_" + canonical_digest(
        {"change_set_id": change_set_id, "change_partition_id": partition_id}
    )
    projection_event = {
        "schema": CHANGE_PROJECTION_SCHEMA,
        "projection_event_id": projection_event_id,
        "change_set_id": change_set_id,
        "change_partition_id": partition_id,
        "partition_epoch_id": epoch_id,
        "partition_sequence": partition_sequence,
        "projection_event_kind": "authority_change",
        "change_kind_or_null": change_kind,
        "authoritative_mutation_refs": list(refs),
        "authorized_source_event_refs": source_refs,
        "authorized_control_refs": [],
        "consumer_effect_or_null": "candidate_available",
        "projection_visibility_or_null": "normal_consumer",
        "recorded_at": recorded_at,
        "operation_idempotency_key": f"{change_set_id}:projection:{partition_id}",
    }

    prior_by_sequence: dict[int, str] = {}
    for event in existing_projection_events:
        if (
            event.get("change_partition_id") != partition_id
            or event.get("partition_epoch_id") != epoch_id
        ):
            return None, ("evidence_change_projection_partition_mismatch",)
        try:
            sequence = int(event["partition_sequence"])
            event_id = str(event["projection_event_id"])
        except (KeyError, TypeError, ValueError):
            return None, ("evidence_change_projection_shape_invalid",)
        if sequence in prior_by_sequence and prior_by_sequence[sequence] != event_id:
            return None, ("evidence_change_projection_sequence_conflict",)
        prior_by_sequence[sequence] = event_id
    if sorted(prior_by_sequence) != list(range(partition_sequence)):
        return None, ("evidence_change_projection_coverage_gap",)

    completed_digest = canonical_digest(
        {"pairs": [{"plan_entry": plan_entry, "projection_event": projection_event}]}
    )
    complete_principal, complete_scope = build_runtime_authority(
        scope_kind="change_feed_authority",
        allowed_operations=("change_set_mark_complete",),
        evidence_space_id=evidence_space_id,
        issued_at=recorded_at,
    )
    mark_complete_event = {
        "schema": CHANGE_SET_SCHEMA,
        "change_set_event_id": new_opaque_id("changesetevent"),
        "change_set_id": change_set_id,
        "change_set_revision": 2,
        "expected_previous_change_set_revision_or_null": 1,
        "evidence_space_id": evidence_space_id,
        "operation": "mark_complete",
        "operation_payload": {
            "planned_change_set_revision": 1,
            "completed_projection_event_ids": [projection_event_id],
            "completed_projection_digest": completed_digest,
        },
        "recorded_at": recorded_at,
        "issuer_principal_ref": complete_principal.to_dict(),
        "issuer_authority_scope": complete_scope.to_dict(),
        "operation_idempotency_key": f"{change_set_id}:mark_complete",
    }
    registry_principal, registry_scope = build_runtime_authority(
        scope_kind="change_feed_authority",
        allowed_operations=("source_projection_registry_initialize",),
        evidence_space_id=evidence_space_id,
        issued_at=recorded_at,
    )
    registry_event = {
        "schema": SOURCE_REGISTRY_SCHEMA,
        "registry_event_id": new_opaque_id("registryevent"),
        "source_event_id": source_refs[0],
        "evidence_space_id": evidence_space_id,
        "registry_revision": 1,
        "expected_previous_registry_revision_or_null": None,
        "operation": "initialize",
        "partition_entries": [
            {
                "change_partition_id": partition_id,
                "partition_epoch_id": epoch_id,
                "visibility_class": "normal_source_visibility",
                "first_projection_event_id": projection_event_id,
                "revocation_target_partition_ref": partition_id,
                "retired_at_or_null": None,
                "retirement_basis_ref_or_null": None,
            }
        ],
        "recorded_at": recorded_at,
        "issuer_principal_ref": registry_principal.to_dict(),
        "issuer_authority_scope": registry_scope.to_dict(),
        "operation_idempotency_key": f"{change_set_id}:registry",
    }
    coverage_principal, coverage_scope = build_runtime_authority(
        scope_kind="change_feed_authority",
        allowed_operations=("change_coverage_advance",),
        evidence_space_id=evidence_space_id,
        issued_at=recorded_at,
    )
    cumulative_pairs = [
        [sequence, prior_by_sequence[sequence]] for sequence in range(partition_sequence)
    ]
    cumulative_pairs.append([partition_sequence, projection_event_id])
    change_coverage_checkpoint = {
        "schema": CHANGE_COVERAGE_SCHEMA,
        "change_coverage_checkpoint_id": new_opaque_id("changecoverage"),
        "change_partition_id": partition_id,
        "partition_epoch_id": epoch_id,
        "coverage_revision": change_coverage_revision,
        "expected_previous_coverage_revision_or_null": (
            expected_previous_change_coverage_revision_or_null
        ),
        "start_sequence": 0,
        "highest_seen_sequence_or_null": partition_sequence,
        "highest_contiguous_committed_sequence_or_null": partition_sequence,
        "missing_sequence_ranges": [],
        "nonterminal_sequence_ranges": [],
        "partition_status": "open",
        "derived_coverage_status": "open_contiguous",
        "change_basis_digest_or_null": canonical_digest({"pairs": cumulative_pairs}),
        "updated_at": recorded_at,
        "issuer_principal_ref": coverage_principal.to_dict(),
        "issuer_authority_scope": coverage_scope.to_dict(),
        "operation_idempotency_key": (
            f"{change_set_id}:change-coverage:{change_coverage_revision}"
        ),
    }
    return (
        AuthorityChangeSetRefResult(
            change_set_id=change_set_id,
            change_projection_plan_digest=plan_digest,
            plan_event=plan_event,
            projection_event=projection_event,
            mark_complete_event=mark_complete_event,
            partition_descriptor=partition_descriptor,
            registry_event=registry_event,
            change_coverage_checkpoint=change_coverage_checkpoint,
        ),
        (),
    )


__all__ = [
    "CAPTURE_STREAM_KINDS",
    "CHANGE_COVERAGE_SCHEMA",
    "CHANGE_PARTITION_SCHEMA",
    "CHANGE_PROJECTION_SCHEMA",
    "CHANGE_SET_SCHEMA",
    "COVERAGE_CHECKPOINT_SCHEMA",
    "SEQUENCE_EVENT_SCHEMA",
    "SOURCE_REGISTRY_SCHEMA",
    "STREAM_DESCRIPTOR_SCHEMA",
    "TERMINAL_OUTCOMES",
    "AuthorityChangeSetRefResult",
    "CaptureSequenceLog",
    "SourceCaptureCoverageCheckpoint",
    "SourceCaptureStreamDescriptor",
    "build_capture_stream_descriptor",
    "compute_coverage_checkpoint",
    "derive_participant_change_partition_id",
    "reserve_and_complete_authority_change_set",
]
