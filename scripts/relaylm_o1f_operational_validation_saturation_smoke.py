from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _relaylm_o1f_support import assert_public_result_safe, operational_config, require
from relaylm.relaymem_slp_scheduler_operational_validation import (
    validate_bounded_public_projection,
    validate_queue_root_inventory,
    validate_scheduler_operational_boundary_once,
)

NOW = datetime(2026, 6, 22, 0, 0, 3, tzinfo=timezone.utc)


def main() -> int:
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        for index in range(6):
            (root / f"ignored-{index}.txt").write_text("content-free\n", encoding="utf-8")
        saturated = validate_queue_root_inventory(queue_root=str(root), max_scan_entries=5, now=NOW)
        require(saturated.status == "unsafe", saturated.projection())
        require("operational_validation_scan_limit_exceeded" in saturated.bounded_reason_ids, saturated.projection())
        assert_public_result_safe(saturated)

    bounded = validate_bounded_public_projection({"bounded_reason_ids": [f"r{index}" for index in range(17)]})
    require(bounded == ("projection_reason_bound_invalid",), bounded)

    config = operational_config(mode="dry_run")
    for _ in range(3):
        result = validate_scheduler_operational_boundary_once(config=config, now=NOW)
        require(result.status == "validated", result.projection())
        require(result.operation_status == "dry_run_ready", result.projection())
        assert_public_result_safe(result)

    print("ok O1F saturation validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
