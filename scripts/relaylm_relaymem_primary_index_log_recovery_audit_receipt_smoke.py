from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm import _relaymem_primary_index_log_apply_io as apply_io
from relaylm.relaymem_primary_index_log_apply import (
    apply_relaymem_primary_index_log_reconciliation,
)
from relaylm.relaymem_primary_index_log_recovery_audit import (
    audit_relaymem_primary_index_log_reconciliation_recovery,
)
from scripts.relaylm_relaymem_primary_index_log_apply_smoke import fresh_plan
from scripts.relaylm_relaymem_primary_index_log_reconciliation_smoke import (
    fixture,
    require,
)


def apply_plan(root: Path, plan: dict[str, object]) -> dict[str, object]:
    return apply_relaymem_primary_index_log_reconciliation(
        plan_artifact=plan,
        root_path=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )


def audit(root: Path, receipt: dict[str, object]) -> dict[str, object]:
    return audit_relaymem_primary_index_log_reconciliation_recovery(
        receipt=receipt,
        root_path=str(root),
        enabled=True,
        dry_run_only=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        page_receipt, _, _, _ = fixture(root)
        plan = fresh_plan(root, page_receipt)
        dry_run = apply_relaymem_primary_index_log_reconciliation(
            plan_artifact=plan,
            root_path=str(root),
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
        )
        require(dry_run["status"] == "dry_run_ready", dry_run)
        require(dry_run["receipt"] is not None, dry_run)

        invalid_receipt = copy.deepcopy(dry_run["receipt"])
        invalid_receipt["status"] = "applied_durability_unconfirmed"
        rejected = audit(root, invalid_receipt)
        require(rejected["status"] == "blocked", rejected)
        require(rejected["receipt_valid"] is False, rejected)
        require(
            "primary_reconciliation_recovery_receipt_durability_state_mismatch"
            in rejected["blocked_reasons"],
            rejected,
        )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        page_receipt, _, _, _ = fixture(root)
        plan = fresh_plan(root, page_receipt)
        original_fsync = apply_io.os.fsync
        fsync_calls = 0

        def simulate_index_directory_fsync_error(fd: int) -> None:
            nonlocal fsync_calls
            fsync_calls += 1
            if fsync_calls == 2:
                raise OSError("simulated index directory fsync error")
            original_fsync(fd)

        apply_io.os.fsync = simulate_index_directory_fsync_error
        try:
            partial = apply_plan(root, plan)
        finally:
            apply_io.os.fsync = original_fsync

        require(partial["status"] == "applied_durability_unconfirmed", partial)
        require(partial["index_reconciled"] is True, partial)
        require(partial["log_reconciled"] is False, partial)
        require(partial["index_updated"] is True, partial)
        require(partial["log_updated"] is False, partial)
        require(partial["writes_memory"] is True, partial)

        accepted = audit(root, partial["receipt"])
        require(accepted["receipt_valid"] is True, accepted)
        require(accepted["store_state"] == "index_applied_log_pending", accepted)
        require(accepted["status"] == "retry_reconciliation", accepted)

    print("all RelayMEM M3h receipt invariant smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
