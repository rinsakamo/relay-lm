"""Compatibility shim for retired E1-R3 durable replay support."""
from __future__ import annotations


def install_durable_finalization_formation_replay_patch() -> None:
    """Route historical opt-in callers through canonical replay support."""

    from . import relaymem_slp_durable_finalization_replay as replay

    sync = getattr(replay, "_sync_dependency_seams")
    sync()
    return None


__all__ = ["install_durable_finalization_formation_replay_patch"]
