"""LC-1E immutable Subjective MEM Consolidate runtime.

This module is the only Consolidate operation owner.  It validates one exact
``active Primary revision N`` predecessor, constructs one immutable
``active Secondary revision N+1`` successor from that predecessor, and drives
publication, replay, and caller-invoked forward recovery entirely through the
shared lifecycle publication engine.  It never re-implements predecessor
authority, candidate discovery, semantic generation, or another operation's
state machine.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Literal

from relaylm.subjective_mem.commit_io import PLATFORM_REVISION, inspect_canonical_page, secure_platform_supported
from relaylm.evidence.common import canonical_digest, sha256_hex
from relaylm.evidence.store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.subjective_mem.models import SUBJECTIVE_MEM_REVISION_SCHEMA, SubjectiveMemCharacterAuthority, SubjectiveMemCurrentState, SubjectiveMemRevision, resolve_subjective_mem_character_authority
from relaylm.subjective_mem.consolidate import CONSOLIDATE_OPERATION_FAMILY, SubjectiveMemConsolidateOperationIdentity, SubjectiveMemConsolidateProposal, derive_subjective_mem_consolidate_operation_identity, subjective_mem_consolidate_transition, validate_subjective_mem_consolidate_proposal
from relaylm.subjective_mem.lifecycle import LIFECYCLE_INTENT_FINALIZATION_SCHEMA, LIFECYCLE_INTENT_SCHEMA, LIFECYCLE_RECEIPT_SCHEMA, LIFECYCLE_RESULT_SCHEMA, LIFECYCLE_TRANSITION_SCHEMA
from relaylm.subjective_mem.lifecycle_authority import SubjectiveMemPredecessorAuthority, SubjectiveMemPredecessorExpectation, load_subjective_mem_predecessor_authority_locked
from relaylm.subjective_mem.lifecycle_engine import LifecycleExecutionOutcome, LifecycleFinalRecords, LifecycleFinalizer, LifecyclePublicationPlan, RecordBinding, lifecycle_claim_record, publish_lifecycle_post_image, read_lifecycle_reservation, read_prepared_post_image, reserve_lifecycle_publication, resolve_finalized_replay
from relaylm.subjective_mem.markdown import LIFECYCLE_BLOCK_SCHEMA, PAGE_PARTITION_REVISION, PAGE_SCHEMA, RENDERER_REVISION, SubjectiveMemPagePlan, canonical_page_digest, parse_subjective_mem_page_bytes, plan_subjective_mem_revision_successor, subjective_mem_page_identity

ConsolidateStatus = Literal["disabled", "dry_run_ready", "committed", "duplicate_finalized", "recovery_pending", "recovery_required", "lock_busy", "fail_closed", "integrity_conflict"]
FaultInjector = Callable[[str], None]
_CURRENT = "subjective_mem_current_state"
_OPERATION = CONSOLIDATE_OPERATION_FAMILY
# The exact existing Subjective MEM gate triples, read here as a bounded
# operation-local precondition.  This module owns no gate authority of its own:
# it names no new configuration and resolves nothing a caller could widen.
_GATE_FIELDS = ("enabled", "dry_run_only", "apply_enabled")
_GATE_MODES = MappingProxyType(
    {
        (False, True, False): "disabled",
        (True, True, False): "dry_run",
        (True, False, True): "apply",
    }
)


@dataclass(frozen=True, repr=False)
class SubjectiveMemConsolidateResult:
    status: ConsolidateStatus
    operation_kind: str = _OPERATION
    transition_id: str | None = None
    receipt_id: str | None = None
    memory_id: str | None = None
    from_revision: int | None = None
    to_revision: int | None = None
    from_formation_stage: str | None = None
    to_formation_stage: str | None = None
    current_state: SubjectiveMemCurrentState | None = None
    blocked_reasons: tuple[str, ...] = ()
    recovery_outcome: str | None = None
    canonical_markdown_published: bool = False
    lifecycle_receipt_present: bool = False
    persisted: bool = False

    def to_log_dict(self) -> dict[str, object]:
        state = self.current_state
        return {"status": self.status, "operation_kind": self.operation_kind,
                "transition_id": self.transition_id, "receipt_id": self.receipt_id,
                "memory_id": self.memory_id, "from_revision": self.from_revision,
                "to_revision": self.to_revision,
                "from_formation_stage": self.from_formation_stage,
                "to_formation_stage": self.to_formation_stage,
                "lifecycle_state": state.lifecycle_state if state else None,
                "mutation_state": state.mutation_state if state else None,
                "retrieval_eligible": state.retrieval_eligible if state else False,
                "canonical_markdown_published": self.canonical_markdown_published,
                "lifecycle_receipt_present": self.lifecycle_receipt_present,
                "ordinary_retrieval_wired": False, "second_logical_memory_created": False,
                "relation_or_supersession_written": False, "tombstone_written": False,
                "usage_event_written": False, "primary_mem_consolidated": False,
                "background_recovery_started": False, "content_rewrite_performed": False,
                "recovery_outcome": self.recovery_outcome, "persisted": self.persisted,
                "content_free": True, "path_values_included": False,
                "digest_values_included": False, "raw_key_included": False,
                "exception_text_included": False}


@dataclass(frozen=True)
class _Prepared:
    predecessor: SubjectiveMemRevision
    successor: SubjectiveMemRevision
    current: SubjectiveMemCurrentState
    prepared: SubjectiveMemCurrentState
    page: SubjectiveMemPagePlan
    intent: dict[str, object]
    bindings: tuple[RecordBinding, ...]


def consolidate_subjective_mem(
    *, store: EvidenceRecordStore, evidence_space_id: str, character_config: object,
    character_authority: SubjectiveMemCharacterAuthority, workspace_root: str,
    operation_idempotency_key: str, proposal: SubjectiveMemConsolidateProposal,
    apply_enabled: bool, committed_at: datetime, observed_at: datetime | None = None,
    fault_injector: FaultInjector | None = None,
) -> SubjectiveMemConsolidateResult:
    """Consolidate one exact active Primary revision into its active Secondary successor."""

    reasons = _request_errors(store, character_config, character_authority,
                              workspace_root, proposal, apply_enabled, fault_injector)
    try:
        operation_time = _utc(committed_at)
        if operation_time > _utc(observed_at or datetime.now(timezone.utc)):
            reasons.append("subjective_mem_consolidate_time_in_future")
    except (TypeError, ValueError):
        operation_time = None
        reasons.append("subjective_mem_consolidate_clock_invalid")
    if reasons:
        return _result("fail_closed", reasons=tuple(dict.fromkeys(reasons)))
    assert operation_time is not None
    mode, gate_errors = _gate_mode_or_errors(character_config, apply_enabled)
    if mode is None:
        return _result("fail_closed", proposal=proposal, reasons=gate_errors)
    if mode == "disabled":
        return _result("disabled", proposal=proposal,
                       reasons=("subjective_mem_consolidate_lifecycle_disabled",))
    if not _space_present(store, evidence_space_id):
        return _result("fail_closed", proposal=proposal,
                       reasons=("subjective_mem_consolidate_evidence_space_unavailable",))
    identity, errors = derive_subjective_mem_consolidate_operation_identity(
        evidence_space_id=evidence_space_id,
        character_authority_digest=canonical_digest(character_authority.to_dict()),
        memory_id=proposal.expected_memory_id,
        operation_idempotency_key=operation_idempotency_key,
        proposal=proposal, operation_time=operation_time.isoformat())
    if identity is None:
        return _result("fail_closed", proposal=proposal, reasons=errors)
    claim, intent, final, errors = read_lifecycle_reservation(
        store=store, evidence_space_id=evidence_space_id,
        operation_slot_id=identity.operation_slot_id, intent_id=identity.intent_id,
        result_id=identity.result_id)
    if errors:
        return _result("fail_closed", identity=identity, proposal=proposal, reasons=errors)
    if final is not None:
        if final.get("input_digest") != identity.input_digest:
            return _conflict(identity, proposal)
        return _replay(store, evidence_space_id, character_authority, workspace_root,
                       proposal, identity, intent)
    if claim is not None:
        if claim.get("input_digest") != identity.input_digest:
            return _conflict(identity, proposal)
        if not isinstance(intent, dict):
            return _result("fail_closed", identity=identity, proposal=proposal,
                           reasons=("subjective_mem_consolidate_intent_missing_or_corrupt",))
        return _resume(store, evidence_space_id, character_authority, workspace_root,
                       proposal, identity, claim, intent, fault_injector)
    prepared, errors = _prepare(store, evidence_space_id, character_authority,
                                workspace_root, proposal, identity, operation_time.isoformat())
    if prepared is None:
        return _result(_status(errors), identity=identity, proposal=proposal, reasons=errors)
    if not apply_enabled:
        return _result("dry_run_ready", identity=identity, proposal=proposal,
                       current_state=prepared.current, recovery_outcome="new_intent_ready")
    return _execute(store, evidence_space_id, character_authority, workspace_root,
                    proposal, identity, prepared, fault_injector)


def _execute(
    store: EvidenceRecordStore, space: str, authority: SubjectiveMemCharacterAuthority,
    workspace: str, proposal: SubjectiveMemConsolidateProposal,
    identity: SubjectiveMemConsolidateOperationIdentity, prepared: _Prepared,
    fault: FaultInjector | None,
) -> SubjectiveMemConsolidateResult:
    """Reserve the singleton selector, publish the exact post-image, and finalize."""

    plan = _plan(space, authority, workspace, identity, prepared.intent,
                 prepared.prepared, prepared.bindings, prepared.current)
    if plan is None:
        return _corrupt(identity, proposal)
    reserved = reserve_lifecycle_publication(
        store=store, plan=plan, post_image=prepared.page.rendered_bytes,
        fault_injector=fault)
    if reserved.status != "reserved":
        return _from_outcome(reserved, identity, proposal)
    try:
        _fault(fault, "after_intent_before_page")
    except Exception:
        return _result("recovery_pending", identity=identity, proposal=proposal,
                       current_state=prepared.prepared,
                       recovery_outcome="pre_image_pending_publication", persisted=True)
    outcome = publish_lifecycle_post_image(
        store=store, plan=plan, post_image=prepared.page.rendered_bytes,
        finalizer=_finalizer(space, authority, identity, prepared.intent),
        fault_injector=fault)
    return _from_outcome(outcome, identity, proposal)


def _prepare(
    store: EvidenceRecordStore, space: str, authority: SubjectiveMemCharacterAuthority,
    workspace: str, proposal: SubjectiveMemConsolidateProposal,
    identity: SubjectiveMemConsolidateOperationIdentity, committed_at: str,
) -> tuple[_Prepared | None, tuple[str, ...]]:
    _from_state, to_state, _from_stage, to_stage = subjective_mem_consolidate_transition()
    try:
        page_id, relative, partition = subjective_mem_page_identity(
            character_id=authority.character_id, memory_kind=proposal.expected_memory_kind)
    except ValueError:
        return None, ("subjective_mem_consolidate_page_identity_invalid",)
    if (page_id, relative) != (proposal.expected_page_id, proposal.expected_relative_path):
        return None, ("subjective_mem_consolidate_page_identity_mismatch",)
    try:
        with store.transaction(space) as tx:
            selector, errors = _selector(tx, proposal, authority.character_id)
            if selector is None:
                return None, errors
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, ("subjective_mem_consolidate_store_unavailable",)
    inspected = inspect_canonical_page(workspace_root=workspace,
        character_id=authority.character_id, relative_path=proposal.expected_relative_path)
    if inspected.snapshot is None or inspected.snapshot.data is None:
        return None, inspected.reasons or ("subjective_mem_consolidate_canonical_page_missing",)
    snapshot = inspected.snapshot
    if snapshot.digest != proposal.expected_page_digest:
        return None, ("subjective_mem_consolidate_page_digest_mismatch",)
    page, errors = parse_subjective_mem_page_bytes(snapshot.data,
        expected_page_id=page_id, expected_character_id=authority.character_id,
        expected_partition=partition)
    if page is None:
        return None, errors
    matches = [item for item in page.blocks
               if item.revision.memory_id == proposal.expected_memory_id
               and item.revision.memory_revision == proposal.expected_current_revision]
    later = [item for item in page.blocks
             if item.revision.memory_id == proposal.expected_memory_id
             and item.revision.memory_revision > proposal.expected_current_revision]
    if len(matches) != 1 or matches[0].block_id != proposal.expected_block_id or later:
        return None, ("subjective_mem_consolidate_current_revision_not_exact",)
    predecessor = matches[0].revision
    try:
        with store.transaction(space) as tx:
            predecessor_authority, errors = load_subjective_mem_predecessor_authority_locked(
                tx=tx, evidence_space_id=space, character_authority=authority,
                predecessor=predecessor, expectation=_expectation(proposal))
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, ("subjective_mem_consolidate_store_unavailable",)
    if predecessor_authority is None:
        return None, errors
    current = _state(selector)
    if current is None or not _predecessor_exact(
            predecessor, current, proposal, authority, workspace, committed_at
    ) or not _predecessor_authorization_exact(predecessor, proposal, predecessor_authority):
        return None, ("subjective_mem_consolidate_current_revision_invalid",)
    successor = replace(predecessor, decision_id=identity.transition_id,
        created_at=committed_at, memory_revision=predecessor.memory_revision + 1,
        formation_stage=to_stage, lifecycle_state=to_state, retrieval_visible=True,
        predecessor_revision_or_null=predecessor.memory_revision,
        authorization_kind="lifecycle_transition")
    planned = plan_subjective_mem_revision_successor(
        predecessor=predecessor, successor=successor, existing_bytes=snapshot.data)
    if planned.plan is None:
        return None, planned.reasons
    prepared = replace(
        current, mutation_state="prepared", retrieval_eligible=False,
        updated_at=committed_at, workspace_authority_digest=_workspace_digest(workspace, authority),
        scope_binding_digest=proposal.expected_scope_binding_digest,
        page_id=proposal.expected_page_id, block_id=proposal.expected_block_id,
        canonical_page_digest=proposal.expected_page_digest,
        authorization_kind=predecessor.authorization_kind,
        authorization_id=predecessor.authorization_id,
        current_receipt_id=proposal.expected_current_receipt_id)
    intent = _intent(space, authority, workspace, proposal, identity, predecessor,
                     successor, prepared, planned.plan, committed_at)
    return _Prepared(predecessor, successor, current, prepared, planned.plan,
                     intent, predecessor_authority.record_bindings), ()


def _resume(
    store: EvidenceRecordStore, space: str, authority: SubjectiveMemCharacterAuthority,
    workspace: str, proposal: SubjectiveMemConsolidateProposal,
    identity: SubjectiveMemConsolidateOperationIdentity, claim: dict[str, object],
    intent: dict[str, object], fault: FaultInjector | None,
) -> SubjectiveMemConsolidateResult:
    if not _intent_exact(intent, identity, proposal, authority, space, workspace):
        return _corrupt(identity, proposal)
    prepared = _prepared_state(intent)
    if prepared is None:
        return _corrupt(identity, proposal)
    try:
        with store.transaction(space) as tx:
            if tx.read_log(log_kind=_CURRENT, key=prepared.memory_state_id) != [prepared.to_dict()]:
                return _result("recovery_required", identity=identity, proposal=proposal,
                               current_state=prepared,
                               reasons=("subjective_mem_lifecycle_current_selector_changed",),
                               persisted=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        return _result("fail_closed", identity=identity, proposal=proposal,
                       reasons=("subjective_mem_consolidate_store_unavailable",))
    artifact, errors = read_prepared_post_image(
        workspace_root=workspace, character_id=authority.character_id,
        artifact_id=str(intent["artifact_id"]),
        expected_post_image_digest=str(intent["post_image_digest"]))
    predecessor = _artifact_predecessor(artifact, intent, proposal, authority) if artifact is not None else None
    if artifact is None or predecessor is None:
        return _result("recovery_required", identity=identity, proposal=proposal,
                       current_state=prepared, reasons=errors or ("subjective_mem_consolidate_artifact_invalid",),
                       recovery_outcome="artifact_unavailable", persisted=True)
    try:
        with store.transaction(space) as tx:
            predecessor_authority, _errors = load_subjective_mem_predecessor_authority_locked(
                tx=tx, evidence_space_id=space, character_authority=authority,
                predecessor=predecessor, expectation=_expectation(proposal))
    except (OSError, RuntimeError, TypeError, ValueError):
        return _result("fail_closed", identity=identity, proposal=proposal,
                       reasons=("subjective_mem_consolidate_store_unavailable",))
    if predecessor_authority is None or not _predecessor_authorization_exact(
            predecessor, proposal, predecessor_authority):
        return _result("recovery_pending", identity=identity, proposal=proposal,
                       current_state=prepared,
                       reasons=("subjective_mem_commit_pre_image_authority_changed",),
                       recovery_outcome="pre_image_pending_publication", persisted=True)
    plan = _plan(space, authority, workspace, identity, intent, prepared,
                 predecessor_authority.record_bindings)
    if plan is None or claim != lifecycle_claim_record(plan):
        return _corrupt(identity, proposal)
    outcome = publish_lifecycle_post_image(
        store=store, plan=plan, post_image=artifact,
        finalizer=_finalizer(space, authority, identity, intent), fault_injector=fault)
    return _from_outcome(outcome, identity, proposal)


def _replay(
    store: EvidenceRecordStore, space: str, authority: SubjectiveMemCharacterAuthority,
    workspace: str, proposal: SubjectiveMemConsolidateProposal,
    identity: SubjectiveMemConsolidateOperationIdentity, intent: object,
) -> SubjectiveMemConsolidateResult:
    plan = None
    if isinstance(intent, dict) and _intent_exact(intent, identity, proposal, authority, space, workspace):
        prepared = _prepared_state(intent)
        if prepared is not None:
            plan = _plan(space, authority, workspace, identity, intent, prepared)
    outcome = resolve_finalized_replay(
        store=store, plan=plan,
        finalizer=_finalizer(space, authority, identity, intent if isinstance(intent, dict) else None)
    ) if plan is not None else None
    if outcome is None:
        return _result("fail_closed", identity=identity, proposal=proposal,
                       reasons=("subjective_mem_consolidate_final_result_incomplete",))
    return _from_outcome(outcome, identity, proposal)


def _plan(
    space: str, authority: SubjectiveMemCharacterAuthority, workspace: str,
    identity: SubjectiveMemConsolidateOperationIdentity, intent: dict[str, object],
    prepared: SubjectiveMemCurrentState, bindings: tuple[RecordBinding, ...] = (),
    current: SubjectiveMemCurrentState | None = None,
) -> LifecyclePublicationPlan | None:
    try:
        _, relative, _ = subjective_mem_page_identity(
            character_id=authority.character_id, memory_kind=str(intent["memory_kind"]))
        return LifecyclePublicationPlan(
            evidence_space_id=space, character_id=authority.character_id,
            workspace_root=workspace, operation_kind=str(intent["operation_kind"]),
            operation_slot_id=identity.operation_slot_id, operation_id=identity.operation_id,
            operation_key_digest=identity.operation_key_digest, input_digest=identity.input_digest,
            intent_id=identity.intent_id, transition_id=identity.transition_id,
            receipt_id=identity.receipt_id, result_id=identity.result_id,
            memory_id=str(intent["memory_id"]), from_revision=int(intent["from_revision"]),
            to_revision=int(intent["to_revision"]),
            to_lifecycle_state=str(intent["to_lifecycle_state"]),
            selector_id=str(intent["current_selector_id"]), prepared_state=prepared,
            page_id=str(intent["page_id"]), page_partition=str(intent["partition"]),
            page_relative_path=relative, pre_image_state=str(intent["pre_image_state"]),
            pre_image_digest=str(intent["pre_image_digest"]),
            post_image_digest=str(intent["post_image_digest"]),
            predecessor_revision_digest=str(intent["predecessor_revision_digest"]),
            successor_revision_digest=str(intent["successor_revision_digest"]),
            successor_block_id=str(intent["successor_block_id"]),
            artifact_id=str(intent["artifact_id"]), prepared_intent=dict(intent),
            prepared_at=str(intent["prepared_at"]), record_bindings=bindings,
            current_state=current)
    except (KeyError, TypeError, ValueError):
        return None


def _intent(
    space: str, authority: SubjectiveMemCharacterAuthority, workspace: str,
    proposal: SubjectiveMemConsolidateProposal,
    identity: SubjectiveMemConsolidateOperationIdentity,
    predecessor: SubjectiveMemRevision, successor: SubjectiveMemRevision,
    prepared: SubjectiveMemCurrentState, page: SubjectiveMemPagePlan, at: str,
) -> dict[str, object]:
    return {"schema": LIFECYCLE_INTENT_SCHEMA, "intent_id": identity.intent_id,
            "operation_slot_id": identity.operation_slot_id,
            "operation_id": identity.operation_id, "operation_kind": _OPERATION,
            "operation_key_digest": identity.operation_key_digest,
            "input_digest": identity.input_digest, "evidence_space_id": space,
            "character_id": authority.character_id,
            "character_authority_digest": canonical_digest(authority.to_dict()),
            "workspace_authority_digest": _workspace_digest(workspace, authority),
            "memory_id": predecessor.memory_id, "memory_kind": predecessor.memory_kind,
            "from_formation_stage": predecessor.formation_stage,
            "to_formation_stage": successor.formation_stage,
            "scope_binding_digest": canonical_digest(predecessor.scope_binding.to_dict()),
            "formation_snapshot_digest": canonical_digest(predecessor.formation_snapshot.to_dict()),
            "strength_digest": canonical_digest(predecessor.strength.to_dict()),
            "from_revision": predecessor.memory_revision,
            "to_revision": successor.memory_revision,
            "from_lifecycle_state": predecessor.lifecycle_state,
            "to_lifecycle_state": successor.lifecycle_state,
            "predecessor_revision_digest": canonical_digest(predecessor.to_dict()),
            "predecessor_block_id": proposal.expected_block_id,
            "predecessor_authorization_kind": predecessor.authorization_kind,
            "predecessor_authorization_id": predecessor.authorization_id,
            "current_authorization_kind": proposal.expected_current_authorization_kind,
            "current_authorization_id": proposal.expected_current_authorization_id,
            "current_authorization_digest": proposal.expected_current_authorization_digest,
            "successor_revision_digest": canonical_digest(successor.to_dict()),
            "transition_id": identity.transition_id, "receipt_id": identity.receipt_id,
            "authorization_class": proposal.authorization_class,
            "authorization_id": proposal.authorization_id,
            "reason_category": proposal.reason_category,
            "policy_revision": proposal.policy_revision,
            "current_receipt_id": proposal.expected_current_receipt_id,
            "current_receipt_digest": proposal.expected_current_receipt_digest,
            "current_selector_id": proposal.expected_current_selector_id,
            "current_selector_digest": proposal.expected_current_selector_digest,
            "prepared_current_state_digest": canonical_digest(prepared.to_dict()),
            "page_id": page.page_id, "partition": page.partition,
            "successor_block_id": page.block_id, "pre_image_state": page.pre_image_state,
            "pre_image_digest": page.pre_image_digest, "post_image_digest": page.post_image_digest,
            "successor_block_digest": page.block_digest, "artifact_id": page.artifact_id,
            "artifact_digest": page.post_image_digest,
            "revision_schema": SUBJECTIVE_MEM_REVISION_SCHEMA, "page_schema": PAGE_SCHEMA,
            "block_schema": LIFECYCLE_BLOCK_SCHEMA, "renderer_revision": RENDERER_REVISION,
            "partition_revision": PAGE_PARTITION_REVISION, "platform_revision": PLATFORM_REVISION,
            "prepared_at": at, "recovery_state": "prepared"}


def _finalizer(
    space: str, authority: SubjectiveMemCharacterAuthority,
    identity: SubjectiveMemConsolidateOperationIdentity, intent: dict[str, object] | None,
) -> LifecycleFinalizer:
    def finalize(state: SubjectiveMemCurrentState) -> LifecycleFinalRecords | None:
        if not isinstance(intent, dict):
            return None
        try:
            transition = {"schema": LIFECYCLE_TRANSITION_SCHEMA,
                "transition_id": identity.transition_id, "character_id": authority.character_id,
                "memory_id": intent["memory_id"], "from_revision": intent["from_revision"],
                "to_revision": intent["to_revision"], "operation": _OPERATION,
                "from_lifecycle_state": intent["from_lifecycle_state"],
                "to_lifecycle_state": intent["to_lifecycle_state"],
                "from_formation_stage": intent["from_formation_stage"],
                "to_formation_stage": intent["to_formation_stage"],
                "authorized_by": intent["authorization_class"], "committed_at": intent["prepared_at"]}
            receipt_body = {"schema": LIFECYCLE_RECEIPT_SCHEMA,
                "receipt_id": identity.receipt_id, "intent_id": identity.intent_id,
                "intent_digest": canonical_digest(intent), "operation_id": identity.operation_id,
                "operation_kind": _OPERATION, "operation_outcome": "committed",
                "input_digest": identity.input_digest, "evidence_space_id": space,
                "character_id": authority.character_id,
                "memory_ref": {"memory_id": intent["memory_id"], "memory_revision": intent["to_revision"]},
                "predecessor_revision": intent["from_revision"], "transition_id": identity.transition_id,
                "authorization_class": intent["authorization_class"],
                "authorization_id": intent["authorization_id"],
                "reason_category": intent["reason_category"], "policy_revision": intent["policy_revision"],
                "revision_schema": intent["revision_schema"], "page_schema": intent["page_schema"],
                "block_schema": intent["block_schema"], "renderer_revision": intent["renderer_revision"],
                "partition_revision": intent["partition_revision"],
                "platform_revision": intent["platform_revision"], "page_id": intent["page_id"],
                "successor_block_id": intent["successor_block_id"],
                "pre_image_digest": intent["pre_image_digest"],
                "post_image_digest": intent["post_image_digest"],
                "successor_revision_digest": intent["successor_revision_digest"],
                "current_state_digest": canonical_digest(state.to_dict()),
                "projection_state": "rebuild_required", "ordinary_retrieval_wired": False,
                "finalized_at": intent["prepared_at"]}
            receipt = {**receipt_body, "receipt_digest": canonical_digest(receipt_body)}
            finalization = {"schema": LIFECYCLE_INTENT_FINALIZATION_SCHEMA,
                "finalization_id": _opaque("smcintentfin", identity.intent_id),
                "intent_id": identity.intent_id, "intent_digest": canonical_digest(intent),
                "receipt_id": identity.receipt_id, "receipt_digest": receipt["receipt_digest"],
                "status": "finalized", "finalized_at": intent["prepared_at"]}
            result_body = {"schema": LIFECYCLE_RESULT_SCHEMA, "result_id": identity.result_id,
                "operation_slot_id": identity.operation_slot_id, "operation_id": identity.operation_id,
                "operation_kind": _OPERATION, "input_digest": identity.input_digest,
                "receipt_id": identity.receipt_id, "receipt_digest": receipt["receipt_digest"],
                "transition_id": identity.transition_id, "memory_id": intent["memory_id"],
                "from_revision": intent["from_revision"], "to_revision": intent["to_revision"],
                "page_id": intent["page_id"], "post_image_digest": intent["post_image_digest"],
                "current_selector_id": intent["current_selector_id"],
                "current_state_digest": canonical_digest(state.to_dict()), "status": "committed",
                "finalized_at": intent["prepared_at"]}
            result = {**result_body, "result_digest": canonical_digest(result_body)}
            projection = {"schema": "relaylm.subjective_mem_projection_state.v1",
                "memory_id": intent["memory_id"], "memory_revision": intent["to_revision"],
                "projection_state": "rebuild_required", "ordinary_retrieval_wired": False,
                "updated_at": intent["prepared_at"]}
            return LifecycleFinalRecords(transition, receipt, finalization, result, projection)
        except (KeyError, TypeError, ValueError):
            return None
    return finalize


def _expectation(p: SubjectiveMemConsolidateProposal) -> SubjectiveMemPredecessorExpectation:
    return SubjectiveMemPredecessorExpectation(
        receipt_id=p.expected_current_receipt_id, receipt_digest=p.expected_current_receipt_digest,
        current_state_digest=p.expected_current_selector_digest, page_id=p.expected_page_id,
        block_id=p.expected_block_id, page_digest=p.expected_page_digest,
        revision_schema=p.expected_revision_schema, page_schema=p.expected_page_schema,
        block_schema=p.expected_block_schema, renderer_revision=p.expected_renderer_revision,
        partition_revision=p.expected_partition_revision, platform_revision=p.expected_platform_revision)


def _selector(tx: EvidenceStoreTransaction, p: SubjectiveMemConsolidateProposal, character_id: str) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    events = tx.read_log(log_kind=_CURRENT, key=p.expected_current_selector_id)
    if not isinstance(events, list) or len(events) != 1 or not isinstance(events[0], dict):
        return None, ("subjective_mem_consolidate_current_selector_missing_or_corrupt",)
    raw = events[0]
    state = _state(raw)
    if (state is None or state.memory_state_id != p.expected_current_selector_id
            or state.memory_id != p.expected_memory_id or state.character_id != character_id
            or state.current_revision != p.expected_current_revision
            or state.lifecycle_state != p.expected_lifecycle_state
            or state.mutation_state != p.expected_mutation_state or not state.retrieval_eligible
            or canonical_digest(raw) != p.expected_current_selector_digest):
        return None, ("subjective_mem_consolidate_current_selector_not_exact",)
    matches = [(key, bodies) for key, bodies in tx.list_logs(log_kind=_CURRENT, limit=4096)
               if any(item.get("character_id") == character_id and item.get("memory_id") == p.expected_memory_id for item in bodies)]
    if matches != [(p.expected_current_selector_id, [raw])]:
        return None, ("subjective_mem_lifecycle_duplicate_logical_current_selector",)
    return raw, ()


def _state(raw: object) -> SubjectiveMemCurrentState | None:
    if not isinstance(raw, dict):
        return None
    binding = raw.get("authority_binding")
    if binding is not None and not isinstance(binding, dict):
        return None
    auth = binding.get("authorization_ref") if isinstance(binding, dict) else None
    if auth is not None and not isinstance(auth, dict):
        return None
    try:
        state = SubjectiveMemCurrentState(memory_state_id=raw["memory_state_id"],
            memory_id=raw["memory_id"], character_id=raw["character_id"],
            current_revision=raw["current_revision"], lifecycle_state=raw["lifecycle_state"],
            mutation_state=raw["mutation_state"], retrieval_eligible=raw["retrieval_eligible"],
            updated_at=raw["updated_at"],
            workspace_authority_digest=(binding.get("workspace_authority_digest") if isinstance(binding, dict) else None),
            scope_binding_digest=(binding.get("scope_binding_digest") if isinstance(binding, dict) else None),
            page_id=(binding.get("page_id") if isinstance(binding, dict) else None),
            block_id=(binding.get("block_id") if isinstance(binding, dict) else None),
            canonical_page_digest=(binding.get("canonical_page_digest") if isinstance(binding, dict) else None),
            authorization_kind=(auth.get("authority_kind") if isinstance(auth, dict) else None),
            authorization_id=(auth.get("authority_id") if isinstance(auth, dict) else None),
            current_receipt_id=(binding.get("current_receipt_id") if isinstance(binding, dict) else None))
    except (KeyError, TypeError, ValueError):
        return None
    return state if state.to_dict() == raw else None


def _prepared_state(intent: dict[str, object]) -> SubjectiveMemCurrentState | None:
    raw = {"schema": "relaylm.subjective_mem_current_state.v2",
           "memory_state_id": intent.get("current_selector_id"), "memory_id": intent.get("memory_id"),
           "character_id": intent.get("character_id"), "current_revision": intent.get("from_revision"),
           "lifecycle_state": intent.get("from_lifecycle_state"), "mutation_state": "prepared",
           "retrieval_eligible": False, "updated_at": intent.get("prepared_at"),
           "authority_binding": {"workspace_authority_digest": intent.get("workspace_authority_digest"),
             "scope_binding_digest": intent.get("scope_binding_digest"), "page_id": intent.get("page_id"),
             "block_id": intent.get("predecessor_block_id"), "canonical_page_digest": intent.get("pre_image_digest"),
             "authorization_ref": {"authority_kind": intent.get("predecessor_authorization_kind"),
                                   "authority_id": intent.get("predecessor_authorization_id")},
             "current_receipt_id": intent.get("current_receipt_id")}}
    state = _state(raw)
    return state if state is not None and canonical_digest(raw) == intent.get("prepared_current_state_digest") else None


def _predecessor_exact(
    r: SubjectiveMemRevision, state: SubjectiveMemCurrentState,
    p: SubjectiveMemConsolidateProposal, authority: SubjectiveMemCharacterAuthority,
    workspace: str, at: str,
) -> bool:
    from_state, _to_state, from_stage, _to_stage = subjective_mem_consolidate_transition()
    return (r.character_id == authority.character_id and r.lifecycle_state == from_state
        and r.retrieval_visible is True and r.memory_kind == p.expected_memory_kind
        and r.formation_stage == from_stage
        and r.formation_stage == p.expected_formation_stage
        and r.memory_id == p.expected_memory_id
        and r.memory_revision == p.expected_current_revision
        and canonical_digest(r.scope_binding.to_dict()) == p.expected_scope_binding_digest
        and canonical_digest(r.formation_snapshot.to_dict()) == p.expected_formation_snapshot_digest
        and canonical_digest(r.strength.to_dict()) == p.expected_strength_digest
        and (state.workspace_authority_digest == _workspace_digest(workspace, authority)
             or (p.expected_current_revision == 1 and not state.authority_bound))
        and _after(at, r.created_at, state.updated_at))


def _predecessor_authorization_exact(
    r: SubjectiveMemRevision, p: SubjectiveMemConsolidateProposal,
    loaded: SubjectiveMemPredecessorAuthority,
) -> bool:
    """Bind the proposal's generic current authorization to the exact loaded authority."""

    receipt = loaded.receipt
    lineage = (
        r.authorization_id == receipt.get("decision_id")
        if p.expected_current_revision == 1
        else (
            r.authorization_id == receipt.get("transition_id")
            and receipt.get("successor_revision_digest") == canonical_digest(r.to_dict())
        )
    )
    return (
        lineage
        and loaded.authorization_kind == p.expected_current_authorization_kind
        and r.authorization_id == p.expected_current_authorization_id
        and canonical_digest(loaded.authorization_record)
        == p.expected_current_authorization_digest
    )


