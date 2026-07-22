"""OVL-1 exact EV-1 authorization and protected-payload resolution."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from relaylm.ctx_ovl_types import _AuthorizedCandidate
from relaylm.evidence_access import resolve_evidence_access_authorization
from relaylm.evidence_common import (
    PolicySnapshotRef, PrincipalRef, dedupe, utf8_text_digest,
)
from relaylm.evidence_governance import AccessGrant, EvidenceGovernanceState
from relaylm.evidence_space import EvidenceSpaceDescriptor, _authority_scope_from_dict
from relaylm.evidence_store import EvidenceStoreTransaction


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
    if source.get("speaker_identity_status") != "verified":
        reasons.append("ctx_ovl_participant_identity_unresolved")
    if source.get("conversation_ref_or_null") != session_id:
        reasons.append("ctx_ovl_source_event_session_mismatch")

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
    validation_id = admission.get("validation_bundle_id_or_null")
    if not isinstance(validation_id, str) or not validation_id:
        return None, ("ctx_ovl_validation_bundle_ref_missing",)
    validation = tx.read_record(
        record_kind="validation_bundle", record_id=validation_id
    )
    if validation is None:
        return None, ("ctx_ovl_validation_bundle_unresolved",)

    grant_payloads = governance_event.get("operation_payload", {}).get(
        "initial_access_grants"
    )
    if not isinstance(grant_payloads, list):
        return None, ("ctx_ovl_access_grants_unresolved",)
    grants: list[AccessGrant] = []
    try:
        for payload in grant_payloads:
            grant = _access_grant_from_dict(payload)
            if grant.purpose == "relayctx_evidence_read":
                persisted = tx.read_record(
                    record_kind="access_grant", record_id=grant.grant_id
                )
                if persisted != payload:
                    return None, ("ctx_ovl_access_grant_integrity_mismatch",)
                grants.append(grant)
        governance_state = _governance_state_from_event(governance_event)
    except (KeyError, TypeError, ValueError):
        return None, ("ctx_ovl_authority_record_shape_invalid",)

    manifest = source.get("canonical_source_manifest")
    parts = manifest.get("parts") if isinstance(manifest, dict) else None
    if not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict):
        return None, ("ctx_ovl_source_manifest_unsupported",)
    part = parts[0]
    part_id = part.get("part_id")
    content_digest = part.get("content_digest_or_null")
    actual_bytes = part.get("byte_length_or_null")
    if (
        part.get("part_kind") != "text"
        or part.get("initial_disposition") != "protected"
        or part.get("part_origin") != "participant_authored"
        or not isinstance(part_id, str)
        or not isinstance(content_digest, str)
        or type(actual_bytes) is not int
        or actual_bytes < 1
    ):
        return None, ("ctx_ovl_source_part_unsupported",)

    partition_id = str(event["change_partition_id"])
    epoch_id = str(event["partition_epoch_id"])
    sequence = int(event["partition_sequence"])
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
        policy_snapshot_ref=PolicySnapshotRef(**admission["policy_snapshot_ref"]),
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
    if (
        attestation.get("source_event_id") != source_event_id
        or attestation.get("part_id") != part_id
        or attestation.get("content_digest") != content_digest
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
