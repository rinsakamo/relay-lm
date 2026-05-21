"""Config-driven memory candidate selection helpers for RelayLM MVP-4."""

from __future__ import annotations

from relaylm.compiler import ContextBlock
from relaylm.config import RelayLMConfig
from relaylm.memory_candidate import (
    build_candidate_memory_block,
    load_seed_memory_candidates,
    select_memory_candidates,
)
from relaylm.memory_context import MemoryConfigurationError
from relaylm.routing import ResolvedRoute


def build_configured_candidate_memory_block(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
) -> ContextBlock | None:
    if not route.character_id:
        return None
    character = config.characters.get(route.character_id)
    if character is None:
        raise MemoryConfigurationError(
            f"RelayLM route {route.route_model} references missing character: {route.character_id}"
        )
    if character.memory_seed_path is None:
        return None

    candidates = load_seed_memory_candidates(character.memory_seed_path)
    selected = select_memory_candidates(
        candidates,
        character_id=route.character_id,
        limit=config.memory.candidate_limit,
    )
    return build_candidate_memory_block(
        selected,
        token_budget_hint=config.memory.token_budget_hint,
    )
