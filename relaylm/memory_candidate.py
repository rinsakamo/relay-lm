"""Memory candidate schema and deterministic selection for RelayLM MVP-4."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from relaylm.compiler import BlockType, ContextBlock, StabilityClass
from relaylm.memory_seed import MemorySeed, load_memory_seed_file


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


@dataclass(frozen=True)
class MemorySelectionSummary:
    total_candidates: int
    eligible_count: int
    selected_count: int
    limit: int
    character_id: str | None
    selected_memory_ids: list[str]
    excluded_disabled_ids: list[str]
    excluded_character_ids: list[str]
    state_counts: dict[str, int]

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MemoryBlockAssembly:
    block: ContextBlock | None
    included_memory_ids: list[str]
    dropped_memory_ids: list[str]
    character_budget: int | None
    rendered_characters: int

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)


def candidate_from_memory_seed(seed: MemorySeed) -> MemoryCandidate:
    return MemoryCandidate(
        memory_id=seed.memory_id,
        content=seed.content,
        character_id=seed.character_id,
        importance=seed.importance,
        recency=0,
        state=seed.state,
        tags=seed.tags,
        source=seed.source,
    )


def load_seed_memory_candidates(path: str | Path) -> list[MemoryCandidate]:
    seed_file = load_memory_seed_file(path)
    return [candidate_from_memory_seed(seed) for seed in seed_file.memories]


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


def summarize_memory_selection(
    candidates: list[MemoryCandidate],
    *,
    character_id: str | None,
    limit: int,
    selected: list[MemoryCandidate] | None = None,
) -> MemorySelectionSummary:
    selected_candidates = selected
    if selected_candidates is None:
        selected_candidates = select_memory_candidates(
            candidates,
            character_id=character_id,
            limit=limit,
        )

    eligible = filter_candidates_for_character(candidates, character_id=character_id)
    state_counts = {"active": 0, "promoted": 0, "demoted": 0, "disabled": 0}
    excluded_disabled_ids: list[str] = []
    excluded_character_ids: list[str] = []

    for candidate in candidates:
        state_counts[candidate.state] += 1
        if candidate.state == "disabled":
            excluded_disabled_ids.append(candidate.memory_id)
        elif candidate.character_id is not None and candidate.character_id != character_id:
            excluded_character_ids.append(candidate.memory_id)

    return MemorySelectionSummary(
        total_candidates=len(candidates),
        eligible_count=len(eligible),
        selected_count=len(selected_candidates),
        limit=limit,
        character_id=character_id,
        selected_memory_ids=[candidate.memory_id for candidate in selected_candidates],
        excluded_disabled_ids=sorted(excluded_disabled_ids),
        excluded_character_ids=sorted(excluded_character_ids),
        state_counts=state_counts,
    )


def _render_candidate_line(candidate: MemoryCandidate) -> str:
    tag_text = f" tags={','.join(candidate.tags)}" if candidate.tags else ""
    return (
        f"- [{candidate.memory_id} score={candidate.score()} state={candidate.state}{tag_text}] "
        f"{candidate.content.strip()}"
    )


def assemble_candidate_memory_block(
    candidates: list[MemoryCandidate],
    *,
    block_id: str = "selected_memory_candidates",
    token_budget_hint: int = 800,
    character_budget: int | None = None,
) -> MemoryBlockAssembly:
    if not candidates:
        return MemoryBlockAssembly(
            block=None,
            included_memory_ids=[],
            dropped_memory_ids=[],
            character_budget=character_budget,
            rendered_characters=0,
        )

    lines: list[str] = []
    included_memory_ids: list[str] = []
    dropped_memory_ids: list[str] = []

    for candidate in candidates:
        line = _render_candidate_line(candidate)
        next_content = "\n".join([*lines, line]) if lines else line
        if character_budget is not None and len(next_content) > character_budget:
            dropped_memory_ids.append(candidate.memory_id)
            continue
        lines.append(line)
        included_memory_ids.append(candidate.memory_id)

    if not lines:
        return MemoryBlockAssembly(
            block=None,
            included_memory_ids=[],
            dropped_memory_ids=dropped_memory_ids,
            character_budget=character_budget,
            rendered_characters=0,
        )

    content = "\n".join(lines)
    return MemoryBlockAssembly(
        block=ContextBlock(
            block_id=block_id,
            block_type=BlockType.RETRIEVED_MEMORY,
            stability_class=StabilityClass.SLOW_PREFIX,
            source="memory_candidate_selection",
            content=content,
            token_budget_hint=token_budget_hint,
            include_in_prefix_cache_target=False,
        ),
        included_memory_ids=included_memory_ids,
        dropped_memory_ids=dropped_memory_ids,
        character_budget=character_budget,
        rendered_characters=len(content),
    )


def build_candidate_memory_block(
    candidates: list[MemoryCandidate],
    *,
    block_id: str = "selected_memory_candidates",
    token_budget_hint: int = 800,
    character_budget: int | None = None,
) -> ContextBlock | None:
    return assemble_candidate_memory_block(
        candidates,
        block_id=block_id,
        token_budget_hint=token_budget_hint,
        character_budget=character_budget,
    ).block
