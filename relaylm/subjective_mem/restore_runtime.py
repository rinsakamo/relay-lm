"""LC-1D Subjective MEM Restore preflight, publication, replay, and recovery.

This Draft-PR slice validates one exact ``hidden -> active`` Restore request,
plans its immutable successor, executes a single fresh apply, resolves an exact
finalized repeat, and carries an exact prepared reservation forward when the
caller asks to apply. The dry-run path stays write-free, and a prepared claim
observed without apply stays pending instead of resuming. Recovery is
caller-invoked and forward-only: no background worker exists here, and an
active successor is never rolled back to its hidden predecessor.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, get_args

from relaylm.subjective_mem.commit_io import PLATFORM_REVISION, inspect_canonical_page
from relaylm.evidence.common import canonical_digest
from relaylm.evidence.store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.subjective_mem.models import (
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCharacterAuthority,
    SubjectiveMemCurrentState,
    SubjectiveMemRevision,
    resolve_subjective_mem_character_authority,
)
from relaylm.subjective_mem.lifecycle import LIFECYCLE_POLICY_REVISION
from relaylm.subjective_mem.lifecycle_authority import (
    load_subjective_mem_predecessor_authority_locked,
)
from relaylm.subjective_mem.lifecycle_engine import (
    LifecycleExecutionOutcome, LifecycleFinalRecords, LifecycleFinalizer,
    LifecyclePublicationPlan, LogBinding, RecordBinding,
    lifecycle_claim_record, publish_lifecycle_post_image,
    read_lifecycle_reservation, read_prepared_post_image,
    reserve_lifecycle_publication, resolve_finalized_replay, validate_lifecycle_plan,
)
from relaylm.subjective_mem.markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
)
from relaylm.subjective_mem.reformation import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
    inspect_subjective_mem_reformation_digest_locked,
)
from relaylm.subjective_mem.restore import (
    SubjectiveMemRestoreOperationIdentity,
    SubjectiveMemRestoreProposal,
    derive_subjective_mem_restore_operation_identity,
    validate_subjective_mem_restore_proposal,
)
from relaylm.subjective_mem.restore_plan import (
    SubjectiveMemRestorePreparedOperation,
    build_subjective_mem_restore_final_records,
    build_subjective_mem_restore_prepared_operation,
    subjective_mem_restore_current_state,
    subjective_mem_restore_predecessor_exact,
    subjective_mem_restore_predecessor_expectation,
    subjective_mem_restore_tombstone_exact,
    subjective_mem_restore_workspace_authority_digest,
)
from relaylm.subjective_mem.restore_replay import (
    build_subjective_mem_restore_replay_plan,
    subjective_mem_restore_page_binding,
    subjective_mem_restore_page_predecessor,
)
from relaylm.subjective_mem.tombstone_release import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
)

RestoreStatus = Literal[
    "dry_run_ready", "committed", "duplicate_finalized", "recovery_pending",
    "recovery_required", "lock_busy", "fail_closed", "integrity_conflict",
]
# every status the shared engine can return: all but the preflight-only dry run
_ENGINE_STATUSES = frozenset(get_args(RestoreStatus)) - {"dry_run_ready"}
_CURRENT = "subjective_mem_current_state"
_TOMBSTONE = "subjective_mem_forget_tombstone"


@dataclass(frozen=True)
class _Bound:
    current: SubjectiveMemCurrentState
    records: tuple[RecordBinding, ...]
    logs: tuple[LogBinding, ...]


@dataclass(frozen=True, repr=False)
class SubjectiveMemRestoreResult:
    status: RestoreStatus
    operation_kind: str = "restore"
    transition_id: str | None = None
    receipt_id: str | None = None
    release_id: str | None = None
    memory_id: str | None = None
    from_revision: int | None = None
    to_revision: int | None = None
    current_state: SubjectiveMemCurrentState | None = None
    blocked_reasons: tuple[str, ...] = ()
    post_image_digest: str | None = None
    canonical_markdown_published: bool = False
    lifecycle_receipt_present: bool = False
    tombstone_release_present: bool = False
    recovery_outcome: str | None = None
    persisted: bool = False

    def to_log_dict(self) -> dict[str, object]:
        state = self.current_state
        return {
            "status": self.status, "operation_kind": self.operation_kind,
            "transition_id": self.transition_id, "receipt_id": self.receipt_id,
            "release_id": self.release_id, "memory_id": self.memory_id,
            "from_revision": self.from_revision, "to_revision": self.to_revision,
            "lifecycle_state": state.lifecycle_state if state else None,
            "mutation_state": state.mutation_state if state else None,
            "retrieval_eligible": state.retrieval_eligible if state else False,
            "canonical_markdown_published": self.canonical_markdown_published,
            "lifecycle_receipt_present": self.lifecycle_receipt_present,
            "tombstone_release_present": self.tombstone_release_present,
            "recovery_outcome": self.recovery_outcome, "persisted": self.persisted,
            "ordinary_retrieval_wired": False, "primary_mem_migrated": False,
            "background_recovery_started": False, "content_free": True,
            "path_values_included": False, "digest_values_included": False,
            "raw_key_included": False, "exception_text_included": False,
        }


def restore_subjective_mem(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_config: object,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    operation_idempotency_key: str,
    proposal: SubjectiveMemRestoreProposal,
    apply_enabled: bool,
    committed_at: datetime,
    observed_at: datetime | None = None,
) -> SubjectiveMemRestoreResult:
    """Validate and plan one exact hidden-to-active Restore operation."""

    reasons = _request_errors(
        store, character_config, character_authority, workspace_root, proposal, apply_enabled
    )
    try:
        operation_time = _utc(committed_at)
        if operation_time > _utc(observed_at or datetime.now(timezone.utc)):
            reasons.append("subjective_mem_restore_time_in_future")
    except (TypeError, ValueError):
        operation_time = None
        reasons.append("subjective_mem_restore_clock_invalid")
    if reasons:
        return _result("fail_closed", reasons=tuple(dict.fromkeys(reasons)))
    assert operation_time is not None
    assert type(store) is EvidenceRecordStore
    assert type(character_authority) is SubjectiveMemCharacterAuthority
    assert type(proposal) is SubjectiveMemRestoreProposal
    if not _space_present(store, evidence_space_id):
        return _result(
            "fail_closed", proposal=proposal,
            reasons=("subjective_mem_restore_evidence_space_unavailable",),
        )
    identity, reasons = derive_subjective_mem_restore_operation_identity(
        evidence_space_id=evidence_space_id,
        character_authority_digest=canonical_digest(character_authority.to_dict()),
        memory_id=proposal.expected_memory_id,
        operation_idempotency_key=operation_idempotency_key,
        proposal=proposal,
        operation_time=operation_time.isoformat(),
    )
    if identity is None:
        status: RestoreStatus = (
            "integrity_conflict"
            if any("idempotency_conflict" in item for item in reasons)
            else "fail_closed"
        )
        return _result(status, proposal=proposal, reasons=reasons)
    claim, intent, final, reasons = read_lifecycle_reservation(
        store=store, evidence_space_id=evidence_space_id,
        operation_slot_id=identity.operation_slot_id, intent_id=identity.intent_id,
        result_id=identity.result_id,
    )
    if reasons:
        return _result(
            "fail_closed", identity=identity, proposal=proposal, reasons=reasons
        )
    if claim is not None or intent is not None or final is not None:
        return _existing_operation(
            store, evidence_space_id, character_authority, workspace_root,
            claim=claim, intent=intent, final=final, identity=identity,
            proposal=proposal, apply_enabled=apply_enabled,
        )
    prepared, reasons = _prepare(
        store, evidence_space_id, character_authority, workspace_root,
        proposal, identity, operation_time.isoformat(),
    )
    if prepared is None:
        return _result(
            "fail_closed", identity=identity, proposal=proposal, reasons=reasons
        )
    if apply_enabled:
        return _apply(store, prepared, identity=identity, proposal=proposal)
    return _result(
        "dry_run_ready", identity=identity, proposal=proposal,
        current=prepared.current, post_digest=prepared.plan.post_image_digest,
    )


def _prepare(
    store: EvidenceRecordStore, space: str,
    authority: SubjectiveMemCharacterAuthority, workspace: str,
    proposal: SubjectiveMemRestoreProposal,
    identity: SubjectiveMemRestoreOperationIdentity, committed_at: str,
) -> tuple[SubjectiveMemRestorePreparedOperation | None, tuple[str, ...]]:
    predecessor, page_bytes, errors = _page_predecessor(workspace, authority, proposal)
    if predecessor is None or page_bytes is None:
        return None, errors
    bound, errors = _stored_authority(store, space, authority, proposal, predecessor)
    if bound is None:
        return None, errors
    if not subjective_mem_restore_predecessor_exact(
        space, predecessor, bound.current, proposal, authority, workspace, committed_at
    ):
        return None, ("subjective_mem_restore_current_revision_invalid",)
    prepared, errors = build_subjective_mem_restore_prepared_operation(
        evidence_space_id=space, character_authority=authority,
        workspace_root=workspace, proposal=proposal, identity=identity,
        predecessor=predecessor, current_state=bound.current,
        page_bytes=page_bytes, record_bindings=bound.records,
        log_bindings=bound.logs, prepared_at=committed_at,
    )
    if prepared is None:
        return None, errors
    errors = validate_lifecycle_plan(prepared.plan)
    if errors:
        return None, errors
    return prepared, ()


def _page_predecessor(
    workspace: str, authority: SubjectiveMemCharacterAuthority,
    proposal: SubjectiveMemRestoreProposal,
) -> tuple[SubjectiveMemRevision | None, bytes | None, tuple[str, ...]]:
    binding, reasons = subjective_mem_restore_page_binding(authority, proposal)
    if binding is None:
        return None, None, reasons
    inspected = inspect_canonical_page(
        workspace_root=workspace, character_id=authority.character_id,
        relative_path=binding[1],
    )
    snapshot = inspected.snapshot
    if snapshot is None or snapshot.data is None:
        return None, None, inspected.reasons or (
            "subjective_mem_restore_canonical_page_missing",
        )
    if snapshot.digest != proposal.expected_page_digest:
        return None, None, ("subjective_mem_restore_page_digest_mismatch",)
    predecessor, reasons = subjective_mem_restore_page_predecessor(
        snapshot.data, binding=binding, character_authority=authority,
        proposal=proposal,
    )
    if predecessor is None:
        return None, None, reasons
    return predecessor, snapshot.data, ()


def _stored_authority(
    store: EvidenceRecordStore, space: str,
    authority: SubjectiveMemCharacterAuthority,
    proposal: SubjectiveMemRestoreProposal, predecessor: SubjectiveMemRevision,
) -> tuple[_Bound | None, tuple[str, ...]]:
    try:
        with store.transaction(space) as tx:
            current, reasons = _selector(tx, proposal, authority.character_id)
            if current is None:
                return None, reasons
            loaded, reasons = load_subjective_mem_predecessor_authority_locked(
                tx=tx, evidence_space_id=space, character_authority=authority,
                predecessor=predecessor,
                expectation=subjective_mem_restore_predecessor_expectation(proposal),
            )
            if loaded is None:
                return None, reasons
            tombstone, reasons = _forget_lineage(
                tx, space, authority.character_id, predecessor, proposal,
                loaded.receipt, loaded.authorization_record,
            )
            if tombstone is None:
                return None, reasons
            logs, reasons = _forget_log_bindings(tx, proposal)
            if logs is None:
                return None, reasons
            records = loaded.record_bindings + (
                (_TOMBSTONE, proposal.expected_forget_tombstone_id, tombstone),
            )
            return _Bound(current=current, records=records, logs=logs), ()
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, ("subjective_mem_restore_store_unavailable",)


def _forget_log_bindings(
    tx: EvidenceStoreTransaction, proposal: SubjectiveMemRestoreProposal,
) -> tuple[tuple[LogBinding, ...] | None, tuple[str, ...]]:
    """Bind the exact singleton tombstone state and prove no release exists."""

    states = tx.read_log(
        log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
        key=proposal.expected_semantic_identity_digest)
    if (
        not isinstance(states, list) or len(states) != 1
        or not isinstance(states[0], dict)
        or states[0].get("tombstone_id") != proposal.expected_forget_tombstone_id
    ):
        return None, ("subjective_mem_restore_forget_tombstone_state_not_exact",)
    released = tx.read_log(
        log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
        key=proposal.expected_forget_tombstone_id)
    if released not in (None, []):
        return None, ("subjective_mem_restore_tombstone_release_present",)
    return (
        (SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
         proposal.expected_semantic_identity_digest, (states[0],)),
        (SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
         proposal.expected_forget_tombstone_id, ()),
    ), ()


def _selector(
    tx: EvidenceStoreTransaction, proposal: SubjectiveMemRestoreProposal,
    character_id: str,
) -> tuple[SubjectiveMemCurrentState | None, tuple[str, ...]]:
    events = tx.read_log(log_kind=_CURRENT, key=proposal.expected_current_selector_id)
    if not isinstance(events, list) or len(events) != 1:
        return None, ("subjective_mem_restore_current_selector_missing_or_corrupt",)
    raw = events[0]
    state = subjective_mem_restore_current_state(raw)
    if (
        state is None
        or state.memory_state_id != proposal.expected_current_selector_id
        or state.memory_id != proposal.expected_memory_id
        or state.character_id != character_id
        or state.current_revision != proposal.expected_current_revision
        or state.lifecycle_state != "hidden"
        or state.mutation_state != "none"
        or state.retrieval_eligible is not False
        or canonical_digest(raw) != proposal.expected_current_selector_digest
    ):
        return None, ("subjective_mem_restore_current_selector_not_exact",)
    if not _sole_logical_selector(tx, proposal, character_id, events):
        return None, ("subjective_mem_lifecycle_duplicate_logical_current_selector",)
    return state, ()


def _sole_logical_selector(
    tx: EvidenceStoreTransaction, proposal: SubjectiveMemRestoreProposal,
    character_id: str, expected: list[object],
) -> bool:
    """Prove exactly one durable selector owns this logical memory right now.

    Fresh preparation, finalized replay, and forward recovery all rest on the
    same singleton: another selector for the same logical memory means the
    operation may no longer publish or prove anything about it.
    """

    matches = [
        (key, bodies)
        for key, bodies in tx.list_logs(log_kind=_CURRENT, limit=4096)
        if any(
            item.get("character_id") == character_id
            and item.get("memory_id") == proposal.expected_memory_id
            for item in bodies)
    ]
    return matches == [(proposal.expected_current_selector_id, expected)]


def _forget_lineage(
    tx: EvidenceStoreTransaction, space: str, character_id: str,
    predecessor: SubjectiveMemRevision, proposal: SubjectiveMemRestoreProposal,
    receipt: dict[str, object], transition: dict[str, object],
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if (
        receipt.get("operation_kind") != "forget"
        or receipt.get("transition_id") != proposal.expected_forget_transition_id
        or canonical_digest(transition) != proposal.expected_forget_transition_digest
        or transition.get("operation") != "forget"
        or transition.get("to_lifecycle_state") != "hidden"
        or transition.get("to_revision") != proposal.expected_current_revision
        or receipt.get("tombstone_id") != proposal.expected_forget_tombstone_id
        or receipt.get("tombstone_digest") != proposal.expected_forget_tombstone_digest
        or receipt.get("semantic_identity_digest")
        != proposal.expected_semantic_identity_digest):
        return None, ("subjective_mem_restore_forget_lineage_not_exact",)
    tombstone = tx.read_record(
        record_kind=_TOMBSTONE, record_id=proposal.expected_forget_tombstone_id
    )
    if not subjective_mem_restore_tombstone_exact(
        tombstone, space, character_id, predecessor, proposal
    ):
        return None, ("subjective_mem_restore_forget_tombstone_not_exact",)
    check = inspect_subjective_mem_reformation_digest_locked(
        tx=tx, evidence_space_id=space, character_id=character_id,
        semantic_identity_digest=proposal.expected_semantic_identity_digest,
    )
    if (
        check.status != "blocked"
        or check.tombstone_ids != (proposal.expected_forget_tombstone_id,)
    ):
        return None, ("subjective_mem_restore_forget_tombstone_not_effective",)
    assert isinstance(tombstone, dict)
    return tombstone, ()


def _request_errors(
    store: object, config: object, authority: object,
    workspace: object, proposal: object, apply: object,
) -> list[str]:
    errors: list[str] = []
    if type(store) is not EvidenceRecordStore:
        errors.append("subjective_mem_restore_store_invalid")
    if type(authority) is not SubjectiveMemCharacterAuthority:
        errors.append("subjective_mem_restore_character_authority_invalid")
    else:
        current, reasons = resolve_subjective_mem_character_authority(
            config,
            workspace_or_tenant_ref=authority.workspace_or_tenant_ref,
            character_id=authority.character_id,
        )
        errors.extend(reasons)
        if current != authority:
            errors.append("subjective_mem_restore_character_authority_not_exact_current")
    if type(proposal) is not SubjectiveMemRestoreProposal:
        errors.append("subjective_mem_restore_proposal_invalid")
    else:
        errors.extend(validate_subjective_mem_restore_proposal(proposal))
        if proposal.policy_revision != LIFECYCLE_POLICY_REVISION:
            errors.append("subjective_mem_restore_policy_revision_invalid")
        if (
            proposal.expected_revision_schema, proposal.expected_page_schema,
            proposal.expected_block_schema, proposal.expected_renderer_revision,
            proposal.expected_partition_revision, proposal.expected_platform_revision,
        ) != (
            SUBJECTIVE_MEM_REVISION_SCHEMA, PAGE_SCHEMA, LIFECYCLE_BLOCK_SCHEMA,
            RENDERER_REVISION, PAGE_PARTITION_REVISION, PLATFORM_REVISION,
        ):
            errors.append("subjective_mem_restore_contract_revision_mismatch")
    if type(apply) is not bool:
        errors.append("subjective_mem_restore_apply_mode_invalid")
    if not isinstance(workspace, str) or not workspace:
        errors.append("subjective_mem_restore_workspace_root_missing")
    elif not Path(workspace).is_absolute():
        errors.append("subjective_mem_restore_workspace_root_not_absolute")
    elif (
        not isinstance(getattr(config, "subjective_mem_workspace_root", None), str)
        or Path(getattr(config, "subjective_mem_workspace_root")) != Path(workspace)
    ):
        errors.append("subjective_mem_restore_workspace_authority_changed")
    return errors


def _space_present(store: EvidenceRecordStore, space: str) -> bool:
    path = store.root / space
    try:
        return path.is_dir() and not path.is_symlink()
    except OSError:
        return False


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("subjective_mem_restore_clock_invalid")
    return value.astimezone(timezone.utc)


def _apply(
    store: EvidenceRecordStore, prepared: SubjectiveMemRestorePreparedOperation, *,
    identity: SubjectiveMemRestoreOperationIdentity,
    proposal: SubjectiveMemRestoreProposal,
) -> SubjectiveMemRestoreResult:
    """Execute one fresh Restore publication through the shared lifecycle engine."""

    plan, post_image = prepared.plan, prepared.page.rendered_bytes
    reserved = reserve_lifecycle_publication(
        store=store, plan=plan, post_image=post_image
    )
    if reserved.status != "reserved":
        return _from_outcome(reserved, identity=identity, proposal=proposal, plan=plan)
    outcome = publish_lifecycle_post_image(
        store=store, plan=plan, post_image=post_image, finalizer=_finalizer(plan)
    )
    return _from_outcome(outcome, identity=identity, proposal=proposal, plan=plan)


def _existing_operation(
    store: EvidenceRecordStore, space: str,
    authority: SubjectiveMemCharacterAuthority, workspace: str, *,
    claim: object, intent: object, final: object,
    identity: SubjectiveMemRestoreOperationIdentity,
    proposal: SubjectiveMemRestoreProposal, apply_enabled: bool,
) -> SubjectiveMemRestoreResult:
    """Resolve one durable idempotency slot without starting a new reservation.

    Only the two cheap slot-shape rejections live here: proving the durable
    authority itself requires the reconstructed plan, so it belongs to the one
    resume path that every remaining outcome is decided from.
    """

    stored = final if final is not None else claim
    if isinstance(stored, dict) and stored.get("input_digest") != identity.input_digest:
        return _result(
            "integrity_conflict", identity=identity, proposal=proposal, persisted=True,
            reasons=("subjective_mem_lifecycle_idempotency_conflict",),
        )
    if claim is None or (final is None and intent is None):
        return _result(
            "fail_closed", identity=identity, proposal=proposal, persisted=True,
            reasons=("subjective_mem_restore_reservation_slot_not_exact",),
        )
    return _resume(
        store, space, authority, workspace, claim=claim, intent=intent,
        final=final, identity=identity, proposal=proposal,
        apply_enabled=apply_enabled,
    )


def _durable_plan(
    store: EvidenceRecordStore, space: str,
    authority: SubjectiveMemCharacterAuthority, workspace: str, *,
    intent: object, identity: SubjectiveMemRestoreOperationIdentity,
    proposal: SubjectiveMemRestoreProposal,
) -> tuple[LifecyclePublicationPlan | None, tuple[str, ...]]:
    """Read the durable Forget authority and rebuild the exact reserved plan."""

    try:
        with store.transaction(space) as tx:
            descriptor = tx.read_record(
                record_kind="evidence_space_descriptor", record_id="revision-1")
            receipt = tx.read_record(
                record_kind="subjective_mem_lifecycle_receipt",
                record_id=proposal.expected_current_receipt_id,
            )
            transition = tx.read_record(
                record_kind="subjective_mem_lifecycle_transition",
                record_id=proposal.expected_forget_transition_id,
            )
            tombstone = tx.read_record(
                record_kind=_TOMBSTONE,
                record_id=proposal.expected_forget_tombstone_id,
            )
            states = tx.read_log(
                log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
                key=proposal.expected_semantic_identity_digest,
            )
            selector = tx.read_log(
                log_kind=_CURRENT, key=proposal.expected_current_selector_id
            )
            if not isinstance(selector, list) or not _sole_logical_selector(
                tx, proposal, authority.character_id, selector
            ):
                return None, (
                    "subjective_mem_lifecycle_duplicate_logical_current_selector",
                )
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, ("subjective_mem_restore_store_unavailable",)
    return build_subjective_mem_restore_replay_plan(
        intent=intent, identity=identity, proposal=proposal,
        evidence_space_id=space, character_authority=authority,
        workspace_root=workspace,
        workspace_authority_digest=(
            subjective_mem_restore_workspace_authority_digest(workspace, authority)
        ),
        descriptor=descriptor, forget_receipt=receipt,
        forget_transition=transition, tombstone=tombstone, tombstone_state=states,
    )


def _resume(
    store: EvidenceRecordStore, space: str,
    authority: SubjectiveMemCharacterAuthority, workspace: str, *,
    claim: object, intent: object, final: object,
    identity: SubjectiveMemRestoreOperationIdentity,
    proposal: SubjectiveMemRestoreProposal, apply_enabled: bool,
) -> SubjectiveMemRestoreResult:
    """Carry one durable Restore reservation forward through the shared engine.

    Every durable outcome is decided from the one reconstructed plan and the
    exact claim it proves: a finalized result is resolved by the shared replay
    resolver regardless of apply mode, a prepared claim stays pending without
    apply, and only an apply-enabled caller republishes the immutable
    post-image. Nothing here reserves again, and nothing rolls an active
    successor back to its hidden predecessor.
    """

    plan, reasons = _durable_plan(
        store, space, authority, workspace,
        intent=intent, identity=identity, proposal=proposal,
    )
    if plan is None or claim != lifecycle_claim_record(plan):
        return _result(
            "fail_closed", identity=identity, proposal=proposal, persisted=True,
            reasons=reasons or ("subjective_mem_restore_reservation_claim_not_exact",),
        )
    if final is not None:
        outcome = resolve_finalized_replay(
            store=store, plan=plan, finalizer=_finalizer(plan)
        )
        if outcome is None:
            return _result(
                "fail_closed", identity=identity, proposal=proposal, persisted=True,
                reasons=("subjective_mem_restore_final_result_incomplete",),
            )
        return _from_outcome(outcome, identity=identity, proposal=proposal, plan=plan)
    if not apply_enabled:
        return _result(
            "recovery_pending", identity=identity, proposal=proposal, persisted=True,
            reasons=("subjective_mem_restore_prepared_recovery_required",),
            recovery_outcome="pre_image_pending_publication",
        )
    artifact, reasons = read_prepared_post_image(
        workspace_root=plan.workspace_root, character_id=plan.character_id,
        artifact_id=plan.artifact_id,
        expected_post_image_digest=plan.post_image_digest,
    )
    if artifact is None:
        return _result(
            "recovery_required", identity=identity, proposal=proposal, persisted=True,
            reasons=reasons or ("subjective_mem_restore_artifact_unavailable",),
            recovery_outcome="artifact_unavailable",
        )
    outcome = publish_lifecycle_post_image(
        store=store, plan=plan, post_image=artifact, finalizer=_finalizer(plan)
    )
    return _from_outcome(outcome, identity=identity, proposal=proposal, plan=plan)


def _finalizer(plan: LifecyclePublicationPlan) -> LifecycleFinalizer:
    """Adapt the deterministic Restore final-record builder for the engine."""

    def finalize(final_state: SubjectiveMemCurrentState) -> LifecycleFinalRecords | None:
        records, _reasons = build_subjective_mem_restore_final_records(
            plan=plan, final_state=final_state
        )
        return records

    return finalize


def _from_outcome(
    outcome: LifecycleExecutionOutcome, *,
    identity: SubjectiveMemRestoreOperationIdentity,
    proposal: SubjectiveMemRestoreProposal, plan: LifecyclePublicationPlan,
) -> SubjectiveMemRestoreResult:
    """Map one bounded engine outcome onto the content-free Restore result."""

    status: RestoreStatus = (
        outcome.status if outcome.status in _ENGINE_STATUSES else "fail_closed"
    )  # type: ignore[assignment]
    # the release is finalized atomically with the receipt, so it is present
    # exactly on a fresh commit or an exact replay
    finalized = outcome.status in {"committed", "duplicate_finalized"}
    return _result(
        status, identity=identity, proposal=proposal, current=outcome.current_state,
        reasons=outcome.reasons, post_digest=plan.post_image_digest,
        published=outcome.canonical_page_published,
        receipt_present=outcome.lifecycle_receipt_present,
        release_present=finalized and outcome.lifecycle_receipt_present,
        recovery_outcome=outcome.recovery_outcome, persisted=outcome.persisted,
    )


def _result(
    status: RestoreStatus, *,
    identity: SubjectiveMemRestoreOperationIdentity | None = None,
    proposal: SubjectiveMemRestoreProposal | None = None,
    current: SubjectiveMemCurrentState | None = None,
    reasons: tuple[str, ...] = (), post_digest: str | None = None,
    published: bool = False, receipt_present: bool = False,
    release_present: bool = False, recovery_outcome: str | None = None,
    persisted: bool = False,
) -> SubjectiveMemRestoreResult:
    return SubjectiveMemRestoreResult(
        status=status,
        transition_id=identity.transition_id if identity else None,
        receipt_id=identity.receipt_id if identity else None,
        release_id=identity.release_id if identity else None,
        memory_id=proposal.expected_memory_id if proposal else None,
        from_revision=proposal.expected_current_revision if proposal else None,
        to_revision=proposal.expected_current_revision + 1 if proposal else None,
        current_state=current, blocked_reasons=tuple(dict.fromkeys(reasons)),
        post_image_digest=post_digest, canonical_markdown_published=published,
        lifecycle_receipt_present=receipt_present,
        tombstone_release_present=release_present,
        recovery_outcome=recovery_outcome, persisted=persisted,
    )


__all__ = ["SubjectiveMemRestoreResult", "restore_subjective_mem"]