def _intent_exact(i: dict[str, object], identity: SubjectiveMemConsolidateOperationIdentity,
                  p: SubjectiveMemConsolidateProposal, authority: SubjectiveMemCharacterAuthority,
                  space: str, workspace: str) -> bool:
    from_state, to_state, from_stage, to_stage = subjective_mem_consolidate_transition()
    try:
        page_id, _, partition = subjective_mem_page_identity(
            character_id=authority.character_id, memory_kind=p.expected_memory_kind)
        at = str(i["prepared_at"])
        post = str(i["post_image_digest"])
    except (KeyError, TypeError, ValueError):
        return False
    expected = {"schema": LIFECYCLE_INTENT_SCHEMA, "intent_id": identity.intent_id,
        "operation_slot_id": identity.operation_slot_id, "operation_id": identity.operation_id,
        "operation_kind": _OPERATION, "operation_key_digest": identity.operation_key_digest,
        "input_digest": identity.input_digest, "evidence_space_id": space,
        "character_id": authority.character_id, "character_authority_digest": canonical_digest(authority.to_dict()),
        "workspace_authority_digest": _workspace_digest(workspace, authority),
        "memory_id": p.expected_memory_id, "memory_kind": p.expected_memory_kind,
        "from_formation_stage": from_stage, "to_formation_stage": to_stage,
        "scope_binding_digest": p.expected_scope_binding_digest,
        "formation_snapshot_digest": p.expected_formation_snapshot_digest,
        "strength_digest": p.expected_strength_digest,
        "from_revision": p.expected_current_revision, "to_revision": p.expected_current_revision + 1,
        "from_lifecycle_state": from_state, "to_lifecycle_state": to_state,
        "predecessor_block_id": p.expected_block_id, "transition_id": identity.transition_id,
        "receipt_id": identity.receipt_id, "authorization_class": p.authorization_class,
        "authorization_id": p.authorization_id, "reason_category": p.reason_category,
        "policy_revision": p.policy_revision,
        "current_authorization_kind": p.expected_current_authorization_kind,
        "current_authorization_id": p.expected_current_authorization_id,
        "current_authorization_digest": p.expected_current_authorization_digest,
        "current_receipt_id": p.expected_current_receipt_id,
        "current_receipt_digest": p.expected_current_receipt_digest,
        "current_selector_id": p.expected_current_selector_id,
        "current_selector_digest": p.expected_current_selector_digest,
        "page_id": page_id, "partition": partition, "pre_image_state": "present",
        "pre_image_digest": p.expected_page_digest, "artifact_id": "smartifact_" + post.removeprefix("sha256:"),
        "artifact_digest": post, "revision_schema": p.expected_revision_schema,
        "page_schema": p.expected_page_schema, "block_schema": p.expected_block_schema,
        "renderer_revision": p.expected_renderer_revision,
        "partition_revision": p.expected_partition_revision,
        "platform_revision": p.expected_platform_revision, "recovery_state": "prepared"}
    variable = {"predecessor_revision_digest", "predecessor_authorization_kind",
        "predecessor_authorization_id", "successor_revision_digest",
        "prepared_current_state_digest", "successor_block_id", "successor_block_digest",
        "post_image_digest", "prepared_at"}
    return set(i) == set(expected) | variable and all(i.get(k) == v for k, v in expected.items()) and i.get("input_digest") == canonical_digest(
        {"proposal_input_digest": p.input_digest, "operation_time": at})


