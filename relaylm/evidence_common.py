"""Common identity, canonical-encoding, and digest primitives for EV-1.

This module owns the shared vocabulary from ``docs/contracts/governed-
evidence-contract-family.md``: canonical JSON/digest handling, opaque ID
generation, and the common reference value objects (``PrincipalRef``,
``ParticipationRef``, ``PolicySnapshotRef``, ``ResourceScope``,
``AuthorityScope``, ``AuthorityChangeSetRef``). Every other ``evidence_*``
module builds on these primitives instead of re-deriving them.

Following the rest of the codebase's idiom, validators return
``(value_or_none, reasons_tuple)`` rather than raising, so callers can
accumulate content-free blocked-reason lists.
"""
from __future__ import annotations

import hashlib
import json
import math
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

_MAX_REASONS = 32


def dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered[:_MAX_REASONS])


def sorted_unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def canonical_json_bytes(value: Any) -> bytes:
    """Encode ``value`` per the family's canonical JSON rules.

    JCS-compatible: sorted object keys, no insignificant whitespace, UTF-8
    without BOM, arrays preserve declared order, non-finite numbers
    forbidden. Callers are responsible for supplying plain ``dict``/``list``/
    scalar structures (no duplicate-key dicts can exist in Python already).
    """

    _reject_non_finite(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("evidence_non_finite_number_forbidden")
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            _reject_non_finite(nested)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            _reject_non_finite(nested)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: Any) -> str:
    """SHA-256 hex digest over ``value``'s canonical JSON encoding."""

    return sha256_hex(canonical_json_bytes(value))


def utf8_text_digest(text: str) -> str:
    """Digest over the exact UTF-8 byte sequence of ``text`` (no normalization)."""

    return sha256_hex(text.encode("utf-8", errors="strict"))


def new_opaque_id(prefix: str) -> str:
    """A globally unique, content-free identifier.

    Never derived from source content, display names, or semantic labels --
    just a random token behind a record-kind prefix so IDs remain readable in
    logs without encoding anything about the record they name.
    """

    return f"{prefix}_{secrets.token_hex(16)}"


PRINCIPAL_KINDS = frozenset(
    {
        "account",
        "participant",
        "assistant",
        "service",
        "tool",
        "sensor",
        "system",
        "external",
    }
)


@dataclass(frozen=True)
class PrincipalRef:
    principal_kind: str
    principal_id: str
    authority_domain_ref: str

    def to_dict(self) -> dict[str, object]:
        return {
            "principal_kind": self.principal_kind,
            "principal_id": self.principal_id,
            "authority_domain_ref": self.authority_domain_ref,
        }


def build_principal_ref(
    *, principal_kind: str, principal_id: str, authority_domain_ref: str
) -> tuple[PrincipalRef | None, tuple[str, ...]]:
    reasons: list[str] = []
    if principal_kind not in PRINCIPAL_KINDS:
        reasons.append("principal_kind_invalid")
    if not _is_token(principal_id):
        reasons.append("principal_id_invalid")
    if not _is_token(authority_domain_ref):
        reasons.append("authority_domain_ref_invalid")
    if reasons:
        return None, dedupe(reasons)
    return (
        PrincipalRef(
            principal_kind=principal_kind,
            principal_id=principal_id,
            authority_domain_ref=authority_domain_ref,
        ),
        (),
    )


PARTICIPATION_KINDS = frozenset(
    {"sender", "recipient", "room_member", "room_moderator", "observer", "unknown"}
)
VERIFICATION_STATES = frozenset({"verified", "asserted", "unresolved", "conflicting"})


@dataclass(frozen=True)
class ParticipationRef:
    principal_ref: PrincipalRef
    participation_kind: str
    room_ref_or_null: str | None
    participation_epoch_ref_or_null: str | None
    verification_state: str


def build_participation_ref(
    *,
    principal_ref: PrincipalRef,
    participation_kind: str,
    room_ref_or_null: str | None = None,
    participation_epoch_ref_or_null: str | None = None,
    verification_state: str,
) -> tuple[ParticipationRef | None, tuple[str, ...]]:
    reasons: list[str] = []
    if type(principal_ref) is not PrincipalRef:
        reasons.append("participation_principal_ref_invalid")
    if participation_kind not in PARTICIPATION_KINDS:
        reasons.append("participation_kind_invalid")
    if verification_state not in VERIFICATION_STATES:
        reasons.append("participation_verification_state_invalid")
    if participation_kind in {"room_member", "room_moderator"} and not room_ref_or_null:
        reasons.append("participation_room_ref_required")
    if reasons:
        return None, dedupe(reasons)
    return (
        ParticipationRef(
            principal_ref=principal_ref,
            participation_kind=participation_kind,
            room_ref_or_null=room_ref_or_null,
            participation_epoch_ref_or_null=participation_epoch_ref_or_null,
            verification_state=verification_state,
        ),
        (),
    )


@dataclass(frozen=True)
class PolicySnapshotRef:
    policy_id: str
    policy_revision: int
    policy_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "policy_revision": self.policy_revision,
            "policy_digest": self.policy_digest,
        }


