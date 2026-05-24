"""Memory context block insertion helpers for RelayLM MVP-3."""

from __future__ import annotations

from pathlib import Path

from relaylm.compiler import ContextBlock, StabilityClass
from relaylm.config import RelayLMConfig
from relaylm.memory_seed import (
    build_memory_context_block,
    filter_memory_seeds,
    load_memory_seed_file,
)
from relaylm.routing import ResolvedRoute


class MemoryConfigurationError(ValueError):
    """Raised when route/memory config cannot resolve memory files."""


def build_seed_memory_block(
    *,
    seed_path: str | Path,
    character_id: str | None,
) -> ContextBlock | None:
    seed_file = load_memory_seed_file(seed_path)
    memories = filter_memory_seeds(seed_file, character_id=character_id)
    return build_memory_context_block(memories)


def resolve_seed_memory_block(config: RelayLMConfig, route: ResolvedRoute) -> ContextBlock | None:
    if not route.character_id:
        return None
    character = config.characters.get(route.character_id)
    if character is None:
        raise MemoryConfigurationError(
            f"RelayLM route {route.route_model} references missing character: {route.character_id}"
        )
    if character.memory_seed_path is None:
        return None
    return build_seed_memory_block(
        seed_path=character.memory_seed_path,
        character_id=route.character_id,
    )


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

    blocks = list(profile_blocks)
    rank = {
        StabilityClass.STABLE_PREFIX: 0,
        StabilityClass.SLOW_PREFIX: 1,
        StabilityClass.DYNAMIC_SUFFIX: 2,
    }
    memory_rank = rank[memory_block.stability_class]

    insert_at = len(blocks)
    for idx, block in enumerate(blocks):
        if rank[block.stability_class] > memory_rank:
            insert_at = idx
            break

    return [*blocks[:insert_at], memory_block, *blocks[insert_at:]]
