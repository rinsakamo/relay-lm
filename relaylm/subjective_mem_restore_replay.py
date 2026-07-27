"""Deterministic reconstruction for one exact finalized Restore replay.

This module owns only the operation-pure material a finalized Restore replay
needs: it rebuilds the publication plan the original operation was reserved
with, from the persisted content-free intent and the durable bindings the
runtime already read. It opens no transaction, touches no file, and never
reserves, publishes, finalizes, or recovers: ``resolve_finalized_replay`` in the
shared lifecycle engine remains the sole replay authority, and
``relaylm.subjective_mem_restore_runtime`` remains the single Restore owner.
"""
from __future__ import annotations

from relaylm.evidence_common import canonical_digest
from relaylm.subjective_mem import (
    SubjectiveMemCharacterAuthority,
    SubjectiveMemCurrentState,
)
from relaylm.subjective_mem_lifecycle import LIFECYCLE_INTENT_SCHEMA
from relaylm.subjective_mem_lifecycle_engine import LifecyclePublicationPlan
from relaylm.subjective_mem_markdown import subjective_mem_page_identity
from relaylm.subjective_mem_reformation import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND as SUBJECTIVE_MEM_FORGET_TOMBSTONE_STATE_LOG_KIND,
)
from relaylm.subjective_mem_restore import (
    SubjectiveMemRestoreOperationIdentity,
    SubjectiveMemRestoreProposal,
)
from relaylm.subjective_mem_tombstone_release import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
)

_FORGET_RECEIPT_KIND = "subjective_mem_lifecycle_receipt"
_FORGET_TOMBSTONE_KIND = "subjective_mem_forget_tombstone"


def build_subjective_mem_restore_replay_plan(
    *,
    intent: object,
    identity: SubjectiveMemRestoreOperationIdentity,
    proposal: SubjectiveMemRestoreProposal,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    workspace_authority_digest: str,
    forget_receipt: object,
    tombstone: object,
    tombstone_state: object,
) -> tuple[LifecyclePublicationPlan | None, tuple[str, ...]]:
    """Rebuild the exact publication plan one finalized Restore was reserved with.

    The persisted intent is reused verbatim so the shared replay resolver can
    prove the durable reservation is unchanged. Nothing here reads a store or a
    page: the caller supplies the durable Forget authority it already read.
    """

    reasons = _replay_intent_errors(
        intent=intent, identity=identity, proposal=proposal,
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        workspace_authority_digest=workspace_authority_digest,
    )
    if reasons:
        return None, reasons
    assert isinstance(intent, dict)
    reasons = _replay_binding_errors(
        intent=intent, forget_receipt=forget_receipt, tombstone=tombstone,
        tombstone_state=tombstone_state,
    )
    if reasons:
        return None, reasons
    prepared = _replay_prepared_state(intent)
    if prepared is None:
        return None, ("subjective_mem_restore_replay_prepared_state_not_exact",)
    assert isinstance(tombstone_state, list)
    return _replay_publication_plan(
        intent=intent, identity=identity, proposal=proposal,
        evidence_space_id=evidence_space_id,
        character_authority=character_authority, workspace_root=workspace_root,
        prepared=prepared, forget_receipt=forget_receipt, tombstone=tombstone,
        tombstone_state=tombstone_state,
    ), ()


