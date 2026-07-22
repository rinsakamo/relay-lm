"""Contract 1C authoritative validation artifacts for EV-1 admission gates."""
from __future__ import annotations

from dataclasses import dataclass

from relaylm.evidence_common import (
    AuthorityChangeSetRef,
    build_runtime_authority,
    canonical_digest,
    ev1_policy_snapshot_ref,
)

SCHEMA = "relaylm.source_derived_artifact_event.v1"
_GATE_ARTIFACT_KIND = {
    "canonicalization": "canonicalization_validation_result",
    "integrity": "integrity_validation_result",
    "assistant_finalization": "assistant_finalization_validation_result",
}


@dataclass(frozen=True)
class ValidationArtifactIdentity:
    gate_kind: str
    requirement_id: str
    derived_artifact_id: str
    artifact_event_id: str


def build_validation_artifact_identities(
    *, operation_idempotency_key: str, gate_kinds: tuple[str, ...]
) -> tuple[ValidationArtifactIdentity, ...]:
    identities: list[ValidationArtifactIdentity] = []
    for gate_kind in gate_kinds:
        if gate_kind not in _GATE_ARTIFACT_KIND:
            raise ValueError("validation_artifact_gate_kind_unsupported")
        seed = canonical_digest(
            {
                "operation_idempotency_key": operation_idempotency_key,
                "gate_kind": gate_kind,
            }
        )
        identities.append(
            ValidationArtifactIdentity(
                gate_kind=gate_kind,
                requirement_id=f"requirement:{gate_kind}",
                derived_artifact_id=f"derivedartifact_{seed}",
                artifact_event_id=f"artifactevent_{seed}",
            )
        )
    return tuple(identities)


def build_validation_artifact_events(
    *,
    identities: tuple[ValidationArtifactIdentity, ...],
    evidence_space_id: str,
    source_event_id: str,
    canonical_manifest_digest: str,
    assistant_response_binding_id_or_null: str | None,
    assistant_response_binding_digest_or_null: str | None,
    authority_change_set_ref: AuthorityChangeSetRef,
    recorded_at: str,
    operation_idempotency_key: str,
) -> tuple[dict[str, object], ...]:
    events: list[dict[str, object]] = []
    for identity in identities:
        artifact_kind = _GATE_ARTIFACT_KIND[identity.gate_kind]
        if identity.gate_kind == "assistant_finalization":
            if (
                assistant_response_binding_id_or_null is None
                or assistant_response_binding_digest_or_null is None
            ):
                raise ValueError("assistant_finalization_artifact_requires_binding")
            subject = {
                "kind": "assistant_response_binding",
                "assistant_response_binding_id": assistant_response_binding_id_or_null,
            }
            input_schema = "relaylm.assistant_response_binding.v1"
            input_digest = assistant_response_binding_digest_or_null
            output_binding_ref = assistant_response_binding_id_or_null
        else:
            subject = {"kind": "source_event", "source_event_id": source_event_id}
            input_schema = "relaylm.canonical_source_manifest.v1"
            input_digest = canonical_manifest_digest
            output_binding_ref = source_event_id
        principal, scope = build_runtime_authority(
            scope_kind="evidence_operator",
            allowed_operations=("source_derived_artifact_create",),
            evidence_space_id=evidence_space_id,
            issued_at=recorded_at,
        )
        events.append(
            {
                "schema": SCHEMA,
                "artifact_event_id": identity.artifact_event_id,
                "derived_artifact_id": identity.derived_artifact_id,
                "artifact_revision": 1,
                "expected_previous_artifact_revision_or_null": None,
                "evidence_space_id": evidence_space_id,
                "subject": subject,
                "artifact_kind": artifact_kind,
                "artifact_authority_class": "integrity_gate",
                "operation": "create",
                "operation_payload": {
                    "producer_name": "relaylm.ev1.deterministic_validator",
                    "producer_version": "1",
                    "input_schema": input_schema,
                    "input_digest": input_digest,
                    "output_binding_ref_or_null": output_binding_ref,
                    "output_digest_or_null": input_digest,
                    "result_status": "pass",
                    "source_governance_inheritance_ref": (
                        f"source-event:{source_event_id}:initial-admission"
                    ),
                },
                "mutation_principal_ref": principal.to_dict(),
                "mutation_authority_scope": scope.to_dict(),
                "policy_snapshot_ref": ev1_policy_snapshot_ref().to_dict(),
                "recorded_at": recorded_at,
                "operation_idempotency_key": (
                    f"{operation_idempotency_key}:validation-artifact:{identity.gate_kind}"
                ),
                "authority_change_set_ref_or_null": authority_change_set_ref.to_dict(),
            }
        )
    return tuple(events)


__all__ = [
    "SCHEMA",
    "ValidationArtifactIdentity",
    "build_validation_artifact_events",
    "build_validation_artifact_identities",
]
