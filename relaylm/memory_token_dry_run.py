"""Config-driven token-estimated memory dry-run helpers for RelayLM MVP-7."""

from __future__ import annotations

from dataclasses import dataclass

from relaylm.config import RelayLMConfig
from relaylm.memory_candidate import (
    MemoryCandidate,
    MemorySelectionSummary,
    load_seed_memory_candidates,
    select_memory_candidates,
    summarize_memory_selection,
)
from relaylm.memory_context import MemoryConfigurationError
from relaylm.memory_token_budget import TokenBudgetMemoryAssembly, assemble_token_budget_memory_block
from relaylm.routing import ResolvedRoute


@dataclass(frozen=True)
class ConfiguredTokenMemoryDryRun:
    summary: MemorySelectionSummary | None
    assembly: TokenBudgetMemoryAssembly | None

    def to_log_dict(self) -> dict[str, object | None]:
        return {
            "summary": self.summary.to_log_dict() if self.summary is not None else None,
            "assembly": self.assembly.to_log_dict() if self.assembly is not None else None,
        }




def build_token_memory_dry_run_from_selected(
    *,
    config: RelayLMConfig,
    selected: list[MemoryCandidate] | None,
    summary: MemorySelectionSummary | None,
) -> ConfiguredTokenMemoryDryRun:
    if selected is None or summary is None:
        return ConfiguredTokenMemoryDryRun(summary=None, assembly=None)
    assembly = assemble_token_budget_memory_block(
        selected,
        token_budget_hint=config.memory.token_budget_hint,
        token_budget=config.memory.token_budget,
        chars_per_token=config.memory.chars_per_token,
    )
    return ConfiguredTokenMemoryDryRun(summary=summary, assembly=assembly)

def build_configured_token_memory_dry_run(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
) -> ConfiguredTokenMemoryDryRun:
    if not route.character_id:
        return ConfiguredTokenMemoryDryRun(summary=None, assembly=None)
    character = config.characters.get(route.character_id)
    if character is None:
        raise MemoryConfigurationError(
            f"RelayLM route {route.route_model} references missing character: {route.character_id}"
        )
    if character.memory_seed_path is None:
        return ConfiguredTokenMemoryDryRun(summary=None, assembly=None)

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
    return build_token_memory_dry_run_from_selected(
        config=config,
        selected=selected,
        summary=summary,
    )
