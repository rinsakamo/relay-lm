from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.compiler import (
    BlockType,
    ContextBlock,
    StabilityClass,
    build_placeholder_persona_blocks,
    render_context_blocks,
    validate_block_order,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    blocks = build_placeholder_persona_blocks(
        common_runtime_policy="Keep replies speakable and do not reveal internal tags.",
        soul="You are a stable AI character with a consistent worldview.",
        output_policy="Speak warmly and keep responses suitable for TTS.",
        relationship_anchor="Maintain the established relationship tone.",
        scene_state="This is a live conversation scene.",
    )

    require([block.block_id for block in blocks] == [
        "common_runtime_policy",
        "character_soul_anchor",
        "character_output_policy",
        "relationship_anchor",
        "scene_state",
    ], f"bad block order: {[block.block_id for block in blocks]}")
    require(
        all(block.stability_class is StabilityClass.STABLE_PREFIX for block in blocks[:4]),
        "expected stable prefix persona blocks",
    )
    require(blocks[-1].stability_class is StabilityClass.DYNAMIC_SUFFIX, "expected dynamic scene state")
    require(all(block.include_in_prefix_cache_target for block in blocks[:4]), "expected prefix cache target blocks")
    require(blocks[-1].include_in_prefix_cache_target is False, "scene_state must not be a cache target")
    validate_block_order(blocks)
    print("ok current persona blocks")

    rendered = render_context_blocks(blocks)
    require(rendered.startswith('<relaylm_context version="1">'), rendered)
    require("<common_runtime_policy>" in rendered, rendered)
    require("<character_soul_anchor>" in rendered, rendered)
    require("<character_output_policy>" in rendered, rendered)
    require("<relationship_anchor>" in rendered, rendered)
    require("<scene_state>" in rendered, rendered)
    require("room_anchor" not in rendered, rendered)
    require(rendered.endswith("</relaylm_context>"), rendered)
    print("ok render context blocks")

    bad_blocks = [
        ContextBlock(
            block_id="latest_input",
            block_type=BlockType.LATEST_INPUT,
            stability_class=StabilityClass.DYNAMIC_SUFFIX,
            source="test",
            content="hello",
        ),
        ContextBlock(
            block_id="character_soul_anchor",
            block_type=BlockType.CHARACTER_SOUL_ANCHOR,
            stability_class=StabilityClass.STABLE_PREFIX,
            source="test",
            content="soul",
        ),
    ]
    try:
        validate_block_order(bad_blocks)
    except ValueError:
        print("ok invalid order error")
    else:
        raise AssertionError("invalid block order did not raise ValueError")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
