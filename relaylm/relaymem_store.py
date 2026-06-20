"""Read-only RelayMEM file-store dry-run diagnostics."""

from __future__ import annotations

import codecs
from collections.abc import Iterator
from pathlib import Path
from typing import Any

_CURRENT_LAYOUT_DIRS = (
    "memory/raw",
    "memory/mem/projects",
    "memory/mem/concepts",
    "memory/mem/summaries",
    "memory/mem/relations",
)
_TARGET_SOURCE_DIRS = (
    "memory/sources/conversations",
    "memory/sources/communications",
    "memory/sources/corrections",
)
_TARGET_MEM_LAYOUT_DIRS = (
    "memory/mem/primary/sessions",
    "memory/mem/primary/scenes",
    "memory/mem/primary/relationships",
    "memory/mem/primary/projects",
    "memory/mem/secondary/projects",
    "memory/mem/secondary/concepts",
    "memory/mem/secondary/claims",
    "memory/mem/secondary/summaries",
    "memory/mem/secondary/relations",
)
_TARGET_LAYOUT_DIRS = _TARGET_SOURCE_DIRS + _TARGET_MEM_LAYOUT_DIRS
_LAYOUT_DIRS = _CURRENT_LAYOUT_DIRS + _TARGET_LAYOUT_DIRS
_LAYOUT_FILES = (
    "memory/mem/index.md",
    "memory/mem/log.md",
)
_ALLOWED_SUFFIXES = {
    "memory/raw": {".jsonl", ".md"},
    "memory/sources": {".jsonl", ".md"},
    "memory/mem": {".md"},
}
_MAX_FILES_TO_VALIDATE = 64
_MAX_FILES_TO_SCAN = 128
_MAX_SAMPLE_BYTES = 4096


_CANDIDATE_DIRS = (
    "memory/mem/projects",
    "memory/mem/concepts",
    "memory/mem/summaries",
    "memory/mem/primary/sessions",
    "memory/mem/primary/scenes",
    "memory/mem/primary/relationships",
    "memory/mem/primary/projects",
    "memory/mem/secondary/projects",
    "memory/mem/secondary/concepts",
    "memory/mem/secondary/claims",
    "memory/mem/secondary/summaries",
    "memory/mem/secondary/relations",
)
_DEFAULT_MAX_CANDIDATES = 8
_DEFAULT_MAX_CANDIDATE_READ_BYTES = 4096
_DEFAULT_MAX_CANDIDATE_SCAN = 128
_SNIPPET_DIRS = (
    "memory/mem/projects",
    "memory/mem/concepts",
    "memory/mem/summaries",
    "memory/mem/primary/sessions",
    "memory/mem/primary/scenes",
    "memory/mem/primary/relationships",
    "memory/mem/primary/projects",
    "memory/mem/secondary/projects",
    "memory/mem/secondary/concepts",
    "memory/mem/secondary/claims",
    "memory/mem/secondary/summaries",
    "memory/mem/secondary/relations",
)
_DEFAULT_MAX_SNIPPET_CHARS = 512
_DEFAULT_MAX_SNIPPET_CANDIDATES = 3
_DEFAULT_MAX_SNIPPET_READ_BYTES = 4096