def _replay_publication_plan(
    *,
    intent: dict[str, object],
    identity: SubjectiveMemRestoreOperationIdentity,
    proposal: SubjectiveMemRestoreProposal,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    prepared: SubjectiveMemCurrentState,
    forget_receipt: object,
    tombstone: object,
    tombstone_state: list,
) -> LifecyclePublicationPlan:
    """Rebuild the plan fields the reserved operation was finalized with."""

    return LifecyclePublicationPlan(
        evidence_space_id=evidence_space_id,
        character_id=character_authority.character_id,
        workspace_root=workspace_root,
        operation_kind="restore",
        operation_slot_id=identity.operation_slot_id,
        operation_id=identity.operation_id,
        operation_key_digest=identity.operation_key_digest,
        input_digest=identity.input_digest,
        intent_id=identity.intent_id,
        transition_id=identity.transition_id,
        receipt_id=identity.receipt_id,
        result_id=identity.result_id,
        memory_id=str(intent["memory_id"]),
        from_revision=int(intent["from_revision"]),
        to_revision=int(intent["to_revision"]),
        to_lifecycle_state="active",
        selector_id=str(intent["current_selector_id"]),
        prepared_state=prepared,
        page_id=str(intent["page_id"]),
        page_partition=str(intent["partition"]),
        page_relative_path=proposal.expected_relative_path,
        pre_image_state=str(intent["pre_image_state"]),
        pre_image_digest=str(intent["pre_image_digest"]),
        post_image_digest=str(intent["post_image_digest"]),
        predecessor_revision_digest=str(intent["predecessor_revision_digest"]),
        successor_revision_digest=str(intent["successor_revision_digest"]),
        successor_block_id=str(intent["successor_block_id"]),
        artifact_id=str(intent["artifact_id"]),
        prepared_intent=dict(intent),
        prepared_at=str(intent["prepared_at"]),
        record_bindings=(
            (_FORGET_RECEIPT_KIND, str(intent["current_receipt_id"]), forget_receipt),
            (_FORGET_TOMBSTONE_KIND, str(intent["forget_tombstone_id"]), tombstone),
        ),
        log_bindings=(
            (
                SUBJECTIVE_MEM_FORGET_TOMBSTONE_STATE_LOG_KIND,
                str(intent["semantic_identity_digest"]),
                (tombstone_state[0],),
            ),
            (
                SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
                str(intent["forget_tombstone_id"]),
                (),
            ),
        ),
    )


def _replay_intent_errors(
    *,
    intent: object,
    identity: SubjectiveMemRestoreOperationIdentity,
    proposal: SubjectiveMemRestoreProposal,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_authority_digest: str,
) -> tuple[str, ...]:
    """Require the persisted intent to be the exact one this request derives."""

    if not isinstance(intent, dict) or intent.get("schema") != LIFECYCLE_INTENT_SCHEMA:
        return ("subjective_mem_restore_replay_intent_missing_or_corrupt",)
    if (
        intent.get("operation_kind") != "restore"
        or intent.get("intent_id") != identity.intent_id
        or intent.get("operation_slot_id") != identity.operation_slot_id
        or intent.get("operation_id") != identity.operation_id
        or intent.get("operation_key_digest") != identity.operation_key_digest
        or intent.get("input_digest") != identity.input_digest
        or intent.get("transition_id") != identity.transition_id
        or intent.get("receipt_id") != identity.receipt_id
        or intent.get("release_id") != identity.release_id
        or intent.get("result_id") != identity.result_id
    ):
        return ("subjective_mem_restore_replay_identity_not_exact",)
    if (
        intent.get("evidence_space_id") != evidence_space_id
        or intent.get("character_id") != character_authority.character_id
        or intent.get("character_authority_digest")
        != canonical_digest(character_authority.to_dict())
        or intent.get("workspace_authority_digest") != workspace_authority_digest
    ):
        return ("subjective_mem_restore_replay_authority_not_exact",)
    try:
        _page_id, relative, partition = subjective_mem_page_identity(
            character_id=character_authority.character_id,
            memory_kind=str(intent.get("memory_kind")),
        )
    except (TypeError, ValueError):
        return ("subjective_mem_restore_replay_proposal_not_exact",)
    if (
        intent.get("memory_id") != proposal.expected_memory_id
        or intent.get("from_revision") != proposal.expected_current_revision
        or intent.get("to_revision") != proposal.expected_current_revision + 1
        or intent.get("from_lifecycle_state") != "hidden"
        or intent.get("to_lifecycle_state") != "active"
        or intent.get("current_selector_id") != proposal.expected_current_selector_id
        or intent.get("current_selector_digest")
        != proposal.expected_current_selector_digest
        or intent.get("current_receipt_id") != proposal.expected_current_receipt_id
        or intent.get("current_receipt_digest")
        != proposal.expected_current_receipt_digest
        or intent.get("page_id") != proposal.expected_page_id
        or intent.get("partition") != partition
        or relative != proposal.expected_relative_path
        or intent.get("predecessor_block_id") != proposal.expected_block_id
        or intent.get("pre_image_digest") != proposal.expected_page_digest
        or intent.get("forget_transition_id") != proposal.expected_forget_transition_id
        or intent.get("forget_transition_digest")
        != proposal.expected_forget_transition_digest
        or intent.get("forget_tombstone_id") != proposal.expected_forget_tombstone_id
        or intent.get("forget_tombstone_digest")
        != proposal.expected_forget_tombstone_digest
        or intent.get("semantic_identity_digest")
        != proposal.expected_semantic_identity_digest
        or intent.get("policy_revision") != proposal.policy_revision
    ):
        return ("subjective_mem_restore_replay_proposal_not_exact",)
    return ()


