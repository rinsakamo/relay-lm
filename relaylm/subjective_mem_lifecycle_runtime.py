"""LC-1A caller-invoked Subjective MEM Correct runtime.

This module implements only the first ordered LC-1 slice: Correct.  It appends
one immutable canonical Markdown successor and commits content-free lifecycle
operations records.  It does not implement Forget, Pin/Unpin, Restore,
Consolidate, ordinary Retrieval, Primary MEM migration, API/UI, background
recovery, or Purge.
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
    secure_platform_supported,
)
from relaylm.evidence.common import canonical_digest, sha256_hex, utf8_text_digest
from relaylm.evidence.store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.shared_assessment.models import SharedAssessmentCurrentState, SharedAssessmentRevision
from relaylm.shared_assessment.runtime import (
    shared_assessment_current_state_key,
    shared_assessment_revision_record_id,
)
from relaylm.subjective_mem_lifecycle_authority import (
    SubjectiveMemPredecessorExpectation,
    load_subjective_mem_predecessor_authority_locked,
)
from relaylm.subjective_mem_lifecycle_engine import (
    LifecycleExecutionOutcome,
    LifecycleFinalRecords,
    LifecycleFinalizer,
    LifecyclePublicationPlan,
    LogBinding,
    RecordBinding,
    lifecycle_claim_record,
    publish_lifecycle_post_image,
    read_lifecycle_reservation,
    read_prepared_post_image,
    reserve_lifecycle_publication,
    resolve_finalized_replay,
)
from relaylm.subjective_mem.models import (
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCharacterAuthority,
    SubjectiveMemCurrentState,
    SubjectiveMemRevision,
    SubjectiveMemStrength,
    resolve_subjective_mem_character_authority,
)
from relaylm.subjective_mem_lifecycle import (
    CORRECT_REASON_CATEGORIES,
    LIFECYCLE_INTENT_FINALIZATION_SCHEMA,
    LIFECYCLE_INTENT_SCHEMA,
    LIFECYCLE_POLICY_REVISION,
    LIFECYCLE_RECEIPT_SCHEMA,
    LIFECYCLE_RESULT_SCHEMA,
    LIFECYCLE_TRANSITION_SCHEMA,
    SubjectiveMemCorrectProposal,
    SubjectiveMemCorrectionBoundary,
    SubjectiveMemLifecycleTransition,
)
from relaylm.subjective_mem.markdown import (
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

LifecycleStatus = Literal[
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


@dataclass(frozen=True)
class SubjectiveMemLifecycleGate:
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    store: EvidenceRecordStore | None
    workspace_root: str | None


@dataclass(frozen=True, repr=False)
class SubjectiveMemLifecycleResult:
    status: LifecycleStatus
    operation_kind: str = "correct"
    transition_id: str | None = None
    receipt_id: str | None = None
    memory_id: str | None = None
    from_revision: int | None = None
    to_revision: int | None = None
    current_state: SubjectiveMemCurrentState | None = None
    blocked_reasons: tuple[str, ...] = ()
    recovery_outcome: str | None = None
    canonical_markdown_published: bool = False
    lifecycle_receipt_present: bool = False
    persisted: bool = False
    _post_image_digest: str | None = field(default=None, repr=False, compare=False)

    def to_log_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "operation_kind": self.operation_kind,
            "transition_id": self.transition_id,
            "receipt_id": self.receipt_id,
            "memory_id": self.memory_id,
            "from_revision": self.from_revision,
            "to_revision": self.to_revision,
            "lifecycle_state": self.current_state.lifecycle_state if self.current_state else None,
            "mutation_state": self.current_state.mutation_state if self.current_state else None,
            "retrieval_eligible": self.current_state.retrieval_eligible if self.current_state else False,
            "canonical_markdown_published": self.canonical_markdown_published,
            "lifecycle_receipt_present": self.lifecycle_receipt_present,
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


@dataclass(frozen=True)
class _Prepared:
    identity: _Identity
    predecessor: SubjectiveMemRevision
    successor: SubjectiveMemRevision
    current_state_key: str
    current_state: SubjectiveMemCurrentState
    prepared_state: SubjectiveMemCurrentState
    transition: SubjectiveMemLifecycleTransition
    page_plan: SubjectiveMemPagePlan
    intent: dict[str, object]
    record_bindings: tuple[RecordBinding, ...]
    log_bindings: tuple[LogBinding, ...]


def resolve_subjective_mem_lifecycle_gate(config: object) -> SubjectiveMemLifecycleGate:
    enabled = getattr(config, "subjective_mem_lifecycle_enabled", False)
    dry_run_only = getattr(config, "subjective_mem_lifecycle_dry_run_only", True)
    requested_apply = getattr(config, "subjective_mem_lifecycle_apply_enabled", False)
    triple = (enabled, dry_run_only, requested_apply)
    if any(type(item) is not bool for item in triple) or triple not in {
        (False, True, False),
        (True, True, False),
        (True, False, True),
    }:
        return SubjectiveMemLifecycleGate(False, True, False, None, None)
    if not enabled:
        return SubjectiveMemLifecycleGate(False, True, False, None, None)
    evidence_root = getattr(config, "evidence_data_root", None)
    workspace_root = getattr(config, "subjective_mem_workspace_root", None)
    store = None
    if isinstance(evidence_root, str) and evidence_root:
        try:
            store = EvidenceRecordStore(evidence_root)
        except ValueError:
            store = None
    workspace_valid = (
        isinstance(workspace_root, str)
        and bool(workspace_root)
        and Path(workspace_root).is_absolute()
        and not any(part in {".", ".."} for part in Path(workspace_root).parts[1:])
    )
    commit_triple = (
        getattr(config, "subjective_mem_commit_enabled", False),
        getattr(config, "subjective_mem_commit_dry_run_only", True),
        getattr(config, "subjective_mem_commit_apply_enabled", False),
    )
    apply_enabled = (
        requested_apply
        and not dry_run_only
        and commit_triple == (True, False, True)
        and store is not None
        and workspace_valid
        and secure_platform_supported()
    )
    return SubjectiveMemLifecycleGate(
        True,
        dry_run_only,
        apply_enabled,
        store,
        workspace_root if workspace_valid else None,
    )


def correct_subjective_mem(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_config: object,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    operation_idempotency_key: str,
    proposal: SubjectiveMemCorrectProposal,
    apply_enabled: bool,
    committed_at: datetime,
    observed_at: datetime | None = None,
    fault_injector: FaultInjector | None = None,
) -> SubjectiveMemLifecycleResult:
    """Apply or recover one exact active -> active Correct operation."""

    reasons: list[str] = []
    if type(store) is not EvidenceRecordStore:
        reasons.append("subjective_mem_lifecycle_store_invalid")
    if type(character_authority) is not SubjectiveMemCharacterAuthority:
        reasons.append("subjective_mem_lifecycle_character_authority_invalid")
    else:
        resolved, authority_reasons = resolve_subjective_mem_character_authority(
            character_config,
            workspace_or_tenant_ref=character_authority.workspace_or_tenant_ref,
            character_id=character_authority.character_id,
        )
        reasons.extend(authority_reasons)
        if resolved != character_authority:
            reasons.append("subjective_mem_lifecycle_character_authority_not_exact_current")
    if type(proposal) is not SubjectiveMemCorrectProposal:
        reasons.append("subjective_mem_lifecycle_correct_proposal_invalid")
    if type(apply_enabled) is not bool:
        reasons.append("subjective_mem_lifecycle_apply_mode_invalid")
    elif apply_enabled and not secure_platform_supported():
        reasons.append("subjective_mem_lifecycle_platform_unsupported")
    if type(workspace_root) is not str or not workspace_root:
        reasons.append("subjective_mem_lifecycle_workspace_root_missing")
    elif not Path(workspace_root).is_absolute():
        reasons.append("subjective_mem_lifecycle_workspace_root_not_absolute")
    elif Path(getattr(character_config, "subjective_mem_workspace_root", "")) != Path(workspace_root):
        reasons.append("subjective_mem_lifecycle_workspace_authority_changed")
    if fault_injector is not None and not callable(fault_injector):
        reasons.append("subjective_mem_lifecycle_fault_injector_invalid")
    try:
        final_time = _utc(committed_at)
        observed_time = _utc(observed_at or datetime.now(timezone.utc))
        if final_time > observed_time:
            reasons.append("subjective_mem_lifecycle_time_in_future")
    except (TypeError, ValueError):
        final_time = None
        reasons.append("subjective_mem_lifecycle_clock_invalid")
    if reasons:
        return _result("fail_closed", reasons=tuple(dict.fromkeys(reasons)))
    assert final_time is not None and isinstance(proposal, SubjectiveMemCorrectProposal)
    if not _evidence_space_directory_present(
        store=store, evidence_space_id=evidence_space_id
    ):
        return _result(
            "fail_closed",
            proposal=proposal,
            reasons=("subjective_mem_lifecycle_evidence_space_unavailable",),
        )

    identity, identity_reasons = _derive_identity(
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        memory_id=proposal.expected_memory_id,
        operation_key=operation_idempotency_key,
        input_digest=canonical_digest({
            "proposal_input_digest": proposal.input_digest,
            "operation_time": final_time.isoformat(),
        }),
    )
    if identity is None:
        return _result("fail_closed", reasons=identity_reasons)

    claim, intent, final_result, read_reasons = read_lifecycle_reservation(
        store=store,
        evidence_space_id=evidence_space_id,
        operation_slot_id=identity.operation_slot_id,
        intent_id=identity.intent_id,
        result_id=identity.result_id,
    )
    if read_reasons:
        return _result(
            "fail_closed", identity=identity, proposal=proposal, reasons=read_reasons
        )
    if final_result is not None:
        return _replay_finalized(
            store=store,
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            workspace_root=workspace_root,
            proposal=proposal,
            identity=identity,
            intent=intent,
            final_result=final_result,
        )
    if claim is not None:
        if claim.get("input_digest") != identity.input_digest:
            return _result(
                "integrity_conflict",
                identity=identity,
                proposal=proposal,
                reasons=("subjective_mem_lifecycle_idempotency_conflict",),
            )
        if intent is None:
            return _result(
                "fail_closed",
                identity=identity,
                proposal=proposal,
                reasons=("subjective_mem_lifecycle_intent_missing_or_corrupt",),
            )
        if intent.get("operation_id") != identity.operation_id:
            return _result(
                "fail_closed",
                identity=identity,
                proposal=proposal,
                reasons=("subjective_mem_lifecycle_intent_corrupt",),
            )
        return _recover_prepared(
            store=store,
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            workspace_root=workspace_root,
            proposal=proposal,
            identity=identity,
            claim=claim,
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
            post_digest=prepared.page_plan.post_image_digest,
        )

    execution_plan = _execution_plan(
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        workspace_root=workspace_root,
        identity=identity,
        intent=prepared.intent,
        prepared_state=prepared.prepared_state,
        record_bindings=prepared.record_bindings,
        log_bindings=prepared.log_bindings,
        current_state=prepared.current_state,
    )
    if execution_plan is None:
        return _result(
            "fail_closed",
            identity=identity,
            proposal=proposal,
            reasons=("subjective_mem_lifecycle_intent_corrupt",),
        )
    reservation = reserve_lifecycle_publication(
        store=store,
        plan=execution_plan,
        post_image=prepared.page_plan.rendered_bytes,
        fault_injector=fault_injector,
    )
    if reservation.status != "reserved":
        return _result_from_outcome(
            reservation, identity=identity, proposal=proposal, plan=execution_plan
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
            post_digest=prepared.page_plan.post_image_digest,
        )
    outcome = publish_lifecycle_post_image(
        store=store,
        plan=execution_plan,
        post_image=prepared.page_plan.rendered_bytes,
        finalizer=_correct_finalizer(
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            identity=identity,
            intent=prepared.intent,
        ),
        fault_injector=fault_injector,
    )
    return _result_from_outcome(
        outcome, identity=identity, proposal=proposal, plan=execution_plan
    )


def _prepare_new(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    proposal: SubjectiveMemCorrectProposal,
    identity: _Identity,
    committed_at: str,
) -> tuple[_Prepared | None, tuple[str, ...]]:
    reasons = list(_validate_proposal(proposal))
    if proposal.expected_lifecycle_state != "active":
        reasons.append("subjective_mem_lifecycle_correct_transition_unsupported")
    if proposal.expected_mutation_state != "none":
        reasons.append("subjective_mem_lifecycle_mutation_in_progress")
    page_id, relative_path, partition = (None, None, None)
    try:
        page_id, relative_path, partition = subjective_mem_page_identity(
            character_id=character_authority.character_id,
            memory_kind="episodic" if "/episodes/" in proposal.expected_relative_path else "semantic",
        )
    except ValueError:
        reasons.append("subjective_mem_lifecycle_page_identity_invalid")
    if page_id != proposal.expected_page_id or relative_path != proposal.expected_relative_path:
        reasons.append("subjective_mem_lifecycle_page_identity_mismatch")
    if reasons:
        return None, tuple(dict.fromkeys(reasons))

    try:
        with store.transaction(evidence_space_id) as tx:
            selector_raw, selector_reasons = _load_exact_selector_locked(
                tx=tx,
                proposal=proposal,
                character_id=character_authority.character_id,
            )
            if selector_raw is None:
                return None, selector_reasons
            assessment_reasons = _validate_assessment_locked(tx=tx, proposal=proposal)
            if assessment_reasons:
                return None, assessment_reasons
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, ("subjective_mem_lifecycle_store_unavailable",)

    inspected = inspect_canonical_page(
        workspace_root=workspace_root,
        character_id=character_authority.character_id,
        relative_path=proposal.expected_relative_path,
    )
    if inspected.snapshot is None or inspected.snapshot.data is None:
        return None, inspected.reasons or ("subjective_mem_lifecycle_canonical_page_missing",)
    snapshot = inspected.snapshot
    if snapshot.digest != proposal.expected_page_digest:
        return None, ("subjective_mem_lifecycle_page_digest_mismatch",)
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
        return None, ("subjective_mem_lifecycle_current_revision_not_exact",)
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
            proposal.assessment_revision.created_at,
            proposal.assessment_current_state.updated_at,
        )
    ):
        return None, ("subjective_mem_lifecycle_current_revision_invalid",)
    try:
        with store.transaction(evidence_space_id) as tx:
            record_bindings, log_bindings, authority_reasons = (
                _read_authority_bindings_locked(
                    tx=tx,
                    proposal=proposal,
                    predecessor=predecessor,
                    character_authority=character_authority,
                    evidence_space_id=evidence_space_id,
                )
            )
            if authority_reasons:
                return None, authority_reasons
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, ("subjective_mem_lifecycle_store_unavailable",)
    if _no_semantic_change(predecessor, proposal):
        return None, ("subjective_mem_lifecycle_correction_no_change",)

    successor = SubjectiveMemRevision(
        memory_id=predecessor.memory_id,
        character_id=predecessor.character_id,
        assessment_id=proposal.assessment_revision.assessment_id,
        assessment_revision=proposal.assessment_revision.assessment_revision,
        grounded_content=proposal.corrected_grounded_content,
        grounded_content_digest=proposal.assessment_revision.supported_content_digest,
        subjective_meaning=proposal.corrected_subjective_meaning,
        memory_kind=predecessor.memory_kind,
        scope_binding=predecessor.scope_binding,
        formation_snapshot=predecessor.formation_snapshot,
        strength=proposal.corrected_strength,
        decision_id=identity.transition_id,
        created_at=committed_at,
        memory_revision=predecessor.memory_revision + 1,
        formation_stage=predecessor.formation_stage,
        lifecycle_state="active",
        retrieval_visible=True,
        predecessor_revision_or_null=predecessor.memory_revision,
        authorization_kind="lifecycle_transition",
    )
    transition = SubjectiveMemLifecycleTransition(
        transition_id=identity.transition_id,
        character_id=predecessor.character_id,
        memory_id=predecessor.memory_id,
        from_revision=predecessor.memory_revision,
        to_revision=successor.memory_revision,
        operation="correct",
        from_lifecycle_state="active",
        to_lifecycle_state="active",
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
    page_plan = plan_result.plan
    current_state = _current_state_from_dict(selector_raw)
    if current_state is None:
        return None, ("subjective_mem_lifecycle_current_selector_not_exact",)
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
        plan=page_plan,
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
            page_plan=page_plan,
            intent=intent,
            record_bindings=record_bindings,
            log_bindings=log_bindings,
        ),
        (),
    )


def _recover_prepared(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    proposal: SubjectiveMemCorrectProposal,
    identity: _Identity,
    claim: dict[str, object],
    intent: dict[str, object],
    fault_injector: FaultInjector | None,
) -> SubjectiveMemLifecycleResult:
    exact = _intent_exact(
        intent,
        identity=identity,
        proposal=proposal,
        character_authority=character_authority,
        evidence_space_id=evidence_space_id,
        workspace_root=workspace_root,
    )
    prepared_state = _prepared_state_from_intent(intent) if exact else None
    if prepared_state is None:
        return _result(
            "fail_closed",
            identity=identity,
            proposal=proposal,
            reasons=("subjective_mem_lifecycle_intent_corrupt",),
        )
    selector_reasons = _prepared_selector_unchanged(
        store=store,
        evidence_space_id=evidence_space_id,
        selector_id=str(intent["current_selector_id"]),
        prepared_state=prepared_state,
    )
    if selector_reasons:
        return _result(
            _status_for_reasons(selector_reasons),
            identity=identity,
            proposal=proposal,
            reasons=selector_reasons,
        )
    post_image, predecessor, artifact_reasons = _exact_prepared_post_image(
        workspace_root=workspace_root,
        character_authority=character_authority,
        proposal=proposal,
        intent=intent,
    )
    if post_image is None or predecessor is None:
        return _result(
            "recovery_required",
            identity=identity,
            proposal=proposal,
            current_state=prepared_state,
            reasons=artifact_reasons,
            recovery_outcome="artifact_unavailable",
            persisted=True,
        )
    return _publish_recovered_post_image(
        store=store,
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        workspace_root=workspace_root,
        proposal=proposal,
        identity=identity,
        claim=claim,
        intent=intent,
        prepared_state=prepared_state,
        predecessor=predecessor,
        post_image=post_image,
        fault_injector=fault_injector,
    )


def _prepared_selector_unchanged(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    selector_id: str,
    prepared_state: SubjectiveMemCurrentState,
) -> tuple[str, ...]:
    try:
        with store.transaction(evidence_space_id) as tx:
            _raw, reasons = _load_exact_selector_locked_raw(
                tx=tx, selector_id=selector_id, expected=prepared_state.to_dict()
            )
            return reasons
    except (OSError, RuntimeError, TypeError, ValueError):
        return ("subjective_mem_lifecycle_store_unavailable",)


def _exact_prepared_post_image(
    *,
    workspace_root: str,
    character_authority: SubjectiveMemCharacterAuthority,
    proposal: SubjectiveMemCorrectProposal,
    intent: dict[str, object],
) -> tuple[bytes | None, SubjectiveMemRevision | None, tuple[str, ...]]:
    """Load the reserved post-image and its exact Correct predecessor revision."""

    artifact, reasons = read_prepared_post_image(
        workspace_root=workspace_root,
        character_id=character_authority.character_id,
        artifact_id=str(intent["artifact_id"]),
        expected_post_image_digest=str(intent["post_image_digest"]),
    )
    default = ("subjective_mem_lifecycle_artifact_invalid",)
    if artifact is None:
        return None, None, reasons or default
    if not _artifact_exact_for_intent(
        artifact,
        intent=intent,
        proposal=proposal,
        character_authority=character_authority,
    ):
        return None, None, default
    predecessor = _predecessor_from_artifact(
        artifact, intent=intent, proposal=proposal, character_authority=character_authority
    )
    if predecessor is None:
        return None, None, default
    return artifact, predecessor, ()


def _publish_recovered_post_image(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    proposal: SubjectiveMemCorrectProposal,
    identity: _Identity,
    claim: dict[str, object],
    intent: dict[str, object],
    prepared_state: SubjectiveMemCurrentState,
    predecessor: SubjectiveMemRevision,
    post_image: bytes,
    fault_injector: FaultInjector | None,
) -> SubjectiveMemLifecycleResult:
    record_bindings, log_bindings, authority_reasons = _read_authority_bindings(
        store=store,
        evidence_space_id=evidence_space_id,
        proposal=proposal,
        predecessor=predecessor,
        character_authority=character_authority,
    )
    if authority_reasons:
        # The predecessor authority a prepared intent was reserved against is no
        # longer exact.  Stay forward-only and leave the canonical page untouched.
        return _result(
            "recovery_pending",
            identity=identity,
            proposal=proposal,
            current_state=prepared_state,
            reasons=("subjective_mem_commit_pre_image_authority_changed",),
            recovery_outcome="pre_image_pending_publication",
            persisted=True,
            post_digest=str(intent["post_image_digest"]),
        )
    execution_plan = _execution_plan(
        evidence_space_id=evidence_space_id,
        character_authority=character_authority,
        workspace_root=workspace_root,
        identity=identity,
        intent=intent,
        prepared_state=prepared_state,
        record_bindings=record_bindings,
        log_bindings=log_bindings,
    )
    if execution_plan is None or claim != lifecycle_claim_record(execution_plan):
        return _result(
            "fail_closed",
            identity=identity,
            proposal=proposal,
            reasons=("subjective_mem_lifecycle_intent_corrupt",),
        )
    outcome = publish_lifecycle_post_image(
        store=store,
        plan=execution_plan,
        post_image=post_image,
        finalizer=_correct_finalizer(
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            identity=identity,
            intent=intent,
        ),
        fault_injector=fault_injector,
    )
    return _result_from_outcome(
        outcome, identity=identity, proposal=proposal, plan=execution_plan
    )


def _replay_finalized(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    proposal: SubjectiveMemCorrectProposal,
    identity: _Identity,
    intent: dict[str, object] | None,
    final_result: dict[str, object],
) -> SubjectiveMemLifecycleResult:
    if final_result.get("input_digest") != identity.input_digest:
        return _result(
            "integrity_conflict",
            identity=identity,
            proposal=proposal,
            reasons=("subjective_mem_lifecycle_idempotency_conflict",),
        )
    execution_plan = None
    if isinstance(intent, dict) and _intent_exact(
        intent,
        identity=identity,
        proposal=proposal,
        character_authority=character_authority,
        evidence_space_id=evidence_space_id,
        workspace_root=workspace_root,
    ):
        prepared_state = _prepared_state_from_intent(intent)
        if prepared_state is not None:
            execution_plan = _execution_plan(
                evidence_space_id=evidence_space_id,
                character_authority=character_authority,
                workspace_root=workspace_root,
                identity=identity,
                intent=intent,
                prepared_state=prepared_state,
            )
    outcome = (
        resolve_finalized_replay(
            store=store,
            plan=execution_plan,
            finalizer=_correct_finalizer(
                evidence_space_id=evidence_space_id,
                character_authority=character_authority,
                identity=identity,
                intent=intent,
            ),
        )
        if execution_plan is not None and isinstance(intent, dict)
        else None
    )
    if outcome is None:
        return _result(
            "fail_closed",
            identity=identity,
            proposal=proposal,
            reasons=("subjective_mem_lifecycle_final_result_incomplete",),
        )
    return _result_from_outcome(
        outcome, identity=identity, proposal=proposal, plan=execution_plan
    )


def _execution_plan(
    *,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    identity: _Identity,
    intent: dict[str, object],
    prepared_state: SubjectiveMemCurrentState,
    record_bindings: tuple[RecordBinding, ...] = (),
    log_bindings: tuple[LogBinding, ...] = (),
    current_state: SubjectiveMemCurrentState | None = None,
) -> LifecyclePublicationPlan | None:
    """Materialize the exact operation-neutral execution plan for this Correct."""

    try:
        _page_id, relative_path, _partition = subjective_mem_page_identity(
            character_id=character_authority.character_id,
            memory_kind=str(intent["memory_kind"]),
        )
        return LifecyclePublicationPlan(
            evidence_space_id=evidence_space_id,
            character_id=character_authority.character_id,
            workspace_root=workspace_root,
            operation_kind="correct",
            operation_slot_id=identity.operation_slot_id,
            operation_id=identity.operation_id,
            operation_key_digest=identity.operation_key_digest,
            input_digest=identity.input_digest,
            intent_id=identity.intent_id,
            transition_id=identity.transition_id,
            receipt_id=identity.receipt_id,
            result_id=identity.result_id,
            memory_id=str(intent["memory_id"]),
            from_revision=intent["from_revision"],  # type: ignore[arg-type]
            to_revision=intent["to_revision"],  # type: ignore[arg-type]
            to_lifecycle_state=str(intent["to_lifecycle_state"]),
            selector_id=str(intent["current_selector_id"]),
            prepared_state=prepared_state,
            page_id=str(intent["page_id"]),
            page_partition=str(intent["partition"]),
            page_relative_path=relative_path,
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
            log_bindings=log_bindings,
            current_state=current_state,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _prepared_state_from_intent(
    intent: dict[str, object]
) -> SubjectiveMemCurrentState | None:
    try:
        state = SubjectiveMemCurrentState(
            memory_state_id=str(intent["current_selector_id"]),
            memory_id=str(intent["memory_id"]),
            character_id=str(intent["character_id"]),
            current_revision=int(intent["from_revision"]),  # type: ignore[call-overload]
            lifecycle_state=str(intent["from_lifecycle_state"]),
            mutation_state="prepared",
            retrieval_eligible=False,
            updated_at=str(intent["prepared_at"]),
            workspace_authority_digest=str(intent["workspace_authority_digest"]),
            scope_binding_digest=str(intent["scope_binding_digest"]),
            page_id=str(intent["page_id"]),
            block_id=str(intent["predecessor_block_id"]),
            canonical_page_digest=str(intent["pre_image_digest"]),
            authorization_kind=str(intent["predecessor_authorization_kind"]),
            authorization_id=str(intent["predecessor_authorization_id"]),
            current_receipt_id=str(intent["current_receipt_id"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if canonical_digest(state.to_dict()) != intent.get(
        "prepared_current_state_digest"
    ):
        return None
    return state


def _read_authority_bindings(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    proposal: SubjectiveMemCorrectProposal,
    predecessor: SubjectiveMemRevision,
    character_authority: SubjectiveMemCharacterAuthority,
) -> tuple[tuple[RecordBinding, ...], tuple[LogBinding, ...], tuple[str, ...]]:
    try:
        with store.transaction(evidence_space_id) as tx:
            return _read_authority_bindings_locked(
                tx=tx,
                proposal=proposal,
                predecessor=predecessor,
                character_authority=character_authority,
                evidence_space_id=evidence_space_id,
            )
    except (OSError, RuntimeError, TypeError, ValueError):
        return (), (), ("subjective_mem_lifecycle_store_unavailable",)


def _read_authority_bindings_locked(
    *,
    tx: EvidenceStoreTransaction,
    proposal: SubjectiveMemCorrectProposal,
    predecessor: SubjectiveMemRevision,
    character_authority: SubjectiveMemCharacterAuthority,
    evidence_space_id: str,
) -> tuple[tuple[RecordBinding, ...], tuple[LogBinding, ...], tuple[str, ...]]:
    """Validate and bind the exact Correct-specific authority this plan depends on."""

    authority, authority_reasons = load_subjective_mem_predecessor_authority_locked(
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
    if authority is None:
        return (), (), authority_reasons
    reasons = _validate_assessment_locked(tx=tx, proposal=proposal)
    if reasons:
        return (), (), reasons
    assessment_id = proposal.assessment_revision.assessment_id
    assessment_key = shared_assessment_current_state_key(assessment_id)
    assessment_record_id = shared_assessment_revision_record_id(
        assessment_id, proposal.assessment_revision.assessment_revision
    )
    assessment_revision = tx.read_record(
        record_kind="shared_assessment_revision",
        record_id=assessment_record_id,
    )
    events = tx.read_log(log_kind="shared_assessment_current_state", key=assessment_key)
    if (
        not isinstance(assessment_revision, dict)
        or not assessment_revision
        or not isinstance(events, list)
    ):
        return (), (), ("subjective_mem_lifecycle_predecessor_authority_missing",)
    records = authority.record_bindings + (
        ("shared_assessment_revision", assessment_record_id, assessment_revision),
    )
    logs = (("shared_assessment_current_state", assessment_key, tuple(events)),)
    return records, logs, ()


def _correct_finalizer(
    *,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    identity: _Identity,
    intent: dict[str, object] | None,
) -> LifecycleFinalizer:
    """Bind the deterministic Correct finalizer the engine invokes exactly once."""

    def finalize(final_state: SubjectiveMemCurrentState) -> LifecycleFinalRecords | None:
        if not isinstance(intent, dict):
            return None
        return _build_final_records(
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            identity=identity,
            intent=intent,
            final_state=final_state,
        )

    return finalize


def _result_from_outcome(
    outcome: LifecycleExecutionOutcome,
    *,
    identity: _Identity,
    proposal: SubjectiveMemCorrectProposal,
    plan: LifecyclePublicationPlan | None,
) -> SubjectiveMemLifecycleResult:
    """Map one bounded neutral engine outcome onto the unchanged Correct result."""

    status: LifecycleStatus = (
        _status_for_reasons(outcome.reasons)
        if outcome.status == "fail_closed"
        else outcome.status  # type: ignore[assignment]
    )
    return _result(
        status,
        identity=identity,
        proposal=proposal,
        current_state=outcome.current_state,
        reasons=outcome.reasons,
        recovery_outcome=outcome.recovery_outcome,
        canonical_published=outcome.canonical_page_published,
        receipt_present=outcome.lifecycle_receipt_present,
        persisted=outcome.persisted,
        post_digest=(
            plan.post_image_digest
            if plan is not None and outcome.recovery_outcome is not None
            else None
        ),
    )


def _build_final_records(
    *,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    identity: _Identity,
    intent: dict[str, object],
    final_state: SubjectiveMemCurrentState,
) -> LifecycleFinalRecords | None:
    try:
        return _correct_final_records(
            evidence_space_id=evidence_space_id,
            character_authority=character_authority,
            identity=identity,
            intent=intent,
            final_state=final_state,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _correct_final_records(
    *,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    identity: _Identity,
    intent: dict[str, object],
    final_state: SubjectiveMemCurrentState,
) -> LifecycleFinalRecords:
    transition = {
        "schema": "relaylm.subjective_mem_lifecycle_transition.v1",
        "transition_id": identity.transition_id,
        "character_id": character_authority.character_id,
        "memory_id": intent["memory_id"],
        "from_revision": intent["from_revision"],
        "to_revision": intent["to_revision"],
        "operation": "correct",
        "from_lifecycle_state": "active",
        "to_lifecycle_state": "active",
        "from_formation_stage": intent["formation_stage"],
        "to_formation_stage": intent["formation_stage"],
        "authorized_by": intent["authorization_class"],
        "committed_at": intent["prepared_at"],
    }
    receipt_body: dict[str, object] = {
        "schema": LIFECYCLE_RECEIPT_SCHEMA,
        "receipt_id": identity.receipt_id,
        "intent_id": identity.intent_id,
        "intent_digest": canonical_digest(intent),
        "operation_id": identity.operation_id,
        "operation_kind": "correct",
        "operation_outcome": "committed",
        "input_digest": identity.input_digest,
        "evidence_space_id": evidence_space_id,
        "character_id": character_authority.character_id,
        "memory_ref": {
            "memory_id": intent["memory_id"],
            "memory_revision": intent["to_revision"],
        },
        "predecessor_revision": intent["from_revision"],
        "transition_id": identity.transition_id,
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
        "finalization_id": _opaque("smlintentfin", identity.intent_id),
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
        "operation_kind": "correct",
        "input_digest": identity.input_digest,
        "receipt_id": identity.receipt_id,
        "receipt_digest": receipt["receipt_digest"],
        "transition_id": identity.transition_id,
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
        "projection_state": "rebuild_required",
        "ordinary_retrieval_wired": False,
        "updated_at": intent["prepared_at"],
    }
    return LifecycleFinalRecords(
        transition=transition,
        receipt=receipt,
        finalization=finalization,
        result=result,
        projection=projection,
    )


def _build_intent(
    *,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    workspace_root: str,
    proposal: SubjectiveMemCorrectProposal,
    identity: _Identity,
    predecessor: SubjectiveMemRevision,
    successor: SubjectiveMemRevision,
    prepared_state: SubjectiveMemCurrentState,
    transition: SubjectiveMemLifecycleTransition,
    plan: SubjectiveMemPagePlan,
    prepared_at: str,
) -> dict[str, object]:
    return {
        "schema": LIFECYCLE_INTENT_SCHEMA,
        "intent_id": identity.intent_id,
        "operation_slot_id": identity.operation_slot_id,
        "operation_id": identity.operation_id,
        "operation_kind": "correct",
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


def _validate_proposal(proposal: SubjectiveMemCorrectProposal) -> tuple[str, ...]:
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
        reasons.append("subjective_mem_lifecycle_correct_identity_invalid")
    if type(proposal.expected_current_revision) is not int or proposal.expected_current_revision < 1:
        reasons.append("subjective_mem_lifecycle_correct_revision_invalid")
    if proposal.authorization_class not in {"user_management", "operator"}:
        reasons.append("subjective_mem_lifecycle_correct_authorization_invalid")
    if proposal.policy_revision != LIFECYCLE_POLICY_REVISION:
        reasons.append("subjective_mem_lifecycle_correct_policy_revision_invalid")
    if proposal.reason_category not in CORRECT_REASON_CATEGORIES:
        reasons.append("subjective_mem_lifecycle_correct_reason_category_invalid")
    if proposal.expected_lifecycle_state != "active" or proposal.expected_mutation_state != "none":
        reasons.append("subjective_mem_lifecycle_correct_precondition_invalid")
    if (
        not _digest(proposal.expected_page_digest, prefixed=True)
        or not _digest(proposal.expected_current_selector_digest)
        or not _digest(proposal.expected_current_receipt_digest)
        or not _digest(proposal.expected_scope_binding_digest)
        or not _digest(proposal.expected_formation_snapshot_digest)
    ):
        reasons.append("subjective_mem_lifecycle_correct_digest_invalid")
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
        reasons.append("subjective_mem_lifecycle_correct_contract_revision_mismatch")
    if type(proposal.corrected_grounded_content) is not str or not 1 <= len(proposal.corrected_grounded_content) <= 8000:
        reasons.append("subjective_mem_lifecycle_correct_grounded_content_invalid")
    if type(proposal.corrected_subjective_meaning) is not str or not 1 <= len(proposal.corrected_subjective_meaning) <= 4000:
        reasons.append("subjective_mem_lifecycle_correct_subjective_meaning_invalid")
    if type(proposal.assessment_revision) is not SharedAssessmentRevision or type(proposal.assessment_current_state) is not SharedAssessmentCurrentState:
        reasons.append("subjective_mem_lifecycle_correct_assessment_invalid")
    else:
        if (
            proposal.assessment_current_state.assessment_id != proposal.assessment_revision.assessment_id
            or proposal.assessment_current_state.current_revision != proposal.assessment_revision.assessment_revision
            or proposal.assessment_current_state.lifecycle_state != "active"
            or proposal.assessment_current_state.authorization_state != "current_admitted"
            or proposal.assessment_revision.character_independent is not True
            or proposal.corrected_grounded_content != proposal.assessment_revision.supported_content
            or utf8_text_digest(proposal.corrected_grounded_content) != proposal.assessment_revision.supported_content_digest
        ):
            reasons.append("subjective_mem_lifecycle_correct_grounding_invalid")
    if not _valid_strength(
        proposal.corrected_strength,
        support_state=(
            proposal.assessment_revision.support_state
            if type(proposal.assessment_revision) is SharedAssessmentRevision
            else None
        ),
    ):
        reasons.append("subjective_mem_lifecycle_correct_strength_invalid")
    if type(proposal.boundary) is not SubjectiveMemCorrectionBoundary or proposal.boundary.to_dict() != SubjectiveMemCorrectionBoundary().to_dict():
        reasons.append("subjective_mem_lifecycle_correct_boundary_invalid")
    if (
        type(proposal.expected_relative_path) is not str
        or proposal.expected_relative_path.startswith("/")
        or "\\" in proposal.expected_relative_path
        or any(part in {"", ".", "..", ".relaylm"} for part in proposal.expected_relative_path.split("/"))
        or not proposal.expected_relative_path.startswith("memory/")
    ):
        reasons.append("subjective_mem_lifecycle_correct_path_invalid")
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

def _validate_assessment_locked(*, tx: EvidenceStoreTransaction, proposal: SubjectiveMemCorrectProposal) -> tuple[str, ...]:
    raw_revision = tx.read_record(
        record_kind="shared_assessment_revision",
        record_id=shared_assessment_revision_record_id(
            proposal.assessment_revision.assessment_id,
            proposal.assessment_revision.assessment_revision,
        ),
    )
    raw_state = tx.read_log(
        log_kind="shared_assessment_current_state",
        key=shared_assessment_current_state_key(proposal.assessment_revision.assessment_id),
    )
    if raw_revision != proposal.assessment_revision.to_dict():
        return ("subjective_mem_lifecycle_assessment_revision_not_exact_stored",)
    if raw_state != [proposal.assessment_current_state.to_dict()]:
        return ("subjective_mem_lifecycle_assessment_current_state_not_exact_stored",)
    return ()


def _load_exact_selector_locked(
    *, tx: EvidenceStoreTransaction, proposal: SubjectiveMemCorrectProposal, character_id: str
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    events = tx.read_log(log_kind="subjective_mem_current_state", key=proposal.expected_current_selector_id)
    if not isinstance(events, list) or len(events) != 1 or not isinstance(events[0], dict):
        return None, ("subjective_mem_lifecycle_current_selector_missing_or_corrupt",)
    raw = events[0]
    state = _current_state_from_dict(raw)
    if state is None or (
        state.memory_state_id != proposal.expected_current_selector_id
        or state.memory_id != proposal.expected_memory_id
        or state.character_id != character_id
        or state.current_revision != proposal.expected_current_revision
        or state.lifecycle_state != proposal.expected_lifecycle_state
        or state.mutation_state != proposal.expected_mutation_state
        or state.retrieval_eligible is not True
        or canonical_digest(raw) != proposal.expected_current_selector_digest
    ):
        return None, ("subjective_mem_lifecycle_current_selector_not_exact",)
    uniqueness = _validate_selector_uniqueness_locked(
        tx=tx,
        selector_id=proposal.expected_current_selector_id,
        character_id=character_id,
        memory_id=proposal.expected_memory_id,
        expected=raw,
    )
    if uniqueness:
        return None, uniqueness
    return raw, ()


def _load_exact_selector_locked_raw(
    *, tx: EvidenceStoreTransaction, selector_id: str, expected: dict[str, object]
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    events = tx.read_log(log_kind="subjective_mem_current_state", key=selector_id)
    if events != [expected]:
        return None, ("subjective_mem_lifecycle_current_selector_changed",)
    return expected, ()


def _validate_selector_uniqueness_locked(
    *,
    tx: EvidenceStoreTransaction,
    selector_id: str,
    character_id: str,
    memory_id: str,
    expected: dict[str, object],
) -> tuple[str, ...]:
    matches = [
        (key, events)
        for key, events in tx.list_logs(log_kind="subjective_mem_current_state", limit=4096)
        if any(item.get("character_id") == character_id and item.get("memory_id") == memory_id for item in events)
    ]
    if len(matches) != 1 or matches[0] != (selector_id, [expected]):
        return ("subjective_mem_lifecycle_duplicate_logical_current_selector",)
    return ()
def _predecessor_from_artifact(
    artifact: bytes,
    *,
    intent: dict[str, object],
    proposal: SubjectiveMemCorrectProposal,
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
    proposal: SubjectiveMemCorrectProposal,
    character_authority: SubjectiveMemCharacterAuthority,
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
        and successor_revision.grounded_content == proposal.corrected_grounded_content
        and successor_revision.subjective_meaning == proposal.corrected_subjective_meaning
        and successor_revision.strength.to_dict() == proposal.corrected_strength.to_dict()
        and successor_revision.assessment_id == proposal.assessment_revision.assessment_id
        and successor_revision.assessment_revision
        == proposal.assessment_revision.assessment_revision
        and successor_revision.authorization_kind == "lifecycle_transition"
        and successor_revision.authorization_id == identity_transition(intent)
        and canonical_page_digest(artifact) == intent.get("post_image_digest")
    )


def identity_transition(intent: dict[str, object]) -> str:
    return str(intent.get("transition_id", ""))


def _workspace_authority_digest(
    workspace_root: str,
    character_authority: SubjectiveMemCharacterAuthority,
) -> str:
    return canonical_digest({
        "workspace_root_digest": sha256_hex(workspace_root.encode("utf-8")),
        "character_authority": character_authority.to_dict(),
    })

def _intent_exact(
    intent: dict[str, object],
    *,
    identity: _Identity,
    proposal: SubjectiveMemCorrectProposal,
    character_authority: SubjectiveMemCharacterAuthority,
    evidence_space_id: str,
    workspace_root: str,
) -> bool:
    required = {
        "schema", "intent_id", "operation_slot_id", "operation_id", "operation_kind",
        "operation_key_digest", "input_digest", "evidence_space_id", "character_id",
        "character_authority_digest", "workspace_authority_digest", "memory_id", "memory_kind",
        "formation_stage", "scope_binding_digest", "from_revision", "to_revision",
        "from_lifecycle_state", "to_lifecycle_state", "predecessor_revision_digest",
        "predecessor_block_id", "predecessor_authorization_kind", "predecessor_authorization_id",
        "successor_revision_digest", "transition_id", "receipt_id", "authorization_class",
        "authorization_id", "reason_category", "policy_revision", "current_receipt_id",
        "current_receipt_digest", "current_selector_id", "current_selector_digest",
        "prepared_current_state_digest", "page_id", "partition", "successor_block_id",
        "pre_image_state", "pre_image_digest", "post_image_digest", "successor_block_digest",
        "artifact_id", "artifact_digest", "revision_schema", "page_schema", "block_schema",
        "renderer_revision", "partition_revision", "platform_revision", "prepared_at",
        "recovery_state",
    }
    prepared_at = intent.get("prepared_at")
    operation_digest = canonical_digest({
        "proposal_input_digest": proposal.input_digest,
        "operation_time": prepared_at,
    })
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
        and intent.get("scope_binding_digest") == proposal.expected_scope_binding_digest
        and intent.get("from_revision") == proposal.expected_current_revision
        and intent.get("to_revision") == proposal.expected_current_revision + 1
        and intent.get("from_lifecycle_state") == "active"
        and intent.get("to_lifecycle_state") == "active"
        and intent.get("predecessor_block_id") == proposal.expected_block_id
        and intent.get("transition_id") == identity.transition_id
        and intent.get("receipt_id") == identity.receipt_id
        and intent.get("authorization_class") == proposal.authorization_class
        and intent.get("authorization_id") == proposal.authorization_id
        and intent.get("reason_category") == proposal.reason_category
        and intent.get("policy_revision") == proposal.policy_revision
        and intent.get("current_receipt_id") == proposal.expected_current_receipt_id
        and intent.get("current_receipt_digest") == proposal.expected_current_receipt_digest
        and intent.get("current_selector_id") == proposal.expected_current_selector_id
        and intent.get("current_selector_digest") == proposal.expected_current_selector_digest
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
        and intent.get("partition_revision") == proposal.expected_partition_revision
        and intent.get("platform_revision") == proposal.expected_platform_revision
        and intent.get("recovery_state") == "prepared"
        and isinstance(prepared_at, str)
    )


def _current_state_from_dict(raw: object) -> SubjectiveMemCurrentState | None:
    if not isinstance(raw, dict):
        return None
    binding = raw.get("authority_binding")
    if binding is not None and not isinstance(binding, dict):
        return None
    authorization = (
        binding.get("authorization_ref") if isinstance(binding, dict) else None
    )
    if authorization is not None and not isinstance(authorization, dict):
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
            workspace_authority_digest=(
                binding.get("workspace_authority_digest")
                if isinstance(binding, dict)
                else None
            ),
            scope_binding_digest=(
                binding.get("scope_binding_digest")
                if isinstance(binding, dict)
                else None
            ),
            page_id=(binding.get("page_id") if isinstance(binding, dict) else None),
            block_id=(binding.get("block_id") if isinstance(binding, dict) else None),
            canonical_page_digest=(
                binding.get("canonical_page_digest")
                if isinstance(binding, dict)
                else None
            ),
            authorization_kind=(
                authorization.get("authority_kind")
                if isinstance(authorization, dict)
                else None
            ),
            authorization_id=(
                authorization.get("authority_id")
                if isinstance(authorization, dict)
                else None
            ),
            current_receipt_id=(
                binding.get("current_receipt_id")
                if isinstance(binding, dict)
                else None
            ),
        )
    except (KeyError, TypeError, ValueError):
        return None
    return state if state.to_dict() == raw else None


def _derive_identity(
    *,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    memory_id: str,
    operation_key: str,
    input_digest: str,
) -> tuple[_Identity | None, tuple[str, ...]]:
    if not all(_token(item) for item in (evidence_space_id, memory_id, operation_key)) or not _digest(input_digest):
        return None, ("subjective_mem_lifecycle_operation_identity_invalid",)
    authority_digest = canonical_digest(character_authority.to_dict())
    key_digest = sha256_hex(operation_key.encode("utf-8"))
    slot_material = "\0".join((evidence_space_id, authority_digest, memory_id, "correct", key_digest))
    slot = _opaque("smlkey", slot_material)
    operation_id = _opaque("smlop", slot + "\0" + input_digest)
    transition_id = _opaque("smltransition", operation_id)
    intent_id = _opaque("smlintent", operation_id)
    receipt_id = _opaque("smlreceipt", operation_id)
    result_id = _opaque("smlresult", slot)
    return _Identity(slot, operation_id, key_digest, input_digest, transition_id, intent_id, receipt_id, result_id), ()


def _valid_strength(value: object, *, support_state: str | None) -> bool:
    if type(value) is not SubjectiveMemStrength:
        return False
    grounded_max = 1.0 if support_state == "supported" else 0.0
    return (
        type(value.grounded_confidence) in {float, int}
        and 0.0 <= value.grounded_confidence <= grounded_max
        and type(value.subjective_conviction) in {float, int}
        and 0.0 <= value.subjective_conviction <= 1.0
        and value.salience in {"low", "medium", "high"}
        and type(value.reinforcement_count) is int
        and value.reinforcement_count >= 0
        and value.strength_basis in {"assessment_support", "subjective_interpretation"}
    )


def _no_semantic_change(predecessor: SubjectiveMemRevision, proposal: SubjectiveMemCorrectProposal) -> bool:
    return (
        predecessor.grounded_content == proposal.corrected_grounded_content
        and predecessor.subjective_meaning == proposal.corrected_subjective_meaning
        and predecessor.strength.to_dict() == proposal.corrected_strength.to_dict()
        and predecessor.assessment_id == proposal.assessment_revision.assessment_id
        and predecessor.assessment_revision == proposal.assessment_revision.assessment_revision
    )


def _strictly_after(candidate: str, *earlier: str) -> bool:
    try:
        candidate_time = _utc_text(candidate)
        return all(candidate_time > _utc_text(value) for value in earlier)
    except (TypeError, ValueError):
        return False


def _utc_text(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("subjective_mem_lifecycle_time_invalid")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("subjective_mem_lifecycle_time_invalid")
    return parsed.astimezone(timezone.utc)


def _status_for_reasons(reasons: tuple[str, ...]) -> LifecycleStatus:
    if any("idempotency_conflict" in item for item in reasons):
        return "integrity_conflict"
    if any("recovery" in item or "foreign_image" in item for item in reasons):
        return "recovery_required"
    if any("lock_busy" in item for item in reasons):
        return "lock_busy"
    return "fail_closed"


def _result(
    status: LifecycleStatus,
    *,
    identity: _Identity | None = None,
    proposal: SubjectiveMemCorrectProposal | None = None,
    current_state: SubjectiveMemCurrentState | None = None,
    reasons: tuple[str, ...] = (),
    recovery_outcome: str | None = None,
    canonical_published: bool = False,
    receipt_present: bool = False,
    persisted: bool = False,
    post_digest: str | None = None,
) -> SubjectiveMemLifecycleResult:
    return SubjectiveMemLifecycleResult(
        status=status,
        transition_id=identity.transition_id if identity else None,
        receipt_id=identity.receipt_id if identity else None,
        memory_id=proposal.expected_memory_id if proposal else None,
        from_revision=proposal.expected_current_revision if proposal else None,
        to_revision=(proposal.expected_current_revision + 1) if proposal else None,
        current_state=current_state,
        blocked_reasons=tuple(dict.fromkeys(reasons)),
        recovery_outcome=recovery_outcome,
        canonical_markdown_published=canonical_published,
        lifecycle_receipt_present=receipt_present,
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
        return len(value) == 71 and value.startswith("sha256:") and all(ch in "0123456789abcdef" for ch in value[7:])
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("subjective_mem_lifecycle_naive_datetime_forbidden")
    return value.astimezone(timezone.utc)


def _fault(injector: FaultInjector | None, stage: str) -> None:
    if injector is not None:
        injector(stage)


__all__ = [
    "SubjectiveMemLifecycleGate",
    "SubjectiveMemLifecycleResult",
    "correct_subjective_mem",
    "resolve_subjective_mem_lifecycle_gate",
]
