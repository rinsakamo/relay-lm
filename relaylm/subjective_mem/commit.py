"""ST-1 content-free operations records for Subjective MEM publication."""
from __future__ import annotations

from dataclasses import dataclass

from relaylm.evidence.common import canonical_digest
from relaylm.subjective_mem.models import SubjectiveMemCurrentState

ST1_INTENT_SCHEMA = "relaylm.subjective_mem_st1_intent.v1"
ST1_RECEIPT_SCHEMA = "relaylm.subjective_mem_st1_commit_receipt.v1"
ST1_IDEMPOTENCY_SCHEMA = "relaylm.subjective_mem_st1_idempotency.v1"
ST1_MANIFEST_FINALIZATION_SCHEMA = (
    "relaylm.subjective_mem_st1_manifest_finalization.v1"
)
ST1_INTENT_FINALIZATION_SCHEMA = (
    "relaylm.subjective_mem_st1_intent_finalization.v1"
)
ST1_PROJECTION_STATE_SCHEMA = "relaylm.subjective_mem_st1_projection_state.v1"


@dataclass(frozen=True)
class SubjectiveMemPublicationIntent:
    intent_id: str
    finalization_id: str
    sm1_operation_slot_id: str
    sm1_operation_id: str
    sm1_operation_key_digest: str
    evidence_space_id: str
    character_id: str
    character_authority_digest: str
    workspace_authority_digest: str
    memory_id: str
    decision_id: str
    prepared_revision_record_id: str
    prepared_revision_digest: str
    prepared_manifest_id: str
    prepared_manifest_digest: str
    target_page_id: str
    target_relative_path: str
    memory_block_id: str
    memory_block_anchor: str
    pre_image_state: str
    pre_image_digest: str
    post_image_digest: str
    block_digest: str
    artifact_id: str
    artifact_digest: str
    page_schema: str
    renderer_revision: str
    partition_revision: str
    platform_revision: str
    prepared_at: str

    def _body(self) -> dict[str, object]:
        return {
            "schema": ST1_INTENT_SCHEMA,
            "intent_id": self.intent_id,
            "finalization_id": self.finalization_id,
            "operation_kind": "create",
            "sm1_operation_slot_id": self.sm1_operation_slot_id,
            "sm1_operation_id": self.sm1_operation_id,
            "sm1_operation_key_digest": self.sm1_operation_key_digest,
            "evidence_space_id": self.evidence_space_id,
            "character_id": self.character_id,
            "character_authority_digest": self.character_authority_digest,
            "workspace_authority_digest": self.workspace_authority_digest,
            "memory_ref": {"memory_id": self.memory_id, "memory_revision": 1},
            "decision_id": self.decision_id,
            "prepared_revision_record_id": self.prepared_revision_record_id,
            "prepared_revision_digest": self.prepared_revision_digest,
            "prepared_manifest_id": self.prepared_manifest_id,
            "prepared_manifest_digest": self.prepared_manifest_digest,
            "target_page_id": self.target_page_id,
            "target_relative_path": self.target_relative_path,
            "memory_block_id": self.memory_block_id,
            "memory_block_anchor": self.memory_block_anchor,
            "pre_image_state": self.pre_image_state,
            "pre_image_digest": self.pre_image_digest,
            "post_image_digest": self.post_image_digest,
            "block_digest": self.block_digest,
            "artifact_id": self.artifact_id,
            "artifact_digest": self.artifact_digest,
            "page_schema": self.page_schema,
            "renderer_revision": self.renderer_revision,
            "partition_revision": self.partition_revision,
            "platform_revision": self.platform_revision,
            "recovery_state": "prepared",
            "prepared_at": self.prepared_at,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "intent_digest": canonical_digest(body)}


