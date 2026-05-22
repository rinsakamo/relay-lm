"""Token-estimated memory assembly helpers for RelayLM MVP-7."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from relaylm.compiler import BlockType, ContextBlock, StabilityClass
from relaylm.memory_candidate import MemoryCandidate
from relaylm.token_budget import estimate_text_tokens, fits_token_budget


@dataclass(frozen=True)
class TokenBudgetMemoryAssembly:
    block: ContextBlock | None
    included_memory_ids: list[str]
    dropped_memory_ids: list[str]
    token_budget: int | None
    estimated_tokens: int
    rendered_characters: int
    chars_per_token: int

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)


def render_token_budget_candidate_line(candidate: MemoryCandidate) -> str:
    tag_text = f" tags={','.join(candidate.tags)}" if candidate.tags else ""
    return (
        f"- [{candidate.memory_id} score={candidate.score()} state={candidate.state}{tag_text}] "
        f"{candidate.content.strip()}"
    )


def assemble_token_budget_memory_block(
    candidates: list[MemoryCandidate],
    *,
    block_id: str = "selected_memory_candidates",
    token_budget_hint: int = 800,
    token_budget: int | None = None,
    chars_per_token: int = 4,
) -> TokenBudgetMemoryAssembly:
    lines: list[str] = []
    included_memory_ids: list[str] = []
    dropped_memory_ids: list[str] = []

    for candidate in candidates:
        line = render_token_budget_candidate_line(candidate)
        next_content = "\n".join([*lines, line]) if lines else line
        if not fits_token_budget(
            next_content,
            token_budget=token_budget,
            chars_per_token=chars_per_token,
        ):
            dropped_memory_ids.append(candidate.memory_id)
            continue
        lines.append(line)
        included_memory_ids.append(candidate.memory_id)

    if not lines:
        return TokenBudgetMemoryAssembly(
            block=None,
            included_memory_ids=[],
            dropped_memory_ids=dropped_memory_ids,
            token_budget=token_budget,
            estimated_tokens=0,
            rendered_characters=0,
            chars_per_token=chars_per_token,
        )

    content = "\n".join(lines)
    estimate = estimate_text_tokens(content, chars_per_token=chars_per_token)
    return TokenBudgetMemoryAssembly(
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
        token_budget=token_budget,
        estimated_tokens=estimate.estimated_tokens,
        rendered_characters=len(content),
        chars_per_token=chars_per_token,
    )
