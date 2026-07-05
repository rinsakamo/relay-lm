#!/usr/bin/env python3
"""O2 supervised scheduler service smoke."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from relaylm.config import RelayLMConfig  # noqa: E402
from relaylm.relaymem_slp_scheduler_operations import (  # noqa: E402
    SchedulerCancellationToken,
    SchedulerOperationalControlsResult,
)
from relaylm.relaymem_slp_scheduler_policy import (  # noqa: E402
    SchedulerPolicyRoundResult,
    SchedulerPolicyState,
)
from relaylm.relaymem_slp_supervised_scheduler_service import (  # noqa: E402
    O2_SUPERVISED_SERVICE_PROJECTION_SCHEMA,
    RelayMEMSLPSupervisedSchedulerServiceSettings,
    run_relaymem_slp_supervised_scheduler_service,
)


FORBIDDEN = (
    "job_id",
    "dispatch_idempotency_key",
    "lease_token",
    "claim_owner",
    "protected_source_body",
    "memory_content",
    "/tmp/relaylm/private/queue-root",
    "O2_PRIVATE_CANARY_399b58",
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _base_config(**overrides: Any) -> RelayLMConfig:
    raw: dict[str, object] = {
        "backends": {"local": {"base_url": "http://127.0.0.1:1234/v1"}},
        "model_routes": {"relaylm-default": {"backend": "local"}},
    }
    raw.update(overrides)
    return RelayLMConfig.model_validate(raw)


def _policy(
    pacing: str,
    *,
    state: SchedulerPolicyState | None = None,
    next_state: SchedulerPolicyState | None = None,
    delay_ms: int | None = None,
    unsafe: bool = False,
) -> SchedulerPolicyRoundResult:
    exact_state = SchedulerPolicyState() if state is None else state
    exact_next = exact_state if next_state is None else next_state
    return SchedulerPolicyRoundResult(
        status="round_unsafe" if unsafe else "policy_evaluated",
        policy_state=exact_state,
        next_policy_state=exact_next,
        pacing_recommendation=pacing,  # type: ignore[arg-type]
        next_delay_ms=delay_ms,
        retry_window="none",
        fairness_lane_preference="none",
        unsafe=unsafe,
        bounded_reason_ids=("o2_smoke_policy",),
    )


def _op(
    *,
    status: str = "completed",
    mode: str = "apply",
    policy: SchedulerPolicyRoundResult | None = None,
    unsafe: bool = False,
    reasons: tuple[str, ...] = ("o2_smoke_operation",),
) -> SchedulerOperationalControlsResult:
    return SchedulerOperationalControlsResult(
        status=status,  # type: ignore[arg-type]
        mode=mode,
        scheduler_round_invoked=policy is not None,
        scheduler_policy_result=policy,
        cancelled=status.startswith("cancelled_"),
        unsafe=unsafe,
        bounded_reason_ids=reasons,
    )


def _safe_projection(result: object) -> dict[str, object]:
    projection = result.projection()  # type: ignore[attr-defined]
    encoded = json.dumps(projection, ensure_ascii=True, sort_keys=True)
    lowered = encoded.lower()
    repr_lowered = repr(result).lower()
    for token in FORBIDDEN:
        require(token.lower() not in lowered, encoded)
        require(token.lower() not in repr_lowered, repr(result))
    return projection


def main() -> None:
    disabled = run_relaymem_slp_supervised_scheduler_service(config=_base_config())
    require(disabled.status == "disabled", disabled.projection())
    require(disabled.projection()["schema_version"] == O2_SUPERVISED_SERVICE_PROJECTION_SCHEMA, disabled.projection())
    _safe_projection(disabled)

    carried_states: list[SchedulerPolicyState | None] = []
    first_next = SchedulerPolicyState(queue_progress_streak=1)

    def run_then_idle(**kwargs: object) -> SchedulerOperationalControlsResult:
        carried_states.append(kwargs.get("policy_state"))  # type: ignore[arg-type]
        if len(carried_states) == 1:
            return _op(policy=_policy("run_next_round", next_state=first_next))
        return _op(policy=_policy("idle", state=first_next, next_state=first_next))

    multi = run_relaymem_slp_supervised_scheduler_service(
        config=_base_config(),
        settings=RelayMEMSLPSupervisedSchedulerServiceSettings(max_rounds=3, stop_after_idle_rounds=1),
        sleeper=lambda seconds: None,
        runner=run_then_idle,
    )
    require(multi.status == "idle", multi.projection())
    require(len(carried_states) == 2, carried_states)
    require(carried_states[0] is None, carried_states)
    require(carried_states[1] == first_next, carried_states)
    require(multi.rounds_attempted == 2, multi.projection())
    _safe_projection(multi)

    slept: list[float] = []

    def wait_then_idle(**_: object) -> SchedulerOperationalControlsResult:
        if not slept:
            return _op(policy=_policy("wait_before_next_round", delay_ms=250))
        return _op(policy=_policy("idle"))

    waited = run_relaymem_slp_supervised_scheduler_service(
        config=_base_config(),
        settings=RelayMEMSLPSupervisedSchedulerServiceSettings(max_rounds=2, max_sleep_ms=1000),
        sleeper=slept.append,
        runner=wait_then_idle,
    )
    require(waited.status == "idle", waited.projection())
    require(slept == [0.25], slept)
    require(waited.slept_count == 1 and waited.total_sleep_ms == 250, waited.projection())
    _safe_projection(waited)

    idle_calls = 0
    idle_sleeps: list[float] = []

    def idle_twice(**_: object) -> SchedulerOperationalControlsResult:
        nonlocal idle_calls
        idle_calls += 1
        return _op(policy=_policy("idle"))

    idle = run_relaymem_slp_supervised_scheduler_service(
        config=_base_config(),
        settings=RelayMEMSLPSupervisedSchedulerServiceSettings(
            max_rounds=3,
            stop_after_idle_rounds=2,
            idle_sleep_ms=25,
        ),
        sleeper=idle_sleeps.append,
        runner=idle_twice,
    )
    require(idle.status == "idle", idle.projection())
    require(idle_calls == 2, idle_calls)
    require(idle_sleeps == [0.025], idle_sleeps)
    require(idle.idle_rounds == 2, idle.projection())
    _safe_projection(idle)

    called = False

    def forbidden_runner(**_: object) -> SchedulerOperationalControlsResult:
        nonlocal called
        called = True
        return _op()

    cancelled = run_relaymem_slp_supervised_scheduler_service(
        config=_base_config(),
        cancellation=SchedulerCancellationToken(lambda: True),
        runner=forbidden_runner,
    )
    require(cancelled.status == "cancelled", cancelled.projection())
    require(called is False, "runner invoked after pre-start cancellation")
    _safe_projection(cancelled)

    after_flag = {"cancel": False}

    def cancel_after_round(**_: object) -> SchedulerOperationalControlsResult:
        after_flag["cancel"] = True
        return _op(policy=_policy("run_next_round"))

    cancel_after = run_relaymem_slp_supervised_scheduler_service(
        config=_base_config(),
        settings=RelayMEMSLPSupervisedSchedulerServiceSettings(max_rounds=3),
        cancellation=SchedulerCancellationToken(lambda: after_flag["cancel"]),
        runner=cancel_after_round,
    )
    require(cancel_after.status == "cancelled", cancel_after.projection())
    require(cancel_after.rounds_attempted == 1, cancel_after.projection())
    _safe_projection(cancel_after)

    unsafe = run_relaymem_slp_supervised_scheduler_service(
        config=_base_config(),
        runner=lambda **_: _op(
            policy=_policy("stop", unsafe=True),
            unsafe=True,
            reasons=("unsafe_state",),
        ),
    )
    require(unsafe.status == "unsafe_state", unsafe.projection())
    _safe_projection(unsafe)

    invalid_exact = run_relaymem_slp_supervised_scheduler_service(
        config=_base_config(),
        runner=lambda **_: object(),  # type: ignore[return-value]
    )
    require(invalid_exact.status == "unexpected_failure", invalid_exact.projection())
    _safe_projection(invalid_exact)

    print("O2 supervised scheduler service smoke passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
