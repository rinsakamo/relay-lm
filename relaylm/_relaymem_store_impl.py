"""Read-only RelayMEM file-store dry-run diagnostics."""
from __future__ import annotations

import codecs
from collections.abc import Iterator
from pathlib import Path
from typing import Any

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
_TARGET_LAYOUT_DIRS = _TARGET_MEM_LAYOUT_DIRS + _TARGET_SOURCE_DIRS
_LAYOUT_DIRS = _TARGET_LAYOUT_DIRS
_LAYOUT_FILES = ("memory/mem/index.md", "memory/mem/log.md")
_ALLOWED_SUFFIXES = {"memory/sources": {".jsonl", ".md"}, "memory/mem": {".md"}}
_MAX_FILES_TO_VALIDATE = 64
_MAX_FILES_TO_SCAN = 128
_MAX_SAMPLE_BYTES = 4096
_CANDIDATE_DIRS = _TARGET_MEM_LAYOUT_DIRS
_DEFAULT_MAX_CANDIDATES = 8
_DEFAULT_MAX_CANDIDATE_READ_BYTES = 4096
_DEFAULT_MAX_CANDIDATE_SCAN = 128
_SNIPPET_DIRS = _CANDIDATE_DIRS
_DEFAULT_MAX_SNIPPET_CHARS = 512
_DEFAULT_MAX_SNIPPET_CANDIDATES = 3
_DEFAULT_MAX_SNIPPET_READ_BYTES = 4096
_MAX_CHARACTER_ROOT_SCAN = 32


def _effective_read_root(root_path: str | None) -> str | None:
    """Resolve the character-scoped store root when given an operator root.

    When ``root_path`` itself has no control files but exactly one
    ``characters/*`` child does, reads are scoped to that single character
    partition. Any ambiguity (zero or multiple valid children, unreadable
    directories) falls back to the original root untouched.
    """
    if not root_path:
        return root_path
    root = Path(root_path)
    if _root_has_any_control_file(root):
        return str(root)
    characters = root / "characters"
    if characters.is_symlink() or not characters.is_dir():
        return str(root)
    valid_roots: list[Path] = []
    try:
        for scanned_count, child in enumerate(characters.iterdir(), start=1):
            if scanned_count > _MAX_CHARACTER_ROOT_SCAN:
                return str(root)
            if child.is_symlink() or not child.is_dir():
                continue
            memory_root = child / "memory"
            if memory_root.is_symlink():
                continue
            if _root_has_control_files(child):
                valid_roots.append(child)
                if len(valid_roots) > 1:
                    return str(root)
    except OSError:
        return str(root)
    if len(valid_roots) == 1:
        return str(valid_roots[0])
    return str(root)


def _root_has_any_control_file(root: Path) -> bool:
    memory_root = root / "memory"
    mem_root = memory_root / "mem"
    if memory_root.is_symlink() or mem_root.is_symlink():
        return False
    return (mem_root / "index.md").is_file() or (mem_root / "log.md").is_file()


def _root_has_control_files(root: Path) -> bool:
    memory_root = root / "memory"
    mem_root = memory_root / "mem"
    if memory_root.is_symlink() or mem_root.is_symlink():
        return False
    return (mem_root / "index.md").is_file() and (mem_root / "log.md").is_file()


