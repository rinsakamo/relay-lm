"""SourceEvent v1, ValidationBundleRevision v1, AdmissionDecision v1 (Contract 1A).

EV-1 boundary: only the ``admitted`` and ``rejected`` outcomes are reachable.
Quarantine, ephemeral, and duplicate-replay handling are explicitly out of
scope for the first apply slice (the governing prompt calls for "a
deterministic admitted-or-fail-closed policy for valid managed private
text"), so ``SourceReplayIdentity`` uses the ``none`` variant (content-digest
distinct admission; the contract permits this "only when policy requires
content-digest-based distinct admission" -- retry/duplicate detection across
turns is deferred to a later slice) except for assistant responses, which use
the Contract-1E-owned ``managed_response_identity`` variant.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from relaylm.evidence.common import (
    AuthorityChangeSetRef,
    AuthorityScope,
    PolicySnapshotRef,
    PrincipalRef,
    build_runtime_authority,
    ev1_policy_snapshot_ref,
)
from relaylm.evidence.manifest import (
    CanonicalSourceManifest,
    OccurrenceAudienceSnapshot,
    ProvenanceSnapshot,
    SourceOccurrenceTime,
)

SOURCE_EVENT_SCHEMA = "relaylm.source_event.v1"
VALIDATION_BUNDLE_SCHEMA = "relaylm.admission_validation_bundle_revision.v1"
ADMISSION_DECISION_SCHEMA = "relaylm.evidence_admission_decision.v1"

ORIGIN_KINDS = frozenset(
    {"participant", "assistant", "tool", "sensor", "system", "import", "external"}
)
SPEAKER_IDENTITY_STATUSES = frozenset(
    {"verified", "asserted", "unresolved", "conflicting", "not_applicable"}
)

ADMISSION_OUTCOMES = frozenset(
    {"admitted", "quarantined", "ephemeral", "rejected", "duplicate_replay"}
)
# EV-1 only ever reaches this narrowed subset of the full reason-code enum.
_EV1_REACHABLE_REASON_CODES = frozenset(
    {
        "admitted_policy_valid",
        "admitted_managed_assistant_response",
        "rejected_schema_invalid",
        "rejected_content_policy",
    }
)


@dataclass(frozen=True)
class SourceReplayIdentityNone:
    kind: str = field(default="none", init=False)

    def to_dict(self) -> dict[str, object]:
        return {"kind": "none"}


@dataclass(frozen=True)
class ManagedResponseIdentity:
    response_id: str
    delivery_cohort_id: str
    response_finalization_idempotency_key: str
    canonical_response_binding_digest: str
    kind: str = field(default="managed_response_identity", init=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "response_id": self.response_id,
            "delivery_cohort_id": self.delivery_cohort_id,
            "response_finalization_idempotency_key": (
                self.response_finalization_idempotency_key
            ),
            "canonical_response_binding_digest": self.canonical_response_binding_digest,
        }


@dataclass(frozen=True)
class ValidationBundleRevision:
    schema: str
    validation_bundle_revision_id: str
    validation_bundle_id: str
    capture_attempt_id: str
    source_event_id_or_null: str | None
    bundle_revision: int
    expected_previous_bundle_revision_or_null: int | None
    bundle_state: str
    gate_requirements: tuple[dict[str, str], ...]
    active_artifact_refs: tuple[str, ...]
    policy_snapshot_ref: PolicySnapshotRef
    authority_principal_ref: PrincipalRef
    authority_scope: AuthorityScope
    recorded_at: str
    authority_change_set_ref_or_null: AuthorityChangeSetRef | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "validation_bundle_revision_id": self.validation_bundle_revision_id,
            "validation_bundle_id": self.validation_bundle_id,
            "capture_attempt_id": self.capture_attempt_id,
            "source_event_id_or_null": self.source_event_id_or_null,
            "bundle_revision": self.bundle_revision,
            "expected_previous_bundle_revision_or_null": (
                self.expected_previous_bundle_revision_or_null
            ),
            "bundle_state": self.bundle_state,
            "gate_requirements": [dict(item) for item in self.gate_requirements],
            "active_artifact_refs": list(self.active_artifact_refs),
            "policy_snapshot_ref": self.policy_snapshot_ref.to_dict(),
            "authority_principal_ref": self.authority_principal_ref.to_dict(),
            "authority_scope": self.authority_scope.to_dict(),
            "recorded_at": self.recorded_at,
            "authority_change_set_ref_or_null": (
                self.authority_change_set_ref_or_null.to_dict()
                if self.authority_change_set_ref_or_null is not None
                else None
            ),
        }


def build_valid_validation_bundle(
    *,
    validation_bundle_id: str,
    validation_bundle_revision_id: str,
    capture_attempt_id: str,
    source_event_id: str | None,
    evidence_space_id: str,
    recorded_at: str,
    gate_kinds: tuple[str, ...],
    gate_artifact_refs: tuple[tuple[str, str], ...],
) -> ValidationBundleRevision:
    """Build a valid bundle only when every gate has one real artifact."""

    if not gate_kinds or len(set(gate_kinds)) != len(gate_kinds):
        raise ValueError("validation_bundle_gate_kinds_invalid")
    artifact_by_gate: dict[str, str] = {}
    for gate_kind, artifact_ref in gate_artifact_refs:
        if gate_kind in artifact_by_gate or not artifact_ref:
            raise ValueError("validation_bundle_artifact_refs_invalid")
        artifact_by_gate[gate_kind] = artifact_ref
    if set(artifact_by_gate) != set(gate_kinds):
        raise ValueError("validation_bundle_gate_artifact_coverage_incomplete")
    authority_principal_ref, authority_scope = build_runtime_authority(
        scope_kind="evidence_operator",
        allowed_operations=("validation_bundle_create",),
        evidence_space_id=evidence_space_id,
        issued_at=recorded_at,
    )
    gate_requirements = tuple(
        {
            "requirement_id": f"requirement:{gate_kind}",
            "gate_kind": gate_kind,
            "required_result": "pass",
        }
        for gate_kind in gate_kinds
    )
    return ValidationBundleRevision(
        schema=VALIDATION_BUNDLE_SCHEMA,
        validation_bundle_revision_id=validation_bundle_revision_id,
        validation_bundle_id=validation_bundle_id,
        capture_attempt_id=capture_attempt_id,
        source_event_id_or_null=source_event_id,
        bundle_revision=1,
        expected_previous_bundle_revision_or_null=None,
        bundle_state="valid",
        gate_requirements=gate_requirements,
        active_artifact_refs=tuple(artifact_by_gate[gate] for gate in gate_kinds),
        policy_snapshot_ref=ev1_policy_snapshot_ref(),
        authority_principal_ref=authority_principal_ref,
        authority_scope=authority_scope,
        recorded_at=recorded_at,
    )


@dataclass(frozen=True)
class SourceEvent:
    schema: str
    source_event_id: str
    evidence_space_id: str
    evidence_space_descriptor_revision: int
    capture_attempt_id: str
    capture_stream_epoch_id: str
    capture_sequence: int
    route_capture_grant_snapshot_ref: str
    received_at: str
    observed_at: str
    capture_channel: str
    source_role: str
    origin_kind: str
    producer_principal_ref: PrincipalRef
    authenticated_account_ref_or_null: str | None
    represented_speaker_ref_or_null: PrincipalRef | None
    speaker_identity_status: str
    source_occurrence_time: SourceOccurrenceTime
    configured_occurrence_audience: OccurrenceAudienceSnapshot
    scene_occurrence_ref_or_null: str | None
    conversation_ref_or_null: str | None
    canonical_source_manifest: CanonicalSourceManifest
    canonical_source_manifest_digest: str
    protected_payload_binding_attestation_ids: tuple[str, ...]
    source_replay_identity: SourceReplayIdentityNone | ManagedResponseIdentity
    assistant_response_binding_ref_or_null: str | None
    provenance_snapshot: ProvenanceSnapshot
    authority_change_set_ref: AuthorityChangeSetRef

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source_event_id": self.source_event_id,
            "evidence_space_id": self.evidence_space_id,
            "evidence_space_descriptor_revision": self.evidence_space_descriptor_revision,
            "capture_attempt_id": self.capture_attempt_id,
            "capture_stream_epoch_id": self.capture_stream_epoch_id,
            "capture_sequence": self.capture_sequence,
            "route_capture_grant_snapshot_ref": self.route_capture_grant_snapshot_ref,
            "received_at": self.received_at,
            "observed_at": self.observed_at,
            "capture_channel": self.capture_channel,
            "source_role": self.source_role,
            "origin_kind": self.origin_kind,
            "producer_principal_ref": self.producer_principal_ref.to_dict(),
            "authenticated_account_ref_or_null": self.authenticated_account_ref_or_null,
            "represented_speaker_ref_or_null": (
                self.represented_speaker_ref_or_null.to_dict()
                if self.represented_speaker_ref_or_null is not None
                else None
            ),
            "speaker_identity_status": self.speaker_identity_status,
            "source_occurrence_time": self.source_occurrence_time.to_dict(),
            "configured_occurrence_audience": self.configured_occurrence_audience.to_dict(),
            "scene_occurrence_ref_or_null": self.scene_occurrence_ref_or_null,
            "conversation_ref_or_null": self.conversation_ref_or_null,
            "canonical_source_manifest": self.canonical_source_manifest.to_dict(),
            "canonical_source_manifest_digest": self.canonical_source_manifest_digest,
            "protected_payload_binding_attestation_ids": list(
                self.protected_payload_binding_attestation_ids
            ),
            "source_replay_identity": self.source_replay_identity.to_dict(),
            "assistant_response_binding_ref_or_null": (
                self.assistant_response_binding_ref_or_null
            ),
            "provenance_snapshot": self.provenance_snapshot.to_dict(),
            "authority_change_set_ref": self.authority_change_set_ref.to_dict(),
        }


@dataclass(frozen=True)
class AdmissionDecision:
    schema: str
    admission_decision_id: str
    capture_attempt_id: str
    evidence_space_id: str
    operation_idempotency_key: str
    outcome: str
    primary_reason_code: str
    reason_codes: tuple[str, ...]
    decided_at: str
    decider_principal_ref: PrincipalRef
    decider_authority_scope: AuthorityScope
    policy_snapshot_ref: PolicySnapshotRef
    route_capture_grant_snapshot_ref: str
    replay_resolution: dict[str, object]
    canonical_source_manifest_digest_or_null: str | None
    validation_bundle_id_or_null: str | None
    validation_bundle_revision_or_null: int | None
    source_event_id_or_null: str | None
    initial_governance_event_id_or_null: str | None
    authority_change_set_ref_or_null: AuthorityChangeSetRef | None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "admission_decision_id": self.admission_decision_id,
            "capture_attempt_id": self.capture_attempt_id,
            "evidence_space_id": self.evidence_space_id,
            "operation_idempotency_key": self.operation_idempotency_key,
            "outcome": self.outcome,
            "primary_reason_code": self.primary_reason_code,
            "reason_codes": list(self.reason_codes),
            "decided_at": self.decided_at,
            "decider_principal_ref": self.decider_principal_ref.to_dict(),
            "decider_authority_scope": self.decider_authority_scope.to_dict(),
            "policy_snapshot_ref": self.policy_snapshot_ref.to_dict(),
            "route_capture_grant_snapshot_ref": self.route_capture_grant_snapshot_ref,
            "replay_resolution": dict(self.replay_resolution),
            "canonical_source_manifest_digest_or_null": (
                self.canonical_source_manifest_digest_or_null
            ),
            "validation_bundle_id_or_null": self.validation_bundle_id_or_null,
            "validation_bundle_revision_or_null": self.validation_bundle_revision_or_null,
            "source_event_id_or_null": self.source_event_id_or_null,
            "initial_governance_event_id_or_null": (
                self.initial_governance_event_id_or_null
            ),
            "authority_change_set_ref_or_null": (
                self.authority_change_set_ref_or_null.to_dict()
                if self.authority_change_set_ref_or_null is not None
                else None
            ),
        }


def build_rejected_admission_decision(
    *,
    admission_decision_id: str,
    capture_attempt_id: str,
    evidence_space_id: str,
    operation_idempotency_key: str,
    route_capture_grant_snapshot_ref: str,
    decided_at: str,
    reason_code: str = "rejected_schema_invalid",
) -> AdmissionDecision:
    decider_principal_ref, decider_authority_scope = build_runtime_authority(
        scope_kind="evidence_operator",
        allowed_operations=("admission_decide",),
        evidence_space_id=evidence_space_id,
        issued_at=decided_at,
    )
    return AdmissionDecision(
        schema=ADMISSION_DECISION_SCHEMA,
        admission_decision_id=admission_decision_id,
        capture_attempt_id=capture_attempt_id,
        evidence_space_id=evidence_space_id,
        operation_idempotency_key=operation_idempotency_key,
        outcome="rejected",
        primary_reason_code=reason_code,
        reason_codes=(reason_code,),
        decided_at=decided_at,
        decider_principal_ref=decider_principal_ref,
        decider_authority_scope=decider_authority_scope,
        policy_snapshot_ref=ev1_policy_snapshot_ref(),
        route_capture_grant_snapshot_ref=route_capture_grant_snapshot_ref,
        replay_resolution={"kind": "none"},
        canonical_source_manifest_digest_or_null=None,
        validation_bundle_id_or_null=None,
        validation_bundle_revision_or_null=None,
        source_event_id_or_null=None,
        initial_governance_event_id_or_null=None,
        authority_change_set_ref_or_null=None,
    )


def build_admitted_admission_decision(
    *,
    admission_decision_id: str,
    capture_attempt_id: str,
    evidence_space_id: str,
    operation_idempotency_key: str,
    route_capture_grant_snapshot_ref: str,
    decided_at: str,
    manifest_digest: str,
    validation_bundle: ValidationBundleRevision,
    source_event_id: str,
    initial_governance_event_id: str,
    authority_change_set_ref: AuthorityChangeSetRef,
    reason_code: str = "admitted_policy_valid",
) -> AdmissionDecision:
    decider_principal_ref, decider_authority_scope = build_runtime_authority(
        scope_kind="evidence_operator",
        allowed_operations=("admission_decide",),
        evidence_space_id=evidence_space_id,
        issued_at=decided_at,
    )
    return AdmissionDecision(
        schema=ADMISSION_DECISION_SCHEMA,
        admission_decision_id=admission_decision_id,
        capture_attempt_id=capture_attempt_id,
        evidence_space_id=evidence_space_id,
        operation_idempotency_key=operation_idempotency_key,
        outcome="admitted",
        primary_reason_code=reason_code,
        reason_codes=(reason_code,),
        decided_at=decided_at,
        decider_principal_ref=decider_principal_ref,
        decider_authority_scope=decider_authority_scope,
        policy_snapshot_ref=ev1_policy_snapshot_ref(),
        route_capture_grant_snapshot_ref=route_capture_grant_snapshot_ref,
        replay_resolution={"kind": "new_source", "source_event_id": source_event_id},
        canonical_source_manifest_digest_or_null=manifest_digest,
        validation_bundle_id_or_null=validation_bundle.validation_bundle_id,
        validation_bundle_revision_or_null=validation_bundle.bundle_revision,
        source_event_id_or_null=source_event_id,
        initial_governance_event_id_or_null=initial_governance_event_id,
        authority_change_set_ref_or_null=authority_change_set_ref,
    )


def source_event_replay_identity_kind(source_role: str) -> str:
    return "managed_response_identity" if source_role == "assistant_response" else "none"


__all__ = [
    "ADMISSION_DECISION_SCHEMA",
    "ADMISSION_OUTCOMES",
    "ORIGIN_KINDS",
    "SOURCE_EVENT_SCHEMA",
    "SPEAKER_IDENTITY_STATUSES",
    "VALIDATION_BUNDLE_SCHEMA",
    "AdmissionDecision",
    "ManagedResponseIdentity",
    "SourceEvent",
    "SourceReplayIdentityNone",
    "ValidationBundleRevision",
    "build_admitted_admission_decision",
    "build_rejected_admission_decision",
    "build_valid_validation_bundle",
    "source_event_replay_identity_kind",
]
