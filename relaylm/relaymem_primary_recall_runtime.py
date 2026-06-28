"""Runtime compatibility hooks for scoped Primary MEM recall."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_TOKEN_WITH_SLASH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")
_JAPANESE_RECALL_PHRASES = (
    "朝の集中作業",
    "集中作業",
    "落ち着く",
    "落ち着き",
    "飲み物",
    "浅煎り",
    "エチオピアコーヒー",
    "エチオピア",
    "コーヒー",
    "紅茶",
)
_INSTALLED = False


def install_relaymem_primary_recall_runtime() -> None:
    """Align scoped Primary recall with durable queue namespaces and E1 queries."""

    global _INSTALLED
    if _INSTALLED:
        return

    from . import _relaymem_store_impl as _store_impl
    from . import relaymem_primary_recall as _primary_recall
    from . import relaymem_store as _store

    _primary_recall._TOKEN_RE = _TOKEN_WITH_SLASH_RE

    def discover_relaymem_page_candidates(
        *,
        root_path: str | None,
        query_terms: list[str] | None = None,
        max_candidates: int = _store_impl._DEFAULT_MAX_CANDIDATES,
        max_read_bytes: int = _store_impl._DEFAULT_MAX_CANDIDATE_READ_BYTES,
        max_scan: int = _store_impl._DEFAULT_MAX_CANDIDATE_SCAN,
    ) -> dict[str, Any]:
        return _store_impl.discover_relaymem_page_candidates(
            root_path=_effective_read_root(root_path),
            query_terms=_expanded_query_terms(query_terms),
            max_candidates=max_candidates,
            max_read_bytes=max_read_bytes,
            max_scan=max_scan,
        )

    def build_relaymem_snippet_evidence_dry_run(
        *,
        root_path: str | None,
        selected_mem_candidates: list[dict[str, Any]] | None,
        snippet_extraction_enabled: bool,
        snippet_dry_run_only: bool,
        max_snippet_chars: int = _store_impl._DEFAULT_MAX_SNIPPET_CHARS,
        max_snippet_candidates: int = _store_impl._DEFAULT_MAX_SNIPPET_CANDIDATES,
        max_read_bytes: int = _store_impl._DEFAULT_MAX_SNIPPET_READ_BYTES,
    ) -> dict[str, Any]:
        return _store_impl.build_relaymem_snippet_evidence_dry_run(
            root_path=_effective_read_root(root_path),
            selected_mem_candidates=selected_mem_candidates,
            snippet_extraction_enabled=snippet_extraction_enabled,
            snippet_dry_run_only=snippet_dry_run_only,
            max_snippet_chars=max_snippet_chars,
            max_snippet_candidates=max_snippet_candidates,
            max_read_bytes=max_read_bytes,
        )

    original_diagnostics = _store.build_relaymem_store_diagnostics

    def build_relaymem_store_diagnostics(
        *,
        root_path: str | None,
        store_enabled: bool,
        retrieval_dry_run_only: bool,
    ) -> dict[str, Any]:
        return original_diagnostics(
            root_path=_effective_read_root(root_path),
            store_enabled=store_enabled,
            retrieval_dry_run_only=retrieval_dry_run_only,
        )

    _store.discover_relaymem_page_candidates = discover_relaymem_page_candidates
    _store.build_relaymem_snippet_evidence_dry_run = build_relaymem_snippet_evidence_dry_run
    _store.build_relaymem_store_diagnostics = build_relaymem_store_diagnostics

    from . import relaymem_retrieval as _retrieval

    _retrieval.discover_relaymem_page_candidates = discover_relaymem_page_candidates
    _retrieval.build_relaymem_snippet_evidence_dry_run = build_relaymem_snippet_evidence_dry_run
    _retrieval._term_hints = _term_hints_with_japanese_recall_phrases
    _INSTALLED = True


def _expanded_query_terms(query_terms: list[str] | None) -> list[str] | None:
    terms: list[str] = []

    def add(term: str) -> None:
        term = term.strip()[:32]
        if len(term) < 2 or term in terms:
            return
        terms.append(term)

    for raw in query_terms or []:
        add(str(raw))
        if len(terms) >= 12:
            return terms[:12]
    haystack = "\n".join(terms)
    for phrase in _JAPANESE_RECALL_PHRASES:
        if phrase in haystack:
            add(phrase)
            if len(terms) >= 12:
                break
    return terms[:12]


def _term_hints_with_japanese_recall_phrases(text: str) -> list[str]:
    terms: list[str] = []

    def add(term: str) -> None:
        term = term.strip(".,!?。！？、:;()[]{}\"'")[:32]
        if len(term) < 2 or term in terms:
            return
        terms.append(term)

    for raw in text.replace("\n", " ").split(" "):
        add(raw)
        if len(terms) >= 12:
            return terms[:12]

    for phrase in _JAPANESE_RECALL_PHRASES:
        if phrase in text:
            add(phrase)
            if len(terms) >= 12:
                break
    return terms[:12]


def _effective_read_root(root_path: str | None) -> str | None:
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
        children = list(characters.iterdir())
    except OSError:
        return str(root)
    for child in children:
        if child.is_symlink() or not child.is_dir():
            continue
        memory_root = child / "memory"
        if memory_root.is_symlink():
            continue
        if _root_has_control_files(child):
            valid_roots.append(child)
            if len(valid_roots) > 1:
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