def discover_relaymem_page_candidates(
    *,
    root_path: str | None,
    query_terms: list[str] | None = None,
    max_candidates: int = _DEFAULT_MAX_CANDIDATES,
    max_read_bytes: int = _DEFAULT_MAX_CANDIDATE_READ_BYTES,
    max_scan: int = _DEFAULT_MAX_CANDIDATE_SCAN,
) -> dict[str, Any]:
    root_path = _effective_read_root(root_path)
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
    if not _target_primary_secondary_present(root):
        result["fallback_reason"] = "target_primary_secondary_layout_missing"
        return result
    terms = [term.lower() for term in (query_terms or []) if term]
    candidates: list[dict[str, Any]] = []
    blocked: list[dict[str, str]] = []
    seen = 0
    truncated = False
    cap_reached = False
    for file_path in _iter_candidate_page_files(root):
        if seen >= max_scan:
            truncated = True
            break
        seen += 1
        relative = file_path.relative_to(root).as_posix()
        if len(candidates) >= max_candidates:
            cap_reached = True
        if file_path.is_symlink():
            blocked.append({"path": relative, "reason": "symlink_blocked"})
            continue
        try:
            sample = _read_text_sample(file_path, max_read_bytes)
        except (UnicodeDecodeError, OSError):
            blocked.append({"path": relative, "reason": "malformed_or_unreadable_file"})
            continue
        if len(candidates) >= max_candidates:
            cap_reached = True
            continue
        candidates.append(
            {
                "path": relative,
                "source": "mem_page",
                "reason": _selection_reason(relative, sample, terms),
                "estimated_chars": len(sample),
                "memory_layer": _memory_layer_for_path(relative),
                "layout_profile": _layout_profile_for_path(relative),
                "applied_to_ctx": False,
            }
        )
    result.update(
        {
            "candidate_scan_seen": seen,
            "candidate_scan_truncated": truncated,
            "candidate_cap_reached": cap_reached
            or (max_candidates > 0 and len(candidates) >= max_candidates and seen > len(candidates)),
            "candidates": candidates,
            "blocked_files": blocked,
        }
    )
    if blocked:
        result["fallback_reason"] = "memory_store_files_blocked"
    elif truncated:
        result["fallback_reason"] = "memory_store_candidate_scan_truncated"
    elif cap_reached:
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
    if snippet_extraction_enabled:
        root_path = _effective_read_root(root_path)
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
    for index, candidate in enumerate((selected_mem_candidates or [])[:max_snippet_candidates]):
        if not isinstance(candidate, dict):
            continue
        relative = str(candidate.get("path", ""))
        evidence_id = f"evidence:{index}"
        reason = _snippet_path_block_reason(root, relative)
        if reason:
            envelope["blocked"].append(
                {"evidence_id": evidence_id, "selected_index": index, "path": relative, "reason": reason}
            )
            continue
        try:
            snippet = _read_bounded_snippet(root / relative, max_read_bytes, max_snippet_chars)
        except UnicodeDecodeError:
            envelope["blocked"].append(
                {"evidence_id": evidence_id, "selected_index": index, "path": relative, "reason": "malformed_utf8"}
            )
            continue
        except OSError:
            envelope["blocked"].append(
                {"evidence_id": evidence_id, "selected_index": index, "path": relative, "reason": "unreadable_file"}
            )
            continue
        except ValueError as exc:
            envelope["blocked"].append(
                {"evidence_id": evidence_id, "selected_index": index, "path": relative, "reason": str(exc)}
            )
            continue
        tokens = max(1, len(snippet) // 4) if snippet else 0
        item = {
            "evidence_id": evidence_id,
            "selected_index": index,
            "path": relative,
            "source": str(candidate.get("source", "mem_page")),
            "evidence_kind": "bounded_page_snippet",
            "snippet_text": snippet,
            "snippet_chars": len(snippet),
            "estimated_tokens": tokens,
            "memory_layer": _memory_layer_for_path(relative),
            "layout_profile": _layout_profile_for_path(relative),
            "applied_to_ctx": False,
            "safe_for_prompt_preview": False,
            "blocked_reasons": [],
        }
        result["snippet_candidates"].append(item)
        envelope["snippets"].append(
            {
                "evidence_id": evidence_id,
                "selected_index": index,
                "path": relative,
                "evidence_kind": "bounded_page_snippet",
                "snippet_chars": len(snippet),
                "estimated_tokens": tokens,
                "memory_layer": item["memory_layer"],
                "layout_profile": item["layout_profile"],
                "content_included_in_runtime_prompt": False,
            }
        )
    if len(selected_mem_candidates or []) > max_snippet_candidates:
        envelope["blocked"].append({"reason": "snippet_candidate_cap_reached"})
    return result


def build_relaymem_store_diagnostics(
    *,
    root_path: str | None,
    store_enabled: bool,
    retrieval_dry_run_only: bool,
) -> dict[str, Any]:
    if store_enabled:
        root_path = _effective_read_root(root_path)
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
    diagnostics["index_present"] = (root / "memory" / "mem" / "index.md").is_file()
    diagnostics["log_present"] = (root / "memory" / "mem" / "log.md").is_file()
    pages: list[str] = []
    blocked: list[dict[str, str]] = []
    seen = 0
    validated = 0
    scan_truncated = False
    validation_truncated = False
    for file_path in _iter_store_files(root):
        if seen >= _MAX_FILES_TO_SCAN:
            scan_truncated = True
            break
        seen += 1
        relative = file_path.relative_to(root).as_posix()
        if not _is_supported_file(relative, file_path.suffix):
            blocked.append({"path": relative, "reason": "unsupported_file_type"})
            continue
        if validated >= _MAX_FILES_TO_VALIDATE:
            validation_truncated = True
            continue
        validation_result = _validate_file_sample(file_path)
        validated += 1
        if validation_result:
            blocked.append({"path": relative, "reason": validation_result})
            continue
        if _is_target_mem_page(relative) and file_path.suffix == ".md":
            pages.append(relative)
    diagnostics["validation"] = {
        "max_files_to_scan": _MAX_FILES_TO_SCAN,
        "max_files_to_validate": _MAX_FILES_TO_VALIDATE,
        "max_sample_bytes": _MAX_SAMPLE_BYTES,
        "files_seen": seen,
        "files_validated": validated,
        "scan_truncated": scan_truncated,
        "validation_truncated": validation_truncated,
        "full_tree_materialized": False,
        "full_file_reads": False,
    }
    diagnostics.update({"page_paths": sorted(pages), "pages_discovered": len(pages), "blocked_files": blocked})
    if blocked:
        diagnostics["fallback_reason"] = "memory_store_files_blocked"
    elif scan_truncated:
        diagnostics["fallback_reason"] = "memory_store_scan_truncated"
    elif validation_truncated:
        diagnostics["fallback_reason"] = "memory_store_validation_truncated"
    elif not diagnostics["layout_compatibility"]["target_primary_secondary_present"]:
        diagnostics["fallback_reason"] = "target_primary_secondary_layout_missing"
    elif not pages:
        diagnostics["fallback_reason"] = "memory_store_no_candidate_pages"
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
            "target_primary_secondary": {
                "directories": [(root / item).as_posix() for item in _TARGET_LAYOUT_DIRS],
                "files": [(root / item).as_posix() for item in _LAYOUT_FILES],
            }
        },
    }


