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


def _require_exact_fields(raw: dict[str, Any], model: type[Any], label: str) -> None:
    expected = set(model.model_fields)
    actual = set(raw)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    require(not missing, f"{label} missing fields: {missing}")
    require(not unexpected, f"{label} unexpected fields: {unexpected}")


def _check_safety_posture(config: RelayLMConfig, label: str) -> None:
    false_fields = [
        "relayctx_short_term_runtime_injection_apply_enabled",
        "relayctx_unpack_apply_enabled",
        "client_history_exclusion_apply_enabled",
        "relayint_quick_clarification_apply_enabled",
        "relayrun_checkpoint_write_enabled",
        "relayrun_resume_preflight_enabled",
        "relayrun_checkpoint_index_enabled",
        "relayrun_recovery_transition_enabled",
        "relayrun_waiting_user_contract_enabled",
        "relayrun_recovery_apply_preflight_enabled",
        "relayrun_recovery_response_draft_enabled",
        "relayrun_visible_recovery_preflight_enabled",
        "relayrun_recovery_response_generator_enabled",
        "relayrun_output_relayscn_recovery_gate_enabled",
        "relayrun_visible_recovery_apply_preflight_enabled",
        "relayrun_user_action_dry_run_enabled",
    ]
    true_fields = [
        "relayctx_short_term_runtime_injection_dry_run_only",
        "relayctx_unpack_dry_run_only",
        "client_history_exclusion_apply_dry_run_only",
        "relayint_quick_clarification_apply_dry_run_only",
        "relayrun_checkpoint_dry_run_only",
        "relayrun_resume_dry_run_only",
        "relayrun_checkpoint_index_dry_run_only",
        "relayrun_recovery_transition_dry_run_only",
        "relayrun_waiting_user_contract_dry_run_only",
        "relayrun_recovery_apply_dry_run_only",
        "relayrun_recovery_response_draft_dry_run_only",
        "relayrun_visible_recovery_dry_run_only",
        "relayrun_recovery_response_generator_dry_run_only",
        "relayrun_output_relayscn_recovery_gate_dry_run_only",
        "relayrun_visible_recovery_apply_preflight_dry_run_only",
        "relayrun_user_action_dry_run_only",
    ]

    for field in false_fields:
        require(
            getattr(config, field) is False,
            f"{label} unsafe enabled posture: {field}",
        )
    for field in true_fields:
        require(
            getattr(config, field) is True,
            f"{label} unsafe dry-run posture: {field}",
        )

    require(
        config.relayemo_text_marker_enabled is False,
        f"{label} relayemo_text_marker_enabled",
    )
    require(
        config.relayemo_text_marker_apply_mode == "diagnostics_only",
        f"{label} relayemo_text_marker_apply_mode={config.relayemo_text_marker_apply_mode}",
    )
    require(
        config.memory.ctx_block_apply_enabled is False,
        f"{label} memory.ctx_block_apply_enabled",
    )
    require(
        config.memory.snippet_apply_enabled is False,
        f"{label} memory.snippet_apply_enabled",
    )
    require(
        config.memory.snippet_runtime_injection_enabled is False,
        f"{label} memory.snippet_runtime_injection_enabled",
    )
    require(
        config.memory.snippet_runtime_dry_run_only is True,
        f"{label} memory.snippet_runtime_dry_run_only",
    )


def _build_runtime_default_config() -> RelayLMConfig:
    return RelayLMConfig.model_validate(
        {
            "backends": {
                "local": {
                    "type": "openai_compatible",
                    "base_url": "http://127.0.0.1:8000/v1",
                }
            },
            "model_routes": {
                "relaylm-default": {
                    "backend": "local",
                }
            },
        }
    )


def _require_all_mapping_entries(
    raw: object,
    model: type[Any],
    label: str,
) -> None:
    require(isinstance(raw, dict) and bool(raw), f"{label} must be a non-empty mapping")
    for entry_name, entry in raw.items():
        require(isinstance(entry, dict), f"{label}.{entry_name} must be a mapping")
        _require_exact_fields(entry, model, f"{label}.{entry_name}")


def _check_exhaustive_config_example() -> None:
    path = REPO_ROOT / "config.example.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    require(isinstance(raw, dict), type(raw))

    _require_exact_fields(raw, RelayLMConfig, "RelayLMConfig")
    _require_exact_fields(raw["listen"], ListenConfig, "listen")
    _require_exact_fields(raw["trace"], TraceConfig, "trace")
    _require_exact_fields(raw["memory"], MemorySelectionConfig, "memory")
    _require_all_mapping_entries(raw["backends"], BackendConfig, "backends")
    _require_all_mapping_entries(raw["model_routes"], ModelRoute, "model_routes")
    _require_all_mapping_entries(raw["characters"], CharacterConfig, "characters")

    example_config = load_config(path)
    _check_safety_posture(example_config, "config.example.yaml")

    runtime_defaults = _build_runtime_default_config()
    _check_safety_posture(runtime_defaults, "RelayLMConfig defaults")

    require(
        runtime_defaults.memory == MemorySelectionConfig(),
        "RelayLMConfig memory default diverges from MemorySelectionConfig defaults",
    )
    print("ok exhaustive config example matches all current Pydantic fields")
    print("ok every dynamic config entry has exact current fields")
    print("ok config example preserves safe posture")
    print("ok Pydantic runtime defaults preserve safe posture")


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
