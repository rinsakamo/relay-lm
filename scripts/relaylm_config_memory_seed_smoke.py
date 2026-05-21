from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.compiler import render_context_blocks, validate_block_order
from relaylm.config import load_config
from relaylm.memory_context import insert_memory_block, resolve_seed_memory_block
from relaylm.profile import build_profile_blocks, resolve_profile_files
from relaylm.routing import resolve_route


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")
    memory_block = resolve_seed_memory_block(config, route)
    require(memory_block is not None, "expected memory block")
    require(memory_block.block_type.value == "retrieved_memory", memory_block)
    require("default-relaylm-project" in memory_block.content, memory_block.content)
    print("ok resolve seed memory block")

    profile_files = resolve_profile_files(config, route)
    profile_blocks = build_profile_blocks(profile_files)
    blocks = insert_memory_block(profile_blocks=profile_blocks, memory_block=memory_block)
    validate_block_order(blocks)
    rendered = render_context_blocks(blocks)
    require("<retrieved_memory>" in rendered, rendered)
    require(rendered.index("<room_anchor>") < rendered.index("<retrieved_memory>"), rendered)
    print("ok insert config memory block")

    no_memory_config = config.model_copy(deep=True)
    no_memory_config.characters["default"].memory_seed_path = None
    no_memory_block = resolve_seed_memory_block(no_memory_config, route)
    require(no_memory_block is None, no_memory_block)
    print("ok missing seed path gives no block")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
