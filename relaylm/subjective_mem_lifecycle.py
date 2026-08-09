"""LC-1 storage-neutral lifecycle records.

Only bounded, content-free operation records belong in the durable operations
store.  Canonical prose remains exclusively in Character Workspace Markdown
and its private immutable transaction artifact.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from relaylm.evidence.common import canonical_digest
from relaylm.shared_assessment import SharedAssessmentCurrentState, SharedAssessmentRevision
from relaylm.subjective_mem import SubjectiveMemStrength

LIFECYCLE_TRANSITION_SCHEMA = "relaylm.subjective_mem_lifecycle_transition.v1"
LIFECYCLE_INTENT_SCHEMA = "relaylm.subjective_mem_lifecycle_intent.v1"
LIFECYCLE_RECEIPT_SCHEMA = "relaylm.subjective_mem_lifecycle_receipt.v1"
LIFECYCLE_CLAIM_SCHEMA = "relaylm.subjective_mem_lifecycle_claim.v1"
LIFECYCLE_RESULT_SCHEMA = "relaylm.subjective_mem_lifecycle_idempotency_result.v1"
LIFECYCLE_INTENT_FINALIZATION_SCHEMA = "relaylm.subjective_mem_lifecycle_intent_finalization.v1"
LIFECYCLE_POLICY_REVISION = "relaylm.subjective_mem_lifecycle_policy.v1"
CORRECT_REASON_CATEGORIES = frozenset(
    {"user_reported_inaccuracy", "operator_grounded_correction"}
)


@dataclass(frozen=True)
class SubjectiveMemCorrectionBoundary:
    subject_class: str = "personal_subjective_memory"
    correction_authority_explicit: bool = True
    evidence_support_exact: bool = True
    uncertainty_preserved: bool = True
    temporal_qualification_preserved: bool = True
    character_scope_kind_stage_preserved: bool = True
    formation_snapshot_preserved: bool = True
    product_knowledge_excluded: bool = True
    model_generation_not_performed: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "subject_class": self.subject_class,
            "correction_authority_explicit": self.correction_authority_explicit,
            "evidence_support_exact": self.evidence_support_exact,
            "uncertainty_preserved": self.uncertainty_preserved,
            "temporal_qualification_preserved": self.temporal_qualification_preserved,
            "character_scope_kind_stage_preserved": self.character_scope_kind_stage_preserved,
            "formation_snapshot_preserved": self.formation_snapshot_preserved,
            "product_knowledge_excluded": self.product_knowledge_excluded,
            "model_generation_not_performed": self.model_generation_not_performed,
        }


@dataclass(frozen=True)
class SubjectiveMemCorrectProposal:
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
    assessment_revision: SharedAssessmentRevision = field(repr=False)
    assessment_current_state: SharedAssessmentCurrentState
    corrected_grounded_content: str = field(repr=False)
    corrected_subjective_meaning: str = field(repr=False)
    corrected_strength: SubjectiveMemStrength
    authorization_class: str
    authorization_id: str
    reason_category: str
    policy_revision: str
    boundary: SubjectiveMemCorrectionBoundary

    def to_digest_input(self) -> dict[str, object]:
        return {
            "operation": "correct",
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
            "assessment_revision": self.assessment_revision.to_dict(),
            "assessment_current_state": self.assessment_current_state.to_dict(),
            "corrected_grounded_content": self.corrected_grounded_content,
            "corrected_subjective_meaning": self.corrected_subjective_meaning,
            "corrected_strength": self.corrected_strength.to_dict(),
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
class SubjectiveMemLifecycleTransition:
    transition_id: str
    character_id: str
    memory_id: str
    from_revision: int
    to_revision: int
    operation: str
    from_lifecycle_state: str
    to_lifecycle_state: str
    from_formation_stage: str
    to_formation_stage: str
    authorized_by: str
    committed_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": LIFECYCLE_TRANSITION_SCHEMA,
            "transition_id": self.transition_id,
            "character_id": self.character_id,
            "memory_id": self.memory_id,
            "from_revision": self.from_revision,
            "to_revision": self.to_revision,
            "operation": self.operation,
            "from_lifecycle_state": self.from_lifecycle_state,
            "to_lifecycle_state": self.to_lifecycle_state,
            "from_formation_stage": self.from_formation_stage,
            "to_formation_stage": self.to_formation_stage,
            "authorized_by": self.authorized_by,
            "committed_at": self.committed_at,
        }


__all__ = [
    "CORRECT_REASON_CATEGORIES",
    "LIFECYCLE_CLAIM_SCHEMA",
    "LIFECYCLE_INTENT_FINALIZATION_SCHEMA",
    "LIFECYCLE_INTENT_SCHEMA",
    "LIFECYCLE_POLICY_REVISION",
    "LIFECYCLE_RECEIPT_SCHEMA",
    "LIFECYCLE_RESULT_SCHEMA",
    "LIFECYCLE_TRANSITION_SCHEMA",
    "SubjectiveMemCorrectProposal",
    "SubjectiveMemCorrectionBoundary",
    "SubjectiveMemLifecycleTransition",
]
