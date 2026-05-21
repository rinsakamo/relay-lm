from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.compiler import BlockType, StabilityClass
from relaylm.memory_candidate import (
    MemoryCandidate,
    build_candidate_memory_block,
    filter_candidates_for_character,
    load_seed_memory_candidates,
    select_memory_candidates,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    candidates = [
        MemoryCandidate(memory_id="shared-style", character_id=None, content="Use short replies.", importance=2, recency=10),
        MemoryCandidate(memory_id="default-project", character_id="default", content="RelayLM project.", importance=5, recency=1),
        MemoryCandidate(memory_id="default-promoted", character_id="default", content="Pinned memory.", importance=1, recency=0, state="promoted", tags=("pin",)),
        MemoryCandidate(memory_id="default-demoted", character_id="default", content="Low priority.", importance=9, recency=99, state="demoted"),
        MemoryCandidate(memory_id="default-disabled", character_id="default", content="Disabled.", importance=10, recency=100, state="disabled"),
        MemoryCandidate(memory_id="other-only", character_id="other", content="Other character.", importance=10, recency=100),
    ]

    default_candidates = filter_candidates_for_character(candidates, character_id="default")
    require([candidate.memory_id for candidate in default_candidates] == [
        "shared-style",
        "default-project",
        "default-promoted",
        "default-demoted",
    ], default_candidates)
    print("ok filter candidates")

    selected = select_memory_candidates(candidates, character_id="default", limit=3)
    require([candidate.memory_id for candidate in selected] == [
        "default-promoted",
        "default-project",
        "shared-style",
    ], selected)
    print("ok select memory candidates")

    limited = select_memory_candidates(candidates, character_id="default", limit=1)
    require([candidate.memory_id for candidate in limited] == ["default-promoted"], limited)
    print("ok selection limit")

    none_selected = select_memory_candidates(candidates, character_id="default", limit=0)
    require(none_selected == [], none_selected)
    print("ok zero selection limit")

    other_selected = select_memory_candidates(candidates, character_id="other", limit=3)
    require([candidate.memory_id for candidate in other_selected] == [
        "other-only",
        "shared-style",
    ], other_selected)
    print("ok character specific selection")

    block = build_candidate_memory_block(selected, token_budget_hint=512)
    require(block is not None, "expected candidate memory block")
    require(block.block_type is BlockType.RETRIEVED_MEMORY, block)
    require(block.stability_class is StabilityClass.SLOW_PREFIX, block)
    require(block.source == "memory_candidate_selection", block)
    require(block.token_budget_hint == 512, block)
    require(block.include_in_prefix_cache_target is False, block)
    require("default-promoted" in block.content, block.content)
    require("tags=pin" in block.content, block.content)
    require(block.content.index("default-promoted") < block.content.index("default-project"), block.content)
    print("ok build candidate memory block")

    empty_block = build_candidate_memory_block([])
    require(empty_block is None, empty_block)
    print("ok empty candidate memory block")

    seed_candidates = load_seed_memory_candidates(REPO_ROOT / "examples" / "memory" / "default_memories.yaml")
    require(len(seed_candidates) == 3, seed_candidates)
    require(seed_candidates[0].memory_id == "default-like-tea", seed_candidates[0])
    require(seed_candidates[0].source == "manual_seed", seed_candidates[0])
    require(seed_candidates[0].state == "active", seed_candidates[0])
    print("ok load seed memory candidates")

    seed_selected = select_memory_candidates(seed_candidates, character_id="default", limit=2)
    require([candidate.memory_id for candidate in seed_selected] == [
        "default-relaylm-project",
        "default-like-tea",
    ], seed_selected)
    seed_block = build_candidate_memory_block(seed_selected)
    require(seed_block is not None, "expected seed candidate block")
    require("default-relaylm-project" in seed_block.content, seed_block.content)
    require("default-like-tea" in seed_block.content, seed_block.content)
    require("shared-short-replies" not in seed_block.content, seed_block.content)
    print("ok seed candidates to memory block")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
