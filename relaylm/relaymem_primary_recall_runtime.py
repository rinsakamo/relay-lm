"""Compatibility no-op for the former Primary MEM recall runtime hook.

Scoped Primary recall root/read behavior (effective read root resolution,
character-scoped root discovery, and Japanese recall phrase query
expansion) is now folded directly into ``_relaymem_store_impl`` and
``relaymem_retrieval``. Importing those modules alone reproduces the
previously patched behavior, so this module no longer installs a runtime
monkey-patch.
"""
from __future__ import annotations


def install_relaymem_primary_recall_runtime() -> None:
    """Compatibility no-op.

    Runtime behavior is folded into canonical RelayMEM modules.
    """
    return None


__all__ = ["install_relaymem_primary_recall_runtime"]
