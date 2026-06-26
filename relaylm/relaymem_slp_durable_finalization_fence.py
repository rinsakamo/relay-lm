"""Shared I1-G per-record mutation fence.

I1-GC remains the original owner of the exact lock filename and flock semantics.
I1-GD imports this boundary instead of creating a second lock authority.
"""
from __future__ import annotations

from typing import Any

from .relaymem_slp_durable_finalization_replay import _acquire_fence


def acquire_relaymem_slp_durable_finalization_fence(
    root: str,
    locator_digest: str,
) -> tuple[Any | None, bool, tuple[str, ...]]:
    """Acquire the exact nonblocking I1-GC locator fence.

    The returned object owns both the private-root descriptor and lock-file
    descriptor and must be closed by the caller.  The lock file itself is never
    unlinked by this boundary.
    """

    return _acquire_fence(root, locator_digest)


__all__ = ["acquire_relaymem_slp_durable_finalization_fence"]