def build_policy_snapshot_ref(
    *, policy_id: str, policy_revision: int, policy_body: Mapping[str, Any]
) -> tuple[PolicySnapshotRef | None, tuple[str, ...]]:
    reasons: list[str] = []
    if not _is_token(policy_id):
        reasons.append("policy_id_invalid")
    if type(policy_revision) is not int or policy_revision < 1:
        reasons.append("policy_revision_invalid")
    if reasons:
        return None, dedupe(reasons)
    digest = canonical_digest(dict(policy_body))
    return (
        PolicySnapshotRef(
            policy_id=policy_id,
            policy_revision=policy_revision,
            policy_digest=digest,
        ),
        (),
    )


@dataclass(frozen=True)
class ResourceScope:
    evidence_space_id: str
    whole_evidence_space: bool
    source_event_ids: tuple[str, ...] = ()
    participant_refs: tuple[str, ...] = ()
    room_refs: tuple[str, ...] = ()
    capture_stream_refs: tuple[str, ...] = ()
    route_refs: tuple[str, ...] = ()
    response_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_space_id": self.evidence_space_id,
            "whole_evidence_space": self.whole_evidence_space,
            "source_event_ids": list(self.source_event_ids),
            "participant_refs": list(self.participant_refs),
            "room_refs": list(self.room_refs),
            "capture_stream_refs": list(self.capture_stream_refs),
            "route_refs": list(self.route_refs),
            "response_refs": list(self.response_refs),
        }


def build_resource_scope(
    *,
    evidence_space_id: str,
    whole_evidence_space: bool,
    source_event_ids: Sequence[str] = (),
    participant_refs: Sequence[str] = (),
    room_refs: Sequence[str] = (),
    capture_stream_refs: Sequence[str] = (),
    route_refs: Sequence[str] = (),
    response_refs: Sequence[str] = (),
) -> tuple[ResourceScope | None, tuple[str, ...]]:
    lists = (
        source_event_ids,
        participant_refs,
        room_refs,
        capture_stream_refs,
        route_refs,
        response_refs,
    )
    any_non_empty = any(len(items) > 0 for items in lists)
    reasons: list[str] = []
    if whole_evidence_space and any_non_empty:
        reasons.append("resource_scope_whole_space_requires_empty_lists")
    if not whole_evidence_space and not any_non_empty:
        reasons.append("resource_scope_bounded_requires_nonempty_list")
    if reasons:
        return None, dedupe(reasons)
    return (
        ResourceScope(
            evidence_space_id=evidence_space_id,
            whole_evidence_space=whole_evidence_space,
            source_event_ids=sorted_unique(source_event_ids),
            participant_refs=sorted_unique(participant_refs),
            room_refs=sorted_unique(room_refs),
            capture_stream_refs=sorted_unique(capture_stream_refs),
            route_refs=sorted_unique(route_refs),
            response_refs=sorted_unique(response_refs),
        ),
        (),
    )


AUTHORITY_SCOPE_KINDS = frozenset(
    {
        "own_source",
        "represented_subject",
        "room_moderator",
        "workspace_admin",
        "evidence_operator",
        "security_operator",
        "retention_service",
        "recovery_service",
        "migration_authority",
        "route_configuration_authority",
        "runtime_finalization_authority",
        "capture_stream_authority",
        "change_feed_authority",
    }
)


@dataclass(frozen=True)
class AuthorityScope:
    scope_id: str
    scope_kind: str
    resource_scope: ResourceScope
    allowed_operations: tuple[str, ...]
    issued_at: str
    expires_at_or_null: str | None
    issuer_principal_ref: PrincipalRef
    issuer_authority_scope_ref_or_null: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "scope_id": self.scope_id,
            "scope_kind": self.scope_kind,
            "resource_scope": self.resource_scope.to_dict(),
            "allowed_operations": list(self.allowed_operations),
            "issued_at": self.issued_at,
            "issuer_principal_ref": self.issuer_principal_ref.to_dict(),
            "expires_at_or_null": self.expires_at_or_null,
            "issuer_authority_scope_ref_or_null": self.issuer_authority_scope_ref_or_null,
        }


