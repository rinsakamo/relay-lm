from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig
from relaylm.relaymem_slp_scheduler_operations import run_relaymem_slp_scheduler_operational_controls_once


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _config(**overrides: Any) -> RelayLMConfig:
    raw: dict[str, Any] = {
        "backends": {"local": {"base_url": "http://127.0.0.1:8000/v1"}},
        "model_routes": {"relaylm-default": {"backend": "local"}},
        "relaymem_local_scheduler_operational_controls_enabled": True,
        "relaymem_local_scheduler_operational_controls_dry_run_only": True,
        "relaymem_local_scheduler_operational_controls_apply_enabled": False,
    }
    raw.update(overrides)
    return RelayLMConfig.model_validate(raw)


def _fault_at(target: str):
    def fault(seam: str) -> None:
        if seam == target:
            raise RuntimeError("private backend error must not leak")
    return fault


def main() -> int:
    before_stale = run_relaymem_slp_scheduler_operational_controls_once(
        config=_config(),
        fault_injector=_fault_at("before_stale_recovery"),
    )
    require(before_stale.status == "unexpected_failure", before_stale.projection())
    require("private backend error" not in str(before_stale.projection()), before_stale.projection())

    before_round = run_relaymem_slp_scheduler_operational_controls_once(
        config=_config(),
        fault_injector=_fault_at("after_stale_recovery_before_scheduler_round"),
    )
    require(before_round.status == "unexpected_failure", before_round.projection())
    require(before_round.scheduler_round_invoked is False, before_round.projection())

    before_return = run_relaymem_slp_scheduler_operational_controls_once(
        config=_config(),
        fault_injector=_fault_at("before_operational_projection_return"),
    )
    require(before_return.status == "unexpected_failure", before_return.projection())

    calls = {"count": 0}

    def cancel_after_stale() -> bool:
        calls["count"] += 1
        return calls["count"] >= 3

    cancelled = run_relaymem_slp_scheduler_operational_controls_once(
        config=_config(),
        cancellation=cancel_after_stale,
    )
    require(cancelled.status == "cancelled_before_scheduler_round", cancelled.projection())
    require(cancelled.scheduler_round_invoked is False, cancelled.projection())
    print("ok O1E fault and cancellation checkpoints remain bounded")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
