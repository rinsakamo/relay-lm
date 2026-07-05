"""Compatibility no-op for the former E1-R5 candidate bridge runtime patch.

E1-R5 candidate bridge behavior (bounded fallback discovery from
character-scoped Primary MEM index/log/page controls, the slash-permitting
scope/namespace token shape, and the associated public/runtime projection
fields) is now folded directly into ``relaymem_primary_recall``. Importing
``relaymem_primary_recall`` alone reproduces the previously bridged behavior,
so this module no longer installs a runtime monkey-patch.
"""
from __future__ import annotations


def install_relaymem_primary_recall_candidate_bridge_runtime() -> None:
    """Compatibility no-op.

    E1-R5 candidate bridge behavior is now folded into
    ``relaymem_primary_recall``. This function is kept only so existing
    callers do not need to be updated in lockstep; it performs no patching.
    """
    return None


__all__ = ["install_relaymem_primary_recall_candidate_bridge_runtime"]