def discover_relaymem_page_candidates(
    *,
    root_path: str | None,
    query_terms: list[str] | None = None,
    max_candidates: int = _DEFAULT_MAX_CANDIDATES,
    max_read_bytes: int = _DEFAULT_MAX_CANDIDATE_READ_BYTES,
    max_scan: int = _DEFAULT_MAX_CANDIDATE_SCAN,
) -> dict[str, Any]:
    """Discover MEM page candidates without writing or building ctx blocks.

    Candidate discovery is bounded because this can run from the request path
    when the store is enabled.
    """

    max_candidates = max(0, int(max_candidates))
    max_read_bytes = max(1, int(max_read_bytes))
    max_scan = max(0, int(max_scan))
    result: dict[str, Any] = {
        "schema_version": "relaymem.page_candidates.v0",
        "diagnostics_only": True,
        "read_only": True,
        "root_path": root_path,
        "max_candidates": max_candidates,
        "max_read_bytes": max_read_bytes,
        "max_scan": max_scan,
        "index_summary": None,
        "candidates": [],
        "blocked_files": [],
        "fallback_reason": None,
        "candidate_scan_seen": 0,
        "candidate_scan_truncated": False,
        "candidate_cap_reached": False,
        "full_candidate_tree_materialized": False,
    }
    if not root_path:
        result["fallback_reason"] = "memory_store_root_not_configured"
        return result

    root = Path(root_path)
    if not root.exists() or not root.is_dir():
        result["fallback_reason"] = "memory_store_root_missing"
        return result

    result["index_summary"] = _read_index_summary(root, max_read_bytes)
    query_terms = [term.lower() for term in (query_terms or []) if term]
    candidates: list[dict[str, Any]] = []
    blocked_files: list[dict[str, str]] = []
    scan_seen = 0
    scan_truncated = False
    candidate_cap_reached = False

    for file_path in _iter_candidate_page_files(root):
        if scan_seen >= max_scan:
            scan_truncated = True
            break
        scan_seen += 1
        relative = file_path.relative_to(root).as_posix()
        if len(candidates) >= max_candidates:
            candidate_cap_reached = True
        if file_path.is_symlink():
            blocked_files.append({"path": relative, "reason": "symlink_blocked"})
            continue
        try:
            sample = _read_text_sample(file_path, max_read_bytes)
        except (UnicodeDecodeError, OSError):
            blocked_files.append(
                {"path": relative, "reason": "malformed_or_unreadable_file"}
            )
            continue
        if len(candidates) >= max_candidates:
            candidate_cap_reached = True
            continue
        reason = _selection_reason(relative, sample, query_terms)
        candidates.append(
            {
                "path": relative,
                "source": "mem_page",
                "reason": reason,
                "estimated_chars": len(sample),
                "memory_layer": _memory_layer_for_path(relative),
                "layout_profile": _layout_profile_for_path(relative),
                "applied_to_ctx": False,
            }
        )

    result["candidate_scan_seen"] = scan_seen
    result["candidate_scan_truncated"] = scan_truncated
    result["candidate_cap_reached"] = candidate_cap_reached or (
        max_candidates > 0
        and len(candidates) >= max_candidates
        and scan_seen > len(candidates)
    )
    result["candidates"] = candidates
    result["blocked_files"] = blocked_files
    if blocked_files:
        result["fallback_reason"] = "memory_store_files_blocked"
    elif scan_truncated:
        result["fallback_reason"] = "memory_store_candidate_scan_truncated"
    elif candidate_cap_reached:
        result["fallback_reason"] = "memory_store_candidate_cap_reached"
    elif not candidates:
        result["fallback_reason"] = "memory_store_no_candidate_pages"
    else:
        result["fallback_reason"] = "memory_store_read_only_selection_dry_run"
    return result


