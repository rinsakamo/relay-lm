"""LC-1E storage-neutral Subjective MEM Consolidate proposal authority.

This module contains only bounded, content-free proposal and identity records for
one exact ``active Primary -> active Secondary`` transition. Candidate discovery,
canonical publication, selectors, receipts, replay, and recovery remain owned by
their existing policy and lifecycle boundaries.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath

from relaylm.evidence.common import canonical_digest, sha256_hex

CONSOLIDATE_OPERATION_FAMILY = "consolidate"
CONSOLIDATE_AUTHORIZATION_CLASS = "relaymem_policy"
CONSOLIDATE_REASON_CATEGORY = "policy_authorized_consolidation"
CONSOLIDATE_POLICY_REVISION = "relaylm.subjective_mem_consolidation_policy.v1"
# The exact predecessor authorization kinds already selected by the shared
# predecessor authority: an ST-1 revision-1 formation decision, or the committed
# lifecycle transition that produced a later canonical revision.
CONSOLIDATE_PREDECESSOR_AUTHORIZATION_KINDS = frozenset(
    {"subjective_mem_decision", "subjective_mem_lifecycle_transition"}
)

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*\Z")


@dataclass(frozen=True)
class SubjectiveMemConsolidateBoundary:
    subject_class: str = "personal_subjective_memory"
    consolidation_authority_explicit: bool = True
    semantic_payload_preserved: bool = True
    scope_preserved: bool = True
    formation_snapshot_preserved: bool = True
    strength_preserved: bool = True
    memory_kind_preserved: bool = True
    lifecycle_state_preserved: bool = True
    retrieval_visibility_preserved: bool = True
    formation_stage_primary_to_secondary_only: bool = True
    model_generation_not_performed: bool = True
    content_rewrite_not_requested: bool = True
    relation_not_requested: bool = True
    supersession_not_requested: bool = True
    merge_not_requested: bool = True
    purge_not_requested: bool = True
    second_logical_memory_not_created: bool = True
    primary_mem_mutation_not_requested: bool = True
    candidate_discovery_not_performed: bool = True
    usage_event_not_written: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "subject_class": self.subject_class,
            "consolidation_authority_explicit": self.consolidation_authority_explicit,
            "semantic_payload_preserved": self.semantic_payload_preserved,
            "scope_preserved": self.scope_preserved,
            "formation_snapshot_preserved": self.formation_snapshot_preserved,
            "strength_preserved": self.strength_preserved,
            "memory_kind_preserved": self.memory_kind_preserved,
            "lifecycle_state_preserved": self.lifecycle_state_preserved,
            "retrieval_visibility_preserved": self.retrieval_visibility_preserved,
            "formation_stage_primary_to_secondary_only": self.formation_stage_primary_to_secondary_only,
            "model_generation_not_performed": self.model_generation_not_performed,
            "content_rewrite_not_requested": self.content_rewrite_not_requested,
            "relation_not_requested": self.relation_not_requested,
            "supersession_not_requested": self.supersession_not_requested,
            "merge_not_requested": self.merge_not_requested,
            "purge_not_requested": self.purge_not_requested,
            "second_logical_memory_not_created": self.second_logical_memory_not_created,
            "primary_mem_mutation_not_requested": self.primary_mem_mutation_not_requested,
            "candidate_discovery_not_performed": self.candidate_discovery_not_performed,
            "usage_event_not_written": self.usage_event_not_written,
        }


@dataclass(frozen=True)
class SubjectiveMemConsolidateProposal:
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
    expected_current_authorization_kind: str
    expected_current_authorization_id: str
    expected_current_authorization_digest: str
    expected_memory_kind: str
    expected_formation_stage: str
    expected_scope_binding_digest: str
    expected_formation_snapshot_digest: str
    expected_strength_digest: str
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
    boundary: SubjectiveMemConsolidateBoundary

    def to_digest_input(self) -> dict[str, object]:
        return {
            "operation_family": CONSOLIDATE_OPERATION_FAMILY,
            "operation_kind": "consolidate",
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
            "expected_current_authorization_kind": self.expected_current_authorization_kind,
            "expected_current_authorization_id": self.expected_current_authorization_id,
            "expected_current_authorization_digest": (
                self.expected_current_authorization_digest
            ),
            "expected_memory_kind": self.expected_memory_kind,
            "expected_formation_stage": self.expected_formation_stage,
            "expected_scope_binding_digest": self.expected_scope_binding_digest,
            "expected_formation_snapshot_digest": self.expected_formation_snapshot_digest,
            "expected_strength_digest": self.expected_strength_digest,
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
class SubjectiveMemConsolidateOperationIdentity:
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


def subjective_mem_consolidate_transition() -> tuple[str, str, str, str]:
    """Return the single LC-1E lifecycle and formation-stage direction."""

    return "active", "active", "primary", "secondary"


def validate_subjective_mem_consolidate_proposal(
    proposal: object,
) -> tuple[str, ...]:
    if type(proposal) is not SubjectiveMemConsolidateProposal:
        return ("subjective_mem_consolidate_proposal_invalid",)
    reasons = (
        *_consolidate_state_reasons(proposal),
        *_consolidate_authority_reasons(proposal),
        *_consolidate_shape_reasons(proposal),
    )
    return tuple(dict.fromkeys(reasons))


def _consolidate_state_reasons(
    proposal: SubjectiveMemConsolidateProposal,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if proposal.expected_lifecycle_state != "active":
        reasons.append("subjective_mem_consolidate_transition_direction_invalid")
    if proposal.expected_formation_stage != "primary":
        reasons.append("subjective_mem_consolidate_formation_stage_invalid")
    if proposal.expected_mutation_state != "none":
        reasons.append("subjective_mem_consolidate_mutation_state_invalid")
    if (
        type(proposal.expected_current_revision) is not int
        or proposal.expected_current_revision < 1
    ):
        reasons.append("subjective_mem_consolidate_current_revision_invalid")
    if proposal.expected_memory_kind not in {"episodic", "semantic"}:
        reasons.append("subjective_mem_consolidate_memory_kind_invalid")
    return tuple(reasons)


def _consolidate_authority_reasons(
    proposal: SubjectiveMemConsolidateProposal,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if proposal.authorization_class != CONSOLIDATE_AUTHORIZATION_CLASS:
        reasons.append("subjective_mem_consolidate_authorization_class_invalid")
    if proposal.reason_category != CONSOLIDATE_REASON_CATEGORY:
        reasons.append("subjective_mem_consolidate_reason_category_invalid")
    if proposal.policy_revision != CONSOLIDATE_POLICY_REVISION:
        reasons.append("subjective_mem_consolidate_policy_revision_invalid")
    if (
        proposal.expected_current_authorization_kind
        not in CONSOLIDATE_PREDECESSOR_AUTHORIZATION_KINDS
    ):
        reasons.append(
            "subjective_mem_consolidate_current_authorization_kind_invalid"
        )
    if (
        type(proposal.boundary) is not SubjectiveMemConsolidateBoundary
        or proposal.boundary.to_dict()
        != SubjectiveMemConsolidateBoundary().to_dict()
    ):
        reasons.append("subjective_mem_consolidate_boundary_invalid")
    return tuple(reasons)


def _consolidate_shape_reasons(
    proposal: SubjectiveMemConsolidateProposal,
) -> tuple[str, ...]:
    reasons: list[str] = []
    token_fields = (
        proposal.expected_memory_id,
        proposal.expected_page_id,
        proposal.expected_block_id,
        proposal.expected_current_selector_id,
        proposal.expected_current_receipt_id,
        proposal.expected_current_authorization_id,
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
        reasons.append("subjective_mem_consolidate_identifier_invalid")
    if not _safe_relative_path(proposal.expected_relative_path):
        reasons.append("subjective_mem_consolidate_relative_path_invalid")
    if not _digest(proposal.expected_page_digest, prefixed=True):
        reasons.append("subjective_mem_consolidate_page_digest_invalid")
    digest_fields = (
        proposal.expected_current_selector_digest,
        proposal.expected_current_receipt_digest,
        proposal.expected_current_authorization_digest,
        proposal.expected_scope_binding_digest,
        proposal.expected_formation_snapshot_digest,
        proposal.expected_strength_digest,
    )
    if any(not _digest(value) for value in digest_fields):
        reasons.append("subjective_mem_consolidate_digest_invalid")
    return tuple(reasons)


def derive_subjective_mem_consolidate_operation_identity(
    *,
    evidence_space_id: str,
    character_authority_digest: str,
    memory_id: str,
    operation_idempotency_key: str,
    proposal: SubjectiveMemConsolidateProposal,
    operation_time: str,
) -> tuple[SubjectiveMemConsolidateOperationIdentity | None, tuple[str, ...]]:
    reasons = list(validate_subjective_mem_consolidate_proposal(proposal))
    if type(proposal) is not SubjectiveMemConsolidateProposal:
        return None, tuple(reasons)
    if not _token(evidence_space_id) or not _token(memory_id):
        reasons.append("subjective_mem_consolidate_operation_identity_invalid")
    elif memory_id != proposal.expected_memory_id:
        reasons.append("subjective_mem_consolidate_memory_identity_mismatch")
    if not _digest(character_authority_digest):
        reasons.append("subjective_mem_consolidate_character_authority_digest_invalid")
    if not _token(operation_idempotency_key):
        reasons.append("subjective_mem_consolidate_idempotency_key_invalid")
    canonical_operation_time = _canonical_timestamp(operation_time)
    if canonical_operation_time is None:
        reasons.append("subjective_mem_consolidate_operation_time_invalid")
    if reasons:
        return None, tuple(dict.fromkeys(reasons))
    assert canonical_operation_time is not None

    key_digest = sha256_hex(operation_idempotency_key.encode("utf-8"))
    slot_material = "\0".join(
        (
            evidence_space_id,
            character_authority_digest,
            memory_id,
            CONSOLIDATE_OPERATION_FAMILY,
            key_digest,
        )
    )
    operation_slot_id = _opaque("smconsolidatekey", slot_material)
    input_digest = canonical_digest(
        {
            "proposal_input_digest": proposal.input_digest,
            "operation_time": canonical_operation_time,
        }
    )
    operation_id = _opaque(
        "smconsolidateop", operation_slot_id + "\0" + input_digest
    )
    return (
        SubjectiveMemConsolidateOperationIdentity(
            operation_slot_id=operation_slot_id,
            operation_id=operation_id,
            operation_key_digest=key_digest,
            input_digest=input_digest,
            transition_id=_opaque("smconsolidatetransition", operation_id),
            intent_id=_opaque("smconsolidateintent", operation_id),
            receipt_id=_opaque("smconsolidatereceipt", operation_id),
            result_id=_opaque("smconsolidateresult", operation_slot_id),
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
    "CONSOLIDATE_AUTHORIZATION_CLASS",
    "CONSOLIDATE_OPERATION_FAMILY",
    "CONSOLIDATE_POLICY_REVISION",
    "CONSOLIDATE_PREDECESSOR_AUTHORIZATION_KINDS",
    "CONSOLIDATE_REASON_CATEGORY",
    "SubjectiveMemConsolidateBoundary",
    "SubjectiveMemConsolidateOperationIdentity",
    "SubjectiveMemConsolidateProposal",
    "derive_subjective_mem_consolidate_operation_identity",
    "subjective_mem_consolidate_transition",
    "validate_subjective_mem_consolidate_proposal",
]
