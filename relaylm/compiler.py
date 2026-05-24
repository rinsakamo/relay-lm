"""Persona-stable context compiler primitives for RelayLM MVP-2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


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
    INCOMING_SYSTEM_PROMPT = "incoming_system_prompt"
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


def compile_profile_system_message(blocks: list[ContextBlock]) -> dict[str, str]:
    """Compile context blocks into one OpenAI-compatible system message."""

    validate_block_order(blocks)
    return {"role": "system", "content": render_context_blocks(blocks)}


def split_incoming_system_messages(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split incoming system messages from non-system messages."""

    system_messages: list[dict[str, Any]] = []
    recent_messages: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") == "system":
            system_messages.append(message)
        else:
            recent_messages.append(message)
    return system_messages, recent_messages


def build_incoming_system_prompt_block(
    system_messages: list[dict[str, Any]],
) -> ContextBlock | None:
    """Build a dynamic fallback block from incoming system messages.

    The incoming system prompt is treated as dynamic evidence, not as authority
    above RelayLM's configured persona stable prefix.
    """

    contents: list[str] = []
    for message in system_messages:
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            contents.append(content.strip())
    if not contents:
        return None

    return ContextBlock(
        block_id=BlockType.INCOMING_SYSTEM_PROMPT.value,
        block_type=BlockType.INCOMING_SYSTEM_PROMPT,
        stability_class=StabilityClass.DYNAMIC_SUFFIX,
        source="incoming/messages/system",
        content="\n\n".join(contents),
        token_budget_hint=600,
        include_in_prefix_cache_target=False,
    )


def append_incoming_system_prompt_block(
    blocks: list[ContextBlock],
    system_messages: list[dict[str, Any]],
) -> list[ContextBlock]:
    block = build_incoming_system_prompt_block(system_messages)
    if block is None:
        return list(blocks)
    return [*blocks, block]


def compile_profile_messages(
    blocks: list[ContextBlock],
    recent_messages: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return OpenAI-compatible messages with compiled context first.

    MVP-2 only builds the message layout; runtime pass-through integration comes
    later. Recent messages are appended unchanged after the compiled system
    message so the latest user input stays near the end.
    """

    messages: list[dict[str, Any]] = [compile_profile_system_message(blocks)]
    if recent_messages:
        messages.extend(recent_messages)
    return messages


def compile_profile_messages_with_system_fallback(
    blocks: list[ContextBlock],
    incoming_messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    system_messages, recent_messages = split_incoming_system_messages(incoming_messages)
    compiled_blocks = append_incoming_system_prompt_block(blocks, system_messages)
    return compile_profile_messages(compiled_blocks, recent_messages=recent_messages)


def build_placeholder_persona_blocks(
    *,
    common_runtime_policy: str,
    soul: str,
    output_policy: str,
    room_anchor: str,
    relationship_anchor: str | None = None,
    stable_memory_summary: str | None = None,
    room_state: str | None = None,
) -> list[ContextBlock]:
    """Build the first stable prefix block set for MVP-2 smoke tests."""

    blocks: list[ContextBlock] = [
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

    if relationship_anchor:
        blocks.append(
            ContextBlock(
                block_id=BlockType.RELATIONSHIP_ANCHOR.value,
                block_type=BlockType.RELATIONSHIP_ANCHOR,
                stability_class=StabilityClass.STABLE_PREFIX,
                source="placeholder/RELATIONSHIP_ANCHOR.md",
                content=relationship_anchor,
                token_budget_hint=300,
                include_in_prefix_cache_target=True,
            )
        )

    if stable_memory_summary:
        blocks.append(
            ContextBlock(
                block_id=BlockType.STABLE_MEMORY_SUMMARY.value,
                block_type=BlockType.STABLE_MEMORY_SUMMARY,
                stability_class=StabilityClass.SLOW_PREFIX,
                source="placeholder/STABLE_MEMORY_SUMMARY.md",
                content=stable_memory_summary,
                token_budget_hint=400,
                include_in_prefix_cache_target=False,
            )
        )

    if room_state:
        blocks.append(
            ContextBlock(
                block_id=BlockType.ROOM_STATE.value,
                block_type=BlockType.ROOM_STATE,
                stability_class=StabilityClass.DYNAMIC_SUFFIX,
                source="placeholder/ROOM_STATE.md",
                content=room_state,
                token_budget_hint=300,
                include_in_prefix_cache_target=False,
            )
        )

    return blocks
