"""Read-only Primary MEM history/observation/admin surface.

RT-1D-R5 retired the ordinary Primary reader. The scoped recall entry point,
its candidate discovery, deterministic selection, snippet handoff, and the
no-candidate/policy fallback are deleted rather than fenced, so there is no
ordinary Primary read path left in this build to re-enter, restore, or fall
back to. Ordinary Retrieval serves Subjective alone.

What survives here is exactly the read-only page and control-state access the
explicitly classified Primary history, observation, lifecycle, correction, and
admin projections still need. Those are frozen historical assets: they never
rank, select, serve ordinary Retrieval, or write. Primary writers stay
unreachable and rejected by the durable RT-1D-R2/R4 writer authority, which
this module neither owns nor re-derives.

The re-exports below are the stable import boundary those admin owners already
depend on; ``relaylm.relaymem_primary_recall_store`` remains the implementation
owner.
"""

from __future__ import annotations

from .relaymem_primary_recall_store import (
    _load_control_state,
    _load_validated_page,
    _safe_root,
    _token,
    resolve_relaymem_character_store_root,
)

__all__ = [
    "resolve_relaymem_character_store_root",
]