def _artifact_predecessor(data: bytes, i: dict[str, object], p: SubjectiveMemConsolidateProposal,
                          authority: SubjectiveMemCharacterAuthority) -> SubjectiveMemRevision | None:
    try:
        _, _, partition = subjective_mem_page_identity(
            character_id=authority.character_id, memory_kind=p.expected_memory_kind)
        page, errors = parse_subjective_mem_page_bytes(data, expected_page_id=p.expected_page_id,
            expected_character_id=authority.character_id, expected_partition=partition)
        if page is None or errors:
            return None
        before = next(x for x in page.blocks if x.revision.memory_id == p.expected_memory_id and x.revision.memory_revision == p.expected_current_revision)
        after = next(x for x in page.blocks if x.revision.memory_id == p.expected_memory_id and x.revision.memory_revision == p.expected_current_revision + 1)
    except (StopIteration, TypeError, ValueError):
        return None
    a, b = before.revision, after.revision
    preserved = replace(b, decision_id=a.decision_id, created_at=a.created_at,
        memory_revision=a.memory_revision, formation_stage=a.formation_stage,
        predecessor_revision_or_null=a.predecessor_revision_or_null,
        authorization_kind=a.authorization_kind).to_dict() == a.to_dict()
    exact = (before.block_id == p.expected_block_id
        and canonical_digest(a.to_dict()) == i.get("predecessor_revision_digest")
        and after.block_id == i.get("successor_block_id") and after.block_digest == i.get("successor_block_digest")
        and canonical_digest(b.to_dict()) == i.get("successor_revision_digest") and preserved
        and b.lifecycle_state == i.get("to_lifecycle_state")
        and b.formation_stage == i.get("to_formation_stage")
        and b.predecessor_revision_or_null == a.memory_revision
        and b.authorization_kind == "lifecycle_transition" and b.authorization_id == i.get("transition_id")
        and canonical_page_digest(data) == i.get("post_image_digest"))
    return a if exact else None