@dataclass(frozen=True)
class SubjectiveMemCommitReceipt:
    receipt_id: str
    finalization_id: str
    intent_id: str
    intent_digest: str
    sm1_operation_slot_id: str
    sm1_operation_id: str
    sm1_operation_key_digest: str
    evidence_space_id: str
    character_id: str
    character_authority_digest: str
    workspace_authority_digest: str
    memory_id: str
    decision_id: str
    prepared_revision_record_id: str
    prepared_revision_digest: str
    prepared_manifest_id: str
    prepared_manifest_digest: str
    target_page_id: str
    target_relative_path: str
    memory_block_id: str
    memory_block_anchor: str
    pre_image_state: str
    pre_image_digest: str
    post_image_digest: str
    block_digest: str
    artifact_id: str
    artifact_digest: str
    page_schema: str
    renderer_revision: str
    partition_revision: str
    platform_revision: str
    current_state_digest: str
    finalized_at: str

    def _body(self) -> dict[str, object]:
        return {
            "schema": ST1_RECEIPT_SCHEMA,
            "receipt_id": self.receipt_id,
            "finalization_id": self.finalization_id,
            "intent_id": self.intent_id,
            "intent_digest": self.intent_digest,
            "operation_kind": "create",
            "operation_outcome": "committed",
            "sm1_operation_slot_id": self.sm1_operation_slot_id,
            "sm1_operation_id": self.sm1_operation_id,
            "sm1_operation_key_digest": self.sm1_operation_key_digest,
            "evidence_space_id": self.evidence_space_id,
            "character_id": self.character_id,
            "character_authority_digest": self.character_authority_digest,
            "workspace_authority_digest": self.workspace_authority_digest,
            "memory_ref": {"memory_id": self.memory_id, "memory_revision": 1},
            "create_precondition": {"from_revision_or_null": None},
            "decision_id": self.decision_id,
            "prepared_revision_record_id": self.prepared_revision_record_id,
            "prepared_revision_digest": self.prepared_revision_digest,
            "prepared_manifest_id": self.prepared_manifest_id,
            "prepared_manifest_digest": self.prepared_manifest_digest,
            "target_page_id": self.target_page_id,
            "target_relative_path": self.target_relative_path,
            "memory_block_id": self.memory_block_id,
            "memory_block_anchor": self.memory_block_anchor,
            "pre_image_state": self.pre_image_state,
            "pre_image_digest": self.pre_image_digest,
            "post_image_digest": self.post_image_digest,
            "block_digest": self.block_digest,
            "artifact_id": self.artifact_id,
            "artifact_digest": self.artifact_digest,
            "page_schema": self.page_schema,
            "renderer_revision": self.renderer_revision,
            "partition_revision": self.partition_revision,
            "platform_revision": self.platform_revision,
            "current_state_digest": self.current_state_digest,
            "projection_state": "rebuild_required",
            "ordinary_retrieval_wired": False,
            "finalized_at": self.finalized_at,
        }

    def to_dict(self) -> dict[str, object]:
        body = self._body()
        return {**body, "receipt_digest": canonical_digest(body)}


@dataclass(frozen=True)
class SubjectiveMemFinalizationRecords:
    current_state: SubjectiveMemCurrentState
    receipt: SubjectiveMemCommitReceipt
    idempotency: dict[str, object]
    manifest_finalization: dict[str, object]
    intent_finalization: dict[str, object]
    projection_state: dict[str, object]


