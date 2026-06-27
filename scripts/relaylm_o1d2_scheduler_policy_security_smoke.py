#!/usr/bin/env python3
"""O1D2 scheduler policy leakage and no-loop smoke."""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from _relaylm_o1d1_support import (  # noqa: E402
    CANARY,
    PATH_CANARY,
    RAW_EXCEPTION_CANARY,
    _lane,
    assert_safe_projection,
    patched_lanes,
    replay_completed,
    replay_no_work,
    scheduler_config,
)
from relaylm import relaymem_slp_scheduler_policy as policy_module  # noqa: E402
from relaylm.relaymem_slp_scheduler_policy import (  # noqa: E402
    SchedulerPolicyState,
    run_relaymem_slp_scheduler_round_once_with_policy,
)


def policy_config(**updates: object):
    return scheduler_config(
        relaymem_local_scheduler_policy_enabled=True,
        relaymem_local_scheduler_policy_dry_run_only=True,
        relaymem_local_scheduler_policy_apply_enabled=False,
        **updates,
    )


def queue_future_retry_with_private_canary():
    return _lane(
        "queue",
        "future_retry_only",
        candidate_observed=True,
        no_work=True,
        future=True,
        retryable=True,
        reason="future_retry_only",
        private={
            "retry_not_before": "2099-01-01T00:00:00Z",
            "queue_path": PATH_CANARY,
            "raw_exception": RAW_EXCEPTION_CANARY,
            "content": CANARY,
        },
    )


def queue_terminal_private_canary():
    return _lane(
        "queue",
        "terminal",
        candidate_observed=True,
        candidate_selected=True,
        reread=True,
        delegated=True,
        completed=True,
        mutation=True,
        terminal=True,
        reason="queue_terminal",
        private={
            "job_id": "job-private-never-project",
            "dispatch_id": "dispatch-private-never-project",
            "claim_token": "claim-private-never-project",
            "path": PATH_CANARY,
            "content": CANARY,
        },
    )


def assert_projection_has_no_private_values(result: object) -> None:
    encoded = assert_safe_projection(result)
    lowered = encoded.lower() + repr(result).lower()
    for token in (
        "2099",
        "job-private-never-project",
        "dispatch-private-never-project",
        "claim-private-never-project",
        CANARY.lower(),
        PATH_CANARY.lower(),
        RAW_EXCEPTION_CANARY.lower(),
        "private_delegate_result",
        "retry_not_before",
    ):
        assert token not in lowered, encoded


def main() -> None:
    with patched_lanes(lambda **_: replay_no_work(), lambda **_: queue_future_retry_with_private_canary()):
        future = run_relaymem_slp_scheduler_round_once_with_policy(config=policy_config())
    projection = future.projection()
    assert projection["retry_window"] == "unknown"
    assert projection["pacing_recommendation"] == "wait_before_next_round"
    assert_projection_has_no_private_values(future)

    with patched_lanes(lambda **_: replay_completed(private=CANARY), lambda **_: queue_terminal_private_canary()):
        private_progress = run_relaymem_slp_scheduler_round_once_with_policy(
            config=policy_config(relaymem_local_scheduler_pacing_jitter_ms=100),
            policy_state=SchedulerPolicyState(queue_progress_streak=2),
        )
    assert private_progress.pacing_recommendation == "run_next_round"
    assert private_progress.fairness_lane_preference in {"replay", "queue", "balanced"}
    assert_projection_has_no_private_values(private_progress)

    projection_text = json.dumps(private_progress.projection(), sort_keys=True)
    assert "scheduler_policy_projection" in projection_text
    assert "round_result" not in projection_text

    source = inspect.getsource(policy_module)
    lowered_source = source.lower()
    assert "time.sleep" not in lowered_source
    assert "asyncio.sleep" not in lowered_source
    assert "threading" not in lowered_source
    assert "while true" not in lowered_source
    assert "daemon" not in lowered_source
    assert "supervision" not in lowered_source

    print("O1D2 scheduler policy security smoke passed")


if __name__ == "__main__":
    main()
