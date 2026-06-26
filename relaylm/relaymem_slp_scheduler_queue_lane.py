"""O1C bounded eligible B2/B3 queue-lane adapter.

One call performs at most one secure bounded queue discovery and at most one
delegation to the existing Phase 6-C2 adapter. It does not poll, sleep,
recover stale claims, or start another scheduler round.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Callable

from .config import RelayLMConfig
from .relaymem_slp_one_queued_job_runner import (
    RelayMEMSLPOneQueuedJobRunnerResult,
    execute_one_queued_relaymem_slp_primary_job,
)
from .relaymem_slp_queue_candidate import (
    FaultInjector,
    build_relaymem_slp_one_queued_job_request,
    canonical_reread_relaymem_slp_queue_candidate,
    discover_relaymem_slp_queue_candidate,
    resolve_relaymem_slp_queue_character_scope,
    validate_configured_roots,
    validate_local_worker_mode,
)
from .relaymem_slp_scheduler_contract import LaneOutcome, SchedulerGates

_REASON_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_MAX_REASONS = 8


@dataclass(frozen=True, repr=False)
class QueueLanePrivateState:
    """Runtime-private hints omitted from repr, equality, and projection."""

    delegate_result: RelayMEMSLPOneQueuedJobRunnerResult | None = field(
        default=None, repr=False, compare=False
    )
    earliest_retry_not_before: datetime | None = field(
        default=None, repr=False, compare=False
    )
    character_scope_resolved: bool = field(default=False, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            "QueueLanePrivateState("
            "delegate_result_omitted=True, retry_timestamp_omitted=True, "
            f"character_scope_resolved={self.character_scope_resolved!r})"
        )


def run_relaymem_slp_scheduler_queue_lane_once(
    *,
    config: RelayLMConfig,
    gates: SchedulerGates,
    now: datetime | None = None,
    fault_injector: Callable[[str], None] | None = None,
) -> LaneOutcome:
    """Run one O1C queue-lane opportunity and return one bounded LaneOutcome."""

    if type(gates) is not SchedulerGates:
        return _lane(
            status="failed",
            enabled=False,
            attempted=False,
            no_immediate_work=True,
            reasons=("exact_scheduler_gates_required",),
        )
    lane_enabled = bool(gates.enabled and gates.queue_lane_enabled)
    gate_reasons = gates.validation_reason_ids()
    if gate_reasons:
        return _lane(
            status="failed",
            enabled=lane_enabled,
            attempted=False,
            no_immediate_work=True,
            unsafe="required_dependency_unavailable" in gate_reasons,
            reasons=gate_reasons,
        )
    if gates.mode == "disabled":
        return _lane(
            status="failed",
            enabled=False,
            attempted=False,
            no_immediate_work=True,
            reasons=("scheduler_disabled",),
        )
    if not gates.queue_lane_enabled:
        return _lane(
            status="failed",
            enabled=False,
            attempted=False,
            no_immediate_work=True,
            reasons=("queue_lane_disabled",),
        )
    if type(config) is not RelayLMConfig:
        return _lane(
            status="failed",
            enabled=True,
            attempted=False,
            no_immediate_work=True,
            reasons=("exact_relaylm_config_required",),
        )

    lower_mode, lower_reasons = validate_local_worker_mode(config)
    if lower_reasons:
        return _lane(
            status="failed",
            enabled=True,
            attempted=False,
            no_immediate_work=True,
            reasons=lower_reasons,
        )
    if lower_mode == "disabled":
        return _lane(
            status="failed",
            enabled=True,
            attempted=False,
            no_immediate_work=True,
            reasons=("local_worker_disabled",),
        )
    assert lower_mode in {"dry_run", "apply"}
    effective_mode = (
        "apply" if gates.mode == "apply" and lower_mode == "apply" else "dry_run"
    )

    roots, root_reasons = validate_configured_roots(config)
    if roots is None:
        return _lane(
            status="unsafe_state",
            enabled=True,
            attempted=True,
            no_immediate_work=True,
            unsafe=True,
            reasons=root_reasons,
        )
    queue_root, protected_source_root, configured_store_root = roots

    exact_now = datetime.now(timezone.utc) if now is None else now
    if (
        type(exact_now) is not datetime
        or exact_now.tzinfo is None
        or exact_now.utcoffset() is None
    ):
        return _lane(
            status="failed",
            enabled=True,
            attempted=False,
            no_immediate_work=True,
            reasons=("queue_lane_now_invalid",),
        )

    try:
        discovery = discover_relaymem_slp_queue_candidate(
            queue_root,
            now=exact_now,
            max_entries=config.relaymem_local_worker_discovery_max_entries,
            fault_injector=fault_injector,
        )
    except Exception:
        return _lane(
            status="failed",
            enabled=True,
            attempted=True,
            no_immediate_work=True,
            reasons=("queue_lane_discovery_failed",),
        )

    private_state = QueueLanePrivateState(
        earliest_retry_not_before=discovery.earliest_retry_not_before
    )
    if discovery.status == "unsafe":
        return _lane(
            status="unsafe_state",
            enabled=True,
            attempted=True,
            candidate_observed=discovery.candidate_observed,
            no_immediate_work=True,
            future_work_hint_present=discovery.future_work_hint_present,
            unsafe=True,
            reasons=discovery.reason_ids or ("queue_inventory_unsafe",),
            private=private_state,
        )
    if discovery.status == "busy":
        return _lane(
            status="busy",
            enabled=True,
            attempted=True,
            no_immediate_work=True,
            contention_observed=True,
            reasons=discovery.reason_ids or ("queue_lock_busy",),
            private=private_state,
        )
    if discovery.status == "future_retry_only":
        return _lane(
            status="future_retry_only",
            enabled=True,
            attempted=True,
            candidate_observed=discovery.candidate_observed,
            no_immediate_work=True,
            future_work_hint_present=True,
            reasons=("future_retry_only",),
            private=private_state,
        )
    if discovery.status == "no_work":
        return _lane(
            status="no_eligible_work",
            enabled=True,
            attempted=True,
            candidate_observed=discovery.candidate_observed,
            no_immediate_work=True,
            reasons=("no_eligible_queue_work",),
            private=private_state,
        )
    candidate = discovery.candidate
    if candidate is None:
        return _lane(
            status="unsafe_state",
            enabled=True,
            attempted=True,
            candidate_observed=True,
            no_immediate_work=True,
            unsafe=True,
            reasons=("selected_candidate_missing",),
        )

    try:
        _fault(fault_injector, "after_selection_before_reread")
        current, reread_status, reread_reasons = (
            canonical_reread_relaymem_slp_queue_candidate(
                queue_root,
                candidate,
                now=exact_now,
                fault_injector=fault_injector,
            )
        )
    except Exception:
        return _lane(
            status="failed",
            enabled=True,
            attempted=True,
            candidate_observed=True,
            candidate_selected=True,
            no_immediate_work=True,
            reasons=("queue_lane_reread_failed",),
            private=private_state,
        )
    if current is None:
        unsafe = reread_status == "unsafe"
        return _lane(
            status="unsafe_state" if unsafe else "candidate_changed",
            enabled=True,
            attempted=True,
            candidate_observed=True,
            candidate_selected=True,
            canonical_reread_performed=True,
            no_immediate_work=unsafe,
            unsafe=unsafe,
            retryable=not unsafe,
            reasons=reread_reasons
            or (
                "queue_candidate_reread_unsafe"
                if unsafe
                else "queue_candidate_changed",
            ),
            private=private_state,
        )

    try:
        _fault(fault_injector, "after_reread_before_scope_resolution")
        character_id, store_root, scope_reasons = (
            resolve_relaymem_slp_queue_character_scope(
                config,
                namespace=current.record.get("namespace"),
                explicit_character_id=None,
                configured_store_root=configured_store_root,
            )
        )
    except Exception:
        character_id = None
        store_root = None
        scope_reasons = ("queue_character_scope_resolution_failed",)
    if character_id is None or store_root is None:
        return _lane(
            status="failed",
            enabled=True,
            attempted=True,
            candidate_observed=True,
            candidate_selected=True,
            canonical_reread_performed=True,
            no_immediate_work=True,
            reasons=scope_reasons or ("queue_character_scope_unavailable",),
            private=private_state,
        )

    private_state = QueueLanePrivateState(
        earliest_retry_not_before=discovery.earliest_retry_not_before,
        character_scope_resolved=True,
    )
    try:
        _fault(fault_injector, "after_scope_resolution_before_request_build")
        c2_request = build_relaymem_slp_one_queued_job_request(
            config=config,
            queued_record=dict(current.record),
            character_id=character_id,
            queue_root=queue_root,
            protected_source_root=protected_source_root,
            store_root=store_root,
            mode=effective_mode,
        )
        _fault(fault_injector, "after_request_build_before_c2")
    except Exception:
        return _lane(
            status="failed",
            enabled=True,
            attempted=True,
            candidate_observed=True,
            candidate_selected=True,
            canonical_reread_performed=True,
            no_immediate_work=True,
            reasons=("queue_c2_request_invalid",),
            private=private_state,
        )

    try:
        c2_result = execute_one_queued_relaymem_slp_primary_job(c2_request)
        _fault(fault_injector, "after_c2_before_lane_mapping")
    except Exception:
        return _lane(
            status="failed",
            enabled=True,
            attempted=True,
            candidate_observed=True,
            candidate_selected=True,
            canonical_reread_performed=True,
            delegation_attempted=True,
            mutation_may_have_occurred=True,
            no_immediate_work=True,
            retryable=True,
            reasons=("queue_c2_delegation_failed",),
            private=private_state,
        )

    private_state = QueueLanePrivateState(
        delegate_result=c2_result,
        earliest_retry_not_before=discovery.earliest_retry_not_before,
        character_scope_resolved=True,
    )
    return _map_c2_result(c2_result, private_state)


def _map_c2_result(
    result: RelayMEMSLPOneQueuedJobRunnerResult,
    private: QueueLanePrivateState,
) -> LaneOutcome:
    mutation = bool(
        result.claim_performed
        or result.worker_invoked
        or result.queue_transition_performed
        or result.terminal
        or result.cleanup_required
    )
    common = dict(
        enabled=True,
        attempted=True,
        candidate_observed=True,
        candidate_selected=True,
        canonical_reread_performed=True,
        delegation_attempted=True,
        delegation_completed=True,
        mutation_may_have_occurred=mutation,
        terminal_for_candidate=bool(result.terminal),
        private=private,
    )
    reasons = result.reason_ids

    if result.status == "dry_run_ready":
        return _lane(
            status="dry_run_ready",
            no_immediate_work=False,
            reasons=reasons or ("queue_dry_run_ready",),
            **common,
        )
    if result.cleanup_required or result.status == "cleanup_required":
        return _lane(
            status="cleanup_required",
            no_immediate_work=True,
            retryable=True,
            reasons=reasons or ("queue_cleanup_required",),
            **common,
        )
    if result.terminal:
        return _lane(
            status="terminal",
            no_immediate_work=False,
            reasons=reasons or ("queue_candidate_terminal",),
            **common,
        )
    if result.retryable or result.worker_status == "retry_released":
        return _lane(
            status="retry_released",
            no_immediate_work=False,
            retryable=True,
            reasons=reasons or ("queue_retry_released",),
            **common,
        )
    if result.status == "worker_completed" and result.worker_invoked:
        return _lane(
            status="executed",
            no_immediate_work=False,
            reasons=reasons or ("queue_worker_executed",),
            **common,
        )
    if result.status in {"claim_not_applied", "claim_lost_before_rehydrate"}:
        return _lane(
            status="candidate_changed",
            no_immediate_work=False,
            retryable=True,
            reasons=reasons or ("queue_claim_conflict",),
            **common,
        )
    if result.status == "source_blocked":
        return _lane(
            status="unsafe_state",
            no_immediate_work=True,
            unsafe=True,
            reasons=reasons or ("queue_source_blocked",),
            **common,
        )
    if result.status == "source_retryable":
        return _lane(
            status="failed",
            no_immediate_work=True,
            retryable=True,
            reasons=reasons or ("queue_source_retryable",),
            **common,
        )
    return _lane(
        status="failed",
        no_immediate_work=True,
        retryable=bool(result.retryable),
        reasons=reasons or ("queue_delegate_failed",),
        **common,
    )


def _fault(fault_injector: FaultInjector | None, seam: str) -> None:
    if fault_injector is not None:
        fault_injector(seam)


def _lane(
    *,
    status: str,
    enabled: bool,
    attempted: bool,
    candidate_observed: bool = False,
    candidate_selected: bool = False,
    canonical_reread_performed: bool = False,
    delegation_attempted: bool = False,
    delegation_completed: bool = False,
    mutation_may_have_occurred: bool = False,
    no_immediate_work: bool,
    future_work_hint_present: bool = False,
    contention_observed: bool = False,
    retryable: bool = False,
    unsafe: bool = False,
    terminal_for_candidate: bool = False,
    reasons: object = (),
    private: QueueLanePrivateState | None = None,
) -> LaneOutcome:
    return LaneOutcome(
        lane_kind="queue",
        status=status,  # type: ignore[arg-type]
        enabled=enabled,
        attempted=attempted,
        candidate_observed=candidate_observed,
        candidate_selected=candidate_selected,
        canonical_reread_performed=canonical_reread_performed,
        delegation_attempted=delegation_attempted,
        delegation_completed=delegation_completed,
        mutation_may_have_occurred=mutation_may_have_occurred,
        no_immediate_work=no_immediate_work,
        future_work_hint_present=future_work_hint_present,
        contention_observed=contention_observed,
        retryable=retryable,
        unsafe=unsafe,
        terminal_for_candidate=terminal_for_candidate,
        bounded_reason_ids=_reason_ids(reasons),
        private_delegate_result=private,
    )


def _reason_ids(values: object) -> tuple[str, ...]:
    output: list[str] = []
    try:
        iterator = iter(values)  # type: ignore[arg-type]
    except TypeError:
        iterator = iter(("queue_lane_reason_invalid",))
    for value in iterator:
        reason = (
            value
            if type(value) is str and _REASON_RE.fullmatch(value)
            else "queue_lane_reason_invalid"
        )
        if reason not in output:
            output.append(reason)
        if len(output) >= _MAX_REASONS:
            break
    if not output:
        output.append("queue_lane_status")
    return tuple(output)


__all__ = [
    "QueueLanePrivateState",
    "run_relaymem_slp_scheduler_queue_lane_once",
]
