"""Contract 1B fail-closed EvidenceAccessAuthorizationProjection resolver."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from relaylm.evidence_common import (
    PolicySnapshotRef,
    canonical_digest,
    dedupe,
    new_opaque_id,
)
from relaylm.evidence_governance import AccessGrant, EvidenceGovernanceState

AUTHORIZATION_SCHEMA = "relaylm.evidence_access_authorization_projection.v1"
_GATE_KIND_BY_PURPOSE = {
    "relayctx_evidence_read": "relayctx_evidence",
    "shared_assessment_read": "shared_assessment",
    "relayref_observation_read": "relayref_observation",
}
_SERVICE_CLASS_BY_PURPOSE = {
    "relayctx_evidence_read": "relayctx_service",
    "shared_assessment_read": "shared_assessment_service",
    "relayref_observation_read": "relayref_service",
}
_ASSISTANT_ONLY_PURPOSES = frozenset({"relayref_observation_read"})


@dataclass(frozen=True)
class EvidenceAccessAuthorizationProjection:
    schema: str
    access_authorization_id: str
    source_event_id: str
    evidence_space_id: str
    gate_kind: str
    purpose: str
    grantee_service_class: str
    selected_part_ids: tuple[str, ...]
    metadata_projection_selectors: tuple[str, ...]
    matched_grant_ids: tuple[str, ...]
    admission_decision_id: str
    governance_revision: int
    metadata_revision: int
    validation_bundle_revision_or_null: int | None
    policy_snapshot_ref: PolicySnapshotRef
    authority_snapshot_digest: str
    change_partition_watermarks: tuple[tuple[str, str, int], ...]
    issued_at: str
    not_after: str
    subject_selector_digest: str
    audience_constraint_digest: str
    destination_class_constraint: str = "no_external_destination"
    emergency_authorization_ref_or_null: str | None = None

    @property
    def change_partition_watermark(self) -> int:
        return self.change_partition_watermarks[0][2]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "access_authorization_id": self.access_authorization_id,
            "source_event_id": self.source_event_id,
            "evidence_space_id": self.evidence_space_id,
            "gate_kind": self.gate_kind,
            "purpose": self.purpose,
            "grantee": {
                "kind": "service_class",
                "service_class": self.grantee_service_class,
            },
            "selected_part_ids": list(self.selected_part_ids),
            "metadata_projection_selectors": list(
                self.metadata_projection_selectors
            ),
            "matched_grant_ids": list(self.matched_grant_ids),
            "subject_selector_digest": self.subject_selector_digest,
            "audience_constraint_digest": self.audience_constraint_digest,
            "destination_class_constraint": self.destination_class_constraint,
            "admission_decision_id": self.admission_decision_id,
            "governance_revision": self.governance_revision,
            "metadata_revision": self.metadata_revision,
            "validation_bundle_revision_or_null": (
                self.validation_bundle_revision_or_null
            ),
            "policy_snapshot_ref": self.policy_snapshot_ref.to_dict(),
            "authority_snapshot_digest": self.authority_snapshot_digest,
            "change_partition_watermarks": [
                {
                    "change_partition_id": partition_id,
                    "partition_epoch_id": epoch_id,
                    "highest_observed_partition_sequence": sequence,
                }
                for partition_id, epoch_id, sequence in self.change_partition_watermarks
            ],
            "emergency_authorization_ref_or_null": (
                self.emergency_authorization_ref_or_null
            ),
            "issued_at": self.issued_at,
            "not_after": self.not_after,
        }


def resolve_evidence_access_authorization(
    *,
    purpose: str,
    origin_kind: str,
    source_event_id: str,
    evidence_space_id: str,
    admission_outcome: str,
    admission_decision_id: str,
    governance_state: EvidenceGovernanceState,
    validation_bundle_state: str,
    validation_bundle_revision: int,
    grants: tuple[AccessGrant, ...],
    policy_snapshot_ref: PolicySnapshotRef,
    change_partition_watermark: int,
    now: datetime | None = None,
    grant_not_after_seconds: int = 300,
    requested_grantee_service_class: str | None = None,
    requested_part_ids: tuple[str, ...] | None = None,
    requested_metadata_projection_selectors: tuple[str, ...] = (
        "source_identity_basic",
    ),
    expected_governance_revision: int = 1,
    expected_metadata_revision: int = 0,
    change_partition_watermarks: tuple[tuple[str, str, int], ...] | None = None,
) -> tuple[EvidenceAccessAuthorizationProjection | None, tuple[str, ...]]:
    """Resolve one exact short-lived authorization; every mismatch denies."""

    reasons: list[str] = []
    expected_service = _SERVICE_CLASS_BY_PURPOSE.get(purpose)
    requested_service = requested_grantee_service_class or expected_service
    if purpose not in _GATE_KIND_BY_PURPOSE or expected_service is None:
        reasons.append("evidence_access_purpose_unsupported_in_ev1")
    if requested_service != expected_service:
        reasons.append("evidence_access_grantee_service_mismatch")
    if purpose in _ASSISTANT_ONLY_PURPOSES and origin_kind != "assistant":
        reasons.append("evidence_access_purpose_requires_assistant_origin")
    if admission_outcome != "admitted":
        reasons.append("evidence_access_source_not_admitted")
    if governance_state.source_event_id != source_event_id:
        reasons.append("evidence_access_governance_source_mismatch")
    if governance_state.record_access_state != "available":
        reasons.append("evidence_access_record_not_available")
    if governance_state.integrity_state != "verified":
        reasons.append("evidence_access_integrity_not_verified")
    if validation_bundle_state != "valid":
        reasons.append("evidence_access_validation_bundle_invalid")
    if expected_governance_revision != 1 or expected_metadata_revision != 0:
        reasons.append("evidence_access_revision_unsupported_or_stale")

    current_time = now or datetime.now(timezone.utc)
    access_until = _parse(governance_state.access_until)
    purge_due_at = _parse(governance_state.purge_due_at)
    if access_until is None or purge_due_at is None:
        reasons.append("evidence_access_deadline_invalid")
    else:
        if current_time >= access_until:
            reasons.append("evidence_access_deadline_expired")
        if access_until > purge_due_at:
            reasons.append("evidence_access_retention_invalid")

    available_parts = tuple(
        sorted(
            part_id
            for part_id, state in governance_state.part_access_states.items()
            if state == "protected_available"
        )
    )
    selected_source = available_parts if requested_part_ids is None else requested_part_ids
    selected_parts = tuple(sorted(selected_source))
    if not selected_parts:
        reasons.append("evidence_access_no_available_parts")
    elif any(part not in available_parts for part in selected_parts):
        reasons.append("evidence_access_part_not_available")

    selectors = tuple(sorted(set(requested_metadata_projection_selectors)))
    if not selectors or selectors != requested_metadata_projection_selectors:
        reasons.append("evidence_access_metadata_selectors_invalid")

    matched: list[AccessGrant] = []
    for grant in grants:
        if grant.purpose != purpose:
            continue
        if (
            grant.source_event_id != source_event_id
            or grant.evidence_space_id != evidence_space_id
        ):
            continue
        if grant.grantee_service_class != requested_service:
            continue
        if grant.admission_decision_id != admission_decision_id:
            continue
        if grant.governance_revision != expected_governance_revision:
            continue
        if grant.metadata_revision != expected_metadata_revision:
            continue
        if grant.validation_bundle_revision != validation_bundle_revision:
            continue
        if grant.policy_snapshot_ref != policy_snapshot_ref:
            continue
        if grant.part_selector != "all_currently_available_parts":
            continue
        if tuple(grant.metadata_projection_selectors) != selectors:
            continue
        if grant.subject_selector != "producer":
            continue
        if grant.audience_use_constraint != "exact_occurrence_audience":
            continue
        if grant.locality_constraint != "device_local_only":
            continue
        if grant.destination_class_constraint != "no_external_destination":
            continue
        grant_expiry = (
            _parse(grant.expires_at_or_null)
            if grant.expires_at_or_null
            else None
        )
        if grant.expires_at_or_null is not None and grant_expiry is None:
            continue
        if grant_expiry is not None and current_time >= grant_expiry:
            continue
        matched.append(grant)
    if not matched:
        reasons.append("evidence_access_no_matching_active_grant")

    watermarks = change_partition_watermarks or (
        ("evidence_control", "ev1", change_partition_watermark),
    )
    normalized_watermarks = tuple(
        sorted(watermarks, key=lambda item: (item[0], item[1]))
    )
    if len({(item[0], item[1]) for item in normalized_watermarks}) != len(
        normalized_watermarks
    ):
        reasons.append("evidence_access_duplicate_partition_watermark")
    if any(type(item[2]) is not int or item[2] < 0 for item in normalized_watermarks):
        reasons.append("evidence_access_partition_watermark_invalid")

    reasons = list(dedupe(reasons))
    if reasons:
        return None, tuple(reasons)

    issued_at = current_time.isoformat()
    not_after_candidates = [current_time.timestamp() + grant_not_after_seconds]
    assert access_until is not None
    not_after_candidates.append(access_until.timestamp())
    for grant in matched:
        if grant.expires_at_or_null:
            parsed = _parse(grant.expires_at_or_null)
            assert parsed is not None
            not_after_candidates.append(parsed.timestamp())
    not_after = datetime.fromtimestamp(
        min(not_after_candidates), tz=timezone.utc
    ).isoformat()
    authority_snapshot = {
        "source_event_id": source_event_id,
        "evidence_space_id": evidence_space_id,
        "admission_outcome": admission_outcome,
        "admission_decision_id": admission_decision_id,
        "governance_digest": governance_state.digest(),
        "governance_revision": expected_governance_revision,
        "metadata_revision": expected_metadata_revision,
        "validation_bundle_state": validation_bundle_state,
        "validation_bundle_revision": validation_bundle_revision,
        "policy_snapshot_ref": policy_snapshot_ref.to_dict(),
        "grantee_service_class": requested_service,
        "selected_part_ids": selected_parts,
        "metadata_projection_selectors": selectors,
        "change_partition_watermarks": normalized_watermarks,
    }
    return (
        EvidenceAccessAuthorizationProjection(
            schema=AUTHORIZATION_SCHEMA,
            access_authorization_id=new_opaque_id("accessauth"),
            source_event_id=source_event_id,
            evidence_space_id=evidence_space_id,
            gate_kind=_GATE_KIND_BY_PURPOSE[purpose],
            purpose=purpose,
            grantee_service_class=requested_service,
            selected_part_ids=selected_parts,
            metadata_projection_selectors=selectors,
            matched_grant_ids=tuple(sorted(grant.grant_id for grant in matched)),
            admission_decision_id=admission_decision_id,
            governance_revision=expected_governance_revision,
            metadata_revision=expected_metadata_revision,
            validation_bundle_revision_or_null=validation_bundle_revision,
            policy_snapshot_ref=policy_snapshot_ref,
            authority_snapshot_digest=canonical_digest(authority_snapshot),
            change_partition_watermarks=normalized_watermarks,
            issued_at=issued_at,
            not_after=not_after,
            subject_selector_digest=canonical_digest({"kind": "producer"}),
            audience_constraint_digest=canonical_digest(
                {"kind": "exact_occurrence_audience"}
            ),
        ),
        (),
    )


def _parse(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


__all__ = [
    "AUTHORIZATION_SCHEMA",
    "EvidenceAccessAuthorizationProjection",
    "resolve_evidence_access_authorization",
]
