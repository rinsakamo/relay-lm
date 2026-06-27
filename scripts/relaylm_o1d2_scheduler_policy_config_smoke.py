#!/usr/bin/env python3
"""O1D2 scheduler policy config smoke."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from _relaylm_o1d1_support import make_config, patched_lanes, scheduler_config  # noqa: E402
from relaylm.config import RelayLMConfig  # noqa: E402
from relaylm.relaymem_slp_scheduler_policy import (  # noqa: E402
    run_relaymem_slp_scheduler_round_once_with_policy,
    validate_scheduler_policy_config,
)


def expect_invalid_config(**updates: object) -> None:
    try:
        make_config(**updates)
    except ValueError:
        return
    raise AssertionError(f"invalid config unexpectedly accepted: {updates!r}")


def policy_config(**updates: object) -> RelayLMConfig:
    return scheduler_config(
        relaymem_local_scheduler_policy_enabled=True,
        relaymem_local_scheduler_policy_dry_run_only=True,
        relaymem_local_scheduler_policy_apply_enabled=False,
        **updates,
    )


def main() -> None:
    default_cfg = make_config()
    mode, reasons = validate_scheduler_policy_config(default_cfg)
    assert mode == "disabled"
    assert reasons == ()

    dry_run_cfg = policy_config()
    mode, reasons = validate_scheduler_policy_config(dry_run_cfg)
    assert mode == "dry_run" and reasons == ()

    apply_cfg = scheduler_config(
        mode="apply",
        relaymem_local_scheduler_policy_enabled=True,
        relaymem_local_scheduler_policy_dry_run_only=False,
        relaymem_local_scheduler_policy_apply_enabled=True,
    )
    mode, reasons = validate_scheduler_policy_config(apply_cfg)
    assert mode == "apply" and reasons == ()

    expect_invalid_config(
        relaymem_local_scheduler_policy_enabled=True,
        relaymem_local_scheduler_policy_dry_run_only=False,
        relaymem_local_scheduler_policy_apply_enabled=False,
    )
    expect_invalid_config(relaymem_local_scheduler_policy_enabled=1)
    expect_invalid_config(relaymem_local_scheduler_policy_enabled="true")
    expect_invalid_config(relaymem_local_scheduler_pacing_base_delay_ms=True)
    expect_invalid_config(relaymem_local_scheduler_pacing_base_delay_ms="250")
    expect_invalid_config(relaymem_local_scheduler_policy_fairness_streak_limit=0)
    expect_invalid_config(relaymem_local_scheduler_pacing_base_delay_ms=5001)
    expect_invalid_config(relaymem_local_scheduler_pacing_jitter_ms=5001)
    expect_invalid_config(
        relaymem_local_scheduler_policy_short_retry_window_ms=600000,
        relaymem_local_scheduler_policy_later_retry_window_ms=300000,
    )

    # model_copy deliberately bypasses Pydantic validation; the policy wrapper must
    # still fail closed before O1B/O1C lane invocation.
    calls: list[str] = []

    def forbidden(**_: object):
        calls.append("lane")
        raise AssertionError("invalid_policy_config_invoked_lane")

    bad_runtime_cfg = dry_run_cfg.model_copy(
        update={"relaymem_local_scheduler_pacing_base_delay_ms": 60001}
    )
    with patched_lanes(forbidden, forbidden):
        bad_runtime = run_relaymem_slp_scheduler_round_once_with_policy(config=bad_runtime_cfg)
    assert bad_runtime.status == "invalid_configuration"
    assert bad_runtime.projection()["round_status"] == "not_invoked"
    assert calls == []

    disabled_policy_cfg = scheduler_config(
        relaymem_local_scheduler_policy_enabled=False,
        relaymem_local_scheduler_policy_dry_run_only=True,
        relaymem_local_scheduler_policy_apply_enabled=False,
    )
    with patched_lanes(forbidden, forbidden):
        disabled_policy = run_relaymem_slp_scheduler_round_once_with_policy(
            config=disabled_policy_cfg
        )
    assert disabled_policy.status == "policy_disabled"
    assert calls == []

    print("O1D2 scheduler policy config smoke passed")


if __name__ == "__main__":
    main()
