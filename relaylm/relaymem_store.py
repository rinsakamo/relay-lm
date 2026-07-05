"""Read-only RelayMEM file-store dry-run diagnostics."""

from __future__ import annotations

from typing import Any

from . import _relaymem_store_impl as _impl

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
_STRIP_CHARS = "\ufeff\u200b\r\n\t .,!?。！？、:;()[]{}\"'`<>«»“”‘’"


def discover_relaymem_page_candidates(
    *,
    root_path: str | None,
    query_terms: list[str] | None = None,
    max_candidates: int = _impl._DEFAULT_MAX_CANDIDATES,
    max_read_bytes: int = _impl._DEFAULT_MAX_CANDIDATE_READ_BYTES,
    max_scan: int = _impl._DEFAULT_MAX_CANDIDATE_SCAN,
) -> dict[str, Any]:
    """Discover read-only RelayMEM page candidates with canonical term expansion.

    Keep direct ``relaymem_store`` callers aligned with the retrieval path: full
    Japanese recall questions are expanded into the bounded recall phrases that
    the store selection layer can match against Primary MEM page summaries.
    """

    return _impl.discover_relaymem_page_candidates(
        root_path=root_path,
        query_terms=_expanded_query_terms(query_terms),
        max_candidates=max_candidates,
        max_read_bytes=max_read_bytes,
        max_scan=max_scan,
    )


build_relaymem_snippet_evidence_dry_run = _impl.build_relaymem_snippet_evidence_dry_run


def build_relaymem_store_diagnostics(
    *,
    root_path: str | None,
    store_enabled: bool,
    retrieval_dry_run_only: bool,
) -> dict[str, Any]:
    """Inspect the target-only RelayMEM store layout without flat fallback."""

    return _impl.build_relaymem_store_diagnostics(
        root_path=root_path,
        store_enabled=store_enabled,
        retrieval_dry_run_only=retrieval_dry_run_only,
    )


def _expanded_query_terms(query_terms: list[str] | None) -> list[str] | None:
    if query_terms is None:
        return None
    expanded: list[str] = []
    for raw_term in query_terms:
        if not isinstance(raw_term, str):
            continue
        term = _clean_query_term(raw_term)
        if not term:
            continue
        lowered = term.lower()
        if lowered not in expanded:
            expanded.append(lowered)
        for phrase in _JAPANESE_RECALL_PHRASES:
            if phrase in term:
                phrase_lowered = phrase.lower()
                if phrase_lowered not in expanded:
                    expanded.append(phrase_lowered)
    return expanded


def _clean_query_term(raw_term: str) -> str:
    term = str(raw_term).strip(_STRIP_CHARS)
    term = " ".join(term.split())
    return term[:128]


__all__ = [
    "discover_relaymem_page_candidates",
    "build_relaymem_snippet_evidence_dry_run",
    "build_relaymem_store_diagnostics",
]
