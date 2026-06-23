"""Sanitized bounded runner for all Phase 6-C1-5 durable-source smokes."""
from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout

from _relaylm_phase6c1_durable_source_support import PRIVATE_TOKENS
from relaylm_phase6c1_durable_source_restart_smoke import (
    restart_retry_new_claim_and_terminal_cleanup,
    separate_process_restart_smoke,
)
from relaylm_phase6c1_durable_source_store_smoke import (
    bounds_orphans_and_cleanup_marker,
    corruption_matrix,
    create_read_duplicate_race_and_leakage,
)
from relaylm_phase6c1_primary_worker_test_support import require

_STAGES = (
    ("store_create_duplicate_race", create_read_duplicate_race_and_leakage),
    ("store_corruption_matrix", corruption_matrix),
    ("store_bounds_orphan_cleanup", bounds_orphans_and_cleanup_marker),
    ("retry_new_claim_terminal", restart_retry_new_claim_and_terminal_cleanup),
    ("separate_process_restart", separate_process_restart_smoke),
)


def main() -> int:
    captured_out, captured_err = io.StringIO(), io.StringIO()
    failed_stage: str | None = None
    try:
        with redirect_stdout(captured_out), redirect_stderr(captured_err):
            for stage_name, stage in _STAGES:
                failed_stage = stage_name
                stage()
            failed_stage = None
    except Exception:
        print(f"Phase 6-C1-5 durable protected source smoke failed: {failed_stage}")
        return 1
    combined = captured_out.getvalue() + captured_err.getvalue()
    for token in PRIVATE_TOKENS:
        require(token not in combined, ("captured output leak", token))
    print("Phase 6-C1-5 durable protected source smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
