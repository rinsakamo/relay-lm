"""LC-1D storage-neutral Subjective MEM Restore proposal authority.

This module contains only bounded, content-free proposal and identity records for
one exact ``hidden -> active`` lifecycle transition. Canonical Markdown,
selectors, Forget lineage, tombstone release publication, replay, and recovery
remain owned by their existing runtime boundaries.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath

from relaylm.evidence_common import canonical_digest, sha256_hex

RESTORE_OPERATION_FAMILY = "restore"
RESTORE_AUTHORIZATION_CLASSES = frozenset({"user_management", "operator_management"})
RESTORE_REASON_CATEGORIES = frozenset(
    {"user_requested_restore", "operator_requested_restore"}
)

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*\Z")


@dataclass(frozen=True)
class SubjectiveMemRestoreBoundary:
    subject_class: str = "personal_subjective_memory"
    restore_authority_explicit: bool = True
    semantic_payload_preserved: bool = True
    scope_preserved: bool = True
    formation_snapshot_preserved: bool = True
    strength_preserved: bool = True
    memory_kind_and_stage_preserved: bool = True
    product_knowledge_excluded: bool = True
    model_generation_not_performed: bool = True
    content_rewrite_not_requested: bool = True
    correction_not_requested: bool = True
    purge_not_requested: bool = True
    consolidation_not_requested: bool = True
    second_logical_memory_not_created: bool = True
    primary_mem_mutation_not_requested: bool = True
    tombstone_mutation_not_requested: bool = True
    immutable_tombstone_release_required: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "subject_class": self.subject_class,
            "restore_authority_explicit": self.restore_authority_explicit,
            "semantic_payload_preserved": self.semantic_payload_preserved,
            "scope_preserved": self.scope_preserved,
            "formation_snapshot_preserved": self.formation_snapshot_preserved,
            "strength_preserved": self.strength_preserved,
            "memory_kind_and_stage_preserved": self.memory_kind_and_stage_preserved,
            "product_knowledge_excluded": self.product_knowledge_excluded,
            "model_generation_not_performed": self.model_generation_not_performed,
            "content_rewrite_not_requested": self.content_rewrite_not_requested,
            "correction_not_requested": self.correction_not_requested,
            "purge_not_requested": self.purge_not_requested,
            "consolidation_not_requested": self.consolidation_not_requested,
            "second_logical_memory_not_created": self.second_logical_memory_not_created,
            "primary_mem_mutation_not_requested": self.primary_mem_mutation_not_requested,
            "tombstone_mutation_not_requested": self.tombstone_mutation_not_requested,
            "immutable_tombstone_release_required": self.immutable_tombstone_release_required,
        }


@dataclass(frozen=True)
class SubjectiveMemRestoreProposal:
    expected_memory_id: str
    expected_current_revision: int
    expected_lifecycle_state: str
    expected_mutation_state: str
    expected_page_id: str
    expected_relative_path: str
    expected_block_id: str
    expected_page_digest: str
    expected_current_selector_id: str
    expected_current_selector_digest: str
    expected_current_receipt_id: str
    expected_current_receipt_digest: str
    expected_forget_transition_id: str
    expected_forget_transition_digest: str
    expected_forget_tombstone_id: str
    expected_forget_tombstone_digest: str
    expected_semantic_identity_digest: str
    expected_memory_kind: str
    expected_formation_stage: str
    expected_scope_binding_digest: str
    expected_formation_snapshot_digest: str
    expected_revision_schema: str
    expected_page_schema: str
    expected_block_schema: str
    expected_renderer_revision: str
    expected_partition_revision: str
    expected_platform_revision: str
    authorization_class: str
    authorization_id: str
    reason_category: str
    policy_revision: str
    boundary: SubjectiveMemRestoreBoundary

    def to_digest_input(self) -> dict[str, object]:
        return {
            "operation_family": RESTORE_OPERATION_FAMILY,
            "operation_kind": "restore",
            "expected_memory_ref": {
                "memory_id": self.expected_memory_id,
                "memory_revision": self.expected_current_revision,
            },
            "expected_lifecycle_state": self.expected_lifecycle_state,
            "expected_mutation_state": self.expected_mutation_state,
            "expected_page_id": self.expected_page_id,
            "expected_relative_path": self.expected_relative_path,
            "expected_block_id": self.expected_block_id,
            "expected_page_digest": self.expected_page_digest,
            "expected_current_selector_id": self.expected_current_selector_id,
            "expected_current_selector_digest": self.expected_current_selector_digest,
            "expected_current_receipt_id": self.expected_current_receipt_id,
            "expected_current_receipt_digest": self.expected_current_receipt_digest,
            "expected_forget_transition_id": self.expected_forget_transition_id,
            "expected_forget_transition_digest": self.expected_forget_transition_digest,
            "expected_forget_tombstone_id": self.expected_forget_tombstone_id,
            "expected_forget_tombstone_digest": self.expected_forget_tombstone_digest,
            "expected_semantic_identity_digest": self.expected_semantic_identity_digest,
            "expected_memory_kind": self.expected_memory_kind,
            "expected_formation_stage": self.expected_formation_stage,
            "expected_scope_binding_digest": self.expected_scope_binding_digest,
            "expected_formation_snapshot_digest": self.expected_formation_snapshot_digest,
            "expected_revision_schema": self.expected_revision_schema,
            "expected_page_schema": self.expected_page_schema,
            "expected_block_schema": self.expected_block_schema,
            "expected_renderer_revision": self.expected_renderer_revision,
            "expected_partition_revision": self.expected_partition_revision,
            "expected_platform_revision": self.expected_platform_revision,
            "authorization_class": self.authorization_class,
            "authorization_id": self.authorization_id,
            "reason_category": self.reason_category,
            "policy_revision": self.policy_revision,
            "boundary": self.boundary.to_dict(),
        }

    @property
    def input_digest(self) -> str:
        return canonical_digest(self.to_digest_input())


@dataclass(frozen=True)
class SubjectiveMemRestoreOperationIdentity:
    operation_slot_id: str
    operation_id: str
    operation_key_digest: str
    input_digest: str
    transition_id: str
    intent_id: str
    receipt_id: str
    release_id: str
    result_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "operation_slot_id": self.operation_slot_id,
            "operation_id": self.operation_id,
            "operation_key_digest": self.operation_key_digest,
            "input_digest": self.input_digest,
            "transition_id": self.transition_id,
            "intent_id": self.intent_id,
            "receipt_id": self.receipt_id,
            "release_id": self.release_id,
            "result_id": self.result_id,
        }


def subjective_mem_restore_transition() -> tuple[str, str]:
    """Return the single LC-1D lifecycle direction."""

    return "hidden", "active"


def validate_subjective_mem_restore_proposal(
    proposal: object,
) -> tuple[str, ...]:
    if type(proposal) is not SubjectiveMemRestoreProposal:
        return ("subjective_mem_restore_proposal_invalid",)
    reasons = (
        *_restore_state_reasons(proposal),
        *_restore_authority_reasons(proposal),
        *_restore_shape_reasons(proposal),
    )
    return tuple(dict.fromkeys(reasons))


def _restore_state_reasons(proposal: SubjectiveMemRestoreProposal) -> tuple[str, ...]:
    reasons: list[str] = []
    if proposal.expected_lifecycle_state != "hidden":
        reasons.append("subjective_mem_restore_transition_direction_invalid")
    if proposal.expected_mutation_state != "none":
        reasons.append("subjective_mem_restore_mutation_state_invalid")
    if (
        type(proposal.expected_current_revision) is not int
        or proposal.expected_current_revision < 2
    ):
        reasons.append("subjective_mem_restore_current_revision_invalid")
    if proposal.expected_memory_kind not in {"episodic", "semantic"}:
        reasons.append("subjective_mem_restore_memory_kind_invalid")
    if proposal.expected_formation_stage not in {"primary", "secondary"}:
        reasons.append("subjective_mem_restore_formation_stage_invalid")
    return tuple(reasons)


def _restore_authority_reasons(
    proposal: SubjectiveMemRestoreProposal,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if proposal.reason_category not in RESTORE_REASON_CATEGORIES:
        reasons.append("subjective_mem_restore_reason_category_invalid")
    else:
        expected_authority = (
            "user_management"
            if proposal.reason_category == "user_requested_restore"
            else "operator_management"
        )
        if proposal.authorization_class != expected_authority:
            reasons.append("subjective_mem_restore_authorization_reason_mismatch")
    if proposal.authorization_class not in RESTORE_AUTHORIZATION_CLASSES:
        reasons.append("subjective_mem_restore_authorization_class_invalid")
    if (
        type(proposal.boundary) is not SubjectiveMemRestoreBoundary
        or proposal.boundary.to_dict() != SubjectiveMemRestoreBoundary().to_dict()
    ):
        reasons.append("subjective_mem_restore_boundary_invalid")
    return tuple(reasons)


def _restore_shape_reasons(proposal: SubjectiveMemRestoreProposal) -> tuple[str, ...]:
    reasons: list[str] = []
    token_fields = (
        proposal.expected_memory_id,
        proposal.expected_page_id,
        proposal.expected_block_id,
        proposal.expected_current_selector_id,
        proposal.expected_current_receipt_id,
        proposal.expected_forget_transition_id,
        proposal.expected_forget_tombstone_id,
        proposal.expected_revision_schema,
        proposal.expected_page_schema,
        proposal.expected_block_schema,
        proposal.expected_renderer_revision,
        proposal.expected_partition_revision,
        proposal.expected_platform_revision,
        proposal.authorization_id,
        proposal.policy_revision,
    )
    if any(not _token(value) for value in token_fields):
        reasons.append("subjective_mem_restore_identifier_invalid")
    if not _safe_relative_path(proposal.expected_relative_path):
        reasons.append("subjective_mem_restore_relative_path_invalid")
    if not _digest(proposal.expected_page_digest, prefixed=True):
        reasons.append("subjective_mem_restore_page_digest_invalid")
    digest_fields = (
        proposal.expected_current_selector_digest,
        proposal.expected_current_receipt_digest,
        proposal.expected_forget_transition_digest,
        proposal.expected_forget_tombstone_digest,
        proposal.expected_semantic_identity_digest,
        proposal.expected_scope_binding_digest,
        proposal.expected_formation_snapshot_digest,
    )
    if any(not _digest(value) for value in digest_fields):
        reasons.append("subjective_mem_restore_digest_invalid")
    return tuple(reasons)


def derive_subjective_mem_restore_operation_identity(
    *,
    evidence_space_id: str,
    character_authority_digest: str,
    memory_id: str,
    operation_idempotency_key: str,
    proposal: SubjectiveMemRestoreProposal,
    operation_time: str,
) -> tuple[SubjectiveMemRestoreOperationIdentity | None, tuple[str, ...]]:
    reasons = list(validate_subjective_mem_restore_proposal(proposal))
    if type(proposal) is not SubjectiveMemRestoreProposal:
        return None, tuple(reasons)
    if not _token(evidence_space_id) or not _token(memory_id):
        reasons.append("subjective_mem_restore_operation_identity_invalid")
    elif memory_id != proposal.expected_memory_id:
        reasons.append("subjective_mem_restore_memory_identity_mismatch")
    if not _digest(character_authority_digest):
        reasons.append("subjective_mem_restore_character_authority_digest_invalid")
    if not _token(operation_idempotency_key):
        reasons.append("subjective_mem_restore_idempotency_key_invalid")
    canonical_operation_time = _canonical_timestamp(operation_time)
    if canonical_operation_time is None:
        reasons.append("subjective_mem_restore_operation_time_invalid")
    if reasons:
        return None, tuple(dict.fromkeys(reasons))
    assert canonical_operation_time is not None

    key_digest = sha256_hex(operation_idempotency_key.encode("utf-8"))
    slot_material = "\0".join(
        (
            evidence_space_id,
            character_authority_digest,
            memory_id,
            RESTORE_OPERATION_FAMILY,
            key_digest,
        )
    )
    operation_slot_id = _opaque("smrestorekey", slot_material)
    input_digest = canonical_digest(
        {
            "proposal_input_digest": proposal.input_digest,
            "operation_time": canonical_operation_time,
        }
    )
    operation_id = _opaque("smrestoreop", operation_slot_id + "\0" + input_digest)
    return (
        SubjectiveMemRestoreOperationIdentity(
            operation_slot_id=operation_slot_id,
            operation_id=operation_id,
            operation_key_digest=key_digest,
            input_digest=input_digest,
            transition_id=_opaque("smrestoretransition", operation_id),
            intent_id=_opaque("smrestoreintent", operation_id),
            receipt_id=_opaque("smrestorereceipt", operation_id),
            release_id=_opaque("smrestorerelease", operation_id),
            result_id=_opaque("smrestoreresult", operation_slot_id),
        ),
        (),
    )


def _opaque(prefix: str, value: str) -> str:
    return f"{prefix}_{sha256_hex(value.encode('utf-8'))}"


def _token(value: object, max_length: int = 256) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= max_length
        and _TOKEN_RE.fullmatch(value) is not None
    )


def _digest(value: object, *, prefixed: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    if prefixed:
        return (
            len(value) == 71
            and value.startswith("sha256:")
            and all(ch in "0123456789abcdef" for ch in value[7:])
        )
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _safe_relative_path(value: object) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 1024
        or "\\" in value
        or "\0" in value
    ):
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and path.as_posix() == value
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _canonical_timestamp(value: object) -> str | None:
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat()


__all__ = [
    "RESTORE_AUTHORIZATION_CLASSES",
    "RESTORE_OPERATION_FAMILY",
    "RESTORE_REASON_CATEGORIES",
    "SubjectiveMemRestoreBoundary",
    "SubjectiveMemRestoreOperationIdentity",
    "SubjectiveMemRestoreProposal",
    "derive_subjective_mem_restore_operation_identity",
    "subjective_mem_restore_transition",
    "validate_subjective_mem_restore_proposal",
]