def build_authority_scope(
    *,
    scope_kind: str,
    resource_scope: ResourceScope,
    allowed_operations: Sequence[str],
    issued_at: str,
    expires_at_or_null: str | None,
    issuer_principal_ref: PrincipalRef,
    issuer_authority_scope_ref_or_null: str | None = None,
) -> tuple[AuthorityScope | None, tuple[str, ...]]:
    reasons: list[str] = []
    if scope_kind not in AUTHORITY_SCOPE_KINDS:
        reasons.append("authority_scope_kind_invalid")
    ops = sorted_unique([op for op in allowed_operations if _is_token(op)])
    if not ops:
        reasons.append("authority_scope_allowed_operations_empty")
    if type(resource_scope) is not ResourceScope:
        reasons.append("authority_scope_resource_scope_invalid")
    if type(issuer_principal_ref) is not PrincipalRef:
        reasons.append("authority_scope_issuer_invalid")
    if reasons:
        return None, dedupe(reasons)
    # Deterministic (not random): AuthorityScope is embedded inside several
    # immutable, content-addressed records (AdmissionDecision,
    # ValidationBundleRevision, EvidenceGovernanceEvent, AccessGrant); a
    # random scope_id here would make every one of those non-idempotent
    # across a genuine retry with identical inputs.
    scope_id = "authscope_" + sha256_hex(
        canonical_json_bytes(
            {
                "scope_kind": scope_kind,
                "resource_scope": resource_scope.to_dict(),
                "allowed_operations": ops,
                "issued_at": issued_at,
                "issuer_principal_ref": issuer_principal_ref.to_dict(),
            }
        )
    )
    return (
        AuthorityScope(
            scope_id=scope_id,
            scope_kind=scope_kind,
            resource_scope=resource_scope,
            allowed_operations=ops,
            issued_at=issued_at,
            expires_at_or_null=expires_at_or_null,
            issuer_principal_ref=issuer_principal_ref,
            issuer_authority_scope_ref_or_null=issuer_authority_scope_ref_or_null,
        ),
        (),
    )


@dataclass(frozen=True)
class AuthorityChangeSetRef:
    change_set_id: str
    change_projection_plan_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "change_set_id": self.change_set_id,
            "change_projection_plan_digest": self.change_projection_plan_digest,
        }


_EV1_POLICY_BODY = {
    "policy_id": "relaylm.evidence_policy.v1",
    "policy_revision": 1,
    "description": (
        "EV-1 deterministic managed-conversation admission/governance policy: "
        "admitted-or-fail-closed for valid managed text, device-local bounded "
        "retention, least-privilege service-class grants."
    ),
}
_EV1_POLICY_SNAPSHOT: "PolicySnapshotRef | None" = None


def ev1_policy_snapshot_ref() -> "PolicySnapshotRef":
    """The one fixed, deterministic EV-1 policy snapshot used by every record.

    EV-1 has exactly one configured admission/governance policy revision
    (see the module docstring in ``evidence_governance``/``evidence_user_input``
    for what it encodes); this just gives every record kind that needs a
    ``PolicySnapshotRef`` the same real object instead of a bare string.
    """

    global _EV1_POLICY_SNAPSHOT
    if _EV1_POLICY_SNAPSHOT is None:
        ref, reasons = build_policy_snapshot_ref(
            policy_id=_EV1_POLICY_BODY["policy_id"],
            policy_revision=_EV1_POLICY_BODY["policy_revision"],
            policy_body=_EV1_POLICY_BODY,
        )
        assert ref is not None and not reasons
        _EV1_POLICY_SNAPSHOT = ref
    return _EV1_POLICY_SNAPSHOT


def build_runtime_authority(
    *,
    scope_kind: str,
    allowed_operations: Sequence[str],
    evidence_space_id: str,
    issued_at: str,
) -> tuple[PrincipalRef, AuthorityScope]:
    """The fixed local runtime service identity/scope for one authority operation.

    EV-1 is a single automated deterministic runtime (no human operator
    session, no multi-tenant identity), so every ``authority_principal_ref``/
    ``authority_scope`` pair in every family record is built from this one
    fixed service identity, scoped to exactly the evidence space and
    operations the caller names -- never a broader ``whole_evidence_space``
    grant than the operation needs.
    """

    principal = PrincipalRef(
        principal_kind="service",
        principal_id="relaylm-evidence-runtime",
        authority_domain_ref="relaylm-local",
    )
    resource_scope, reasons = build_resource_scope(
        evidence_space_id=evidence_space_id, whole_evidence_space=True
    )
    assert resource_scope is not None and not reasons
    scope, reasons = build_authority_scope(
        scope_kind=scope_kind,
        resource_scope=resource_scope,
        allowed_operations=allowed_operations,
        issued_at=issued_at,
        expires_at_or_null=None,
        issuer_principal_ref=principal,
    )
    assert scope is not None and not reasons
    return principal, scope


def _is_token(value: object) -> bool:
    return type(value) is str and bool(value) and len(value) <= 256


__all__ = [
    "AUTHORITY_SCOPE_KINDS",
    "AuthorityChangeSetRef",
    "AuthorityScope",
    "PARTICIPATION_KINDS",
    "PRINCIPAL_KINDS",
    "ParticipationRef",
    "PolicySnapshotRef",
    "PrincipalRef",
    "ResourceScope",
    "VERIFICATION_STATES",
    "build_authority_scope",
    "build_participation_ref",
    "build_policy_snapshot_ref",
    "build_principal_ref",
    "build_resource_scope",
    "build_runtime_authority",
    "canonical_digest",
    "canonical_json_bytes",
    "dedupe",
    "ev1_policy_snapshot_ref",
    "new_opaque_id",
    "sha256_hex",
    "sorted_unique",
    "utf8_text_digest",
]
