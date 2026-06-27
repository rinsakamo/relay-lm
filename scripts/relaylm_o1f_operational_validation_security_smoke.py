from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _relaylm_o1f_support import CANARY, RAW_EXCEPTION_CANARY, assert_public_result_safe, operational_config, require
from relaylm.relaymem_slp_scheduler_operational_validation import (
    validate_content_free_projection,
    validate_scheduler_operational_boundary_once,
)
from relaylm.relaymem_slp_scheduler_operations import SchedulerSignalCancellationAdapter

NOW = datetime(2026, 6, 22, 0, 0, 3, tzinfo=timezone.utc)


def main() -> int:
    leaked = validate_content_free_projection({"public": CANARY})
    require(leaked == ("projection_private_token_leaked",), leaked)

    def raw_fault(_: str) -> None:
        raise RuntimeError(RAW_EXCEPTION_CANARY)

    faulted = validate_scheduler_operational_boundary_once(
        config=operational_config(mode="dry_run"),
        now=NOW,
        fault_injector=raw_fault,
    )
    require(faulted.status == "operation_unsafe", faulted.projection())
    require("scheduler_operational_fault_before_stale_recovery" in faulted.bounded_reason_ids, faulted.projection())
    assert_public_result_safe(faulted)

    adapter = SchedulerSignalCancellationAdapter()
    adapter.request_shutdown()
    cancelled = validate_scheduler_operational_boundary_once(
        config=operational_config(mode="dry_run"),
        now=NOW,
        cancellation=adapter.token,
    )
    require(cancelled.operation_status == "cancelled_before_start", cancelled.projection())
    assert_public_result_safe(cancelled)

    print("ok O1F security validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
