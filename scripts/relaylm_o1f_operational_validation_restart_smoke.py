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
    initial_record,
    operational_config,
    require,
    stale_claimed_record,
    terminal_record,
    write_record,
)
from relaylm.relaymem_slp_scheduler_operational_validation import (
    validate_durable_finalization_locator,
    validate_queue_root_inventory,
    validate_scheduler_operational_boundary_once,
)

NOW = datetime(2026, 6, 22, 0, 0, 3, tzinfo=timezone.utc)


def main() -> int:
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        missing = validate_durable_finalization_locator(sealed_root=str(root), locator_digest="d" * 64)
        require(missing.status == "validated", missing.projection())
        assert_public_result_safe(missing)

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        write_record(root, initial_record())
        queued = validate_queue_root_inventory(queue_root=str(root), max_scan_entries=16, now=NOW)
        require(queued.status == "validated", queued.projection())
        assert_public_result_safe(queued)

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        write_record(root, stale_claimed_record())
        claimed = validate_queue_root_inventory(queue_root=str(root), max_scan_entries=16, now=NOW)
        require(claimed.status == "validated", claimed.projection())
        recovered = validate_scheduler_operational_boundary_once(
            config=operational_config(mode="apply", stale="apply", queue_root=root),
            now=NOW,
        )
        require(recovered.status == "validated", recovered.projection())
        require(recovered.stale_recovery_status == "stale_recovery_attempted", recovered.projection())
        reread = validate_queue_root_inventory(queue_root=str(root), max_scan_entries=16, now=NOW)
        require(reread.status == "validated", reread.projection())
        assert_public_result_safe(recovered)
        assert_public_result_safe(reread)

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        write_record(root, terminal_record())
        terminal = validate_queue_root_inventory(queue_root=str(root), max_scan_entries=16, now=NOW)
        require(terminal.status == "validated", terminal.projection())
        assert_public_result_safe(terminal)

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = initial_record()
        path = write_record(root, record)
        path.write_bytes(b"{")
        malformed = validate_queue_root_inventory(queue_root=str(root), max_scan_entries=16, now=NOW)
        require(malformed.status == "unsafe", malformed.projection())
        assert_public_result_safe(malformed)

    print("ok O1F restart validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
