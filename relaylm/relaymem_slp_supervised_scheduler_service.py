"""O2 supervised RelayMEM SLP scheduler service.

This module is an opt-in service loop around the O1E operational controls
boundary. It does not own queue mutation, worker execution, stale recovery, or
memory finalization authority; each iteration delegates to
run_relaymem_slp_scheduler_operational_controls_once.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
import re
import time
from typing import Final, Literal

from .config import RelayLMConfig
from .relaymem_slp_primary_worker_source_registry import RelayMEMSLPPrimaryWorkerSourceRegistry
from .relaymem_slp_scheduler_operations import (
    SchedulerCancellationToken,
    SchedulerOperationalControlsResult,
    SchedulerSignalCancellationAdapter,
    run_relaymem_slp_scheduler_operational_controls_once,
)
from .relaymem_slp_scheduler_policy import SchedulerPolicyState

O2_SUPERVISED_SERVICE_RESULT_SCHEMA: Final = "relaylm.o2_supervised_scheduler_service_result.v0"
O2_SUPERVISED_SERVICE_PROJECTION_SCHEMA: Final = "relaylm.o2_supervised_scheduler_service_projection.v0"

MAX_O2_REASON_IDS: Final = 16
MAX_O2_ROUNDS: Final = 1_000_000
MAX_O2_SLEEP_MS: Final = 60_000
MAX_O2_SLEEP_COUNT: Final = 1_000_000
MAX_O2_TOTAL_SLEEP_MS: Final = 3_600_000_000
_REASON_RE: Final = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

CancellationProbe = Callable[[], bool]
Sleeper = Callable[[float], None]
OperationalRunner = Callable[..., SchedulerOperationalControlsResult]

ServiceStatus = Literal[
    "disabled",
    "completed",
    "idle",
    "cancelled",
    "shutdown_requested",
    "unsafe_state",
    "invalid_input",
    "invalid_config",
    "unexpected_failure",
]


@dataclass(frozen=True)
class RelayMEMSLPSupervisedSchedulerServiceSettings:
    """Bounded opt-in O2 service-loop settings."""

    max_rounds: int | None = 1
    stop_after_idle_rounds: int = 1
    idle_sleep_ms: int = 1000
    max_sleep_ms: int = 60_000
    install_signal_handlers: bool = False

    def __post_init__(self) -> None:
        if self.max_rounds is not None and (
            type(self.max_rounds) is not int or not 1 <= self.max_rounds <= MAX_O2_ROUNDS
        ):
            raise ValueError("o2_service_max_rounds_invalid")
        for name in ("stop_after_idle_rounds", "idle_sleep_ms", "max_sleep_ms"):
            value = getattr(self, name)
            if type(value) is not int:
                raise TypeError("o2_service_setting_int_required")
        if not 1 <= self.stop_after_idle_rounds <= MAX_O2_ROUNDS:
            raise ValueError("o2_service_stop_after_idle_rounds_invalid")
        if not 0 <= self.idle_sleep_ms <= MAX_O2_SLEEP_MS:
            raise ValueError("o2_service_idle_sleep_ms_invalid")
        if not 0 <= self.max_sleep_ms <= MAX_O2_SLEEP_MS:
            raise ValueError("o2_service_max_sleep_ms_invalid")
        if type(self.install_signal_handlers) is not bool:
            raise TypeError("o2_service_install_signal_handlers_bool_required")


@dataclass(frozen=True, repr=False)
class RelayMEMSLPSupervisedSchedulerServiceResult:
    """Content-free O2 service-loop result.

    Private O1E/O1D2/O1D1 results are not retained. Public projection exposes
    only bounded operational statuses and counters.
    """

    status: ServiceStatus
    mode: str
    rounds_attempted: int
    rounds_completed: int
    idle_rounds: int
    slept_count: int
    total_sleep_ms: int
    last_operational_status: str
    last_policy_status: str
    last_round_status: str
    last_pacing_recommendation: str
    cancelled: bool
    shutdown_requested: bool
    unsafe: bool
    bounded_reason_ids: tuple[str, ...] = ()
    schema_version: str = field(default=O2_SUPERVISED_SERVICE_RESULT_SCHEMA, init=False)

    def __post_init__(self) -> None:
        if self.status not in {
            "disabled",
            "completed",
            "idle",
            "cancelled",
            "shutdown_requested",
            "unsafe_state",
            "invalid_input",
            "invalid_config",
            "unexpected_failure",
        }:
            raise ValueError("o2_service_status_invalid")
        for name in (
            "mode",
            "last_operational_status",
            "last_policy_status",
            "last_round_status",
            "last_pacing_recommendation",
        ):
            if type(getattr(self, name)) is not str:
                raise TypeError("o2_service_string_field_invalid")
        for name in (
            "rounds_attempted",
            "rounds_completed",
            "idle_rounds",
            "slept_count",
            "total_sleep_ms",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError("o2_service_counter_invalid")
        for name in ("cancelled", "shutdown_requested", "unsafe"):
            if type(getattr(self, name)) is not bool:
                raise TypeError("o2_service_bool_invalid")
        object.__setattr__(
            self,
            "bounded_reason_ids",
            _reason_ids(self.bounded_reason_ids, maximum=MAX_O2_REASON_IDS),
        )

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPSupervisedSchedulerServiceResult("
            f"status={self.status!r}, mode={self.mode!r}, "
            f"rounds_attempted={self.rounds_attempted!r}, "
            f"rounds_completed={self.rounds_completed!r}, "
            "private_results_omitted=True)"
        )

    def projection(self) -> Mapping[str, object]:
        return {
            "schema_version": O2_SUPERVISED_SERVICE_PROJECTION_SCHEMA,
            "status": self.status,
            "mode": self.mode,
            "rounds_attempted": self.rounds_attempted,
            "rounds_completed": self.rounds_completed,
            "idle_rounds": self.idle_rounds,
            "slept_count": self.slept_count,
            "total_sleep_ms": self.total_sleep_ms,
            "last_operational_status": self.last_operational_status,
            "last_policy_status": self.last_policy_status,
            "last_round_status": self.last_round_status,
            "last_pacing_recommendation": self.last_pacing_recommendation,
            "cancelled": self.cancelled,
            "shutdown_requested": self.shutdown_requested,
            "unsafe": self.unsafe,
            "bounded_reason_ids": list(self.bounded_reason_ids),
        }


def run_relaymem_slp_supervised_scheduler_service(
    *,
    config: RelayLMConfig,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None = None,
    settings: RelayMEMSLPSupervisedSchedulerServiceSettings | None = None,
    now: datetime | None = None,
    cancellation: SchedulerCancellationToken | CancellationProbe | None = None,
    sleeper: Sleeper | None = None,
    runner: OperationalRunner = run_relaymem_slp_scheduler_operational_controls_once,
) -> RelayMEMSLPSupervisedSchedulerServiceResult:
    """Run an opt-in supervised local scheduler service loop.

    The loop delegates every operational iteration to O1E. It never mutates
    queue records directly and never reads or retains protected source bodies.
    """

    exact_settings = RelayMEMSLPSupervisedSchedulerServiceSettings() if settings is None else settings
    if type(config) is not RelayLMConfig:
        return _result(
            "invalid_input",
            "invalid",
            reasons=("exact_relaylm_config_required",),
            unsafe=True,
        )
    if registry is not None and type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        return _result(
            "invalid_input",
            "invalid",
            reasons=("exact_source_registry_required",),
            unsafe=True,
        )
    if type(exact_settings) is not RelayMEMSLPSupervisedSchedulerServiceSettings:
        return _result(
            "invalid_input",
            "invalid",
            reasons=("exact_o2_service_settings_required",),
            unsafe=True,
        )
    if sleeper is not None and not callable(sleeper):
        return _result(
            "invalid_input",
            "invalid",
            reasons=("o2_service_sleeper_invalid",),
            unsafe=True,
        )
    if not callable(runner):
        return _result(
            "invalid_input",
            "invalid",
            reasons=("o2_service_runner_invalid",),
            unsafe=True,
        )

    token = _coerce_cancellation(cancellation)
    if token is None and cancellation is not None:
        return _result(
            "invalid_input",
            "invalid",
            reasons=("scheduler_cancellation_probe_required",),
            unsafe=True,
        )

    exact_sleeper = time.sleep if sleeper is None else sleeper

    if exact_settings.install_signal_handlers:
        adapter = SchedulerSignalCancellationAdapter()
        token = _combine_cancellation(token, adapter.token)
        loop_settings = replace(exact_settings, install_signal_handlers=False)
        with adapter.installed():
            return _run_loop(
                config=config,
                registry=registry,
                settings=loop_settings,
                now=now,
                token=token,
                sleeper=exact_sleeper,
                runner=runner,
            )

    return _run_loop(
        config=config,
        registry=registry,
        settings=exact_settings,
        now=now,
        token=token,
        sleeper=exact_sleeper,
        runner=runner,
    )


def make_relaymem_slp_supervised_scheduler_service_projection(
    *,
    status: ServiceStatus,
    reason_id: str,
) -> Mapping[str, object]:
    """Return a content-free O2-shaped projection for CLI pre-service failures."""

    return _result(
        status,
        "invalid",
        reasons=(reason_id,),
        unsafe=status in {"invalid_input", "unsafe_state", "unexpected_failure"},
    ).projection()


def _run_loop(
    *,
    config: RelayLMConfig,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None,
    settings: RelayMEMSLPSupervisedSchedulerServiceSettings,
    now: datetime | None,
    token: SchedulerCancellationToken | None,
    sleeper: Sleeper,
    runner: OperationalRunner,
) -> RelayMEMSLPSupervisedSchedulerServiceResult:
    policy_state: SchedulerPolicyState | None = None
    rounds_attempted = 0
    rounds_completed = 0
    idle_rounds = 0
    slept_count = 0
    total_sleep_ms = 0

    last_mode = "unknown"
    last_operational_status = "not_invoked"
    last_policy_status = "not_invoked"
    last_round_status = "not_invoked"
    last_pacing_recommendation = "stop"

    while True:
        if token is not None and token.requested():
            return _result(
                "cancelled",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status=last_operational_status,
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                cancelled=True,
                reasons=("service_cancelled",),
            )

        if settings.max_rounds is not None and rounds_attempted >= settings.max_rounds:
            return _result(
                "completed",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status=last_operational_status,
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                reasons=("service_max_rounds_reached",),
            )

        rounds_attempted += 1
        try:
            operational = runner(
                config=config,
                registry=registry,
                now=now,
                policy_state=policy_state,
                cancellation=token,
            )
        except Exception:
            return _result(
                "unexpected_failure",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status="unexpected_failure",
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                unsafe=True,
                reasons=("service_runner_failed",),
            )

        if type(operational) is not SchedulerOperationalControlsResult:
            return _result(
                "unexpected_failure",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status="unexpected_failure",
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                unsafe=True,
                reasons=("exact_scheduler_operational_result_required",),
            )

        rounds_completed += 1
        last_mode = operational.mode
        last_operational_status = operational.status

        policy = operational.scheduler_policy_result
        if policy is not None:
            policy_projection = policy.projection()
            last_policy_status = policy.status
            last_round_status = (
                str(policy_projection.get("round_status"))
                if type(policy_projection) is dict
                else "not_invoked"
            )
            last_pacing_recommendation = policy.pacing_recommendation
            policy_state = policy.next_policy_state
        else:
            last_policy_status = "not_invoked"
            last_round_status = "not_invoked"
            last_pacing_recommendation = "stop"

        if operational.unsafe:
            return _result(
                "unsafe_state",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status=last_operational_status,
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                unsafe=True,
                reasons=_merge_reasons(operational.bounded_reason_ids, ("service_operational_unsafe",)),
            )
        if operational.status == "disabled":
            return _result(
                "disabled",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status=last_operational_status,
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                reasons=_merge_reasons(operational.bounded_reason_ids, ("service_disabled",)),
            )
        if operational.status == "invalid_input":
            return _result(
                "invalid_input",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status=last_operational_status,
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                unsafe=True,
                reasons=_merge_reasons(operational.bounded_reason_ids, ("service_invalid_input",)),
            )
        if operational.status == "invalid_config":
            return _result(
                "invalid_config",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status=last_operational_status,
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                reasons=_merge_reasons(operational.bounded_reason_ids, ("service_invalid_config",)),
            )
        if operational.status == "unexpected_failure":
            return _result(
                "unexpected_failure",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status=last_operational_status,
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                unsafe=True,
                reasons=_merge_reasons(operational.bounded_reason_ids, ("service_unexpected_failure",)),
            )
        if operational.shutdown_requested or operational.status == "shutdown_requested":
            return _result(
                "shutdown_requested",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status=last_operational_status,
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                shutdown_requested=True,
                reasons=_merge_reasons(operational.bounded_reason_ids, ("service_shutdown_requested",)),
            )
        if operational.cancelled or operational.status.startswith("cancelled_"):
            return _result(
                "cancelled",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status=last_operational_status,
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                cancelled=True,
                reasons=_merge_reasons(operational.bounded_reason_ids, ("service_cancelled",)),
            )
        if token is not None and token.requested():
            return _result(
                "cancelled",
                last_mode,
                rounds_attempted=rounds_attempted,
                rounds_completed=rounds_completed,
                idle_rounds=idle_rounds,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
                last_operational_status=last_operational_status,
                last_policy_status=last_policy_status,
                last_round_status=last_round_status,
                last_pacing_recommendation=last_pacing_recommendation,
                cancelled=True,
                reasons=("service_cancelled_after_round",),
            )

        if last_pacing_recommendation == "run_next_round":
            idle_rounds = 0
            continue
        if last_pacing_recommendation == "wait_before_next_round":
            idle_rounds = 0
            delay_ms = 0
            if policy is not None and type(policy.next_delay_ms) is int:
                delay_ms = min(policy.next_delay_ms, settings.max_sleep_ms)
            slept_count, total_sleep_ms = _sleep(
                sleeper=sleeper,
                delay_ms=delay_ms,
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
            )
            continue
        if last_pacing_recommendation == "idle":
            idle_rounds = min(idle_rounds + 1, MAX_O2_ROUNDS)
            if idle_rounds >= settings.stop_after_idle_rounds:
                return _result(
                    "idle",
                    last_mode,
                    rounds_attempted=rounds_attempted,
                    rounds_completed=rounds_completed,
                    idle_rounds=idle_rounds,
                    slept_count=slept_count,
                    total_sleep_ms=total_sleep_ms,
                    last_operational_status=last_operational_status,
                    last_policy_status=last_policy_status,
                    last_round_status=last_round_status,
                    last_pacing_recommendation=last_pacing_recommendation,
                    reasons=("service_idle_limit_reached",),
                )
            slept_count, total_sleep_ms = _sleep(
                sleeper=sleeper,
                delay_ms=min(settings.idle_sleep_ms, settings.max_sleep_ms),
                slept_count=slept_count,
                total_sleep_ms=total_sleep_ms,
            )
            continue

        return _result(
            "completed",
            last_mode,
            rounds_attempted=rounds_attempted,
            rounds_completed=rounds_completed,
            idle_rounds=idle_rounds,
            slept_count=slept_count,
            total_sleep_ms=total_sleep_ms,
            last_operational_status=last_operational_status,
            last_policy_status=last_policy_status,
            last_round_status=last_round_status,
            last_pacing_recommendation=last_pacing_recommendation,
            reasons=("service_completed",),
        )


def _sleep(
    *,
    sleeper: Sleeper,
    delay_ms: int,
    slept_count: int,
    total_sleep_ms: int,
) -> tuple[int, int]:
    bounded_delay_ms = min(max(0, delay_ms), MAX_O2_SLEEP_MS)
    sleeper(bounded_delay_ms / 1000.0)
    return (
        min(slept_count + 1, MAX_O2_SLEEP_COUNT),
        min(total_sleep_ms + bounded_delay_ms, MAX_O2_TOTAL_SLEEP_MS),
    )


def _coerce_cancellation(value: SchedulerCancellationToken | CancellationProbe | None) -> SchedulerCancellationToken | None:
    if value is None:
        return None
    if type(value) is SchedulerCancellationToken:
        return value
    if callable(value):
        return SchedulerCancellationToken(value)
    return None


def _combine_cancellation(
    first: SchedulerCancellationToken | None,
    second: SchedulerCancellationToken,
) -> SchedulerCancellationToken:
    if first is None:
        return second
    return SchedulerCancellationToken(lambda: first.requested() or second.requested())


def _result(
    status: ServiceStatus,
    mode: str,
    *,
    rounds_attempted: int = 0,
    rounds_completed: int = 0,
    idle_rounds: int = 0,
    slept_count: int = 0,
    total_sleep_ms: int = 0,
    last_operational_status: str = "not_invoked",
    last_policy_status: str = "not_invoked",
    last_round_status: str = "not_invoked",
    last_pacing_recommendation: str = "stop",
    cancelled: bool = False,
    shutdown_requested: bool = False,
    unsafe: bool = False,
    reasons: Sequence[str],
) -> RelayMEMSLPSupervisedSchedulerServiceResult:
    return RelayMEMSLPSupervisedSchedulerServiceResult(
        status=status,
        mode=mode,
        rounds_attempted=min(rounds_attempted, MAX_O2_ROUNDS),
        rounds_completed=min(rounds_completed, MAX_O2_ROUNDS),
        idle_rounds=min(idle_rounds, MAX_O2_ROUNDS),
        slept_count=min(slept_count, MAX_O2_SLEEP_COUNT),
        total_sleep_ms=min(total_sleep_ms, MAX_O2_TOTAL_SLEEP_MS),
        last_operational_status=last_operational_status,
        last_policy_status=last_policy_status,
        last_round_status=last_round_status,
        last_pacing_recommendation=last_pacing_recommendation,
        cancelled=cancelled,
        shutdown_requested=shutdown_requested,
        unsafe=unsafe,
        bounded_reason_ids=_reason_ids(reasons, maximum=MAX_O2_REASON_IDS),
    )


def _merge_reasons(first: Sequence[str], second: Sequence[str]) -> tuple[str, ...]:
    return _reason_ids(tuple(first) + tuple(second), maximum=MAX_O2_REASON_IDS)


def _reason_ids(values: Sequence[str], *, maximum: int) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        values = ("o2_service_reason_invalid",)
    output: list[str] = []
    for value in values:
        reason = value if type(value) is str and _REASON_RE.fullmatch(value) else "o2_service_reason_invalid"
        if reason not in output:
            output.append(reason)
        if len(output) >= maximum:
            break
    if not output:
        output.append("o2_service_status")
    return tuple(output)


__all__ = [
    "O2_SUPERVISED_SERVICE_PROJECTION_SCHEMA",
    "O2_SUPERVISED_SERVICE_RESULT_SCHEMA",
    "RelayMEMSLPSupervisedSchedulerServiceResult",
    "RelayMEMSLPSupervisedSchedulerServiceSettings",
    "make_relaymem_slp_supervised_scheduler_service_projection",
    "run_relaymem_slp_supervised_scheduler_service",
]
