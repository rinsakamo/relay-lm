"""Deterministic Restore lifecycle plan composition.

This module owns only the write-free composition of the content-free prepared
intent and the immutable ``LifecyclePublicationPlan`` for one already validated
``hidden N -> active N+1`` Restore operation. It performs no filesystem or
Evidence-store access, holds no runtime state, and is not a second Restore
owner: request validation, authority loading, and orchestration remain in
``relaylm.subjective_mem_restore_runtime``, while reservation, publication, and
finalization remain owned by the shared lifecycle engine.
"""
from __future__ import annotations

from dataclasses import dataclass

from relaylm._subjective_mem_commit_io import PLATFORM_REVISION
from relaylm.evidence_common import canonical_digest
from relaylm.subjective_mem import (
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCharacterAuthority,
    SubjectiveMemCurrentState,
    SubjectiveMemRevision,
)
from relaylm.subjective_mem_lifecycle import LIFECYCLE_INTENT_SCHEMA
from relaylm.subjective_mem_lifecycle_engine import (
    LifecyclePublicationPlan,
    LogBinding,
    RecordBinding,
)
from relaylm.subjective_mem_markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    SubjectiveMemPagePlan,
)
from relaylm.subjective_mem_restore import (
    SubjectiveMemRestoreOperationIdentity,
    SubjectiveMemRestoreProposal,
)


@dataclass(frozen=True)
class SubjectiveMemRestorePlanInputs:
    """Exact already-validated values one Restore publication plan is built from."""

    evidence_space_id: str
    character_authority: SubjectiveMemCharacterAuthority
    workspace_root: str
    workspace_authority_digest: str
    proposal: SubjectiveMemRestoreProposal
    identity: SubjectiveMemRestoreOperationIdentity
    predecessor: SubjectiveMemRevision
    successor: SubjectiveMemRevision
    current_state: SubjectiveMemCurrentState
    prepared_state: SubjectiveMemCurrentState
    page: SubjectiveMemPagePlan
    record_bindings: tuple[RecordBinding, ...]
    log_bindings: tuple[LogBinding, ...]
    prepared_at: str


def build_subjective_mem_restore_lifecycle_plan(
    inputs: SubjectiveMemRestorePlanInputs,
) -> LifecyclePublicationPlan:
    """Compose one exact, deterministic Restore publication plan."""

    proposal, identity, page = inputs.proposal, inputs.identity, inputs.page
    predecessor, successor = inputs.predecessor, inputs.successor
    return LifecyclePublicationPlan(
        evidence_space_id=inputs.evidence_space_id,
        character_id=inputs.character_authority.character_id,
        workspace_root=inputs.workspace_root,
        operation_kind="restore",
        operation_slot_id=identity.operation_slot_id,
        operation_id=identity.operation_id,
        operation_key_digest=identity.operation_key_digest,
        input_digest=identity.input_digest,
        intent_id=identity.intent_id,
        transition_id=identity.transition_id,
        receipt_id=identity.receipt_id,
        result_id=identity.result_id,
        memory_id=predecessor.memory_id,
        from_revision=predecessor.memory_revision,
        to_revision=successor.memory_revision,
        to_lifecycle_state="active",
        selector_id=proposal.expected_current_selector_id,
        prepared_state=inputs.prepared_state,
        page_id=page.page_id,
        page_partition=page.partition,
        page_relative_path=proposal.expected_relative_path,
        pre_image_state=page.pre_image_state,
        pre_image_digest=page.pre_image_digest,
        post_image_digest=page.post_image_digest,
        predecessor_revision_digest=canonical_digest(predecessor.to_dict()),
        successor_revision_digest=canonical_digest(successor.to_dict()),
        successor_block_id=page.block_id,
        artifact_id=page.artifact_id,
        prepared_intent=build_subjective_mem_restore_prepared_intent(inputs),
        prepared_at=inputs.prepared_at,
        record_bindings=inputs.record_bindings,
        log_bindings=inputs.log_bindings,
        current_state=inputs.current_state,
    )


