from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.compiler import render_context_blocks, validate_block_order
from relaylm.profile import ProfileFiles, build_profile_blocks, load_profile_texts


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    profile_dir = REPO_ROOT / "examples" / "profiles" / "default"
    files = ProfileFiles(
        common_runtime_policy=profile_dir / "common_runtime_policy.md",
        soul=profile_dir / "SOUL.md",
        output_policy=profile_dir / "style.md",
        scene_state=profile_dir / "SCENE_STATE.md",
    )

    texts = load_profile_texts(files)
    require("speakable" in texts.common_runtime_policy, texts.common_runtime_policy)
    require("focused on the current exchange" in texts.common_runtime_policy, texts.common_runtime_policy)
    require("stable identity" in texts.soul, texts.soul)
    require("realtime conversation" in texts.output_policy, texts.output_policy)
    require("synchronous live conversation" in str(texts.scene_state), texts.scene_state)
    require(texts.room_anchor is None, texts.room_anchor)
    print("ok load current profile texts without room anchor")

    blocks = build_profile_blocks(files)
    validate_block_order(blocks)
    require(
        [block.block_id for block in blocks]
        == [
            "common_runtime_policy",
            "character_soul_anchor",
            "character_output_policy",
            "scene_state",
        ],
        [block.block_id for block in blocks],
    )
    print("ok build current profile blocks")

    rendered = render_context_blocks(blocks)
    require("<relaylm_context" in rendered, rendered)
    require("<character_soul_anchor>" in rendered, rendered)
    require("<character_output_policy>" in rendered, rendered)
    require("<scene_state>" in rendered, rendered)
    require("<room_anchor>" not in rendered, rendered)
    print("ok render current profile context")

    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temp_dir:
        room_anchor = Path(temp_dir) / "ROOM_ANCHOR.md"
        room_anchor.write_text("Fixed compatibility room constraint.", encoding="utf-8")
        compatibility_files = ProfileFiles(
            common_runtime_policy=profile_dir / "common_runtime_policy.md",
            soul=profile_dir / "SOUL.md",
            output_policy=profile_dir / "style.md",
            room_anchor=room_anchor,
        )
        compatibility_blocks = build_profile_blocks(compatibility_files)
        require(
            "room_anchor" in [block.block_id for block in compatibility_blocks],
            compatibility_blocks,
        )
    print("ok optional room-anchor compatibility fixture")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
