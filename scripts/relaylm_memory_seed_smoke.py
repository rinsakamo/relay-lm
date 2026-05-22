from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.compiler import BlockType, StabilityClass
from relaylm.memory_seed import (
    build_memory_context_block,
    filter_memory_seeds,
    load_memory_seed_file,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    seed_file = load_memory_seed_file(REPO_ROOT / "examples" / "memory" / "default_memories.yaml")
    require(len(seed_file.memories) == 5, seed_file.memories)
    require(seed_file.memories[0].memory_id == "default-like-tea", seed_file.memories[0])
    require(seed_file.memories[0].tags == ("preference",), seed_file.memories[0])
    require(seed_file.memories[0].state == "active", seed_file.memories[0])
    require(seed_file.memories[1].state == "promoted", seed_file.memories[1])
    require(seed_file.memories[3].state == "demoted", seed_file.memories[3])
    print("ok load memory seed file")
    print("ok load memory seed states")

    default_memories = filter_memory_seeds(seed_file, character_id="default")
    require(len(default_memories) == 5, default_memories)
    other_memories = filter_memory_seeds(seed_file, character_id="other")
    require([memory.memory_id for memory in other_memories] == ["shared-short-replies"], other_memories)
    print("ok filter memory seeds")

    block = build_memory_context_block(default_memories)
    require(block is not None, "expected memory block")
    require(block.block_type is BlockType.RETRIEVED_MEMORY, block)
    require(block.stability_class is StabilityClass.SLOW_PREFIX, block)
    require(block.include_in_prefix_cache_target is False, block)
    require("default-relaylm-project" in block.content, block.content)
    require(block.content.index("default-relaylm-project") < block.content.index("default-like-tea"), block.content)
    print("ok build memory context block")

    empty_block = build_memory_context_block([])
    require(empty_block is None, empty_block)
    print("ok empty memory context block")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
