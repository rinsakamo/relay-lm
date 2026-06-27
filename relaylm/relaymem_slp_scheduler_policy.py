"""O1D2 deterministic scheduler policy, fairness, retry, and pacing hints.

This module wraps the existing O1D1 one-round coordinator with a content-free
policy boundary. It never discovers lane work itself, never sleeps, never loops,
and never supervises a service.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Final, Literal

from .config import RelayLMConfig
from .relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from .relaymem_slp_scheduler_contract import LaneOutcome, SchedulerRoundResult

POLICY_RESULT_SCHEMA: Final = "relaylm.local_scheduler_policy_round_result.v0"
POLICY_PROJECTION_SCHEMA: Final = "relaylm.local_scheduler_policy_projection.v0"
MAX_POLICY_REASON_IDS: Final = 16
MAX_POLICY_COUNTER: Final = 1_000_000
MAX_POLICY_DELAY_MS: Final = 60_000

_REASON_RE: Final = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_PROGRESS_STATUSES: Final = frozenset(
    {"completed", "already_complete", "dry_run_ready", "executed", "retry_released", "terminal"}
)
_NO_WORK_STATUSES: Final = frozenset(
    {
        "no_eligible_work",
        "future_retry_only",
        "busy",
        "not_replayable",
        "cleanup_required",
        "dependency_unavailable",
        "failed",
        "unsafe_state",
        "isolated",
    }
)

RetryWindow = Literal["none", "immediate", "short", "later", "unknown"]
PacingRecommendation = Literal["stop", "run_next_round", "wait_before_next_round", "idle"]
FairnessLanePreference = Literal["replay", "queue", "balanced", "none"]
PolicyStatus = Literal[
    "policy_disabled",
    "invalid_input",
    "invalid_configuration",
    "policy_evaluated",
    "policy_blocked",
    "round_unsafe",
    "unexpected_failure",
]

FaultInjector = Callable[[str], None]


@dataclass(frozen=True)
class SchedulerPolicyState:
    """Content-free bounded counters carried by an external caller between invocations."""

    replay_progress_streak: int = 0
    queue_progress_streak: int = 0
    replay_idle_streak: int = 0
    queue_idle_streak: int = 0
    consecutive_contention_count: int = 0
    consecutive_future_retry_count: int = 0
    consecutive_no_work_count: int = 0

    def __post_init__(self) -> None:
        for name in _STATE_COUNTER_NAMES:
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= MAX_POLICY_COUNTER:
                raise ValueError("scheduler_policy_state_counter_invalid")

    def projection(self) -> Mapping[str, object]:
        return {name: getattr(self, name) for name in _STATE_COUNTER_NAMES}

    def advance(self, result: SchedulerRoundResult) -> "SchedulerPolicyState":
        if type(result) is not SchedulerRoundResult:
            raise TypeError("exact_scheduler_round_result_required")
        replay = result.replay_lane
        queue = result.queue_lane
        replay_progress = _lane_progressed(replay)
        queue_progress = _lane_progressed(queue)
        replay_idle = _lane_idle(replay)
        queue_idle = _lane_idle(queue)
        contention = any(
            bool(lane and (lane.contention_observed or lane.status == "busy"))
            for lane in (replay, queue)
        )
        future_retry = bool(result.future_work_hint_present)
        lanes = tuple(lane for lane in (replay, queue) if type(lane) is LaneOutcome)
        no_work = bool(
            lanes
            and not replay_progress
            and not queue_progress
            and all(lane.no_immediate_work or lane.status in _NO_WORK_STATUSES for lane in lanes)
        )
        return SchedulerPolicyState(
            replay_progress_streak=_next_counter(self.replay_progress_streak, replay_progress),
            queue_progress_streak=_next_counter(self.queue_progress_streak, queue_progress),
            replay_idle_streak=_next_counter(self.replay_idle_streak, replay_idle),
            queue_idle_streak=_next_counter(self.queue_idle_streak, queue_idle),
            consecutive_contention_count=_next_counter(
                self.consecutive_contention_count, contention
            ),
            consecutive_future_retry_count=_next_counter(
                self.consecutive_future_retry_count, future_retry
            ),
            consecutive_no_work_count=_next_counter(self.consecutive_no_work_count, no_work),
        )


_STATE_COUNTER_NAMES: Final = (
    "replay_progress_streak",
    "queue_progress_streak",
    "replay_idle_streak",
    "queue_idle_streak",
    "consecutive_contention_count",
    "consecutive_future_retry_count",
    "consecutive_no_work_count",
)


@dataclass(frozen=True)
class SchedulerPolicyRoundResult:
    status: PolicyStatus
    round_result: SchedulerRoundResult | None = field(default=None, repr=False, compare=False)
    policy_state: SchedulerPolicyState = field(default_factory=SchedulerPolicyState)
    next_policy_state: SchedulerPolicyState = field(default_factory=SchedulerPolicyState)
    pacing_recommendation: PacingRecommendation = "stop"
    next_delay_ms: int | None = None
    retry_window: RetryWindow = "none"
    fairness_lane_preference: FairnessLanePreference = "none"
    unsafe: bool = False
    bounded_reason_ids: tuple[str, ...] = ()
    schema_version: str = field(default=POLICY_RESULT_SCHEMA, init=False)

    def __post_init__(self) -> None:
        if self.status not in {
            "policy_disabled",
            "invalid_input",
            "invalid_configuration",
            "policy_evaluated",
            "policy_blocked",
            "round_unsafe",
            "unexpected_failure",
        }:
            raise ValueError("unknown_scheduler_policy_status")
        if self.round_result is not None and type(self.round_result) is not SchedulerRoundResult:
            raise TypeError("exact_scheduler_round_result_required")
        if type(self.policy_state) is not SchedulerPolicyState:
            raise TypeError("exact_scheduler_policy_state_required")
        if type(self.next_policy_state) is not SchedulerPolicyState:
            raise TypeError("exact_next_scheduler_policy_state_required")
        if self.pacing_recommendation not in {
            "stop",
            "run_next_round",
            "wait_before_next_round",
            "idle",
        }:
            raise ValueError("scheduler_policy_pacing_invalid")
        if self.retry_window not in {"none", "immediate", "short", "later", "unknown"}:
            raise ValueError("scheduler_policy_retry_window_invalid")
        if self.fairness_lane_preference not in {"replay", "queue", "balanced", "none"}:
            raise ValueError("scheduler_policy_fairness_preference_invalid")
        if self.next_delay_ms is not None and (
            type(self.next_delay_ms) is not int or not 0 <= self.next_delay_ms <= MAX_POLICY_DELAY_MS
        ):
            raise ValueError("scheduler_policy_delay_invalid")
        if type(self.unsafe) is not bool:
            raise TypeError("scheduler_policy_unsafe_invalid")
        object.__setattr__(
            self,
            "bounded_reason_ids",
            _reason_ids(self.bounded_reason_ids, maximum=MAX_POLICY_REASON_IDS),
        )
        if self.pacing_recommendation != "wait_before_next_round" and self.next_delay_ms is not None:
            raise ValueError("scheduler_policy_delay_requires_wait")

    def projection(self) -> Mapping[str, object]:
        round_result = self.round_result
        return {
            "schema_version": POLICY_PROJECTION_SCHEMA,
            "status": self.status,
            "round_status": round_result.status if round_result is not None else "not_invoked",
            "pacing_recommendation": self.pacing_recommendation,
            "next_delay_ms": self.next_delay_ms,
            "retry_window": self.retry_window,
            "fairness_lane_preference": self.fairness_lane_preference,
            "unsafe": self.unsafe,
            "bounded_reason_ids": list(self.bounded_reason_ids),
            "policy_state": dict(self.next_policy_state.projection()),
        }


def run_relaymem_slp_scheduler_round_once_with_policy(
    *,
    config: RelayLMConfig,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None = None,
    now: datetime | None = None,
    policy_state: SchedulerPolicyState | None = None,
    fault_injector: FaultInjector | None = None,
) -> SchedulerPolicyRoundResult:
    """Run one O1D1 round through the O1D2 policy wrapper and return immediately."""

    if type(config) is not RelayLMConfig:
        return _policy_result(status="invalid_input", reasons=("exact_relaylm_config_required",), unsafe=True)
    if registry is not None and type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        return _policy_result(status="invalid_input", reasons=("exact_source_registry_required",), unsafe=True)
    if now is not None and not _valid_now(now):
        return _policy_result(status="invalid_input", reasons=("scheduler_policy_now_invalid",), unsafe=True)
    if policy_state is not None and type(policy_state) is not SchedulerPolicyState:
        return _policy_result(status="invalid_input", reasons=("exact_scheduler_policy_state_required",), unsafe=True)
    if fault_injector is not None and not callable(fault_injector):
        return _policy_result(status="invalid_input", reasons=("scheduler_policy_fault_injector_invalid",), unsafe=True)

    exact_state = SchedulerPolicyState() if policy_state is None else policy_state
    policy_mode, config_reasons = validate_scheduler_policy_config(config)
    if config_reasons:
        return _policy_result(
            status="invalid_configuration",
            state=exact_state,
            reasons=config_reasons,
            unsafe=False,
        )
    if policy_mode == "disabled":
        return _policy_result(
            status="policy_disabled",
            state=exact_state,
            reasons=("scheduler_policy_disabled",),
            unsafe=False,
        )

    try:
        _fault(fault_injector, "after_policy_validation_before_round")
    except Exception:
        return _policy_result(
            status="unexpected_failure",
            state=exact_state,
            reasons=("scheduler_policy_fault_before_round",),
            unsafe=True,
        )

    try:
        from .relaymem_slp_scheduler_round import run_relaymem_slp_scheduler_round_once

        round_result = run_relaymem_slp_scheduler_round_once(
            config=config,
            registry=registry,
            now=now,
            fault_injector=fault_injector,
        )
    except Exception:
        return _policy_result(
            status="unexpected_failure",
            state=exact_state,
            reasons=("scheduler_policy_round_failed",),
            unsafe=True,
        )
    if type(round_result) is not SchedulerRoundResult:
        return _policy_result(
            status="unexpected_failure",
            state=exact_state,
            reasons=("scheduler_policy_round_result_invalid",),
            unsafe=True,
        )

    try:
        _fault(fault_injector, "after_round_before_policy")
    except Exception:
        return _policy_result(
            status="unexpected_failure",
            state=exact_state,
            round_result=round_result,
            reasons=("scheduler_policy_fault_before_projection",),
            unsafe=True,
        )

    policy_result = apply_scheduler_round_policy(
        config=config,
        round_result=round_result,
        now=now,
        policy_state=exact_state,
    )

    try:
        _fault(fault_injector, "after_policy_before_return")
    except Exception:
        return _policy_result(
            status="unexpected_failure",
            state=exact_state,
            round_result=round_result,
            reasons=("scheduler_policy_fault_before_return",),
            unsafe=True,
        )
    return policy_result


def validate_scheduler_policy_config(config: RelayLMConfig) -> tuple[str, tuple[str, ...]]:
    """Return policy mode and bounded invalid-configuration reason IDs."""

    bool_fields = (
        "relaymem_local_scheduler_policy_enabled",
        "relaymem_local_scheduler_policy_dry_run_only",
        "relaymem_local_scheduler_policy_apply_enabled",
    )
    for name in bool_fields:
        if type(getattr(config, name, None)) is not bool:
            return "invalid", ("scheduler_policy_gate_must_be_bool",)

    triple = tuple(getattr(config, name) for name in bool_fields)
    if triple == (False, True, False):
        mode = "disabled"
    elif triple == (True, True, False):
        mode = "dry_run"
    elif triple == (True, False, True):
        mode = "apply"
    else:
        return "invalid", ("invalid_scheduler_policy_gate_combination",)

    numeric_bounds = {
        "relaymem_local_scheduler_policy_fairness_streak_limit": (1, 100),
        "relaymem_local_scheduler_pacing_base_delay_ms": (0, MAX_POLICY_DELAY_MS),
        "relaymem_local_scheduler_pacing_max_delay_ms": (0, MAX_POLICY_DELAY_MS),
        "relaymem_local_scheduler_pacing_jitter_ms": (0, MAX_POLICY_DELAY_MS),
        "relaymem_local_scheduler_policy_short_retry_window_ms": (1, 3_600_000),
        "relaymem_local_scheduler_policy_later_retry_window_ms": (1, 86_400_000),
    }
    values: dict[str, int] = {}
    for name, (lower, upper) in numeric_bounds.items():
        value = getattr(config, name, None)
        if type(value) is not int or not lower <= value <= upper:
            return "invalid", ("scheduler_policy_numeric_bound_invalid",)
        values[name] = value

    if values["relaymem_local_scheduler_pacing_base_delay_ms"] > values[
        "relaymem_local_scheduler_pacing_max_delay_ms"
    ]:
        return "invalid", ("scheduler_policy_base_delay_exceeds_max",)
    if values["relaymem_local_scheduler_pacing_jitter_ms"] > values[
        "relaymem_local_scheduler_pacing_max_delay_ms"
    ]:
        return "invalid", ("scheduler_policy_jitter_exceeds_max",)
    if values["relaymem_local_scheduler_policy_short_retry_window_ms"] > values[
        "relaymem_local_scheduler_policy_later_retry_window_ms"
    ]:
        return "invalid", ("scheduler_policy_retry_windows_inverted",)
    return mode, ()


def apply_scheduler_round_policy(
    *,
    config: RelayLMConfig,
    round_result: SchedulerRoundResult,
    now: datetime | None,
    policy_state: SchedulerPolicyState,
) -> SchedulerPolicyRoundResult:
    """Convert one content-free O1D1 result to a bounded O1D2 policy projection."""

    if type(config) is not RelayLMConfig or type(round_result) is not SchedulerRoundResult:
        return _policy_result(status="invalid_input", reasons=("scheduler_policy_input_invalid",), unsafe=True)
    if type(policy_state) is not SchedulerPolicyState:
        return _policy_result(status="invalid_input", reasons=("exact_scheduler_policy_state_required",), unsafe=True)
    _, config_reasons = validate_scheduler_policy_config(config)
    if config_reasons:
        return _policy_result(
            status="invalid_configuration",
            state=policy_state,
            round_result=None,
            reasons=config_reasons,
            unsafe=False,
        )

    next_state = policy_state.advance(round_result)
    retry_window = _retry_window(config=config, round_result=round_result, now=now)
    fairness = _fairness_preference(config=config, state=next_state)
    pacing, delay, pacing_reason = _pacing(
        config=config,
        round_result=round_result,
        retry_window=retry_window,
        state=next_state,
    )
    if round_result.unsafe:
        status: PolicyStatus = "round_unsafe"
    elif round_result.status in {"disabled", "invalid_configuration", "invalid_input", "blocked"}:
        status = "policy_blocked"
    else:
        status = "policy_evaluated"
    reasons = _reason_ids(
        tuple(round_result.bounded_reason_ids) + (pacing_reason,),
        maximum=MAX_POLICY_REASON_IDS,
    )
    return SchedulerPolicyRoundResult(
        status=status,
        round_result=round_result,
        policy_state=policy_state,
        next_policy_state=next_state,
        pacing_recommendation=pacing,
        next_delay_ms=delay,
        retry_window=retry_window,
        fairness_lane_preference=fairness,
        unsafe=bool(round_result.unsafe),
        bounded_reason_ids=reasons,
    )


def _pacing(
    *,
    config: RelayLMConfig,
    round_result: SchedulerRoundResult,
    retry_window: RetryWindow,
    state: SchedulerPolicyState,
) -> tuple[PacingRecommendation, int | None, str]:
    if round_result.status in {"disabled", "invalid_input", "invalid_configuration"}:
        return "stop", None, "round_not_runnable"
    if round_result.unsafe:
        return "stop", None, "round_unsafe"
    if round_result.immediate_next_round_recommended:
        return "run_next_round", None, "round_progress"
    if retry_window == "immediate":
        return "run_next_round", None, "retry_window_immediate"
    if state.consecutive_contention_count > 0:
        return (
            "wait_before_next_round",
            _bounded_delay_ms(config, state.consecutive_contention_count, "contention"),
            "contention_pacing",
        )
    if retry_window in {"short", "later", "unknown"}:
        return (
            "wait_before_next_round",
            _bounded_delay_ms(config, state.consecutive_future_retry_count, "future_retry"),
            "future_retry_pacing",
        )
    if round_result.retryable:
        return (
            "wait_before_next_round",
            _bounded_delay_ms(config, 1, "retryable_idle"),
            "retryable_idle_pacing",
        )
    if state.consecutive_no_work_count >= 2:
        return (
            "wait_before_next_round",
            _bounded_delay_ms(config, state.consecutive_no_work_count, "no_work"),
            "no_work_pacing",
        )
    return "idle", None, "no_immediate_work"


def _retry_window(
    *,
    config: RelayLMConfig,
    round_result: SchedulerRoundResult,
    now: datetime | None,
) -> RetryWindow:
    if not round_result.future_work_hint_present:
        return "none"
    queue = round_result.queue_lane
    if queue is None or queue.status != "future_retry_only":
        return "unknown"
    retry_at = getattr(queue.private_delegate_result, "earliest_retry_not_before", None)
    if type(retry_at) is not datetime or not _valid_now(retry_at) or not _valid_now(now):
        return "unknown"
    delta_ms = int((retry_at - now).total_seconds() * 1000)
    if delta_ms <= 0:
        return "immediate"
    if delta_ms <= config.relaymem_local_scheduler_policy_short_retry_window_ms:
        return "short"
    return "later"


def _fairness_preference(
    *,
    config: RelayLMConfig,
    state: SchedulerPolicyState,
) -> FairnessLanePreference:
    limit = config.relaymem_local_scheduler_policy_fairness_streak_limit
    if state.replay_progress_streak >= limit and state.queue_progress_streak < limit:
        return "queue"
    if state.queue_progress_streak >= limit and state.replay_progress_streak < limit:
        return "replay"
    if state.replay_idle_streak >= limit and state.queue_idle_streak < limit:
        return "queue"
    if state.queue_idle_streak >= limit and state.replay_idle_streak < limit:
        return "replay"
    if any(getattr(state, name) for name in _STATE_COUNTER_NAMES):
        return "balanced"
    return "none"


def _bounded_delay_ms(config: RelayLMConfig, streak: int, reason: str) -> int:
    base = config.relaymem_local_scheduler_pacing_base_delay_ms
    max_delay = config.relaymem_local_scheduler_pacing_max_delay_ms
    jitter_max = config.relaymem_local_scheduler_pacing_jitter_ms
    bounded_streak = min(max(1, streak), 7)
    raw = min(max_delay, base * (2 ** (bounded_streak - 1)))
    jitter = _deterministic_jitter_ms(jitter_max, streak=bounded_streak, reason=reason)
    return min(max_delay, raw + jitter)


def _deterministic_jitter_ms(max_jitter_ms: int, *, streak: int, reason: str) -> int:
    if max_jitter_ms <= 0:
        return 0
    seed = streak * 131 + sum(ord(char) for char in reason)
    return seed % (max_jitter_ms + 1)


def _lane_progressed(lane: LaneOutcome | None) -> bool:
    return bool(
        type(lane) is LaneOutcome
        and (lane.mutation_may_have_occurred or lane.status in _PROGRESS_STATUSES)
    )


def _lane_idle(lane: LaneOutcome | None) -> bool:
    return bool(
        type(lane) is LaneOutcome
        and lane.attempted
        and not _lane_progressed(lane)
        and (lane.no_immediate_work or lane.status in _NO_WORK_STATUSES)
    )


def _next_counter(value: int, condition: bool) -> int:
    return min(value + 1, MAX_POLICY_COUNTER) if condition else 0


def _valid_now(value: object) -> bool:
    return bool(
        type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None
    )


def _fault(fault_injector: FaultInjector | None, seam: str) -> None:
    if fault_injector is not None:
        fault_injector(seam)


def _reason_ids(values: Sequence[str], *, maximum: int) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        values = ("scheduler_policy_reason_invalid",)
    output: list[str] = []
    for value in values:
        reason = (
            value
            if type(value) is str and _REASON_RE.fullmatch(value)
            else "scheduler_policy_reason_invalid"
        )
        if reason not in output:
            output.append(reason)
        if len(output) >= maximum:
            break
    if not output:
        output.append("scheduler_policy_status")
    return tuple(output)


def _policy_result(
    *,
    status: PolicyStatus,
    reasons: Sequence[str],
    state: SchedulerPolicyState | None = None,
    round_result: SchedulerRoundResult | None = None,
    unsafe: bool,
) -> SchedulerPolicyRoundResult:
    exact_state = SchedulerPolicyState() if state is None else state
    return SchedulerPolicyRoundResult(
        status=status,
        round_result=round_result,
        policy_state=exact_state,
        next_policy_state=exact_state,
        pacing_recommendation="stop",
        next_delay_ms=None,
        retry_window="none",
        fairness_lane_preference="none",
        unsafe=unsafe,
        bounded_reason_ids=_reason_ids(reasons, maximum=MAX_POLICY_REASON_IDS),
    )


__all__ = [
    "POLICY_PROJECTION_SCHEMA",
    "POLICY_RESULT_SCHEMA",
    "SchedulerPolicyRoundResult",
    "SchedulerPolicyState",
    "apply_scheduler_round_policy",
    "run_relaymem_slp_scheduler_round_once_with_policy",
    "validate_scheduler_policy_config",
]
