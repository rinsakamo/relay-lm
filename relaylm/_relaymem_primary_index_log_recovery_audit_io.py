"""Secure bounded read-only store audit for RelayMEM M3h."""
from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from .portable_lock import acquire_portable_lock, release_portable_lock
from ._relaymem_primary_index_log_reconciliation_io import (
    _open_directory_parts,
    _open_root_directory,
    _read_regular_file,
)
from ._relaymem_primary_index_log_reconciliation_plan import MAX_INDEX_LOG_BYTES
from ._relaymem_primary_index_log_recovery_audit_io_cleanup import (
    inspect_cleanup_artifacts,
)
from ._relaymem_primary_index_log_recovery_audit_io_control import (
    apply_control_result,
    cross_validate_entries,
    derive_store_state,
)
from ._relaymem_primary_index_log_recovery_audit_io_page import apply_page_result
from ._relaymem_primary_page_writer_common import MAX_PAGE_BYTES


def inspect_reconciliation_recovery_store(
    *, root_path: str | None, receipt: Mapping[str, Any]
) -> dict[str, Any]:
    state = empty_recovery_store_state()
    root = _open_root_directory(root_path)
    if root.get("valid") is not True:
        state["blocked_reasons"] = list(root.get("blocked_reasons", []))
        return state
    root_fd = root["fd"]
    mem_fd = -1
    page_parent_fd = -1
    locked = False
    try:
        mem = _open_directory_parts(root_fd, ("memory", "mem"), "control")
        if mem.get("valid") is not True:
            state["blocked_reasons"] = list(mem.get("blocked_reasons", []))
            return state
        mem_fd = mem["fd"]
        try:
            acquire_portable_lock(mem_fd, mode="shared", blocking=False)
            locked = True
        except OSError:
            state["blocked_reasons"] = ["primary_reconciliation_recovery_lock_unavailable"]
            return state

        page_parts = PurePosixPath(receipt["page_relative_path"]).parts
        page_parent = _open_directory_parts(root_fd, page_parts[:-1], "page")
        if page_parent.get("valid") is not True:
            state["page_state"] = "missing" if any(
                "missing" in reason for reason in page_parent.get("blocked_reasons", [])
            ) else "invalid"
            state["blocked_reasons"].extend(page_parent.get("blocked_reasons", []))
        else:
            page_parent_fd = page_parent["fd"]
            page = _read_regular_file(page_parent_fd, page_parts[-1], MAX_PAGE_BYTES, "page")
            apply_page_result(state, page, receipt)

        index = _read_regular_file(mem_fd, "index.md", MAX_INDEX_LOG_BYTES, "index")
        log = _read_regular_file(mem_fd, "log.md", MAX_INDEX_LOG_BYTES, "log")
        apply_control_result(state, index, receipt, "index")
        apply_control_result(state, log, receipt, "log")
        cross_validate_entries(state)
        inspect_cleanup_artifacts(state, mem_fd, receipt)
        state["store_state"] = derive_store_state(state)
        return state
    finally:
        if locked and mem_fd >= 0:
            try:
                release_portable_lock(mem_fd)
            except OSError:
                pass
        if page_parent_fd >= 0:
            os.close(page_parent_fd)
        if mem_fd >= 0:
            os.close(mem_fd)
        os.close(root_fd)


def empty_recovery_store_state() -> dict[str, Any]:
    return {
        "page_state": "not_checked",
        "index_state": "not_checked",
        "log_state": "not_checked",
        "store_state": "not_evaluated",
        "page_metadata": None,
        "index_entry": None,
        "log_entry": None,
        "cleanup_artifact_count": 0,
        "cleanup_artifacts_present": False,
        "blocked_reasons": [],
    }


__all__ = ["empty_recovery_store_state", "inspect_reconciliation_recovery_store"]
