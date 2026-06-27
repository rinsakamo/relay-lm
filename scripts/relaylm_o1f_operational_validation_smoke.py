from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _relaylm_o1f_support import (
    assert_public_result_safe,
    base_config,
    initial_record,
    operational_config,
    require,
    sequence_probe,
    stale_claimed_record,
    write_record,
)
from relaylm.relaymem_slp_scheduler_operational_validation import (
    validate_queue_root_inventory,
    validate_scheduler_operational_boundary_once,
    validate_source_queue_correlation,
)
from relaylm.relaymem_slp_scheduler_operations import SchedulerCancellationToken

NOW = datetime(2026, 6, 22, 0, 0, 3, tzinfo=timezone.utc)


def main() -> int:
    disabled = validate_scheduler_operational_boundary_once(config=base_config())
    require(disabled.status == "validated", disabled.projection())
    require(disabled.operation_status == "disabled", disabled.projection())
    require(disabled.scheduler_round_invoked is False, disabled.projection())
    assert_public_result_safe(disabled)

    dry_run = validate_scheduler_operational_boundary_once(config=operational_config(mode="dry_run"), now=NOW)
    require(dry_run.status == "validated", dry_run.projection())
    require(dry_run.operation_status == "dry_run_ready", dry_run.projection())
    require(dry_run.scheduler_round_invoked is True, dry_run.projection())
    assert_public_result_safe(dry_run)

    for values, expected in (
        ([True], "cancelled_before_start"),
        ([False, True], "cancelled_before_stale_recovery"),
        ([False, False, True], "cancelled_before_scheduler_round"),
        ([False, False, False, True], "cancelled_after_scheduler_round"),
    ):
        cancelled = validate_scheduler_operational_boundary_once(
            config=operational_config(mode="dry_run"),
            now=NOW,
            cancellation=SchedulerCancellationToken(sequence_probe(list(values))),
        )
        require(cancelled.status == "validated", cancelled.projection())
        require(cancelled.operation_status == expected, cancelled.projection())
        assert_public_result_safe(cancelled)

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        queued_path = write_record(root, initial_record())
        inventory = validate_queue_root_inventory(queue_root=str(root), max_scan_entries=16, now=NOW)
        require(inventory.status == "validated", inventory.projection())
        require(inventory.checked_candidate_count == 1, inventory.projection())
        require(queued_path.exists(), "inventory mutated record")
        assert_public_result_safe(inventory)

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = stale_claimed_record()
        path = write_record(root, record)
        stale = validate_scheduler_operational_boundary_once(
            config=operational_config(mode="apply", stale="apply", queue_root=root),
            now=NOW,
        )
        require(stale.status == "validated", stale.projection())
        require(stale.operation_status == "completed", stale.projection())
        require(stale.stale_recovery_status == "stale_recovery_attempted", stale.projection())
        require(path.exists(), "stale recovery removed record")
        assert_public_result_safe(stale)

    source_ok = validate_source_queue_correlation(
        source_dispatch_idempotency_key="same",
        queue_dispatch_idempotency_key="same",
    )
    require(source_ok.status == "validated", source_ok.projection())
    assert_public_result_safe(source_ok)

    print("ok O1F operational boundary validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