def _request_errors(store: object, config: object, authority: object, workspace: object,
                    proposal: object, apply: object, fault: object) -> list[str]:
    errors: list[str] = []
    if type(store) is not EvidenceRecordStore:
        errors.append("subjective_mem_consolidate_store_invalid")
    if type(authority) is not SubjectiveMemCharacterAuthority:
        errors.append("subjective_mem_consolidate_character_authority_invalid")
    else:
        current, reasons = resolve_subjective_mem_character_authority(config,
            workspace_or_tenant_ref=authority.workspace_or_tenant_ref, character_id=authority.character_id)
        errors.extend(reasons)
        if current != authority:
            errors.append("subjective_mem_consolidate_character_authority_not_exact_current")
    if type(proposal) is not SubjectiveMemConsolidateProposal:
        errors.append("subjective_mem_consolidate_proposal_invalid")
    else:
        errors.extend(validate_subjective_mem_consolidate_proposal(proposal))
        if (proposal.expected_revision_schema, proposal.expected_page_schema, proposal.expected_block_schema,
            proposal.expected_renderer_revision, proposal.expected_partition_revision, proposal.expected_platform_revision) != (
            SUBJECTIVE_MEM_REVISION_SCHEMA, PAGE_SCHEMA, LIFECYCLE_BLOCK_SCHEMA, RENDERER_REVISION,
            PAGE_PARTITION_REVISION, PLATFORM_REVISION):
            errors.append("subjective_mem_consolidate_contract_revision_mismatch")
    if type(apply) is not bool:
        errors.append("subjective_mem_consolidate_apply_mode_invalid")
    elif apply and not secure_platform_supported():
        errors.append("subjective_mem_consolidate_platform_unsupported")
    if not isinstance(workspace, str) or not workspace:
        errors.append("subjective_mem_consolidate_workspace_root_missing")
    elif not Path(workspace).is_absolute():
        errors.append("subjective_mem_consolidate_workspace_root_not_absolute")
    elif not isinstance(getattr(config, "subjective_mem_workspace_root", None), str) or Path(getattr(config, "subjective_mem_workspace_root")) != Path(workspace):
        errors.append("subjective_mem_consolidate_workspace_authority_changed")
    if fault is not None and not callable(fault):
        errors.append("subjective_mem_consolidate_fault_injector_invalid")
    return errors


