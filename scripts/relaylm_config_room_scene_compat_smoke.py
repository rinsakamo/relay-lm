from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig
from relaylm.profile import build_profile_blocks, resolve_profile_files
from relaylm.profile_plan import build_profile_compile_plan
from relaylm.routing import resolve_route


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _base_character() -> dict[str, object]:
    return {
        "soul": "examples/profiles/default/SOUL.md",
        "output_policy": "examples/profiles/default/style.md",
    }


def _base_config(character: dict[str, object]) -> dict[str, object]:
    return {
        "common_runtime_policy": "examples/profiles/default/common_runtime_policy.md",
        "backends": {
            "local": {
                "type": "openai_compatible",
                "base_url": "http://127.0.0.1:8000/v1",
                "api_key": "dummy",
            }
        },
        "model_routes": {
            "relaylm-default": {
                "backend": "local",
                "character_id": "default",
            }
        },
        "characters": {"default": character},
    }


def _verify_profile_compile(cfg: RelayLMConfig, expect_room_anchor_block: bool) -> None:
    route = resolve_route(cfg, "relaylm-default")
    profile_files = resolve_profile_files(cfg, route)
    require((profile_files.room_anchor is not None) == expect_room_anchor_block, profile_files)

    blocks = build_profile_blocks(profile_files)
    block_ids = [block.block_id for block in blocks]
    require(("room_anchor" in block_ids) == expect_room_anchor_block, block_ids)

    plan = build_profile_compile_plan(
        config=cfg,
        route=route,
        incoming_messages=[{"role": "user", "content": "hello"}],
    )
    require(plan.enabled is True, plan)


def main() -> int:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temp_dir:
        compatibility_anchor = Path(temp_dir) / "ROOM_ANCHOR.md"
        compatibility_anchor.write_text("Compatibility fixture.", encoding="utf-8")

        case1 = _base_character()
        case1["room_anchor"] = str(compatibility_anchor)
        case1["scene_state"] = "examples/profiles/default/SCENE_STATE.md"
        cfg1 = RelayLMConfig.model_validate(_base_config(case1))
        c1 = cfg1.characters["default"]
        require(c1.room_anchor == str(compatibility_anchor), c1)
        require(c1.scene_state == "examples/profiles/default/SCENE_STATE.md", c1)
        _verify_profile_compile(cfg1, expect_room_anchor_block=True)
        print("ok optional room_anchor + scene_state compatibility")

        case2 = _base_character()
        case2["scene_state"] = "examples/profiles/default/SCENE_STATE.md"
        cfg2 = RelayLMConfig.model_validate(_base_config(case2))
        c2 = cfg2.characters["default"]
        require(c2.room_anchor is None, c2)
        require(c2.scene_state == "examples/profiles/default/SCENE_STATE.md", c2)
        _verify_profile_compile(cfg2, expect_room_anchor_block=False)
        print("ok current scene_state without room_anchor")

        case3 = _base_character()
        case3["room_state"] = "examples/profiles/default/SCENE_STATE.md"
        cfg3 = RelayLMConfig.model_validate(_base_config(case3))
        c3 = cfg3.characters["default"]
        require(c3.room_anchor is None, c3)
        require(c3.scene_state == "examples/profiles/default/SCENE_STATE.md", c3)
        require(c3.room_state == "examples/profiles/default/SCENE_STATE.md", c3)
        _verify_profile_compile(cfg3, expect_room_anchor_block=False)
        print("ok room_state legacy alias to scene_state")

        case4 = _base_character()
        cfg4 = RelayLMConfig.model_validate(_base_config(case4))
        c4 = cfg4.characters["default"]
        require(c4.room_anchor is None, c4)
        require(c4.scene_state is None, c4)
        require(c4.room_state is None, c4)
        _verify_profile_compile(cfg4, expect_room_anchor_block=False)
        print("ok no room_anchor/scene_state for compatibility")

    print("ok no Path(None) TypeError in profile compile path")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
