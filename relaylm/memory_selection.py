"""Config-driven memory candidate selection helpers for RelayLM MVP-4."""

from __future__ import annotations

from dataclasses import dataclass

from relaylm.compiler import ContextBlock
from relaylm.config import RelayLMConfig
from relaylm.memory_candidate import (
    MemoryBlockAssembly,
    MemorySelectionSummary,
    assemble_candidate_memory_block,
    load_seed_memory_candidates,
    select_memory_candidates,
    summarize_memory_selection,
)
from relaylm.memory_context import MemoryConfigurationError
from relaylm.routing import ResolvedRoute


@dataclass(frozen=True)
class ConfiguredMemorySelection:
    block: ContextBlock | None
    summary: MemorySelectionSummary | None
    assembly: MemoryBlockAssembly | None = None


def build_configured_candidate_memory_selection(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
) -> ConfiguredMemorySelection:
    if not route.character_id:
        return ConfiguredMemorySelection(block=None, summary=None)
    character = config.characters.get(route.character_id)
    if character is None:
        raise MemoryConfigurationError(
            f"RelayLM route {route.route_model} references missing character: {route.character_id}"
        )
    if character.memory_seed_path is None:
        return ConfiguredMemorySelection(block=None, summary=None)

    candidates = load_seed_memory_candidates(character.memory_seed_path)
    selected = select_memory_candidates(
        candidates,
        character_id=route.character_id,
        limit=config.memory.candidate_limit,
    )
    summary = summarize_memory_selection(
        candidates,
        character_id=route.character_id,
        limit=config.memory.candidate_limit,
        selected=selected,
    )
    assembly = assemble_candidate_memory_block(
        selected,
        token_budget_hint=config.memory.token_budget_hint,
        character_budget=config.memory.character_budget,
    )
    return ConfiguredMemorySelection(block=assembly.block, summary=summary, assembly=assembly)


def build_configured_candidate_memory_block(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
) -> ContextBlock | None:
    return build_configured_candidate_memory_selection(config=config, route=route).block
