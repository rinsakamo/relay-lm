#!/usr/bin/env python3
"""O1D1 content, identity, path, exception, and schema leakage smoke."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from _relaylm_o1d1_support import (  # noqa: E402
    CANARY,
    PATH_CANARY,
    RAW_EXCEPTION_CANARY,
    assert_safe_projection,
    patched_lanes,
    queue_terminal,
    replay_completed,
    scheduler_config,
)
from relaylm.relaymem_slp_scheduler_contract import LaneOutcome  # noqa: E402
from relaylm.relaymem_slp_scheduler_round import (  # noqa: E402
    run_relaymem_slp_scheduler_round_once,
)


def expect_raises(exc_type: type[BaseException], fn) -> None:
    try:
        fn()
    except exc_type:
        return
    raise AssertionError(f"expected_{exc_type.__name__}")


def main() -> None:
    private = {
        "user_text": CANARY,
        "assistant_text": CANARY,
        "protected_source": CANARY,
        "job_id": "private-job",
        "dispatch_id": "private-dispatch",
        "queue_root": PATH_CANARY,
        "claim_owner": "private-owner",
        "lease_token": "private-token",
        "retry_not_before": "2099-01-01T00:00:00Z",
    }
    with patched_lanes(
        lambda **_: replay_completed(private),
        lambda **_: queue_terminal(private),
    ):
        result = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config(
                relaymem_slp_queue_root=PATH_CANARY,
                relaymem_slp_protected_source_root=PATH_CANARY,
            )
        )
    encoded = assert_safe_projection(result)
    assert CANARY not in encoded and PATH_CANARY not in encoded
    assert result.replay_lane == replay_completed({"different": "private"})
    assert result.queue_lane == queue_terminal({"different": "private"})

    def replay_exception(**_: object):
        raise RuntimeError(f"{RAW_EXCEPTION_CANARY}:{PATH_CANARY}:{CANARY}")

    with patched_lanes(replay_exception, lambda **_: queue_terminal(private)):
        failed = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    failed_encoded = assert_safe_projection(failed)
    assert RAW_EXCEPTION_CANARY not in failed_encoded
    assert failed.queue_lane is None

    # Wrong result types and unknown statuses fail closed before queue invocation.
    queue_calls: list[str] = []

    def queue_should_not_run(**_: object):
        queue_calls.append("queue")
        return queue_terminal()

    with patched_lanes(lambda **_: object(), queue_should_not_run):
        wrong_type = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert wrong_type.status == "unexpected_failure" and queue_calls == []
    assert_safe_projection(wrong_type)

    unknown = object.__new__(LaneOutcome)
    for name, value in {
        "lane_kind": "replay",
        "status": "unknown_private_status",
        "enabled": True,
        "attempted": True,
        "candidate_observed": False,
        "candidate_selected": False,
        "canonical_reread_performed": False,
        "delegation_attempted": False,
        "delegation_completed": False,
        "mutation_may_have_occurred": False,
        "no_immediate_work": True,
        "future_work_hint_present": False,
        "contention_observed": False,
        "retryable": False,
        "unsafe": False,
        "terminal_for_candidate": False,
        "bounded_reason_ids": ("private_unknown",),
        "private_delegate_result": private,
        "schema_version": "relaylm.local_scheduler_lane_result.v0",
    }.items():
        object.__setattr__(unknown, name, value)
    queue_calls.clear()
    with patched_lanes(lambda **_: unknown, queue_should_not_run):
        unknown_result = run_relaymem_slp_scheduler_round_once(
            config=scheduler_config()
        )
    assert unknown_result.status == "unexpected_failure" and queue_calls == []
    assert_safe_projection(unknown_result)

    # O1A reason count/format bounds remain authoritative.
    expect_raises(
        (TypeError, ValueError),
        lambda: LaneOutcome(
            lane_kind="replay",
            status="no_eligible_work",
            enabled=True,
            attempted=True,
            candidate_observed=False,
            candidate_selected=False,
            canonical_reread_performed=False,
            delegation_attempted=False,
            delegation_completed=False,
            mutation_may_have_occurred=False,
            no_immediate_work=True,
            future_work_hint_present=False,
            contention_observed=False,
            retryable=False,
            unsafe=False,
            terminal_for_candidate=False,
            bounded_reason_ids=tuple(f"reason_{index}" for index in range(9)),
        ),
    )
    print("O1D1 production round security smoke passed")


if __name__ == "__main__":
    main()
