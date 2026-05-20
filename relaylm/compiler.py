"""Persona-stable context compiler primitives for RelayLM MVP-2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StabilityClass(str, Enum):
    STABLE_PREFIX = "stable_prefix"
    SLOW_PREFIX = "slow_prefix"
    DYNAMIC_SUFFIX = "dynamic_suffix"


class BlockType(str, Enum):
    COMMON_RUNTIME_POLICY = "common_runtime_policy"
    CHARACTER_SOUL_ANCHOR = "character_soul_anchor"
    CHARACTER_OUTPUT_POLICY = "character_output_policy"
    ROOM_ANCHOR = "room_anchor"
    RELATIONSHIP_ANCHOR = "relationship_anchor"
    STABLE_MEMORY_SUMMARY = "stable_memory_summary"
    ROOM_STATE = "room_state"
    RETRIEVED_MEMORY = "retrieved_memory"
    RECENT_TURNS = "recent_turns"
    LATEST_INPUT = "latest_input"
    RESPONSE_INSTRUCTION = "response_instruction"


@dataclass(frozen=True)
class ContextBlock:
    block_id: str
    block_type: BlockType
    stability_class: StabilityClass
    source: str
    content: str
    token_budget_hint: int | None = None
    include_in_prefix_cache_target: bool = False


def render_context_blocks(blocks: list[ContextBlock]) -> str:
    """Render context blocks in a stable XML-like envelope.

    MVP-2 intentionally uses plain tags instead of tokenizer-specific special
    tokens. The ordering is supplied by the caller and can be checked with
    ``validate_block_order``.
    """

    lines = ["<relaylm_context version=\"1\">"]
    for block in blocks:
        tag = block.block_type.value
        lines.append(f"  <{tag}>")
        if block.content:
            for line in block.content.splitlines():
                lines.append(f"    {line}")
        lines.append(f"  </{tag}>")
    lines.append("</relaylm_context>")
    return "\n".join(lines)


def validate_block_order(blocks: list[ContextBlock]) -> None:
    """Validate stable_prefix -> slow_prefix -> dynamic_suffix ordering."""

    rank = {
        StabilityClass.STABLE_PREFIX: 0,
        StabilityClass.SLOW_PREFIX: 1,
        StabilityClass.DYNAMIC_SUFFIX: 2,
    }
    previous_rank = -1
    for block in blocks:
        current_rank = rank[block.stability_class]
        if current_rank < previous_rank:
            raise ValueError(
                "Context blocks must be ordered stable_prefix -> slow_prefix -> dynamic_suffix; "
                f"block {block.block_id!r} with {block.stability_class.value!r} was out of order."
            )
        previous_rank = current_rank


def build_placeholder_persona_blocks(
    *,
    common_runtime_policy: str,
    soul: str,
    output_policy: str,
    room_anchor: str,
) -> list[ContextBlock]:
    """Build the first stable prefix block set for MVP-2 smoke tests."""

    return [
        ContextBlock(
            block_id=BlockType.COMMON_RUNTIME_POLICY.value,
            block_type=BlockType.COMMON_RUNTIME_POLICY,
            stability_class=StabilityClass.STABLE_PREFIX,
            source="placeholder/common_runtime_policy",
            content=common_runtime_policy,
            token_budget_hint=200,
            include_in_prefix_cache_target=True,
        ),
        ContextBlock(
            block_id=BlockType.CHARACTER_SOUL_ANCHOR.value,
            block_type=BlockType.CHARACTER_SOUL_ANCHOR,
            stability_class=StabilityClass.STABLE_PREFIX,
            source="placeholder/SOUL.md",
            content=soul,
            token_budget_hint=800,
            include_in_prefix_cache_target=True,
        ),
        ContextBlock(
            block_id=BlockType.CHARACTER_OUTPUT_POLICY.value,
            block_type=BlockType.CHARACTER_OUTPUT_POLICY,
            stability_class=StabilityClass.STABLE_PREFIX,
            source="placeholder/OUTPUT_POLICY.md",
            content=output_policy,
            token_budget_hint=400,
            include_in_prefix_cache_target=True,
        ),
        ContextBlock(
            block_id=BlockType.ROOM_ANCHOR.value,
            block_type=BlockType.ROOM_ANCHOR,
            stability_class=StabilityClass.STABLE_PREFIX,
            source="placeholder/ROOM_ANCHOR.md",
            content=room_anchor,
            token_budget_hint=300,
            include_in_prefix_cache_target=True,
        ),
    ]
