"""Model-name routing for RelayLM."""

from __future__ import annotations

from dataclasses import dataclass

from relaylm.config import BackendConfig, ModelRoute, RelayLMConfig


@dataclass(frozen=True)
class ResolvedRoute:
    route_model: str
    backend_name: str
    backend: BackendConfig
    backend_model: str
    character_id: str | None
    mode_requested: str
    mode_applied: str
    cache_namespace: str | None
    memory_namespace: str | None
    user_id: str | None = None
    user_type: str | None = None
    room_id: str | None = None
    scene_id: str | None = None
    session_id: str | None = None
    relayctx_unpack_enabled: bool = False
    relayctx_unpack_apply_enabled: bool = False
    relayctx_unpack_dry_run_only: bool = True
    relayctx_unpack_max_update_chars: int = 4096
    relayctx_stream_unpack_dry_run_enabled: bool = False
    relayctx_stream_unpack_dry_run_only: bool = True
    relayctx_stream_unpack_max_buffer_chars: int = 256
    relayctx_tts_adapter_handoff_runtime_enabled: bool = False
    relayctx_tts_adapter_handoff_runtime_dry_run_only: bool = True
    relayctx_tts_adapter_handoff_max_segment_chars: int = 120
    relayctx_tts_adapter_handoff_min_segment_chars: int = 8
    client_message_canonicalization_dry_run_enabled: bool = False
    client_history_exclusion_preflight_enabled: bool = False
    client_history_exclusion_apply_enabled: bool = False
    client_history_exclusion_apply_dry_run_only: bool = True
    client_instruction_extraction_dry_run_enabled: bool = False
    client_instruction_cache_lookup_enabled: bool = False
    client_instruction_cache_root: str | None = None
    client_instruction_cache_max_entry_bytes: int = 65536
    client_instruction_typed_parse_enabled: bool = False
    client_instruction_cache_write_enabled: bool = False
    client_instruction_cache_write_dry_run_only: bool = True


class RouteNotFoundError(ValueError):
    """Raised when an incoming model name does not match a RelayLM route."""


class RouteConfigurationError(ValueError):
    """Raised when a matched route references invalid server-side config."""


def resolve_route(config: RelayLMConfig, model: str) -> ResolvedRoute:
    route: ModelRoute | None = config.model_routes.get(model)
    if route is None:
        raise RouteNotFoundError(f"No RelayLM model route configured for model: {model}")

    backend = config.backends.get(route.backend)
    if backend is None:
        raise RouteConfigurationError(
            f"RelayLM route {model} references missing backend: {route.backend}"
        )

    backend_model = route.backend_model or backend.default_model or model
    mode = route.mode or config.mode

    return ResolvedRoute(
        route_model=model,
        backend_name=route.backend,
        backend=backend,
        backend_model=backend_model,
        character_id=route.character_id,
        mode_requested=route.mode or config.mode,
        mode_applied=mode,
        cache_namespace=route.cache_namespace,
        memory_namespace=route.memory_namespace,
        user_id=route.user_id,
        user_type=route.user_type,
        room_id=route.room_id,
        scene_id=route.scene_id,
        session_id=route.session_id,
        relayctx_unpack_enabled=config.relayctx_unpack_enabled,
        relayctx_unpack_apply_enabled=config.relayctx_unpack_apply_enabled,
        relayctx_unpack_dry_run_only=config.relayctx_unpack_dry_run_only,
        relayctx_unpack_max_update_chars=config.relayctx_unpack_max_update_chars,
        relayctx_stream_unpack_dry_run_enabled=(
            config.relayctx_stream_unpack_dry_run_enabled
        ),
        relayctx_stream_unpack_dry_run_only=config.relayctx_stream_unpack_dry_run_only,
        relayctx_stream_unpack_max_buffer_chars=(
            config.relayctx_stream_unpack_max_buffer_chars
        ),
        relayctx_tts_adapter_handoff_runtime_enabled=(
            config.relayctx_tts_adapter_handoff_runtime_enabled
        ),
        relayctx_tts_adapter_handoff_runtime_dry_run_only=(
            config.relayctx_tts_adapter_handoff_runtime_dry_run_only
        ),
        relayctx_tts_adapter_handoff_max_segment_chars=(
            config.relayctx_tts_adapter_handoff_max_segment_chars
        ),
        relayctx_tts_adapter_handoff_min_segment_chars=(
            config.relayctx_tts_adapter_handoff_min_segment_chars
        ),
        client_message_canonicalization_dry_run_enabled=(
            config.client_message_canonicalization_dry_run_enabled
        ),
        client_history_exclusion_preflight_enabled=(
            config.client_history_exclusion_preflight_enabled
            or config.client_history_exclusion_apply_enabled
        ),
        client_history_exclusion_apply_enabled=(
            config.client_history_exclusion_apply_enabled
        ),
        client_history_exclusion_apply_dry_run_only=(
            config.client_history_exclusion_apply_dry_run_only
        ),
        client_instruction_extraction_dry_run_enabled=(
            config.client_instruction_extraction_dry_run_enabled
        ),
        client_instruction_cache_lookup_enabled=(
            config.client_instruction_cache_lookup_enabled
        ),
        client_instruction_cache_root=config.client_instruction_cache_root,
        client_instruction_cache_max_entry_bytes=(
            config.client_instruction_cache_max_entry_bytes
        ),
        client_instruction_typed_parse_enabled=(
            config.client_instruction_typed_parse_enabled
        ),
        client_instruction_cache_write_enabled=(
            config.client_instruction_cache_write_enabled
        ),
        client_instruction_cache_write_dry_run_only=(
            config.client_instruction_cache_write_dry_run_only
        ),
    )


def list_model_ids(config: RelayLMConfig) -> list[str]:
    return sorted(config.model_routes.keys())
