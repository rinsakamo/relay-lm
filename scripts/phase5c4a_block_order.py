"""Typed block-order fixture for Phase 5-C4a smoke."""
from __future__ import annotations

from relaylm.compiler import BlockType, ContextBlock, StabilityClass


def build_blocks() -> list[ContextBlock]:
    return [
        ContextBlock(
            block_id="common_runtime_policy",
            block_type=BlockType.COMMON_RUNTIME_POLICY,
            stability_class=StabilityClass.STABLE_PREFIX,
            source="smoke",
            content="runtime sentinel",
        ),
        ContextBlock(
            block_id="soul",
            block_type=BlockType.CHARACTER_SOUL_ANCHOR,
            stability_class=StabilityClass.STABLE_PREFIX,
            source="smoke",
            content="persona sentinel",
        ),
        ContextBlock(
            block_id="incoming_system_prompt",
            block_type=BlockType.INCOMING_SYSTEM_PROMPT,
            stability_class=StabilityClass.DYNAMIC_SUFFIX,
            source="smoke",
            content="legacy sentinel",
        ),
    ]
