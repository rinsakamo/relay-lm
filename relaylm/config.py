"""RelayLM runtime config loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, HttpUrl, model_validator


Mode = Literal["pass_through", "memory_light", "memory_full"]


class ListenConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8090


class BackendConfig(BaseModel):
    type: Literal["openai_compatible"] = "openai_compatible"
    base_url: HttpUrl
    api_key: str | None = None
    default_model: str | None = None
    timeout_seconds: float = 60.0


class TraceConfig(BaseModel):
    enabled: bool = False
    path: str | None = None


class MemorySelectionConfig(BaseModel):
    candidate_limit: int = 3
    token_budget_hint: int = 800
    character_budget: int | None = None
    token_budget: int | None = Field(default=None, gt=0)
    chars_per_token: int = Field(default=4, gt=0)
    token_policy_shadow_enabled: bool = False
    token_budget_truncation_enabled: bool = False
    root_path: str | None = None
    store_enabled: bool = False
    retrieval_dry_run_only: bool = True
    ctx_block_apply_enabled: bool = False
    snippet_extraction_enabled: bool = False
    snippet_dry_run_only: bool = True
    snippet_apply_enabled: bool = False
    snippet_runtime_injection_enabled: bool = False
    snippet_runtime_dry_run_only: bool = True
    snippet_budget: int = Field(default=512, gt=0)
    max_snippet_chars: int = Field(default=512, gt=0)
    max_snippet_candidates: int = Field(default=3, ge=0)


class CharacterConfig(BaseModel):
    common_runtime_policy: str | None = None
    soul: str
    output_policy: str
    room_anchor: str | None = None
    memory_seed_path: str | None = None
    relationship_anchor: str | None = None
    stable_memory_summary: str | None = None
    scene_state: str | None = None
    room_state: str | None = None
    token_policy_shadow_enabled: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _apply_scene_state_alias(cls, raw: Any) -> Any:
        if not isinstance(raw, dict):
            return raw
        if raw.get("scene_state") is None and raw.get("room_state") is not None:
            raw = dict(raw)
            raw["scene_state"] = raw.get("room_state")
        return raw


class ModelRoute(BaseModel):
    backend: str
    backend_model: str | None = None
    character_id: str | None = None
    mode: Mode | None = None
    cache_namespace: str | None = None
    memory_namespace: str | None = None
    user_id: str | None = None
    user_type: str | None = None
    room_id: str | None = None
    scene_id: str | None = None
    session_id: str | None = None


class RelayLMConfig(BaseModel):
    mode: Mode = "pass_through"
    listen: ListenConfig = Field(default_factory=ListenConfig)
    common_runtime_policy: str | None = None
    trace: TraceConfig = Field(default_factory=TraceConfig)
    relayctx_short_term_source_diagnostics_enabled: bool = False
    relayctx_short_term_extraction_dry_run_enabled: bool = False
    relayctx_short_term_block_assembly_dry_run_enabled: bool = False
    relayctx_short_term_runtime_injection_preflight_enabled: bool = False
    relayctx_short_term_runtime_injection_apply_enabled: bool = False
    relayctx_short_term_runtime_injection_dry_run_only: bool = True
    relayctx_short_term_runtime_injection_token_budget: int = Field(default=400, gt=0)
    relayctx_unpack_enabled: bool = False
    relayctx_unpack_apply_enabled: bool = False
    relayctx_unpack_dry_run_only: bool = True
    relayctx_unpack_max_update_chars: int = Field(default=4096, gt=0)
    client_message_canonicalization_dry_run_enabled: bool = False
    client_history_exclusion_preflight_enabled: bool = False
    client_history_exclusion_apply_enabled: bool = False
    client_history_exclusion_apply_dry_run_only: bool = True
    client_instruction_extraction_dry_run_enabled: bool = False
    client_instruction_cache_lookup_enabled: bool = False
    client_instruction_cache_root: str | None = None
    client_instruction_cache_max_entry_bytes: int = Field(
        default=65536,
        ge=1,
        le=1048576,
    )
    relayint_fast_path_dry_run_enabled: bool = False
    relayint_fast_path_high_confidence_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    relayint_fast_path_low_confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    relayint_quick_clarification_preflight_enabled: bool = False
    relayint_quick_clarification_dry_run_only: bool = True
    relayint_quick_clarification_apply_enabled: bool = False
    relayint_quick_clarification_apply_dry_run_only: bool = True
    relayint_quick_clarification_response_max_chars: int = Field(default=120, gt=0)
    memory: MemorySelectionConfig = Field(default_factory=MemorySelectionConfig)
    backends: dict[str, BackendConfig]
    model_routes: dict[str, ModelRoute]
    characters: dict[str, CharacterConfig] = Field(default_factory=dict)
    relayemo_enabled: bool = False
    relayemo_dry_run: bool = True
    relayemo_text_marker_enabled: bool = False
    relayemo_text_marker_apply_mode: Literal["diagnostics_only", "preview", "apply"] = (
        "diagnostics_only"
    )
    relayemo_marker_open_threshold: float = 0.65
    relayemo_marker_close_threshold: float = 0.45
    relayemo_max_markers: int = Field(default=3, ge=1, le=3)
    relayemo_scene_gate_enabled: bool = True
    relayemo_session_state_enabled: bool = False
    relayemo_session_state_ttl_seconds: int = Field(default=1800, ge=1)
    relayemo_session_state_max_entries: int = Field(default=256, ge=1)
    relayemo_affect_probe_mode: Literal["heuristic", "llm_structured_dry_run"] = "heuristic"
    relayemo_llm_affect_probe_enabled: bool = False
    relayemo_llm_affect_probe_dry_run: bool = True
    relayemo_llm_affect_probe_max_input_chars: int = Field(default=2000, ge=1)
    relayemo_llm_affect_probe_timeout_ms: int = Field(default=1500, ge=1)
    relayemo_llm_affect_probe_max_output_tokens: int = Field(default=160, ge=1)
    relayemo_llm_affect_probe_skip_when_busy: bool = True
    relayemo_llm_affect_probe_every_n_turns: int = Field(default=1, ge=1)
    relayrun_checkpoint_write_enabled: bool = False
    relayrun_checkpoint_root: str = ".relayrun/checkpoints"
    relayrun_checkpoint_dry_run_only: bool = True
    relayrun_resume_preflight_enabled: bool = False
    relayrun_resume_dry_run_only: bool = True
    relayrun_checkpoint_index_enabled: bool = False
    relayrun_checkpoint_index_dry_run_only: bool = True
    relayrun_checkpoint_index_max_files: int = Field(default=100, ge=1)
    relayrun_recovery_transition_enabled: bool = False
    relayrun_recovery_transition_dry_run_only: bool = True
    relayrun_waiting_user_contract_enabled: bool = False
    relayrun_waiting_user_contract_dry_run_only: bool = True
    relayrun_recovery_apply_preflight_enabled: bool = False
    relayrun_recovery_apply_dry_run_only: bool = True
    relayrun_recovery_response_draft_enabled: bool = False
    relayrun_recovery_response_draft_dry_run_only: bool = True
    relayrun_visible_recovery_preflight_enabled: bool = False
    relayrun_visible_recovery_dry_run_only: bool = True
    relayrun_recovery_response_generator_enabled: bool = False
    relayrun_recovery_response_generator_dry_run_only: bool = True
    relayrun_output_relayscn_recovery_gate_enabled: bool = False
    relayrun_output_relayscn_recovery_gate_dry_run_only: bool = True
    relayrun_visible_recovery_apply_preflight_enabled: bool = False
    relayrun_visible_recovery_apply_preflight_dry_run_only: bool = True
    relayrun_user_action_dry_run_enabled: bool = False
    relayrun_user_action_dry_run_only: bool = True


def default_config_path() -> Path:
    env_path = os.environ.get("RELAYLM_CONFIG")
    if env_path:
        return Path(env_path)
    return Path("config.yaml")


def load_config(path: str | Path | None = None) -> RelayLMConfig:
    config_path = Path(path) if path is not None else default_config_path()
    if not config_path.exists():
        raise FileNotFoundError(
            f"RelayLM config not found: {config_path}. "
            "Set RELAYLM_CONFIG or create config.yaml. "
            "Use config.example.yaml as a starting point."
        )

    with config_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    return RelayLMConfig.model_validate(raw)
