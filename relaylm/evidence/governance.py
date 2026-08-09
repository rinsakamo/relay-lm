"""EvidenceGovernanceState v1 / EvidenceGovernanceEvent v1 / AccessGrant v1
(Contract 1B), narrowed to the ``initialize_admitted`` transition EV-1 needs.

Quarantine, holds, redaction, purge, export, and replication are all out of
the EV-1 boundary (no ``rejected``/``quarantined`` SourceEvent ever reaches
this module -- ``evidence_user_input``/``evidence_response_capture`` only
call here for the admitted path), so only ``initialize_admitted`` is
implemented.
"""
from __future__ import annotations

from dataclasses import dataclass

from relaylm.evidence.common import (
    AuthorityChangeSetRef,
    AuthorityScope,
    PolicySnapshotRef,
    PrincipalRef,
    build_runtime_authority,
    canonical_digest,
    ev1_policy_snapshot_ref,
)

GOVERNANCE_EVENT_SCHEMA = "relaylm.evidence_governance_event.v1"
ACCESS_GRANT_SCHEMA = "relaylm.evidence_access_grant.v1"

GRANT_PURPOSES = frozenset(
    {
        "relayctx_evidence_read",
        "relayref_observation_read",
        "shared_assessment_read",
        "authorized_evidence_review",
        "user_export_eligible",
        "replication_eligible",
        "recovery_read",
    }
)
_SERVICE_CLASS_BY_PURPOSE = {
    "relayctx_evidence_read": "relayctx_service",
    "shared_assessment_read": "shared_assessment_service",
    "relayref_observation_read": "relayref_service",
}


@dataclass(frozen=True)
class AccessGrant:
    schema: str
    grant_id: str
    source_event_id: str
    evidence_space_id: str
    purpose: str
    grantee_service_class: str
    part_selector: str
    metadata_projection_selectors: tuple[str, ...]
    subject_selector: str
    audience_use_constraint: str
    locality_constraint: str
    destination_class_constraint: str
    policy_snapshot_ref: PolicySnapshotRef
    admission_decision_id: str
    governance_revision: int
    metadata_revision: int
    validation_bundle_revision: int
    issued_by_principal_ref: PrincipalRef
    issued_by_authority_scope: AuthorityScope
    issued_at: str
    expires_at_or_null: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "grant_id": self.grant_id,
            "source_event_id": self.source_event_id,
            "evidence_space_id": self.evidence_space_id,
            "purpose": self.purpose,
            "grantee": {"kind": "service_class", "service_class": self.grantee_service_class},
            "part_selector": {"kind": self.part_selector},
            "metadata_projection_selectors": list(self.metadata_projection_selectors),
            "subject_selector": {"kind": self.subject_selector},
            "audience_use_constraint": {"kind": self.audience_use_constraint},
            "locality_constraint": self.locality_constraint,
            "destination_class_constraint": self.destination_class_constraint,
            "grant_basis": {
                "policy_snapshot_ref": self.policy_snapshot_ref.to_dict(),
                "authorization_basis_ref": "relaylm.evidence_policy.v1",
                "admission_decision_id": self.admission_decision_id,
                "governance_revision": self.governance_revision,
                "metadata_revision": self.metadata_revision,
                "validation_bundle_revision": self.validation_bundle_revision,
            },
            "issued_by_principal_ref": self.issued_by_principal_ref.to_dict(),
            "issued_by_authority_scope": self.issued_by_authority_scope.to_dict(),
            "issued_at": self.issued_at,
            "expires_at_or_null": self.expires_at_or_null,
        }


def build_least_privilege_grant(
    *,
    grant_id: str,
    source_event_id: str,
    evidence_space_id: str,
    purpose: str,
    admission_decision_id: str,
    validation_bundle_revision: int,
    issued_at: str,
) -> tuple[AccessGrant | None, tuple[str, ...]]:
    if purpose not in _SERVICE_CLASS_BY_PURPOSE:
        return None, ("evidence_grant_purpose_unsupported_in_ev1",)
    issued_by_principal_ref, issued_by_authority_scope = build_runtime_authority(
        scope_kind="evidence_operator",
        allowed_operations=("grant_access",),
        evidence_space_id=evidence_space_id,
        issued_at=issued_at,
    )
    return (
        AccessGrant(
            schema=ACCESS_GRANT_SCHEMA,
            grant_id=grant_id,
            source_event_id=source_event_id,
            evidence_space_id=evidence_space_id,
            purpose=purpose,
            grantee_service_class=_SERVICE_CLASS_BY_PURPOSE[purpose],
            part_selector="all_currently_available_parts",
            metadata_projection_selectors=("source_identity_basic",),
            subject_selector="producer",
            audience_use_constraint="exact_occurrence_audience",
            locality_constraint="device_local_only",
            destination_class_constraint="no_external_destination",
            policy_snapshot_ref=ev1_policy_snapshot_ref(),
            admission_decision_id=admission_decision_id,
            governance_revision=1,
            metadata_revision=0,
            validation_bundle_revision=validation_bundle_revision,
            issued_by_principal_ref=issued_by_principal_ref,
            issued_by_authority_scope=issued_by_authority_scope,
            issued_at=issued_at,
            expires_at_or_null=None,
        ),
        (),
    )


