#!/usr/bin/env python3
"""O1D1 accepted-gate and one production-round smoke."""
from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from _relaylm_o1d1_support import (  # noqa: E402
    assert_safe_projection,
    patched_lanes,
    queue_busy,
    queue_future_retry,
    queue_no_work,
    queue_terminal,
    replay_busy,
    replay_candidate_changed,
    replay_completed,
    replay_no_work,
    scheduler_config,
    write_marker,
)
from relaylm.relaymem_slp_scheduler_round import (  # noqa: E402
    build_relaymem_slp_scheduler_gates,
    run_relaymem_slp_scheduler_round_once,
)


def main() -> None:
    calls: list[str] = []

    def forbidden(**_: object):
        calls.append("forbidden")
        raise AssertionError("disabled_scheduler_invoked_lane")

    with patched_lanes(forbidden, forbidden):
        disabled = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config(mode="disabled")
        )
    assert disabled.status == "disabled" and disabled.disposition == "stop"
    assert calls == []

    order: list[str] = []

    def replay_once(**_: object):
        order.append("replay")
        return replay_no_work()

    def queue_once(**_: object):
        order.append("queue")
        return queue_no_work()

    with patched_lanes(replay_once, queue_once):
        both_idle = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert order == ["replay", "queue"]
    assert both_idle.status == "idle" and both_idle.disposition == "idle"
    assert both_idle.work_units_attempted == 0

    order.clear()
    with patched_lanes(replay_once, forbidden):
        replay_only = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config(replay=True, queue=False)
        )
    assert order == ["replay"] and replay_only.queue_lane is None

    order.clear()
    with patched_lanes(forbidden, queue_once):
        queue_only = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config(replay=False, queue=True)
        )
    assert order == ["queue"] and queue_only.replay_lane is None

    with patched_lanes(
        lambda **_: replay_completed(),
        lambda **_: queue_no_work(),
    ):
        replay_progress = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert replay_progress.disposition == "run_next_round"
    assert replay_progress.work_units_completed == 1

    with patched_lanes(
        lambda **_: replay_no_work(),
        lambda **_: queue_terminal(),
    ):
        queue_progress = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert queue_progress.disposition == "run_next_round"
    assert queue_progress.work_units_completed == 1

    with patched_lanes(
        lambda **_: replay_completed(),
        lambda **_: queue_terminal(),
    ):
        both_progress = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config(mode="apply")
        )
    assert both_progress.work_units_attempted == 2
    assert both_progress.work_units_completed == 2
    assert both_progress.status == "round_completed"

    with patched_lanes(
        lambda **_: replay_candidate_changed(),
        lambda **_: queue_no_work(),
    ):
        changed = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert changed.disposition == "run_next_round"

    with patched_lanes(
        lambda **_: replay_no_work(),
        lambda **_: queue_future_retry(),
    ):
        future = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert future.disposition == "idle" and future.future_work_hint_present
    assert "2099" not in assert_safe_projection(future)

    with patched_lanes(
        lambda **_: replay_busy(),
        lambda **_: queue_busy(),
    ):
        busy = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert busy.disposition == "idle" and busy.retryable

    # Same-round convergence is sequencing plus an independent queue-root reopen.
    with TemporaryDirectory() as tmp:
        queue_root = Path(tmp).resolve()
        marker = queue_root / "new-b2-record"
        same_round_order: list[str] = []

        def replay_creates_b2(*, config, **_: object):
            same_round_order.append("replay")
            assert Path(config.relaymem_slp_queue_root) == queue_root
            write_marker(marker)
            return replay_completed()

        def queue_rediscovers(*, config, **_: object):
            same_round_order.append("queue")
            independently_opened = Path(config.relaymem_slp_queue_root)
            assert independently_opened == queue_root
            assert independently_opened.joinpath(marker.name).is_file()
            return queue_terminal()

        with patched_lanes(replay_creates_b2, queue_rediscovers):
            same_round = run_relaymem_slp_scheduler_round_once(
                config=scheduler_config(relaymem_slp_queue_root=str(queue_root))
            )
        assert same_round_order == ["replay", "queue"]
        assert same_round.work_units_completed == 2

    # Scheduler apply is only an upper gate; lower authority values are unchanged.
    observed: list[tuple[bool, bool, bool, str]] = []

    def observe_lower_gates(*, config, gates, **_: object):
        observed.append(
            (
                config.relaymem_local_worker_enabled,
                config.relaymem_local_worker_dry_run_only,
                config.relaymem_local_worker_apply_enabled,
                gates.mode,
            )
        )
        return queue_no_work()

    cfg = scheduler_config(
        mode="apply",
        replay=False,
        queue=True,
        relaymem_local_worker_enabled=True,
        relaymem_local_worker_dry_run_only=True,
        relaymem_local_worker_apply_enabled=False,
    )
    with patched_lanes(forbidden, observe_lower_gates):
        run_relaymem_slp_scheduler_round_once(config=cfg)
    assert observed == [(True, True, False, "apply")]

    gates = build_relaymem_slp_scheduler_gates(cfg)
    assert gates.mode == "apply"
    assert_safe_projection(both_idle)
    assert_safe_projection(both_progress)
    print("O1D1 production round smoke passed")


if __name__ == "__main__":
    main()