def _from_outcome(outcome: LifecycleExecutionOutcome,
                  identity: SubjectiveMemConsolidateOperationIdentity,
                  proposal: SubjectiveMemConsolidateProposal) -> SubjectiveMemConsolidateResult:
    status: ConsolidateStatus = _status(outcome.reasons) if outcome.status == "fail_closed" else outcome.status  # type: ignore[assignment]
    return _result(status, identity=identity, proposal=proposal,
        current_state=outcome.current_state, reasons=outcome.reasons,
        recovery_outcome=outcome.recovery_outcome,
        canonical_published=outcome.canonical_page_published,
        receipt_present=outcome.lifecycle_receipt_present, persisted=outcome.persisted)


def _result(status: ConsolidateStatus, *,
            identity: SubjectiveMemConsolidateOperationIdentity | None = None,
            proposal: SubjectiveMemConsolidateProposal | None = None,
            current_state: SubjectiveMemCurrentState | None = None,
            reasons: tuple[str, ...] = (), recovery_outcome: str | None = None,
            canonical_published: bool = False, receipt_present: bool = False,
            persisted: bool = False) -> SubjectiveMemConsolidateResult:
    _from_state, _to_state, from_stage, to_stage = subjective_mem_consolidate_transition()
    return SubjectiveMemConsolidateResult(status, _OPERATION,
        identity.transition_id if identity else None, identity.receipt_id if identity else None,
        proposal.expected_memory_id if proposal else None,
        proposal.expected_current_revision if proposal else None,
        proposal.expected_current_revision + 1 if proposal else None,
        from_stage if proposal else None, to_stage if proposal else None,
        current_state, tuple(dict.fromkeys(reasons)), recovery_outcome,
        canonical_published, receipt_present, persisted)


