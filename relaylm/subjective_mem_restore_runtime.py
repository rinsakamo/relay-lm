"""LC-1D write-free Subjective MEM Restore preflight.

This Draft-PR slice validates one exact ``hidden -> active`` Restore request and
plans its immutable successor without writing the canonical page or Evidence
store. Publication, tombstone-release finalization, replay, and recovery remain
later commits in the same LC-1D PR.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from relaylm._subjective_mem_commit_io import PLATFORM_REVISION, inspect_canonical_page
from relaylm.evidence_common import canonical_digest, sha256_hex
from relaylm.evidence_store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.subjective_mem import (
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCharacterAuthority,
    SubjectiveMemCurrentState,
    SubjectiveMemRevision,
    resolve_subjective_mem_character_authority,
)
from relaylm.subjective_mem_lifecycle import LIFECYCLE_POLICY_REVISION
from relaylm.subjective_mem_lifecycle_authority import (
    SubjectiveMemPredecessorExpectation,
    load_subjective_mem_predecessor_authority_locked,
)
from relaylm.subjective_mem_lifecycle_engine import (
    LifecyclePublicationPlan, LogBinding, RecordBinding, validate_lifecycle_plan,
)
from relaylm.subjective_mem_markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    SubjectiveMemPagePlan,
    parse_subjective_mem_page_bytes,
    plan_subjective_mem_revision_successor,
    subjective_mem_page_identity,
)
from relaylm.subjective_mem_reformation import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
    inspect_subjective_mem_reformation_digest_locked, subjective_mem_semantic_identity_digest,
)
from relaylm.subjective_mem_restore import (
    SubjectiveMemRestoreOperationIdentity,
    SubjectiveMemRestoreProposal,
    derive_subjective_mem_restore_operation_identity,
    validate_subjective_mem_restore_proposal,
)
from relaylm.subjective_mem_restore_plan import (
    SubjectiveMemRestorePlanInputs, build_subjective_mem_restore_lifecycle_plan,
)
from relaylm.subjective_mem_tombstone_release import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
)

RestoreStatus = Literal["dry_run_ready", "fail_closed", "integrity_conflict"]
_CURRENT = "subjective_mem_current_state"
_TOMBSTONE = "subjective_mem_forget_tombstone"


@dataclass(frozen=True)
class _Bound:
    current: SubjectiveMemCurrentState
    records: tuple[RecordBinding, ...]
    logs: tuple[LogBinding, ...]


@dataclass(frozen=True)
class _Prepared:
    current: SubjectiveMemCurrentState
    prepared: SubjectiveMemCurrentState
    predecessor: SubjectiveMemRevision
    successor: SubjectiveMemRevision
    page: SubjectiveMemPagePlan
    plan: LifecyclePublicationPlan


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
    persisted: bool = False

    def to_log_dict(self) -> dict[str, object]:
        state = self.current_state
        return {
            "status": self.status,
            "operation_kind": self.operation_kind,
            "transition_id": self.transition_id,
            "receipt_id": self.receipt_id,
            "release_id": self.release_id,
            "memory_id": self.memory_id,
            "from_revision": self.from_revision,
            "to_revision": self.to_revision,
            "lifecycle_state": state.lifecycle_state if state else None,
            "mutation_state": state.mutation_state if state else None,
            "retrieval_eligible": state.retrieval_eligible if state else False,
            "canonical_markdown_published": False,
            "lifecycle_receipt_present": False,
            "tombstone_release_present": False,
            "ordinary_retrieval_wired": False,
            "primary_mem_migrated": False,
            "background_recovery_started": False,
            "persisted": False,
            "content_free": True,
            "path_values_included": False,
            "digest_values_included": False,
            "raw_key_included": False,
            "exception_text_included": False,
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
    prepared, reasons = _prepare(
        store, evidence_space_id, character_authority, workspace_root,
        proposal, identity, operation_time.isoformat(),
    )
    if prepared is None:
        return _result(
            "fail_closed", identity=identity, proposal=proposal, reasons=reasons
        )
    if apply_enabled:
        return _result(
            "fail_closed", identity=identity, proposal=proposal,
            current=prepared.current, post_digest=prepared.plan.post_image_digest,
            reasons=("subjective_mem_restore_apply_not_implemented",),
        )
    return _result(
        "dry_run_ready", identity=identity, proposal=proposal,
        current=prepared.current, post_digest=prepared.plan.post_image_digest,
    )


def _prepare(
    store: EvidenceRecordStore,
    space: str,
    authority: SubjectiveMemCharacterAuthority,
    workspace: str,
    proposal: SubjectiveMemRestoreProposal,
    identity: SubjectiveMemRestoreOperationIdentity,
    committed_at: str,
) -> tuple[_Prepared | None, tuple[str, ...]]:
    predecessor, page_bytes, errors = _page_predecessor(workspace, authority, proposal)
    if predecessor is None or page_bytes is None:
        return None, errors
    bound, errors = _stored_authority(store, space, authority, proposal, predecessor)
    if bound is None:
        return None, errors
    if not _predecessor_exact(
        space, predecessor, bound.current, proposal, authority, workspace, committed_at
    ):
        return None, ("subjective_mem_restore_current_revision_invalid",)
    successor = replace(
        predecessor,
        decision_id=identity.transition_id,
        created_at=committed_at,
        memory_revision=predecessor.memory_revision + 1,
        lifecycle_state="active",
        retrieval_visible=True,
        predecessor_revision_or_null=predecessor.memory_revision,
        authorization_kind="lifecycle_transition",
    )
    planned = plan_subjective_mem_revision_successor(
        predecessor=predecessor, successor=successor, existing_bytes=page_bytes
    )
    if planned.plan is None:
        return None, planned.reasons
    # The hidden selector is fenced by reserving it: only the mutation state and
    # the exact operation time change, and it stays retrieval-ineligible.
    prepared = replace(
        bound.current, mutation_state="prepared", retrieval_eligible=False,
        updated_at=committed_at,
    )
    plan = build_subjective_mem_restore_lifecycle_plan(
        SubjectiveMemRestorePlanInputs(
            evidence_space_id=space,
            character_authority=authority,
            workspace_root=workspace,
            workspace_authority_digest=_workspace_digest(workspace, authority),
            proposal=proposal,
            identity=identity,
            predecessor=predecessor,
            successor=successor,
            current_state=bound.current,
            prepared_state=prepared,
            page=planned.plan,
            record_bindings=bound.records,
            log_bindings=bound.logs,
            prepared_at=committed_at,
        )
    )
    errors = validate_lifecycle_plan(plan)
    if errors:
        return None, errors
    return _Prepared(
        current=bound.current, prepared=prepared, predecessor=predecessor,
        successor=successor, page=planned.plan, plan=plan,
    ), ()


def _page_predecessor(
    workspace: str,
    authority: SubjectiveMemCharacterAuthority,
    proposal: SubjectiveMemRestoreProposal,
) -> tuple[SubjectiveMemRevision | None, bytes | None, tuple[str, ...]]:
    try:
        page_id, relative, partition = subjective_mem_page_identity(
            character_id=authority.character_id,
            memory_kind=proposal.expected_memory_kind,
        )
    except ValueError:
        return None, None, ("subjective_mem_restore_page_identity_invalid",)
    if (page_id, relative) != (
        proposal.expected_page_id, proposal.expected_relative_path
    ):
        return None, None, ("subjective_mem_restore_page_identity_mismatch",)
    inspected = inspect_canonical_page(
        workspace_root=workspace,
        character_id=authority.character_id,
        relative_path=relative,
    )
    if inspected.snapshot is None or inspected.snapshot.data is None:
        return None, None, inspected.reasons or (
            "subjective_mem_restore_canonical_page_missing",
        )
    snapshot = inspected.snapshot
    if snapshot.digest != proposal.expected_page_digest:
        return None, None, ("subjective_mem_restore_page_digest_mismatch",)
    page, reasons = parse_subjective_mem_page_bytes(
        snapshot.data,
        expected_page_id=page_id,
        expected_character_id=authority.character_id,
        expected_partition=partition,
    )
    if page is None:
        return None, None, reasons
    exact = [
        item for item in page.blocks
        if item.revision.memory_id == proposal.expected_memory_id
        and item.revision.memory_revision == proposal.expected_current_revision
    ]
    later = [
        item for item in page.blocks
        if item.revision.memory_id == proposal.expected_memory_id
        and item.revision.memory_revision > proposal.expected_current_revision
    ]
    if len(exact) != 1 or exact[0].block_id != proposal.expected_block_id or later:
        return None, None, ("subjective_mem_restore_current_revision_not_exact",)
    return exact[0].revision, snapshot.data, ()


def _stored_authority(
    store: EvidenceRecordStore,
    space: str,
    authority: SubjectiveMemCharacterAuthority,
    proposal: SubjectiveMemRestoreProposal,
    predecessor: SubjectiveMemRevision,
) -> tuple[_Bound | None, tuple[str, ...]]:
    try:
        with store.transaction(space) as tx:
            current, reasons = _selector(tx, proposal, authority.character_id)
            if current is None:
                return None, reasons
            loaded, reasons = load_subjective_mem_predecessor_authority_locked(
                tx=tx,
                evidence_space_id=space,
                character_authority=authority,
                predecessor=predecessor,
                expectation=_expectation(proposal),
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
        key=proposal.expected_semantic_identity_digest,
    )
    if (
        not isinstance(states, list) or len(states) != 1
        or not isinstance(states[0], dict)
        or states[0].get("tombstone_id") != proposal.expected_forget_tombstone_id
    ):
        return None, ("subjective_mem_restore_forget_tombstone_state_not_exact",)
    released = tx.read_log(
        log_kind=SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
        key=proposal.expected_forget_tombstone_id,
    )
    if released not in (None, []):
        return None, ("subjective_mem_restore_tombstone_release_present",)
    return (
        (SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND,
         proposal.expected_semantic_identity_digest, (states[0],)),
        (SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
         proposal.expected_forget_tombstone_id, ()),
    ), ()


def _selector(
    tx: EvidenceStoreTransaction,
    proposal: SubjectiveMemRestoreProposal,
    character_id: str,
) -> tuple[SubjectiveMemCurrentState | None, tuple[str, ...]]:
    events = tx.read_log(log_kind=_CURRENT, key=proposal.expected_current_selector_id)
    if not isinstance(events, list) or len(events) != 1:
        return None, ("subjective_mem_restore_current_selector_missing_or_corrupt",)
    raw = events[0]
    state = _state(raw)
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
    matches = [
        (key, bodies)
        for key, bodies in tx.list_logs(log_kind=_CURRENT, limit=4096)
        if any(
            item.get("character_id") == character_id
            and item.get("memory_id") == proposal.expected_memory_id
            for item in bodies
        )
    ]
    if matches != [(proposal.expected_current_selector_id, [raw])]:
        return None, ("subjective_mem_lifecycle_duplicate_logical_current_selector",)
    return state, ()


def _forget_lineage(
    tx: EvidenceStoreTransaction,
    space: str,
    character_id: str,
    predecessor: SubjectiveMemRevision,
    proposal: SubjectiveMemRestoreProposal,
    receipt: dict[str, object],
    transition: dict[str, object],
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if (
        receipt.get("operation_kind") != "forget"
        or receipt.get("transition_id") != proposal.expected_forget_transition_id
        or canonical_digest(transition) != proposal.expected_forget_transition_digest
        or transition.get("operation") != "forget"
        or transition.get("to_lifecycle_state") != "hidden"
        or transition.get("to_revision") != proposal.expected_current_revision
        or receipt.get("tombstone_id") != proposal.expected_forget_tombstone_id
        or receipt.get("tombstone_digest")
        != proposal.expected_forget_tombstone_digest
        or receipt.get("semantic_identity_digest")
        != proposal.expected_semantic_identity_digest
    ):
        return None, ("subjective_mem_restore_forget_lineage_not_exact",)
    tombstone = tx.read_record(
        record_kind=_TOMBSTONE, record_id=proposal.expected_forget_tombstone_id
    )
    if not _tombstone_exact(tombstone, space, character_id, predecessor, proposal):
        return None, ("subjective_mem_restore_forget_tombstone_not_exact",)
    check = inspect_subjective_mem_reformation_digest_locked(
        tx=tx,
        evidence_space_id=space,
        character_id=character_id,
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
    store: object,
    config: object,
    authority: object,
    workspace: object,
    proposal: object,
    apply: object,
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
        actual = (
            proposal.expected_revision_schema, proposal.expected_page_schema,
            proposal.expected_block_schema, proposal.expected_renderer_revision,
            proposal.expected_partition_revision, proposal.expected_platform_revision,
        )
        expected = (
            SUBJECTIVE_MEM_REVISION_SCHEMA, PAGE_SCHEMA, LIFECYCLE_BLOCK_SCHEMA,
            RENDERER_REVISION, PAGE_PARTITION_REVISION, PLATFORM_REVISION,
        )
        if actual != expected:
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


def _state(raw: object) -> SubjectiveMemCurrentState | None:
    if not isinstance(raw, dict):
        return None
    binding = raw.get("authority_binding")
    auth = binding.get("authorization_ref") if isinstance(binding, dict) else None
    if not isinstance(binding, dict) or not isinstance(auth, dict):
        return None
    try:
        state = SubjectiveMemCurrentState(
            memory_state_id=raw["memory_state_id"],
            memory_id=raw["memory_id"],
            character_id=raw["character_id"],
            current_revision=raw["current_revision"],
            lifecycle_state=raw["lifecycle_state"],
            mutation_state=raw["mutation_state"],
            retrieval_eligible=raw["retrieval_eligible"],
            updated_at=raw["updated_at"],
            workspace_authority_digest=binding.get("workspace_authority_digest"),
            scope_binding_digest=binding.get("scope_binding_digest"),
            page_id=binding.get("page_id"),
            block_id=binding.get("block_id"),
            canonical_page_digest=binding.get("canonical_page_digest"),
            authorization_kind=auth.get("authority_kind"),
            authorization_id=auth.get("authority_id"),
            current_receipt_id=binding.get("current_receipt_id"),
        )
    except (KeyError, TypeError, ValueError):
        return None
    return state if state.to_dict() == raw else None


def _expectation(
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


def _tombstone_exact(
    raw: object,
    space: str,
    character_id: str,
    predecessor: SubjectiveMemRevision,
    proposal: SubjectiveMemRestoreProposal,
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
        and raw.get("effective") is True
        and raw.get("content_free") is True
    )


def _predecessor_exact(
    space: str,
    predecessor: SubjectiveMemRevision,
    state: SubjectiveMemCurrentState,
    proposal: SubjectiveMemRestoreProposal,
    authority: SubjectiveMemCharacterAuthority,
    workspace: str,
    committed_at: str,
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
        and state.workspace_authority_digest == _workspace_digest(workspace, authority)
        and state.scope_binding_digest == proposal.expected_scope_binding_digest
        and state.page_id == proposal.expected_page_id
        and state.block_id == proposal.expected_block_id
        and state.canonical_page_digest == proposal.expected_page_digest
        and state.authorization_kind == predecessor.authorization_kind
        and state.authorization_id == predecessor.authorization_id
        and state.current_receipt_id == proposal.expected_current_receipt_id
        and _after(committed_at, predecessor.created_at, state.updated_at)
    )


def _workspace_digest(
    workspace: str, authority: SubjectiveMemCharacterAuthority
) -> str:
    return canonical_digest(
        {
            "workspace_root_digest": sha256_hex(workspace.encode("utf-8")),
            "character_authority": authority.to_dict(),
        }
    )


def _space_present(store: EvidenceRecordStore, space: str) -> bool:
    path = store.root / space
    try:
        return path.is_dir() and not path.is_symlink()
    except OSError:
        return False


def _after(candidate: str, *earlier: str) -> bool:
    try:
        current = _utc_text(candidate)
        return all(current > _utc_text(item) for item in earlier)
    except (TypeError, ValueError):
        return False


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("subjective_mem_restore_clock_invalid")
    return value.astimezone(timezone.utc)


def _utc_text(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("subjective_mem_restore_clock_invalid")
    return parsed.astimezone(timezone.utc)


def _result(
    status: RestoreStatus,
    *,
    identity: SubjectiveMemRestoreOperationIdentity | None = None,
    proposal: SubjectiveMemRestoreProposal | None = None,
    current: SubjectiveMemCurrentState | None = None,
    reasons: tuple[str, ...] = (),
    post_digest: str | None = None,
) -> SubjectiveMemRestoreResult:
    return SubjectiveMemRestoreResult(
        status=status,
        transition_id=identity.transition_id if identity else None,
        receipt_id=identity.receipt_id if identity else None,
        release_id=identity.release_id if identity else None,
        memory_id=proposal.expected_memory_id if proposal else None,
        from_revision=proposal.expected_current_revision if proposal else None,
        to_revision=proposal.expected_current_revision + 1 if proposal else None,
        current_state=current,
        blocked_reasons=tuple(dict.fromkeys(reasons)),
        post_image_digest=post_digest,
    )


__all__ = ["SubjectiveMemRestoreResult", "restore_subjective_mem"]
