"""I-4D unified Correct/Forget current-state projection for ordinary retrieval.

The shared scanner remains the only parser for correction receipts, prepared
operations, hidden successors, controls, and finalized tombstones.  I-4D exposes
that complete fail-closed currentness to ordinary Primary recall.  M2 still owns
candidate discovery, relevance ordering, caps, and budgets.
"""
from __future__ import annotations

from pathlib import Path

from . import _relaymem_primary_current_state_impl as _impl


def load_primary_current_state_index(
    store_root: str | Path, *, namespace: str
) -> _impl.PrimaryCorrectionStateIndex:
    """Return one read-only Correct/Forget lifecycle index for retrieval.

    A prepared operation makes the current physical revision pending as well as
    any declared successor.  The compatibility identity resolver therefore
    returns no eligible identity throughout the prepared-to-finalized window.
    Finalized Forget state keeps the hidden successor as canonical current state,
    so every prior active physical revision remains non-current without fallback.
    """

    combined = _impl.load_primary_current_state_index(
        store_root, namespace=namespace
    )
    pending_physical = set(combined.pending_physical)
    for logical in combined.pending_logical:
        current = combined.current_by_logical.get(logical, (logical, 1))
        pending_physical.add(current[0])
    return _impl.PrimaryCorrectionStateIndex(
        current_by_logical=combined.current_by_logical,
        logical_by_physical=combined.logical_by_physical,
        superseded_physical=combined.superseded_physical,
        pending_physical=frozenset(pending_physical),
        invalid_logical=combined.invalid_logical,
        receipts_by_logical=combined.receipts_by_logical,
        pending_logical=combined.pending_logical,
    )


__all__ = ["load_primary_current_state_index"]
