from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
from hashlib import sha256
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm._relaymem_primary_page_writer_common import stable_hash
from relaylm.relaymem_primary_index_log_reconciliation import (
    build_relaymem_primary_index_log_reconciliation_preflight,
)


def require(condition: bool, value: object) -> None:
    if not condition:
        raise AssertionError(value)


def fixture(root: Path) -> tuple[dict[str, object], Path, Path, Path]:
    candidate_id = "candidate-1"
    namespace = "character-main"
    event_kind = "turn"
    memory_kind = "recent_project_event"
    target_category = "primary_projects"
    lineage = sha256(b"lineage").hexdigest()
    key = stable_hash((
        "relaymem-primary-write-preflight-v0",
        namespace,
        event_kind,
        lineage,
        candidate_id,
        event_kind,
        "primary",
        memory_kind,
        "free_to_update",
    ))
    summary = "RelayMEM M3f smoke summary."
    metadata = [
        ("summary", summary),
        ("schema_version", "relaymem.primary_page.v0"),
        ("memory_layer", "primary"),
        ("memory_kind", memory_kind),
        ("source_event_kind", event_kind),
        ("promotion_policy", "free_to_update"),
        ("safety_scope", "ordinary_memory"),
        ("namespace", namespace),
        ("lineage_fingerprint", lineage),
        ("idempotency_key", key),
        ("summary_origin", "trusted_in_process_summary"),
        ("content_role", "evidence"),
        ("title", "M3f smoke"),
    ]
    page = "---\n" + "\n".join(
        f"{field}: {json.dumps(value, ensure_ascii=False)}" for field, value in metadata
    ) + f"\n---\n# Primary memory\n\n## Summary\n\n{summary}\n"
    page_bytes = page.encode("utf-8")
    relative = f"memory/mem/primary/projects/{key}.md"
    page_path = root / relative
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_bytes(page_bytes)
    index_path = root / "memory/mem/index.md"
    log_path = root / "memory/mem/log.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("# Index\n", encoding="utf-8")
    log_path.write_text("# Log\n", encoding="utf-8")
    receipt: dict[str, object] = {
        "schema_version": "relaymem.primary_page_write_receipt.v0",
        "runtime_private": True,
        "content_included": False,
        "candidate_id": candidate_id,
        "namespace": namespace,
        "source_event_kind": event_kind,
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "target_category": target_category,
        "target_relative_path": relative,
        "lineage_fingerprint": lineage,
        "idempotency_key": key,
        "page_bytes": len(page_bytes),
        "page_digest": sha256(page_bytes).hexdigest(),
        "status": "applied",
        "writes_memory": True,
        "page_applied": True,
        "idempotent_noop": False,
        "durability_confirmed": True,
        "cleanup_complete": True,
        "updates_index": False,
        "updates_log": False,
    }
    return receipt, page_path, index_path, log_path


def preflight(root: Path, receipt: dict[str, object]) -> dict[str, object]:
    return build_relaymem_primary_index_log_reconciliation_preflight(
        receipt=receipt,
        root_path=str(root),
        enabled=True,
        dry_run_only=True,
    )


