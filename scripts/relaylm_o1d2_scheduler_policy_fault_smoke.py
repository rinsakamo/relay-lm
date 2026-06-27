#!/usr/bin/env python3
"""O1D2 scheduler policy fault smoke."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from _relaylm_o1d1_support import (  # noqa: E402
    RAW_EXCEPTION_CANARY,
    assert_safe_projection,
    patched_lanes,
    queue_no_work,
    replay_completed,
    replay_no_work,
    scheduler_config,
)
from relaylm.relaymem_slp_scheduler_policy import (  # noqa: E402
    run_relaymem_slp_scheduler_round_once_with_policy,
)


def policy_config(**updates: object):
    return scheduler_config(
        relaymem_local_scheduler_policy_enabled=True,
        relaymem_local_scheduler_policy_dry_run_only=True,
        relaymem_local_scheduler_policy_apply_enabled=False,
        **updates,
    )


def raising_at(target: str):
    def fault(seam: str) -> None:
        if seam == target:
            raise RuntimeError(RAW_EXCEPTION_CANARY)

    return fault


def main() -> None:
    calls: list[str] = []

    def forbidden(**_: object):
        calls.append("lane")
        raise AssertionError("pre_round_fault_invoked_lane")

    with patched_lanes(forbidden, forbidden):
        before_round = run_relaymem_slp_scheduler_round_once_with_policy(
            config=policy_config(),
            fault_injector=raising_at("after_policy_validation_before_round"),
        )
    assert before_round.status == "unexpected_failure"
    assert before_round.projection()["round_status"] == "not_invoked"
    assert calls == []
    assert RAW_EXCEPTION_CANARY not in assert_safe_projection(before_round)

    order: list[str] = []

    def replay_once(**_: object):
        order.append("replay")
        return replay_completed()

    def queue_once(**_: object):
        order.append("queue")
        return queue_no_work()

    with patched_lanes(replay_once, queue_once):
        after_round = run_relaymem_slp_scheduler_round_once_with_policy(
            config=policy_config(),
            fault_injector=raising_at("after_round_before_policy"),
        )
    assert order == ["replay", "queue"]
    assert after_round.status == "unexpected_failure"
    assert after_round.projection()["round_status"] == "round_completed"
    assert RAW_EXCEPTION_CANARY not in assert_safe_projection(after_round)

    order.clear()
    with patched_lanes(replay_once, queue_once):
        before_return = run_relaymem_slp_scheduler_round_once_with_policy(
            config=policy_config(),
            fault_injector=raising_at("after_policy_before_return"),
        )
    assert order == ["replay", "queue"]
    assert before_return.status == "unexpected_failure"
    assert before_return.projection()["round_status"] == "round_completed"
    assert RAW_EXCEPTION_CANARY not in assert_safe_projection(before_return)

    with patched_lanes(lambda **_: replay_no_work(), lambda **_: queue_no_work()):
        o1d1_fault = run_relaymem_slp_scheduler_round_once_with_policy(
            config=policy_config(),
            fault_injector=raising_at("after_gate_validation_before_replay"),
        )
    assert o1d1_fault.status == "round_unsafe"
    assert o1d1_fault.projection()["round_status"] == "unexpected_failure"
    assert RAW_EXCEPTION_CANARY not in assert_safe_projection(o1d1_fault)

    print("O1D2 scheduler policy fault smoke passed")


if __name__ == "__main__":
    main()
