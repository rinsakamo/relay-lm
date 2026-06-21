"""Read-only RelayMEM file-store dry-run diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import _relaymem_store_impl as _impl


discover_relaymem_page_candidates = _impl.discover_relaymem_page_candidates
build_relaymem_snippet_evidence_dry_run = _impl.build_relaymem_snippet_evidence_dry_run


def build_relaymem_store_diagnostics(
    *,
    root_path: str | None,
    store_enabled: bool,
    retrieval_dry_run_only: bool,
) -> dict[str, Any]:
    """Inspect the store while reserving validation capacity for MEM pages."""

    diagnostics: dict[str, Any] = {
        "schema_version": "relaymem.store_diagnostics.v0",
        "diagnostics_only": True,
        "read_only": True,
        "store_enabled": bool(store_enabled),
        "retrieval_dry_run_only": bool(retrieval_dry_run_only),
        "root_path": root_path,
        "root_present": False,
        "layout": _impl._layout(root_path),
        "layout_compatibility": _impl._empty_layout_compatibility(),
        "index_present": False,
        "log_present": False,
        "pages_discovered": 0,
        "page_paths": [],
        "blocked_files": [],
        "fallback_reason": None,
        "validation": {
            "max_files_to_scan": _impl._MAX_FILES_TO_SCAN,
            "max_files_to_validate": _impl._MAX_FILES_TO_VALIDATE,
            "max_sample_bytes": _impl._MAX_SAMPLE_BYTES,
            "files_seen": 0,
            "files_validated": 0,
            "scan_truncated": False,
            "validation_truncated": False,
            "full_tree_materialized": False,
            "full_file_reads": False,
        },
    }

    if not store_enabled:
        diagnostics["fallback_reason"] = "memory_store_disabled"
        return diagnostics
    if not root_path:
        diagnostics["fallback_reason"] = "memory_store_root_not_configured"
        return diagnostics

    root = Path(root_path)
    diagnostics["root_path"] = str(root)
    if not root.exists() or not root.is_dir():
        diagnostics["fallback_reason"] = "memory_store_root_missing"
        return diagnostics

    diagnostics["root_present"] = True
    diagnostics["layout_compatibility"] = _impl._layout_compatibility(root)
    diagnostics["index_present"] = (root / "memory" / "mem" / "index.md").is_file()
    diagnostics["log_present"] = (root / "memory" / "mem" / "log.md").is_file()

    page_paths: list[str] = []
    blocked_files: list[dict[str, str]] = []
    mem_files: list[tuple[Path, str]] = []
    other_files: list[tuple[Path, str]] = []
    files_seen = 0
    files_validated = 0
    scan_truncated = False

    for file_path in _impl._iter_store_files(root):
        if files_seen >= _impl._MAX_FILES_TO_SCAN:
            scan_truncated = True
            break
        files_seen += 1
        relative = file_path.relative_to(root).as_posix()
        if not _impl._is_supported_file(relative, file_path.suffix):
            blocked_files.append({"path": relative, "reason": "unsupported_file_type"})
            continue
        target = mem_files if relative.startswith("memory/mem/") else other_files
        target.append((file_path, relative))

    supported_files = mem_files + other_files
    validation_truncated = len(supported_files) > _impl._MAX_FILES_TO_VALIDATE
    for file_path, relative in supported_files[: _impl._MAX_FILES_TO_VALIDATE]:
        validation_result = _impl._validate_file_sample(file_path)
        files_validated += 1
        if validation_result is not None:
            blocked_files.append({"path": relative, "reason": validation_result})
            continue
        if relative.startswith("memory/mem/") and file_path.suffix == ".md":
            page_paths.append(relative)

    diagnostics["validation"] = {
        "max_files_to_scan": _impl._MAX_FILES_TO_SCAN,
        "max_files_to_validate": _impl._MAX_FILES_TO_VALIDATE,
        "max_sample_bytes": _impl._MAX_SAMPLE_BYTES,
        "files_seen": files_seen,
        "files_validated": files_validated,
        "scan_truncated": scan_truncated,
        "validation_truncated": validation_truncated,
        "full_tree_materialized": False,
        "full_file_reads": False,
    }
    diagnostics["page_paths"] = sorted(page_paths)
    diagnostics["pages_discovered"] = len(page_paths)
    diagnostics["blocked_files"] = blocked_files
    if blocked_files:
        diagnostics["fallback_reason"] = "memory_store_files_blocked"
    elif scan_truncated:
        diagnostics["fallback_reason"] = "memory_store_scan_truncated"
    elif validation_truncated:
        diagnostics["fallback_reason"] = "memory_store_validation_truncated"
    elif not diagnostics["index_present"]:
        diagnostics["fallback_reason"] = "memory_store_index_missing"
    else:
        diagnostics["fallback_reason"] = "memory_store_read_only_dry_run"
    return diagnostics


__all__ = [
    "discover_relaymem_page_candidates",
    "build_relaymem_snippet_evidence_dry_run",
    "build_relaymem_store_diagnostics",
]