def _empty_layout_compatibility() -> dict[str, Any]:
    return {
        "target_primary_secondary_present": False,
        "sources_present": False,
        "flat_store_compatibility_removed": True,
    }


def _safe_layout_dir_present(root: Path, relative_path: str) -> bool:
    candidate = root / relative_path
    return candidate.is_dir() and not _path_contains_symlink(root, candidate)


def _target_primary_secondary_present(root: Path) -> bool:
    return _safe_layout_dir_present(root, "memory/mem/primary") and _safe_layout_dir_present(root, "memory/mem/secondary")


def _layout_compatibility(root: Path) -> dict[str, Any]:
    return {
        "target_primary_secondary_present": _target_primary_secondary_present(root),
        "sources_present": (root / "memory" / "sources").is_dir()
        or any((root / item).is_dir() for item in _TARGET_SOURCE_DIRS),
        "flat_store_compatibility_removed": True,
    }


def _iter_store_files(root: Path) -> Iterator[Path]:
    for control_file in sorted(root / item for item in _LAYOUT_FILES):
        if control_file.is_file() or control_file.is_symlink():
            yield control_file
    for rel_root in _TARGET_LAYOUT_DIRS:
        layout_root = root / rel_root
        if not layout_root.exists() or not layout_root.is_dir() or _path_contains_symlink(root, layout_root):
            continue
        pending = [layout_root]
        while pending:
            current = pending.pop()
            try:
                children = list(current.iterdir())
            except OSError:
                continue
            for path in children:
                if path.is_symlink():
                    if path.is_file():
                        yield path
                elif path.is_dir():
                    pending.append(path)
                elif path.is_file():
                    yield path


