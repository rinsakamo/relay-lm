from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import load_config
from relaylm.profile_plan import build_profile_compile_plan
from relaylm.routing import resolve_route


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config_path = REPO_ROOT / "examples/config/openwebui_lmstudio.yaml"
    config = load_config(config_path)

    require("lmstudio_backend" in config.backends, config.backends)
    backend = config.backends["lmstudio_backend"]
    require(str(backend.base_url) == "http://127.0.0.1:1234/v1", backend)
    print("ok config load and backend")

    require(config.client_history_exclusion_apply_enabled is False, config)
    require(config.client_history_exclusion_apply_dry_run_only is True, config)
    print("ok current history exclusion defaults")

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

        plan = build_profile_compile_plan(
            config=config,
            route=route,
            incoming_messages=incoming_messages,
        )
        require(plan.enabled is True, plan)
        require(plan.compiled_block_count == 4, plan)
        require(plan.compiled_message_count == 2, plan)

    print("ok openwebui lmstudio copy-ready config routes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
