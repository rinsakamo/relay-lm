"""Shared I1-G per-record maintenance fence.

I1-GC remains the owner of the exact per-record lock filename and flock
semantics. I1-GD acquires that exact fence and, while it is held, also acquires
the existing I1-GB store-root exclusive flock. The second lock is not a new
I1-GD authority: it is the pre-existing publication lock needed to exclude an
I1-GB base/segment/seal mutation that predates the per-record fence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .relaymem_slp_durable_finalization_replay import _acquire_fence
from .relaymem_slp_durable_finalization_store import _acquire_lock, _release_lock


@dataclass(repr=False)
class RelayMEMSLPDurableFinalizationMaintenanceFence:
    """Exact I1-GC record fence plus the existing I1-GB root mutation lock."""

    _record_fence: Any
    _closed: bool = False

    @property
    def root_fd(self) -> int:
        return int(self._record_fence.root_fd)

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationMaintenanceFence("
            f"closed={self._closed!r}, identifier_values_omitted=True)"
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        # Release in reverse acquisition order. The underlying record-fence
        # close then unlocks the exact I1-GC lock file and closes both fds.
        _release_lock(self.root_fd)
        self._record_fence.close()


def acquire_relaymem_slp_durable_finalization_fence(
    root: str,
    locator_digest: str,
) -> tuple[
    RelayMEMSLPDurableFinalizationMaintenanceFence | None,
    bool,
    tuple[str, ...],
]:
    """Acquire the I1-GC record fence and existing I1-GB publication lock.

    Lock order is always per-record fence first, store-root flock second. I1-GC
    already uses per-record then store read-lock; I1-GB uses only the store-root
    mutation lock. All locks are nonblocking, so contention is a bounded skip and
    cannot deadlock. The per-record lock file is never unlinked.
    """

    record_fence, busy, reasons = _acquire_fence(root, locator_digest)
    if record_fence is None:
        return None, busy, reasons
    root_reason = _acquire_lock(record_fence.root_fd, exclusive=True)
    if root_reason is not None:
        record_fence.close()
        return (
            None,
            root_reason == "durable_finalization_store_lock_busy",
            (root_reason,),
        )
    return RelayMEMSLPDurableFinalizationMaintenanceFence(record_fence), False, ()


__all__ = [
    "RelayMEMSLPDurableFinalizationMaintenanceFence",
    "acquire_relaymem_slp_durable_finalization_fence",
]
