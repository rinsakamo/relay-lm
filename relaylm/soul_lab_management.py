"""Read-only, content-free SOUL Lab management projections."""

from __future__ import annotations

from collections import defaultdict
from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field

from relaylm.config import RelayLMConfig

ProjectionState = Literal["configured", "unconfigured"]


class LabListenProjection(BaseModel):
    host: str
    port: int
    loopback_only: bool


class LabCredentialBoundaryProjection(BaseModel):
    owner: Literal["relaylm_server"] = "relaylm_server"
    browser_loaded: bool = False
    credential_fields_included: bool = False


class LabDiagnosticsProjection(BaseModel):
    mode: Literal["content_free"] = "content_free"
    projected_event_count: int = 0
    credential_fields_loaded: int = 0
    source_content_included: bool = False
    raw_trace_included: bool = False


class LabRuntimeComponentProjection(BaseModel):
    component_id: str
    label: str
    state: ProjectionState
    endpoint: str | None = None
    model_labels: list[str] = Field(default_factory=list)
    capability: str
    network_probe_performed: bool = False


class LabSettingsProjection(BaseModel):
    schema_version: Literal["relaylm.lab.settings.v0"] = "relaylm.lab.settings.v0"
    projection_kind: Literal["read_only"] = "read_only"
    source: Literal["runtime_config"] = "runtime_config"
    content_free: bool = True
    settings_write_supported: bool = False
    network_probe_performed: bool = False
    listen: LabListenProjection
    runtime_components: list[LabRuntimeComponentProjection]
    credential_boundary: LabCredentialBoundaryProjection = Field(
        default_factory=LabCredentialBoundaryProjection
    )
    diagnostics: LabDiagnosticsProjection = Field(default_factory=LabDiagnosticsProjection)


class LabCharacterProjection(BaseModel):
    character_id: str
    route_models: list[str] = Field(default_factory=list)
    backend_ids: list[str] = Field(default_factory=list)
    memory_namespaces: list[str] = Field(default_factory=list)
    modes: list[str] = Field(default_factory=list)
    soul_configured: bool
    output_policy_configured: bool
    relationship_anchor_configured: bool
    memory_seed_configured: bool
    stable_memory_summary_configured: bool
    source_complete: bool
    source_content_included: bool = False
    source_paths_included: bool = False


class LabCharactersProjection(BaseModel):
    schema_version: Literal["relaylm.lab.characters.v0"] = "relaylm.lab.characters.v0"
    projection_kind: Literal["read_only"] = "read_only"
    source: Literal["runtime_config"] = "runtime_config"
    content_free: bool = True
    persistent_registry_mutation_supported: bool = False
    credential_fields_included: bool = False
    source_content_included: bool = False
    characters: list[LabCharacterProjection]


def build_lab_settings_projection(config: RelayLMConfig) -> LabSettingsProjection:
    runtime_components = [
        LabRuntimeComponentProjection(
            component_id="relaylm",
            label="RelayLM Core",
            state="configured",
            endpoint=f"http://{_display_host(config.listen.host)}:{config.listen.port}/v1",
            model_labels=sorted(config.model_routes),
            capability="openai_compatible_proxy",
        )
    ]

    route_models_by_backend: dict[str, list[str]] = defaultdict(list)
    for route in config.model_routes.values():
        if route.backend_model:
            route_models_by_backend[route.backend].append(route.backend_model)

    for backend_id in sorted(config.backends):
        backend = config.backends[backend_id]
        model_labels = set(route_models_by_backend.get(backend_id, []))
        if backend.default_model:
            model_labels.add(backend.default_model)
        runtime_components.append(
            LabRuntimeComponentProjection(
                component_id=f"backend:{backend_id}",
                label=f"Backend {backend_id}",
                state="configured",
                endpoint=_safe_endpoint_projection(str(backend.base_url)),
                model_labels=sorted(model_labels),
                capability="chat_completions",
            )
        )

    runtime_components.extend(
        [
            LabRuntimeComponentProjection(
                component_id="tts",
                label="TTS Adapter",
                state="unconfigured",
                capability="tts_adapter_handoff_only",
            ),
            LabRuntimeComponentProjection(
                component_id="avatar",
                label="Avatar Adapter",
                state="unconfigured",
                capability="avatar_adapter_not_configured",
            ),
        ]
    )

    return LabSettingsProjection(
        listen=LabListenProjection(
            host=config.listen.host,
            port=config.listen.port,
            loopback_only=is_loopback_host(config.listen.host),
        ),
        runtime_components=runtime_components,
    )


def build_lab_characters_projection(config: RelayLMConfig) -> LabCharactersProjection:
    route_models: dict[str, set[str]] = defaultdict(set)
    backend_ids: dict[str, set[str]] = defaultdict(set)
    memory_namespaces: dict[str, set[str]] = defaultdict(set)
    modes: dict[str, set[str]] = defaultdict(set)

    character_ids = set(config.characters)
    for route_model, route in config.model_routes.items():
        if not route.character_id:
            continue
        character_ids.add(route.character_id)
        route_models[route.character_id].add(route_model)
        backend_ids[route.character_id].add(route.backend)
        modes[route.character_id].add(route.mode or config.mode)
        if route.memory_namespace:
            memory_namespaces[route.character_id].add(route.memory_namespace)

    characters: list[LabCharacterProjection] = []
    for character_id in sorted(character_ids):
        character = config.characters.get(character_id)
        soul_configured = bool(character and character.soul.strip())
        output_policy_configured = bool(character and character.output_policy.strip())
        relationship_anchor_configured = bool(
            character and character.relationship_anchor and character.relationship_anchor.strip()
        )
        memory_seed_configured = bool(
            character and character.memory_seed_path and character.memory_seed_path.strip()
        )
        stable_memory_summary_configured = bool(
            character
            and character.stable_memory_summary
            and character.stable_memory_summary.strip()
        )
        characters.append(
            LabCharacterProjection(
                character_id=character_id,
                route_models=sorted(route_models.get(character_id, set())),
                backend_ids=sorted(backend_ids.get(character_id, set())),
                memory_namespaces=sorted(memory_namespaces.get(character_id, set())),
                modes=sorted(modes.get(character_id, set())),
                soul_configured=soul_configured,
                output_policy_configured=output_policy_configured,
                relationship_anchor_configured=relationship_anchor_configured,
                memory_seed_configured=memory_seed_configured,
                stable_memory_summary_configured=stable_memory_summary_configured,
                source_complete=(
                    soul_configured
                    and output_policy_configured
                    and relationship_anchor_configured
                ),
            )
        )

    return LabCharactersProjection(characters=characters)


def is_loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized == "localhost":
        return True
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def _safe_endpoint_projection(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return "configured"
        host = _display_host(parsed.hostname)
        port = f":{parsed.port}" if parsed.port is not None else ""
        path = parsed.path.rstrip("/")
        return urlunsplit((parsed.scheme, f"{host}{port}", path, "", ""))
    except (ValueError, TypeError):
        return "configured"


def _display_host(host: str) -> str:
    return f"[{host}]" if ":" in host and not host.startswith("[") else host
