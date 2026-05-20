from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.compiler import render_context_blocks, validate_block_order
from relaylm.config import load_config
from relaylm.profile import ProfileConfigurationError, build_profile_blocks, resolve_profile_files
from relaylm.routing import resolve_route


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")
    files = resolve_profile_files(config, route)

    require(files.common_runtime_policy.exists(), f"missing common policy: {files.common_runtime_policy}")
    require(files.soul.exists(), f"missing soul: {files.soul}")
    require(files.output_policy.exists(), f"missing output policy: {files.output_policy}")
    require(files.room_anchor.exists(), f"missing room anchor: {files.room_anchor}")
    print("ok resolve profile files")

    blocks = build_profile_blocks(files)
    validate_block_order(blocks)
    require([block.block_id for block in blocks] == [
        "common_runtime_policy",
        "character_soul_anchor",
        "character_output_policy",
        "room_anchor",
    ], f"bad blocks: {[block.block_id for block in blocks]}")
    print("ok build config profile blocks")

    rendered = render_context_blocks(blocks)
    require("<common_runtime_policy>" in rendered, rendered)
    require("<character_soul_anchor>" in rendered, rendered)
    require("<character_output_policy>" in rendered, rendered)
    require("<room_anchor>" in rendered, rendered)
    print("ok render config profile context")

    broken_config = config.model_copy(deep=True)
    broken_config.characters.pop(route.character_id or "")
    try:
        resolve_profile_files(broken_config, route)
    except ProfileConfigurationError:
        print("ok missing character error")
    else:
        raise AssertionError("missing character did not raise ProfileConfigurationError")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
