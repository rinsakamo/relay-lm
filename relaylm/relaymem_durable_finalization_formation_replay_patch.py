"""Compatibility shim for retired E1-R3 durable replay patching.

Formation summary preservation is implemented by the canonical durable-finalization
record and replay authorities.  This module is retained temporarily so historical
callers fail closed into the canonical path instead of monkeypatching authorities.
"""
from __future__ import annotations


def install_durable_finalization_formation_replay_patch() -> None:
    """No-op compatibility hook; canonical authorities already preserve formation summaries."""

    return None


__all__ = ["install_durable_finalization_formation_replay_patch"]
