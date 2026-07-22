"""EvidenceSpaceDescriptor v1 for the bounded EV-1 private conversation.

Evidence-space identity is intentionally independent of character and memory
configuration.  The current public function signatures retain those arguments
for call-site compatibility, but they are validation context only and never
participate in the evidence-space identifier.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from relaylm.evidence_common import (
    AuthorityChangeSetRef,
    AuthorityScope,
    PolicySnapshotRef,
    PrincipalRef,
    build_resource_scope,
    build_runtime_authority,
    canonical_digest,
    dedupe,
    ev1_policy_snapshot_ref,
)

if TYPE_CHECKING:
    from relaylm.evidence_store import EvidenceRecordStore

SCHEMA = "relaylm.evidence_space_descriptor.v1"
_SUPPORTED_ISOLATION_MODES = frozenset({"private_conversation"})


@dataclass(frozen=True)
class EvidenceSpaceDescriptor:
    schema: str
    evidence_space_id: str
    descriptor_revision: int
    expected_previous_descriptor_revision_or_null: int | None
    workspace_or_tenant_ref: str
    isolation_mode: str
    controller_principal_ref: PrincipalRef
    participant_domain_ref: str
    policy_snapshot_ref: PolicySnapshotRef
    created_at: str
    retired_at_or_null: str | None
    authority_principal_ref: PrincipalRef
    authority_scope: AuthorityScope
    authority_change_set_ref_or_null: AuthorityChangeSetRef | None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "evidence_space_id": self.evidence_space_id,
            "descriptor_revision": self.descriptor_revision,
            "expected_previous_descriptor_revision_or_null": self.expected_previous_descriptor_revision_or_null,
            "workspace_or_tenant_ref": self.workspace_or_tenant_ref,
            "isolation_mode": self.isolation_mode,
            "controller_principal_ref": self.controller_principal_ref.to_dict(),
            "participant_domain_ref": self.participant_domain_ref,
            "policy_snapshot_ref": self.policy_snapshot_ref.to_dict(),
            "created_at": self.created_at,
            "retired_at_or_null": self.retired_at_or_null,
            "authority_principal_ref": self.authority_principal_ref.to_dict(),
            "authority_scope": self.authority_scope.to_dict(),
            "authority_change_set_ref_or_null": (
                self.authority_change_set_ref_or_null.to_dict()
                if self.authority_change_set_ref_or_null is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "EvidenceSpaceDescriptor":
        return cls(
            schema=str(payload["schema"]),
            evidence_space_id=str(payload["evidence_space_id"]),
            descriptor_revision=int(payload["descriptor_revision"]),
            expected_previous_descriptor_revision_or_null=payload[
                "expected_previous_descriptor_revision_or_null"
            ],  # type: ignore[assignment]
            workspace_or_tenant_ref=str(payload["workspace_or_tenant_ref"]),
            isolation_mode=str(payload["isolation_mode"]),
            controller_principal_ref=PrincipalRef(**payload["controller_principal_ref"]),  # type: ignore[arg-type]
            participant_domain_ref=str(payload["participant_domain_ref"]),
            policy_snapshot_ref=PolicySnapshotRef(**payload["policy_snapshot_ref"]),  # type: ignore[arg-type]
            created_at=str(payload["created_at"]),
            retired_at_or_null=payload["retired_at_or_null"],  # type: ignore[assignment]
            authority_principal_ref=PrincipalRef(**payload["authority_principal_ref"]),  # type: ignore[arg-type]
            authority_scope=_authority_scope_from_dict(payload["authority_scope"]),  # type: ignore[arg-type]
            authority_change_set_ref_or_null=(
                AuthorityChangeSetRef(**payload["authority_change_set_ref_or_null"])  # type: ignore[arg-type]
                if payload["authority_change_set_ref_or_null"] is not None
                else None
            ),
        )


def _authority_scope_from_dict(payload: dict[str, object]) -> AuthorityScope:
    resource_scope_payload = dict(payload["resource_scope"])  # type: ignore[arg-type]
    resource_scope, reasons = build_resource_scope(
        evidence_space_id=str(resource_scope_payload["evidence_space_id"]),
        whole_evidence_space=bool(resource_scope_payload["whole_evidence_space"]),
        source_event_ids=tuple(resource_scope_payload["source_event_ids"]),  # type: ignore[arg-type]
        participant_refs=tuple(resource_scope_payload["participant_refs"]),  # type: ignore[arg-type]
        room_refs=tuple(resource_scope_payload["room_refs"]),  # type: ignore[arg-type]
        capture_stream_refs=tuple(resource_scope_payload["capture_stream_refs"]),  # type: ignore[arg-type]
        route_refs=tuple(resource_scope_payload["route_refs"]),  # type: ignore[arg-type]
        response_refs=tuple(resource_scope_payload["response_refs"]),  # type: ignore[arg-type]
    )
    if resource_scope is None or reasons:
        raise ValueError("evidence_space_authority_scope_invalid")
    return AuthorityScope(
        scope_id=str(payload["scope_id"]),
        scope_kind=str(payload["scope_kind"]),
        resource_scope=resource_scope,
        allowed_operations=tuple(payload["allowed_operations"]),  # type: ignore[arg-type]
        issued_at=str(payload["issued_at"]),
        expires_at_or_null=payload["expires_at_or_null"],  # type: ignore[assignment]
        issuer_principal_ref=PrincipalRef(**payload["issuer_principal_ref"]),  # type: ignore[arg-type]
        issuer_authority_scope_ref_or_null=payload["issuer_authority_scope_ref_or_null"],  # type: ignore[assignment]
    )


def derive_evidence_space_id(
    *,
    workspace_or_tenant_ref: str,
    character_id: str,
    memory_namespace: str,
    session_id: str,
) -> str:
    """Return a character-independent private-conversation identity.

    ``character_id`` and ``memory_namespace`` are deliberately excluded from
    the digest.  The managed route's validated session is the bounded
    conversation identity for EV-1.
    """

    del character_id, memory_namespace
    digest = canonical_digest(
        {
            "schema": SCHEMA,
            "workspace_or_tenant_ref": workspace_or_tenant_ref,
            "isolation_mode": "private_conversation",
            "conversation_ref": session_id,
        }
    )
    return f"evsp_{digest}"


def derive_participant_principal(
    *, workspace_or_tenant_ref: str, session_id: str
) -> PrincipalRef:
    principal_id = "principal_" + canonical_digest(
        {
            "workspace_or_tenant_ref": workspace_or_tenant_ref,
            "conversation_ref": session_id,
            "role": "single_principal_controller",
        }
    )
    domain = "participant_domain_" + canonical_digest(
        {"workspace_or_tenant_ref": workspace_or_tenant_ref, "kind": "private_conversation"}
    )
    return PrincipalRef(
        principal_kind="participant",
        principal_id=principal_id,
        authority_domain_ref=domain,
    )


def build_bootstrap_evidence_space_descriptor(
    *,
    workspace_or_tenant_ref: str,
    character_id: str,
    memory_namespace: str,
    session_id: str,
    created_at: str,
) -> tuple[EvidenceSpaceDescriptor | None, tuple[str, ...]]:
    reasons: list[str] = []
    for name, value in (
        ("workspace_or_tenant_ref", workspace_or_tenant_ref),
        ("character_id", character_id),
        ("memory_namespace", memory_namespace),
        ("session_id", session_id),
        ("created_at", created_at),
    ):
        if type(value) is not str or not value:
            reasons.append(f"evidence_space_{name}_invalid")
    if reasons:
        return None, dedupe(reasons)

    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref=workspace_or_tenant_ref,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
    )
    participant = derive_participant_principal(
        workspace_or_tenant_ref=workspace_or_tenant_ref,
        session_id=session_id,
    )
    authority_principal_ref, authority_scope = build_runtime_authority(
        scope_kind="route_configuration_authority",
        allowed_operations=("evidence_space_descriptor_bootstrap",),
        evidence_space_id=evidence_space_id,
        issued_at=created_at,
    )
    return (
        EvidenceSpaceDescriptor(
            schema=SCHEMA,
            evidence_space_id=evidence_space_id,
            descriptor_revision=1,
            expected_previous_descriptor_revision_or_null=None,
            workspace_or_tenant_ref=workspace_or_tenant_ref,
            isolation_mode="private_conversation",
            controller_principal_ref=participant,
            participant_domain_ref=participant.authority_domain_ref,
            policy_snapshot_ref=ev1_policy_snapshot_ref(),
            created_at=created_at,
            retired_at_or_null=None,
            authority_principal_ref=authority_principal_ref,
            authority_scope=authority_scope,
            authority_change_set_ref_or_null=None,
        ),
        (),
    )


def resolve_evidence_space_descriptor(
    *,
    store: "EvidenceRecordStore | None",
    workspace_or_tenant_ref: str,
    character_id: str,
    memory_namespace: str,
    session_id: str,
    created_at: str,
) -> tuple[EvidenceSpaceDescriptor | None, tuple[str, ...]]:
    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref=workspace_or_tenant_ref,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
    )
    if store is not None:
        persisted = store.read_record(
            evidence_space_id=evidence_space_id,
            record_kind="evidence_space_descriptor",
            record_id="revision-1",
        )
        if persisted is not None:
            try:
                descriptor = EvidenceSpaceDescriptor.from_dict(persisted)
            except (TypeError, KeyError, ValueError):
                return None, ("evidence_space_descriptor_persisted_shape_invalid",)
            if descriptor.evidence_space_id != evidence_space_id:
                return None, ("evidence_space_descriptor_identity_mismatch",)
            return descriptor, ()
    return build_bootstrap_evidence_space_descriptor(
        workspace_or_tenant_ref=workspace_or_tenant_ref,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
        created_at=created_at,
    )


def isolation_mode_supported(isolation_mode: str) -> bool:
    return isolation_mode in _SUPPORTED_ISOLATION_MODES


__all__ = [
    "SCHEMA",
    "EvidenceSpaceDescriptor",
    "build_bootstrap_evidence_space_descriptor",
    "derive_evidence_space_id",
    "derive_participant_principal",
    "isolation_mode_supported",
    "resolve_evidence_space_descriptor",
]
