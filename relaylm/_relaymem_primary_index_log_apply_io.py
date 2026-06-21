"""Secure ordered atomic control-file apply for RelayMEM M3g."""
from __future__ import annotations

import errno
import json
import os
import secrets
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX-only apply boundary
    fcntl = None  # type: ignore[assignment]

from ._relaymem_primary_index_log_reconciliation_io import (
    _open_directory_parts,
    _open_root_directory,
    _read_regular_file,
)
from ._relaymem_primary_index_log_reconciliation_plan import (
    MAX_INDEX_LOG_BYTES,
    _parse_markers,
    _valid_existing_entry,
)


def apply_or_inspect_reconciliation(
    *, root_path: str | None, plan: Mapping[str, Any], apply_requested: bool
) -> dict[str, Any]:
    state = empty_reconciliation_apply_state()
    if fcntl is None:
        state["blocked_reasons"] = ["primary_reconciliation_apply_platform_unsupported"]
        return state
    root = _open_root_directory(root_path)
    if root.get("valid") is not True:
        state["blocked_reasons"] = list(root.get("blocked_reasons", []))
        return state
    root_fd = root["fd"]
    mem_fd = -1
    locked = False
    try:
        directory = _open_directory_parts(root_fd, ("memory", "mem"), "control")
        if directory.get("valid") is not True:
            state["blocked_reasons"] = list(directory.get("blocked_reasons", []))
            return state
        mem_fd = directory["fd"]
        try:
            fcntl.flock(mem_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except (BlockingIOError, OSError):
            state["blocked_reasons"] = ["primary_reconciliation_apply_lock_unavailable"]
            return state

        index_check = _inspect_control(mem_fd, "index.md", plan["index_plan"], "index")
        log_check = _inspect_control(mem_fd, "log.md", plan["log_plan"], "log")
        if index_check["status"] == "invalid":
            state["blocked_reasons"].extend(index_check["blocked_reasons"])
        if log_check["status"] == "invalid":
            state["blocked_reasons"].extend(log_check["blocked_reasons"])
        if state["blocked_reasons"]:
            return state

        state["index_reconciled"] = index_check["status"] == "proposed"
        state["log_reconciled"] = log_check["status"] == "proposed"
        state["index_idempotent_noop"] = state["index_reconciled"]
        state["log_idempotent_noop"] = state["log_reconciled"]

        allowed = {"expected", "proposed"}
        if index_check["status"] not in allowed:
            state["blocked_reasons"].append("primary_reconciliation_apply_index_conflict")
        if log_check["status"] not in allowed:
            state["blocked_reasons"].append("primary_reconciliation_apply_log_conflict")
        if state["blocked_reasons"]:
            return state

        if not apply_requested:
            state["receipt_status"] = (
                "already_applied"
                if state["index_reconciled"] and state["log_reconciled"]
                else "resume_ready"
                if state["index_reconciled"] and not state["log_reconciled"]
                else "dry_run_ready"
            )
            return state

        for operation in plan["ordered_operations"]:
            role = (
                "index"
                if operation["operation_kind"] == "append_index_entry"
                else "log"
            )
            if role == "log" and not state["index_reconciled"]:
                state["blocked_reasons"].append(
                    "primary_reconciliation_apply_index_not_reconciled_before_log"
                )
                state["receipt_status"] = "index_applied_log_pending"
                return state
            filename = "index.md" if role == "index" else "log.md"
            control_plan = plan[f"{role}_plan"]
            current = _inspect_control(mem_fd, filename, control_plan, role)
            if current["status"] == "proposed":
                state[f"{role}_reconciled"] = True
                state[f"{role}_idempotent_noop"] = True
                continue
            if current["status"] != "expected":
                state["blocked_reasons"].extend(
                    current.get("blocked_reasons", [])
                    or [f"primary_reconciliation_apply_{role}_conflict"]
                )
                if role == "log" and state["index_reconciled"]:
                    state["receipt_status"] = "index_applied_log_pending"
                return state

            outcome = _atomic_replace_control(
                parent_fd=mem_fd,
                filename=filename,
                control_plan=control_plan,
                role=role,
            )
            state["cleanup_complete"] = (
                state["cleanup_complete"] and outcome["cleanup_complete"]
            )
            state["writes_memory"] = state["writes_memory"] or outcome["wrote"]
            state[f"{role}_updated"] = outcome["wrote"]
            state[f"{role}_idempotent_noop"] = outcome["idempotent_noop"]
            state[f"{role}_reconciled"] = outcome["reconciled"]
            if outcome["status"] not in {"applied", "already_applied"}:
                state["blocked_reasons"].extend(outcome["blocked_reasons"])
                state["receipt_status"] = _partial_status(
                    role=role,
                    outcome_status=outcome["status"],
                    index_reconciled=state["index_reconciled"],
                )
                return state

        final_index = _inspect_control(mem_fd, "index.md", plan["index_plan"], "index")
        final_log = _inspect_control(mem_fd, "log.md", plan["log_plan"], "log")
        state["index_reconciled"] = final_index["status"] == "proposed"
        state["log_reconciled"] = final_log["status"] == "proposed"
        if not state["index_reconciled"] or not state["log_reconciled"]:
            state["receipt_status"] = "applied_state_uncertain"
            state["blocked_reasons"].append(
                "primary_reconciliation_apply_final_state_mismatch"
            )
            return state
        try:
            _confirm_control_durability(mem_fd, "index.md")
            _confirm_control_durability(mem_fd, "log.md")
            os.fsync(mem_fd)
        except OSError:
            state["receipt_status"] = "applied_durability_unconfirmed"
            state["blocked_reasons"].append(
                "primary_reconciliation_apply_durability_confirmation_failed"
            )
            return state
        final_index = _inspect_control(mem_fd, "index.md", plan["index_plan"], "index")
        final_log = _inspect_control(mem_fd, "log.md", plan["log_plan"], "log")
        if final_index["status"] != "proposed" or final_log["status"] != "proposed":
            state["receipt_status"] = "applied_state_uncertain"
            state["blocked_reasons"].append(
                "primary_reconciliation_apply_post_fsync_state_mismatch"
            )
            return state
        state["durability_confirmed"] = True
        state["receipt_status"] = (
            "applied" if state["writes_memory"] else "already_applied"
        )
        return state
    finally:
        if locked and mem_fd >= 0:
            try:
                fcntl.flock(mem_fd, fcntl.LOCK_UN)
            except OSError:
                pass
        if mem_fd >= 0:
            os.close(mem_fd)
        os.close(root_fd)


def _inspect_control(
    parent_fd: int, filename: str, control_plan: Mapping[str, Any], role: str
) -> dict[str, Any]:
    read = _read_regular_file(parent_fd, filename, MAX_INDEX_LOG_BYTES, role)
    if read.get("valid") is not True:
        return {
            "status": "invalid",
            "blocked_reasons": list(read.get("blocked_reasons", [])),
        }
    content = read["content"]
    if (
        len(content) == control_plan["proposed_next_bytes"]
        and sha256(content).hexdigest() == control_plan["proposed_next_digest"]
        and content.decode("utf-8") == control_plan["proposed_next_content"]
    ):
        return {"status": "proposed", "blocked_reasons": []}
    if (
        len(content) == control_plan["expected_current_bytes"]
        and sha256(content).hexdigest() == control_plan["expected_current_digest"]
    ):
        transition_reasons = _append_transition_reasons(
            current=content, control_plan=control_plan, role=role
        )
        if transition_reasons:
            return {"status": "invalid", "blocked_reasons": transition_reasons}
        return {"status": "expected", "blocked_reasons": []}
    return {"status": "conflict", "blocked_reasons": []}


def _append_transition_reasons(
    *, current: bytes, control_plan: Mapping[str, Any], role: str
) -> list[str]:
    if control_plan["idempotent_noop"] is True:
        return [f"primary_reconciliation_apply_{role}_noop_current_mismatch"]
    marker = f"relaymem-primary-{role}-entry-v0"
    header = "# Index" if role == "index" else "# Log"
    current_parsed = _parse_markers(current, marker, header)
    if current_parsed.get("valid") is not True or any(
        not _valid_existing_entry(marker, entry)
        for entry in current_parsed.get("entries", [])
    ):
        return [f"primary_reconciliation_apply_{role}_current_contract_invalid"]
    proposed = str(control_plan["proposed_next_content"]).encode("utf-8")
    proposed_parsed = _parse_markers(proposed, marker, header)
    if proposed_parsed.get("valid") is not True:
        return [f"primary_reconciliation_apply_{role}_append_transition_invalid"]
    matches = [
        entry
        for entry in proposed_parsed["entries"]
        if entry.get("entry_id") == control_plan["entry_identity"]
    ]
    if len(matches) != 1:
        return [f"primary_reconciliation_apply_{role}_append_transition_invalid"]
    serialized = json.dumps(
        matches[0], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    suffix = f"<!-- {marker} {serialized} -->\n".encode("utf-8")
    expected = current
    if expected and not expected.endswith(b"\n"):
        expected += b"\n"
    expected += suffix
    if proposed != expected:
        return [f"primary_reconciliation_apply_{role}_append_transition_invalid"]
    return []


def _atomic_replace_control(
    *,
    parent_fd: int,
    filename: str,
    control_plan: Mapping[str, Any],
    role: str,
) -> dict[str, Any]:
    result = {
        "status": "blocked",
        "wrote": False,
        "reconciled": False,
        "idempotent_noop": False,
        "cleanup_complete": True,
        "blocked_reasons": [],
    }
    entry_identity = str(control_plan["entry_identity"])
    temp_name = f".relaymem-reconcile-{entry_identity}-{secrets.token_hex(8)}.tmp"
    temp_created = False
    replaced = False
    temp_fd = -1
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    data = str(control_plan["proposed_next_content"]).encode("utf-8")
    try:
        temp_fd = os.open(temp_name, flags, 0o600, dir_fd=parent_fd)
        temp_created = True
        offset = 0
        while offset < len(data):
            written = os.write(temp_fd, data[offset:])
            if written <= 0:
                raise OSError(errno.EIO, "short write")
            offset += written
        os.fsync(temp_fd)
        info = os.fstat(temp_fd)
        if (
            info.st_size != control_plan["proposed_next_bytes"]
            or sha256(data).hexdigest() != control_plan["proposed_next_digest"]
        ):
            result["blocked_reasons"] = [
                f"primary_reconciliation_apply_{role}_temp_mismatch"
            ]
            return result
        os.close(temp_fd)
        temp_fd = -1

        current = _inspect_control(parent_fd, filename, control_plan, role)
        if current["status"] == "proposed":
            result.update(
                status="already_applied",
                reconciled=True,
                idempotent_noop=True,
            )
            return result
        if current["status"] != "expected":
            result["blocked_reasons"] = current.get("blocked_reasons", []) or [
                f"primary_reconciliation_apply_{role}_precondition_changed"
            ]
            return result

        os.replace(temp_name, filename, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        temp_created = False
        replaced = True
        result["wrote"] = True
        final = _inspect_control(parent_fd, filename, control_plan, role)
        if final["status"] != "proposed":
            result.update(
                status="state_uncertain",
                blocked_reasons=[
                    f"primary_reconciliation_apply_{role}_published_state_mismatch"
                ],
            )
            return result
        try:
            os.fsync(parent_fd)
        except OSError:
            result.update(
                status="durability_unconfirmed",
                reconciled=True,
                blocked_reasons=[
                    f"primary_reconciliation_apply_{role}_directory_fsync_failed"
                ],
            )
            return result
        result.update(status="applied", reconciled=True)
        return result
    except OSError:
        if replaced:
            final = _inspect_control(parent_fd, filename, control_plan, role)
            if final["status"] == "proposed":
                result.update(
                    status="durability_unconfirmed",
                    wrote=True,
                    reconciled=True,
                    blocked_reasons=[
                        f"primary_reconciliation_apply_{role}_post_replace_failed"
                    ],
                )
            else:
                result.update(
                    status="state_uncertain",
                    wrote=True,
                    blocked_reasons=[
                        f"primary_reconciliation_apply_{role}_state_uncertain"
                    ],
                )
        else:
            result["blocked_reasons"] = [
                f"primary_reconciliation_apply_{role}_replace_failed"
            ]
        return result
    finally:
        if temp_fd >= 0:
            try:
                os.close(temp_fd)
            except OSError:
                pass
        if temp_created:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except OSError:
                result["cleanup_complete"] = False
                if not result["blocked_reasons"]:
                    result["blocked_reasons"] = [
                        f"primary_reconciliation_apply_{role}_temp_cleanup_failed"
                    ]
                if result["status"] in {"applied", "already_applied"}:
                    result["status"] = "cleanup_incomplete"


def _confirm_control_durability(parent_fd: int, filename: str) -> None:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    fd = os.open(filename, flags, dir_fd=parent_fd)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _partial_status(*, role: str, outcome_status: str, index_reconciled: bool) -> str:
    if outcome_status == "durability_unconfirmed":
        return "applied_durability_unconfirmed"
    if outcome_status == "cleanup_incomplete":
        return "applied_cleanup_incomplete"
    if outcome_status == "state_uncertain":
        return "applied_state_uncertain"
    if role == "log" and index_reconciled:
        return "index_applied_log_pending"
    return "blocked"


def empty_reconciliation_apply_state() -> dict[str, Any]:
    return {
        "receipt_status": "",
        "writes_memory": False,
        "index_reconciled": False,
        "log_reconciled": False,
        "index_updated": False,
        "log_updated": False,
        "index_idempotent_noop": False,
        "log_idempotent_noop": False,
        "durability_confirmed": False,
        "cleanup_complete": True,
        "blocked_reasons": [],
    }


__all__ = ["apply_or_inspect_reconciliation", "empty_reconciliation_apply_state"]
