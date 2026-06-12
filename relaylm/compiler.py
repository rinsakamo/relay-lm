"""Persona-stable context compiler primitives for RelayLM MVP-2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from html import escape as escape_html
import json
from typing import Any


CLIENT_INSTRUCTION_ROLES = frozenset({"system", "developer"})
CLIENT_INSTRUCTION_TEXT_PART_TYPES = frozenset({"text", "input_text"})


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
    SCENE_STATE = "scene_state"
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


def _render_block_content(block: ContextBlock) -> str:
    """Render block content while isolating untrusted client evidence.

    Stable profile and RelayLM-owned blocks retain their existing rendering.
    Incoming client instruction evidence is XML-escaped so it cannot close its
    wrapper or spoof sibling RelayLM context blocks.
    """

    if block.block_type == BlockType.INCOMING_SYSTEM_PROMPT:
        return escape_html(block.content, quote=False)
    return block.content


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
        rendered_content = _render_block_content(block)
        if rendered_content:
            for line in rendered_content.splitlines():
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


def build_stable_prefix_hash_diagnostics(
    blocks: list[ContextBlock],
) -> tuple[str | None, list[str] | None]:
    prefix_blocks = [b for b in blocks if b.include_in_prefix_cache_target]
    if not prefix_blocks:
        return None, None

    block_ids = [block.block_id for block in prefix_blocks]
    payload = [
        {
            "block_id": block.block_id,
            "block_type": block.block_type.value,
            "stability_class": block.stability_class.value,
            "content": block.content,
        }
        for block in prefix_blocks
    ]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return digest, block_ids


def summarize_context_blocks(blocks: list[ContextBlock]) -> dict[str, object]:
    """Build machine-readable diagnostics for compiled profile/memory blocks."""

    block_ids = [block.block_id for block in blocks]
    block_types = [block.block_type.value for block in blocks]
    stability_classes = [block.stability_class.value for block in blocks]
    prefix_cache_target_block_ids = [
        block.block_id for block in blocks if block.include_in_prefix_cache_target
    ]
    dynamic_block_ids = [
        block.block_id
        for block in blocks
        if block.stability_class == StabilityClass.DYNAMIC_SUFFIX
    ]

    return {
        "block_count": len(blocks),
        "block_ids": block_ids,
        "block_types": block_types,
        "stability_classes": stability_classes,
        "prefix_cache_target_block_ids": prefix_cache_target_block_ids,
        "dynamic_block_ids": dynamic_block_ids,
        "scene_state_present": any(block.block_type == BlockType.SCENE_STATE for block in blocks),
        "retrieved_memory_present": any(block.block_type == BlockType.RETRIEVED_MEMORY for block in blocks),
    }


def build_persona_source_budget_diagnostics(blocks: list[ContextBlock]) -> dict[str, object]:
    """Build content-free character-source budget diagnostics from profile blocks."""

    source_budgets: dict[str, int] = {
        BlockType.CHARACTER_SOUL_ANCHOR.value: 3200,
        BlockType.CHARACTER_OUTPUT_POLICY.value: 2400,
        BlockType.RELATIONSHIP_ANCHOR.value: 2000,
        BlockType.STABLE_MEMORY_SUMMARY.value: 4000,
        BlockType.SCENE_STATE.value: 1200,
    }
    source_blocks = [block for block in blocks if block.block_id in source_budgets]
    if not source_blocks:
        return {
            "budget_status": "missing",
            "total_source_chars": 0,
            "over_budget_block_ids": [],
            "source_budgets": source_budgets,
            "source_char_counts": {},
            "source_budget_ratios": {},
            "source_warning_count": 0,
        }

    source_char_counts: dict[str, int] = {}
    source_budget_ratios: dict[str, float] = {}
    over_budget_block_ids: list[str] = []
    for block in source_blocks:
        char_count = len(block.content)
        budget = source_budgets[block.block_id]
        source_char_counts[block.block_id] = char_count
        source_budget_ratios[block.block_id] = (char_count / budget) if budget > 0 else 0.0
        if char_count > budget:
            over_budget_block_ids.append(block.block_id)

    return {
        "budget_status": "warning" if over_budget_block_ids else "ok",
        "total_source_chars": sum(source_char_counts.values()),
        "over_budget_block_ids": over_budget_block_ids,
        "source_budgets": source_budgets,
        "source_char_counts": source_char_counts,
        "source_budget_ratios": source_budget_ratios,
        "source_warning_count": len(over_budget_block_ids),
    }


def compile_profile_system_message(blocks: list[ContextBlock]) -> dict[str, str]:
    """Compile context blocks into one OpenAI-compatible system message."""

    validate_block_order(blocks)
    return {"role": "system", "content": render_context_blocks(blocks)}


def split_incoming_system_messages(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split system/developer instruction messages from recent messages.

    The legacy helper name is kept for compatibility. Managed compilation must
    not leave ``developer`` messages in the recent-message chain, because they
    carry instruction authority rather than conversation-turn content.
    """

    instruction_messages: list[dict[str, Any]] = []
    recent_messages: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") in CLIENT_INSTRUCTION_ROLES:
            instruction_messages.append(message)
        else:
            recent_messages.append(message)
    return instruction_messages, recent_messages


