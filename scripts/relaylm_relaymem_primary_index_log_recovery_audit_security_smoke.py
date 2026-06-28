from __future__ import annotations

import copy
import fcntl
import os
import sys
import tempfile
from hashlib import sha256
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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


def audit(root: Path, receipt: dict[str, object]) -> dict[str, object]:
    return audit_relaymem_primary_index_log_reconciliation_recovery(
        receipt=receipt, root_path=str(root), enabled=True, dry_run_only=True
    )


def apply_plan(root: Path, plan: dict[str, object]) -> dict[str, object]:
    return apply_relaymem_primary_index_log_reconciliation(
        plan_artifact=plan,
        root_path=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        page_receipt, page_path, index_path, _ = fixture(root)
        plan = fresh_plan(root, page_receipt)
        applied = apply_plan(root, plan)
        receipt = applied["receipt"]

        invalid_gate = audit_relaymem_primary_index_log_reconciliation_recovery(
            receipt=receipt, root_path=str(root), enabled=True, dry_run_only=False
        )
        require(invalid_gate["status"] == "blocked", invalid_gate)

        extra = copy.deepcopy(receipt)
        extra["unexpected"] = True
        exact = audit(root, extra)
        require(exact["status"] == "blocked", exact)
        require(exact["receipt_valid"] is False, exact)

        traversal = copy.deepcopy(receipt)
        traversal["page_relative_path"] = "../outside.md"
        blocked = audit(root, traversal)
        require(blocked["status"] == "blocked", blocked)

        forged_page = page_path.read_text(encoding="utf-8").replace(
            'summary_origin: "trusted_in_process_summary"',
            'summary_origin: "assistant_output"',
        )
        page_path.write_text(forged_page, encoding="utf-8")
        forged_receipt = copy.deepcopy(receipt)
        forged_receipt["page_digest"] = sha256(forged_page.encode("utf-8")).hexdigest()
        forged = audit(root, forged_receipt)
        require(forged["status"] == "blocked", forged)
        require(forged["receipt_valid"] is True, forged)
        require(forged["page_verified"] is False, forged)
        require(
            "primary_reconciliation_recovery_page_summary_origin_mismatch"
            in forged["blocked_reasons"],
            forged,
        )

        page_path.write_bytes(page_receipt["page_digest"].encode("utf-8"))

        lock_fd = os.open(root / "memory/mem", os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            contention = audit(root, receipt)
            require(contention["status"] == "blocked", contention)
            require(
                "primary_reconciliation_recovery_lock_unavailable"
                in contention["blocked_reasons"],
                contention,
            )
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

        index_path.unlink()
        index_path.symlink_to(root / "memory/mem/log.md")
        symlink = audit(root, receipt)
        require(symlink["status"] == "blocked", symlink)
        require(symlink["writes_memory"] is False, symlink)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        page_receipt, _, index_path, _ = fixture(root)
        initial_plan = fresh_plan(root, page_receipt)
        index_path.write_text(
            initial_plan["index_plan"]["proposed_next_content"], encoding="utf-8"
        )
        log_only_plan = fresh_plan(root, page_receipt)
        require(
            log_only_plan["reconciliation_state"] == "log_update_required",
            log_only_plan,
        )
        log_only_applied = apply_plan(root, log_only_plan)
        require(log_only_applied["status"] == "applied", log_only_applied)

        forged = copy.deepcopy(log_only_applied["receipt"])
        forged["index_updated"] = True
        forged["updates_index"] = True
        forged["index_idempotent_noop"] = False
        forged["writes_memory"] = True
        rejected = audit(root, forged)
        require(rejected["status"] == "blocked", rejected)
        require(rejected["receipt_valid"] is False, rejected)
        require(
            "primary_reconciliation_recovery_receipt_index_update_not_planned"
            in rejected["blocked_reasons"],
            rejected,
        )

    print("all RelayMEM M3h recovery audit security smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
