#!/usr/bin/env python3
"""O1D1 ordering and partial-completion fault smoke."""
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
    queue_terminal,
    queue_unsafe,
    replay_busy,
    replay_completed,
    replay_isolated,
    scheduler_config,
)
from relaylm import relaymem_slp_scheduler_round as round_module  # noqa: E402
from relaylm.relaymem_slp_scheduler_round import (  # noqa: E402
    run_relaymem_slp_scheduler_round_once,
)


def inject_at(target: str):
    def inject(stage: str) -> None:
        if stage == target:
            raise RuntimeError(f"{RAW_EXCEPTION_CANARY}:{target}")

    return inject


def main() -> None:
    calls: list[str] = []

    def replay_success(**_: object):
        calls.append("replay")
        return replay_completed()

    def queue_success(**_: object):
        calls.append("queue")
        return queue_terminal()

    with patched_lanes(replay_success, queue_success):
        before_replay = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config(),
            fault_injector=inject_at("after_gate_validation_before_replay"),
        )
    assert calls == []
    assert before_replay.status == "unexpected_failure"
    assert before_replay.replay_lane is None and before_replay.queue_lane is None

    calls.clear()
    with patched_lanes(replay_success, queue_success):
        before_queue = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config(),
            fault_injector=inject_at("after_replay_before_queue"),
        )
    assert calls == ["replay"]
    assert before_queue.status == "unexpected_failure"
    assert before_queue.replay_lane is not None
    assert before_queue.replay_lane.delegation_completed
    assert before_queue.queue_lane is None

    calls.clear()
    with patched_lanes(replay_success, queue_success):
        before_aggregation = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config(),
            fault_injector=inject_at("after_queue_before_aggregation"),
        )
    assert calls == ["replay", "queue"]
    assert before_aggregation.status == "unexpected_failure"
    assert before_aggregation.work_units_completed == 2

    for stage in (
        "after_aggregation_before_projection",
        "after_projection_before_return",
    ):
        calls.clear()
        with patched_lanes(replay_success, queue_success):
            result = run_relaymem_slp_scheduler_round_once(
                config=scheduler_config(), fault_injector=inject_at(stage)
            )
        assert calls == ["replay", "queue"]
        assert result.status == "unexpected_failure"
        assert result.work_units_completed == 2
        assert_safe_projection(result)

    def replay_raises(**_: object):
        calls.append("replay")
        raise RuntimeError(RAW_EXCEPTION_CANARY)

    calls.clear()
    with patched_lanes(replay_raises, queue_success):
        replay_failure = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert calls == ["replay"]
    assert replay_failure.status == "unexpected_failure"
    assert replay_failure.queue_lane is None
    assert RAW_EXCEPTION_CANARY not in assert_safe_projection(replay_failure)

    def queue_raises(**_: object):
        calls.append("queue")
        raise RuntimeError(RAW_EXCEPTION_CANARY)

    calls.clear()
    with patched_lanes(replay_success, queue_raises):
        queue_failure = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert calls == ["replay", "queue"]
    assert queue_failure.status == "unexpected_failure"
    assert queue_failure.replay_lane is not None
    assert queue_failure.replay_lane.delegation_completed
    assert RAW_EXCEPTION_CANARY not in assert_safe_projection(queue_failure)

    # Classified lane-local outcomes do not suppress the independent queue lane.
    calls.clear()
    with patched_lanes(
        lambda **_: (calls.append("replay"), replay_busy())[1],
        queue_success,
    ):
        replay_busy_queue_works = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert calls == ["replay", "queue"]
    assert replay_busy_queue_works.queue_lane is not None
    assert replay_busy_queue_works.queue_lane.delegation_completed

    calls.clear()
    with patched_lanes(
        lambda **_: (calls.append("replay"), replay_isolated())[1],
        queue_success,
    ):
        isolated_queue_works = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert calls == ["replay", "queue"]
    assert isolated_queue_works.queue_lane is not None
    assert isolated_queue_works.queue_lane.delegation_completed

    with patched_lanes(replay_success, lambda **_: queue_unsafe()):
        queue_unsafe_after_replay = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert queue_unsafe_after_replay.replay_lane is not None
    assert queue_unsafe_after_replay.replay_lane.delegation_completed
    assert queue_unsafe_after_replay.unsafe

    # A projection invariant failure is converted to one fixed content-free result.
    previous = round_module._validate_round_projection

    def invalid_projection(*_: object) -> None:
        raise ValueError(RAW_EXCEPTION_CANARY)

    round_module._validate_round_projection = invalid_projection
    try:
        with patched_lanes(replay_success, queue_no_work):
            projection_failure = run_relaymem_slp_scheduler_round_once(
                config=scheduler_config()
            )
    finally:
        round_module._validate_round_projection = previous
    assert projection_failure.status == "unexpected_failure"
    assert projection_failure.replay_lane is not None
    assert projection_failure.replay_lane.delegation_completed
    assert RAW_EXCEPTION_CANARY not in assert_safe_projection(projection_failure)
    print("O1D1 production round fault smoke passed")


if __name__ == "__main__":
    main()