def _is_supported_file(relative_path: str, suffix: str) -> bool:
    return (
        (relative_path.startswith("memory/sources/") and suffix in _ALLOWED_SUFFIXES["memory/sources"])
        or (relative_path in _LAYOUT_FILES and suffix in _ALLOWED_SUFFIXES["memory/mem"])
        or (_is_target_mem_page(relative_path) and suffix in _ALLOWED_SUFFIXES["memory/mem"])
    )


def _validate_file_sample(file_path: Path) -> str | None:
    if file_path.is_symlink():
        return "symlink_blocked"
    try:
        with file_path.open("rb") as handle:
            sample = handle.read(_MAX_SAMPLE_BYTES)
            reached_limit = len(sample) == _MAX_SAMPLE_BYTES
            if reached_limit:
                reached_limit = bool(handle.read(1))
        _decode_utf8_sample(sample, allow_truncated_final_sequence=reached_limit)
    except (UnicodeDecodeError, OSError):
        return "malformed_or_unreadable_file"
    return None


def _snippet_path_block_reason(root: Path, relative_path: str) -> str | None:
    if not relative_path or Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
        return "path_outside_mem_scope"
    if not any(relative_path.startswith(f"{allowed}/") for allowed in _SNIPPET_DIRS) or not relative_path.endswith(".md"):
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
    return None if candidate_path.is_file() else "file_missing"


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


def _read_bounded_snippet(file_path: Path, max_read_bytes: int, max_snippet_chars: int) -> str:
    with file_path.open("rb") as handle:
        sample = handle.read(max_read_bytes + 1)
    if len(sample) > max_read_bytes:
        raise ValueError("read_limit_exceeded")
    return sample.decode("utf-8")[:max_snippet_chars]


def _read_index_summary(root: Path, max_read_bytes: int) -> dict[str, Any] | None:
    index_path = root / "memory" / "mem" / "index.md"
    if not index_path.is_file():
        return None
    try:
        sample = _read_text_sample(index_path, max_read_bytes)
    except (UnicodeDecodeError, OSError):
        return {"path": "memory/mem/index.md", "readable": False}
    return {"path": "memory/mem/index.md", "readable": True, "estimated_chars": len(sample)}


def _iter_candidate_page_files(root: Path) -> Iterator[Path]:
    for relative_dir in _CANDIDATE_DIRS:
        page_dir = root / relative_dir
        if page_dir.exists() and page_dir.is_dir() and not _path_contains_symlink(root, page_dir):
            yield from (path for path in page_dir.glob("*.md") if path.is_file())


def _read_text_sample(file_path: Path, max_read_bytes: int) -> str:
    with file_path.open("rb") as handle:
        sample = handle.read(max(1, max_read_bytes))
        reached_limit = len(sample) == max(1, max_read_bytes)
        if reached_limit:
            reached_limit = bool(handle.read(1))
    return _decode_utf8_sample(sample, allow_truncated_final_sequence=reached_limit)


def _decode_utf8_sample(sample: bytes, *, allow_truncated_final_sequence: bool) -> str:
    return codecs.getincrementaldecoder("utf-8")().decode(sample, final=not allow_truncated_final_sequence)


def _is_target_mem_page(relative_path: str) -> bool:
    return relative_path.endswith(".md") and any(
        relative_path.startswith(f"{directory}/") for directory in _TARGET_MEM_LAYOUT_DIRS
    )


def _memory_layer_for_path(relative_path: str) -> str:
    if relative_path.startswith("memory/mem/primary/"):
        return "primary"
    if relative_path.startswith("memory/mem/secondary/"):
        return "secondary"
    return "unknown"


def _layout_profile_for_path(relative_path: str) -> str:
    if relative_path.startswith("memory/mem/primary/") or relative_path.startswith("memory/mem/secondary/"):
        return "target_primary_secondary"
    return "unknown"


def _selection_reason(relative_path: str, sample: str, query_terms: list[str]) -> str:
    haystack = f"{relative_path}\n{sample}".lower()
    if any(term in haystack for term in query_terms):
        return "keyword_match"
    return "store_page_available"
