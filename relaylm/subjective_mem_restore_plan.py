"""Deterministic Restore lifecycle plan composition and operation-pure checks.

This module owns the write-free composition of the content-free prepared
intent, the immutable ``LifecyclePublicationPlan``, and the final records for
one ``hidden N -> active N+1`` Restore operation, together with the
operation-pure exactness predicates those payloads depend on. It performs no
filesystem, transaction, or Evidence-store access, holds no runtime state, and
is not a second Restore owner: request handling, durable authority loading, and
orchestration remain in ``relaylm.subjective_mem_restore_runtime``, while
reservation, publication, and finalization remain owned by the shared engine.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from relaylm.subjective_mem.commit_io import PLATFORM_REVISION
from relaylm.evidence.common import canonical_digest, sha256_hex
from relaylm.subjective_mem.models import (
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCharacterAuthority,
    SubjectiveMemCurrentState,
    SubjectiveMemRevision,
)
from relaylm.subjective_mem_lifecycle_authority import (
    SubjectiveMemPredecessorExpectation,
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
from relaylm.subjective_mem.markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    SubjectiveMemPagePlan,
    plan_subjective_mem_revision_successor,
)
from relaylm.subjective_mem_reformation import (
    subjective_mem_semantic_identity_digest,
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


@dataclass(frozen=True)
class SubjectiveMemRestorePreparedOperation:
    """One deterministic fresh Restore publication, composed but not reserved."""

    current: SubjectiveMemCurrentState
    prepared: SubjectiveMemCurrentState
    predecessor: SubjectiveMemRevision
    successor: SubjectiveMemRevision
    page: SubjectiveMemPagePlan
    plan: LifecyclePublicationPlan


def build_subjective_mem_restore_prepared_operation(
    *,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    proposal: SubjectiveMemRestoreProposal,
    identity: SubjectiveMemRestoreOperationIdentity,
    predecessor: SubjectiveMemRevision,
    current_state: SubjectiveMemCurrentState,
    page_bytes: bytes,
    record_bindings: tuple[RecordBinding, ...],
    log_bindings: tuple[LogBinding, ...],
    prepared_at: str,
) -> tuple[SubjectiveMemRestorePreparedOperation | None, tuple[str, ...]]:
    """Compose the exact active successor and reserved plan for one fresh Restore."""

    successor = replace(
        predecessor, decision_id=identity.transition_id, created_at=prepared_at,
        memory_revision=predecessor.memory_revision + 1, lifecycle_state="active",
        retrieval_visible=True, authorization_kind="lifecycle_transition",
        predecessor_revision_or_null=predecessor.memory_revision,
    )
    planned = plan_subjective_mem_revision_successor(
        predecessor=predecessor, successor=successor, existing_bytes=page_bytes
    )
    if planned.plan is None:
        return None, planned.reasons
    # The hidden selector is fenced by reserving it: only the mutation state and
    # the exact operation time change, and it stays retrieval-ineligible.
    prepared = replace(
        current_state, mutation_state="prepared", retrieval_eligible=False,
        updated_at=prepared_at,
    )
    plan = build_subjective_mem_restore_lifecycle_plan(
        SubjectiveMemRestorePlanInputs(
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            workspace_root=workspace_root,
            workspace_authority_digest=(
                subjective_mem_restore_workspace_authority_digest(
                    workspace_root, character_authority
                )
            ),
            proposal=proposal, identity=identity, predecessor=predecessor,
            successor=successor, current_state=current_state,
            prepared_state=prepared, page=planned.plan,
            record_bindings=record_bindings, log_bindings=log_bindings,
            prepared_at=prepared_at,
        )
    )
    return SubjectiveMemRestorePreparedOperation(
        current=current_state, prepared=prepared, predecessor=predecessor,
        successor=successor, page=planned.plan, plan=plan,
    ), ()


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
        "evidence_space_descriptor_digest": _binding_digest(
            inputs.record_bindings, "evidence_space_descriptor"
        ),
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


def _binding_digest(bindings: tuple[RecordBinding, ...], kind: str) -> str:
    """Digest the exact bound record of one kind, or empty when it is absent.

    An empty digest can never match a durable record, so an unbound kind fails
    closed when the replay reconstruction proves this intent against the store.
    """

    for record_kind, _record_id, body in bindings:
        if record_kind == kind:
            return canonical_digest(body)
    return ""


def subjective_mem_restore_predecessor_expectation(
    proposal: SubjectiveMemRestoreProposal,
) -> SubjectiveMemPredecessorExpectation:
    return SubjectiveMemPredecessorExpectation(
        proposal.expected_current_receipt_id,
        proposal.expected_current_receipt_digest,
        proposal.expected_current_selector_digest,
        proposal.expected_page_id,
        proposal.expected_block_id,
        proposal.expected_page_digest,
        proposal.expected_revision_schema,
        proposal.expected_page_schema,
        proposal.expected_block_schema,
        proposal.expected_renderer_revision,
        proposal.expected_partition_revision,
        proposal.expected_platform_revision,
    )


def subjective_mem_restore_tombstone_exact(
    raw: object, space: str, character_id: str,
    predecessor: SubjectiveMemRevision, proposal: SubjectiveMemRestoreProposal,
) -> bool:
    if not isinstance(raw, dict):
        return False
    body = {key: value for key, value in raw.items() if key != "tombstone_digest"}
    return (
        raw.get("tombstone_id") == proposal.expected_forget_tombstone_id
        and raw.get("tombstone_digest") == proposal.expected_forget_tombstone_digest
        and canonical_digest(body) == proposal.expected_forget_tombstone_digest
        and raw.get("evidence_space_id") == space
        and raw.get("character_id") == character_id
        and raw.get("memory_id") == predecessor.memory_id
        and raw.get("hidden_revision") == predecessor.memory_revision
        and raw.get("transition_id") == proposal.expected_forget_transition_id
        and raw.get("receipt_id") == proposal.expected_current_receipt_id
        and raw.get("semantic_identity_digest")
        == proposal.expected_semantic_identity_digest
        and raw.get("effective") is True and raw.get("content_free") is True)


def subjective_mem_restore_predecessor_exact(
    space: str, predecessor: SubjectiveMemRevision, state: SubjectiveMemCurrentState,
    proposal: SubjectiveMemRestoreProposal,
    authority: SubjectiveMemCharacterAuthority, workspace: str, committed_at: str,
) -> bool:
    try:
        semantic_identity = subjective_mem_semantic_identity_digest(
            evidence_space_id=space,
            character_id=authority.character_id,
            grounded_content_digest=predecessor.grounded_content_digest,
            subjective_meaning=predecessor.subjective_meaning,
            memory_kind=predecessor.memory_kind,
            scope_binding=predecessor.scope_binding,
        )
    except (TypeError, ValueError):
        return False
    return (
        predecessor.character_id == authority.character_id
        and predecessor.memory_id == proposal.expected_memory_id
        and predecessor.memory_revision == proposal.expected_current_revision
        and predecessor.lifecycle_state == "hidden"
        and predecessor.retrieval_visible is False
        and predecessor.memory_kind == proposal.expected_memory_kind
        and predecessor.formation_stage == proposal.expected_formation_stage
        and semantic_identity == proposal.expected_semantic_identity_digest
        and canonical_digest(predecessor.scope_binding.to_dict())
        == proposal.expected_scope_binding_digest
        and canonical_digest(predecessor.formation_snapshot.to_dict())
        == proposal.expected_formation_snapshot_digest
        and state.workspace_authority_digest
        == subjective_mem_restore_workspace_authority_digest(workspace, authority)
        and state.scope_binding_digest == proposal.expected_scope_binding_digest
        and state.page_id == proposal.expected_page_id
        and state.block_id == proposal.expected_block_id
        and state.canonical_page_digest == proposal.expected_page_digest
        and state.authorization_kind == predecessor.authorization_kind
        and state.authorization_id == predecessor.authorization_id
        and state.current_receipt_id == proposal.expected_current_receipt_id
        and _after(committed_at, predecessor.created_at, state.updated_at))


def subjective_mem_restore_workspace_authority_digest(
    workspace: str, authority: SubjectiveMemCharacterAuthority
) -> str:
    return canonical_digest({
        "workspace_root_digest": sha256_hex(workspace.encode("utf-8")),
        "character_authority": authority.to_dict(),
    })


def _after(candidate: str, *earlier: str) -> bool:
    try:
        current = _utc_text(candidate)
        return all(current > _utc_text(item) for item in earlier)
    except (TypeError, ValueError):
        return False


def _utc_text(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("subjective_mem_restore_clock_invalid")
    return parsed.astimezone(timezone.utc)


def subjective_mem_restore_current_state(
    raw: object,
) -> SubjectiveMemCurrentState | None:
    if not isinstance(raw, dict):
        return None
    binding = raw.get("authority_binding")
    auth = binding.get("authorization_ref") if isinstance(binding, dict) else None
    if not isinstance(binding, dict) or not isinstance(auth, dict):
        return None
    try:
        state = SubjectiveMemCurrentState(
            memory_state_id=raw["memory_state_id"], memory_id=raw["memory_id"],
            character_id=raw["character_id"],
            current_revision=raw["current_revision"],
            lifecycle_state=raw["lifecycle_state"],
            mutation_state=raw["mutation_state"],
            retrieval_eligible=raw["retrieval_eligible"],
            updated_at=raw["updated_at"],
            workspace_authority_digest=binding.get("workspace_authority_digest"),
            scope_binding_digest=binding.get("scope_binding_digest"),
            page_id=binding.get("page_id"), block_id=binding.get("block_id"),
            canonical_page_digest=binding.get("canonical_page_digest"),
            authorization_kind=auth.get("authority_kind"),
            authorization_id=auth.get("authority_id"),
            current_receipt_id=binding.get("current_receipt_id"),
        )
    except (KeyError, TypeError, ValueError):
        return None
    return state if state.to_dict() == raw else None


__all__ = [
    "SubjectiveMemRestorePlanInputs",
    "SubjectiveMemRestorePreparedOperation",
    "build_subjective_mem_restore_final_records",
    "build_subjective_mem_restore_lifecycle_plan",
    "build_subjective_mem_restore_prepared_intent",
    "build_subjective_mem_restore_prepared_operation",
    "subjective_mem_restore_current_state",
    "subjective_mem_restore_predecessor_exact",
    "subjective_mem_restore_predecessor_expectation",
    "subjective_mem_restore_tombstone_exact",
    "subjective_mem_restore_workspace_authority_digest",
]
