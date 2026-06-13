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
    client_instruction_extraction_dry_run_enabled: bool = False


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
        client_instruction_extraction_dry_run_enabled=(
            config.client_instruction_extraction_dry_run_enabled
        ),
    )


def list_model_ids(config: RelayLMConfig) -> list[str]:
    return sorted(config.model_routes.keys())