def _replay_binding_errors(
    *,
    intent: dict[str, object],
    forget_receipt: object,
    tombstone: object,
    tombstone_state: object,
) -> tuple[str, ...]:
    """Require the durable Forget authority the finalized plan was bound to."""

    if (
        not isinstance(forget_receipt, dict)
        or not isinstance(tombstone, dict)
        or forget_receipt.get("receipt_id") != intent["current_receipt_id"]
        or forget_receipt.get("receipt_digest") != intent["current_receipt_digest"]
        or forget_receipt.get("operation_kind") != "forget"
        or forget_receipt.get("transition_id") != intent["forget_transition_id"]
        or forget_receipt.get("tombstone_id") != intent["forget_tombstone_id"]
        or tombstone.get("tombstone_id") != intent["forget_tombstone_id"]
        or tombstone.get("tombstone_digest") != intent["forget_tombstone_digest"]
        or tombstone.get("semantic_identity_digest")
        != intent["semantic_identity_digest"]
    ):
        return ("subjective_mem_restore_replay_forget_authority_not_exact",)
    if (
        not isinstance(tombstone_state, list)
        or len(tombstone_state) != 1
        or not isinstance(tombstone_state[0], dict)
        or tombstone_state[0].get("tombstone_id") != intent["forget_tombstone_id"]
    ):
        return ("subjective_mem_restore_replay_tombstone_state_not_exact",)
    return ()


def _replay_prepared_state(
    intent: dict[str, object],
) -> SubjectiveMemCurrentState | None:
    """Rebuild the fenced hidden selector this operation reserved."""

    try:
        state = SubjectiveMemCurrentState(
            memory_state_id=str(intent["current_selector_id"]),
            memory_id=str(intent["memory_id"]),
            character_id=str(intent["character_id"]),
            current_revision=int(intent["from_revision"]),
            lifecycle_state=str(intent["from_lifecycle_state"]),
            mutation_state="prepared",
            retrieval_eligible=False,
            updated_at=str(intent["prepared_at"]),
            workspace_authority_digest=intent.get("workspace_authority_digest"),
            scope_binding_digest=intent.get("scope_binding_digest"),
            page_id=intent.get("page_id"),
            block_id=intent.get("predecessor_block_id"),
            canonical_page_digest=intent.get("pre_image_digest"),
            authorization_kind=intent.get("predecessor_authorization_kind"),
            authorization_id=intent.get("predecessor_authorization_id"),
            current_receipt_id=intent.get("current_receipt_id"),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if canonical_digest(state.to_dict()) != intent.get("prepared_current_state_digest"):
        return None
    return state


__all__ = ["build_subjective_mem_restore_replay_plan"]
