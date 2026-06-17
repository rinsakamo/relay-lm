from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import (
    BackendConfig,
    CharacterConfig,
    ListenConfig,
    MemorySelectionConfig,
    ModelRoute,
    RelayLMConfig,
    TraceConfig,
    load_config,
)
from relaylm.profile_plan import build_profile_compile_plan
from relaylm.routing import resolve_route


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _require_all_fields(raw: dict[str, Any], model: type[Any], label: str) -> None:
    missing = sorted(set(model.model_fields) - set(raw))
    require(not missing, f"{label} missing fields: {missing}")


def _check_exhaustive_config_example() -> None:
    path = REPO_ROOT / "config.example.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    require(isinstance(raw, dict), type(raw))

    _require_all_fields(raw, RelayLMConfig, "RelayLMConfig")
    _require_all_fields(raw["listen"], ListenConfig, "listen")
    _require_all_fields(raw["trace"], TraceConfig, "trace")
    _require_all_fields(raw["memory"], MemorySelectionConfig, "memory")

    backend = next(iter(raw["backends"].values()))
    route = next(iter(raw["model_routes"].values()))
    character = next(iter(raw["characters"].values()))
    _require_all_fields(backend, BackendConfig, "backend")
    _require_all_fields(route, ModelRoute, "model route")
    _require_all_fields(character, CharacterConfig, "character")

    load_config(path)
    print("ok exhaustive config example matches current Pydantic fields")


def main() -> int:
    _check_exhaustive_config_example()

    config_path = REPO_ROOT / "examples/config/openwebui_lmstudio.yaml"
    config = load_config(config_path)

    require("lmstudio_backend" in config.backends, config.backends)
    backend = config.backends["lmstudio_backend"]
    require(str(backend.base_url) == "http://127.0.0.1:1234/v1", backend)
    print("ok config load and backend")

    require(config.client_history_exclusion_apply_enabled is False, config)
    require(config.client_history_exclusion_apply_dry_run_only is True, config)
    print("ok current history exclusion defaults")

    common_policy = Path(str(config.common_runtime_policy)).read_text(encoding="utf-8")
    require("focused on the current exchange" in common_policy, common_policy)

    incoming_messages = [
        {"role": "system", "content": "Use concise answers."},
        {"role": "user", "content": "hello"},
    ]

    expected = {
        "relaylm-companion": "companion",
        "relaylm-work-assistant": "work_assistant",
        "relaylm-code-reviewer": "code_reviewer",
    }

    for route_model, expected_character_id in expected.items():
        require(route_model in config.model_routes, config.model_routes)
        route = resolve_route(config, route_model)
        require(route.character_id == expected_character_id, route)

        require(expected_character_id in config.characters, config.characters)
        character = config.characters[expected_character_id]
        for path_value in [
            character.soul,
            character.output_policy,
            character.scene_state,
            character.memory_seed_path,
        ]:
            require(isinstance(path_value, str) and Path(path_value).exists(), path_value)

        require(character.room_anchor is None, character)
        scene_state = Path(str(character.scene_state)).read_text(encoding="utf-8")
        require("synchronous live conversation" in scene_state, scene_state)

        plan = build_profile_compile_plan(
            config=config,
            route=route,
            incoming_messages=incoming_messages,
        )
        require(plan.enabled is True, plan)
        require(plan.compiled_block_count == 4, plan)
        require(plan.compiled_message_count == 2, plan)

    print("ok room-anchor content migrated to current owners")
    print("ok openwebui lmstudio copy-ready config routes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
