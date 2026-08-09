"""LC-1B caller-invoked Subjective MEM Forget runtime.

This module appends one immutable hidden successor to the canonical Subjective
MEM Markdown page and finalizes one content-free anti-reformation tombstone in
the existing Evidence-space operations store. It reuses the LC-1A selector,
receipt, authority, page-lock, publication, and recovery fences. Anti-reformation
identity and lineage semantics are owned exclusively by
``relaylm.subjective_mem_reformation``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Callable, Literal

from relaylm.subjective_mem.commit_io import (
    PLATFORM_REVISION,
    inspect_canonical_page,
    publish_canonical_page,
    read_immutable_rendered_artifact,
    secure_platform_supported,
    write_immutable_rendered_artifact,
)
from relaylm.evidence.common import canonical_digest, sha256_hex
from relaylm.evidence.store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.subjective_mem.models import (
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCharacterAuthority,
    SubjectiveMemCurrentState,
    SubjectiveMemRevision,
    resolve_subjective_mem_character_authority,
)
from relaylm.subjective_mem_forget import (
    FORGET_REASON_CATEGORIES,
    FORGET_TOMBSTONE_STATE_SCHEMA,
    SubjectiveMemForgetBoundary,
    SubjectiveMemForgetProposal,
    SubjectiveMemForgetTombstone,
)
from relaylm.subjective_mem_lifecycle import (
    LIFECYCLE_CLAIM_SCHEMA,
    LIFECYCLE_INTENT_FINALIZATION_SCHEMA,
    LIFECYCLE_INTENT_SCHEMA,
    LIFECYCLE_POLICY_REVISION,
    LIFECYCLE_RECEIPT_SCHEMA,
    LIFECYCLE_RESULT_SCHEMA,
    LIFECYCLE_TRANSITION_SCHEMA,
    SubjectiveMemLifecycleTransition,
)
from relaylm.subjective_mem_lifecycle_authority import (
    SubjectiveMemPredecessorExpectation,
    load_subjective_mem_predecessor_authority_locked,
)
from relaylm.subjective_mem_lifecycle_runtime import (
    SubjectiveMemLifecycleGate,
    _current_state_from_dict,
    _load_exact_selector_locked,
    _load_exact_selector_locked_raw,
    _validate_selector_uniqueness_locked,
    _workspace_authority_digest,
    resolve_subjective_mem_lifecycle_gate,
)
from relaylm.subjective_mem_markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    SubjectiveMemPagePlan,
    canonical_page_digest,
    parse_subjective_mem_page_bytes,
    plan_subjective_mem_revision_successor,
    subjective_mem_page_identity,
)
from relaylm.subjective_mem_reformation import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_LOG_KIND as _TOMBSTONE_LOG_KIND,
    inspect_subjective_mem_reformation_digest_locked,
    subjective_mem_semantic_identity_digest,
)

ForgetStatus = Literal[
    "disabled",
    "dry_run_ready",
    "committed",
    "duplicate_finalized",
    "recovery_pending",
    "recovery_required",
    "lock_busy",
    "fail_closed",
    "integrity_conflict",
]
FaultInjector = Callable[[str], None]
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")


@dataclass(frozen=True, repr=False)
class SubjectiveMemForgetResult:
    status: ForgetStatus
    operation_kind: str = "forget"
    transition_id: str | None = None
    receipt_id: str | None = None
    tombstone_id: str | None = None
    memory_id: str | None = None
    from_revision: int | None = None
    to_revision: int | None = None
    current_state: SubjectiveMemCurrentState | None = None
    blocked_reasons: tuple[str, ...] = ()
    recovery_outcome: str | None = None
    canonical_markdown_published: bool = False
    lifecycle_receipt_present: bool = False
    tombstone_present: bool = False
    persisted: bool = False
    _post_image_digest: str | None = field(default=None, repr=False, compare=False)

    def to_log_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "operation_kind": self.operation_kind,
            "transition_id": self.transition_id,
            "receipt_id": self.receipt_id,
            "tombstone_id": self.tombstone_id,
            "memory_id": self.memory_id,
            "from_revision": self.from_revision,
            "to_revision": self.to_revision,
            "lifecycle_state": self.current_state.lifecycle_state if self.current_state else None,
            "mutation_state": self.current_state.mutation_state if self.current_state else None,
            "retrieval_eligible": self.current_state.retrieval_eligible if self.current_state else False,
            "canonical_markdown_published": self.canonical_markdown_published,
            "lifecycle_receipt_present": self.lifecycle_receipt_present,
            "anti_reformation_tombstone_present": self.tombstone_present,
            "ordinary_retrieval_wired": False,
            "primary_mem_migrated": False,
            "background_recovery_started": False,
            "purge_authorized": False,
            "recovery_outcome": self.recovery_outcome,
            "persisted": self.persisted,
            "content_free": True,
            "path_values_included": False,
            "digest_values_included": False,
            "raw_key_included": False,
            "exception_text_included": False,
        }


@dataclass(frozen=True)
class _Identity:
    operation_slot_id: str
    operation_id: str
    operation_key_digest: str
    input_digest: str
    transition_id: str
    intent_id: str
    receipt_id: str
    result_id: str
    tombstone_id: str


@dataclass(frozen=True)
class _Prepared:
    identity: _Identity
    predecessor: SubjectiveMemRevision
    successor: SubjectiveMemRevision
    current_state_key: str
    current_state: SubjectiveMemCurrentState
    prepared_state: SubjectiveMemCurrentState
    transition: SubjectiveMemLifecycleTransition
    semantic_identity_digest: str
    plan: SubjectiveMemPagePlan
    intent: dict[str, object]


def forget_subjective_mem(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_config: object,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    operation_idempotency_key: str,
    proposal: SubjectiveMemForgetProposal,
    apply_enabled: bool,
    committed_at: datetime,
    observed_at: datetime | None = None,
    fault_injector: FaultInjector | None = None,
) -> SubjectiveMemForgetResult:
    """Apply or recover one exact active -> hidden Forget operation."""

    reasons: list[str] = []
    if type(store) is not EvidenceRecordStore:
        reasons.append("subjective_mem_forget_store_invalid")
    if type(character_authority) is not SubjectiveMemCharacterAuthority:
        reasons.append("subjective_mem_forget_character_authority_invalid")
    else:
        resolved, authority_reasons = resolve_subjective_mem_character_authority(
            character_config,
            workspace_or_tenant_ref=character_authority.workspace_or_tenant_ref,
            character_id=character_authority.character_id,
        )
        reasons.extend(authority_reasons)
        if resolved != character_authority:
            reasons.append("subjective_mem_forget_character_authority_not_exact_current")
    if type(proposal) is not SubjectiveMemForgetProposal:
        reasons.append("subjective_mem_forget_proposal_invalid")
    if type(apply_enabled) is not bool:
        reasons.append("subjective_mem_forget_apply_mode_invalid")
    elif apply_enabled and not secure_platform_supported():
        reasons.append("subjective_mem_forget_platform_unsupported")
    if type(workspace_root) is not str or not workspace_root:
        reasons.append("subjective_mem_forget_workspace_root_missing")
    elif not Path(workspace_root).is_absolute():
        reasons.append("subjective_mem_forget_workspace_root_not_absolute")
    elif Path(getattr(character_config, "subjective_mem_workspace_root", "")) != Path(
        workspace_root
    ):
        reasons.append("subjective_mem_forget_workspace_authority_changed")
    if fault_injector is not None and not callable(fault_injector):
        reasons.append("subjective_mem_forget_fault_injector_invalid")
    try:
        final_time = _utc(committed_at)
        observed_time = _utc(observed_at or datetime.now(timezone.utc))
        if final_time > observed_time:
            reasons.append("subjective_mem_forget_time_in_future")
    except (TypeError, ValueError):
        final_time = None
        reasons.append("subjective_mem_forget_clock_invalid")
    if reasons:
        return _result("fail_closed", reasons=tuple(dict.fromkeys(reasons)))
    assert final_time is not None and isinstance(proposal, SubjectiveMemForgetProposal)
    if not _evidence_space_directory_present(
        store=store, evidence_space_id=evidence_space_id
    ):
        return _result(
            "fail_closed",
            proposal=proposal,
            reasons=("subjective_mem_forget_evidence_space_unavailable",),
        )

    identity, identity_reasons = _derive_identity(
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        memory_id=proposal.expected_memory_id,
        operation_key=operation_idempotency_key,
        input_digest=canonical_digest(
            {
                "proposal_input_digest": proposal.input_digest,
                "operation_time": final_time.isoformat(),
            }
        ),
    )
    if identity is None:
        return _result("fail_closed", reasons=identity_reasons)

    replay = _resolve_final_replay(
        store=store,
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        workspace_root=workspace_root,
        proposal=proposal,
        identity=identity,
    )
    if replay is not None:
        return replay

    claim, intent = _read_claim_and_intent(
        store=store, evidence_space_id=evidence_space_id, identity=identity
    )
    if claim is not None:
        if claim.get("input_digest") != identity.input_digest:
            return _result(
                "integrity_conflict",
                identity=identity,
                proposal=proposal,
                reasons=("subjective_mem_forget_idempotency_conflict",),
            )
        if intent is None:
            return _result(
                "fail_closed",
                identity=identity,
                proposal=proposal,
                reasons=("subjective_mem_forget_intent_missing_or_corrupt",),
            )
        if (
            intent.get("operation_id") != identity.operation_id
            or claim != _claim_from_intent(identity=identity, intent=intent)
        ):
            return _result(
                "fail_closed",
                identity=identity,
                proposal=proposal,
                reasons=("subjective_mem_forget_intent_corrupt",),
            )
        return _recover_prepared(
            store=store,
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            workspace_root=workspace_root,
            proposal=proposal,
            identity=identity,
            intent=intent,
            fault_injector=fault_injector,
        )

    prepared, prepare_reasons = _prepare_new(
        store=store,
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        workspace_root=workspace_root,
        proposal=proposal,
        identity=identity,
        committed_at=final_time.isoformat(),
    )
    if prepared is None:
        return _result(
            _status_for_reasons(prepare_reasons),
            identity=identity,
            proposal=proposal,
            reasons=prepare_reasons,
        )
    if not apply_enabled:
        return _result(
            "dry_run_ready",
            identity=identity,
            proposal=proposal,
            current_state=prepared.current_state,
            recovery_outcome="new_intent_ready",
            post_digest=prepared.plan.post_image_digest,
        )

    artifact = write_immutable_rendered_artifact(
        workspace_root=workspace_root,
        character_id=character_authority.character_id,
        artifact_id=prepared.plan.artifact_id,
        data=prepared.plan.rendered_bytes,
    )
    if artifact.status not in {"created", "duplicate_existing"}:
        return _result(
            "fail_closed",
            identity=identity,
            proposal=proposal,
            reasons=artifact.reasons,
        )
    try:
        _fault(fault_injector, "after_artifact_before_intent")
    except Exception:
        return _result(
            "fail_closed",
            identity=identity,
            proposal=proposal,
            reasons=("subjective_mem_forget_fault_before_intent",),
        )

    persisted, persist_reasons = _persist_prepared(
        store=store,
        evidence_space_id=evidence_space_id,
        prepared=prepared,
    )
    if not persisted:
        return _result(
            _status_for_reasons(persist_reasons),
            identity=identity,
            proposal=proposal,
            reasons=persist_reasons,
        )
    try:
        _fault(fault_injector, "after_intent_before_page")
    except Exception:
        return _result(
            "recovery_pending",
            identity=identity,
            proposal=proposal,
            current_state=prepared.prepared_state,
            recovery_outcome="pre_image_pending_publication",
            persisted=True,
            post_digest=prepared.plan.post_image_digest,
        )
    return _publish_and_finalize(
        store=store,
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        workspace_root=workspace_root,
        proposal=proposal,
        identity=identity,
        intent=prepared.intent,
        artifact_bytes=prepared.plan.rendered_bytes,
        fault_injector=fault_injector,
    )


def _prepare_new(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    proposal: SubjectiveMemForgetProposal,
    identity: _Identity,
    committed_at: str,
) -> tuple[_Prepared | None, tuple[str, ...]]:
    reasons = list(_validate_proposal(proposal))
    if proposal.expected_lifecycle_state != "active":
        reasons.append("subjective_mem_forget_transition_unsupported")
    if proposal.expected_mutation_state != "none":
        reasons.append("subjective_mem_forget_mutation_in_progress")
    page_id, relative_path, partition = (None, None, None)
    try:
        page_id, relative_path, partition = subjective_mem_page_identity(
            character_id=character_authority.character_id,
            memory_kind=(
                "episodic"
                if "/episodes/" in proposal.expected_relative_path
                else "semantic"
            ),
        )
    except ValueError:
        reasons.append("subjective_mem_forget_page_identity_invalid")
    if page_id != proposal.expected_page_id or relative_path != proposal.expected_relative_path:
        reasons.append("subjective_mem_forget_page_identity_mismatch")
    if reasons:
        return None, tuple(dict.fromkeys(reasons))

    try:
        with store.transaction(evidence_space_id) as tx:
            selector_raw, selector_reasons = _load_exact_selector_locked(
                tx=tx,
                proposal=proposal,  # type: ignore[arg-type]
                character_id=character_authority.character_id,
            )
            if selector_raw is None:
                return None, selector_reasons
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, ("subjective_mem_forget_store_unavailable",)

    inspected = inspect_canonical_page(
        workspace_root=workspace_root,
        character_id=character_authority.character_id,
        relative_path=proposal.expected_relative_path,
    )
    if inspected.snapshot is None or inspected.snapshot.data is None:
        return None, inspected.reasons or ("subjective_mem_forget_canonical_page_missing",)
    snapshot = inspected.snapshot
    if snapshot.digest != proposal.expected_page_digest:
        return None, ("subjective_mem_forget_page_digest_mismatch",)
    page, parse_reasons = parse_subjective_mem_page_bytes(
        snapshot.data,
        expected_page_id=proposal.expected_page_id,
        expected_character_id=character_authority.character_id,
        expected_partition=partition,  # type: ignore[arg-type]
    )
    if page is None:
        return None, parse_reasons
    current = [
        item
        for item in page.blocks
        if item.revision.memory_id == proposal.expected_memory_id
        and item.revision.memory_revision == proposal.expected_current_revision
    ]
    if len(current) != 1 or current[0].block_id != proposal.expected_block_id:
        return None, ("subjective_mem_forget_current_revision_not_exact",)
    predecessor = current[0].revision
    if (
        predecessor.lifecycle_state != "active"
        or predecessor.retrieval_visible is not True
        or predecessor.character_id != character_authority.character_id
        or predecessor.memory_kind != proposal.expected_memory_kind
        or predecessor.formation_stage != proposal.expected_formation_stage
        or canonical_digest(predecessor.scope_binding.to_dict())
        != proposal.expected_scope_binding_digest
        or canonical_digest(predecessor.formation_snapshot.to_dict())
        != proposal.expected_formation_snapshot_digest
        or not _strictly_after(
            committed_at,
            predecessor.created_at,
            str(selector_raw["updated_at"]),
        )
    ):
        return None, ("subjective_mem_forget_current_revision_invalid",)
    try:
        semantic_identity = subjective_mem_semantic_identity_digest(
            evidence_space_id=evidence_space_id,
            character_id=character_authority.character_id,
            grounded_content_digest=predecessor.grounded_content_digest,
            subjective_meaning=predecessor.subjective_meaning,
            memory_kind=predecessor.memory_kind,
            scope_binding=predecessor.scope_binding,
        )
        with store.transaction(evidence_space_id) as tx:
            predecessor_authority, authority_reasons = (
                load_subjective_mem_predecessor_authority_locked(
                    tx=tx,
                    evidence_space_id=evidence_space_id,
                    character_authority=character_authority,
                    predecessor=predecessor,
                    expectation=SubjectiveMemPredecessorExpectation(
                        receipt_id=proposal.expected_current_receipt_id,
                        receipt_digest=proposal.expected_current_receipt_digest,
                        current_state_digest=proposal.expected_current_selector_digest,
                        page_id=proposal.expected_page_id,
                        block_id=proposal.expected_block_id,
                        page_digest=proposal.expected_page_digest,
                        revision_schema=proposal.expected_revision_schema,
                        page_schema=proposal.expected_page_schema,
                        block_schema=proposal.expected_block_schema,
                        renderer_revision=proposal.expected_renderer_revision,
                        partition_revision=proposal.expected_partition_revision,
                        platform_revision=proposal.expected_platform_revision,
                    ),
                )
            )
            if predecessor_authority is None:
                return None, authority_reasons
            reformation = inspect_subjective_mem_reformation_digest_locked(
                tx=tx,
                evidence_space_id=evidence_space_id,
                character_id=character_authority.character_id,
                semantic_identity_digest=semantic_identity,
            )
            if reformation.status == "fail_closed":
                return None, reformation.blocked_reasons
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, ("subjective_mem_forget_store_unavailable",)

    successor = SubjectiveMemRevision(
        memory_id=predecessor.memory_id,
        character_id=predecessor.character_id,
        assessment_id=predecessor.assessment_id,
        assessment_revision=predecessor.assessment_revision,
        grounded_content=predecessor.grounded_content,
        grounded_content_digest=predecessor.grounded_content_digest,
        subjective_meaning=predecessor.subjective_meaning,
        memory_kind=predecessor.memory_kind,
        scope_binding=predecessor.scope_binding,
        formation_snapshot=predecessor.formation_snapshot,
        strength=predecessor.strength,
        decision_id=identity.transition_id,
        created_at=committed_at,
        memory_revision=predecessor.memory_revision + 1,
        formation_stage=predecessor.formation_stage,
        lifecycle_state="hidden",
        retrieval_visible=False,
        predecessor_revision_or_null=predecessor.memory_revision,
        authorization_kind="lifecycle_transition",
    )
    transition = SubjectiveMemLifecycleTransition(
        transition_id=identity.transition_id,
        character_id=predecessor.character_id,
        memory_id=predecessor.memory_id,
        from_revision=predecessor.memory_revision,
        to_revision=successor.memory_revision,
        operation="forget",
        from_lifecycle_state="active",
        to_lifecycle_state="hidden",
        from_formation_stage=predecessor.formation_stage,
        to_formation_stage=predecessor.formation_stage,
        authorized_by=proposal.authorization_class,
        committed_at=committed_at,
    )
    plan_result = plan_subjective_mem_revision_successor(
        predecessor=predecessor,
        successor=successor,
        existing_bytes=snapshot.data,
    )
    if plan_result.plan is None:
        return None, plan_result.reasons
    plan = plan_result.plan
    current_state = _current_state_from_dict(selector_raw)
    if current_state is None:
        return None, ("subjective_mem_forget_current_selector_not_exact",)
    prepared_state = SubjectiveMemCurrentState(
        memory_state_id=current_state.memory_state_id,
        memory_id=current_state.memory_id,
        character_id=current_state.character_id,
        current_revision=current_state.current_revision,
        lifecycle_state=current_state.lifecycle_state,
        mutation_state="prepared",
        retrieval_eligible=False,
        updated_at=committed_at,
        workspace_authority_digest=_workspace_authority_digest(
            workspace_root, character_authority
        ),
        scope_binding_digest=canonical_digest(predecessor.scope_binding.to_dict()),
        page_id=proposal.expected_page_id,
        block_id=proposal.expected_block_id,
        canonical_page_digest=proposal.expected_page_digest,
        authorization_kind=predecessor.authorization_kind,
        authorization_id=predecessor.authorization_id,
        current_receipt_id=proposal.expected_current_receipt_id,
    )
    intent = _build_intent(
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        workspace_root=workspace_root,
        proposal=proposal,
        identity=identity,
        predecessor=predecessor,
        successor=successor,
        prepared_state=prepared_state,
        transition=transition,
        semantic_identity_digest=semantic_identity,
        plan=plan,
        prepared_at=committed_at,
    )
    return (
        _Prepared(
            identity=identity,
            predecessor=predecessor,
            successor=successor,
            current_state_key=current_state.memory_state_id,
            current_state=current_state,
            prepared_state=prepared_state,
            transition=transition,
            semantic_identity_digest=semantic_identity,
            plan=plan,
            intent=intent,
        ),
        (),
    )


def _persist_prepared(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    prepared: _Prepared,
) -> tuple[bool, tuple[str, ...]]:
    claim = _claim_from_intent(identity=prepared.identity, intent=prepared.intent)
    try:
        with store.transaction(evidence_space_id) as tx:
            reformation = inspect_subjective_mem_reformation_digest_locked(
                tx=tx,
                evidence_space_id=evidence_space_id,
                character_id=prepared.current_state.character_id,
                semantic_identity_digest=prepared.semantic_identity_digest,
            )
            if reformation.status == "fail_closed":
                return False, reformation.blocked_reasons
            existing_result = tx.read_record(
                record_kind="subjective_mem_lifecycle_idempotency_result",
                record_id=prepared.identity.result_id,
            )
            if existing_result is not None:
                return False, ("subjective_mem_forget_result_already_exists",)
            existing_claim = tx.read_record(
                record_kind="subjective_mem_lifecycle_claim",
                record_id=prepared.identity.operation_slot_id,
            )
            if existing_claim is not None:
                if existing_claim == claim:
                    return True, ()
                if existing_claim.get("input_digest") != prepared.identity.input_digest:
                    return False, ("subjective_mem_forget_idempotency_conflict",)
                return False, ("subjective_mem_forget_claim_conflict",)
            selector_raw, reasons = _load_exact_selector_locked_raw(
                tx=tx,
                selector_id=prepared.current_state_key,
                expected=prepared.current_state.to_dict(),
            )
            if selector_raw is None:
                return False, reasons
            uniqueness = _validate_selector_uniqueness_locked(
                tx=tx,
                selector_id=prepared.current_state_key,
                character_id=prepared.current_state.character_id,
                memory_id=prepared.current_state.memory_id,
                expected=prepared.current_state.to_dict(),
            )
            if uniqueness:
                return False, uniqueness
            commit = tx.commit(
                transaction_id=_opaque("smfpreparetx", prepared.identity.operation_id),
                records=(
                    (
                        "subjective_mem_lifecycle_claim",
                        prepared.identity.operation_slot_id,
                        claim,
                    ),
                    (
                        "subjective_mem_lifecycle_intent",
                        prepared.identity.intent_id,
                        prepared.intent,
                    ),
                ),
                logs=(
                    (
                        "subjective_mem_current_state",
                        prepared.current_state_key,
                        (prepared.prepared_state.to_dict(),),
                    ),
                ),
            )
            if commit.status == "collision":
                return False, ("subjective_mem_forget_prepare_collision",)
            if commit.status not in {"created", "duplicate_existing"}:
                return False, commit.reasons or ("subjective_mem_forget_prepare_failed",)
            return True, ()
    except (OSError, RuntimeError, TypeError, ValueError):
        return False, ("subjective_mem_forget_store_unavailable",)


def _recover_prepared(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    proposal: SubjectiveMemForgetProposal,
    identity: _Identity,
    intent: dict[str, object],
    fault_injector: FaultInjector | None,
) -> SubjectiveMemForgetResult:
    if not _intent_exact(
        intent,
        identity=identity,
        proposal=proposal,
        character_authority=character_authority,
        evidence_space_id=evidence_space_id,
        workspace_root=workspace_root,
    ):
        return _result(
            "fail_closed",
            identity=identity,
            proposal=proposal,
            reasons=("subjective_mem_forget_intent_corrupt",),
        )
    try:
        with store.transaction(evidence_space_id) as tx:
            expected_prepared = _state_from_intent(intent, prepared=True)
            if expected_prepared is None:
                return _result(
                    "fail_closed",
                    identity=identity,
                    proposal=proposal,
                    reasons=("subjective_mem_forget_intent_corrupt",),
                )
            raw, reasons = _load_exact_selector_locked_raw(
                tx=tx,
                selector_id=str(intent["current_selector_id"]),
                expected=expected_prepared.to_dict(),
            )
            if raw is None:
                return _result(
                    _status_for_reasons(reasons),
                    identity=identity,
                    proposal=proposal,
                    reasons=reasons,
                )
    except (OSError, RuntimeError, TypeError, ValueError):
        return _result(
            "fail_closed",
            identity=identity,
            proposal=proposal,
            reasons=("subjective_mem_forget_store_unavailable",),
        )
    artifact, artifact_reasons = read_immutable_rendered_artifact(
        workspace_root=workspace_root,
        character_id=character_authority.character_id,
        artifact_id=str(intent["artifact_id"]),
    )
    if (
        artifact is None
        or canonical_page_digest(artifact) != intent.get("post_image_digest")
        or not _artifact_exact_for_intent(
            artifact,
            intent=intent,
            proposal=proposal,
            character_authority=character_authority,
            evidence_space_id=evidence_space_id,
        )
    ):
        return _result(
            "recovery_required",
            identity=identity,
            proposal=proposal,
            current_state=expected_prepared,
            reasons=artifact_reasons or ("subjective_mem_forget_artifact_invalid",),
            recovery_outcome="artifact_unavailable",
            persisted=True,
        )
    return _publish_and_finalize(
        store=store,
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        workspace_root=workspace_root,
        proposal=proposal,
        identity=identity,
        intent=intent,
        artifact_bytes=artifact,
        fault_injector=fault_injector,
    )


def _publish_and_finalize(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    proposal: SubjectiveMemForgetProposal,
    identity: _Identity,
    intent: dict[str, object],
    artifact_bytes: bytes,
    fault_injector: FaultInjector | None,
) -> SubjectiveMemForgetResult:
    partition = str(intent["partition"])
    _page_id, relative_path, _partition = subjective_mem_page_identity(
        character_id=character_authority.character_id,
        memory_kind=str(intent["memory_kind"]),
    )
    finalization: dict[str, object] = {}

    def verify(data: bytes) -> bool:
        page, reasons = parse_subjective_mem_page_bytes(
            data,
            expected_page_id=str(intent["page_id"]),
            expected_character_id=character_authority.character_id,
            expected_partition=partition,  # type: ignore[arg-type]
        )
        if page is None or reasons:
            return False
        successors = [
            item
            for item in page.blocks
            if item.revision.memory_id == intent["memory_id"]
            and item.revision.memory_revision == intent["to_revision"]
            and canonical_digest(item.revision.to_dict())
            == intent["successor_revision_digest"]
            and item.block_id == intent["successor_block_id"]
            and item.revision.lifecycle_state == "hidden"
            and item.revision.retrieval_visible is False
        ]
        predecessors = [
            item
            for item in page.blocks
            if item.revision.memory_id == intent["memory_id"]
            and item.revision.memory_revision == intent["from_revision"]
            and canonical_digest(item.revision.to_dict())
            == intent["predecessor_revision_digest"]
        ]
        return len(successors) == 1 and len(predecessors) == 1

    def finalize() -> bool:
        try:
            _fault(fault_injector, "after_page_before_receipt")
        except Exception:
            finalization["reasons"] = ("subjective_mem_forget_fault_before_receipt",)
            return False
        ok, duplicate, records, reasons = _finalize_operations(
            store=store,
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            identity=identity,
            intent=intent,
        )
        finalization.update(
            {"ok": ok, "duplicate": duplicate, "records": records, "reasons": reasons}
        )
        return ok

    def validate_pre_image() -> bool:
        return _validate_pre_image_authority_current(
            store=store,
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            proposal=proposal,
            identity=identity,
            intent=intent,
            artifact_bytes=artifact_bytes,
        )

    publish = publish_canonical_page(
        workspace_root=workspace_root,
        character_id=character_authority.character_id,
        relative_path=relative_path,
        expected_pre_state="present",
        expected_pre_digest=str(intent["pre_image_digest"]),
        post_image=artifact_bytes,
        expected_post_digest=str(intent["post_image_digest"]),
        verify_installed=verify,
        finalize_installed=finalize,
        validate_pre_image=validate_pre_image,
        fault_injector=fault_injector,
    )
    if publish.status == "lock_busy":
        return _result(
            "lock_busy",
            identity=identity,
            proposal=proposal,
            reasons=publish.reasons,
            persisted=True,
        )
    if publish.status == "pre_image_conflict":
        _mark_recovery_required(
            store=store,
            evidence_space_id=evidence_space_id,
            identity=identity,
            intent=intent,
        )
        return _result(
            "recovery_required",
            identity=identity,
            proposal=proposal,
            current_state=_state_from_intent(intent, prepared=False, recovery=True),
            reasons=publish.reasons,
            recovery_outcome="foreign_image",
            persisted=True,
            post_digest=str(intent["post_image_digest"]),
        )
    if publish.status == "failed":
        page_present = publish.installed_digest == intent.get("post_image_digest")
        return _result(
            "recovery_pending",
            identity=identity,
            proposal=proposal,
            current_state=_state_from_intent(intent, prepared=True),
            reasons=tuple(finalization.get("reasons", publish.reasons)),
            recovery_outcome=(
                "post_image_pending_receipt"
                if page_present
                else "pre_image_pending_publication"
            ),
            canonical_published=page_present,
            persisted=True,
            post_digest=str(intent["post_image_digest"]),
        )
    records = finalization.get("records")
    if not finalization.get("ok") or not isinstance(records, dict):
        replay = _resolve_final_replay(
            store=store,
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            workspace_root=workspace_root,
            proposal=proposal,
            identity=identity,
        )
        if replay is not None:
            return replay
        return _result(
            "recovery_pending",
            identity=identity,
            proposal=proposal,
            current_state=_state_from_intent(intent, prepared=True),
            reasons=tuple(
                finalization.get(
                    "reasons", ("subjective_mem_forget_receipt_finalization_failed",)
                )
            ),
            recovery_outcome="post_image_pending_receipt",
            canonical_published=True,
            persisted=True,
            post_digest=str(intent["post_image_digest"]),
        )
    state = _current_state_from_dict(records["current_state"])
    return _result(
        "duplicate_finalized" if finalization.get("duplicate") else "committed",
        identity=identity,
        proposal=proposal,
        current_state=state,
        recovery_outcome=(
            "post_image_rolled_forward"
            if publish.status == "already_post_image"
            else "published_and_finalized"
        ),
        canonical_published=True,
        receipt_present=True,
        tombstone_present=True,
        persisted=True,
        post_digest=str(intent["post_image_digest"]),
    )


def _build_intent(
    *,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    proposal: SubjectiveMemForgetProposal,
    identity: _Identity,
    predecessor: SubjectiveMemRevision,
    successor: SubjectiveMemRevision,
    prepared_state: SubjectiveMemCurrentState,
    transition: SubjectiveMemLifecycleTransition,
    semantic_identity_digest: str,
    plan: SubjectiveMemPagePlan,
    prepared_at: str,
) -> dict[str, object]:
    return {
        "schema": LIFECYCLE_INTENT_SCHEMA,
        "intent_id": identity.intent_id,
        "operation_slot_id": identity.operation_slot_id,
        "operation_id": identity.operation_id,
        "operation_kind": "forget",
        "operation_key_digest": identity.operation_key_digest,
        "input_digest": identity.input_digest,
        "evidence_space_id": evidence_space_id,
        "character_id": character_authority.character_id,
        "character_authority_digest": canonical_digest(character_authority.to_dict()),
        "workspace_authority_digest": _workspace_authority_digest(
            workspace_root, character_authority
        ),
        "memory_id": predecessor.memory_id,
        "memory_kind": predecessor.memory_kind,
        "formation_stage": predecessor.formation_stage,
        "scope_binding_digest": canonical_digest(predecessor.scope_binding.to_dict()),
        "formation_snapshot_digest": canonical_digest(
            predecessor.formation_snapshot.to_dict()
        ),
        "semantic_identity_digest": semantic_identity_digest,
        "from_revision": predecessor.memory_revision,
        "to_revision": successor.memory_revision,
        "from_lifecycle_state": predecessor.lifecycle_state,
        "to_lifecycle_state": successor.lifecycle_state,
        "predecessor_revision_digest": canonical_digest(predecessor.to_dict()),
        "predecessor_block_id": proposal.expected_block_id,
        "predecessor_authorization_kind": predecessor.authorization_kind,
        "predecessor_authorization_id": predecessor.authorization_id,
        "successor_revision_digest": canonical_digest(successor.to_dict()),
        "transition_id": transition.transition_id,
        "receipt_id": identity.receipt_id,
        "tombstone_id": identity.tombstone_id,
        "authorization_class": proposal.authorization_class,
        "authorization_id": proposal.authorization_id,
        "reason_category": proposal.reason_category,
        "policy_revision": proposal.policy_revision,
        "current_receipt_id": proposal.expected_current_receipt_id,
        "current_receipt_digest": proposal.expected_current_receipt_digest,
        "current_selector_id": proposal.expected_current_selector_id,
        "current_selector_digest": proposal.expected_current_selector_digest,
        "prepared_current_state_digest": canonical_digest(prepared_state.to_dict()),
        "page_id": plan.page_id,
        "partition": plan.partition,
        "successor_block_id": plan.block_id,
        "pre_image_state": plan.pre_image_state,
        "pre_image_digest": plan.pre_image_digest,
        "post_image_digest": plan.post_image_digest,
        "successor_block_digest": plan.block_digest,
        "artifact_id": plan.artifact_id,
        "artifact_digest": plan.post_image_digest,
        "revision_schema": SUBJECTIVE_MEM_REVISION_SCHEMA,
        "page_schema": PAGE_SCHEMA,
        "block_schema": LIFECYCLE_BLOCK_SCHEMA,
        "renderer_revision": RENDERER_REVISION,
        "partition_revision": PAGE_PARTITION_REVISION,
        "platform_revision": PLATFORM_REVISION,
        "prepared_at": prepared_at,
        "recovery_state": "prepared",
    }


def _claim_from_intent(
    *, identity: _Identity, intent: dict[str, object]
) -> dict[str, object]:
    return {
        "schema": LIFECYCLE_CLAIM_SCHEMA,
        "operation_slot_id": identity.operation_slot_id,
        "operation_id": identity.operation_id,
        "operation_kind": "forget",
        "operation_key_digest": identity.operation_key_digest,
        "input_digest": identity.input_digest,
        "intent_digest": canonical_digest(intent),
        "evidence_space_id": intent["evidence_space_id"],
        "character_id": intent["character_id"],
        "memory_id": intent["memory_id"],
        "from_revision": intent["from_revision"],
        "to_revision": intent["to_revision"],
        "intent_id": identity.intent_id,
        "claimed_at": intent["prepared_at"],
    }


def _build_final_records(
    *,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    identity: _Identity,
    intent: dict[str, object],
) -> dict[str, dict[str, object]] | None:
    final_state = _state_from_intent(intent, prepared=False)
    if final_state is None:
        return None
    transition = {
        "schema": LIFECYCLE_TRANSITION_SCHEMA,
        "transition_id": identity.transition_id,
        "character_id": character_authority.character_id,
        "memory_id": intent["memory_id"],
        "from_revision": intent["from_revision"],
        "to_revision": intent["to_revision"],
        "operation": "forget",
        "from_lifecycle_state": "active",
        "to_lifecycle_state": "hidden",
        "from_formation_stage": intent["formation_stage"],
        "to_formation_stage": intent["formation_stage"],
        "authorized_by": intent["authorization_class"],
        "committed_at": intent["prepared_at"],
    }
    transition_digest = canonical_digest(transition)
    tombstone = SubjectiveMemForgetTombstone(
        tombstone_id=identity.tombstone_id,
        evidence_space_id=evidence_space_id,
        character_id=character_authority.character_id,
        memory_id=str(intent["memory_id"]),
        source_revision=int(intent["from_revision"]),
        hidden_revision=int(intent["to_revision"]),
        formation_stage=str(intent["formation_stage"]),
        transition_id=identity.transition_id,
        transition_digest=transition_digest,
        receipt_id=identity.receipt_id,
        semantic_identity_digest=str(intent["semantic_identity_digest"]),
        scope_binding_digest=str(intent["scope_binding_digest"]),
        authorization_class=str(intent["authorization_class"]),
        authorization_id=str(intent["authorization_id"]),
        reason_category=str(intent["reason_category"]),
        policy_revision=str(intent["policy_revision"]),
        effective_at=str(intent["prepared_at"]),
    ).to_dict()
    tombstone_state = {
        "schema": FORGET_TOMBSTONE_STATE_SCHEMA,
        "tombstone_id": identity.tombstone_id,
        "tombstone_digest": tombstone["tombstone_digest"],
        "evidence_space_id": evidence_space_id,
        "character_id": character_authority.character_id,
        "semantic_identity_digest": intent["semantic_identity_digest"],
        "memory_id": intent["memory_id"],
        "hidden_revision": intent["to_revision"],
        "formation_stage": intent["formation_stage"],
        "transition_id": identity.transition_id,
        "transition_digest": transition_digest,
        "receipt_id": identity.receipt_id,
        "effective": True,
        "superseded_by_tombstone_id_or_null": None,
        "updated_at": intent["prepared_at"],
        "content_free": True,
    }
    receipt_body: dict[str, object] = {
        "schema": LIFECYCLE_RECEIPT_SCHEMA,
        "receipt_id": identity.receipt_id,
        "intent_id": identity.intent_id,
        "intent_digest": canonical_digest(intent),
        "operation_id": identity.operation_id,
        "operation_kind": "forget",
        "operation_outcome": "committed",
        "input_digest": identity.input_digest,
        "evidence_space_id": evidence_space_id,
        "character_id": character_authority.character_id,
        "memory_ref": {
            "memory_id": intent["memory_id"],
            "memory_revision": intent["to_revision"],
        },
        "predecessor_revision": intent["from_revision"],
        "formation_stage": intent["formation_stage"],
        "transition_id": identity.transition_id,
        "transition_digest": transition_digest,
        "tombstone_id": identity.tombstone_id,
        "tombstone_digest": tombstone["tombstone_digest"],
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
        "page_id": intent["page_id"],
        "successor_block_id": intent["successor_block_id"],
        "pre_image_digest": intent["pre_image_digest"],
        "post_image_digest": intent["post_image_digest"],
        "successor_revision_digest": intent["successor_revision_digest"],
        "current_state_digest": canonical_digest(final_state.to_dict()),
        "projection_state": "rebuild_required",
        "ordinary_retrieval_wired": False,
        "finalized_at": intent["prepared_at"],
    }
    receipt = {**receipt_body, "receipt_digest": canonical_digest(receipt_body)}
    finalization = {
        "schema": LIFECYCLE_INTENT_FINALIZATION_SCHEMA,
        "finalization_id": _opaque("smfintentfin", identity.intent_id),
        "intent_id": identity.intent_id,
        "intent_digest": canonical_digest(intent),
        "receipt_id": identity.receipt_id,
        "receipt_digest": receipt["receipt_digest"],
        "status": "finalized",
        "finalized_at": intent["prepared_at"],
    }
    result_body: dict[str, object] = {
        "schema": LIFECYCLE_RESULT_SCHEMA,
        "result_id": identity.result_id,
        "operation_slot_id": identity.operation_slot_id,
        "operation_id": identity.operation_id,
        "operation_kind": "forget",
        "input_digest": identity.input_digest,
        "receipt_id": identity.receipt_id,
        "receipt_digest": receipt["receipt_digest"],
        "transition_id": identity.transition_id,
        "tombstone_id": identity.tombstone_id,
        "tombstone_digest": tombstone["tombstone_digest"],
        "semantic_identity_digest": intent["semantic_identity_digest"],
        "memory_id": intent["memory_id"],
        "from_revision": intent["from_revision"],
        "to_revision": intent["to_revision"],
        "page_id": intent["page_id"],
        "post_image_digest": intent["post_image_digest"],
        "current_selector_id": intent["current_selector_id"],
        "current_state_digest": canonical_digest(final_state.to_dict()),
        "status": "committed",
        "finalized_at": intent["prepared_at"],
    }
    result = {**result_body, "result_digest": canonical_digest(result_body)}
    projection = {
        "schema": "relaylm.subjective_mem_projection_state.v1",
        "memory_id": intent["memory_id"],
        "memory_revision": intent["to_revision"],
        "lifecycle_state": "hidden",
        "retrieval_eligible": False,
        "projection_state": "rebuild_required",
        "ordinary_retrieval_wired": False,
        "updated_at": intent["prepared_at"],
    }
    return {
        "transition": transition,
        "tombstone": tombstone,
        "tombstone_state": tombstone_state,
        "receipt": receipt,
        "finalization": finalization,
        "result": result,
        "current_state": final_state.to_dict(),
        "projection": projection,
    }


def _finalize_operations(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    identity: _Identity,
    intent: dict[str, object],
) -> tuple[bool, bool, dict[str, dict[str, object]] | None, tuple[str, ...]]:
    records = _build_final_records(
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        identity=identity,
        intent=intent,
    )
    if records is None:
        return False, False, None, ("subjective_mem_forget_intent_corrupt",)
    final_state = _current_state_from_dict(records["current_state"])
    if final_state is None:
        return False, False, None, ("subjective_mem_forget_intent_corrupt",)
    try:
        with store.transaction(evidence_space_id) as tx:
            if _final_records_exact_locked(tx=tx, identity=identity, records=records):
                return True, True, records, ()
            if _any_final_record_present_locked(tx=tx, identity=identity):
                return False, False, None, (
                    "subjective_mem_forget_partial_finalization_conflict",
                )
            claim = tx.read_record(
                record_kind="subjective_mem_lifecycle_claim",
                record_id=identity.operation_slot_id,
            )
            stored_intent = tx.read_record(
                record_kind="subjective_mem_lifecycle_intent",
                record_id=identity.intent_id,
            )
            if (
                not isinstance(claim, dict)
                or claim.get("input_digest") != identity.input_digest
                or stored_intent != intent
            ):
                return False, False, None, (
                    "subjective_mem_forget_claim_or_intent_changed",
                )
            prepared_state = _state_from_intent(intent, prepared=True)
            if prepared_state is None:
                return False, False, None, ("subjective_mem_forget_intent_corrupt",)
            selector, reasons = _load_exact_selector_locked_raw(
                tx=tx,
                selector_id=str(intent["current_selector_id"]),
                expected=prepared_state.to_dict(),
            )
            if selector is None:
                return False, False, None, reasons
            reformation = inspect_subjective_mem_reformation_digest_locked(
                tx=tx,
                evidence_space_id=evidence_space_id,
                character_id=character_authority.character_id,
                semantic_identity_digest=str(intent["semantic_identity_digest"]),
            )
            if reformation.status == "fail_closed":
                return False, False, None, reformation.blocked_reasons
            current_tombstones = tx.read_log(
                log_kind=_TOMBSTONE_LOG_KIND,
                key=str(intent["semantic_identity_digest"]),
            )
            if current_tombstones is None:
                current_tombstones = []
            state_item = records["tombstone_state"]
            same_id = [
                item
                for item in current_tombstones
                if item.get("tombstone_id") == identity.tombstone_id
            ]
            if same_id and same_id != [state_item]:
                return False, False, None, (
                    "subjective_mem_forget_tombstone_state_conflict",
                )
            tombstone_log = list(current_tombstones)
            if not same_id:
                tombstone_log.append(state_item)
            tombstone_log.sort(key=lambda item: str(item.get("tombstone_id", "")))
            commit = tx.commit(
                transaction_id=_opaque("smffinaltx", identity.operation_id),
                records=(
                    (
                        "subjective_mem_lifecycle_transition",
                        identity.transition_id,
                        records["transition"],
                    ),
                    (
                        "subjective_mem_forget_tombstone",
                        identity.tombstone_id,
                        records["tombstone"],
                    ),
                    (
                        "subjective_mem_lifecycle_receipt",
                        identity.receipt_id,
                        records["receipt"],
                    ),
                    (
                        "subjective_mem_lifecycle_intent_finalization",
                        str(records["finalization"]["finalization_id"]),
                        records["finalization"],
                    ),
                    (
                        "subjective_mem_lifecycle_idempotency_result",
                        identity.result_id,
                        records["result"],
                    ),
                ),
                logs=(
                    (
                        "subjective_mem_current_state",
                        str(intent["current_selector_id"]),
                        (final_state.to_dict(),),
                    ),
                    (
                        "subjective_mem_projection_state",
                        str(intent["current_selector_id"]),
                        (records["projection"],),
                    ),
                    (
                        _TOMBSTONE_LOG_KIND,
                        str(intent["semantic_identity_digest"]),
                        tuple(tombstone_log),
                    ),
                ),
            )
            if commit.status == "collision":
                return False, False, None, (
                    "subjective_mem_forget_finalization_collision",
                )
            if commit.status not in {"created", "duplicate_existing"}:
                return False, False, None, commit.reasons or (
                    "subjective_mem_forget_finalization_failed",
                )
            return True, commit.status == "duplicate_existing", records, ()
    except (OSError, RuntimeError, TypeError, ValueError):
        return False, False, None, ("subjective_mem_forget_store_unavailable",)


def _resolve_final_replay(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    proposal: SubjectiveMemForgetProposal,
    identity: _Identity,
) -> SubjectiveMemForgetResult | None:
    try:
        with store.transaction(evidence_space_id) as tx:
            result = tx.read_record(
                record_kind="subjective_mem_lifecycle_idempotency_result",
                record_id=identity.result_id,
            )
            if result is None:
                claim = tx.read_record(
                    record_kind="subjective_mem_lifecycle_claim",
                    record_id=identity.operation_slot_id,
                )
                if claim is not None and claim.get("input_digest") != identity.input_digest:
                    return _result(
                        "integrity_conflict",
                        identity=identity,
                        proposal=proposal,
                        reasons=("subjective_mem_forget_idempotency_conflict",),
                    )
                return None
            if result.get("input_digest") != identity.input_digest:
                return _result(
                    "integrity_conflict",
                    identity=identity,
                    proposal=proposal,
                    reasons=("subjective_mem_forget_idempotency_conflict",),
                )
            intent = tx.read_record(
                record_kind="subjective_mem_lifecycle_intent",
                record_id=identity.intent_id,
            )
            claim = tx.read_record(
                record_kind="subjective_mem_lifecycle_claim",
                record_id=identity.operation_slot_id,
            )
            if (
                not isinstance(intent, dict)
                or not _intent_exact(
                    intent,
                    identity=identity,
                    proposal=proposal,
                    character_authority=character_authority,
                    evidence_space_id=evidence_space_id,
                    workspace_root=workspace_root,
                )
                or claim != _claim_from_intent(identity=identity, intent=intent)
            ):
                return _result(
                    "fail_closed",
                    identity=identity,
                    proposal=proposal,
                    reasons=("subjective_mem_forget_final_result_incomplete",),
                )
            records = _build_final_records(
                evidence_space_id=evidence_space_id,
                character_authority=character_authority,
                identity=identity,
                intent=intent,
            )
            if (
                records is None
                or result != records["result"]
                or not _final_records_exact_locked(
                    tx=tx, identity=identity, records=records
                )
            ):
                return _result(
                    "fail_closed",
                    identity=identity,
                    proposal=proposal,
                    reasons=("subjective_mem_forget_final_result_incomplete",),
                )
            state = _current_state_from_dict(records["current_state"])
            if state is None:
                return _result(
                    "fail_closed",
                    identity=identity,
                    proposal=proposal,
                    reasons=("subjective_mem_forget_final_selector_invalid",),
                )
            uniqueness = _validate_selector_uniqueness_locked(
                tx=tx,
                selector_id=state.memory_state_id,
                character_id=state.character_id,
                memory_id=state.memory_id,
                expected=state.to_dict(),
            )
            if uniqueness:
                return _result(
                    "fail_closed",
                    identity=identity,
                    proposal=proposal,
                    current_state=state,
                    reasons=uniqueness,
                    receipt_present=True,
                    tombstone_present=True,
                    persisted=True,
                )
    except (OSError, RuntimeError, TypeError, ValueError):
        return _result(
            "fail_closed",
            identity=identity,
            proposal=proposal,
            reasons=("subjective_mem_forget_store_unavailable",),
        )

    _page_id, relative_path, partition = subjective_mem_page_identity(
        character_id=character_authority.character_id,
        memory_kind=str(intent["memory_kind"]),
    )
    inspected = inspect_canonical_page(
        workspace_root=workspace_root,
        character_id=character_authority.character_id,
        relative_path=relative_path,
    )
    if (
        inspected.snapshot is None
        or inspected.snapshot.data is None
        or inspected.snapshot.digest != result.get("post_image_digest")
    ):
        return _result(
            "fail_closed",
            identity=identity,
            proposal=proposal,
            current_state=state,
            reasons=("subjective_mem_forget_receipt_without_exact_page",),
            receipt_present=True,
            tombstone_present=True,
            persisted=True,
        )
    page, reasons = parse_subjective_mem_page_bytes(
        inspected.snapshot.data,
        expected_page_id=str(result.get("page_id")),
        expected_character_id=character_authority.character_id,
        expected_partition=partition,
    )
    current = (
        [
            item
            for item in page.blocks
            if item.revision.memory_id == result.get("memory_id")
            and item.revision.memory_revision == result.get("to_revision")
            and item.block_id == intent.get("successor_block_id")
            and canonical_digest(item.revision.to_dict())
            == intent.get("successor_revision_digest")
            and item.revision.lifecycle_state == "hidden"
            and item.revision.retrieval_visible is False
        ]
        if page is not None
        else []
    )
    predecessors = (
        [
            item
            for item in page.blocks
            if item.revision.memory_id == result.get("memory_id")
            and item.revision.memory_revision == result.get("from_revision")
            and canonical_digest(item.revision.to_dict())
            == intent.get("predecessor_revision_digest")
        ]
        if page is not None
        else []
    )
    if page is None or reasons or len(current) != 1 or len(predecessors) != 1:
        return _result(
            "fail_closed",
            identity=identity,
            proposal=proposal,
            current_state=state,
            reasons=("subjective_mem_forget_final_page_invalid",),
            receipt_present=True,
            tombstone_present=True,
            persisted=True,
        )
    return _result(
        "duplicate_finalized",
        identity=identity,
        proposal=proposal,
        current_state=state,
        recovery_outcome="exact_replay",
        canonical_published=True,
        receipt_present=True,
        tombstone_present=True,
        persisted=True,
        post_digest=str(result.get("post_image_digest")),
    )


def _validate_pre_image_authority_current(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    proposal: SubjectiveMemForgetProposal,
    identity: _Identity,
    intent: dict[str, object],
    artifact_bytes: bytes,
) -> bool:
    try:
        with store.transaction(evidence_space_id) as tx:
            expected_prepared = _state_from_intent(intent, prepared=True)
            if expected_prepared is None:
                return False
            selector, _ = _load_exact_selector_locked_raw(
                tx=tx,
                selector_id=expected_prepared.memory_state_id,
                expected=expected_prepared.to_dict(),
            )
            if selector is None:
                return False
            claim = tx.read_record(
                record_kind="subjective_mem_lifecycle_claim",
                record_id=identity.operation_slot_id,
            )
            stored_intent = tx.read_record(
                record_kind="subjective_mem_lifecycle_intent",
                record_id=identity.intent_id,
            )
            if (
                claim != _claim_from_intent(identity=identity, intent=intent)
                or stored_intent != intent
            ):
                return False
            reformation = inspect_subjective_mem_reformation_digest_locked(
                tx=tx,
                evidence_space_id=evidence_space_id,
                character_id=character_authority.character_id,
                semantic_identity_digest=str(intent["semantic_identity_digest"]),
            )
            if reformation.status == "fail_closed":
                return False
            predecessor = _predecessor_from_artifact(
                artifact_bytes,
                intent=intent,
                proposal=proposal,
                character_authority=character_authority,
            )
            if predecessor is None:
                return False
            predecessor_authority, _authority_reasons = (
                load_subjective_mem_predecessor_authority_locked(
                    tx=tx,
                    evidence_space_id=evidence_space_id,
                    character_authority=character_authority,
                    predecessor=predecessor,
                    expectation=SubjectiveMemPredecessorExpectation(
                        receipt_id=proposal.expected_current_receipt_id,
                        receipt_digest=proposal.expected_current_receipt_digest,
                        current_state_digest=proposal.expected_current_selector_digest,
                        page_id=proposal.expected_page_id,
                        block_id=proposal.expected_block_id,
                        page_digest=proposal.expected_page_digest,
                        revision_schema=proposal.expected_revision_schema,
                        page_schema=proposal.expected_page_schema,
                        block_schema=proposal.expected_block_schema,
                        renderer_revision=proposal.expected_renderer_revision,
                        partition_revision=proposal.expected_partition_revision,
                        platform_revision=proposal.expected_platform_revision,
                    ),
                )
            )
            return predecessor_authority is not None
    except (OSError, RuntimeError, TypeError, ValueError):
        return False


def _predecessor_from_artifact(
    artifact: bytes,
    *,
    intent: dict[str, object],
    proposal: SubjectiveMemForgetProposal,
    character_authority: SubjectiveMemCharacterAuthority,
) -> SubjectiveMemRevision | None:
    try:
        _page_id, _relative, partition = subjective_mem_page_identity(
            character_id=character_authority.character_id,
            memory_kind=proposal.expected_memory_kind,
        )
        page, reasons = parse_subjective_mem_page_bytes(
            artifact,
            expected_page_id=proposal.expected_page_id,
            expected_character_id=character_authority.character_id,
            expected_partition=partition,
        )
        if page is None or reasons:
            return None
        matches = [
            item.revision
            for item in page.blocks
            if item.revision.memory_id == proposal.expected_memory_id
            and item.revision.memory_revision == proposal.expected_current_revision
            and canonical_digest(item.revision.to_dict())
            == intent.get("predecessor_revision_digest")
        ]
        return matches[0] if len(matches) == 1 else None
    except (TypeError, ValueError):
        return None


def _artifact_exact_for_intent(
    artifact: bytes,
    *,
    intent: dict[str, object],
    proposal: SubjectiveMemForgetProposal,
    character_authority: SubjectiveMemCharacterAuthority,
    evidence_space_id: str,
) -> bool:
    try:
        _page_id, _relative, partition = subjective_mem_page_identity(
            character_id=character_authority.character_id,
            memory_kind=proposal.expected_memory_kind,
        )
        page, reasons = parse_subjective_mem_page_bytes(
            artifact,
            expected_page_id=proposal.expected_page_id,
            expected_character_id=character_authority.character_id,
            expected_partition=partition,
        )
        if page is None or reasons:
            return False
        predecessor = next(
            item
            for item in page.blocks
            if item.revision.memory_id == proposal.expected_memory_id
            and item.revision.memory_revision == proposal.expected_current_revision
        )
        successor = next(
            item
            for item in page.blocks
            if item.revision.memory_id == proposal.expected_memory_id
            and item.revision.memory_revision == proposal.expected_current_revision + 1
        )
    except (StopIteration, TypeError, ValueError):
        return False
    predecessor_revision = predecessor.revision
    successor_revision = successor.revision
    try:
        semantic_identity = subjective_mem_semantic_identity_digest(
            evidence_space_id=evidence_space_id,
            character_id=character_authority.character_id,
            grounded_content_digest=predecessor_revision.grounded_content_digest,
            subjective_meaning=predecessor_revision.subjective_meaning,
            memory_kind=predecessor_revision.memory_kind,
            scope_binding=predecessor_revision.scope_binding,
        )
    except ValueError:
        return False
    return (
        predecessor.block_id == proposal.expected_block_id
        and canonical_digest(predecessor_revision.to_dict())
        == intent.get("predecessor_revision_digest")
        and predecessor_revision.authorization_kind
        == intent.get("predecessor_authorization_kind")
        and predecessor_revision.authorization_id
        == intent.get("predecessor_authorization_id")
        and successor.block_id == intent.get("successor_block_id")
        and successor.block_digest == intent.get("successor_block_digest")
        and canonical_digest(successor_revision.to_dict())
        == intent.get("successor_revision_digest")
        and successor_revision.predecessor_revision_or_null
        == proposal.expected_current_revision
        and successor_revision.grounded_content == predecessor_revision.grounded_content
        and successor_revision.grounded_content_digest
        == predecessor_revision.grounded_content_digest
        and successor_revision.subjective_meaning
        == predecessor_revision.subjective_meaning
        and successor_revision.strength.to_dict()
        == predecessor_revision.strength.to_dict()
        and successor_revision.scope_binding.to_dict()
        == predecessor_revision.scope_binding.to_dict()
        and successor_revision.formation_snapshot.to_dict()
        == predecessor_revision.formation_snapshot.to_dict()
        and successor_revision.memory_kind == predecessor_revision.memory_kind
        and successor_revision.formation_stage == predecessor_revision.formation_stage
        and successor_revision.lifecycle_state == "hidden"
        and successor_revision.retrieval_visible is False
        and successor_revision.authorization_kind == "lifecycle_transition"
        and successor_revision.authorization_id == intent.get("transition_id")
        and semantic_identity == intent.get("semantic_identity_digest")
        and canonical_page_digest(artifact) == intent.get("post_image_digest")
    )


def _intent_exact(
    intent: dict[str, object],
    *,
    identity: _Identity,
    proposal: SubjectiveMemForgetProposal,
    character_authority: SubjectiveMemCharacterAuthority,
    evidence_space_id: str,
    workspace_root: str,
) -> bool:
    required = {
        "schema",
        "intent_id",
        "operation_slot_id",
        "operation_id",
        "operation_kind",
        "operation_key_digest",
        "input_digest",
        "evidence_space_id",
        "character_id",
        "character_authority_digest",
        "workspace_authority_digest",
        "memory_id",
        "memory_kind",
        "formation_stage",
        "scope_binding_digest",
        "formation_snapshot_digest",
        "semantic_identity_digest",
        "from_revision",
        "to_revision",
        "from_lifecycle_state",
        "to_lifecycle_state",
        "predecessor_revision_digest",
        "predecessor_block_id",
        "predecessor_authorization_kind",
        "predecessor_authorization_id",
        "successor_revision_digest",
        "transition_id",
        "receipt_id",
        "tombstone_id",
        "authorization_class",
        "authorization_id",
        "reason_category",
        "policy_revision",
        "current_receipt_id",
        "current_receipt_digest",
        "current_selector_id",
        "current_selector_digest",
        "prepared_current_state_digest",
        "page_id",
        "partition",
        "successor_block_id",
        "pre_image_state",
        "pre_image_digest",
        "post_image_digest",
        "successor_block_digest",
        "artifact_id",
        "artifact_digest",
        "revision_schema",
        "page_schema",
        "block_schema",
        "renderer_revision",
        "partition_revision",
        "platform_revision",
        "prepared_at",
        "recovery_state",
    }
    prepared_at = intent.get("prepared_at")
    operation_digest = canonical_digest(
        {
            "proposal_input_digest": proposal.input_digest,
            "operation_time": prepared_at,
        }
    )
    expected_page_id, _relative, partition = subjective_mem_page_identity(
        character_id=character_authority.character_id,
        memory_kind=proposal.expected_memory_kind,
    )
    post_digest = intent.get("post_image_digest")
    return (
        set(intent) == required
        and intent.get("schema") == LIFECYCLE_INTENT_SCHEMA
        and intent.get("intent_id") == identity.intent_id
        and intent.get("operation_slot_id") == identity.operation_slot_id
        and intent.get("operation_id") == identity.operation_id
        and intent.get("operation_kind") == "forget"
        and intent.get("operation_key_digest") == identity.operation_key_digest
        and intent.get("input_digest") == identity.input_digest == operation_digest
        and intent.get("evidence_space_id") == evidence_space_id
        and intent.get("character_id") == character_authority.character_id
        and intent.get("character_authority_digest")
        == canonical_digest(character_authority.to_dict())
        and intent.get("workspace_authority_digest")
        == _workspace_authority_digest(workspace_root, character_authority)
        and intent.get("memory_id") == proposal.expected_memory_id
        and intent.get("memory_kind") == proposal.expected_memory_kind
        and intent.get("formation_stage") == proposal.expected_formation_stage
        and intent.get("scope_binding_digest")
        == proposal.expected_scope_binding_digest
        and intent.get("formation_snapshot_digest")
        == proposal.expected_formation_snapshot_digest
        and _digest(intent.get("semantic_identity_digest"))
        and intent.get("from_revision") == proposal.expected_current_revision
        and intent.get("to_revision") == proposal.expected_current_revision + 1
        and intent.get("from_lifecycle_state") == "active"
        and intent.get("to_lifecycle_state") == "hidden"
        and intent.get("predecessor_block_id") == proposal.expected_block_id
        and intent.get("transition_id") == identity.transition_id
        and intent.get("receipt_id") == identity.receipt_id
        and intent.get("tombstone_id") == identity.tombstone_id
        and intent.get("authorization_class") == proposal.authorization_class
        and intent.get("authorization_id") == proposal.authorization_id
        and intent.get("reason_category") == proposal.reason_category
        and intent.get("policy_revision") == proposal.policy_revision
        and intent.get("current_receipt_id") == proposal.expected_current_receipt_id
        and intent.get("current_receipt_digest")
        == proposal.expected_current_receipt_digest
        and intent.get("current_selector_id")
        == proposal.expected_current_selector_id
        and intent.get("current_selector_digest")
        == proposal.expected_current_selector_digest
        and intent.get("page_id") == proposal.expected_page_id == expected_page_id
        and intent.get("partition") == partition
        and intent.get("pre_image_state") == "present"
        and intent.get("pre_image_digest") == proposal.expected_page_digest
        and isinstance(post_digest, str)
        and intent.get("artifact_digest") == post_digest
        and intent.get("artifact_id")
        == "smartifact_" + post_digest.removeprefix("sha256:")
        and intent.get("revision_schema") == proposal.expected_revision_schema
        and intent.get("page_schema") == proposal.expected_page_schema
        and intent.get("block_schema") == proposal.expected_block_schema
        and intent.get("renderer_revision") == proposal.expected_renderer_revision
        and intent.get("partition_revision")
        == proposal.expected_partition_revision
        and intent.get("platform_revision") == proposal.expected_platform_revision
        and intent.get("recovery_state") == "prepared"
        and isinstance(prepared_at, str)
    )


def _state_from_intent(
    intent: dict[str, object], *, prepared: bool, recovery: bool = False
) -> SubjectiveMemCurrentState | None:
    try:
        mutation = "recovery_required" if recovery else "prepared" if prepared else "none"
        predecessor = prepared or recovery
        state = SubjectiveMemCurrentState(
            memory_state_id=str(intent["current_selector_id"]),
            memory_id=str(intent["memory_id"]),
            character_id=str(intent["character_id"]),
            current_revision=int(
                intent["from_revision"] if predecessor else intent["to_revision"]
            ),
            lifecycle_state="active" if predecessor else "hidden",
            mutation_state=mutation,
            retrieval_eligible=False,
            updated_at=str(intent["prepared_at"]),
            workspace_authority_digest=str(intent["workspace_authority_digest"]),
            scope_binding_digest=str(intent["scope_binding_digest"]),
            page_id=str(intent["page_id"]),
            block_id=str(
                intent["predecessor_block_id"]
                if predecessor
                else intent["successor_block_id"]
            ),
            canonical_page_digest=str(
                intent["pre_image_digest"] if predecessor else intent["post_image_digest"]
            ),
            authorization_kind=str(
                intent["predecessor_authorization_kind"]
                if predecessor
                else "lifecycle_transition"
            ),
            authorization_id=str(
                intent["predecessor_authorization_id"]
                if predecessor
                else intent["transition_id"]
            ),
            current_receipt_id=str(
                intent["current_receipt_id"] if predecessor else intent["receipt_id"]
            ),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if prepared and canonical_digest(state.to_dict()) != intent.get(
        "prepared_current_state_digest"
    ):
        return None
    return state


def _mark_recovery_required(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    identity: _Identity,
    intent: dict[str, object],
) -> None:
    prepared = _state_from_intent(intent, prepared=True)
    recovery = _state_from_intent(intent, prepared=False, recovery=True)
    if prepared is None or recovery is None:
        return
    try:
        with store.transaction(evidence_space_id) as tx:
            if tx.read_log(
                log_kind="subjective_mem_current_state",
                key=prepared.memory_state_id,
            ) != [prepared.to_dict()]:
                return
            recovery_record = {
                "schema": "relaylm.subjective_mem_lifecycle_recovery.v1",
                "recovery_id": _opaque("smfrecovery", identity.operation_id),
                "operation_id": identity.operation_id,
                "intent_id": identity.intent_id,
                "operation_kind": "forget",
                "memory_id": recovery.memory_id,
                "memory_revision": recovery.current_revision,
                "recovery_state": "recovery_required",
                "reason_id": "foreign_or_ambiguous_canonical_image",
                "recorded_at": recovery.updated_at,
                "content_free": True,
            }
            tx.commit(
                transaction_id=_opaque("smfrecoverytx", identity.operation_id),
                records=(
                    (
                        "subjective_mem_lifecycle_recovery",
                        str(recovery_record["recovery_id"]),
                        recovery_record,
                    ),
                ),
                logs=(
                    (
                        "subjective_mem_current_state",
                        prepared.memory_state_id,
                        (recovery.to_dict(),),
                    ),
                ),
            )
    except (OSError, RuntimeError, TypeError, ValueError):
        return


def _final_records_exact_locked(
    *,
    tx: EvidenceStoreTransaction,
    identity: _Identity,
    records: dict[str, dict[str, object]],
) -> bool:
    reformation = inspect_subjective_mem_reformation_digest_locked(
        tx=tx,
        evidence_space_id=str(records["tombstone"]["evidence_space_id"]),
        character_id=str(records["tombstone"]["character_id"]),
        semantic_identity_digest=str(
            records["tombstone_state"]["semantic_identity_digest"]
        ),
    )
    return (
        reformation.status == "blocked"
        and identity.tombstone_id in reformation.tombstone_ids
        and tx.read_record(
            record_kind="subjective_mem_lifecycle_transition",
            record_id=identity.transition_id,
        )
        == records["transition"]
        and tx.read_record(
            record_kind="subjective_mem_forget_tombstone",
            record_id=identity.tombstone_id,
        )
        == records["tombstone"]
        and tx.read_record(
            record_kind="subjective_mem_lifecycle_receipt",
            record_id=identity.receipt_id,
        )
        == records["receipt"]
        and tx.read_record(
            record_kind="subjective_mem_lifecycle_intent_finalization",
            record_id=str(records["finalization"]["finalization_id"]),
        )
        == records["finalization"]
        and tx.read_record(
            record_kind="subjective_mem_lifecycle_idempotency_result",
            record_id=identity.result_id,
        )
        == records["result"]
        and tx.read_log(
            log_kind="subjective_mem_current_state",
            key=str(records["current_state"]["memory_state_id"]),
        )
        == [records["current_state"]]
        and tx.read_log(
            log_kind="subjective_mem_projection_state",
            key=str(records["current_state"]["memory_state_id"]),
        )
        == [records["projection"]]
    )


def _any_final_record_present_locked(
    *, tx: EvidenceStoreTransaction, identity: _Identity
) -> bool:
    return any(
        item is not None
        for item in (
            tx.read_record(
                record_kind="subjective_mem_lifecycle_transition",
                record_id=identity.transition_id,
            ),
            tx.read_record(
                record_kind="subjective_mem_forget_tombstone",
                record_id=identity.tombstone_id,
            ),
            tx.read_record(
                record_kind="subjective_mem_lifecycle_receipt",
                record_id=identity.receipt_id,
            ),
            tx.read_record(
                record_kind="subjective_mem_lifecycle_idempotency_result",
                record_id=identity.result_id,
            ),
        )
    )


def _validate_proposal(proposal: SubjectiveMemForgetProposal) -> tuple[str, ...]:
    reasons: list[str] = []
    token_values = (
        proposal.expected_memory_id,
        proposal.expected_page_id,
        proposal.expected_block_id,
        proposal.expected_current_selector_id,
        proposal.expected_current_receipt_id,
        proposal.expected_memory_kind,
        proposal.expected_formation_stage,
        proposal.expected_revision_schema,
        proposal.expected_page_schema,
        proposal.expected_block_schema,
        proposal.expected_renderer_revision,
        proposal.expected_partition_revision,
        proposal.expected_platform_revision,
        proposal.authorization_id,
        proposal.reason_category,
        proposal.policy_revision,
    )
    if any(not _token(value) for value in token_values):
        reasons.append("subjective_mem_forget_identity_invalid")
    if (
        type(proposal.expected_current_revision) is not int
        or proposal.expected_current_revision < 1
    ):
        reasons.append("subjective_mem_forget_revision_invalid")
    if proposal.authorization_class not in {"user_management", "operator"}:
        reasons.append("subjective_mem_forget_authorization_invalid")
    if proposal.policy_revision != LIFECYCLE_POLICY_REVISION:
        reasons.append("subjective_mem_forget_policy_revision_invalid")
    if proposal.reason_category not in FORGET_REASON_CATEGORIES:
        reasons.append("subjective_mem_forget_reason_category_invalid")
    if (
        proposal.expected_lifecycle_state != "active"
        or proposal.expected_mutation_state != "none"
    ):
        reasons.append("subjective_mem_forget_precondition_invalid")
    if (
        not _digest(proposal.expected_page_digest, prefixed=True)
        or not _digest(proposal.expected_current_selector_digest)
        or not _digest(proposal.expected_current_receipt_digest)
        or not _digest(proposal.expected_scope_binding_digest)
        or not _digest(proposal.expected_formation_snapshot_digest)
    ):
        reasons.append("subjective_mem_forget_digest_invalid")
    if (
        proposal.expected_memory_kind not in {"episodic", "semantic"}
        or proposal.expected_formation_stage not in {"primary", "secondary"}
        or proposal.expected_revision_schema != SUBJECTIVE_MEM_REVISION_SCHEMA
        or proposal.expected_page_schema != PAGE_SCHEMA
        or proposal.expected_block_schema != LIFECYCLE_BLOCK_SCHEMA
        or proposal.expected_renderer_revision != RENDERER_REVISION
        or proposal.expected_partition_revision != PAGE_PARTITION_REVISION
        or proposal.expected_platform_revision != PLATFORM_REVISION
    ):
        reasons.append("subjective_mem_forget_contract_revision_mismatch")
    if (
        type(proposal.boundary) is not SubjectiveMemForgetBoundary
        or proposal.boundary.to_dict() != SubjectiveMemForgetBoundary().to_dict()
    ):
        reasons.append("subjective_mem_forget_boundary_invalid")
    if (
        type(proposal.expected_relative_path) is not str
        or proposal.expected_relative_path.startswith("/")
        or "\\" in proposal.expected_relative_path
        or any(
            part in {"", ".", "..", ".relaylm"}
            for part in proposal.expected_relative_path.split("/")
        )
        or not proposal.expected_relative_path.startswith("memory/")
    ):
        reasons.append("subjective_mem_forget_path_invalid")
    return tuple(dict.fromkeys(reasons))


def _evidence_space_directory_present(
    *, store: EvidenceRecordStore, evidence_space_id: str
) -> bool:
    if type(store) is not EvidenceRecordStore or not _token(evidence_space_id, 128):
        return False
    path = store.root / evidence_space_id
    try:
        return not path.is_symlink() and path.is_dir()
    except OSError:
        return False


def _read_claim_and_intent(
    *, store: EvidenceRecordStore, evidence_space_id: str, identity: _Identity
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    try:
        with store.transaction(evidence_space_id) as tx:
            claim = tx.read_record(
                record_kind="subjective_mem_lifecycle_claim",
                record_id=identity.operation_slot_id,
            )
            intent = tx.read_record(
                record_kind="subjective_mem_lifecycle_intent",
                record_id=identity.intent_id,
            )
            return claim, intent
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, None


def _derive_identity(
    *,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    memory_id: str,
    operation_key: str,
    input_digest: str,
) -> tuple[_Identity | None, tuple[str, ...]]:
    if (
        not all(_token(item) for item in (evidence_space_id, memory_id, operation_key))
        or not _digest(input_digest)
    ):
        return None, ("subjective_mem_forget_operation_identity_invalid",)
    authority_digest = canonical_digest(character_authority.to_dict())
    key_digest = sha256_hex(operation_key.encode("utf-8"))
    slot_material = "\0".join(
        (evidence_space_id, authority_digest, memory_id, "forget", key_digest)
    )
    slot = _opaque("smfkey", slot_material)
    operation_id = _opaque("smfop", slot + "\0" + input_digest)
    transition_id = _opaque("smftransition", operation_id)
    intent_id = _opaque("smfintent", operation_id)
    receipt_id = _opaque("smfreceipt", operation_id)
    result_id = _opaque("smfresult", slot)
    tombstone_id = _opaque("smftombstone", transition_id)
    return (
        _Identity(
            slot,
            operation_id,
            key_digest,
            input_digest,
            transition_id,
            intent_id,
            receipt_id,
            result_id,
            tombstone_id,
        ),
        (),
    )


def _strictly_after(candidate: str, *earlier: str) -> bool:
    try:
        candidate_time = _utc_text(candidate)
        return all(candidate_time > _utc_text(value) for value in earlier)
    except (TypeError, ValueError):
        return False


def _utc_text(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("subjective_mem_forget_time_invalid")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("subjective_mem_forget_time_invalid")
    return parsed.astimezone(timezone.utc)


def _status_for_reasons(reasons: tuple[str, ...]) -> ForgetStatus:
    if any("idempotency_conflict" in item for item in reasons):
        return "integrity_conflict"
    if any("recovery" in item or "foreign_image" in item for item in reasons):
        return "recovery_required"
    if any("lock_busy" in item for item in reasons):
        return "lock_busy"
    return "fail_closed"


def _result(
    status: ForgetStatus,
    *,
    identity: _Identity | None = None,
    proposal: SubjectiveMemForgetProposal | None = None,
    current_state: SubjectiveMemCurrentState | None = None,
    reasons: tuple[str, ...] = (),
    recovery_outcome: str | None = None,
    canonical_published: bool = False,
    receipt_present: bool = False,
    tombstone_present: bool = False,
    persisted: bool = False,
    post_digest: str | None = None,
) -> SubjectiveMemForgetResult:
    return SubjectiveMemForgetResult(
        status=status,
        transition_id=identity.transition_id if identity else None,
        receipt_id=identity.receipt_id if identity else None,
        tombstone_id=identity.tombstone_id if identity else None,
        memory_id=proposal.expected_memory_id if proposal else None,
        from_revision=proposal.expected_current_revision if proposal else None,
        to_revision=(proposal.expected_current_revision + 1) if proposal else None,
        current_state=current_state,
        blocked_reasons=tuple(dict.fromkeys(reasons)),
        recovery_outcome=recovery_outcome,
        canonical_markdown_published=canonical_published,
        lifecycle_receipt_present=receipt_present,
        tombstone_present=tombstone_present,
        persisted=persisted,
        _post_image_digest=post_digest,
    )


def _opaque(prefix: str, value: str) -> str:
    return f"{prefix}_{sha256_hex(value.encode('utf-8'))}"


def _token(value: object, max_length: int = 256) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= max_length
        and _TOKEN_RE.fullmatch(value) is not None
    )


def _digest(value: object, *, prefixed: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    if prefixed:
        return (
            len(value) == 71
            and value.startswith("sha256:")
            and all(ch in "0123456789abcdef" for ch in value[7:])
        )
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("subjective_mem_forget_naive_datetime_forbidden")
    return value.astimezone(timezone.utc)


def _fault(injector: FaultInjector | None, stage: str) -> None:
    if injector is not None:
        injector(stage)


__all__ = [
    "SubjectiveMemForgetResult",
    "SubjectiveMemLifecycleGate",
    "forget_subjective_mem",
    "resolve_subjective_mem_lifecycle_gate",
]
