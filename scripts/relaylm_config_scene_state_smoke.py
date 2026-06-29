from __future__ import annotations

import sys
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


def _verify_profile_compile(cfg: RelayLMConfig, expect_scene_state_block: bool) -> None:
    route = resolve_route(cfg, "relaylm-default")
    profile_files = resolve_profile_files(cfg, route)
    require((profile_files.scene_state is not None) == expect_scene_state_block, profile_files)

    blocks = build_profile_blocks(profile_files)
    block_ids = [block.block_id for block in blocks]
    require(("scene_state" in block_ids) == expect_scene_state_block, block_ids)

    plan = build_profile_compile_plan(
        config=cfg,
        route=route,
        incoming_messages=[{"role": "user", "content": "hello"}],
    )
    require(plan.enabled is True, plan)


def main() -> int:
    case1 = _base_character()
    case1["scene_state"] = "examples/profiles/default/SCENE_STATE.md"
    cfg1 = RelayLMConfig.model_validate(_base_config(case1))
    c1 = cfg1.characters["default"]
    require(c1.scene_state == "examples/profiles/default/SCENE_STATE.md", c1)
    _verify_profile_compile(cfg1, expect_scene_state_block=True)
    print("ok current scene_state profile compile")

    case2 = _base_character()
    cfg2 = RelayLMConfig.model_validate(_base_config(case2))
    c2 = cfg2.characters["default"]
    require(c2.scene_state is None, c2)
    _verify_profile_compile(cfg2, expect_scene_state_block=False)
    print("ok no scene_state profile compile")

    print("ok scene_state is the only scene file field")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
