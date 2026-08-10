"""LC-1B storage-neutral Subjective MEM Forget records.

Forget preserves the complete semantic payload of one exact current active
revision while appending an immutable hidden successor. The durable
anti-reformation tombstone is content-free: it stores only bounded identity,
digest, lifecycle, authorization, and receipt lineage.
"""
from __future__ import annotations

from dataclasses import dataclass

from relaylm.evidence.common import canonical_digest

FORGET_TOMBSTONE_SCHEMA = "relaylm.subjective_mem_forget_tombstone.v1"
FORGET_TOMBSTONE_STATE_SCHEMA = "relaylm.subjective_mem_forget_tombstone_state.v1"
FORGET_REASON_CATEGORIES = frozenset(
    {"user_requested_forget", "operator_requested_forget"}
)


@dataclass(frozen=True)
class SubjectiveMemForgetBoundary:
    subject_class: str = "personal_subjective_memory"
    forget_authority_explicit: bool = True
    semantic_payload_preserved: bool = True
    scope_preserved: bool = True
    formation_snapshot_preserved: bool = True
    product_knowledge_excluded: bool = True
    model_generation_not_performed: bool = True
    purge_not_requested: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "subject_class": self.subject_class,
            "forget_authority_explicit": self.forget_authority_explicit,
            "semantic_payload_preserved": self.semantic_payload_preserved,
            "scope_preserved": self.scope_preserved,
            "formation_snapshot_preserved": self.formation_snapshot_preserved,
            "product_knowledge_excluded": self.product_knowledge_excluded,
            "model_generation_not_performed": self.model_generation_not_performed,
            "purge_not_requested": self.purge_not_requested,
        }


@dataclass(frozen=True)
class SubjectiveMemForgetProposal:
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
    boundary: SubjectiveMemForgetBoundary

    def to_digest_input(self) -> dict[str, object]:
        return {
            "operation": "forget",
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
class SubjectiveMemForgetTombstone:
    tombstone_id: str
    evidence_space_id: str
    character_id: str
    memory_id: str
    source_revision: int
    hidden_revision: int
    formation_stage: str
    transition_id: str
    transition_digest: str
    receipt_id: str
    semantic_identity_digest: str
    scope_binding_digest: str
    authorization_class: str
    authorization_id: str
    reason_category: str
    policy_revision: str
    effective_at: str

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": FORGET_TOMBSTONE_SCHEMA,
            "tombstone_id": self.tombstone_id,
            "evidence_space_id": self.evidence_space_id,
            "character_id": self.character_id,
            "memory_id": self.memory_id,
            "source_revision": self.source_revision,
            "hidden_revision": self.hidden_revision,
            "formation_stage": self.formation_stage,
            "transition_id": self.transition_id,
            "transition_digest": self.transition_digest,
            "receipt_id": self.receipt_id,
            "semantic_identity_digest": self.semantic_identity_digest,
            "scope_binding_digest": self.scope_binding_digest,
            "authorization_class": self.authorization_class,
            "authorization_id": self.authorization_id,
            "reason_category": self.reason_category,
            "policy_revision": self.policy_revision,
            "effective_at": self.effective_at,
            "effective": True,
            "content_free": True,
        }
        return {**body, "tombstone_digest": canonical_digest(body)}


__all__ = [
    "FORGET_REASON_CATEGORIES",
    "FORGET_TOMBSTONE_SCHEMA",
    "FORGET_TOMBSTONE_STATE_SCHEMA",
    "SubjectiveMemForgetBoundary",
    "SubjectiveMemForgetProposal",
    "SubjectiveMemForgetTombstone",
]
