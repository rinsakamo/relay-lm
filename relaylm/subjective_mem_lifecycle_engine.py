"""Operation-neutral Subjective MEM lifecycle publication, replay, and recovery engine.

This module owns the shared execution mechanics required to reserve one singleton
current selector, persist one lifecycle claim and prepared intent, publish one
immutable canonical post-image, invoke one operation-owned deterministic
finalizer, replay one exact finalized operation, and drive caller-invoked forward
recovery.

It never decides operation kind, allowed lifecycle transition, semantic successor
payload, authorization, or reason policy, and never imports a lifecycle operation
owner.  Operation owners supply one immutable execution plan carrying complete
exact authority bindings plus one deterministic finalizer, and map the bounded
content-free outcomes returned here onto their own result surface.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Literal, Mapping

from relaylm._subjective_mem_commit_io import (
    CanonicalPublishResult,
    inspect_canonical_page,
    publish_canonical_page,
    read_immutable_rendered_artifact,
    write_immutable_rendered_artifact,
)
from relaylm.evidence_common import canonical_digest, sha256_hex
from relaylm.evidence_store import EvidenceRecordStore, EvidenceStoreTransaction
from relaylm.subjective_mem import SubjectiveMemCurrentState
from relaylm.subjective_mem_lifecycle import LIFECYCLE_CLAIM_SCHEMA
from relaylm.subjective_mem_markdown import (
    canonical_page_digest,
    parse_subjective_mem_page_bytes,
)

CLAIM_RECORD_KIND = "subjective_mem_lifecycle_claim"
INTENT_RECORD_KIND = "subjective_mem_lifecycle_intent"
INTENT_FINALIZATION_RECORD_KIND = "subjective_mem_lifecycle_intent_finalization"
TRANSITION_RECORD_KIND = "subjective_mem_lifecycle_transition"
RECEIPT_RECORD_KIND = "subjective_mem_lifecycle_receipt"
RESULT_RECORD_KIND = "subjective_mem_lifecycle_idempotency_result"
RECOVERY_RECORD_KIND = "subjective_mem_lifecycle_recovery"
CURRENT_STATE_LOG_KIND = "subjective_mem_current_state"
PROJECTION_LOG_KIND = "subjective_mem_projection_state"
LIFECYCLE_RECOVERY_SCHEMA = "relaylm.subjective_mem_lifecycle_recovery.v1"

LifecycleOutcomeStatus = Literal[
    "reserved", "committed", "duplicate_finalized", "recovery_pending",
    "recovery_required", "lock_busy", "fail_closed", "integrity_conflict",
]
FaultInjector = Callable[[str], None]
_CONFLICT = ("subjective_mem_lifecycle_idempotency_conflict",)
RecordBinding = tuple[str, str, dict[str, object]]
LogBinding = tuple[str, str, tuple[dict[str, object], ...]]
LifecycleReservation = tuple[
    dict[str, object] | None, dict[str, object] | None, dict[str, object] | None, tuple[str, ...]
]


@dataclass(frozen=True)
class LifecycleFinalRecords:
    """Operation-owned durable records for one finalized lifecycle operation."""

    transition: dict[str, object]
    receipt: dict[str, object]
    finalization: dict[str, object]
    result: dict[str, object]
    projection: dict[str, object]


LifecycleFinalizer = Callable[[SubjectiveMemCurrentState], LifecycleFinalRecords | None]
_PLAN_TOKENS = (
    "evidence_space_id", "character_id", "workspace_root", "operation_kind",
    "operation_slot_id", "operation_id", "operation_key_digest", "input_digest",
    "intent_id", "transition_id", "receipt_id", "result_id", "memory_id",
    "to_lifecycle_state", "selector_id", "page_id", "page_partition",
    "page_relative_path", "pre_image_digest", "post_image_digest",
    "predecessor_revision_digest", "successor_revision_digest",
    "successor_block_id", "artifact_id", "prepared_at",
)
_PLAN_INTENT_FIELDS = (
    ("operation_slot_id", "operation_slot_id"),
    ("operation_id", "operation_id"),
    ("operation_kind", "operation_kind"),
    ("operation_key_digest", "operation_key_digest"),
    ("input_digest", "input_digest"),
    ("intent_id", "intent_id"),
    ("transition_id", "transition_id"),
    ("receipt_id", "receipt_id"),
    ("evidence_space_id", "evidence_space_id"),
    ("character_id", "character_id"),
    ("memory_id", "memory_id"),
    ("from_revision", "from_revision"),
    ("to_revision", "to_revision"),
    ("to_lifecycle_state", "to_lifecycle_state"),
    ("current_selector_id", "selector_id"),
    ("page_id", "page_id"),
    ("partition", "page_partition"),
    ("pre_image_state", "pre_image_state"),
    ("pre_image_digest", "pre_image_digest"),
    ("post_image_digest", "post_image_digest"),
    ("predecessor_revision_digest", "predecessor_revision_digest"),
    ("successor_revision_digest", "successor_revision_digest"),
    ("successor_block_id", "successor_block_id"),
    ("artifact_id", "artifact_id"),
    ("prepared_at", "prepared_at"),
)


@dataclass(frozen=True)
class LifecyclePublicationPlan:
    """One immutable, bounded execution plan for a single lifecycle publication."""

    # exact execution authority
    evidence_space_id: str
    character_id: str
    workspace_root: str
    # operation identity
    operation_kind: str
    operation_slot_id: str
    operation_id: str
    operation_key_digest: str
    input_digest: str
    intent_id: str
    transition_id: str
    receipt_id: str
    result_id: str
    # exact logical memory, revisions, and singleton selector reservation
    memory_id: str
    from_revision: int
    to_revision: int
    to_lifecycle_state: str
    selector_id: str
    prepared_state: SubjectiveMemCurrentState
    # exact canonical page identity and pre/post images
    page_id: str
    page_partition: str
    page_relative_path: str
    pre_image_state: str
    pre_image_digest: str
    post_image_digest: str
    predecessor_revision_digest: str
    successor_revision_digest: str
    successor_block_id: str
    artifact_id: str
    # exact durable reservation payload
    prepared_intent: Mapping[str, object]
    prepared_at: str
    record_bindings: tuple[RecordBinding, ...] = ()
    log_bindings: tuple[LogBinding, ...] = ()


@dataclass(frozen=True)
class LifecycleExecutionOutcome:
    """Bounded, content-free result of one engine-owned execution step."""

    status: LifecycleOutcomeStatus
    reasons: tuple[str, ...] = ()
    current_state: SubjectiveMemCurrentState | None = None
    recovery_outcome: str | None = None
    canonical_page_published: bool = False
    lifecycle_receipt_present: bool = False
    persisted: bool = False


def reserve_lifecycle_publication(
    *,
    store: EvidenceRecordStore,
    plan: LifecyclePublicationPlan,
    post_image: bytes,
    observed_current_state: SubjectiveMemCurrentState,
    fault_injector: FaultInjector | None = None,
) -> LifecycleExecutionOutcome:
    """Write the immutable post-image artifact and reserve the singleton selector."""

    reasons = validate_lifecycle_plan(plan)
    if reasons:
        return LifecycleExecutionOutcome("fail_closed", reasons)
    artifact = write_immutable_rendered_artifact(
        workspace_root=plan.workspace_root,
        character_id=plan.character_id,
        artifact_id=plan.artifact_id,
        data=post_image,
    )
    if artifact.status not in {"created", "duplicate_existing"}:
        return LifecycleExecutionOutcome("fail_closed", artifact.reasons)
    try:
        _fault(fault_injector, "after_artifact_before_intent")
    except Exception:
        return LifecycleExecutionOutcome(
            "fail_closed", ("subjective_mem_lifecycle_fault_before_intent",)
        )
    persisted, persist_reasons = _persist_reservation(
        store=store, plan=plan, observed_current_state=observed_current_state
    )
    if not persisted:
        return LifecycleExecutionOutcome("fail_closed", persist_reasons)
    return LifecycleExecutionOutcome("reserved", current_state=plan.prepared_state, persisted=True)


def read_lifecycle_reservation(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    operation_slot_id: str,
    intent_id: str,
    result_id: str,
) -> LifecycleReservation:
    """Read the exact durable claim, prepared intent, and finalized result."""

    try:
        with store.transaction(evidence_space_id) as tx:
            return (
                tx.read_record(record_kind=CLAIM_RECORD_KIND, record_id=operation_slot_id),
                tx.read_record(record_kind=INTENT_RECORD_KIND, record_id=intent_id),
                tx.read_record(record_kind=RESULT_RECORD_KIND, record_id=result_id),
                (),
            )
    except (OSError, RuntimeError, TypeError, ValueError):
        return None, None, None, ("subjective_mem_lifecycle_store_unavailable",)


def read_prepared_post_image(
    *,
    workspace_root: str,
    character_id: str,
    artifact_id: str,
    expected_post_image_digest: str,
) -> tuple[bytes | None, tuple[str, ...]]:
    """Read one immutable rendered post-image artifact at its exact digest."""

    artifact, reasons = read_immutable_rendered_artifact(
        workspace_root=workspace_root,
        character_id=character_id,
        artifact_id=artifact_id,
    )
    if artifact is None:
        return None, reasons or ("subjective_mem_lifecycle_artifact_invalid",)
    if canonical_page_digest(artifact) != expected_post_image_digest:
        return None, ("subjective_mem_lifecycle_artifact_invalid",)
    return artifact, ()


def publish_lifecycle_post_image(
    *,
    store: EvidenceRecordStore,
    plan: LifecyclePublicationPlan,
    post_image: bytes,
    finalizer: LifecycleFinalizer,
    fault_injector: FaultInjector | None = None,
) -> LifecycleExecutionOutcome:
    """Publish the exact post-image and finalize the operation forward-only."""

    reasons = validate_lifecycle_plan(plan)
    if reasons:
        return LifecycleExecutionOutcome("fail_closed", reasons)
    final_state = final_lifecycle_state(plan)
    finalization: dict[str, object] = {}

    def verify(data: bytes) -> bool:
        return _successor_installed_exactly(data, plan=plan)

    def finalize() -> bool:
        try:
            _fault(fault_injector, "after_page_before_receipt")
        except Exception:
            finalization["reasons"] = ("subjective_mem_lifecycle_fault_before_receipt",)
            return False
        ok, duplicate, finalize_reasons = _finalize_locked(
            store=store, plan=plan, finalizer=finalizer, final_state=final_state
        )
        finalization.update({"ok": ok, "duplicate": duplicate, "reasons": finalize_reasons})
        return ok

    def validate_pre_image() -> bool:
        return _pre_image_authority_current(store=store, plan=plan)

    publish = publish_canonical_page(
        workspace_root=plan.workspace_root,
        character_id=plan.character_id,
        relative_path=plan.page_relative_path,
        expected_pre_state="present",
        expected_pre_digest=plan.pre_image_digest,
        post_image=post_image,
        expected_post_digest=plan.post_image_digest,
        verify_installed=verify,
        finalize_installed=finalize,
        validate_pre_image=validate_pre_image,
        fault_injector=fault_injector,
    )
    return _publication_outcome(
        publish=publish,
        plan=plan,
        finalization=finalization,
        final_state=final_state,
        store=store,
        finalizer=finalizer,
    )


def _publication_outcome(
    *,
    publish: CanonicalPublishResult,
    plan: LifecyclePublicationPlan,
    finalization: dict[str, object],
    final_state: SubjectiveMemCurrentState,
    store: EvidenceRecordStore,
    finalizer: LifecycleFinalizer,
) -> LifecycleExecutionOutcome:
    if publish.status == "lock_busy":
        return LifecycleExecutionOutcome("lock_busy", publish.reasons, persisted=True)
    if publish.status == "pre_image_conflict":
        _fence_recovery_required(store=store, plan=plan)
        return LifecycleExecutionOutcome(
            "recovery_required",
            publish.reasons,
            current_state=recovery_lifecycle_state(plan),
            recovery_outcome="foreign_image",
            persisted=True,
        )
    if publish.status == "failed":
        page_present = publish.installed_digest == plan.post_image_digest
        return LifecycleExecutionOutcome(
            "recovery_pending",
            tuple(finalization.get("reasons", publish.reasons)),
            current_state=plan.prepared_state,
            recovery_outcome=(
                "post_image_pending_receipt"
                if page_present
                else "pre_image_pending_publication"
            ),
            canonical_page_published=page_present,
            persisted=True,
        )
    if not finalization.get("ok"):
        # An already-post-image retry can arrive after the prior finalizer
        # committed.  Resolve the exact durable result instead of guessing.
        replay = resolve_finalized_replay(store=store, plan=plan, finalizer=finalizer)
        if replay is not None:
            return replay
        default = ("subjective_mem_lifecycle_receipt_finalization_failed",)
        return LifecycleExecutionOutcome(
            "recovery_pending",
            tuple(finalization.get("reasons", default)),
            current_state=plan.prepared_state,
            recovery_outcome="post_image_pending_receipt",
            canonical_page_published=True,
            persisted=True,
        )
    return LifecycleExecutionOutcome(
        "duplicate_finalized" if finalization.get("duplicate") else "committed",
        current_state=final_state,
        recovery_outcome=(
            "post_image_rolled_forward"
            if publish.status == "already_post_image"
            else "published_and_finalized"
        ),
        canonical_page_published=True,
        lifecycle_receipt_present=True,
        persisted=True,
    )


def resolve_finalized_replay(
    *,
    store: EvidenceRecordStore,
    plan: LifecyclePublicationPlan,
    finalizer: LifecycleFinalizer,
) -> LifecycleExecutionOutcome | None:
    """Resolve one exact finalized operation without producing another revision."""

    reasons = validate_lifecycle_plan(plan)
    if reasons:
        return LifecycleExecutionOutcome("fail_closed", reasons)
    final_state = final_lifecycle_state(plan)
    try:
        with store.transaction(plan.evidence_space_id) as tx:
            result = tx.read_record(
                record_kind=RESULT_RECORD_KIND, record_id=plan.result_id
            )
            if result is None:
                claim = tx.read_record(
                    record_kind=CLAIM_RECORD_KIND, record_id=plan.operation_slot_id
                )
                if claim is not None and claim.get("input_digest") != plan.input_digest:
                    return LifecycleExecutionOutcome("integrity_conflict", _CONFLICT)
                return None
            if result.get("input_digest") != plan.input_digest:
                return LifecycleExecutionOutcome("integrity_conflict", _CONFLICT)
            records = finalizer(final_state)
            if (
                records is None
                or not _reservation_unchanged_locked(tx=tx, plan=plan)
                or result != records.result
                or not _final_records_exact_locked(
                    tx=tx, plan=plan, records=records, final_state=final_state
                )
            ):
                return LifecycleExecutionOutcome(
                    "fail_closed", ("subjective_mem_lifecycle_final_result_incomplete",)
                )
            duplicate_selector = _duplicate_logical_selector_locked(
                tx=tx, plan=plan, expected=final_state
            )
            if duplicate_selector:
                return LifecycleExecutionOutcome(
                    "fail_closed",
                    duplicate_selector,
                    current_state=final_state,
                    lifecycle_receipt_present=True,
                    persisted=True,
                )
    except (OSError, RuntimeError, TypeError, ValueError):
        return LifecycleExecutionOutcome(
            "fail_closed", ("subjective_mem_lifecycle_store_unavailable",)
        )

    inspected = inspect_canonical_page(
        workspace_root=plan.workspace_root,
        character_id=plan.character_id,
        relative_path=plan.page_relative_path,
    )
    if (
        inspected.snapshot is None
        or inspected.snapshot.data is None
        or inspected.snapshot.digest != plan.post_image_digest
    ):
        return _replay_page_failure(
            final_state, "subjective_mem_lifecycle_receipt_without_exact_page"
        )
    if not _successor_installed_exactly(inspected.snapshot.data, plan=plan):
        return _replay_page_failure(
            final_state, "subjective_mem_lifecycle_final_page_invalid"
        )
    return LifecycleExecutionOutcome(
        "duplicate_finalized",
        current_state=final_state,
        recovery_outcome="exact_replay",
        canonical_page_published=True,
        lifecycle_receipt_present=True,
        persisted=True,
    )


def _replay_page_failure(
    final_state: SubjectiveMemCurrentState, reason: str
) -> LifecycleExecutionOutcome:
    return LifecycleExecutionOutcome(
        "fail_closed",
        (reason,),
        current_state=final_state,
        lifecycle_receipt_present=True,
        persisted=True,
    )


def final_lifecycle_state(plan: LifecyclePublicationPlan) -> SubjectiveMemCurrentState:
    """Reconstruct the finalized, Retrieval-eligible selector state from the plan."""

    return replace(
        plan.prepared_state,
        current_revision=plan.to_revision,
        lifecycle_state=plan.to_lifecycle_state,
        mutation_state="none",
        retrieval_eligible=True,
        block_id=plan.successor_block_id,
        canonical_page_digest=plan.post_image_digest,
        authorization_kind="lifecycle_transition",
        authorization_id=plan.transition_id,
        current_receipt_id=plan.receipt_id,
    )


def recovery_lifecycle_state(plan: LifecyclePublicationPlan) -> SubjectiveMemCurrentState:
    """Reconstruct the fenced recovery-required selector state from the plan."""

    return replace(plan.prepared_state, mutation_state="recovery_required")


def validate_lifecycle_plan(plan: LifecyclePublicationPlan) -> tuple[str, ...]:
    """Revalidate one immutable execution plan at the engine boundary."""

    if type(plan) is not LifecyclePublicationPlan:
        return ("subjective_mem_lifecycle_plan_invalid",)
    intent, prepared = plan.prepared_intent, plan.prepared_state
    if (
        any(type(getattr(plan, name)) is not str or not getattr(plan, name) for name in _PLAN_TOKENS)
        or plan.pre_image_state != "present"
        or type(plan.from_revision) is not int
        or type(plan.to_revision) is not int
        or plan.from_revision < 1
        or plan.to_revision <= plan.from_revision
        or type(prepared) is not SubjectiveMemCurrentState
        or not isinstance(intent, Mapping)
    ):
        return ("subjective_mem_lifecycle_plan_invalid",)
    if (
        prepared.memory_state_id != plan.selector_id
        or prepared.memory_id != plan.memory_id
        or prepared.character_id != plan.character_id
        or prepared.current_revision != plan.from_revision
        or prepared.mutation_state != "prepared"
        or prepared.retrieval_eligible is not False
        or prepared.page_id != plan.page_id
        or prepared.canonical_page_digest != plan.pre_image_digest
        or prepared.updated_at != plan.prepared_at
    ):
        return ("subjective_mem_lifecycle_plan_selector_not_exact",)
    if (
        any(intent.get(key) != getattr(plan, name) for key, name in _PLAN_INTENT_FIELDS)
        or intent.get("prepared_current_state_digest")
        != canonical_digest(prepared.to_dict())
    ):
        return ("subjective_mem_lifecycle_plan_intent_not_exact",)
    if any(
        len(binding) != 3 or not isinstance(binding[2], dict) or not binding[2]
        for binding in plan.record_bindings
    ) or any(
        len(binding) != 3 or not isinstance(binding[2], tuple)
        for binding in plan.log_bindings
    ):
        return ("subjective_mem_lifecycle_plan_binding_invalid",)
    return ()


def _persist_reservation(
    *,
    store: EvidenceRecordStore,
    plan: LifecyclePublicationPlan,
    observed_current_state: SubjectiveMemCurrentState,
) -> tuple[bool, tuple[str, ...]]:
    claim = lifecycle_claim_record(plan)
    expected = observed_current_state.to_dict()
    try:
        with store.transaction(plan.evidence_space_id) as tx:
            existing_result = tx.read_record(
                record_kind=RESULT_RECORD_KIND, record_id=plan.result_id
            )
            if existing_result is not None:
                return False, ("subjective_mem_lifecycle_result_already_exists",)
            existing_claim = tx.read_record(
                record_kind=CLAIM_RECORD_KIND, record_id=plan.operation_slot_id
            )
            if existing_claim is not None:
                if existing_claim == claim:
                    return True, ()
                if existing_claim.get("input_digest") != plan.input_digest:
                    return False, ("subjective_mem_lifecycle_idempotency_conflict",)
                return False, ("subjective_mem_lifecycle_claim_conflict",)
            if tx.read_log(log_kind=CURRENT_STATE_LOG_KIND, key=plan.selector_id) != [
                expected
            ]:
                return False, ("subjective_mem_lifecycle_current_selector_changed",)
            duplicate_selector = _duplicate_logical_selector_locked(
                tx=tx, plan=plan, expected=observed_current_state
            )
            if duplicate_selector:
                return False, duplicate_selector
            commit = tx.commit(
                transaction_id=_opaque("smlpreparetx", plan.operation_id),
                records=(
                    (CLAIM_RECORD_KIND, plan.operation_slot_id, claim),
                    (INTENT_RECORD_KIND, plan.intent_id, dict(plan.prepared_intent)),
                ),
                logs=(
                    (
                        CURRENT_STATE_LOG_KIND,
                        plan.selector_id,
                        (plan.prepared_state.to_dict(),),
                    ),
                ),
            )
            if commit.status == "collision":
                return False, ("subjective_mem_lifecycle_prepare_collision",)
            if commit.status not in {"created", "duplicate_existing"}:
                return False, commit.reasons or ("subjective_mem_lifecycle_prepare_failed",)
            return True, ()
    except (OSError, RuntimeError, TypeError, ValueError):
        return False, ("subjective_mem_lifecycle_store_unavailable",)


def _finalize_locked(
    *,
    store: EvidenceRecordStore,
    plan: LifecyclePublicationPlan,
    finalizer: LifecycleFinalizer,
    final_state: SubjectiveMemCurrentState,
) -> tuple[bool, bool, tuple[str, ...]]:
    records = finalizer(final_state)
    if records is None:
        return False, False, ("subjective_mem_lifecycle_intent_corrupt",)
    try:
        with store.transaction(plan.evidence_space_id) as tx:
            if _final_records_exact_locked(
                tx=tx, plan=plan, records=records, final_state=final_state
            ):
                return True, True, ()
            if _any_final_record_present_locked(tx=tx, plan=plan):
                return False, False, (
                    "subjective_mem_lifecycle_partial_finalization_conflict",
                )
            claim = tx.read_record(
                record_kind=CLAIM_RECORD_KIND, record_id=plan.operation_slot_id
            )
            stored_intent = tx.read_record(
                record_kind=INTENT_RECORD_KIND, record_id=plan.intent_id
            )
            if (
                not isinstance(claim, dict)
                or claim.get("input_digest") != plan.input_digest
                or stored_intent != dict(plan.prepared_intent)
            ):
                return False, False, ("subjective_mem_lifecycle_claim_or_intent_changed",)
            if tx.read_log(log_kind=CURRENT_STATE_LOG_KIND, key=plan.selector_id) != [
                plan.prepared_state.to_dict()
            ]:
                return False, False, ("subjective_mem_lifecycle_current_selector_changed",)
            commit_records, commit_logs = _final_commit_payload(
                plan, records, final_state
            )
            commit = tx.commit(
                transaction_id=_opaque("smlfinaltx", plan.operation_id),
                records=commit_records,
                logs=commit_logs,
            )
            if commit.status == "collision":
                return False, False, ("subjective_mem_lifecycle_finalization_collision",)
            if commit.status not in {"created", "duplicate_existing"}:
                return False, False, commit.reasons or (
                    "subjective_mem_lifecycle_finalization_failed",
                )
            return True, commit.status == "duplicate_existing", ()
    except (OSError, RuntimeError, TypeError, ValueError):
        return False, False, ("subjective_mem_lifecycle_store_unavailable",)


def _pre_image_authority_current(
    *, store: EvidenceRecordStore, plan: LifecyclePublicationPlan
) -> bool:
    try:
        with store.transaction(plan.evidence_space_id) as tx:
            if tx.read_log(log_kind=CURRENT_STATE_LOG_KIND, key=plan.selector_id) != [
                plan.prepared_state.to_dict()
            ]:
                return False
            if not _reservation_unchanged_locked(tx=tx, plan=plan):
                return False
            for record_kind, record_id, body in plan.record_bindings:
                if tx.read_record(record_kind=record_kind, record_id=record_id) != body:
                    return False
            for log_kind, key, events in plan.log_bindings:
                if tx.read_log(log_kind=log_kind, key=key) != list(events):
                    return False
            return True
    except (OSError, RuntimeError, TypeError, ValueError):
        return False


def _fence_recovery_required(
    *, store: EvidenceRecordStore, plan: LifecyclePublicationPlan
) -> None:
    recovery = recovery_lifecycle_state(plan)
    try:
        with store.transaction(plan.evidence_space_id) as tx:
            if tx.read_log(log_kind=CURRENT_STATE_LOG_KIND, key=plan.selector_id) != [
                plan.prepared_state.to_dict()
            ]:
                return
            recovery_record = {
                "schema": LIFECYCLE_RECOVERY_SCHEMA,
                "recovery_id": _opaque("smlrecovery", plan.operation_id),
                "operation_id": plan.operation_id,
                "intent_id": plan.intent_id,
                "memory_id": recovery.memory_id,
                "memory_revision": recovery.current_revision,
                "recovery_state": "recovery_required",
                "reason_id": "foreign_or_ambiguous_canonical_image",
                "recorded_at": recovery.updated_at,
                "content_free": True,
            }
            tx.commit(
                transaction_id=_opaque("smlrecoverytx", plan.operation_id),
                records=(
                    (
                        RECOVERY_RECORD_KIND,
                        str(recovery_record["recovery_id"]),
                        recovery_record,
                    ),
                ),
                logs=(
                    (CURRENT_STATE_LOG_KIND, plan.selector_id, (recovery.to_dict(),)),
                ),
            )
    except (OSError, RuntimeError, TypeError, ValueError):
        return


def _reservation_unchanged_locked(
    *, tx: EvidenceStoreTransaction, plan: LifecyclePublicationPlan
) -> bool:
    claim = tx.read_record(
        record_kind=CLAIM_RECORD_KIND, record_id=plan.operation_slot_id
    )
    stored_intent = tx.read_record(
        record_kind=INTENT_RECORD_KIND, record_id=plan.intent_id
    )
    return claim == lifecycle_claim_record(plan) and stored_intent == dict(plan.prepared_intent)


def _final_commit_payload(
    plan: LifecyclePublicationPlan,
    records: LifecycleFinalRecords,
    final_state: SubjectiveMemCurrentState,
) -> tuple[tuple[RecordBinding, ...], tuple[LogBinding, ...]]:
    return (
        (
            (TRANSITION_RECORD_KIND, plan.transition_id, records.transition),
            (RECEIPT_RECORD_KIND, plan.receipt_id, records.receipt),
            (
                INTENT_FINALIZATION_RECORD_KIND,
                str(records.finalization["finalization_id"]),
                records.finalization,
            ),
            (RESULT_RECORD_KIND, plan.result_id, records.result),
        ),
        (
            (CURRENT_STATE_LOG_KIND, plan.selector_id, (final_state.to_dict(),)),
            (PROJECTION_LOG_KIND, plan.selector_id, (records.projection,)),
        ),
    )


def _final_records_exact_locked(
    *,
    tx: EvidenceStoreTransaction,
    plan: LifecyclePublicationPlan,
    records: LifecycleFinalRecords,
    final_state: SubjectiveMemCurrentState,
) -> bool:
    commit_records, commit_logs = _final_commit_payload(plan, records, final_state)
    return all(
        tx.read_record(record_kind=kind, record_id=record_id) == body
        for kind, record_id, body in commit_records
    ) and all(
        tx.read_log(log_kind=kind, key=key) == list(events)
        for kind, key, events in commit_logs
    )


def _any_final_record_present_locked(
    *, tx: EvidenceStoreTransaction, plan: LifecyclePublicationPlan
) -> bool:
    return any(
        item is not None
        for item in (
            tx.read_record(
                record_kind=TRANSITION_RECORD_KIND, record_id=plan.transition_id
            ),
            tx.read_record(record_kind=RECEIPT_RECORD_KIND, record_id=plan.receipt_id),
            tx.read_record(record_kind=RESULT_RECORD_KIND, record_id=plan.result_id),
        )
    )


def _duplicate_logical_selector_locked(
    *,
    tx: EvidenceStoreTransaction,
    plan: LifecyclePublicationPlan,
    expected: SubjectiveMemCurrentState,
) -> tuple[str, ...]:
    raw = expected.to_dict()
    matches = [
        (key, events)
        for key, events in tx.list_logs(log_kind=CURRENT_STATE_LOG_KIND, limit=4096)
        if any(
            item.get("character_id") == expected.character_id
            and item.get("memory_id") == expected.memory_id
            for item in events
        )
    ]
    if len(matches) != 1 or matches[0] != (plan.selector_id, [raw]):
        return ("subjective_mem_lifecycle_duplicate_logical_current_selector",)
    return ()


def _successor_installed_exactly(
    data: bytes, *, plan: LifecyclePublicationPlan
) -> bool:
    page, reasons = parse_subjective_mem_page_bytes(
        data,
        expected_page_id=plan.page_id,
        expected_character_id=plan.character_id,
        expected_partition=plan.page_partition,  # type: ignore[arg-type]
    )
    if page is None or reasons:
        return False
    successors = [
        item
        for item in page.blocks
        if item.revision.memory_id == plan.memory_id
        and item.revision.memory_revision == plan.to_revision
        and canonical_digest(item.revision.to_dict()) == plan.successor_revision_digest
        and item.block_id == plan.successor_block_id
    ]
    predecessors = [
        item
        for item in page.blocks
        if item.revision.memory_id == plan.memory_id
        and item.revision.memory_revision == plan.from_revision
        and canonical_digest(item.revision.to_dict()) == plan.predecessor_revision_digest
    ]
    return len(successors) == 1 and len(predecessors) == 1


def lifecycle_claim_record(plan: LifecyclePublicationPlan) -> dict[str, object]:
    """Derive the canonical lifecycle claim reserved for one execution plan."""

    return {
        "schema": LIFECYCLE_CLAIM_SCHEMA,
        "operation_slot_id": plan.operation_slot_id,
        "operation_id": plan.operation_id,
        "operation_kind": plan.operation_kind,
        "operation_key_digest": plan.operation_key_digest,
        "input_digest": plan.input_digest,
        "intent_digest": canonical_digest(dict(plan.prepared_intent)),
        "evidence_space_id": plan.evidence_space_id,
        "character_id": plan.character_id,
        "memory_id": plan.memory_id,
        "from_revision": plan.from_revision,
        "to_revision": plan.to_revision,
        "intent_id": plan.intent_id,
        "claimed_at": plan.prepared_at,
    }


def _opaque(prefix: str, value: str) -> str:
    return f"{prefix}_{sha256_hex(value.encode('utf-8'))}"


def _fault(injector: FaultInjector | None, stage: str) -> None:
    if injector is not None:
        injector(stage)


__all__ = [
    "LifecycleExecutionOutcome",
    "LifecycleFinalRecords",
    "LifecycleFinalizer",
    "LifecyclePublicationPlan",
    "final_lifecycle_state",
    "lifecycle_claim_record",
    "publish_lifecycle_post_image",
    "read_lifecycle_reservation",
    "read_prepared_post_image",
    "recovery_lifecycle_state",
    "reserve_lifecycle_publication",
    "resolve_finalized_replay",
    "validate_lifecycle_plan",
]
