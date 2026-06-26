"""I-4C2 projection split between mutation governance and ordinary retrieval.

The underlying shared scanner validates the complete Correct/Forget operation
chain, including finalized Forget tombstones.  Phase I-4C2 must not, however,
change ordinary M2 currentness; that lifecycle exclusion belongs to I-4D.
This adapter therefore preserves the scanner's corruption, pending, and physical
identity evidence while rebuilding only the public correction-current projection
from completed correction receipts.
"""
from __future__ import annotations

from pathlib import Path

from . import _relaymem_primary_current_state_impl as _impl


def load_primary_current_state_index(
    store_root: str | Path, *, namespace: str
) -> _impl.PrimaryCorrectionStateIndex:
    """Return the correction-only retrieval projection after full chain validation."""

    combined = _impl.load_primary_current_state_index(store_root, namespace=namespace)
    current_by_logical: dict[str, tuple[str, int]] = {}
    logical_by_physical = dict(combined.logical_by_physical)
    superseded_physical: set[str] = set()
    invalid_logical = set(combined.invalid_logical)

    for logical in combined.current_by_logical:
        physical = logical
        revision = 1
        receipts = sorted(
            combined.receipts_by_logical.get(logical, ()),
            key=lambda item: (
                int(item["result_revision"]),
                str(item["operation_key"]),
            ),
        )
        for receipt in receipts:
            if (
                receipt.get("prior_physical_id") != physical
                or receipt.get("prior_revision") != revision
                or receipt.get("result_revision") != revision + 1
            ):
                invalid_logical.add(logical)
                break
            superseded_physical.add(physical)
            logical_by_physical[physical] = logical
            physical = str(receipt["result_physical_id"])
            revision = int(receipt["result_revision"])
            logical_by_physical[physical] = logical
        else:
            current_by_logical[logical] = (physical, revision)

    return _impl.PrimaryCorrectionStateIndex(
        current_by_logical=current_by_logical,
        logical_by_physical=logical_by_physical,
        superseded_physical=frozenset(superseded_physical),
        pending_physical=combined.pending_physical,
        invalid_logical=frozenset(invalid_logical),
        receipts_by_logical=combined.receipts_by_logical,
        pending_logical=combined.pending_logical,
    )


__all__ = ["load_primary_current_state_index"]