def build_relaymem_snippet_evidence_dry_run(
    *,
    root_path: str | None,
    selected_mem_candidates: list[dict[str, Any]] | None,
    snippet_extraction_enabled: bool,
    snippet_dry_run_only: bool,
    max_snippet_chars: int = _DEFAULT_MAX_SNIPPET_CHARS,
    max_snippet_candidates: int = _DEFAULT_MAX_SNIPPET_CANDIDATES,
    max_read_bytes: int = _DEFAULT_MAX_SNIPPET_READ_BYTES,
) -> dict[str, Any]:
    """Build bounded MEM page snippet diagnostics without prompt injection."""

    max_snippet_chars = max(1, int(max_snippet_chars))
    max_snippet_candidates = max(0, int(max_snippet_candidates))
    max_read_bytes = max(1, int(max_read_bytes))
    result: dict[str, Any] = {
        "schema_version": "relaymem.snippet_evidence_dry_run.v0",
        "diagnostics_only": True,
        "read_only": True,
        "snippet_extraction_enabled": bool(snippet_extraction_enabled),
        "snippet_dry_run_only": bool(snippet_dry_run_only),
        "root_path": root_path,
        "max_snippet_chars": max_snippet_chars,
        "max_snippet_candidates": max_snippet_candidates,
        "max_read_bytes": max_read_bytes,
        "snippet_candidates": [],
        "evidence_envelope": {
            "schema_version": "relaymem.evidence_envelope.v0",
            "diagnostics_only": True,
            "applied_to_ctx": False,
            "source": "selected_mem_candidates",
            "snippets": [],
            "blocked": [],
        },
    }
    envelope = result["evidence_envelope"]
    if not snippet_extraction_enabled:
        return result
    if not root_path:
        envelope["blocked"].append({"reason": "memory_store_root_not_configured"})
        return result
    root = Path(root_path)
    if not root.exists() or not root.is_dir():
        envelope["blocked"].append({"reason": "memory_store_root_missing"})
        return result

    candidates = selected_mem_candidates or []
    for selected_index, candidate in enumerate(candidates[:max_snippet_candidates]):
        if not isinstance(candidate, dict):
            continue
        evidence_id = f"evidence:{selected_index}"
        relative = str(candidate.get("path", ""))
        source = str(candidate.get("source", "mem_page"))
        blocked_reason = _snippet_path_block_reason(root, relative)
        if blocked_reason is not None:
            envelope["blocked"].append(
                {
                    "evidence_id": evidence_id,
                    "selected_index": selected_index,
                    "path": relative,
                    "reason": blocked_reason,
                }
            )
            continue
        file_path = root / relative
        try:
            snippet = _read_bounded_snippet(file_path, max_read_bytes, max_snippet_chars)
        except UnicodeDecodeError:
            envelope["blocked"].append(
                {
                    "evidence_id": evidence_id,
                    "selected_index": selected_index,
                    "path": relative,
                    "reason": "malformed_utf8",
                }
            )
            continue
        except OSError:
            envelope["blocked"].append(
                {
                    "evidence_id": evidence_id,
                    "selected_index": selected_index,
                    "path": relative,
                    "reason": "unreadable_file",
                }
            )
            continue
        except ValueError as exc:
            envelope["blocked"].append(
                {
                    "evidence_id": evidence_id,
                    "selected_index": selected_index,
                    "path": relative,
                    "reason": str(exc),
                }
            )
            continue
        estimated_tokens = max(1, len(snippet) // 4) if snippet else 0
        snippet_candidate = {
            "evidence_id": evidence_id,
            "selected_index": selected_index,
            "path": relative,
            "source": source,
            "evidence_kind": "bounded_page_snippet",
            "snippet_text": snippet,
            "snippet_chars": len(snippet),
            "estimated_tokens": estimated_tokens,
            "memory_layer": _memory_layer_for_path(relative),
            "layout_profile": _layout_profile_for_path(relative),
            "applied_to_ctx": False,
            "safe_for_prompt_preview": False,
            "blocked_reasons": [],
        }
        result["snippet_candidates"].append(snippet_candidate)
        envelope["snippets"].append(
            {
                "evidence_id": evidence_id,
                "selected_index": selected_index,
                "path": relative,
                "evidence_kind": "bounded_page_snippet",
                "snippet_chars": len(snippet),
                "estimated_tokens": estimated_tokens,
                "memory_layer": _memory_layer_for_path(relative),
                "layout_profile": _layout_profile_for_path(relative),
                "content_included_in_runtime_prompt": False,
            }
        )
    if len(candidates) > max_snippet_candidates:
        envelope["blocked"].append({"reason": "snippet_candidate_cap_reached"})
    return result


def build_relaymem_store_diagnostics(
    *,
    root_path: str | None,
    store_enabled: bool,
    retrieval_dry_run_only: bool,
) -> dict[str, Any]:
    """Inspect the RelayMEM file-backed store layout without writing to it.

    The runtime dry-run path intentionally streams only a bounded sample of the
    store. It must not materialize or read the full memory tree on every request.
    """

    diagnostics: dict[str, Any] = {
        "schema_version": "relaymem.store_diagnostics.v0",
        "diagnostics_only": True,
        "read_only": True,
        "store_enabled": bool(store_enabled),
        "retrieval_dry_run_only": bool(retrieval_dry_run_only),
        "root_path": root_path,
        "root_present": False,
        "layout": _layout(root_path),
        "layout_compatibility": _empty_layout_compatibility(),
        "index_present": False,
        "log_present": False,
        "pages_discovered": 0,
        "page_paths": [],
        "blocked_files": [],
        "fallback_reason": None,
        "validation": {
            "max_files_to_scan": _MAX_FILES_TO_SCAN,
            "max_files_to_validate": _MAX_FILES_TO_VALIDATE,
            "max_sample_bytes": _MAX_SAMPLE_BYTES,
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
    diagnostics["layout_compatibility"] = _layout_compatibility(root)
    index_path = root / "memory" / "mem" / "index.md"
    log_path = root / "memory" / "mem" / "log.md"
    diagnostics["index_present"] = index_path.is_file()
    diagnostics["log_present"] = log_path.is_file()

    page_paths: list[str] = []
    blocked_files: list[dict[str, str]] = []
    files_seen = 0
    files_validated = 0
    scan_truncated = False
    validation_truncated = False

    for file_path in _iter_store_files(root):
        if files_seen >= _MAX_FILES_TO_SCAN:
            scan_truncated = True
            break
        files_seen += 1
        relative = file_path.relative_to(root).as_posix()
        if not _is_supported_file(relative, file_path.suffix):
            blocked_files.append({"path": relative, "reason": "unsupported_file_type"})
            continue
        if files_validated >= _MAX_FILES_TO_VALIDATE:
            validation_truncated = True
            continue
        validation_result = _validate_file_sample(file_path)
        files_validated += 1
        if validation_result is not None:
            blocked_files.append({"path": relative, "reason": validation_result})
            continue
        if relative.startswith("memory/mem/") and file_path.suffix == ".md":
            page_paths.append(relative)

    diagnostics["validation"] = {
        "max_files_to_scan": _MAX_FILES_TO_SCAN,
        "max_files_to_validate": _MAX_FILES_TO_VALIDATE,
        "max_sample_bytes": _MAX_SAMPLE_BYTES,
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


def _layout(root_path: str | None) -> dict[str, Any]:
    root = Path(root_path) if root_path else Path(".")
    return {
        "directories": [(root / item).as_posix() for item in _LAYOUT_DIRS],
        "files": [(root / item).as_posix() for item in _LAYOUT_FILES],
        "profiles": {
            "current_flat": {
                "directories": [(root / item).as_posix() for item in _CURRENT_LAYOUT_DIRS],
                "files": [(root / item).as_posix() for item in _LAYOUT_FILES],
            },
            "target_primary_secondary": {
                "directories": [(root / item).as_posix() for item in _TARGET_LAYOUT_DIRS],
                "files": [(root / item).as_posix() for item in _LAYOUT_FILES],
            },
        },
    }


def _empty_layout_compatibility() -> dict[str, Any]:
    return {
        "current_flat_present": False,
        "target_primary_secondary_present": False,
        "sources_present": False,
        "migration_required": False,
        "read_only_compatibility_mode": True,
    }


def _layout_compatibility(root: Path) -> dict[str, Any]:
    current_flat_present = any((root / item).is_dir() for item in _CURRENT_LAYOUT_DIRS)
    primary_present = (root / "memory" / "mem" / "primary").is_dir()
    secondary_present = (root / "memory" / "mem" / "secondary").is_dir()
    target_primary_secondary_present = primary_present and secondary_present
    sources_present = (root / "memory" / "sources").is_dir() or any(
        (root / item).is_dir() for item in _TARGET_SOURCE_DIRS
    )
    return {
        "current_flat_present": current_flat_present,
        "target_primary_secondary_present": target_primary_secondary_present,
        "sources_present": sources_present,
        "migration_required": current_flat_present and not target_primary_secondary_present,
        "read_only_compatibility_mode": True,
    }


def _iter_store_files(root: Path) -> Iterator[Path]:
    memory_root = root / "memory"
    if not memory_root.exists() or not memory_root.is_dir():
        return
    for path in memory_root.rglob("*"):
        if path.is_file():
            yield path


def _is_supported_file(relative_path: str, suffix: str) -> bool:
    if relative_path.startswith("memory/raw/"):
        return suffix in _ALLOWED_SUFFIXES["memory/raw"]
    if relative_path.startswith("memory/sources/"):
        return suffix in _ALLOWED_SUFFIXES["memory/sources"]
    if relative_path.startswith("memory/mem/"):
        return suffix in _ALLOWED_SUFFIXES["memory/mem"]
    return False


def _validate_file_sample(file_path: Path) -> str | None:
    if file_path.is_symlink():
        return "symlink_blocked"
    try:
        with file_path.open("rb") as handle:
            sample = handle.read(_MAX_SAMPLE_BYTES)
            reached_limit = len(sample) == _MAX_SAMPLE_BYTES
            if reached_limit:
                extra = handle.read(1)
                reached_limit = bool(extra)
        _decode_utf8_sample(sample, allow_truncated_final_sequence=reached_limit)
    except UnicodeDecodeError:
        return "malformed_or_unreadable_file"
    except OSError:
        return "malformed_or_unreadable_file"
    return None



def _snippet_path_block_reason(root: Path, relative_path: str) -> str | None:
    if not relative_path or Path(relative_path).is_absolute():
        return "path_outside_mem_scope"
    if ".." in Path(relative_path).parts:
        return "path_outside_mem_scope"
    if not any(relative_path.startswith(f"{allowed}/") for allowed in _SNIPPET_DIRS):
        return "unsupported_scope"
    if not relative_path.endswith(".md"):
        return "unsupported_scope"
    candidate_path = root / relative_path
    try:
        root_resolved = root.resolve(strict=True)
        parent_resolved = candidate_path.parent.resolve(strict=True)
    except OSError:
        return "path_outside_mem_scope"
    if root_resolved != parent_resolved and root_resolved not in parent_resolved.parents:
        return "path_outside_mem_scope"
    if _path_contains_symlink(root, candidate_path):
        return "symlink_blocked"
    if not candidate_path.is_file():
        return "file_missing"
    return None


def _path_contains_symlink(root: Path, candidate_path: Path) -> bool:
    current = root
    try:
        relative_parts = candidate_path.relative_to(root).parts
    except ValueError:
        return True
    for part in relative_parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _read_bounded_snippet(
    file_path: Path,
    max_read_bytes: int,
    max_snippet_chars: int,
) -> str:
    with file_path.open("rb") as handle:
        sample = handle.read(max_read_bytes + 1)
    if len(sample) > max_read_bytes:
        raise ValueError("read_limit_exceeded")
    text = sample.decode("utf-8")
    return text[:max_snippet_chars]


def _read_index_summary(root: Path, max_read_bytes: int) -> dict[str, Any] | None:
    index_path = root / "memory" / "mem" / "index.md"
    if not index_path.is_file():
        return None
    try:
        sample = _read_text_sample(index_path, max_read_bytes)
    except (UnicodeDecodeError, OSError):
        return {"path": "memory/mem/index.md", "readable": False}
    return {
        "path": "memory/mem/index.md",
        "readable": True,
        "estimated_chars": len(sample),
    }


def _iter_candidate_page_files(root: Path) -> Iterator[Path]:
    for relative_dir in _CANDIDATE_DIRS:
        page_dir = root / relative_dir
        if not page_dir.exists() or not page_dir.is_dir():
            continue
        if _path_contains_symlink(root, page_dir):
            continue
        for path in page_dir.glob("*.md"):
            if path.is_file():
                yield path


def _read_text_sample(file_path: Path, max_read_bytes: int) -> str:
    with file_path.open("rb") as handle:
        sample = handle.read(max(1, max_read_bytes))
        reached_limit = len(sample) == max(1, max_read_bytes)
        if reached_limit:
            extra = handle.read(1)
            reached_limit = bool(extra)
    return _decode_utf8_sample(sample, allow_truncated_final_sequence=reached_limit)


def _decode_utf8_sample(
    sample: bytes,
    *,
    allow_truncated_final_sequence: bool,
) -> str:
    decoder = codecs.getincrementaldecoder("utf-8")()
    return decoder.decode(sample, final=not allow_truncated_final_sequence)


def _memory_layer_for_path(relative_path: str) -> str:
    if relative_path.startswith("memory/mem/primary/"):
        return "primary"
    if relative_path.startswith("memory/mem/secondary/"):
        return "secondary"
    if relative_path.startswith("memory/mem/"):
        return "legacy_flat"
    return "unknown"


def _layout_profile_for_path(relative_path: str) -> str:
    if relative_path.startswith("memory/mem/primary/") or relative_path.startswith(
        "memory/mem/secondary/"
    ):
        return "target_primary_secondary"
    if relative_path.startswith("memory/mem/"):
        return "current_flat"
    return "unknown"


def _selection_reason(relative_path: str, sample: str, query_terms: list[str]) -> str:
    haystack = f"{relative_path}\n{sample}".lower()
    if any(term in haystack for term in query_terms):
        return "keyword_match"
    return "store_page_available"
