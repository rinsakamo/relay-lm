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
from relaylm.evidence_common import canonical_digest, sha256_hex
from relaylm.subjective_mem import (
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCharacterAuthority,
    SubjectiveMemCurrentState,
    SubjectiveMemRevision,
)
from relaylm.subjective_mem_lifecycle import (
    LIFECYCLE_INTENT_FINALIZATION_SCHEMA,
    LIFECYCLE_INTENT_SCHEMA,
    LIFECYCLE_RECEIPT_SCHEMA,
    LIFECYCLE_RESULT_SCHEMA,
    LIFECYCLE_TRANSITION_SCHEMA,
)
from relaylm.subjective_mem_lifecycle_engine import (
    LifecycleFinalRecordsWithBindings,
    LifecyclePublicationPlan,
    LogBinding,
    RecordBinding,
    final_lifecycle_state,
    validate_lifecycle_plan,
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
from relaylm.subjective_mem_tombstone_release import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND,
    build_subjective_mem_forget_tombstone_release_authority,
)

_FORGET_RECEIPT_KIND = "subjective_mem_lifecycle_receipt"
_FORGET_TOMBSTONE_KIND = "subjective_mem_forget_tombstone"


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


def build_subjective_mem_restore_final_records(
    *,
    plan: LifecyclePublicationPlan,
    final_state: SubjectiveMemCurrentState,
) -> tuple[LifecycleFinalRecordsWithBindings | None, tuple[str, ...]]:
    """Compose the complete deterministic final payload for one Restore plan.

    The payload is write-free: it only derives records from the already valid
    plan, its bound Forget authority, and the exact final active selector.
    """

    if (
        type(plan) is not LifecyclePublicationPlan
        or validate_lifecycle_plan(plan) != ()
        or plan.operation_kind != "restore"
    ):
        return None, ("subjective_mem_restore_final_plan_not_exact",)
    if (
        type(final_state) is not SubjectiveMemCurrentState
        or final_state != final_lifecycle_state(plan)
    ):
        return None, ("subjective_mem_restore_final_state_not_exact",)
    intent = dict(plan.prepared_intent)
    forget_receipt, tombstone, reasons = _bound_forget_authority(plan, intent)
    if forget_receipt is None or tombstone is None:
        return None, reasons
    transition = _restore_transition(plan, intent)
    receipt = _restore_receipt(plan, intent, final_state)
    authority, reasons = build_subjective_mem_forget_tombstone_release_authority(
        release_id=str(intent["release_id"]),
        tombstone=tombstone,
        forget_receipt=forget_receipt,
        restore_transition=transition,
        restore_receipt=receipt,
        authorization_class=str(intent["authorization_class"]),
        authorization_id=str(intent["authorization_id"]),
        reason_category=str(intent["reason_category"]),
        policy_revision=str(intent["policy_revision"]),
        released_at=plan.prepared_at,
    )
    if authority is None:
        return None, reasons
    return LifecycleFinalRecordsWithBindings(
        transition=transition,
        receipt=receipt,
        finalization=_restore_finalization(plan, intent, receipt),
        result=_restore_result(plan, intent, receipt, final_state),
        projection=_restore_projection(plan),
        additional_records=(
            (
                SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND,
                str(intent["release_id"]),
                authority.release,
            ),
        ),
        additional_logs=(
            (
                SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
                str(intent["forget_tombstone_id"]),
                (authority.state,),
            ),
        ),
    ), ()


def _bound_forget_authority(
    plan: LifecyclePublicationPlan, intent: dict[str, object]
) -> tuple[dict[str, object] | None, dict[str, object] | None, tuple[str, ...]]:
    """Locate the exact single bound Forget receipt and immutable tombstone."""

    receipts = [
        body
        for kind, record_id, body in plan.record_bindings
        if kind == _FORGET_RECEIPT_KIND and record_id == intent["current_receipt_id"]
    ]
    tombstones = [
        body
        for kind, record_id, body in plan.record_bindings
        if kind == _FORGET_TOMBSTONE_KIND
        and record_id == intent["forget_tombstone_id"]
    ]
    if len(receipts) != 1 or len(tombstones) != 1:
        return None, None, ("subjective_mem_restore_final_forget_authority_not_bound",)
    receipt, tombstone = receipts[0], tombstones[0]
    if (
        receipt.get("operation_kind") != "forget"
        or receipt.get("transition_id") != intent["forget_transition_id"]
        or receipt.get("tombstone_id") != intent["forget_tombstone_id"]
        or receipt.get("tombstone_digest") != intent["forget_tombstone_digest"]
        or receipt.get("semantic_identity_digest")
        != intent["semantic_identity_digest"]
        or tombstone.get("tombstone_digest") != intent["forget_tombstone_digest"]
        or tombstone.get("memory_id") != intent["memory_id"]
        or tombstone.get("hidden_revision") != intent["from_revision"]
        or tombstone.get("semantic_identity_digest")
        != intent["semantic_identity_digest"]
    ):
        return None, None, ("subjective_mem_restore_final_forget_authority_not_exact",)
    return receipt, tombstone, ()


