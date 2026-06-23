"""Content-free stage diagnostic for the Phase 6-C1-5 smoke suite."""
from __future__ import annotations

from pathlib import Path

from relaylm_phase6c1_durable_source_restart_smoke import (
    restart_retry_new_claim_and_terminal_cleanup,
    separate_process_restart_smoke,
)
from relaylm_phase6c1_durable_source_store_smoke import (
    bounds_orphans_and_cleanup_marker,
    corruption_matrix,
    create_read_duplicate_race_and_leakage,
)

_OUTPUT = Path("phase6c1-durable-source-stage.txt")
_STAGES = (
    ("store_create_duplicate_race", create_read_duplicate_race_and_leakage),
    ("store_corruption_matrix", corruption_matrix),
    ("store_bounds_orphan_cleanup", bounds_orphans_and_cleanup_marker),
    ("retry_new_claim_terminal", restart_retry_new_claim_and_terminal_cleanup),
    ("separate_process_restart", separate_process_restart_smoke),
)


def main() -> int:
    for stage_name, stage in _STAGES:
        try:
            stage()
        except Exception:
            _OUTPUT.write_text(f"failed_stage={stage_name}\n", encoding="utf-8")
            return 1
    _OUTPUT.write_text("failed_stage=none\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
