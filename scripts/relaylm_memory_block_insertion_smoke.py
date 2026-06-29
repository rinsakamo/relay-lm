from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.compiler import (
    append_incoming_system_prompt_block,
    render_context_blocks,
    validate_block_order,
)
from relaylm.config import load_config
from relaylm.memory_context import build_seed_memory_block, insert_memory_block
from relaylm.profile import build_profile_blocks, resolve_profile_files
from relaylm.routing import resolve_route


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")
    profile_files = resolve_profile_files(config, route)
    profile_blocks = build_profile_blocks(profile_files)

    memory_block = build_seed_memory_block(
        seed_path=REPO_ROOT / "examples" / "memory" / "default_memories.yaml",
        character_id=route.character_id,
    )
    blocks_with_memory = insert_memory_block(
        profile_blocks=profile_blocks,
        memory_block=memory_block,
    )
    require(len(blocks_with_memory) == len(profile_blocks) + 1, blocks_with_memory)
    require(blocks_with_memory[-2].block_type.value == "retrieved_memory", blocks_with_memory[-2])
    validate_block_order(blocks_with_memory)
    print("ok insert memory block")

    final_blocks = append_incoming_system_prompt_block(
        blocks_with_memory,
        [{"role": "system", "content": "Keep this session concise."}],
    )
    validate_block_order(final_blocks)
    block_order = [block.block_type.value for block in final_blocks]
    require(block_order == [
        "common_runtime_policy",
        "character_soul_anchor",
        "character_output_policy",
        "retrieved_memory",
        "scene_state",
        "incoming_system_prompt",
    ], block_order)
    print("ok memory before current scene and incoming system fallback")

    rendered = render_context_blocks(final_blocks)
    require("<retrieved_memory>" in rendered, rendered)
    require("default-relaylm-project" in rendered, rendered)
    require(rendered.index("<retrieved_memory>") < rendered.index("<scene_state>"), rendered)
    require(rendered.index("<scene_state>") < rendered.index("<incoming_system_prompt>"), rendered)
    print("ok render memory context")

    no_memory_blocks = insert_memory_block(
        profile_blocks=profile_blocks,
        memory_block=None,
    )
    require(no_memory_blocks == profile_blocks, no_memory_blocks)
    print("ok no memory block unchanged")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
