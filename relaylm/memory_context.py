"""Memory context block insertion helpers for RelayLM MVP-3."""

from __future__ import annotations

from pathlib import Path

from relaylm.compiler import ContextBlock
from relaylm.memory_seed import (
    build_memory_context_block,
    filter_memory_seeds,
    load_memory_seed_file,
)


def build_seed_memory_block(
    *,
    seed_path: str | Path,
    character_id: str | None,
) -> ContextBlock | None:
    seed_file = load_memory_seed_file(seed_path)
    memories = filter_memory_seeds(seed_file, character_id=character_id)
    return build_memory_context_block(memories)


def insert_memory_block(
    *,
    profile_blocks: list[ContextBlock],
    memory_block: ContextBlock | None,
) -> list[ContextBlock]:
    """Insert memory after stable profile blocks.

    The current MVP-3 contract is:

    stable profile blocks -> slow-prefix memory block -> dynamic blocks later
    """

    if memory_block is None:
        return list(profile_blocks)
    return [*profile_blocks, memory_block]
