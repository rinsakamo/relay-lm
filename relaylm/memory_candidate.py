"""Memory candidate schema and deterministic selection for RelayLM MVP-4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from relaylm.compiler import BlockType, ContextBlock, StabilityClass


MemoryCandidateState = Literal["active", "promoted", "demoted", "disabled"]


@dataclass(frozen=True)
class MemoryCandidate:
    memory_id: str
    content: str
    character_id: str | None = None
    importance: int = 1
    recency: int = 0
    state: MemoryCandidateState = "active"
    tags: tuple[str, ...] = field(default_factory=tuple)
    source: str = "manual"

    def score(self) -> int:
        state_bonus = {
            "promoted": 1000,
            "active": 0,
            "demoted": -1000,
            "disabled": -100000,
        }[self.state]
        return state_bonus + (self.importance * 100) + self.recency


def filter_candidates_for_character(
    candidates: list[MemoryCandidate],
    *,
    character_id: str | None,
) -> list[MemoryCandidate]:
    return [
        candidate
        for candidate in candidates
        if candidate.state != "disabled"
        and (candidate.character_id is None or candidate.character_id == character_id)
    ]


def select_memory_candidates(
    candidates: list[MemoryCandidate],
    *,
    character_id: str | None,
    limit: int,
) -> list[MemoryCandidate]:
    if limit <= 0:
        return []
    eligible = filter_candidates_for_character(candidates, character_id=character_id)
    return sorted(
        eligible,
        key=lambda candidate: (-candidate.score(), candidate.memory_id),
    )[:limit]


def build_candidate_memory_block(
    candidates: list[MemoryCandidate],
    *,
    block_id: str = "selected_memory_candidates",
    token_budget_hint: int = 800,
) -> ContextBlock | None:
    if not candidates:
        return None

    lines: list[str] = []
    for candidate in candidates:
        tag_text = f" tags={','.join(candidate.tags)}" if candidate.tags else ""
        lines.append(
            f"- [{candidate.memory_id} score={candidate.score()} state={candidate.state}{tag_text}] "
            f"{candidate.content.strip()}"
        )

    return ContextBlock(
        block_id=block_id,
        block_type=BlockType.RETRIEVED_MEMORY,
        stability_class=StabilityClass.SLOW_PREFIX,
        source="memory_candidate_selection",
        content="\n".join(lines),
        token_budget_hint=token_budget_hint,
        include_in_prefix_cache_target=False,
    )
