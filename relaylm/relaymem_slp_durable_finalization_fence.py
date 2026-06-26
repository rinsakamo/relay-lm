"""Shared I1-G per-record maintenance fence.

I1-GD uses the exact I1-GC per-record fence and the existing I1-GB root
publication lock. Unsafe locator-owned objects are rejected before a new lock
file is created.
"""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from typing import Any

from .relaymem_slp_durable_finalization_replay import _acquire_fence
from .relaymem_slp_durable_finalization_store import (
    _acquire_lock,
    _open_store_root,
    _release_lock,
)


@dataclass(repr=False)
class RelayMEMSLPDurableFinalizationMaintenanceFence:
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
    """Acquire the exact I1-GC fence plus the existing root mutation lock."""

    preflight = _preflight_locator_objects(root, locator_digest)
    if preflight:
        return None, False, preflight
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


def _preflight_locator_objects(root: str, locator: str) -> tuple[str, ...]:
    if type(locator) is not str or len(locator) != 64 or any(
        char not in "0123456789abcdef" for char in locator
    ):
        return ("durable_finalization_locator_invalid",)
    root_fd, reasons = _open_store_root(root)
    if root_fd is None:
        return reasons
    record_prefix = f"durable-finalization-v0-{locator}"
    completion_name = f"durable-finalization-completion-v0-{locator}.json"
    lock_name = f".durable-finalization-replay-v0-{locator}.lock"
    exact_names = {
        f"{record_prefix}.base.json",
        f"{record_prefix}.seal.json",
        f"{record_prefix}.segment-isolation.json",
        completion_name,
        lock_name,
    }
    try:
        count = 0
        with os.scandir(root_fd) as entries:
            for entry in entries:
                count += 1
                if count > 1_000_000:
                    return (
                        "durable_finalization_retention_inventory_capacity_exceeded",
                    )
                name = entry.name
                if locator not in name or not name.startswith(
                    ("durable-finalization", ".durable-finalization")
                ):
                    continue
                is_segment = (
                    name.startswith(f"{record_prefix}.segment-")
                    and name.endswith(".json")
                    and len(name) == len(record_prefix) + len(".segment-000000.json")
                    and name[-11:-5].isdigit()
                )
                if name not in exact_names and not is_segment:
                    return ("durable_finalization_noncanonical_filename",)
                try:
                    info = entry.stat(follow_symlinks=False)
                except OSError:
                    return ("durable_finalization_component_unreadable",)
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                    return ("durable_finalization_unsafe_file_type",)
                if info.st_nlink != 1:
                    return ("durable_finalization_hardlink_invalid",)
        return ()
    except OSError:
        return ("durable_finalization_retention_inventory_failed",)
    finally:
        os.close(root_fd)


__all__ = [
    "RelayMEMSLPDurableFinalizationMaintenanceFence",
    "acquire_relaymem_slp_durable_finalization_fence",
]
