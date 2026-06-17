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
    expected_top_level = {
        "relayctx_short_term_source_diagnostics_enabled": False,
        "relayctx_short_term_extraction_dry_run_enabled": False,
        "relayctx_short_term_block_assembly_dry_run_enabled": False,
        "relayctx_short_term_runtime_injection_preflight_enabled": False,
        "relayctx_short_term_runtime_injection_apply_enabled": False,
        "relayctx_short_term_runtime_injection_dry_run_only": True,
        "relayctx_unpack_enabled": False,
        "relayctx_unpack_apply_enabled": False,
        "relayctx_unpack_dry_run_only": True,
        "client_message_canonicalization_dry_run_enabled": False,
        "client_history_exclusion_preflight_enabled": False,
        "client_history_exclusion_apply_enabled": False,
        "client_history_exclusion_apply_dry_run_only": True,
        "client_instruction_extraction_dry_run_enabled": False,
        "client_instruction_cache_lookup_enabled": False,
        "relayint_fast_path_dry_run_enabled": False,
        "relayint_quick_clarification_preflight_enabled": False,
        "relayint_quick_clarification_dry_run_only": True,
        "relayint_quick_clarification_apply_enabled": False,
        "relayint_quick_clarification_apply_dry_run_only": True,
        "relayemo_enabled": False,
        "relayemo_dry_run": True,
        "relayemo_text_marker_enabled": False,
        "relayemo_scene_gate_enabled": True,
        "relayemo_session_state_enabled": False,
        "relayemo_llm_affect_probe_enabled": False,
        "relayemo_llm_affect_probe_dry_run": True,
        "relayemo_llm_affect_probe_skip_when_busy": True,
        "relayrun_checkpoint_write_enabled": False,
        "relayrun_checkpoint_dry_run_only": True,
        "relayrun_resume_preflight_enabled": False,
        "relayrun_resume_dry_run_only": True,
        "relayrun_checkpoint_index_enabled": False,
        "relayrun_checkpoint_index_dry_run_only": True,
        "relayrun_recovery_transition_enabled": False,
        "relayrun_recovery_transition_dry_run_only": True,
        "relayrun_waiting_user_contract_enabled": False,
        "relayrun_waiting_user_contract_dry_run_only": True,
        "relayrun_recovery_apply_preflight_enabled": False,
        "relayrun_recovery_apply_dry_run_only": True,
        "relayrun_recovery_response_draft_enabled": False,
        "relayrun_recovery_response_draft_dry_run_only": True,
        "relayrun_visible_recovery_preflight_enabled": False,
        "relayrun_visible_recovery_dry_run_only": True,
        "relayrun_recovery_response_generator_enabled": False,
        "relayrun_recovery_response_generator_dry_run_only": True,
        "relayrun_output_relayscn_recovery_gate_enabled": False,
        "relayrun_output_relayscn_recovery_gate_dry_run_only": True,
        "relayrun_visible_recovery_apply_preflight_enabled": False,
        "relayrun_visible_recovery_apply_preflight_dry_run_only": True,
        "relayrun_user_action_dry_run_enabled": False,
        "relayrun_user_action_dry_run_only": True,
    }
    expected_memory = {
        "token_policy_shadow_enabled": False,
        "token_budget_truncation_enabled": False,
        "store_enabled": False,
        "retrieval_dry_run_only": True,
        "ctx_block_apply_enabled": False,
        "snippet_extraction_enabled": False,
        "snippet_dry_run_only": True,
        "snippet_apply_enabled": False,
        "snippet_runtime_injection_enabled": False,
        "snippet_runtime_dry_run_only": True,
    }

    require(config.mode == "pass_through", f"{label} mode={config.mode}")
    require(config.trace.enabled is False, f"{label} trace.enabled")

    for field, expected in expected_top_level.items():
        actual = getattr(config, field)
        require(actual is expected, f"{label} {field}={actual!r}; expected {expected!r}")

    require(
        config.relayemo_text_marker_apply_mode == "diagnostics_only",
        f"{label} relayemo_text_marker_apply_mode={config.relayemo_text_marker_apply_mode}",
    )

    for field, expected in expected_memory.items():
        actual = getattr(config.memory, field)
        require(
            actual is expected,
            f"{label} memory.{field}={actual!r}; expected {expected!r}",
        )


def _build_runtime_default_config() -> RelayLMConfig:
    """Instantiate Pydantic defaults without loading config.example.yaml."""

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

    # Check the example's explicitly documented posture.
    example_config = load_config(path)
    _check_safety_posture(example_config, "config.example.yaml")

    # Check the actual Pydantic defaults independently of the example file.
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
