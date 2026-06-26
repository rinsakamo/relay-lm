"""O1D1 accepted scheduler gates and one replay-before-queue round.

The coordinator validates one exact server-owned ``RelayLMConfig``, invokes each
accepted lane at most once in fixed replay-then-queue order, delegates all lane
semantics to O1B/O1C, aggregates with the pure O1A contract, validates the
content-free projection, and returns without polling or sleeping.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
import re
from typing import Final

from .config import RelayLMConfig
from .relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from .relaymem_slp_scheduler_contract import (
    MAX_ROUND_REASON_IDS,
    QUEUE_LANE_STATUSES,
    REPLAY_LANE_STATUSES,
    ROUND_PROJECTION_SCHEMA,
    LaneOutcome,
    SchedulerGates,
    SchedulerRoundResult,
    aggregate_scheduler_round,
)
from .relaymem_slp_scheduler_queue_lane import (
    run_relaymem_slp_scheduler_queue_lane_once,
)
from .relaymem_slp_scheduler_replay_lane import (
    run_relaymem_slp_scheduler_replay_lane_once,
)

FaultInjector = Callable[[str], None]

_REASON_RE: Final = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_PROJECTION_KEYS: Final = frozenset(
    {
        "schema_version",
        "status",
        "disposition",
        "replay_lane_enabled",
        "replay_lane_attempted",
        "replay_lane_status",
        "replay_candidate_selected",
        "replay_delegated",
        "replay_completed",
        "queue_lane_enabled",
        "queue_lane_attempted",
        "queue_lane_status",
        "queue_candidate_selected",
        "queue_delegated",
        "queue_completed",
        "work_units_attempted",
        "work_units_completed",
        "idle_recommended",
        "immediate_next_round_recommended",
        "future_work_hint_present",
        "retryable",
        "unsafe",
        "bounded_reason_ids",
    }
)
_BOOL_PROJECTION_KEYS: Final = frozenset(
    {
        "replay_lane_enabled",
        "replay_lane_attempted",
        "replay_candidate_selected",
        "replay_delegated",
        "replay_completed",
        "queue_lane_enabled",
        "queue_lane_attempted",
        "queue_candidate_selected",
        "queue_delegated",
        "queue_completed",
        "idle_recommended",
        "immediate_next_round_recommended",
        "future_work_hint_present",
        "retryable",
        "unsafe",
    }
)
_ROUND_STATUSES: Final = frozenset(
    {
        "disabled",
        "invalid_input",
        "invalid_configuration",
        "round_completed",
        "partial_progress",
        "idle",
        "blocked",
        "unsafe_state",
        "unexpected_failure",
    }
)
_DISPOSITIONS: Final = frozenset({"stop", "run_next_round", "idle"})


def build_relaymem_slp_scheduler_gates(config: RelayLMConfig) -> SchedulerGates:
    """Build exact O1A gates from accepted server-owned configuration."""

    if type(config) is not RelayLMConfig:
        raise TypeError("exact_relaylm_config_required")
    names = (
        "relaymem_local_scheduler_enabled",
        "relaymem_local_scheduler_dry_run_only",
        "relaymem_local_scheduler_apply_enabled",
        "relaymem_local_scheduler_replay_lane_enabled",
        "relaymem_local_scheduler_queue_lane_enabled",
    )
    values: dict[str, bool] = {}
    for name in names:
        value = getattr(config, name, None)
        if type(value) is not bool:
            raise TypeError("scheduler_gate_must_be_exact_bool")
        values[name] = value

    replay_enabled = values["relaymem_local_scheduler_replay_lane_enabled"]
    queue_enabled = values["relaymem_local_scheduler_queue_lane_enabled"]
    required_dependency_available = bool(
        (not replay_enabled or callable(run_relaymem_slp_scheduler_replay_lane_once))
        and (not queue_enabled or callable(run_relaymem_slp_scheduler_queue_lane_once))
    )
    return SchedulerGates(
        enabled=values["relaymem_local_scheduler_enabled"],
        dry_run_only=values["relaymem_local_scheduler_dry_run_only"],
        apply_enabled=values["relaymem_local_scheduler_apply_enabled"],
        replay_lane_enabled=replay_enabled,
        queue_lane_enabled=queue_enabled,
        required_dependency_available=required_dependency_available,
        supported_schema=True,
    )


def run_relaymem_slp_scheduler_round_once(
    *,
    config: RelayLMConfig,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None = None,
    now: datetime | None = None,
    fault_injector: FaultInjector | None = None,
) -> SchedulerRoundResult:
    """Run one sequential production scheduler round and return immediately."""

    if type(config) is not RelayLMConfig:
        return _invalid_input_result("exact_relaylm_config_required")
    if registry is not None and type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        return _invalid_input_result("exact_source_registry_required")
    if now is not None and not _valid_now(now):
        return _invalid_input_result("scheduler_now_invalid")
    if fault_injector is not None and not callable(fault_injector):
        return _invalid_input_result("scheduler_fault_injector_invalid")

    try:
        gates = build_relaymem_slp_scheduler_gates(config)
    except (AttributeError, TypeError, ValueError):
        return _invalid_configuration_result("scheduler_config_schema_invalid")

    gate_reasons = gates.validation_reason_ids()
    if gate_reasons or gates.mode == "disabled":
        result = aggregate_scheduler_round(
            gates=gates,
            invocation_order=(),
            replay_lane=None,
            queue_lane=None,
        )
        return _return_validated(result)

    replay_lane: LaneOutcome | None = None
    queue_lane: LaneOutcome | None = None
    invocation_order: list[str] = []

    try:
        _fault(fault_injector, "after_gate_validation_before_replay")
    except Exception:
        return _unexpected_failure_result(
            replay_lane=None,
            queue_lane=None,
            reason_id="scheduler_fault_before_replay",
        )

    if gates.replay_lane_enabled:
        try:
            replay_lane = run_relaymem_slp_scheduler_replay_lane_once(
                config=config,
                gates=gates,
                registry=registry,
                fault_injector=fault_injector,
            )
        except Exception:
            return _unexpected_failure_result(
                replay_lane=None,
                queue_lane=None,
                reason_id="replay_lane_unexpected_failure",
            )
        if not _valid_lane_result(replay_lane, "replay"):
            return _unexpected_failure_result(
                replay_lane=None,
                queue_lane=None,
                reason_id="replay_lane_result_invalid",
            )
        invocation_order.append("replay")

    if gates.queue_lane_enabled:
        try:
            _fault(fault_injector, "after_replay_before_queue")
        except Exception:
            return _unexpected_failure_result(
                replay_lane=replay_lane,
                queue_lane=None,
                reason_id="scheduler_fault_before_queue",
            )
        try:
            queue_lane = run_relaymem_slp_scheduler_queue_lane_once(
                config=config,
                gates=gates,
                now=now,
                fault_injector=fault_injector,
            )
        except Exception:
            return _unexpected_failure_result(
                replay_lane=replay_lane,
                queue_lane=None,
                reason_id="queue_lane_unexpected_failure",
            )
        if not _valid_lane_result(queue_lane, "queue"):
            return _unexpected_failure_result(
                replay_lane=replay_lane,
                queue_lane=None,
                reason_id="queue_lane_result_invalid",
            )
        invocation_order.append("queue")
        try:
            _fault(fault_injector, "after_queue_before_aggregation")
        except Exception:
            return _unexpected_failure_result(
                replay_lane=replay_lane,
                queue_lane=queue_lane,
                reason_id="scheduler_fault_before_aggregation",
            )

    try:
        result = aggregate_scheduler_round(
            gates=gates,
            invocation_order=tuple(invocation_order),
            replay_lane=replay_lane,
            queue_lane=queue_lane,
        )
    except Exception:
        return _unexpected_failure_result(
            replay_lane=replay_lane,
            queue_lane=queue_lane,
            reason_id="scheduler_aggregation_failed",
        )

    try:
        _fault(fault_injector, "after_aggregation_before_projection")
    except Exception:
        return _unexpected_failure_result(
            replay_lane=replay_lane,
            queue_lane=queue_lane,
            reason_id="scheduler_fault_before_projection",
        )

    try:
        projection = result.projection()
        _validate_round_projection(result, projection)
    except Exception:
        return _unexpected_failure_result(
            replay_lane=replay_lane,
            queue_lane=queue_lane,
            reason_id="scheduler_projection_invalid",
        )

    try:
        _fault(fault_injector, "after_projection_before_return")
    except Exception:
        return _unexpected_failure_result(
            replay_lane=replay_lane,
            queue_lane=queue_lane,
            reason_id="scheduler_fault_before_return",
        )
    return result


def _valid_now(value: object) -> bool:
    return bool(
        type(value) is datetime
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def _fault(fault_injector: FaultInjector | None, stage: str) -> None:
    if fault_injector is not None:
        fault_injector(stage)


def _valid_lane_result(value: object, lane_kind: str) -> bool:
    if type(value) is not LaneOutcome or value.lane_kind != lane_kind:
        return False
    allowed = REPLAY_LANE_STATUSES if lane_kind == "replay" else QUEUE_LANE_STATUSES
    return type(value.status) is str and value.status in allowed


def _invalid_input_result(reason_id: str) -> SchedulerRoundResult:
    return SchedulerRoundResult(
        status="invalid_input",
        disposition="stop",
        replay_lane=None,
        queue_lane=None,
        work_units_attempted=0,
        work_units_completed=0,
        idle_recommended=False,
        immediate_next_round_recommended=False,
        future_work_hint_present=False,
        retryable=False,
        unsafe=True,
        bounded_reason_ids=(reason_id,),
    )


def _invalid_configuration_result(reason_id: str) -> SchedulerRoundResult:
    return SchedulerRoundResult(
        status="invalid_configuration",
        disposition="stop",
        replay_lane=None,
        queue_lane=None,
        work_units_attempted=0,
        work_units_completed=0,
        idle_recommended=False,
        immediate_next_round_recommended=False,
        future_work_hint_present=False,
        retryable=False,
        unsafe=False,
        bounded_reason_ids=(reason_id,),
    )


def _unexpected_failure_result(
    *,
    replay_lane: LaneOutcome | None,
    queue_lane: LaneOutcome | None,
    reason_id: str,
) -> SchedulerRoundResult:
    lanes: Sequence[LaneOutcome] = tuple(
        lane for lane in (replay_lane, queue_lane) if type(lane) is LaneOutcome
    )
    attempted = sum(1 for lane in lanes if lane.delegation_attempted)
    completed = sum(1 for lane in lanes if lane.delegation_completed)
    return SchedulerRoundResult(
        status="unexpected_failure",
        disposition="stop",
        replay_lane=replay_lane if type(replay_lane) is LaneOutcome else None,
        queue_lane=queue_lane if type(queue_lane) is LaneOutcome else None,
        work_units_attempted=attempted,
        work_units_completed=completed,
        idle_recommended=False,
        immediate_next_round_recommended=False,
        future_work_hint_present=any(lane.future_work_hint_present for lane in lanes),
        retryable=False,
        unsafe=True,
        bounded_reason_ids=(reason_id,),
    )


def _return_validated(result: SchedulerRoundResult) -> SchedulerRoundResult:
    try:
        _validate_round_projection(result, result.projection())
    except Exception:
        return _unexpected_failure_result(
            replay_lane=result.replay_lane,
            queue_lane=result.queue_lane,
            reason_id="scheduler_projection_invalid",
        )
    return result


def _validate_round_projection(
    result: SchedulerRoundResult,
    projection: Mapping[str, object],
) -> None:
    if type(result) is not SchedulerRoundResult:
        raise TypeError("exact_scheduler_round_result_required")
    if type(projection) is not dict or frozenset(projection) != _PROJECTION_KEYS:
        raise ValueError("scheduler_projection_shape_invalid")
    if projection.get("schema_version") != ROUND_PROJECTION_SCHEMA:
        raise ValueError("scheduler_projection_schema_invalid")
    if projection.get("status") not in _ROUND_STATUSES:
        raise ValueError("scheduler_projection_status_invalid")
    if projection.get("disposition") not in _DISPOSITIONS:
        raise ValueError("scheduler_projection_disposition_invalid")
    if projection.get("replay_lane_status") not in REPLAY_LANE_STATUSES | {"not_invoked"}:
        raise ValueError("scheduler_projection_replay_status_invalid")
    if projection.get("queue_lane_status") not in QUEUE_LANE_STATUSES | {"not_invoked"}:
        raise ValueError("scheduler_projection_queue_status_invalid")
    for key in _BOOL_PROJECTION_KEYS:
        if type(projection.get(key)) is not bool:
            raise TypeError("scheduler_projection_bool_invalid")
    attempted = projection.get("work_units_attempted")
    completed = projection.get("work_units_completed")
    if type(attempted) is not int or not 0 <= attempted <= 2:
        raise ValueError("scheduler_projection_attempted_invalid")
    if type(completed) is not int or not 0 <= completed <= attempted:
        raise ValueError("scheduler_projection_completed_invalid")
    reasons = projection.get("bounded_reason_ids")
    if type(reasons) is not list or len(reasons) > MAX_ROUND_REASON_IDS:
        raise ValueError("scheduler_projection_reasons_invalid")
    if len(set(reasons)) != len(reasons):
        raise ValueError("scheduler_projection_reasons_invalid")
    if any(type(reason) is not str or _REASON_RE.fullmatch(reason) is None for reason in reasons):
        raise ValueError("scheduler_projection_reasons_invalid")

    replay = result.replay_lane
    queue = result.queue_lane
    expected = {
        "schema_version": ROUND_PROJECTION_SCHEMA,
        "status": result.status,
        "disposition": result.disposition,
        "replay_lane_enabled": bool(replay and replay.enabled),
        "replay_lane_attempted": bool(replay and replay.attempted),
        "replay_lane_status": replay.status if replay else "not_invoked",
        "replay_candidate_selected": bool(replay and replay.candidate_selected),
        "replay_delegated": bool(replay and replay.delegation_attempted),
        "replay_completed": bool(replay and replay.delegation_completed),
        "queue_lane_enabled": bool(queue and queue.enabled),
        "queue_lane_attempted": bool(queue and queue.attempted),
        "queue_lane_status": queue.status if queue else "not_invoked",
        "queue_candidate_selected": bool(queue and queue.candidate_selected),
        "queue_delegated": bool(queue and queue.delegation_attempted),
        "queue_completed": bool(queue and queue.delegation_completed),
        "work_units_attempted": result.work_units_attempted,
        "work_units_completed": result.work_units_completed,
        "idle_recommended": result.idle_recommended,
        "immediate_next_round_recommended": result.immediate_next_round_recommended,
        "future_work_hint_present": result.future_work_hint_present,
        "retryable": result.retryable,
        "unsafe": result.unsafe,
        "bounded_reason_ids": list(result.bounded_reason_ids),
    }
    if projection != expected:
        raise ValueError("scheduler_projection_result_mismatch")
