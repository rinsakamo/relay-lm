"""Read-only RelayMEM file-store dry-run diagnostics."""

from __future__ import annotations

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
    """Inspect the target-only RelayMEM store layout without flat fallback."""

    return _impl.build_relaymem_store_diagnostics(
        root_path=root_path,
        store_enabled=store_enabled,
        retrieval_dry_run_only=retrieval_dry_run_only,
    )


__all__ = [
    "discover_relaymem_page_candidates",
    "build_relaymem_snippet_evidence_dry_run",
    "build_relaymem_store_diagnostics",
]