@dataclass(frozen=True)
class EvidenceGovernanceState:
    schema: str
    source_event_id: str
    record_access_state: str
    integrity_state: str
    retention_class: str
    access_until: str
    purge_due_at: str
    locality: str
    part_access_states: dict[str, str]
    grant_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source_event_id": self.source_event_id,
            "record_access_state": self.record_access_state,
            "integrity_state": self.integrity_state,
            "retention_state": {
                "retention_class": self.retention_class,
                "access_until_or_null": self.access_until,
                "purge_due_at_or_null": self.purge_due_at,
                "locality": self.locality,
            },
            "part_access_states": dict(self.part_access_states),
            "active_holds": [],
            "grant_ids": list(self.grant_ids),
            "sensitive_part_ids": [],
            "purge_tombstone_id_or_null": None,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class EvidenceGovernanceEvent:
    schema: str
    governance_event_id: str
    source_event_id: str
    evidence_space_id: str
    governance_revision: int
    operation: str
    operation_payload: dict[str, object]
    operation_idempotency_key: str
    authority_principal_ref: PrincipalRef
    authority_scope: AuthorityScope
    policy_snapshot_ref: PolicySnapshotRef
    recorded_at: str
    effective_at: str
    resulting_governance_state_digest: str
    authority_change_set_ref: AuthorityChangeSetRef

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "governance_event_id": self.governance_event_id,
            "source_event_id": self.source_event_id,
            "evidence_space_id": self.evidence_space_id,
            "governance_revision": self.governance_revision,
            "expected_previous_governance_revision_or_null": None,
            "expected_metadata_revision": 0,
            "expected_validation_bundle_revision": 1,
            "operation": self.operation,
            "operation_payload": self.operation_payload,
            "operation_idempotency_key": self.operation_idempotency_key,
            "authority_principal_ref": self.authority_principal_ref.to_dict(),
            "authority_scope": self.authority_scope.to_dict(),
            "policy_snapshot_ref": self.policy_snapshot_ref.to_dict(),
            "recorded_at": self.recorded_at,
            "effective_at": self.effective_at,
            "resulting_governance_state_digest": self.resulting_governance_state_digest,
            "authority_change_set_ref": self.authority_change_set_ref.to_dict(),
        }


def initialize_admitted_governance(
    *,
    governance_event_id: str,
    source_event_id: str,
    evidence_space_id: str,
    part_ids: tuple[str, ...],
    grants: tuple[AccessGrant, ...],
    access_until: str,
    purge_due_at: str,
    authority_change_set_ref: AuthorityChangeSetRef,
    recorded_at: str,
    operation_idempotency_key: str,
) -> tuple[EvidenceGovernanceState, EvidenceGovernanceEvent]:
    state = EvidenceGovernanceState(
        schema="relaylm.evidence_governance_state.v1",
        source_event_id=source_event_id,
        record_access_state="available",
        integrity_state="verified",
        retention_class="bounded",
        access_until=access_until,
        purge_due_at=purge_due_at,
        locality="device_local",
        part_access_states={part_id: "protected_available" for part_id in part_ids},
        grant_ids=tuple(grant.grant_id for grant in grants),
    )
    authority_principal_ref, authority_scope = build_runtime_authority(
        scope_kind="evidence_operator",
        allowed_operations=("initialize_admitted",),
        evidence_space_id=evidence_space_id,
        issued_at=recorded_at,
    )
    event = EvidenceGovernanceEvent(
        schema=GOVERNANCE_EVENT_SCHEMA,
        governance_event_id=governance_event_id,
        source_event_id=source_event_id,
        evidence_space_id=evidence_space_id,
        governance_revision=1,
        operation="initialize_admitted",
        operation_payload={
            "integrity_state": "verified",
            "retention_state": {
                "retention_class": "bounded",
                "access_until_or_null": access_until,
                "purge_due_at_or_null": purge_due_at,
                "review_due_at_or_null": None,
                "review_policy_ref_or_null": None,
                "locality": "device_local",
            },
            "initial_part_access_states": dict(state.part_access_states),
            "initial_access_grants": [grant.to_dict() for grant in grants],
            "active_holds": [],
        },
        operation_idempotency_key=operation_idempotency_key,
        authority_principal_ref=authority_principal_ref,
        authority_scope=authority_scope,
        policy_snapshot_ref=ev1_policy_snapshot_ref(),
        recorded_at=recorded_at,
        effective_at=recorded_at,
        resulting_governance_state_digest=state.digest(),
        authority_change_set_ref=authority_change_set_ref,
    )
    return state, event


__all__ = [
    "ACCESS_GRANT_SCHEMA",
    "GOVERNANCE_EVENT_SCHEMA",
    "GRANT_PURPOSES",
    "AccessGrant",
    "EvidenceGovernanceEvent",
    "EvidenceGovernanceState",
    "build_least_privilege_grant",
    "initialize_admitted_governance",
]
