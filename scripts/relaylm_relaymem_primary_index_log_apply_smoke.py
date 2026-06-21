from __future__ import annotations

import copy
import json
import os
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
from scripts.relaylm_relaymem_primary_index_log_reconciliation_smoke import (
    fixture,
    preflight,
    require,
)


def apply_plan(
    root: Path,
    plan: dict[str, object],
    *,
    dry_run_only: bool = False,
    apply_enabled: bool = True,
) -> dict[str, object]:
    return apply_relaymem_primary_index_log_reconciliation(
        plan_artifact=plan,
        root_path=str(root),
        enabled=True,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
    )


def fresh_plan(root: Path, receipt: dict[str, object]) -> dict[str, object]:
    result = preflight(root, receipt)
    require(result["plan"] is not None, result)
    return result["plan"]


def main() -> int:
    disabled = apply_relaymem_primary_index_log_reconciliation(
        plan_artifact=None,
        root_path=None,
    )
    require(disabled["status"] == "disabled", disabled)
    require(disabled["writes_memory"] is False, disabled)
    print("ok default-off apply boundary is inert")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        receipt, page_path, index_path, log_path = fixture(root)
        plan = fresh_plan(root, receipt)
        require(plan["reconciliation_state"] == "index_and_log_update_required", plan)

        invalid_dry = apply_relaymem_primary_index_log_reconciliation(
            plan_artifact=plan,
            root_path=str(root),
            enabled=True,
            dry_run_only=1,
            apply_enabled=True,
        )
        require(invalid_dry["status"] == "blocked", invalid_dry)
        require(invalid_dry["writes_memory"] is False, invalid_dry)
        invalid_apply = apply_relaymem_primary_index_log_reconciliation(
            plan_artifact=plan,
            root_path=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=1,
        )
        require(invalid_apply["status"] == "blocked", invalid_apply)
        require(invalid_apply["writes_memory"] is False, invalid_apply)
        print("ok non-boolean apply gates fail closed")

        before_index = index_path.read_bytes()
        before_log = log_path.read_bytes()
        dry = apply_plan(root, plan, dry_run_only=True, apply_enabled=False)
        require(dry["status"] == "dry_run_ready", dry)
        require(dry["writes_memory"] is False, dry)
        require(index_path.read_bytes() == before_index, dry)
        require(log_path.read_bytes() == before_log, dry)
        print("ok dry-run validates without mutation")

        applied = apply_plan(root, plan)
        require(applied["status"] == "applied", applied)
        require(applied["index_updated"] is True, applied)
        require(applied["log_updated"] is True, applied)
        require(applied["index_reconciled"] is True, applied)
        require(applied["log_reconciled"] is True, applied)
        require(applied["durability_confirmed"] is True, applied)
        require(
            index_path.read_text(encoding="utf-8")
            == plan["index_plan"]["proposed_next_content"],
            applied,
        )
        require(
            log_path.read_text(encoding="utf-8")
            == plan["log_plan"]["proposed_next_content"],
            applied,
        )
        require(applied["receipt"]["status"] == "applied", applied)
        projection_text = json.dumps(applied["projection"], sort_keys=True)
        for secret in (
            str(root),
            receipt["namespace"],
            receipt["idempotency_key"],
            receipt["page_digest"],
            receipt["target_relative_path"],
            plan["index_plan"]["entry_identity"],
        ):
            require(str(secret) not in projection_text, applied["projection"])
        print("ok ordered index then log apply is durable and projection-safe")

        repeated = apply_plan(root, plan)
        require(repeated["status"] == "already_applied", repeated)
        require(repeated["writes_memory"] is False, repeated)
        require(repeated["index_idempotent_noop"] is True, repeated)
        require(repeated["log_idempotent_noop"] is True, repeated)
        print("ok exact plan retry is idempotent")

        receipt, _, index_path, log_path = fixture(root)
        plan = fresh_plan(root, receipt)
        original_replace = apply_io.os.replace
        replace_calls = 0

        def fail_second_replace(*args: object, **kwargs: object) -> None:
            nonlocal replace_calls
            replace_calls += 1
            if replace_calls == 2:
                raise OSError("injected log replace failure")
            original_replace(*args, **kwargs)

        apply_io.os.replace = fail_second_replace
        try:
            partial = apply_plan(root, plan)
        finally:
            apply_io.os.replace = original_replace
        require(partial["status"] == "index_applied_log_pending", partial)
        require(partial["index_reconciled"] is True, partial)
        require(partial["log_reconciled"] is False, partial)
        require(partial["index_updated"] is True, partial)
        require(partial["log_updated"] is False, partial)
        require(
            index_path.read_text(encoding="utf-8")
            == plan["index_plan"]["proposed_next_content"],
            partial,
        )
        require(log_path.read_text(encoding="utf-8") == "# Log\n", partial)
        resumed = apply_plan(root, plan)
        require(resumed["status"] == "applied", resumed)
        require(resumed["index_idempotent_noop"] is True, resumed)
        require(resumed["log_updated"] is True, resumed)
        print("ok interrupted two-file apply resumes from exact same plan")

        receipt, _, index_path, log_path = fixture(root)
        base_plan = fresh_plan(root, receipt)
        index_path.write_text(
            base_plan["index_plan"]["proposed_next_content"], encoding="utf-8"
        )
        log_only_plan = fresh_plan(root, receipt)
        require(
            log_only_plan["reconciliation_state"] == "log_update_required",
            log_only_plan,
        )
        log_only = apply_plan(root, log_only_plan)
        require(log_only["status"] == "applied", log_only)
        require(log_only["index_updated"] is False, log_only)
        require(log_only["log_updated"] is True, log_only)

        receipt, _, index_path, log_path = fixture(root)
        base_plan = fresh_plan(root, receipt)
        log_path.write_text(
            base_plan["log_plan"]["proposed_next_content"], encoding="utf-8"
        )
        index_only_plan = fresh_plan(root, receipt)
        require(
            index_only_plan["reconciliation_state"] == "index_update_required",
            index_only_plan,
        )
        index_only = apply_plan(root, index_only_plan)
        require(index_only["status"] == "applied", index_only)
        require(index_only["index_updated"] is True, index_only)
        require(index_only["log_updated"] is False, index_only)
        print("ok fresh index-only and log-only plans apply independently")

        receipt, _, index_path, log_path = fixture(root)
        base_plan = fresh_plan(root, receipt)
        index_path.write_text(
            base_plan["index_plan"]["proposed_next_content"], encoding="utf-8"
        )
        log_path.write_text(
            base_plan["log_plan"]["proposed_next_content"], encoding="utf-8"
        )
        noop_plan = fresh_plan(root, receipt)
        require(
            noop_plan["reconciliation_state"] == "already_reconciled", noop_plan
        )
        noop = apply_plan(root, noop_plan)
        require(noop["status"] == "already_applied", noop)
        require(noop["writes_memory"] is False, noop)
        print("ok zero-operation reconciled plan remains a durable no-op")

        receipt, page_path, index_path, _ = fixture(root)
        plan = fresh_plan(root, receipt)
        index_path.write_text("# Index\nexternal change\n", encoding="utf-8")
        conflict = apply_plan(root, plan)
        require(conflict["status"] == "blocked", conflict)
        require(
            "primary_reconciliation_apply_index_conflict"
            in conflict["blocked_reasons"],
            conflict,
        )
        require(conflict["writes_memory"] is False, conflict)
        print("ok changed current digest blocks apply without overwrite")

        fixture(root)
        page_path.unlink()
        missing_page = apply_plan(root, plan)
        require(missing_page["status"] == "blocked", missing_page)
        require(
            "primary_reconciliation_apply_page_missing"
            in missing_page["blocked_reasons"],
            missing_page,
        )

        receipt, page_path, _, _ = fixture(root)
        plan = fresh_plan(root, receipt)
        page_path.write_text("wrong", encoding="utf-8")
        bad_page = apply_plan(root, plan)
        require(bad_page["status"] == "blocked", bad_page)
        require(bad_page["writes_memory"] is False, bad_page)
        print("ok page is revalidated immediately before control-file apply")

        receipt, _, index_path, _ = fixture(root)
        plan = fresh_plan(root, receipt)
        extra = copy.deepcopy(plan)
        extra["unexpected"] = True
        bad_plan = apply_plan(root, extra)
        require(bad_plan["status"] == "blocked", bad_plan)
        require(
            "primary_reconciliation_apply_plan_fields_mismatch"
            in bad_plan["blocked_reasons"],
            bad_plan,
        )
        reversed_plan = copy.deepcopy(plan)
        reversed_plan["ordered_operations"] = list(
            reversed(reversed_plan["ordered_operations"])
        )
        bad_order = apply_plan(root, reversed_plan)
        require(bad_order["status"] == "blocked", bad_order)
        require(bad_order["writes_memory"] is False, bad_order)
        print("ok exact plan fields and index-before-log ordering are enforced")

        if hasattr(os, "symlink"):
            outside = root / "outside-index.md"
            outside.write_text("# Index\n", encoding="utf-8")
            index_path.unlink()
            try:
                index_path.symlink_to(outside)
            except OSError:
                print("ok control-file symlink smoke skipped")
            else:
                symlinked = apply_plan(root, plan)
                require(symlinked["status"] == "blocked", symlinked)
                require(
                    "primary_reconciliation_index_symlink_blocked"
                    in symlinked["blocked_reasons"],
                    symlinked,
                )
                print("ok control-file symlink is rejected")

    print("all RelayMEM M3g reconciliation apply smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
