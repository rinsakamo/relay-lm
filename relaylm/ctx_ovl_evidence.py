"""OVL-1 exact EV-1 authorization and protected-payload resolution."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from relaylm.ctx_ovl_types import _AuthorizedCandidate
from relaylm.evidence.access import resolve_evidence_access_authorization
from relaylm.evidence.common import (
    PolicySnapshotRef,
    PrincipalRef,
    canonical_digest,
    dedupe,
    utf8_text_digest,
)
from relaylm.evidence.governance import AccessGrant, EvidenceGovernanceState
from relaylm.evidence.space import EvidenceSpaceDescriptor, _authority_scope_from_dict
from relaylm.evidence.store import EvidenceStoreTransaction


def _read_authorized_candidate(
    tx: EvidenceStoreTransaction,
    *,
    event: dict,
    descriptor: EvidenceSpaceDescriptor,
    session_id: str,
    evaluated_at: datetime,
) -> tuple[_AuthorizedCandidate | None, tuple[str, ...]]:
    reasons: list[str] = []
    if event.get("projection_event_kind") != "authority_change":
        return None, ("ctx_ovl_change_projection_kind_invalid",)
    if event.get("change_kind_or_null") != "source_admitted":
        return None, ("ctx_ovl_change_kind_unsupported_in_ovl1",)
    source_refs = event.get("authorized_source_event_refs")
    if not isinstance(source_refs, list) or len(source_refs) != 1:
        return None, ("ctx_ovl_source_event_ref_cardinality_invalid",)
    source_event_id = source_refs[0]
    if not isinstance(source_event_id, str) or not source_event_id:
        return None, ("ctx_ovl_source_event_ref_invalid",)
    source = tx.read_record(record_kind="source_event", record_id=source_event_id)
    if source is None:
        return None, ("ctx_ovl_source_event_unresolved",)
    if source.get("schema") != "relaylm.source_event.v1":
        reasons.append("ctx_ovl_source_event_schema_invalid")
    if source.get("source_event_id") != source_event_id:
        reasons.append("ctx_ovl_source_event_identity_mismatch")
    if source.get("evidence_space_id") != descriptor.evidence_space_id:
        reasons.append("ctx_ovl_source_event_space_mismatch")
    if source.get("origin_kind") != "participant":
        reasons.append("ctx_ovl_non_participant_source_unsupported_in_ovl1")
    if source.get("source_role") != "user_input":
        reasons.append("ctx_ovl_source_role_unsupported_in_ovl1")
    if source.get("speaker_identity_status") != "verified":
        reasons.append("ctx_ovl_participant_identity_unresolved")
    if source.get("conversation_ref_or_null") != session_id:
        reasons.append("ctx_ovl_source_event_session_mismatch")
    participant = descriptor.controller_principal_ref.to_dict()
    if source.get("producer_principal_ref") != participant:
        reasons.append("ctx_ovl_source_producer_participant_mismatch")
    if source.get("represented_speaker_ref_or_null") != participant:
        reasons.append("ctx_ovl_source_represented_speaker_mismatch")
    audience = source.get("configured_occurrence_audience")
    if not isinstance(audience, dict):
        reasons.append("ctx_ovl_source_audience_invalid")
    elif (
        audience.get("audience_class") != "private_direct"
        or audience.get("participant_refs") != [participant]
        or audience.get("room_ref_or_null") is not None
        or audience.get("shared_scene_ref_or_null") is not None
        or audience.get("trust") != "trusted_route"
    ):
        reasons.append("ctx_ovl_source_audience_not_exact_private_direct")

    manifest = source.get("canonical_source_manifest")
    if not isinstance(manifest, dict):
        reasons.append("ctx_ovl_source_manifest_invalid")
    elif canonical_digest(manifest) != source.get("canonical_source_manifest_digest"):
        reasons.append("ctx_ovl_source_manifest_digest_mismatch")

    refs = event.get("authoritative_mutation_refs")
    if not isinstance(refs, list):
        reasons.append("ctx_ovl_authoritative_mutation_refs_invalid")
        refs = []
    admission_id = _single_ref(refs, "admission_decision")
    governance_id = _single_ref(refs, "governance_event")
    if admission_id is None:
        reasons.append("ctx_ovl_admission_decision_ref_missing")
    if governance_id is None:
        reasons.append("ctx_ovl_governance_event_ref_missing")
    if reasons:
        return None, dedupe(reasons)
    assert admission_id is not None and governance_id is not None

    admission = tx.read_record(
        record_kind="admission_decision", record_id=admission_id
    )
    governance_event = tx.read_record(
        record_kind="governance_event", record_id=governance_id
    )
    if admission is None or governance_event is None:
        return None, ("ctx_ovl_authority_record_unresolved",)
    authority_reasons = _validate_authority_records(
        source=source,
        admission=admission,
        admission_id=admission_id,
        governance_event=governance_event,
        governance_id=governance_id,
        source_event_id=source_event_id,
        evidence_space_id=descriptor.evidence_space_id,
    )
    if authority_reasons:
        return None, authority_reasons

    validation_id = admission.get("validation_bundle_id_or_null")
    if not isinstance(validation_id, str) or not validation_id:
        return None, ("ctx_ovl_validation_bundle_ref_missing",)
    validation = tx.read_record(
        record_kind="validation_bundle", record_id=validation_id
    )
    if validation is None:
        return None, ("ctx_ovl_validation_bundle_unresolved",)
    validation_reasons = _validate_validation_bundle(
        validation=validation,
        validation_id=validation_id,
        admission=admission,
        source=source,
        source_event_id=source_event_id,
    )
    if validation_reasons:
        return None, validation_reasons

    grant_payloads = governance_event.get("operation_payload", {}).get(
        "initial_access_grants"
    )
    if not isinstance(grant_payloads, list):
        return None, ("ctx_ovl_access_grants_unresolved",)
    grants: list[AccessGrant] = []
    try:
        for payload in grant_payloads:
            grant = _access_grant_from_dict(payload)
            if grant.to_dict() != payload:
                return None, ("ctx_ovl_access_grant_shape_mismatch",)
            persisted = tx.read_record(
                record_kind="access_grant", record_id=grant.grant_id
            )
            if persisted != payload:
                return None, ("ctx_ovl_access_grant_integrity_mismatch",)
            if grant.purpose == "relayctx_evidence_read":
                grants.append(grant)
        governance_state = _governance_state_from_event(governance_event)
    except (KeyError, TypeError, ValueError):
        return None, ("ctx_ovl_authority_record_shape_invalid",)
    if (
        governance_state.digest()
        != governance_event.get("resulting_governance_state_digest")
    ):
        return None, ("ctx_ovl_governance_state_digest_mismatch",)

    parts = manifest.get("parts") if isinstance(manifest, dict) else None
    if not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict):
        return None, ("ctx_ovl_source_manifest_unsupported",)
    part = parts[0]
    part_id = part.get("part_id")
    content_digest = part.get("content_digest_or_null")
    actual_bytes = part.get("byte_length_or_null")
    if (
        part.get("part_kind") != "text"
        or part.get("media_type") != "text/plain"
        or part.get("initial_disposition") != "protected"
        or part.get("part_origin") != "participant_authored"
        or part.get("part_derivation_class") != "direct_occurrence"
        or not isinstance(part_id, str)
        or not isinstance(content_digest, str)
        or type(actual_bytes) is not int
        or actual_bytes < 1
    ):
        return None, ("ctx_ovl_source_part_unsupported",)

    partition_id = event.get("change_partition_id")
    epoch_id = event.get("partition_epoch_id")
    sequence = event.get("partition_sequence")
    if (
        not isinstance(partition_id, str)
        or not isinstance(epoch_id, str)
        or type(sequence) is not int
        or sequence < 0
    ):
        return None, ("ctx_ovl_change_projection_shape_invalid",)
    try:
        policy_snapshot_ref = PolicySnapshotRef(**admission["policy_snapshot_ref"])
    except (KeyError, TypeError, ValueError):
        return None, ("ctx_ovl_policy_snapshot_invalid",)
    projection, access_reasons = resolve_evidence_access_authorization(
        purpose="relayctx_evidence_read",
        origin_kind=str(source.get("origin_kind")),
        source_event_id=source_event_id,
        evidence_space_id=descriptor.evidence_space_id,
        admission_outcome=str(admission.get("outcome")),
        admission_decision_id=admission_id,
        governance_state=governance_state,
        validation_bundle_state=str(validation.get("bundle_state")),
        validation_bundle_revision=int(validation.get("bundle_revision", -1)),
        grants=tuple(grants),
        policy_snapshot_ref=policy_snapshot_ref,
        change_partition_watermark=sequence,
        now=evaluated_at,
        requested_part_ids=(part_id,),
        change_partition_watermarks=((partition_id, epoch_id, sequence),),
    )
    if projection is None:
        return None, tuple(f"ctx_ovl:{reason}" for reason in access_reasons)

    text, payload_reasons = _read_bound_text(
        tx,
        source=source,
        source_event_id=source_event_id,
        evidence_space_id=descriptor.evidence_space_id,
        part_id=part_id,
        content_digest=content_digest,
        actual_bytes=actual_bytes,
    )
    if text is None:
        return None, payload_reasons
    return (
        _AuthorizedCandidate(
            source_event_id=source_event_id,
            source_sequence=sequence,
            text=text,
            content_digest=content_digest,
            actual_bytes=actual_bytes,
            evidence_space_id=descriptor.evidence_space_id,
            change_partition_id=partition_id,
            partition_epoch_id=epoch_id,
            authority_snapshot_digest=projection.authority_snapshot_digest,
            validated_at=projection.issued_at,
            not_after=projection.not_after,
        ),
        (),
    )


def _validate_authority_records(
    *,
    source: dict,
    admission: dict,
    admission_id: str,
    governance_event: dict,
    governance_id: str,
    source_event_id: str,
    evidence_space_id: str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if admission.get("schema") != "relaylm.evidence_admission_decision.v1":
        reasons.append("ctx_ovl_admission_decision_schema_invalid")
    if admission.get("admission_decision_id") != admission_id:
        reasons.append("ctx_ovl_admission_decision_identity_mismatch")
    if admission.get("source_event_id_or_null") != source_event_id:
        reasons.append("ctx_ovl_admission_decision_source_mismatch")
    if admission.get("evidence_space_id") != evidence_space_id:
        reasons.append("ctx_ovl_admission_decision_space_mismatch")
    if admission.get("capture_attempt_id") != source.get("capture_attempt_id"):
        reasons.append("ctx_ovl_admission_capture_attempt_mismatch")
    if admission.get("outcome") != "admitted":
        reasons.append("ctx_ovl_admission_decision_not_admitted")
    if admission.get("canonical_source_manifest_digest_or_null") != source.get(
        "canonical_source_manifest_digest"
    ):
        reasons.append("ctx_ovl_admission_manifest_digest_mismatch")
    if admission.get("initial_governance_event_id_or_null") != governance_id:
        reasons.append("ctx_ovl_admission_governance_ref_mismatch")
    if governance_event.get("schema") != "relaylm.evidence_governance_event.v1":
        reasons.append("ctx_ovl_governance_event_schema_invalid")
    if governance_event.get("governance_event_id") != governance_id:
        reasons.append("ctx_ovl_governance_event_identity_mismatch")
    if governance_event.get("source_event_id") != source_event_id:
        reasons.append("ctx_ovl_governance_event_source_mismatch")
    if governance_event.get("evidence_space_id") != evidence_space_id:
        reasons.append("ctx_ovl_governance_event_space_mismatch")
    if governance_event.get("operation") != "initialize_admitted":
        reasons.append("ctx_ovl_governance_event_operation_invalid")
    if governance_event.get("governance_revision") != 1:
        reasons.append("ctx_ovl_governance_event_revision_invalid")
    if governance_event.get("expected_previous_governance_revision_or_null") is not None:
        reasons.append("ctx_ovl_governance_previous_revision_invalid")
    if governance_event.get("expected_metadata_revision") != 0:
        reasons.append("ctx_ovl_governance_metadata_revision_invalid")
    if governance_event.get("expected_validation_bundle_revision") != admission.get(
        "validation_bundle_revision_or_null"
    ):
        reasons.append("ctx_ovl_governance_validation_revision_mismatch")
    if governance_event.get("policy_snapshot_ref") != admission.get(
        "policy_snapshot_ref"
    ):
        reasons.append("ctx_ovl_authority_policy_snapshot_mismatch")
    return dedupe(reasons)


def _validate_validation_bundle(
    *,
    validation: dict,
    validation_id: str,
    admission: dict,
    source: dict,
    source_event_id: str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if validation.get("schema") != "relaylm.admission_validation_bundle_revision.v1":
        reasons.append("ctx_ovl_validation_bundle_schema_invalid")
    if validation.get("validation_bundle_id") != validation_id:
        reasons.append("ctx_ovl_validation_bundle_identity_mismatch")
    if validation.get("source_event_id_or_null") != source_event_id:
        reasons.append("ctx_ovl_validation_bundle_source_mismatch")
    if validation.get("capture_attempt_id") != source.get("capture_attempt_id"):
        reasons.append("ctx_ovl_validation_capture_attempt_mismatch")
    if validation.get("bundle_revision") != admission.get(
        "validation_bundle_revision_or_null"
    ):
        reasons.append("ctx_ovl_validation_bundle_revision_mismatch")
    if validation.get("bundle_state") != "valid":
        reasons.append("ctx_ovl_validation_bundle_not_valid")
    if validation.get("policy_snapshot_ref") != admission.get("policy_snapshot_ref"):
        reasons.append("ctx_ovl_validation_policy_snapshot_mismatch")
    return dedupe(reasons)


def _single_ref(refs: Sequence[object], record_kind: str) -> str | None:
    matches = [
        item.get("record_id")
        for item in refs
        if isinstance(item, dict) and item.get("record_kind") == record_kind
    ]
    if len(matches) != 1 or not isinstance(matches[0], str):
        return None
    return matches[0]


def _access_grant_from_dict(payload: object) -> AccessGrant:
    if not isinstance(payload, dict):
        raise TypeError("grant")
    basis = payload["grant_basis"]
    grantee = payload["grantee"]
    return AccessGrant(
        schema=str(payload["schema"]),
        grant_id=str(payload["grant_id"]),
        source_event_id=str(payload["source_event_id"]),
        evidence_space_id=str(payload["evidence_space_id"]),
        purpose=str(payload["purpose"]),
        grantee_service_class=str(grantee["service_class"]),
        part_selector=str(payload["part_selector"]["kind"]),
        metadata_projection_selectors=tuple(payload["metadata_projection_selectors"]),
        subject_selector=str(payload["subject_selector"]["kind"]),
        audience_use_constraint=str(payload["audience_use_constraint"]["kind"]),
        locality_constraint=str(payload["locality_constraint"]),
        destination_class_constraint=str(payload["destination_class_constraint"]),
        policy_snapshot_ref=PolicySnapshotRef(**basis["policy_snapshot_ref"]),
        admission_decision_id=str(basis["admission_decision_id"]),
        governance_revision=int(basis["governance_revision"]),
        metadata_revision=int(basis["metadata_revision"]),
        validation_bundle_revision=int(basis["validation_bundle_revision"]),
        issued_by_principal_ref=PrincipalRef(**payload["issued_by_principal_ref"]),
        issued_by_authority_scope=_authority_scope_from_dict(
            payload["issued_by_authority_scope"]
        ),
        issued_at=str(payload["issued_at"]),
        expires_at_or_null=payload["expires_at_or_null"],
    )


def _governance_state_from_event(payload: dict) -> EvidenceGovernanceState:
    operation = payload["operation_payload"]
    retention = operation["retention_state"]
    grants = operation["initial_access_grants"]
    return EvidenceGovernanceState(
        schema="relaylm.evidence_governance_state.v1",
        source_event_id=str(payload["source_event_id"]),
        record_access_state="available",
        integrity_state=str(operation["integrity_state"]),
        retention_class=str(retention["retention_class"]),
        access_until=str(retention["access_until_or_null"]),
        purge_due_at=str(retention["purge_due_at_or_null"]),
        locality=str(retention["locality"]),
        part_access_states={
            str(key): str(value)
            for key, value in operation["initial_part_access_states"].items()
        },
        grant_ids=tuple(str(item["grant_id"]) for item in grants),
    )


def _read_bound_text(
    tx: EvidenceStoreTransaction,
    *,
    source: dict,
    source_event_id: str,
    evidence_space_id: str,
    part_id: str,
    content_digest: str,
    actual_bytes: int,
) -> tuple[str | None, tuple[str, ...]]:
    attestation_ids = source.get("protected_payload_binding_attestation_ids")
    if not isinstance(attestation_ids, list) or len(attestation_ids) != 1:
        return None, ("ctx_ovl_payload_binding_cardinality_invalid",)
    attestation_id = attestation_ids[0]
    if not isinstance(attestation_id, str):
        return None, ("ctx_ovl_payload_binding_ref_invalid",)
    attestation = tx.read_record(
        record_kind="payload_binding_attestation", record_id=attestation_id
    )
    if attestation is None:
        return None, ("ctx_ovl_payload_binding_unresolved",)
    authority_scope = attestation.get("attester_authority_scope")
    resource_scope = (
        authority_scope.get("resource_scope")
        if isinstance(authority_scope, dict)
        else None
    )
    if (
        attestation.get("schema")
        != "relaylm.protected_payload_binding_attestation.v1"
        or attestation.get("payload_binding_attestation_id") != attestation_id
        or attestation.get("source_event_id") != source_event_id
        or attestation.get("part_id") != part_id
        or attestation.get("content_digest") != content_digest
        or attestation.get("storage_binding_schema")
        != "relaylm.evidence_store_binding.v1"
        or attestation.get("storage_authority_ref")
        != "relaylm.ev1.device_local_store"
        or not isinstance(authority_scope, dict)
        or authority_scope.get("scope_kind") != "evidence_operator"
        or "storage_binding_attest"
        not in authority_scope.get("allowed_operations", [])
        or not isinstance(resource_scope, dict)
        or resource_scope.get("evidence_space_id") != evidence_space_id
        or resource_scope.get("whole_evidence_space") is not True
    ):
        return None, ("ctx_ovl_payload_binding_mismatch",)
    storage_ref = attestation.get("storage_binding_ref")
    if not isinstance(storage_ref, str) or not storage_ref:
        return None, ("ctx_ovl_payload_storage_ref_invalid",)
    payload = tx.read_payload(payload_id=storage_ref)
    if payload is None:
        return None, ("ctx_ovl_protected_payload_unresolved",)
    text = payload.get("text")
    if not isinstance(text, str) or not text:
        return None, ("ctx_ovl_protected_payload_text_invalid",)
    if payload.get("content_digest") != content_digest:
        return None, ("ctx_ovl_protected_payload_digest_mismatch",)
    if utf8_text_digest(text) != content_digest:
        return None, ("ctx_ovl_protected_payload_integrity_mismatch",)
    if len(text.encode("utf-8")) != actual_bytes:
        return None, ("ctx_ovl_protected_payload_byte_count_mismatch",)
    return text, ()


__all__ = ["_read_authorized_candidate"]
