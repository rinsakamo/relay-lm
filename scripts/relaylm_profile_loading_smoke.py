from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.compiler import render_context_blocks, validate_block_order
from relaylm.profile import ProfileFiles, build_profile_blocks, load_profile_texts


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    profile_dir = REPO_ROOT / "examples" / "profiles" / "default"
    files = ProfileFiles(
        common_runtime_policy=profile_dir / "common_runtime_policy.md",
        soul=profile_dir / "SOUL.md",
        output_policy=profile_dir / "style.md",
        room_anchor=profile_dir / "ROOM_ANCHOR.md",
    )

    texts = load_profile_texts(files)
    require("speakable" in texts.common_runtime_policy, texts.common_runtime_policy)
    require("stable identity" in texts.soul, texts.soul)
    require("realtime conversation" in texts.output_policy, texts.output_policy)
    require("live conversation room" in texts.room_anchor, texts.room_anchor)
    print("ok load profile texts")

    blocks = build_profile_blocks(files)
    validate_block_order(blocks)
    require([block.block_id for block in blocks] == [
        "common_runtime_policy",
        "character_soul_anchor",
        "character_output_policy",
        "room_anchor",
    ], f"bad blocks: {[block.block_id for block in blocks]}")
    print("ok build profile blocks")

    rendered = render_context_blocks(blocks)
    require("<relaylm_context" in rendered, rendered)
    require("<character_soul_anchor>" in rendered, rendered)
    require("<character_output_policy>" in rendered, rendered)
    require("<room_anchor>" in rendered, rendered)
    print("ok render profile context")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