def main() -> int:
    disabled = build_relaymem_primary_index_log_reconciliation_preflight(
        receipt=None, root_path=None
    )
    require(disabled["status"] == "blocked", disabled)
    require("primary_reconciliation_disabled" in disabled["blocked_reasons"], disabled)
    print("ok default-off fails closed")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        receipt, page_path, index_path, log_path = fixture(root)

        initial_index = index_path.read_bytes()
        initial_log = log_path.read_bytes()
        first = preflight(root, receipt)
        require(first["status"] == "index_and_log_update_required", first)
        require(first["page_verified"] is True, first)
        require(first["index_update_required"] is True, first)
        require(first["log_update_required"] is True, first)
        plan = first["plan"]
        require(plan["operation_count"] == 2, plan)
        require(plan["index_plan"]["proposed_next_content"].count(receipt["namespace"]) == 1, plan)
        require(plan["log_plan"]["proposed_next_content"].count(receipt["lineage_fingerprint"]) == 1, plan)
        require(index_path.read_bytes() == initial_index, first)
        require(log_path.read_bytes() == initial_log, first)
        require(
            [item["operation_kind"] for item in plan["ordered_operations"]]
            == ["append_index_entry", "append_log_entry"],
            plan,
        )
        projection_text = json.dumps(first["projection"], sort_keys=True)
        for secret in (
            str(root),
            receipt["candidate_id"],
            receipt["namespace"],
            receipt["idempotency_key"],
            receipt["page_digest"],
            receipt["target_relative_path"],
        ):
            require(str(secret) not in projection_text, first["projection"])
        print("ok page verification yields ordered content-free reconciliation plan")

        non_dry = build_relaymem_primary_index_log_reconciliation_preflight(
            receipt=receipt, root_path=str(root), enabled=True, dry_run_only=False
        )
        require(non_dry["status"] == "blocked", non_dry)
        require("primary_reconciliation_dry_run_required" in non_dry["blocked_reasons"], non_dry)
        print("ok non-dry-run request is rejected")

        index_path.write_text(plan["index_plan"]["proposed_next_content"], encoding="utf-8")
        index_only = preflight(root, receipt)
        require(index_only["status"] == "log_update_required", index_only)
        require(index_only["index_update_required"] is False, index_only)
        require(index_only["log_update_required"] is True, index_only)
        print("ok index-only state plans log append")

        index_path.write_text("# Index\n", encoding="utf-8")
        log_path.write_text(plan["log_plan"]["proposed_next_content"], encoding="utf-8")
        log_only = preflight(root, receipt)
        require(log_only["status"] == "index_update_required", log_only)
        require(log_only["index_update_required"] is True, log_only)
        require(log_only["log_update_required"] is False, log_only)
        print("ok exact log-only state is repairable from verified page")

        index_path.write_text(plan["index_plan"]["proposed_next_content"], encoding="utf-8")
        both = preflight(root, receipt)
        require(both["status"] == "already_reconciled", both)
        require(both["plan"]["operation_count"] == 0, both)
        print("ok repeated run is deterministic no-op")

        already = copy.deepcopy(receipt)
        already.update(
            status="already_applied",
            writes_memory=False,
            page_applied=False,
            idempotent_noop=True,
            durability_confirmed=False,
        )
        already_result = preflight(root, already)
        require(already_result["status"] == "already_reconciled", already_result)
        require(already_result["page_verified"] is True, already_result)
        print("ok already-applied receipt becomes eligible only after page revalidation")

        index_text = index_path.read_text(encoding="utf-8")
        index_path.write_text(index_text.replace(receipt["page_digest"], "0" * 64), encoding="utf-8")
        conflict = preflight(root, receipt)
        require(conflict["status"] == "index_conflict", conflict)
        require(conflict["projection"]["conflict_counts"]["index"] == 1, conflict)
        print("ok conflicting deterministic index identity fails closed")

        index_path.write_text(plan["index_plan"]["proposed_next_content"], encoding="utf-8")
        log_text = plan["log_plan"]["proposed_next_content"]
        log_path.write_text(
            log_text.replace(receipt["page_digest"], "1" * 64), encoding="utf-8"
        )
        log_conflict = preflight(root, receipt)
        require(log_conflict["status"] == "log_conflict", log_conflict)
        require(log_conflict["projection"]["conflict_counts"]["log"] == 1, log_conflict)
        print("ok conflicting deterministic log identity fails closed")

        index_path.write_text(
            "# Index\n<!-- relaymem-primary-index-entry-v0 not-json -->\n",
            encoding="utf-8",
        )
        malformed = preflight(root, receipt)
        require(malformed["status"] == "index_conflict", malformed)
        print("ok malformed index marker fails closed")

        index_path.write_text(
            plan["index_plan"]["proposed_next_content"]
            + plan["index_plan"]["proposed_next_content"].splitlines()[-1]
            + "\n",
            encoding="utf-8",
        )
        duplicate = preflight(root, receipt)
        require(duplicate["status"] == "index_conflict", duplicate)
        print("ok duplicate exact identity fails closed")

        fixture(root)
        index_path.unlink()
        missing_index = preflight(root, receipt)
        require(missing_index["status"] == "blocked", missing_index)
        require(
            "primary_reconciliation_index_file_missing"
            in missing_index["blocked_reasons"],
            missing_index,
        )
        fixture(root)
        log_path.unlink()
        missing_log = preflight(root, receipt)
        require(missing_log["status"] == "blocked", missing_log)
        require(
            "primary_reconciliation_log_file_missing" in missing_log["blocked_reasons"],
            missing_log,
        )
        print("ok missing index and log control files fail closed")

        fixture(root)
        page_path.unlink()
        missing = preflight(root, receipt)
        require(missing["status"] == "page_missing", missing)
        print("ok missing page is distinct")

        _, page_path, _, _ = fixture(root)
        page_path.write_text("wrong", encoding="utf-8")
        mismatch = preflight(root, receipt)
        require(mismatch["status"] == "page_mismatch", mismatch)
        print("ok page bytes and digest are revalidated")

        fixture(root)
        extra = copy.deepcopy(receipt)
        extra["unexpected"] = True
        blocked = preflight(root, extra)
        require(blocked["status"] == "blocked", blocked)
        require("primary_reconciliation_receipt_fields_mismatch" in blocked["blocked_reasons"], blocked)

        bool_bytes = copy.deepcopy(receipt)
        bool_bytes["page_bytes"] = True
        blocked_bool = preflight(root, bool_bytes)
        require("primary_reconciliation_receipt_page_bytes_invalid" in blocked_bool["blocked_reasons"], blocked_bool)

        non_hashable_event = copy.deepcopy(receipt)
        non_hashable_event["source_event_kind"] = ["turn"]
        blocked_event = preflight(root, non_hashable_event)
        require(
            "primary_reconciliation_receipt_source_event_kind_invalid"
            in blocked_event["blocked_reasons"],
            blocked_event,
        )
        non_hashable_kind = copy.deepcopy(receipt)
        non_hashable_kind["memory_kind"] = ["recent_project_event"]
        blocked_kind = preflight(root, non_hashable_kind)
        require(
            "primary_reconciliation_receipt_memory_kind_invalid"
            in blocked_kind["blocked_reasons"],
            blocked_kind,
        )
        non_hashable_category = copy.deepcopy(receipt)
        non_hashable_category["target_category"] = ["primary_projects"]
        blocked_category = preflight(root, non_hashable_category)
        require(
            "primary_reconciliation_receipt_target_category_invalid"
            in blocked_category["blocked_reasons"],
            blocked_category,
        )
        invalid_bool = copy.deepcopy(receipt)
        invalid_bool["cleanup_complete"] = 1
        blocked_bool_field = preflight(root, invalid_bool)
        require(
            "primary_reconciliation_receipt_cleanup_complete_invalid"
            in blocked_bool_field["blocked_reasons"],
            blocked_bool_field,
        )
        traversing = copy.deepcopy(receipt)
        traversing["target_relative_path"] = "../memory/mem/index.md"
        blocked_path = preflight(root, traversing)
        require(
            "primary_reconciliation_receipt_target_path_invalid"
            in blocked_path["blocked_reasons"],
            blocked_path,
        )
        print("ok exact fields, strict types, enums, and paths fail closed")

        fixture(root)
        index_path.write_bytes(b"x" * 65537)
        oversized = preflight(root, receipt)
        require(
            "primary_reconciliation_index_size_exceeded"
            in oversized["blocked_reasons"],
            oversized,
        )
        print("ok bounded control-file reads fail closed")

        if hasattr(os, "symlink"):
            fixture(root)
            outside = root / "outside.md"
            outside.write_text("# Index\n", encoding="utf-8")
            index_path.unlink()
            try:
                index_path.symlink_to(outside)
            except OSError:
                print("ok index symlink smoke skipped")
            else:
                symlinked = preflight(root, receipt)
                require(
                    "primary_reconciliation_index_symlink_blocked"
                    in symlinked["blocked_reasons"],
                    symlinked,
                )
                print("ok index symlink is rejected")

            fixture(root)
            outside_page = root / "outside-page.md"
            outside_page.write_bytes(page_path.read_bytes())
            page_path.unlink()
            try:
                page_path.symlink_to(outside_page)
            except OSError:
                print("ok page symlink smoke skipped")
            else:
                page_symlinked = preflight(root, receipt)
                require(page_symlinked["status"] == "page_mismatch", page_symlinked)
                require(
                    "primary_reconciliation_page_symlink_blocked"
                    in page_symlinked["blocked_reasons"],
                    page_symlinked,
                )
                print("ok page symlink is rejected")

    print("all RelayMEM M3f reconciliation preflight smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
