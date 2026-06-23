"""Content-free stage diagnostic for the Phase 6-C1-5 smoke suite."""
from __future__ import annotations

from pathlib import Path

import relaylm_phase6c1_durable_source_restart_smoke as restart_smoke
import relaylm_phase6c1_durable_source_store_smoke as store_smoke

_OUTPUT = Path("phase6c1-durable-source-stage.txt")
_STAGES = (
    ("store_create_duplicate_race", store_smoke.create_read_duplicate_race_and_leakage),
    ("store_corruption_matrix", store_smoke.corruption_matrix),
    ("store_bounds_orphan_cleanup", store_smoke.bounds_orphans_and_cleanup_marker),
    ("retry_new_claim_terminal", restart_smoke.restart_retry_new_claim_and_terminal_cleanup),
    ("separate_process_restart", restart_smoke.separate_process_restart_smoke),
)


def main() -> int:
    assertion_index = 0
    original_store_require = store_smoke.require
    original_restart_require = restart_smoke.require

    def diagnostic_store_require(condition: bool, detail: object) -> None:
        nonlocal assertion_index
        assertion_index += 1
        original_store_require(condition, detail)

    def diagnostic_restart_require(condition: bool, detail: object) -> None:
        nonlocal assertion_index
        assertion_index += 1
        original_restart_require(condition, detail)

    store_smoke.require = diagnostic_store_require
    restart_smoke.require = diagnostic_restart_require
    for stage_name, stage in _STAGES:
        assertion_index = 0
        try:
            stage()
        except Exception:
            _OUTPUT.write_text(
                f"failed_stage={stage_name}\nassertion_index={assertion_index}\n",
                encoding="utf-8",
            )
            return 1
    _OUTPUT.write_text("failed_stage=none\nassertion_index=0\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
