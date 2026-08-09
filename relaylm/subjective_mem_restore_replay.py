"""Deterministic reconstruction of exact Restore material from durable images.

This module owns the operation-pure reconstruction one Restore operation needs.
It rebuilds the publication plan the original operation was reserved with, from
the persisted content-free intent and the durable bindings the runtime already
read, and it reconstructs the exact page identity and hidden predecessor a
canonical or prepared page image encodes. Both rest on the same page-identity
authority, so they live together here. It opens no transaction, touches no
file, and never reserves, publishes, finalizes, or recovers:
``resolve_finalized_replay`` in the shared lifecycle engine remains the sole
replay authority, and ``relaylm.subjective_mem_restore_runtime`` remains the
single Restore owner.
"""
from __future__ import annotations

from relaylm.evidence.common import canonical_digest
from relaylm.evidence.space import EvidenceSpaceDescriptor
from relaylm.subjective_mem import (
    SubjectiveMemCharacterAuthority,
    SubjectiveMemCurrentState,
    SubjectiveMemRevision,
)
from relaylm.subjective_mem_forget import FORGET_TOMBSTONE_STATE_SCHEMA
from relaylm.subjective_mem_lifecycle import LIFECYCLE_INTENT_SCHEMA
from relaylm.subjective_mem_lifecycle_engine import (
    LifecyclePublicationPlan,
    RecordBinding,
)
from relaylm.subjective_mem_markdown import (
    parse_subjective_mem_page_bytes,
    subjective_mem_page_identity,
)
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

_DESCRIPTOR_KIND = "evidence_space_descriptor"
_DESCRIPTOR_ID = "revision-1"
_FORGET_RECEIPT_KIND = "subjective_mem_lifecycle_receipt"
_FORGET_TRANSITION_KIND = "subjective_mem_lifecycle_transition"
_FORGET_TOMBSTONE_KIND = "subjective_mem_forget_tombstone"
_TOMBSTONE_STATE_FIELDS = frozenset(
    "schema tombstone_id tombstone_digest evidence_space_id character_id "
    "semantic_identity_digest memory_id hidden_revision formation_stage "
    "transition_id transition_digest receipt_id effective "
    "superseded_by_tombstone_id_or_null updated_at content_free".split()
)