def _restore_transition(
    plan: LifecyclePublicationPlan, intent: dict[str, object]
) -> dict[str, object]:
    return {
        "schema": LIFECYCLE_TRANSITION_SCHEMA,
        "transition_id": plan.transition_id,
        "character_id": plan.character_id,
        "memory_id": plan.memory_id,
        "from_revision": plan.from_revision,
        "to_revision": plan.to_revision,
        "operation": "restore",
        "from_lifecycle_state": "hidden",
        "to_lifecycle_state": "active",
        "from_formation_stage": intent["formation_stage"],
        "to_formation_stage": intent["formation_stage"],
        "authorized_by": intent["authorization_class"],
        "committed_at": plan.prepared_at,
    }


def _restore_receipt(
    plan: LifecyclePublicationPlan,
    intent: dict[str, object],
    final_state: SubjectiveMemCurrentState,
) -> dict[str, object]:
    body: dict[str, object] = {
        "schema": LIFECYCLE_RECEIPT_SCHEMA,
        "receipt_id": plan.receipt_id,
        "intent_id": plan.intent_id,
        "intent_digest": canonical_digest(intent),
        "operation_id": plan.operation_id,
        "operation_kind": "restore",
        "operation_outcome": "committed",
        "input_digest": plan.input_digest,
        "evidence_space_id": plan.evidence_space_id,
        "character_id": plan.character_id,
        "memory_ref": {
            "memory_id": plan.memory_id,
            "memory_revision": plan.to_revision,
        },
        "predecessor_revision": plan.from_revision,
        "transition_id": plan.transition_id,
        "release_id": intent["release_id"],
        "tombstone_id": intent["forget_tombstone_id"],
        "tombstone_digest": intent["forget_tombstone_digest"],
        "semantic_identity_digest": intent["semantic_identity_digest"],
        "authorization_class": intent["authorization_class"],
        "authorization_id": intent["authorization_id"],
        "reason_category": intent["reason_category"],
        "policy_revision": intent["policy_revision"],
        "revision_schema": intent["revision_schema"],
        "page_schema": intent["page_schema"],
        "block_schema": intent["block_schema"],
        "renderer_revision": intent["renderer_revision"],
        "partition_revision": intent["partition_revision"],
        "platform_revision": intent["platform_revision"],
        "page_id": plan.page_id,
        "successor_block_id": plan.successor_block_id,
        "pre_image_digest": plan.pre_image_digest,
        "post_image_digest": plan.post_image_digest,
        "successor_revision_digest": plan.successor_revision_digest,
        "current_state_digest": canonical_digest(final_state.to_dict()),
        "projection_state": "rebuild_required",
        "ordinary_retrieval_wired": False,
        "finalized_at": plan.prepared_at,
    }
    return {**body, "receipt_digest": canonical_digest(body)}


def _restore_finalization(
    plan: LifecyclePublicationPlan,
    intent: dict[str, object],
    receipt: dict[str, object],
) -> dict[str, object]:
    return {
        "schema": LIFECYCLE_INTENT_FINALIZATION_SCHEMA,
        "finalization_id": _opaque("smlintentfin", plan.intent_id),
        "intent_id": plan.intent_id,
        "intent_digest": canonical_digest(intent),
        "receipt_id": plan.receipt_id,
        "receipt_digest": receipt["receipt_digest"],
        "status": "finalized",
        "finalized_at": plan.prepared_at,
    }


def _restore_result(
    plan: LifecyclePublicationPlan,
    intent: dict[str, object],
    receipt: dict[str, object],
    final_state: SubjectiveMemCurrentState,
) -> dict[str, object]:
    body: dict[str, object] = {
        "schema": LIFECYCLE_RESULT_SCHEMA,
        "result_id": plan.result_id,
        "operation_slot_id": plan.operation_slot_id,
        "operation_id": plan.operation_id,
        "operation_kind": "restore",
        "input_digest": plan.input_digest,
        "receipt_id": plan.receipt_id,
        "receipt_digest": receipt["receipt_digest"],
        "transition_id": plan.transition_id,
        "release_id": intent["release_id"],
        "memory_id": plan.memory_id,
        "from_revision": plan.from_revision,
        "to_revision": plan.to_revision,
        "page_id": plan.page_id,
        "post_image_digest": plan.post_image_digest,
        "current_selector_id": plan.selector_id,
        "current_state_digest": canonical_digest(final_state.to_dict()),
        "status": "committed",
        "finalized_at": plan.prepared_at,
    }
    return {**body, "result_digest": canonical_digest(body)}


def _restore_projection(plan: LifecyclePublicationPlan) -> dict[str, object]:
    return {
        "schema": "relaylm.subjective_mem_projection_state.v1",
        "memory_id": plan.memory_id,
        "memory_revision": plan.to_revision,
        "projection_state": "rebuild_required",
        "ordinary_retrieval_wired": False,
        "updated_at": plan.prepared_at,
    }


def _opaque(prefix: str, value: str) -> str:
    return f"{prefix}_{sha256_hex(value.encode('utf-8'))}"


# NOTE: ``build_subjective_mem_restore_final_records`` is public API but is not
# re-exported yet: the Restore runtime tests pin this ``__all__`` to the plan
# builders, and that file is outside this slice's allowed paths.
__all__ = [
    "SubjectiveMemRestorePlanInputs",
    "build_subjective_mem_restore_lifecycle_plan",
    "build_subjective_mem_restore_prepared_intent",
]
