"""Compatibility no-op for the former RelayMEM retrieval priority runtime hook.

Retrieval priority behavior (priority-aware candidate selection, the larger
discovery cap, and the ``query_summary`` / ``retrieval_query_candidate`` /
``retrieval_query_private`` / ``retrieval_priority`` artifact fields) is now
folded directly into ``relaymem_retrieval``. Importing ``relaymem_retrieval``
alone reproduces the previously patched behavior, so this module no longer
installs a runtime monkey-patch.
"""
from __future__ import annotations

from typing import Any


def install_relaymem_retrieval_priority_runtime(
    retrieval_module: Any | None = None,
) -> None:
    """Compatibility no-op.

    Retrieval priority behavior is folded into relaymem_retrieval.
    """
    return None


__all__ = ["install_relaymem_retrieval_priority_runtime"]
