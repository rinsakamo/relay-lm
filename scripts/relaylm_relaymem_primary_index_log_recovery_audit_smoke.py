from __future__ import annotations

import copy
import json
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
    disabled = audit_relaymem_primary_index_log_reconciliation_recovery(
        receipt=None, root_path=None
    )
    require(disabled["status"] == "disabled", disabled)
    require(disabled["writes_memory"] is False, disabled)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        page_receipt, page_path, index_path, log_path = fixture(root)
        plan = fresh_plan(root, page_receipt)
        applied = apply_plan(root, plan)
        require(applied["status"] == "applied", applied)
        before = (page_path.read_bytes(), index_path.read_bytes(), log_path.read_bytes())

        complete = audit(root, applied["receipt"])
        require(complete["status"] == "recovery_not_required", complete)
        require(complete["store_state"] == "fully_reconciled", complete)
        require(
            before == (page_path.read_bytes(), index_path.read_bytes(), log_path.read_bytes()),
            complete,
        )

        projection_text = json.dumps(complete["projection"], sort_keys=True)
        for private_value in (
            str(root),
            page_receipt["namespace"],
            applied["receipt"]["idempotency_key"],
            applied["receipt"]["page_relative_path"],
            applied["receipt"]["page_digest"],
        ):
            require(str(private_value) not in projection_text, complete["projection"])

        repeated = apply_plan(root, plan)
        require(repeated["status"] == "already_applied", repeated)
        require(repeated["writes_memory"] is False, repeated)
        require(repeated["durability_confirmed"] is True, repeated)
        repeated_audit = audit(root, repeated["receipt"])
        require(repeated_audit["receipt_valid"] is True, repeated_audit)
        require(repeated_audit["status"] == "recovery_not_required", repeated_audit)
        require(repeated_audit["store_state"] == "fully_reconciled", repeated_audit)

        original_confirm = apply_io._confirm_control_durability

        def fail_durability(*args: object, **kwargs: object) -> None:
            raise OSError("injected final durability failure")

        apply_io._confirm_control_durability = fail_durability
        try:
            no_write_uncertain = apply_plan(root, plan)
        finally:
            apply_io._confirm_control_durability = original_confirm

        require(
            no_write_uncertain["status"] == "applied_durability_unconfirmed",
            no_write_uncertain,
        )
        require(no_write_uncertain["writes_memory"] is False, no_write_uncertain)
        durability = audit(root, no_write_uncertain["receipt"])
        require(durability["receipt_valid"] is True, durability)
        require(durability["status"] == "manual_confirmation_required", durability)
        require(durability["store_state"] == "fully_reconciled", durability)

        uncertain = copy.deepcopy(applied["receipt"])
        uncertain["status"] = "applied_durability_unconfirmed"
        uncertain["durability_confirmed"] = False
        durability_after_write = audit(root, uncertain)
        require(
            durability_after_write["status"] == "manual_confirmation_required",
            durability_after_write,
        )
        require(
            durability_after_write["store_state"] == "fully_reconciled",
            durability_after_write,
        )

    print("all RelayMEM M3h recovery audit functional smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