def build_subjective_mem_restore_prepared_intent(
    inputs: SubjectiveMemRestorePlanInputs,
) -> dict[str, object]:
    """Bind the engine plan fields and the operation-owned Restore lineage."""

    proposal, identity, page = inputs.proposal, inputs.identity, inputs.page
    predecessor, successor = inputs.predecessor, inputs.successor
    return {
        "schema": LIFECYCLE_INTENT_SCHEMA,
        "intent_id": identity.intent_id,
        "operation_slot_id": identity.operation_slot_id,
        "operation_id": identity.operation_id,
        "operation_kind": "restore",
        "operation_key_digest": identity.operation_key_digest,
        "input_digest": identity.input_digest,
        "evidence_space_id": inputs.evidence_space_id,
        "character_id": inputs.character_authority.character_id,
        "character_authority_digest": canonical_digest(
            inputs.character_authority.to_dict()
        ),
        "workspace_authority_digest": inputs.workspace_authority_digest,
        "memory_id": predecessor.memory_id,
        "memory_kind": predecessor.memory_kind,
        "formation_stage": predecessor.formation_stage,
        "scope_binding_digest": proposal.expected_scope_binding_digest,
        "formation_snapshot_digest": proposal.expected_formation_snapshot_digest,
        "semantic_identity_digest": proposal.expected_semantic_identity_digest,
        "from_revision": predecessor.memory_revision,
        "from_lifecycle_state": "hidden",
        "to_revision": successor.memory_revision,
        "to_lifecycle_state": "active",
        "predecessor_revision_digest": canonical_digest(predecessor.to_dict()),
        "predecessor_block_id": proposal.expected_block_id,
        "predecessor_authorization_kind": predecessor.authorization_kind,
        "predecessor_authorization_id": predecessor.authorization_id,
        "successor_revision_digest": canonical_digest(successor.to_dict()),
        "transition_id": identity.transition_id,
        "receipt_id": identity.receipt_id,
        "release_id": identity.release_id,
        "result_id": identity.result_id,
        "forget_transition_id": proposal.expected_forget_transition_id,
        "forget_transition_digest": proposal.expected_forget_transition_digest,
        "forget_tombstone_id": proposal.expected_forget_tombstone_id,
        "forget_tombstone_digest": proposal.expected_forget_tombstone_digest,
        "authorization_class": proposal.authorization_class,
        "authorization_id": proposal.authorization_id,
        "reason_category": proposal.reason_category,
        "policy_revision": proposal.policy_revision,
        "current_receipt_id": proposal.expected_current_receipt_id,
        "current_receipt_digest": proposal.expected_current_receipt_digest,
        "current_selector_id": proposal.expected_current_selector_id,
        "current_selector_digest": proposal.expected_current_selector_digest,
        "prepared_current_state_digest": canonical_digest(
            inputs.prepared_state.to_dict()
        ),
        "page_id": page.page_id,
        "partition": page.partition,
        "successor_block_id": page.block_id,
        "artifact_id": page.artifact_id,
        "successor_block_digest": page.block_digest,
        "artifact_digest": page.post_image_digest,
        "pre_image_state": page.pre_image_state,
        "pre_image_digest": page.pre_image_digest,
        "post_image_digest": page.post_image_digest,
        "revision_schema": SUBJECTIVE_MEM_REVISION_SCHEMA,
        "page_schema": PAGE_SCHEMA,
        "block_schema": LIFECYCLE_BLOCK_SCHEMA,
        "renderer_revision": RENDERER_REVISION,
        "partition_revision": PAGE_PARTITION_REVISION,
        "platform_revision": PLATFORM_REVISION,
        "prepared_at": inputs.prepared_at,
        "recovery_state": "prepared",
    }


__all__ = [
    "SubjectiveMemRestorePlanInputs",
    "build_subjective_mem_restore_lifecycle_plan",
    "build_subjective_mem_restore_prepared_intent",
]
