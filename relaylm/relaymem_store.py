"""Read-only RelayMEM file-store dry-run diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_LAYOUT_DIRS = (
    "memory/raw",
    "memory/mem/projects",
    "memory/mem/concepts",
    "memory/mem/summaries",
    "memory/mem/relations",
)
_LAYOUT_FILES = (
    "memory/mem/index.md",
    "memory/mem/log.md",
)
_ALLOWED_SUFFIXES = {
    "memory/raw": {".jsonl", ".md"},
    "memory/mem": {".md"},
}


def build_relaymem_store_diagnostics(
    *,
    root_path: str | None,
    store_enabled: bool,
    retrieval_dry_run_only: bool,
) -> dict[str, Any]:
    """Inspect the RelayMEM file-backed store layout without writing to it."""

    diagnostics: dict[str, Any] = {
        "schema_version": "relaymem.store_diagnostics.v0",
        "diagnostics_only": True,
        "read_only": True,
        "store_enabled": bool(store_enabled),
        "retrieval_dry_run_only": bool(retrieval_dry_run_only),
        "root_path": root_path,
        "root_present": False,
        "layout": _layout(root_path),
        "index_present": False,
        "log_present": False,
        "pages_discovered": 0,
        "page_paths": [],
        "blocked_files": [],
        "fallback_reason": None,
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
    index_path = root / "memory" / "mem" / "index.md"
    log_path = root / "memory" / "mem" / "log.md"
    diagnostics["index_present"] = index_path.is_file()
    diagnostics["log_present"] = log_path.is_file()

    page_paths: list[str] = []
    blocked_files: list[dict[str, str]] = []
    for file_path in _iter_store_files(root):
        relative = file_path.relative_to(root).as_posix()
        if not _is_supported_file(relative, file_path.suffix):
            blocked_files.append({"path": relative, "reason": "unsupported_file_type"})
            continue
        try:
            file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            blocked_files.append({"path": relative, "reason": "malformed_or_unreadable_file"})
            continue
        if relative.startswith("memory/mem/") and file_path.suffix == ".md":
            page_paths.append(relative)

    diagnostics["page_paths"] = sorted(page_paths)
    diagnostics["pages_discovered"] = len(page_paths)
    diagnostics["blocked_files"] = blocked_files
    if blocked_files:
        diagnostics["fallback_reason"] = "memory_store_files_blocked"
    elif not diagnostics["index_present"]:
        diagnostics["fallback_reason"] = "memory_store_index_missing"
    else:
        diagnostics["fallback_reason"] = "memory_store_read_only_dry_run"
    return diagnostics


def _layout(root_path: str | None) -> dict[str, list[str]]:
    root = Path(root_path) if root_path else Path(".")
    return {
        "directories": [(root / item).as_posix() for item in _LAYOUT_DIRS],
        "files": [(root / item).as_posix() for item in _LAYOUT_FILES],
    }


def _iter_store_files(root: Path) -> list[Path]:
    memory_root = root / "memory"
    if not memory_root.exists() or not memory_root.is_dir():
        return []
    return [path for path in memory_root.rglob("*") if path.is_file()]


def _is_supported_file(relative_path: str, suffix: str) -> bool:
    if relative_path.startswith("memory/raw/"):
        return suffix in _ALLOWED_SUFFIXES["memory/raw"]
    if relative_path.startswith("memory/mem/"):
        return suffix in _ALLOWED_SUFFIXES["memory/mem"]
    return False
