from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import load_config
from relaylm.memory_selection import build_configured_candidate_memory_block
from relaylm.routing import resolve_route


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")
    block = build_configured_candidate_memory_block(config=config, route=route)
    require(block is not None, "expected configured candidate memory block")
    require(block.block_type.value == "retrieved_memory", block)
    require(block.token_budget_hint == 800, block)
    require("default-relaylm-project" in block.content, block.content)
    require("default-like-tea" in block.content, block.content)
    require("shared-short-replies" in block.content, block.content)
    print("ok configured candidate memory block")

    limited_config = config.model_copy(deep=True)
    limited_config.memory.candidate_limit = 1
    limited_config.memory.token_budget_hint = 256
    limited_block = build_configured_candidate_memory_block(config=limited_config, route=route)
    require(limited_block is not None, "expected limited candidate memory block")
    require(limited_block.token_budget_hint == 256, limited_block)
    require("default-relaylm-project" in limited_block.content, limited_block.content)
    require("default-like-tea" not in limited_block.content, limited_block.content)
    require("shared-short-replies" not in limited_block.content, limited_block.content)
    print("ok configured candidate limit")
    print("ok configured token budget hint")

    zero_config = config.model_copy(deep=True)
    zero_config.memory.candidate_limit = 0
    zero_block = build_configured_candidate_memory_block(config=zero_config, route=route)
    require(zero_block is None, zero_block)
    print("ok configured zero candidate limit")

    no_seed_config = config.model_copy(deep=True)
    no_seed_config.characters["default"].memory_seed_path = None
    no_seed_block = build_configured_candidate_memory_block(config=no_seed_config, route=route)
    require(no_seed_block is None, no_seed_block)
    print("ok configured missing seed path")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