def _conflict(identity: SubjectiveMemConsolidateOperationIdentity,
              proposal: SubjectiveMemConsolidateProposal) -> SubjectiveMemConsolidateResult:
    return _result("integrity_conflict", identity=identity, proposal=proposal,
                   reasons=("subjective_mem_lifecycle_idempotency_conflict",))


def _corrupt(identity: SubjectiveMemConsolidateOperationIdentity,
             proposal: SubjectiveMemConsolidateProposal) -> SubjectiveMemConsolidateResult:
    return _result("fail_closed", identity=identity, proposal=proposal,
                   reasons=("subjective_mem_consolidate_intent_corrupt",))


def _gate_triple_mode(config: object, gate: str) -> str | None:
    """Resolve one exact existing gate triple, or None when it is unsupported."""

    triple = tuple(
        getattr(config, f"subjective_mem_{gate}_{field}", None) for field in _GATE_FIELDS
    )
    if any(type(value) is not bool for value in triple):
        return None
    return _GATE_MODES.get(triple)


def _gate_mode_or_errors(
    config: object, apply_enabled: bool
) -> tuple[str | None, tuple[str, ...]]:
    """Enforce the exact lifecycle and lower-commit gate authority for this operation.

    Publication requires the exact lifecycle apply triple, the exact lower
    Subjective MEM commit apply triple, and a caller that asks to apply.  A
    caller can never escalate a configured dry-run mode, and any malformed,
    unsupported, or dependency-incoherent pair fails closed before a read.
    """

    lifecycle = _gate_triple_mode(config, "lifecycle")
    commit = _gate_triple_mode(config, "commit")
    if lifecycle is None or commit is None:
        return None, ("subjective_mem_consolidate_gate_configuration_invalid",)
    if lifecycle == "disabled":
        return "disabled", ()
    if commit == "disabled":
        return None, ("subjective_mem_consolidate_commit_gate_not_enabled",)
    if lifecycle == "apply" and commit != "apply":
        return None, ("subjective_mem_consolidate_commit_gate_not_apply_enabled",)
    if apply_enabled and lifecycle != "apply":
        return None, ("subjective_mem_consolidate_apply_not_configured",)
    return lifecycle, ()


