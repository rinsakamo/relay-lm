#!/usr/bin/env python3
"""O1D2 deterministic scheduler policy smoke."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from _relaylm_o1d1_support import (  # noqa: E402
    _lane,
    assert_safe_projection,
    patched_lanes,
    queue_busy,
    queue_no_work,
    queue_terminal,
    replay_busy,
    replay_completed,
    replay_no_work,
    scheduler_config,
)
from relaylm.relaymem_slp_scheduler_policy import (  # noqa: E402
    POLICY_PROJECTION_SCHEMA,
    SchedulerPolicyState,
    run_relaymem_slp_scheduler_round_once_with_policy,
)


@dataclass(frozen=True, repr=False)
class _RetryPrivate:
    earliest_retry_not_before: datetime
    private_locator: str = "locator-private-never-project"

    def __repr__(self) -> str:
        return "RetryPrivate(timestamp_omitted=True, locator_omitted=True)"


def policy_config(*, scheduler_mode: str = "dry_run", policy_mode: str = "dry_run", **updates: object):
    triples = {
        "disabled": (False, True, False),
        "dry_run": (True, True, False),
        "apply": (True, False, True),
    }
    enabled, dry_run_only, apply_enabled = triples[policy_mode]
    return scheduler_config(
        mode=scheduler_mode,
        relaymem_local_scheduler_policy_enabled=enabled,
        relaymem_local_scheduler_policy_dry_run_only=dry_run_only,
        relaymem_local_scheduler_policy_apply_enabled=apply_enabled,
        **updates,
    )


def queue_future_retry_at(when: datetime):
    return _lane(
        "queue",
        "future_retry_only",
        candidate_observed=True,
        no_work=True,
        future=True,
        retryable=True,
        reason="future_retry_only",
        private=_RetryPrivate(when),
    )


def main() -> None:
    calls: list[str] = []

    def forbidden(**_: object):
        calls.append("forbidden")
        raise AssertionError("policy_disabled_invoked_lane")

    with patched_lanes(forbidden, forbidden):
        disabled = run_relaymem_slp_scheduler_round_once_with_policy(
            config=policy_config(policy_mode="disabled")
        )
    assert disabled.status == "policy_disabled"
    assert disabled.projection()["round_status"] == "not_invoked"
    assert calls == []
    assert_safe_projection(disabled)

    order: list[str] = []

    def replay_once(**_: object):
        order.append("replay")
        return replay_no_work()

    def queue_once(**_: object):
        order.append("queue")
        return queue_no_work()

    with patched_lanes(replay_once, queue_once):
        idle_a = run_relaymem_slp_scheduler_round_once_with_policy(config=policy_config())
    with patched_lanes(replay_once, queue_once):
        idle_b = run_relaymem_slp_scheduler_round_once_with_policy(config=policy_config())
    assert order == ["replay", "queue", "replay", "queue"]
    assert idle_a.projection() == idle_b.projection()
    assert idle_a.projection()["schema_version"] == POLICY_PROJECTION_SCHEMA
    assert idle_a.pacing_recommendation == "idle"
    assert idle_a.next_policy_state.consecutive_no_work_count == 1
    assert_safe_projection(idle_a)

    with patched_lanes(replay_once, queue_once):
        no_work_repeat = run_relaymem_slp_scheduler_round_once_with_policy(
            config=policy_config(relaymem_local_scheduler_pacing_jitter_ms=10),
            policy_state=idle_a.next_policy_state,
        )
    assert no_work_repeat.pacing_recommendation == "wait_before_next_round"
    assert type(no_work_repeat.next_delay_ms) is int
    assert 0 <= no_work_repeat.next_delay_ms <= 5000

    with patched_lanes(lambda **_: replay_completed(), lambda **_: queue_no_work()):
        replay_fairness = run_relaymem_slp_scheduler_round_once_with_policy(
            config=policy_config(relaymem_local_scheduler_policy_fairness_streak_limit=3),
            policy_state=SchedulerPolicyState(replay_progress_streak=2),
        )
    assert replay_fairness.pacing_recommendation == "run_next_round"
    assert replay_fairness.fairness_lane_preference == "queue"

    with patched_lanes(lambda **_: replay_no_work(), lambda **_: queue_terminal()):
        queue_fairness = run_relaymem_slp_scheduler_round_once_with_policy(
            config=policy_config(relaymem_local_scheduler_policy_fairness_streak_limit=3),
            policy_state=SchedulerPolicyState(queue_progress_streak=2),
        )
    assert queue_fairness.pacing_recommendation == "run_next_round"
    assert queue_fairness.fairness_lane_preference == "replay"

    with patched_lanes(lambda **_: replay_busy(), lambda **_: queue_busy()):
        busy = run_relaymem_slp_scheduler_round_once_with_policy(config=policy_config())
    assert busy.pacing_recommendation == "wait_before_next_round"
    assert 0 <= busy.next_delay_ms <= 5000
    assert busy.next_policy_state.consecutive_contention_count == 1

    now = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
    with patched_lanes(
        lambda **_: replay_no_work(),
        lambda **_: queue_future_retry_at(now + timedelta(seconds=10)),
    ):
        future_short = run_relaymem_slp_scheduler_round_once_with_policy(
            config=policy_config(),
            now=now,
        )
    assert future_short.retry_window == "short"
    assert future_short.pacing_recommendation == "wait_before_next_round"
    assert "2026" not in assert_safe_projection(future_short)

    with patched_lanes(
        lambda **_: replay_no_work(),
        lambda **_: queue_future_retry_at(now + timedelta(hours=2)),
    ):
        future_later = run_relaymem_slp_scheduler_round_once_with_policy(
            config=policy_config(),
            now=now,
        )
    assert future_later.retry_window == "later"
    assert future_later.pacing_recommendation == "wait_before_next_round"

    print("O1D2 scheduler policy smoke passed")


if __name__ == "__main__":
    main()
