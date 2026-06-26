#!/usr/bin/env python3
"""O1D1 concurrent round and delegated-authority contention smoke."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from _relaylm_o1d1_support import (  # noqa: E402
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
from relaylm.relaymem_slp_scheduler_round import (  # noqa: E402
    run_relaymem_slp_scheduler_round_once,
)


def run_two(fn):
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(fn) for _ in range(2)]
        return [future.result(timeout=10) for future in futures]


def main() -> None:
    # Two production rounds may race; the queue authority admits one candidate.
    queue_barrier = threading.Barrier(2)
    queue_state_lock = threading.Lock()
    queue_claimed = False

    def queue_contended(**_: object):
        nonlocal queue_claimed
        queue_barrier.wait(timeout=5)
        with queue_state_lock:
            if queue_claimed:
                return queue_busy()
            queue_claimed = True
            return queue_terminal()

    with patched_lanes(lambda **_: replay_no_work(), queue_contended):
        results = run_two(
            lambda: run_relaymem_slp_scheduler_round_once(
                config=scheduler_config(replay=True, queue=True)
            )
        )
    assert sum(result.work_units_completed for result in results) == 1
    assert all(result.work_units_attempted <= 1 for result in results)
    assert sorted(result.queue_lane.status for result in results) == ["busy", "terminal"]

    # O0 and O1D1 share the same conceptual B3 claim authority; either may win.
    claim_barrier = threading.Barrier(2)
    claim_lock = threading.Lock()
    claim_owner: list[str] = []

    def shared_claim(actor: str) -> bool:
        claim_barrier.wait(timeout=5)
        with claim_lock:
            if claim_owner:
                return False
            claim_owner.append(actor)
            return True

    def o0_competitor() -> str:
        return "o0_won" if shared_claim("o0") else "o0_lost"

    def scheduler_queue(**_: object):
        return queue_terminal() if shared_claim("o1d1") else queue_busy()

    with patched_lanes(lambda **_: replay_no_work(), scheduler_queue):
        with ThreadPoolExecutor(max_workers=2) as pool:
            o0_future = pool.submit(o0_competitor)
            round_future = pool.submit(
                run_relaymem_slp_scheduler_round_once,
                config=scheduler_config(replay=False, queue=True),
            )
            o0_result = o0_future.result(timeout=10)
            round_result = round_future.result(timeout=10)
    assert len(claim_owner) == 1
    assert (o0_result == "o0_won") != (round_result.work_units_completed == 1)

    # Normal finalization and O1D1 replay share the per-record replay fence.
    replay_barrier = threading.Barrier(2)
    replay_lock = threading.Lock()
    replay_owner: list[str] = []

    def shared_replay(actor: str) -> bool:
        replay_barrier.wait(timeout=5)
        with replay_lock:
            if replay_owner:
                return False
            replay_owner.append(actor)
            return True

    def finalizer_competitor() -> str:
        return "finalizer_won" if shared_replay("finalizer") else "finalizer_lost"

    def scheduler_replay(**_: object):
        return replay_completed() if shared_replay("o1d1") else replay_busy()

    with patched_lanes(scheduler_replay, lambda **_: queue_no_work()):
        with ThreadPoolExecutor(max_workers=2) as pool:
            finalizer_future = pool.submit(finalizer_competitor)
            round_future = pool.submit(
                run_relaymem_slp_scheduler_round_once,
                config=scheduler_config(replay=True, queue=False),
            )
            finalizer_result = finalizer_future.result(timeout=10)
            replay_result = round_future.result(timeout=10)
    assert len(replay_owner) == 1
    assert (finalizer_result == "finalizer_won") != (
        replay_result.work_units_completed == 1
    )

    for result in (*results, round_result, replay_result):
        assert result.work_units_attempted <= 2
        assert result.work_units_completed <= 2
        assert_safe_projection(result)
    print("O1D1 production round concurrency smoke passed")


if __name__ == "__main__":
    main()