def _workspace_digest(workspace: str, authority: SubjectiveMemCharacterAuthority) -> str:
    return canonical_digest({"workspace_root_digest": sha256_hex(workspace.encode()),
                             "character_authority": authority.to_dict()})


def _space_present(store: EvidenceRecordStore, space: str) -> bool:
    path = store.root / space
    try:
        return path.is_dir() and not path.is_symlink()
    except OSError:
        return False


def _after(candidate: str, *earlier: str) -> bool:
    try:
        return all(_utc_text(candidate) > _utc_text(item) for item in earlier)
    except (TypeError, ValueError):
        return False


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError
    return value.astimezone(timezone.utc)


def _utc_text(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError
    return parsed.astimezone(timezone.utc)


def _status(errors: tuple[str, ...]) -> ConsolidateStatus:
    if any("idempotency_conflict" in x for x in errors):
        return "integrity_conflict"
    if any("recovery" in x or "foreign_image" in x for x in errors):
        return "recovery_required"
    if any("lock_busy" in x for x in errors):
        return "lock_busy"
    return "fail_closed"


def _opaque(prefix: str, value: str) -> str:
    return f"{prefix}_{sha256_hex(value.encode())}"


def _fault(injector: FaultInjector | None, stage: str) -> None:
    if injector is not None:
        injector(stage)


__all__ = ["SubjectiveMemConsolidateResult", "consolidate_subjective_mem"]