def build_finalization_records(
    *,
    intent: SubjectiveMemPublicationIntent,
    receipt_id: str,
    finalized_at: str,
    current_state: SubjectiveMemCurrentState,
) -> SubjectiveMemFinalizationRecords:
    intent_raw = intent.to_dict()
    current_raw = current_state.to_dict()
    receipt = SubjectiveMemCommitReceipt(
        receipt_id=receipt_id,
        finalization_id=intent.finalization_id,
        intent_id=intent.intent_id,
        intent_digest=str(intent_raw["intent_digest"]),
        sm1_operation_slot_id=intent.sm1_operation_slot_id,
        sm1_operation_id=intent.sm1_operation_id,
        sm1_operation_key_digest=intent.sm1_operation_key_digest,
        evidence_space_id=intent.evidence_space_id,
        character_id=intent.character_id,
        character_authority_digest=intent.character_authority_digest,
        workspace_authority_digest=intent.workspace_authority_digest,
        memory_id=intent.memory_id,
        decision_id=intent.decision_id,
        prepared_revision_record_id=intent.prepared_revision_record_id,
        prepared_revision_digest=intent.prepared_revision_digest,
        prepared_manifest_id=intent.prepared_manifest_id,
        prepared_manifest_digest=intent.prepared_manifest_digest,
        target_page_id=intent.target_page_id,
        target_relative_path=intent.target_relative_path,
        memory_block_id=intent.memory_block_id,
        memory_block_anchor=intent.memory_block_anchor,
        pre_image_state=intent.pre_image_state,
        pre_image_digest=intent.pre_image_digest,
        post_image_digest=intent.post_image_digest,
        block_digest=intent.block_digest,
        artifact_id=intent.artifact_id,
        artifact_digest=intent.artifact_digest,
        page_schema=intent.page_schema,
        renderer_revision=intent.renderer_revision,
        partition_revision=intent.partition_revision,
        platform_revision=intent.platform_revision,
        current_state_digest=canonical_digest(current_raw),
        finalized_at=finalized_at,
    )
    receipt_raw = receipt.to_dict()
    idempotency_body = {
        "schema": ST1_IDEMPOTENCY_SCHEMA,
        "finalization_id": intent.finalization_id,
        "sm1_operation_id": intent.sm1_operation_id,
        "intent_id": intent.intent_id,
        "intent_digest": intent_raw["intent_digest"],
        "receipt_id": receipt_id,
        "receipt_digest": receipt_raw["receipt_digest"],
        "memory_ref": {"memory_id": intent.memory_id, "memory_revision": 1},
        "target_page_id": intent.target_page_id,
        "memory_block_id": intent.memory_block_id,
        "post_image_digest": intent.post_image_digest,
        "status": "finalized",
        "finalized_at": finalized_at,
    }
    manifest_body = {
        "schema": ST1_MANIFEST_FINALIZATION_SCHEMA,
        "finalization_id": intent.finalization_id,
        "prepared_manifest_id": intent.prepared_manifest_id,
        "prepared_manifest_digest": intent.prepared_manifest_digest,
        "receipt_id": receipt_id,
        "state": "consumed_finalized",
        "finalized_at": finalized_at,
    }
    intent_finalization_body = {
        "schema": ST1_INTENT_FINALIZATION_SCHEMA,
        "finalization_id": intent.finalization_id,
        "intent_id": intent.intent_id,
        "intent_digest": intent_raw["intent_digest"],
        "receipt_id": receipt_id,
        "state": "finalized",
        "finalized_at": finalized_at,
    }
    projection_body = {
        "schema": ST1_PROJECTION_STATE_SCHEMA,
        "finalization_id": intent.finalization_id,
        "memory_ref": {"memory_id": intent.memory_id, "memory_revision": 1},
        "target_page_id": intent.target_page_id,
        "memory_block_id": intent.memory_block_id,
        "post_image_digest": intent.post_image_digest,
        "projection_state": "rebuild_required",
        "ordinary_retrieval_wired": False,
        "updated_at": finalized_at,
    }
    return SubjectiveMemFinalizationRecords(
        current_state=current_state,
        receipt=receipt,
        idempotency={**idempotency_body, "result_digest": canonical_digest(idempotency_body)},
        manifest_finalization={
            **manifest_body,
            "finalization_digest": canonical_digest(manifest_body),
        },
        intent_finalization={
            **intent_finalization_body,
            "finalization_digest": canonical_digest(intent_finalization_body),
        },
        projection_state={
            **projection_body,
            "projection_state_digest": canonical_digest(projection_body),
        },
    )


__all__ = [
    "ST1_IDEMPOTENCY_SCHEMA",
    "ST1_INTENT_FINALIZATION_SCHEMA",
    "ST1_INTENT_SCHEMA",
    "ST1_MANIFEST_FINALIZATION_SCHEMA",
    "ST1_PROJECTION_STATE_SCHEMA",
    "ST1_RECEIPT_SCHEMA",
    "SubjectiveMemCommitReceipt",
    "SubjectiveMemFinalizationRecords",
    "SubjectiveMemPublicationIntent",
    "build_finalization_records",
]
