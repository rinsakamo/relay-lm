"""RelayLM runtime config loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, HttpUrl


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


class CharacterConfig(BaseModel):
    common_runtime_policy: str | None = None
    soul: str
    output_policy: str
    room_anchor: str
    memory_seed_path: str | None = None
    relationship_anchor: str | None = None
    stable_memory_summary: str | None = None
    room_state: str | None = None
    token_policy_shadow_enabled: bool | None = None


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
    memory: MemorySelectionConfig = Field(default_factory=MemorySelectionConfig)
    backends: dict[str, BackendConfig]
    model_routes: dict[str, ModelRoute]
    characters: dict[str, CharacterConfig] = Field(default_factory=dict)


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
