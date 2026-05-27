from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _base_character() -> dict[str, object]:
    return {
        "soul": "./characters/default/SOUL.md",
        "output_policy": "./characters/default/OUTPUT_POLICY.md",
    }


def _base_config(character: dict[str, object]) -> dict[str, object]:
    return {
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
        "characters": {
            "default": character,
        },
    }


def main() -> int:
    case1 = _base_character()
    case1["room_anchor"] = "./rooms/default/ROOM_ANCHOR.md"
    case1["scene_state"] = "./scenes/default/SCENE_STATE.md"
    cfg1 = RelayLMConfig.model_validate(_base_config(case1))
    c1 = cfg1.characters["default"]
    require(c1.room_anchor == "./rooms/default/ROOM_ANCHOR.md", c1)
    require(c1.scene_state == "./scenes/default/SCENE_STATE.md", c1)
    print("ok room_anchor + scene_state")

    case2 = _base_character()
    case2["scene_state"] = "./scenes/default/SCENE_STATE.md"
    cfg2 = RelayLMConfig.model_validate(_base_config(case2))
    c2 = cfg2.characters["default"]
    require(c2.room_anchor is None, c2)
    require(c2.scene_state == "./scenes/default/SCENE_STATE.md", c2)
    print("ok scene_state without room_anchor")

    case3 = _base_character()
    case3["room_state"] = "./scenes/default/LEGACY_ROOM_STATE.md"
    cfg3 = RelayLMConfig.model_validate(_base_config(case3))
    c3 = cfg3.characters["default"]
    require(c3.room_anchor is None, c3)
    require(c3.scene_state == "./scenes/default/LEGACY_ROOM_STATE.md", c3)
    require(c3.room_state == "./scenes/default/LEGACY_ROOM_STATE.md", c3)
    print("ok room_state legacy alias to scene_state")

    case4 = _base_character()
    cfg4 = RelayLMConfig.model_validate(_base_config(case4))
    c4 = cfg4.characters["default"]
    require(c4.room_anchor is None, c4)
    require(c4.scene_state is None, c4)
    require(c4.room_state is None, c4)
    print("ok no room_anchor/scene_state for pass-through compatibility")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
