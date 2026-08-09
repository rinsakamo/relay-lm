"""LC-1C storage-neutral Subjective MEM Pin / Unpin proposal authority.

This module contains only bounded, content-free proposal and identity records.
Canonical prose, selectors, lifecycle receipts, and publication remain owned by
the existing Subjective MEM lifecycle and canonical Markdown boundaries.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath

from relaylm.evidence.common import canonical_digest, sha256_hex

PIN_OPERATION_FAMILY = "pin_unpin"
PIN_OPERATIONS = frozenset({"pin", "unpin"})
PIN_AUTHORIZATION_CLASSES = frozenset({"user_management", "operator_management"})
PIN_REASON_CATEGORIES = {
    "pin": frozenset({"user_requested_pin", "operator_requested_pin"}),
    "unpin": frozenset({"user_requested_unpin", "operator_requested_unpin"}),
}

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*\Z")


@dataclass(frozen=True)
class SubjectiveMemPinBoundary:
    subject_class: str = "personal_subjective_memory"
    pin_unpin_authority_explicit: bool = True
    semantic_payload_preserved: bool = True
    scope_preserved: bool = True
    formation_snapshot_preserved: bool = True
    strength_preserved: bool = True
    memory_kind_and_stage_preserved: bool = True
    product_knowledge_excluded: bool = True
    model_generation_not_performed: bool = True
    content_rewrite_not_requested: bool = True
    purge_not_requested: bool = True
    restore_not_requested: bool = True
    primary_mem_projection_not_written: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "subject_class": self.subject_class,
            "pin_unpin_authority_explicit": self.pin_unpin_authority_explicit,
            "semantic_payload_preserved": self.semantic_payload_preserved,
            "scope_preserved": self.scope_preserved,
            "formation_snapshot_preserved": self.formation_snapshot_preserved,
            "strength_preserved": self.strength_preserved,
            "memory_kind_and_stage_preserved": self.memory_kind_and_stage_preserved,
            "product_knowledge_excluded": self.product_knowledge_excluded,
            "model_generation_not_performed": self.model_generation_not_performed,
            "content_rewrite_not_requested": self.content_rewrite_not_requested,
            "purge_not_requested": self.purge_not_requested,
            "restore_not_requested": self.restore_not_requested,
            "primary_mem_projection_not_written": self.primary_mem_projection_not_written,
        }


@dataclass(frozen=True)
class SubjectiveMemPinProposal:
    operation_kind: str
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
    boundary: SubjectiveMemPinBoundary

    def to_digest_input(self) -> dict[str, object]:
        return {
            "operation_family": PIN_OPERATION_FAMILY,
            "operation_kind": self.operation_kind,
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
class SubjectiveMemPinOperationIdentity:
    operation_slot_id: str
    operation_id: str
    operation_key_digest: str
    input_digest: str
    transition_id: str
    intent_id: str
    receipt_id: str
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
            "result_id": self.result_id,
        }


def subjective_mem_pin_transition(operation_kind: str) -> tuple[str, str]:
    if operation_kind == "pin":
        return "active", "pinned"
    if operation_kind == "unpin":
        return "pinned", "active"
    raise ValueError("subjective_mem_pin_operation_kind_invalid")


def validate_subjective_mem_pin_proposal(
    proposal: object,
) -> tuple[str, ...]:
    if type(proposal) is not SubjectiveMemPinProposal:
        return ("subjective_mem_pin_proposal_invalid",)

    reasons: list[str] = []
    operation = proposal.operation_kind
    if operation not in PIN_OPERATIONS:
        reasons.append("subjective_mem_pin_operation_kind_invalid")
        expected_from = None
    else:
        expected_from, _expected_to = subjective_mem_pin_transition(operation)
        if proposal.expected_lifecycle_state != expected_from:
            reasons.append("subjective_mem_pin_transition_direction_invalid")
        if proposal.reason_category not in PIN_REASON_CATEGORIES[operation]:
            reasons.append("subjective_mem_pin_reason_category_invalid")
        expected_authority = (
            "user_management"
            if proposal.reason_category.startswith("user_requested_")
            else "operator_management"
        )
        if proposal.authorization_class != expected_authority:
            reasons.append("subjective_mem_pin_authorization_reason_mismatch")

    if proposal.expected_mutation_state != "none":
        reasons.append("subjective_mem_pin_mutation_state_invalid")
    if type(proposal.expected_current_revision) is not int or proposal.expected_current_revision < 1:
        reasons.append("subjective_mem_pin_current_revision_invalid")

    token_fields = (
        proposal.expected_memory_id,
        proposal.expected_page_id,
        proposal.expected_block_id,
        proposal.expected_current_selector_id,
        proposal.expected_current_receipt_id,
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
        reasons.append("subjective_mem_pin_identifier_invalid")

    if proposal.expected_memory_kind not in {"episodic", "semantic"}:
        reasons.append("subjective_mem_pin_memory_kind_invalid")
    if proposal.expected_formation_stage not in {"primary", "secondary"}:
        reasons.append("subjective_mem_pin_formation_stage_invalid")
    if proposal.authorization_class not in PIN_AUTHORIZATION_CLASSES:
        reasons.append("subjective_mem_pin_authorization_class_invalid")

    if not _safe_relative_path(proposal.expected_relative_path):
        reasons.append("subjective_mem_pin_relative_path_invalid")
    if not _digest(proposal.expected_page_digest, prefixed=True):
        reasons.append("subjective_mem_pin_page_digest_invalid")
    if any(
        not _digest(value)
        for value in (
            proposal.expected_current_selector_digest,
            proposal.expected_current_receipt_digest,
            proposal.expected_scope_binding_digest,
            proposal.expected_formation_snapshot_digest,
        )
    ):
        reasons.append("subjective_mem_pin_digest_invalid")

    if (
        type(proposal.boundary) is not SubjectiveMemPinBoundary
        or proposal.boundary.to_dict() != SubjectiveMemPinBoundary().to_dict()
    ):
        reasons.append("subjective_mem_pin_boundary_invalid")

    return tuple(dict.fromkeys(reasons))


def derive_subjective_mem_pin_operation_identity(
    *,
    evidence_space_id: str,
    character_authority_digest: str,
    memory_id: str,
    operation_idempotency_key: str,
    proposal: SubjectiveMemPinProposal,
    operation_time: str,
) -> tuple[SubjectiveMemPinOperationIdentity | None, tuple[str, ...]]:
    reasons = list(validate_subjective_mem_pin_proposal(proposal))
    if not _token(evidence_space_id) or not _token(memory_id):
        reasons.append("subjective_mem_pin_operation_identity_invalid")
    elif memory_id != proposal.expected_memory_id:
        reasons.append("subjective_mem_pin_memory_identity_mismatch")
    if not _digest(character_authority_digest):
        reasons.append("subjective_mem_pin_character_authority_digest_invalid")
    if not _token(operation_idempotency_key):
        reasons.append("subjective_mem_pin_idempotency_key_invalid")
    canonical_operation_time = _canonical_timestamp(operation_time)
    if canonical_operation_time is None:
        reasons.append("subjective_mem_pin_operation_time_invalid")
    if reasons:
        return None, tuple(dict.fromkeys(reasons))
    assert canonical_operation_time is not None

    key_digest = sha256_hex(operation_idempotency_key.encode("utf-8"))
    slot_material = "\0".join(
        (
            evidence_space_id,
            character_authority_digest,
            memory_id,
            PIN_OPERATION_FAMILY,
            key_digest,
        )
    )
    operation_slot_id = _opaque("smpinkey", slot_material)
    input_digest = canonical_digest(
        {
            "proposal_input_digest": proposal.input_digest,
            "operation_time": canonical_operation_time,
        }
    )
    operation_id = _opaque("smpinop", operation_slot_id + "\0" + input_digest)
    return (
        SubjectiveMemPinOperationIdentity(
            operation_slot_id=operation_slot_id,
            operation_id=operation_id,
            operation_key_digest=key_digest,
            input_digest=input_digest,
            transition_id=_opaque("smpintransition", operation_id),
            intent_id=_opaque("smpinintent", operation_id),
            receipt_id=_opaque("smpinreceipt", operation_id),
            result_id=_opaque("smpinresult", operation_slot_id),
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
    "PIN_AUTHORIZATION_CLASSES",
    "PIN_OPERATION_FAMILY",
    "PIN_OPERATIONS",
    "PIN_REASON_CATEGORIES",
    "SubjectiveMemPinBoundary",
    "SubjectiveMemPinOperationIdentity",
    "SubjectiveMemPinProposal",
    "derive_subjective_mem_pin_operation_identity",
    "subjective_mem_pin_transition",
    "validate_subjective_mem_pin_proposal",
]