def extract_instruction_text(content: Any) -> str | None:
    """Normalize supported string or text-part-array instruction content.

    Textual content parts are concatenated exactly in their original order, and
    only the combined value is trimmed. This preserves boundaries such as
    ``"Return " + "JSON only"`` without inserting or deleting internal
    whitespace. Unsupported non-text parts are ignored rather than stringified.
    """

    if isinstance(content, str):
        normalized = content.strip()
        return normalized or None

    if not isinstance(content, list):
        return None

    text_parts: list[str] = []
    for part in content:
        if isinstance(part, str):
            text_parts.append(part)
        elif isinstance(part, dict) and part.get("type") in CLIENT_INSTRUCTION_TEXT_PART_TYPES:
            value = part.get("text")
            if isinstance(value, str):
                text_parts.append(value)

    normalized = "".join(text_parts).strip()
    return normalized or None


def build_incoming_system_prompt_block(
    system_messages: list[dict[str, Any]],
) -> ContextBlock | None:
    """Build a dynamic evidence block from system/developer messages.

    The legacy helper/block name is kept for compatibility. Incoming client
    instructions are treated as dynamic evidence, not as authority above
    RelayLM's configured persona stable prefix. Rendering escapes this block so
    client text cannot spoof RelayLM context tags.
    """

    contents: list[str] = []
    for message in system_messages:
        content = extract_instruction_text(message.get("content"))
        if content is not None:
            contents.append(content)
    if not contents:
        return None

    return ContextBlock(
        block_id=BlockType.INCOMING_SYSTEM_PROMPT.value,
        block_type=BlockType.INCOMING_SYSTEM_PROMPT,
        stability_class=StabilityClass.DYNAMIC_SUFFIX,
        source="incoming/messages/system_or_developer",
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
    room_anchor: str | None,
    relationship_anchor: str | None = None,
    stable_memory_summary: str | None = None,
    scene_state: str | None = None,
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
    ]

    if room_anchor:
        blocks.append(
            ContextBlock(
                block_id=BlockType.ROOM_ANCHOR.value,
                block_type=BlockType.ROOM_ANCHOR,
                stability_class=StabilityClass.STABLE_PREFIX,
                source="placeholder/ROOM_ANCHOR.md",
                content=room_anchor,
                token_budget_hint=300,
                include_in_prefix_cache_target=True,
            )
        )

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

    if scene_state:
        blocks.append(
            ContextBlock(
                block_id=BlockType.SCENE_STATE.value,
                block_type=BlockType.SCENE_STATE,
                stability_class=StabilityClass.DYNAMIC_SUFFIX,
                source="placeholder/SCENE_STATE.md",
                content=scene_state,
                token_budget_hint=300,
                include_in_prefix_cache_target=False,
            )
        )

    return blocks
