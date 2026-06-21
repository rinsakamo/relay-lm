from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm import _relaymem_primary_index_log_apply_io as apply_io
from relaylm._relaymem_primary_index_log_apply_contract import (
    parse_m3f_reconciliation_plan,
    verify_m3g_page,
)
from relaylm.relaymem_primary_index_log_apply import (
    apply_relaymem_primary_index_log_reconciliation,
)
from scripts.relaylm_relaymem_primary_index_log_apply_smoke import (
    apply_plan,
    fresh_plan,
)
from scripts.relaylm_relaymem_primary_index_log_reconciliation_smoke import (
    fixture,
    require,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        receipt, _, index_path, _ = fixture(root)
        plan = fresh_plan(root, receipt)

        cases: list[tuple[str, dict[str, object], str]] = []

        bool_count = copy.deepcopy(plan)
        bool_count["operation_count"] = True
        cases.append(("strict operation count", bool_count, "operation_count_invalid"))

        extra_nested = copy.deepcopy(plan)
        extra_nested["index_plan"]["unexpected"] = True
        cases.append(("exact nested fields", extra_nested, "index_plan_fields_mismatch"))

        forged_digest = copy.deepcopy(plan)
        forged_digest["index_plan"]["proposed_next_digest"] = "0" * 64
        cases.append(("proposed digest", forged_digest, "proposed_digest_mismatch"))

        forged_identity = copy.deepcopy(plan)
        forged_identity["index_plan"]["entry_identity"] = "1" * 64
        cases.append(("entry identity", forged_identity, "entry_count_invalid"))

        bad_target = copy.deepcopy(plan)
        bad_target["index_plan"]["target_relative_path"] = "../index.md"
        cases.append(("target traversal", bad_target, "index_target_path_invalid"))

        noncanonical = copy.deepcopy(plan)
        index_content = noncanonical["index_plan"]["proposed_next_content"]
        marker_line = next(
            line
            for line in index_content.splitlines()
            if "relaymem-primary-index-entry-v0" in line
        )
        prefix = "<!-- relaymem-primary-index-entry-v0 "
        entry = json.loads(marker_line[len(prefix) : -4])
        noncanonical_line = (
            "<!-- relaymem-primary-index-entry-v0 "
            + json.dumps(entry, ensure_ascii=False)
            + " -->"
        )
        changed = index_content.replace(marker_line, noncanonical_line)
        changed_bytes = changed.encode("utf-8")
        changed_digest = hashlib.sha256(changed_bytes).hexdigest()
        noncanonical["index_plan"]["proposed_next_content"] = changed
        noncanonical["index_plan"]["proposed_next_bytes"] = len(changed_bytes)
        noncanonical["index_plan"]["proposed_next_digest"] = changed_digest
        noncanonical["ordered_operations"][0]["proposed_next_content"] = changed
        noncanonical["ordered_operations"][0]["proposed_next_bytes"] = len(
            changed_bytes
        )
        noncanonical["ordered_operations"][0]["proposed_next_digest"] = changed_digest
        cases.append(("canonical marker", noncanonical, "content_contract_invalid"))

        surrogate = copy.deepcopy(plan)
        surrogate["index_plan"]["proposed_next_content"] = "\ud800"
        surrogate["ordered_operations"][0]["proposed_next_content"] = "\ud800"
        cases.append(("UTF-8 surrogate", surrogate, "content_utf8_invalid"))

        empty_noop = copy.deepcopy(plan)
        empty_noop["reconciliation_state"] = "already_reconciled"
        empty_noop["ordered_operations"] = []
        empty_noop["operation_count"] = 0
        empty_digest = hashlib.sha256(b"").hexdigest()
        for role in ("index", "log"):
            control = empty_noop[f"{role}_plan"]
            control["proposed_next_content"] = ""
            control["proposed_next_bytes"] = 0
            control["proposed_next_digest"] = empty_digest
            control["expected_current_bytes"] = 0
            control["expected_current_digest"] = empty_digest
            control["idempotent_noop"] = True
        cases.append(("empty no-op content", empty_noop, "content_contract_invalid"))

        for label, candidate, reason_fragment in cases:
            result = apply_plan(root, candidate)
            require(result["status"] == "blocked", (label, result))
            require(result["writes_memory"] is False, (label, result))
            require(
                any(reason_fragment in reason for reason in result["blocked_reasons"]),
                (label, result),
            )
        require(index_path.read_text(encoding="utf-8") == "# Index\n", index_path)
        print("ok exact nested plan contract fails closed without mutation")

        append_violation = copy.deepcopy(plan)
        original = append_violation["index_plan"]["proposed_next_content"]
        changed = original.replace("# Index\n", "# Index\nrewritten content\n", 1)
        changed_bytes = changed.encode("utf-8")
        changed_digest = hashlib.sha256(changed_bytes).hexdigest()
        append_violation["index_plan"]["proposed_next_content"] = changed
        append_violation["index_plan"]["proposed_next_bytes"] = len(changed_bytes)
        append_violation["index_plan"]["proposed_next_digest"] = changed_digest
        append_violation["ordered_operations"][0]["proposed_next_content"] = changed
        append_violation["ordered_operations"][0]["proposed_next_bytes"] = len(changed_bytes)
        append_violation["ordered_operations"][0]["proposed_next_digest"] = changed_digest
        append_result = apply_plan(root, append_violation)
        require(append_result["status"] == "blocked", append_result)
        require(append_result["writes_memory"] is False, append_result)
        require(
            "primary_reconciliation_apply_index_append_transition_invalid"
            in append_result["blocked_reasons"],
            append_result,
        )
        require(index_path.read_text(encoding="utf-8") == "# Index\n", index_path)
        print("ok proposed control content must be an exact append transition")

        page_bytes = (root / receipt["target_relative_path"]).read_bytes()
        page_plan = dict(plan["page"])
        index_content = plan["index_plan"]["proposed_next_content"]
        log_content = plan["log_plan"]["proposed_next_content"]
        index_line = next(
            line for line in index_content.splitlines()
            if "relaymem-primary-index-entry-v0" in line
        )
        log_line = next(
            line for line in log_content.splitlines()
            if "relaymem-primary-log-entry-v0" in line
        )
        index_entry = json.loads(
            index_line[len("<!-- relaymem-primary-index-entry-v0 ") : -4]
        )
        log_entry = json.loads(
            log_line[len("<!-- relaymem-primary-log-entry-v0 ") : -4]
        )
        mismatched_page = page_bytes.decode("utf-8").replace(
            'namespace: "character-main"',
            'namespace: "different-character"',
            1,
        ).encode("utf-8")
        page_plan["page_bytes"] = len(mismatched_page)
        page_plan["page_digest"] = hashlib.sha256(mismatched_page).hexdigest()
        page_reasons = verify_m3g_page(
            page_plan,
            mismatched_page,
            index_entry=index_entry,
            log_entry=log_entry,
        )
        require(
            "primary_reconciliation_apply_page_namespace_mismatch" in page_reasons,
            page_reasons,
        )
        print("ok page namespace and lineage remain bound to control entries")

        no_op_with_invalid_unrelated = copy.deepcopy(plan)
        no_op_with_invalid_unrelated["reconciliation_state"] = "already_reconciled"
        no_op_with_invalid_unrelated["ordered_operations"] = []
        no_op_with_invalid_unrelated["operation_count"] = 0
        for role in ("index", "log"):
            control = no_op_with_invalid_unrelated[f"{role}_plan"]
            control["expected_current_bytes"] = control["proposed_next_bytes"]
            control["expected_current_digest"] = control["proposed_next_digest"]
            control["idempotent_noop"] = True
        unrelated = copy.deepcopy(index_entry)
        unrelated["idempotency_key"] = "2" * 64
        unrelated["page_digest"] = "3" * 64
        unrelated["page_relative_path"] = (
            f"memory/mem/primary/projects/{'2' * 64}.md"
        )
        unrelated["entry_id"] = "4" * 64
        unrelated_line = (
            "<!-- relaymem-primary-index-entry-v0 "
            + json.dumps(
                unrelated,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + " -->\n"
        )
        control = no_op_with_invalid_unrelated["index_plan"]
        malformed_content = control["proposed_next_content"] + unrelated_line
        malformed_bytes = malformed_content.encode("utf-8")
        malformed_digest = hashlib.sha256(malformed_bytes).hexdigest()
        control["proposed_next_content"] = malformed_content
        control["proposed_next_bytes"] = len(malformed_bytes)
        control["proposed_next_digest"] = malformed_digest
        control["expected_current_bytes"] = len(malformed_bytes)
        control["expected_current_digest"] = malformed_digest
        invalid_noop = parse_m3f_reconciliation_plan(no_op_with_invalid_unrelated)
        require(invalid_noop["valid"] is False, invalid_noop)
        require(
            "primary_reconciliation_apply_index_content_entry_invalid"
            in invalid_noop["blocked_reasons"],
            invalid_noop,
        )
        print("ok no-op plans validate every existing marker entry")

        invalid_enabled = apply_relaymem_primary_index_log_reconciliation(
            plan_artifact=plan,
            root_path=str(root),
            enabled=1,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(invalid_enabled["status"] == "blocked", invalid_enabled)
        require(invalid_enabled["writes_memory"] is False, invalid_enabled)
        print("ok invalid enabled gate is blocked rather than treated as disabled")

        original_replace = apply_io.os.replace
        original_fsync = apply_io.os.fsync

        def fail_replace(*args: object, **kwargs: object) -> None:
            raise OSError("injected replace failure")

        def fail_directory_fsync(fd: int) -> None:
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError("injected cleanup directory fsync failure")
            original_fsync(fd)

        apply_io.os.replace = fail_replace
        apply_io.os.fsync = fail_directory_fsync
        try:
            cleanup_failure = apply_plan(root, plan)
        finally:
            apply_io.os.replace = original_replace
            apply_io.os.fsync = original_fsync
        require(cleanup_failure["status"] == "blocked", cleanup_failure)
        require(cleanup_failure["cleanup_complete"] is False, cleanup_failure)
        require(cleanup_failure["writes_memory"] is False, cleanup_failure)
        require(
            not any(
                path.name.startswith(".relaymem-reconcile-")
                for path in (root / "memory/mem").iterdir()
            ),
            cleanup_failure,
        )
        print("ok temp cleanup requires directory fsync confirmation")

        mem_dir = root / "memory/mem"
        lock_fd = os.open(mem_dir, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = apply_plan(root, plan)
            require(locked["status"] == "blocked", locked)
            require(
                "primary_reconciliation_apply_lock_unavailable"
                in locked["blocked_reasons"],
                locked,
            )
            require(locked["writes_memory"] is False, locked)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
        print("ok concurrent RelayMEM writer lock fails closed")

        receipt, _, _, _ = fixture(root)
        plan = fresh_plan(root, receipt)
        primary_dir = root / "memory/mem/primary"
        outside_dir = root / "outside-primary"
        primary_dir.rename(outside_dir)
        try:
            primary_dir.symlink_to(outside_dir, target_is_directory=True)
        except OSError:
            print("ok directory symlink smoke skipped")
        else:
            directory_symlink = apply_plan(root, plan)
            require(directory_symlink["status"] == "blocked", directory_symlink)
            require(directory_symlink["writes_memory"] is False, directory_symlink)
            require(
                any("symlink" in reason for reason in directory_symlink["blocked_reasons"]),
                directory_symlink,
            )
            print("ok page-directory symlink substitution is rejected")

    print("all RelayMEM M3g reconciliation apply security smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