def build_subjective_mem_restore_replay_plan(
    *,
    intent: object,
    identity: SubjectiveMemRestoreOperationIdentity,
    proposal: SubjectiveMemRestoreProposal,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    workspace_authority_digest: str,
    descriptor: object,
    forget_receipt: object,
    forget_transition: object,
    tombstone: object,
    tombstone_state: object,
) -> tuple[LifecyclePublicationPlan | None, tuple[str, ...]]:
    """Rebuild the exact publication plan one finalized Restore was reserved with.

    The persisted intent is reused verbatim so the shared replay resolver can
    prove the durable reservation is unchanged. Nothing here reads a store or a
    page: the caller supplies the durable predecessor authority it already read.
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
    bindings, reasons = _replay_record_bindings(
        intent=intent, character_authority=character_authority,
        descriptor=descriptor, forget_receipt=forget_receipt,
        forget_transition=forget_transition, tombstone=tombstone,
        tombstone_state=tombstone_state,
    )
    if bindings is None:
        return None, reasons
    prepared = _replay_prepared_state(intent)
    if prepared is None:
        return None, ("subjective_mem_restore_replay_prepared_state_not_exact",)
    assert isinstance(tombstone_state, list)
    return _replay_publication_plan(
        intent=intent, identity=identity, proposal=proposal,
        evidence_space_id=evidence_space_id,
        character_authority=character_authority, workspace_root=workspace_root,
        prepared=prepared, record_bindings=bindings,
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
    record_bindings: tuple[RecordBinding, ...],
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
        record_bindings=record_bindings,
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


def _replay_record_bindings(
    *,
    intent: dict[str, object],
    character_authority: SubjectiveMemCharacterAuthority,
    descriptor: object,
    forget_receipt: object,
    forget_transition: object,
    tombstone: object,
    tombstone_state: object,
) -> tuple[tuple[RecordBinding, ...] | None, tuple[str, ...]]:
    """Rebuild the exact four predecessor bindings the operation was reserved with.

    The reserved set and its order are the shared predecessor authority's
    Evidence-space descriptor, current Forget receipt, and original Forget
    transition, followed by the immutable Forget tombstone this operation
    releases. Anything short of that exact set cannot reconstruct the plan.
    """

    if not _descriptor_exact(
        descriptor, intent=intent, character_authority=character_authority
    ):
        return None, ("subjective_mem_restore_replay_evidence_space_not_exact",)
    if not isinstance(forget_receipt, dict) or not isinstance(tombstone, dict):
        return None, ("subjective_mem_restore_replay_forget_authority_not_exact",)
    if not _forget_lineage_exact(
        forget_receipt=forget_receipt, forget_transition=forget_transition,
        tombstone=tombstone, intent=intent,
    ):
        return None, ("subjective_mem_restore_replay_forget_authority_not_exact",)
    if (
        not isinstance(tombstone_state, list)
        or len(tombstone_state) != 1
        or not _tombstone_state_exact(
            tombstone_state[0], intent=intent, tombstone=tombstone
        )
    ):
        return None, ("subjective_mem_restore_replay_tombstone_state_not_exact",)
    return (
        (_DESCRIPTOR_KIND, _DESCRIPTOR_ID, descriptor),
        (_FORGET_RECEIPT_KIND, str(intent["current_receipt_id"]), forget_receipt),
        (
            _FORGET_TRANSITION_KIND,
            str(intent["forget_transition_id"]),
            forget_transition,
        ),
        (_FORGET_TOMBSTONE_KIND, str(intent["forget_tombstone_id"]), tombstone),
    ), ()


def _descriptor_exact(
    descriptor: object, *,
    intent: dict[str, object],
    character_authority: SubjectiveMemCharacterAuthority,
) -> bool:
    """Require the exact current, non-retired Evidence-space descriptor."""

    if not isinstance(descriptor, dict):
        return False
    try:
        parsed = EvidenceSpaceDescriptor.from_dict(descriptor)
    except (KeyError, TypeError, ValueError):
        return False
    return (
        parsed.to_dict() == descriptor
        and parsed.evidence_space_id == intent["evidence_space_id"]
        and parsed.workspace_or_tenant_ref
        == character_authority.workspace_or_tenant_ref
        and parsed.isolation_mode == "private_conversation"
        and parsed.retired_at_or_null is None
        and canonical_digest(descriptor)
        == intent["evidence_space_descriptor_digest"]
    )


def _forget_lineage_exact(
    *,
    forget_receipt: dict[str, object],
    forget_transition: object,
    tombstone: dict[str, object],
    intent: dict[str, object],
) -> bool:
    """Authenticate the whole Forget receipt, transition, and tombstone bodies.

    Anchoring each complete record to the digest the reservation persisted is
    stronger than comparing selected fields: with the body pinned, no
    uninspected field can differ while a stale digest field is retained, and
    the lineage the three records cross-link follows by construction. Only the
    store keys they were read under still need their own comparison.
    """

    return (
        _self_digest_exact(
            forget_receipt, "receipt_digest", intent["current_receipt_digest"]
        )
        and _self_digest_exact(
            tombstone, "tombstone_digest", intent["forget_tombstone_digest"]
        )
        and isinstance(forget_transition, dict)
        and canonical_digest(forget_transition) == intent["forget_transition_digest"]
        and forget_receipt.get("receipt_id") == intent["current_receipt_id"]
        and forget_receipt.get("transition_id") == intent["forget_transition_id"]
        and forget_receipt.get("tombstone_id") == intent["forget_tombstone_id"]
        and tombstone.get("tombstone_id") == intent["forget_tombstone_id"]
        and forget_transition.get("transition_id") == intent["forget_transition_id"]
    )


def _self_digest_exact(record: object, field: str, persisted: object) -> bool:
    """Recompute one record's self-digest and anchor it to the persisted value.

    The record carries its own digest, so a retained stale digest field is only
    caught by recomputing it over the rest of the body.
    """

    if not isinstance(record, dict):
        return False
    recomputed = canonical_digest(
        {key: value for key, value in record.items() if key != field}
    )
    return recomputed == record.get(field) == persisted


def _tombstone_state_exact(
    event: object, *, intent: dict[str, object], tombstone: dict[str, object]
) -> bool:
    """Require the exact singleton Forget tombstone-state event, field by field.

    The shared reservation claim carries no bindings, so this reconstruction
    layer must prove the whole original state event, not only its identifier.
    """

    if not isinstance(event, dict) or set(event) != _TOMBSTONE_STATE_FIELDS:
        return False
    return (
        event["schema"] == FORGET_TOMBSTONE_STATE_SCHEMA
        and event["tombstone_id"] == intent["forget_tombstone_id"]
        and event["tombstone_id"] == tombstone.get("tombstone_id")
        and event["tombstone_digest"] == intent["forget_tombstone_digest"]
        and event["tombstone_digest"] == tombstone.get("tombstone_digest")
        and event["evidence_space_id"] == intent["evidence_space_id"]
        and event["evidence_space_id"] == tombstone.get("evidence_space_id")
        and event["character_id"] == intent["character_id"]
        and event["character_id"] == tombstone.get("character_id")
        and event["semantic_identity_digest"] == intent["semantic_identity_digest"]
        and event["semantic_identity_digest"]
        == tombstone.get("semantic_identity_digest")
        and event["memory_id"] == intent["memory_id"]
        and event["memory_id"] == tombstone.get("memory_id")
        and event["hidden_revision"] == intent["from_revision"]
        and event["hidden_revision"] == tombstone.get("hidden_revision")
        and event["formation_stage"] == intent["formation_stage"]
        and event["formation_stage"] == tombstone.get("formation_stage")
        and event["transition_id"] == intent["forget_transition_id"]
        and event["transition_id"] == tombstone.get("transition_id")
        and event["transition_digest"] == intent["forget_transition_digest"]
        and event["transition_digest"] == tombstone.get("transition_digest")
        and event["receipt_id"] == intent["current_receipt_id"]
        and event["receipt_id"] == tombstone.get("receipt_id")
        and event["effective"] is True
        and event["superseded_by_tombstone_id_or_null"] is None
        and event["updated_at"] == tombstone.get("effective_at")
        and event["content_free"] is True
    )


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


def subjective_mem_restore_page_binding(
    character_authority: SubjectiveMemCharacterAuthority,
    proposal: SubjectiveMemRestoreProposal,
) -> tuple[tuple[str, str, str] | None, tuple[str, ...]]:
    """Derive the exact page identity one Restore proposal claims to address.

    This decides where the canonical image lives; it never reads it. The caller
    owns the filesystem access and passes the bytes back for selection.
    """

    try:
        page_id, relative_path, partition = subjective_mem_page_identity(
            character_id=character_authority.character_id,
            memory_kind=proposal.expected_memory_kind,
        )
    except ValueError:
        return None, ("subjective_mem_restore_page_identity_invalid",)
    if (page_id, relative_path) != (
        proposal.expected_page_id, proposal.expected_relative_path
    ):
        return None, ("subjective_mem_restore_page_identity_mismatch",)
    return (page_id, relative_path, partition), ()


def subjective_mem_restore_page_predecessor(
    page_bytes: bytes, *,
    binding: tuple[str, str, str],
    character_authority: SubjectiveMemCharacterAuthority,
    proposal: SubjectiveMemRestoreProposal,
) -> tuple[SubjectiveMemRevision | None, tuple[str, ...]]:
    """Select the exact hidden predecessor block encoded by one page image.

    The logical memory must be present exactly once at the expected revision,
    in the expected block, with nothing later already published for it.
    """

    page_id, _relative_path, partition = binding
    page, reasons = parse_subjective_mem_page_bytes(
        page_bytes, expected_page_id=page_id,
        expected_character_id=character_authority.character_id,
        expected_partition=partition,
    )
    if page is None:
        return None, reasons
    logical = [
        item for item in page.blocks
        if item.revision.memory_id == proposal.expected_memory_id
    ]
    exact = [
        item for item in logical
        if item.revision.memory_revision == proposal.expected_current_revision
    ]
    later = [
        item for item in logical
        if item.revision.memory_revision > proposal.expected_current_revision
    ]
    if len(exact) != 1 or exact[0].block_id != proposal.expected_block_id or later:
        return None, ("subjective_mem_restore_current_revision_not_exact",)
    return exact[0].revision, ()


__all__ = [
    "build_subjective_mem_restore_replay_plan",
    "subjective_mem_restore_page_binding",
    "subjective_mem_restore_page_predecessor",
]
