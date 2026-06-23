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


def main() -> int:
    captured_out, captured_err = io.StringIO(), io.StringIO()
    with redirect_stdout(captured_out), redirect_stderr(captured_err):
        create_read_duplicate_race_and_leakage()
        corruption_matrix()
        bounds_orphans_and_cleanup_marker()
        restart_retry_new_claim_and_terminal_cleanup()
        separate_process_restart_smoke()
    combined = captured_out.getvalue() + captured_err.getvalue()
    for token in PRIVATE_TOKENS:
        require(token not in combined, ("captured output leak", token))
    print("Phase 6-C1-5 durable protected source smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
