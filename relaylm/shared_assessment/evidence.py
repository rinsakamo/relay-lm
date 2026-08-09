"""ASM-1 exact EV-1 Evidence authorization and Assessment Pass inputs.

This module is the read/validation side of ASM-1. It resolves the EV-1
``shared_assessment_read`` grant, validates protected text and provenance, and
returns character-independent source inputs. It owns no Shared Assessment
current-state or Subjective MEM write authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from relaylm.evidence.access import resolve_evidence_access_authorization
from relaylm.evidence.common import (
    PolicySnapshotRef,
    build_runtime_authority,
    canonical_digest,
    ev1_policy_snapshot_ref,
    utf8_text_digest,
)
from relaylm.evidence.governance import AccessGrant, EvidenceGovernanceState
from relaylm.evidence.store import EvidenceStoreTransaction
from relaylm.shared_assessment.models import (
    SharedAssessmentAuthorizationSnapshot,
    SharedAssessmentEvidenceRef,
    SharedAssessmentPassBundle,
    SharedAssessmentPassPart,
)

@dataclass(frozen=True)
class AuthorizedSharedAssessmentSource:
    evidence_ref: SharedAssessmentEvidenceRef
    parts: tuple[SharedAssessmentPassPart, ...]
    authorization_snapshot: SharedAssessmentAuthorizationSnapshot

def load_authorized_shared_assessment_sources(
    *,
    tx: EvidenceStoreTransaction,
    evidence_space_id: str,
    source_event_ids: tuple[str, ...],
    now: datetime,
) -> tuple[tuple[AuthorizedSharedAssessmentSource, ...] | None, tuple[str, ...]]:
    authorized: list[AuthorizedSharedAssessmentSource] = []
    reasons: list[str] = []
    for source_event_id in source_event_ids:
        item, item_reasons = _load_authorized_shared_assessment_source(
            tx=tx,
            evidence_space_id=evidence_space_id,
            source_event_id=source_event_id,
            now=now,
        )
        if item is None:
            reasons.extend(item_reasons)
        else:
            authorized.append(item)
    if reasons:
        return None, tuple(dict.fromkeys(reasons))
    return tuple(authorized), ()


def _load_authorized_shared_assessment_source(
    *,
    tx: EvidenceStoreTransaction,
    evidence_space_id: str,
    source_event_id: str,
    now: datetime,
) -> tuple[AuthorizedSharedAssessmentSource | None, tuple[str, ...]]:
    source = tx.read_record(record_kind="source_event", record_id=source_event_id)
    if source is None or source.get("schema") != "relaylm.source_event.v1":
        return None, ("shared_assessment_source_event_missing_or_invalid",)
    if source.get("source_event_id") != source_event_id or source.get("evidence_space_id") != evidence_space_id:
        return None, ("shared_assessment_source_event_scope_mismatch",)
    origin = _normalize_origin(source.get("origin_kind"))
    if origin is None:
        return None, ("shared_assessment_source_origin_unsupported",)
    provenance = source.get("provenance_snapshot")
    source_material_classes = (
        provenance.get("source_material_classes")
        if isinstance(provenance, dict)
        else None
    )
    if not isinstance(source_material_classes, list):
        return None, ("shared_assessment_source_provenance_invalid",)
    if "product_knowledge_derived" in source_material_classes:
        return None, ("shared_assessment_product_knowledge_forbidden",)
    manifest = source.get("canonical_source_manifest")
    manifest_digest = source.get("canonical_source_manifest_digest")
    if (
        not isinstance(manifest, dict)
        or not isinstance(manifest_digest, str)
        or canonical_digest(manifest) != manifest_digest
    ):
        return None, ("shared_assessment_source_manifest_invalid",)
    semantic_reasons = _validate_source_semantics(
        source=source, manifest=manifest, normalized_origin=origin
    )
    if semantic_reasons:
        return None, semantic_reasons

    capture_attempt_id = source.get("capture_attempt_id")
    if not isinstance(capture_attempt_id, str):
        return None, ("shared_assessment_capture_attempt_invalid",)
    attempt_log = tx.read_log(log_kind="capture_attempt", key=capture_attempt_id)
    admission_id = _admission_id_from_attempt(attempt_log)
    if admission_id is None:
        return None, ("shared_assessment_admission_binding_missing",)
    admission = tx.read_record(
        record_kind="admission_decision", record_id=admission_id
    )
    if (
        admission is None
        or admission.get("outcome") != "admitted"
        or admission.get("source_event_id_or_null") != source_event_id
        or admission.get("evidence_space_id") != evidence_space_id
        or admission.get("capture_attempt_id") != capture_attempt_id
    ):
        return None, ("shared_assessment_source_not_admitted",)
    if admission.get("canonical_source_manifest_digest_or_null") != manifest_digest:
        return None, ("shared_assessment_source_admission_manifest_mismatch",)
    validation_id = admission.get("validation_bundle_id_or_null")
    validation_revision = admission.get("validation_bundle_revision_or_null")
    if not isinstance(validation_id, str) or type(validation_revision) is not int:
        return None, ("shared_assessment_validation_bundle_reference_invalid",)
    validation = tx.read_record(
        record_kind="validation_bundle", record_id=validation_id
    )
    if (
        validation is None
        or validation.get("bundle_state") != "valid"
        or validation.get("bundle_revision") != validation_revision
        or validation.get("source_event_id_or_null") != source_event_id
        or validation.get("capture_attempt_id") != capture_attempt_id
    ):
        return None, ("shared_assessment_validation_bundle_invalid",)
    artifact_reasons = _validate_validation_artifacts(
        tx=tx,
        source=source,
        manifest=manifest,
        validation=validation,
        source_event_id=source_event_id,
        evidence_space_id=evidence_space_id,
        manifest_digest=manifest_digest,
        normalized_origin=origin,
    )
    if artifact_reasons:
        return None, artifact_reasons
    governance_event_id = admission.get("initial_governance_event_id_or_null")
    if not isinstance(governance_event_id, str):
        return None, ("shared_assessment_governance_reference_invalid",)
    governance = tx.read_record(
        record_kind="governance_event", record_id=governance_event_id
    )
    state, grants, governance_revision, governance_reasons = _parse_governance(
        tx=tx,
        raw=governance,
        source_event_id=source_event_id,
        evidence_space_id=evidence_space_id,
        admission_id=admission_id,
        validation_revision=validation_revision,
    )
    if state is None:
        return None, governance_reasons
    not_before, timing_reasons = _authority_not_before(
        source=source,
        admission=admission,
        validation=validation,
        governance=governance,
        grants=grants,
        now=now,
    )
    if not_before is None:
        return None, timing_reasons
    part_ids = _manifest_protected_text_part_ids(manifest)
    if not part_ids:
        return None, ("shared_assessment_no_supported_text_parts",)
    capture_sequence = source.get("capture_sequence")
    if type(capture_sequence) is not int or capture_sequence < 0:
        return None, ("shared_assessment_capture_sequence_invalid",)
    projection, projection_reasons = resolve_evidence_access_authorization(
        purpose="shared_assessment_read",
        origin_kind=str(source.get("origin_kind")),
        source_event_id=source_event_id,
        evidence_space_id=evidence_space_id,
        admission_outcome="admitted",
        admission_decision_id=admission_id,
        governance_state=state,
        validation_bundle_state="valid",
        validation_bundle_revision=validation_revision,
        grants=grants,
        policy_snapshot_ref=ev1_policy_snapshot_ref(),
        change_partition_watermark=capture_sequence,
        now=now,
        requested_part_ids=part_ids,
        requested_metadata_projection_selectors=("source_identity_basic",),
        expected_governance_revision=governance_revision,
        expected_metadata_revision=0,
    )
    if projection is None:
        return None, tuple(
            f"shared_assessment_{reason}" for reason in projection_reasons
        )
    parts, part_reasons = _load_parts(
        tx=tx,
        source=source,
        manifest=manifest,
        selected_part_ids=projection.selected_part_ids,
    )
    if parts is None:
        return None, part_reasons
    evidence_ref = SharedAssessmentEvidenceRef(
        source_event_id=source_event_id,
        evidence_space_id=evidence_space_id,
        authorization_state="current_admitted",
        source_origin=origin,
        lineage_revision=governance_revision,
    )
    snapshot = SharedAssessmentAuthorizationSnapshot(
        source_event_id=source_event_id,
        access_authorization_id=projection.access_authorization_id,
        authority_snapshot_digest=projection.authority_snapshot_digest,
        selected_part_ids=projection.selected_part_ids,
        matched_grant_ids=projection.matched_grant_ids,
        governance_revision=projection.governance_revision,
        validation_bundle_revision=validation_revision,
        not_before=not_before,
        not_after=projection.not_after,
    )
    return AuthorizedSharedAssessmentSource(evidence_ref, parts, snapshot), ()


def _parse_governance(
    *,
    tx: EvidenceStoreTransaction,
    raw: dict | None,
    source_event_id: str,
    evidence_space_id: str,
    admission_id: str,
    validation_revision: int,
) -> tuple[
    EvidenceGovernanceState | None,
    tuple[AccessGrant, ...],
    int,
    tuple[str, ...],
]:
    if (
        raw is None
        or raw.get("schema") != "relaylm.evidence_governance_event.v1"
        or raw.get("operation") != "initialize_admitted"
        or raw.get("source_event_id") != source_event_id
        or raw.get("evidence_space_id") != evidence_space_id
    ):
        return None, (), 0, ("shared_assessment_governance_event_invalid",)
    revision = raw.get("governance_revision")
    payload = raw.get("operation_payload")
    if type(revision) is not int or revision < 1 or not isinstance(payload, dict):
        return None, (), 0, ("shared_assessment_governance_event_invalid",)
    retention = payload.get("retention_state")
    part_states = payload.get("initial_part_access_states")
    raw_grants = payload.get("initial_access_grants")
    if not isinstance(retention, dict) or not isinstance(part_states, dict) or not isinstance(raw_grants, list):
        return None, (), 0, ("shared_assessment_governance_payload_invalid",)
    grants: list[AccessGrant] = []
    for raw_grant in raw_grants:
        grant = _grant_from_dict(
            raw_grant,
            evidence_space_id=evidence_space_id,
            source_event_id=source_event_id,
            admission_id=admission_id,
            validation_revision=validation_revision,
        )
        if grant is None:
            return None, (), 0, ("shared_assessment_access_grant_invalid",)
        canonical_grant = tx.read_record(
            record_kind="access_grant", record_id=grant.grant_id
        )
        if canonical_grant != raw_grant:
            return None, (), 0, ("shared_assessment_access_grant_record_mismatch",)
        grants.append(grant)
    if len({grant.grant_id for grant in grants}) != len(grants):
        return None, (), 0, ("shared_assessment_access_grant_duplicate",)
    state = EvidenceGovernanceState(
        schema="relaylm.evidence_governance_state.v1",
        source_event_id=source_event_id,
        record_access_state="available",
        integrity_state=str(payload.get("integrity_state")),
        retention_class=str(retention.get("retention_class")),
        access_until=str(retention.get("access_until_or_null")),
        purge_due_at=str(retention.get("purge_due_at_or_null")),
        locality=str(retention.get("locality")),
        part_access_states={str(key): str(value) for key, value in part_states.items()},
        grant_ids=tuple(grant.grant_id for grant in grants),
    )
    if raw.get("resulting_governance_state_digest") != state.digest():
        return None, (), 0, ("shared_assessment_governance_state_digest_invalid",)
    return state, tuple(grants), revision, ()


def _grant_from_dict(
    raw: object,
    *,
    evidence_space_id: str,
    source_event_id: str,
    admission_id: str,
    validation_revision: int,
) -> AccessGrant | None:
    if not isinstance(raw, dict) or raw.get("schema") != "relaylm.evidence_access_grant.v1":
        return None
    grantee = raw.get("grantee")
    part_selector = raw.get("part_selector")
    subject_selector = raw.get("subject_selector")
    audience = raw.get("audience_use_constraint")
    basis = raw.get("grant_basis")
    if not all(isinstance(item, dict) for item in (grantee, part_selector, subject_selector, audience, basis)):
        return None
    policy = basis.get("policy_snapshot_ref")
    if not isinstance(policy, dict):
        return None
    expected_policy = ev1_policy_snapshot_ref()
    if policy != expected_policy.to_dict():
        return None
    issued_at = raw.get("issued_at")
    grant_id = raw.get("grant_id")
    selectors = raw.get("metadata_projection_selectors")
    if not isinstance(issued_at, str) or not isinstance(grant_id, str) or not isinstance(selectors, list):
        return None
    integer_fields = (
        basis.get("governance_revision"),
        basis.get("metadata_revision"),
        basis.get("validation_bundle_revision"),
        policy.get("policy_revision"),
    )
    if any(type(value) is not int for value in integer_fields):
        return None
    principal, scope = build_runtime_authority(
        scope_kind="evidence_operator",
        allowed_operations=("grant_access",),
        evidence_space_id=evidence_space_id,
        issued_at=issued_at,
    )
    if (
        raw.get("issued_by_principal_ref") != principal.to_dict()
        or raw.get("issued_by_authority_scope") != scope.to_dict()
    ):
        return None
    grant = AccessGrant(
        schema="relaylm.evidence_access_grant.v1",
        grant_id=grant_id,
        source_event_id=str(raw.get("source_event_id")),
        evidence_space_id=str(raw.get("evidence_space_id")),
        purpose=str(raw.get("purpose")),
        grantee_service_class=str(grantee.get("service_class")),
        part_selector=str(part_selector.get("kind")),
        metadata_projection_selectors=tuple(str(item) for item in selectors),
        subject_selector=str(subject_selector.get("kind")),
        audience_use_constraint=str(audience.get("kind")),
        locality_constraint=str(raw.get("locality_constraint")),
        destination_class_constraint=str(raw.get("destination_class_constraint")),
        policy_snapshot_ref=PolicySnapshotRef(
            policy_id=str(policy.get("policy_id")),
            policy_revision=int(policy.get("policy_revision", 0)),
            policy_digest=str(policy.get("policy_digest")),
        ),
        admission_decision_id=str(basis.get("admission_decision_id")),
        governance_revision=int(basis.get("governance_revision", 0)),
        metadata_revision=int(basis.get("metadata_revision", -1)),
        validation_bundle_revision=int(basis.get("validation_bundle_revision", 0)),
        issued_by_principal_ref=principal,
        issued_by_authority_scope=scope,
        issued_at=issued_at,
        expires_at_or_null=(
            str(raw["expires_at_or_null"])
            if raw.get("expires_at_or_null") is not None
            else None
        ),
    )
    return grant if grant.to_dict() == raw else None



def _validate_source_semantics(
    *, source: dict, manifest: dict, normalized_origin: str
) -> tuple[str, ...]:
    provenance = source.get("provenance_snapshot")
    raw_parts = manifest.get("parts")
    if not isinstance(provenance, dict) or not isinstance(raw_parts, list):
        return ("shared_assessment_source_provenance_invalid",)
    material_classes = provenance.get("source_material_classes")
    if not isinstance(material_classes, list):
        return ("shared_assessment_source_provenance_invalid",)
    if "product_knowledge_derived" in material_classes or any(
        isinstance(part, dict)
        and part.get("part_derivation_class") == "product_knowledge_derived"
        for part in raw_parts
    ):
        return ("shared_assessment_product_knowledge_forbidden",)
    if normalized_origin == "user":
        if (
            source.get("assistant_response_binding_ref_or_null") is not None
            or source.get("source_replay_identity") != {"kind": "none"}
        ):
            return ("shared_assessment_source_provenance_invalid",)
        expected = {
            "source_role": "user_input",
            "occurrence_kind": "message",
            "source_material_classes": ["personal_source"],
            "part_origin": "participant_authored",
            "part_derivation_class": "direct_occurrence",
        }
    else:
        expected = {
            "source_role": "assistant_response",
            "occurrence_kind": "assistant_response",
            "source_material_classes": ["assistant_generation"],
            "part_origin": "assistant_authored",
            "part_derivation_class": "model_generated",
        }
    if (
        source.get("source_role") != expected["source_role"]
        or manifest.get("schema") != "relaylm.canonical_source_manifest.v1"
        or manifest.get("occurrence_kind") != expected["occurrence_kind"]
        or material_classes != expected["source_material_classes"]
        or provenance.get("capture_method") != "managed_runtime"
        or provenance.get("provenance_assurance") != "verified"
    ):
        return ("shared_assessment_source_provenance_invalid",)
    for part in raw_parts:
        if not isinstance(part, dict):
            return ("shared_assessment_source_parts_invalid",)
        if part.get("part_kind") == "text" and part.get("initial_disposition") == "protected":
            if (
                part.get("part_origin") != expected["part_origin"]
                or part.get("part_derivation_class")
                != expected["part_derivation_class"]
            ):
                return ("shared_assessment_source_provenance_invalid",)
    return ()


_ASSISTANT_BINDING_DIGEST_FIELDS = (
    "response_id",
    "run_id",
    "turn_id_or_null",
    "delivery_cohort_id",
    "request_source_refs",
    "canonical_output_parts",
    "completion_extent",
    "termination_cause",
    "first_output_unit_sequence",
    "last_output_unit_sequence",
    "output_unit_count",
    "finalization_idempotency_key",
)


def _load_assistant_response_binding(
    *,
    tx: EvidenceStoreTransaction,
    source: dict,
    manifest: dict,
    evidence_space_id: str,
) -> tuple[tuple[str, str] | None, tuple[str, ...]]:
    binding_id = source.get("assistant_response_binding_ref_or_null")
    replay = source.get("source_replay_identity")
    if not isinstance(binding_id, str) or not isinstance(replay, dict):
        return None, ("shared_assessment_assistant_response_binding_invalid",)
    binding = tx.read_record(
        record_kind="assistant_response_binding", record_id=binding_id
    )
    if (
        not isinstance(binding, dict)
        or binding.get("schema") != "relaylm.assistant_response_binding.v1"
        or binding.get("assistant_response_binding_id") != binding_id
    ):
        return None, ("shared_assessment_assistant_response_binding_invalid",)
    digest_input = {
        field: binding.get(field) for field in _ASSISTANT_BINDING_DIGEST_FIELDS
    }
    binding_digest = binding.get("canonical_binding_digest")
    if (
        not isinstance(binding_digest, str)
        or canonical_digest(digest_input) != binding_digest
    ):
        return None, ("shared_assessment_assistant_response_binding_invalid",)
    finalized_at = _parse_time(binding.get("finalized_at"))
    first_output_at = _parse_time(binding.get("first_output_accepted_at"))
    received_at = _parse_time(source.get("received_at"))
    observed_at = _parse_time(source.get("observed_at"))
    if (
        finalized_at is None
        or first_output_at is None
        or received_at != finalized_at
        or observed_at != finalized_at
        or first_output_at > finalized_at
        or binding.get("finalization_basis_ref")
        != "relaylm-managed-visible-output-finalization"
    ):
        return None, ("shared_assessment_assistant_response_binding_invalid",)
    principal, scope = build_runtime_authority(
        scope_kind="runtime_finalization_authority",
        allowed_operations=("response_finalize",),
        evidence_space_id=evidence_space_id,
        issued_at=str(binding["finalized_at"]),
    )
    if (
        binding.get("runtime_principal_ref") != principal.to_dict()
        or binding.get("runtime_finalization_authority_scope")
        != scope.to_dict()
    ):
        return None, ("shared_assessment_assistant_response_binding_invalid",)
    expected_replay = {
        "kind": "managed_response_identity",
        "response_id": binding.get("response_id"),
        "delivery_cohort_id": binding.get("delivery_cohort_id"),
        "response_finalization_idempotency_key": binding.get(
            "finalization_idempotency_key"
        ),
        "canonical_response_binding_digest": binding_digest,
    }
    if replay != expected_replay:
        return None, ("shared_assessment_assistant_response_binding_invalid",)

    reservation_id = binding.get("response_capture_reservation_id")
    if not isinstance(reservation_id, str):
        return None, ("shared_assessment_assistant_response_binding_invalid",)
    reservation = tx.read_record(
        record_kind="response_capture_reservation", record_id=reservation_id
    )
    if (
        not isinstance(reservation, dict)
        or reservation.get("schema")
        != "relaylm.assistant_response_capture_reservation.v1"
        or reservation.get("response_capture_reservation_id") != reservation_id
        or reservation.get("evidence_space_id") != evidence_space_id
        or any(
            reservation.get(field) != binding.get(field)
            for field in (
                "response_id",
                "run_id",
                "turn_id_or_null",
                "delivery_cohort_id",
                "request_source_refs",
            )
        )
    ):
        return None, ("shared_assessment_assistant_response_binding_invalid",)
    response_events = tx.read_log(
        log_kind="response_capture", key=reservation_id
    )
    finalize_events = [
        event
        for event in (response_events or [])
        if isinstance(event, dict) and event.get("operation") == "finalize"
    ]
    if (
        len(finalize_events) != 1
        or not isinstance(finalize_events[0].get("operation_payload"), dict)
        or finalize_events[0]["operation_payload"].get(
            "assistant_response_binding"
        )
        != binding
    ):
        return None, ("shared_assessment_assistant_response_binding_invalid",)

    manifest_parts = manifest.get("parts")
    binding_parts = binding.get("canonical_output_parts")
    if not isinstance(manifest_parts, list) or not isinstance(binding_parts, list):
        return None, ("shared_assessment_assistant_response_binding_invalid",)
    manifest_by_id = {
        item.get("part_id"): item
        for item in manifest_parts
        if isinstance(item, dict) and isinstance(item.get("part_id"), str)
    }
    if len(binding_parts) != len(manifest_by_id) or not binding_parts:
        return None, ("shared_assessment_assistant_response_binding_invalid",)
    for output_part in binding_parts:
        if not isinstance(output_part, dict):
            return None, ("shared_assessment_assistant_response_binding_invalid",)
        part_id = output_part.get("part_id")
        manifest_part = manifest_by_id.get(part_id)
        representation = output_part.get("content_representation")
        ranges = output_part.get("accepted_ranges")
        if (
            not isinstance(manifest_part, dict)
            or not isinstance(representation, dict)
            or representation
            != {
                "kind": "content_digest",
                "digest_algorithm": "sha256",
                "digest_value": manifest_part.get("content_digest_or_null"),
            }
            or not isinstance(ranges, list)
            or not ranges
            or output_part.get("media_type")
            != "text/plain; charset=utf-8"
            or str(manifest_part.get("media_type", "")).split(";", 1)[0]
            .strip()
            .lower()
            != "text/plain"
        ):
            return None, ("shared_assessment_assistant_response_binding_invalid",)
        cursor = 0
        for accepted_range in ranges:
            if (
                not isinstance(accepted_range, dict)
                or accepted_range.get("unit") != "utf8_byte"
                or type(accepted_range.get("start_inclusive")) is not int
                or type(accepted_range.get("end_exclusive")) is not int
                or accepted_range["start_inclusive"] != cursor
                or accepted_range["end_exclusive"] <= cursor
            ):
                return None, ("shared_assessment_assistant_response_binding_invalid",)
            cursor = accepted_range["end_exclusive"]
        if cursor != manifest_part.get("byte_length_or_null"):
            return None, ("shared_assessment_assistant_response_binding_invalid",)
    return (binding_id, binding_digest), ()


def _validate_validation_artifacts(
    *,
    tx: EvidenceStoreTransaction,
    source: dict,
    manifest: dict,
    validation: dict,
    source_event_id: str,
    evidence_space_id: str,
    manifest_digest: str,
    normalized_origin: str,
) -> tuple[str, ...]:
    requirements = validation.get("gate_requirements")
    refs = validation.get("active_artifact_refs")
    if not isinstance(requirements, list) or not isinstance(refs, list):
        return ("shared_assessment_validation_artifacts_invalid",)
    expected_gates = (
        ("canonicalization", "integrity")
        if normalized_origin == "user"
        else ("canonicalization", "integrity", "assistant_finalization")
    )
    assistant_binding: tuple[str, str] | None = None
    if normalized_origin == "assistant":
        assistant_binding, binding_reasons = _load_assistant_response_binding(
            tx=tx,
            source=source,
            manifest=manifest,
            evidence_space_id=evidence_space_id,
        )
        if assistant_binding is None:
            return binding_reasons
    if len(requirements) != len(refs) or len(set(refs)) != len(refs):
        return ("shared_assessment_validation_artifacts_invalid",)
    gates: list[str] = []
    for requirement, derived_id in zip(requirements, refs):
        if not isinstance(requirement, dict) or not isinstance(derived_id, str):
            return ("shared_assessment_validation_artifacts_invalid",)
        gate = requirement.get("gate_kind")
        if (
            not isinstance(gate, str)
            or requirement.get("requirement_id") != f"requirement:{gate}"
            or requirement.get("required_result") != "pass"
            or not derived_id.startswith("derivedartifact_")
        ):
            return ("shared_assessment_validation_artifacts_invalid",)
        event_id = "artifactevent_" + derived_id.removeprefix("derivedartifact_")
        event = tx.read_record(
            record_kind="source_derived_artifact_event", record_id=event_id
        )
        payload = event.get("operation_payload") if isinstance(event, dict) else None
        if (
            not isinstance(event, dict)
            or event.get("schema") != "relaylm.source_derived_artifact_event.v1"
            or event.get("artifact_event_id") != event_id
            or event.get("derived_artifact_id") != derived_id
            or event.get("artifact_revision") != 1
            or event.get("evidence_space_id") != evidence_space_id
            or not isinstance(payload, dict)
            or payload.get("result_status") != "pass"
        ):
            return ("shared_assessment_validation_artifacts_invalid",)
        if gate in {"canonicalization", "integrity"}:
            if (
                event.get("subject")
                != {"kind": "source_event", "source_event_id": source_event_id}
                or payload.get("input_schema")
                != "relaylm.canonical_source_manifest.v1"
                or payload.get("input_digest") != manifest_digest
                or payload.get("output_digest_or_null") != manifest_digest
                or payload.get("output_binding_ref_or_null") != source_event_id
            ):
                return ("shared_assessment_validation_artifacts_invalid",)
        elif gate == "assistant_finalization":
            assert assistant_binding is not None
            binding_id, binding_digest = assistant_binding
            if (
                event.get("subject")
                != {
                    "kind": "assistant_response_binding",
                    "assistant_response_binding_id": binding_id,
                }
                or payload.get("input_schema")
                != "relaylm.assistant_response_binding.v1"
                or payload.get("input_digest") != binding_digest
                or payload.get("output_digest_or_null") != binding_digest
                or payload.get("output_binding_ref_or_null") != binding_id
            ):
                return ("shared_assessment_validation_artifacts_invalid",)
        gates.append(gate)
    if tuple(gates) != expected_gates:
        return ("shared_assessment_validation_artifacts_invalid",)
    return ()


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _authority_not_before(
    *,
    source: dict,
    admission: dict,
    validation: dict,
    governance: dict | None,
    grants: tuple[AccessGrant, ...],
    now: datetime,
) -> tuple[str | None, tuple[str, ...]]:
    if now.tzinfo is None:
        return None, ("shared_assessment_clock_invalid",)
    values: list[object] = [
        source.get("received_at"),
        source.get("observed_at"),
        admission.get("decided_at"),
        validation.get("recorded_at"),
    ]
    if isinstance(governance, dict):
        values.extend((governance.get("recorded_at"), governance.get("effective_at")))
    values.extend(grant.issued_at for grant in grants)
    parsed = [_parse_time(value) for value in values]
    if any(value is None for value in parsed):
        return None, ("shared_assessment_authority_time_invalid",)
    latest = max(value for value in parsed if value is not None)
    current = now.astimezone(timezone.utc)
    if current < latest:
        return None, ("shared_assessment_authority_not_yet_effective",)
    return latest.isoformat(), ()


def _load_parts(
    *,
    tx: EvidenceStoreTransaction,
    source: dict,
    manifest: dict,
    selected_part_ids: tuple[str, ...],
) -> tuple[tuple[SharedAssessmentPassPart, ...] | None, tuple[str, ...]]:
    raw_parts = manifest.get("parts")
    attestation_ids = source.get("protected_payload_binding_attestation_ids")
    if not isinstance(raw_parts, list) or not isinstance(attestation_ids, list):
        return None, ("shared_assessment_source_parts_invalid",)
    manifest_part_ids = [
        item.get("part_id")
        for item in raw_parts
        if isinstance(item, dict) and isinstance(item.get("part_id"), str)
    ]
    if (
        len(manifest_part_ids) != len(raw_parts)
        or len(set(manifest_part_ids)) != len(manifest_part_ids)
        or len(set(attestation_ids)) != len(attestation_ids)
    ):
        return None, ("shared_assessment_source_parts_invalid",)
    manifest_by_id = {item["part_id"]: item for item in raw_parts}
    attestation_by_part: dict[str, dict] = {}
    for attestation_id in attestation_ids:
        if not isinstance(attestation_id, str):
            continue
        attestation = tx.read_record(
            record_kind="payload_binding_attestation", record_id=attestation_id
        )
        if (
            isinstance(attestation, dict)
            and attestation.get("schema")
            == "relaylm.protected_payload_binding_attestation.v1"
            and attestation.get("payload_binding_attestation_id") == attestation_id
            and isinstance(attestation.get("part_id"), str)
        ):
            part_id = str(attestation["part_id"])
            if part_id in attestation_by_part:
                return None, ("shared_assessment_payload_binding_duplicate",)
            attestation_by_part[part_id] = attestation
    parts: list[SharedAssessmentPassPart] = []
    for part_id in selected_part_ids:
        manifest_part = manifest_by_id.get(part_id)
        attestation = attestation_by_part.get(part_id)
        if not isinstance(manifest_part, dict) or not isinstance(attestation, dict):
            return None, ("shared_assessment_payload_binding_missing",)
        if (
            manifest_part.get("part_kind") != "text"
            or manifest_part.get("initial_disposition") != "protected"
            or attestation.get("source_event_id") != source.get("source_event_id")
            or attestation.get("content_digest") != manifest_part.get("content_digest_or_null")
            or attestation.get("storage_binding_schema")
            != "relaylm.evidence_store_binding.v1"
            or attestation.get("storage_authority_ref")
            != "relaylm.ev1.device_local_store"
        ):
            return None, ("shared_assessment_payload_binding_invalid",)
        storage_ref = attestation.get("storage_binding_ref")
        if not isinstance(storage_ref, str):
            return None, ("shared_assessment_payload_binding_invalid",)
        payload = tx.read_payload(payload_id=storage_ref)
        if not isinstance(payload, dict):
            return None, ("shared_assessment_protected_payload_missing",)
        text = payload.get("text")
        digest = payload.get("content_digest")
        media_type = payload.get("media_type")
        if (
            not isinstance(text, str)
            or not isinstance(digest, str)
            or not isinstance(media_type, str)
            or utf8_text_digest(text) != digest
            or digest != manifest_part.get("content_digest_or_null")
            or not _text_media_types_compatible(
                media_type, manifest_part.get("media_type")
            )
            or type(manifest_part.get("byte_length_or_null")) is not int
            or len(text.encode("utf-8")) != manifest_part.get("byte_length_or_null")
        ):
            return None, ("shared_assessment_protected_payload_integrity_invalid",)
        parts.append(
            SharedAssessmentPassPart(
                source_event_id=str(source["source_event_id"]),
                part_id=part_id,
                media_type=media_type,
                text=text,
                content_digest=digest,
            )
        )
    return tuple(parts), ()


def _text_media_types_compatible(payload_media_type: str, manifest_media_type: object) -> bool:
    if not isinstance(manifest_media_type, str):
        return False
    return (
        payload_media_type.split(";", 1)[0].strip().lower()
        == manifest_media_type.split(";", 1)[0].strip().lower()
        == "text/plain"
    )


def _manifest_protected_text_part_ids(manifest: dict) -> tuple[str, ...]:
    raw_parts = manifest.get("parts")
    if not isinstance(raw_parts, list):
        return ()
    values = [
        str(item["part_id"])
        for item in raw_parts
        if isinstance(item, dict)
        and isinstance(item.get("part_id"), str)
        and item.get("part_kind") == "text"
        and item.get("initial_disposition") == "protected"
    ]
    return tuple(sorted(values))


def _admission_id_from_attempt(events: list[dict] | None) -> str | None:
    if not isinstance(events, list):
        return None
    values = []
    for event in events:
        if event.get("operation") != "bind_admission":
            continue
        payload = event.get("operation_payload")
        if isinstance(payload, dict) and isinstance(payload.get("admission_decision_id"), str):
            values.append(str(payload["admission_decision_id"]))
    return values[-1] if len(set(values)) == 1 and values else None


def authorized_shared_assessment_sources_match_bundle(
    authorized: tuple[AuthorizedSharedAssessmentSource, ...], bundle: SharedAssessmentPassBundle
) -> bool:
    stable_authorizations = [
        {
            "source_event_id": item.authorization_snapshot.source_event_id,
            "authority_snapshot_digest": (
                item.authorization_snapshot.authority_snapshot_digest
            ),
            "selected_part_ids": list(
                item.authorization_snapshot.selected_part_ids
            ),
            "matched_grant_ids": list(item.authorization_snapshot.matched_grant_ids),
            "governance_revision": item.authorization_snapshot.governance_revision,
            "validation_bundle_revision": (
                item.authorization_snapshot.validation_bundle_revision
            ),
            "not_before": item.authorization_snapshot.not_before,
        }
        for item in authorized
    ]
    bundle_authorizations = [
        {
            "source_event_id": item.source_event_id,
            "authority_snapshot_digest": item.authority_snapshot_digest,
            "selected_part_ids": list(item.selected_part_ids),
            "matched_grant_ids": list(item.matched_grant_ids),
            "governance_revision": item.governance_revision,
            "validation_bundle_revision": item.validation_bundle_revision,
            "not_before": item.not_before,
        }
        for item in bundle.authorization_snapshots
    ]
    return (
        [item.evidence_ref.to_dict() for item in authorized]
        == [item.to_dict() for item in bundle.evidence_refs]
        and [part.to_dict() for item in authorized for part in item.parts]
        == [item.to_dict() for item in bundle.parts]
        and stable_authorizations == bundle_authorizations
    )


def _normalize_origin(value: object) -> str | None:
    return {
        "participant": "user",
        "assistant": "assistant",
    }.get(value if isinstance(value, str) else "")



__all__ = [
    "AuthorizedSharedAssessmentSource",
    "authorized_shared_assessment_sources_match_bundle",
    "load_authorized_shared_assessment_sources",
]
