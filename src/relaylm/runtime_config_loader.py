from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml
from yaml.nodes import MappingNode
from yaml.resolver import BaseResolver

from relaylm.budget import (
    BudgetDegradationPolicy,
    BudgetDegradationStep,
    BudgetLayer,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
    TotalBudgetConfig,
)
from relaylm.budget_enforcement import TokenCountMode
from relaylm.cognitive import CognitionExecutionMode
from relaylm.cognition_execution import (
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.providers.openai_compatible_backend import (
    OpenAICompatibleBackendId,
    resolve_openai_compatible_backend,
)
from relaylm.runtime_config import (
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    RUNTIME_CONFIG_FORMAT_VERSION,
    CALIBRATION_PROFILES,
    CalibrationProfile,
    RUNTIME_CONFIG_PATH_ENV,
    CognitiveProfileConfig,
    CognitiveProfileProviderConfig,
    CognitionRuntimeSettings,
    ConfigSource,
    ContinuityRuntimeSettings,
    EffectiveConfigSecret,
    EffectiveConfigValue,
    EventRetrievalRuntimeConfig,
    ExplicitCognitiveBudgetConfig,
    MemoryRetrievalRuntimeConfig,
    ProviderRuntimeConfig,
    RuntimeConfig,
    RuntimeConfigErrorCode,
    RuntimePolicyConfig,
    RuntimeSecretInputs,
    SecretEnvReference,
    ServerRuntimeConfig,
    TokenCounterCapabilityConfig,
    validate_provider_base_url_secret_boundary,
)


DEFAULT_PROVIDER_ADAPTER = "openai_compatible"
DEFAULT_PROVIDER_BACKEND = OpenAICompatibleBackendId.GENERIC
_RAW_PROVIDER_API_KEY_ENV = "RELAYLM_PROVIDER_API_KEY"
_INTEGER_TEXT_RE = re.compile(r"^[0-9]+$")
_MISSING = object()


class RuntimeConfigResolutionError(ValueError):
    """Safe typed failure while discovering, parsing, or resolving runtime config."""

    def __init__(
        self,
        code: RuntimeConfigErrorCode,
        *,
        field: str | None,
        message: str,
    ) -> None:
        self.code = code
        self.field = field
        prefix = code.value if field is None else f"{code.value}: {field}"
        super().__init__(f"{prefix}: {message}")


@dataclass(frozen=True, slots=True)
class RuntimeConfigOverrides:
    """Named explicit CLI override inputs for release runtime configuration."""

    profile_name: str | None = None
    profile_root: str | None = None
    provider_adapter: str | None = None
    provider_backend: str | None = None
    provider_base_url: str | None = None
    provider_model: str | None = None
    provider_api_key_env: str | None = field(default=None, repr=False)
    server_host: str | None = None
    server_port: int | None = None
    calibration_profile: str | None = None
    cognition_mode: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedRuntimeConfig:
    """Validated non-secret config, process-local secrets, and provenance."""

    config: RuntimeConfig
    secrets: RuntimeSecretInputs
    provenance: Mapping[str, EffectiveConfigValue]
    secret_effective: EffectiveConfigSecret
    config_path: Path | None
    config_path_source: ConfigSource | None
    calibration_profile: CalibrationProfile | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))

    def source_for(self, field_path: str) -> ConfigSource:
        return self.provenance[field_path].source

    def effective_diagnostics(self) -> dict[str, object]:
        values = {
            path: {
                "value": _diagnostic_value(item.value),
                "source": item.source.value,
            }
            for path, item in sorted(self.provenance.items())
        }
        secret = {
            "configured": self.secret_effective.configured,
            "source": (
                None
                if self.secret_effective.source is None
                else self.secret_effective.source.value
            ),
            "material_source": (
                None
                if self.secret_effective.material_source is None
                else self.secret_effective.material_source.value
            ),
        }
        if self.config_path is None:
            config_path: dict[str, object] | None = None
        else:
            assert self.config_path_source is not None
            config_path = {
                "value": str(self.config_path),
                "source": self.config_path_source.value,
            }
        return {
            "format_version": self.config.format_version,
            "config_path": config_path,
            "values": values,
            "secrets": {"provider.api_key": secret},
            "validation_status": "valid",
        }


class _DuplicateKeyError(yaml.YAMLError):
    def __init__(self, key: object) -> None:
        self.key = key
        super().__init__(f"duplicate YAML key: {key}")


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.YAMLError("runtime config mapping key must be scalar") from exc
        if duplicate:
            raise _DuplicateKeyError(key)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def resolve_runtime_config(
    *,
    config_path: str | Path | None = None,
    overrides: RuntimeConfigOverrides | None = None,
    environ: Mapping[str, str] | None = None,
) -> ResolvedRuntimeConfig:
    """Resolve one deterministic v1 runtime configuration without assembly effects."""

    active_overrides = overrides or RuntimeConfigOverrides()
    active_env: Mapping[str, str] = os.environ if environ is None else environ
    selected_path, selected_path_source = _discover_config_path(
        config_path=config_path,
        environ=active_env,
    )
    raw = _load_config_mapping(selected_path) if selected_path is not None else {}

    provenance: dict[str, EffectiveConfigValue] = {}
    if selected_path is not None:
        _collect_file_provenance(raw, provenance)
    calibration_profile_name = _resolve_optional_string_leaf(
        "runtime.calibration_profile",
        cli_value=active_overrides.calibration_profile,
        env_name="RELAYLM_CALIBRATION_PROFILE",
        environ=active_env,
        file_value=_file_value(raw, "runtime", "calibration_profile"),
        provenance=provenance,
    )
    calibration_profile = _resolve_calibration_profile(calibration_profile_name)
    if calibration_profile is not None:
        _record_calibration_profile_provenance(provenance, calibration_profile)

    if selected_path is not None:
        _validate_file_shape(raw, calibration_profile=calibration_profile)
        format_version = raw["format_version"]
        _record(provenance, "format_version", format_version, ConfigSource.CONFIG_FILE)
        profiles = _parse_profiles(raw["profiles"])
        if _profile_override_requested(active_overrides, active_env):
            raise RuntimeConfigResolutionError(
                RuntimeConfigErrorCode.INVALID_COMBINATION,
                field="profiles",
                message=(
                    "profile name/root overrides cannot replace a configured multi-profile registry"
                ),
            )
    else:
        format_version = RUNTIME_CONFIG_FORMAT_VERSION
        _record(
            provenance,
            "format_version",
            format_version,
            ConfigSource.CANONICAL_DEFAULT,
        )
        profile_name = _resolve_string_leaf(
            "profiles[0].name",
            cli_value=active_overrides.profile_name,
            env_name="RELAYLM_PROFILE_NAME",
            environ=active_env,
            file_value=_MISSING,
            provenance=provenance,
            required=True,
        )
        profile_root = _resolve_string_leaf(
            "profiles[0].root",
            cli_value=active_overrides.profile_root,
            env_name="RELAYLM_PROFILE_ROOT",
            environ=active_env,
            file_value=_MISSING,
            provenance=provenance,
            required=True,
        )
        profiles = (
            CognitiveProfileConfig(name=profile_name, root=profile_root),
        )

    provider_adapter = _resolve_string_leaf(
        "provider.adapter",
        cli_value=active_overrides.provider_adapter,
        env_name="RELAYLM_PROVIDER_ADAPTER",
        environ=active_env,
        file_value=_file_value(raw, "provider", "adapter"),
        provenance=provenance,
        default=DEFAULT_PROVIDER_ADAPTER,
    )
    if provider_adapter != DEFAULT_PROVIDER_ADAPTER:
        _invalid_value("provider.adapter", "unsupported provider adapter")

    provider_backend = _resolve_backend_leaf(
        "provider.backend",
        cli_value=active_overrides.provider_backend,
        env_name="RELAYLM_PROVIDER_BACKEND",
        environ=active_env,
        file_value=_file_value(raw, "provider", "backend"),
        provenance=provenance,
        default=DEFAULT_PROVIDER_BACKEND,
    )
    provider_base_url = _resolve_string_leaf(
        "provider.base_url",
        cli_value=active_overrides.provider_base_url,
        env_name="RELAYLM_PROVIDER_BASE_URL",
        environ=active_env,
        file_value=_file_value(raw, "provider", "base_url"),
        provenance=provenance,
        required=True,
    )
    provider_model = _resolve_string_leaf(
        "provider.model",
        cli_value=active_overrides.provider_model,
        env_name="RELAYLM_PROVIDER_MODEL",
        environ=active_env,
        file_value=_file_value(raw, "provider", "model"),
        provenance=provenance,
        required=True,
    )
    server_host = _resolve_string_leaf(
        "server.host",
        cli_value=active_overrides.server_host,
        env_name="RELAYLM_HOST",
        environ=active_env,
        file_value=_file_value(raw, "server", "host"),
        provenance=provenance,
        default=DEFAULT_SERVER_HOST,
    )
    server_port = _resolve_int_leaf(
        "server.port",
        cli_value=active_overrides.server_port,
        env_name="RELAYLM_PORT",
        environ=active_env,
        file_value=_file_value(raw, "server", "port"),
        provenance=provenance,
        default=DEFAULT_SERVER_PORT,
    )
    _validate_port(server_port, "server.port")

    provider_api_key_ref, secrets, secret_effective = _resolve_provider_secret(
        overrides=active_overrides,
        environ=active_env,
        raw=raw,
    )
    runtime_policy = _parse_runtime_policy(
        raw.get("runtime", {}), calibration_profile=calibration_profile
    )
    _record_calibrated_budget_provenance(
        raw, calibration_profile=calibration_profile, provenance=provenance
    )
    cognition_mode_text = _resolve_string_leaf(
        "runtime.cognition.mode",
        cli_value=active_overrides.cognition_mode,
        env_name="RELAYLM_COGNITION_MODE",
        environ=active_env,
        file_value=_file_value(raw, "runtime", "cognition", "mode"),
        provenance=provenance,
        default=CognitionExecutionMode.TWO_PASS.value,
    )
    try:
        cognition_mode = CognitionExecutionMode(cognition_mode_text)
    except ValueError:
        _invalid_value("runtime.cognition.mode", "unsupported cognition execution mode")
    runtime_policy = RuntimePolicyConfig(
        calibration_profile=(
            None if calibration_profile is None else calibration_profile.name
        ),
        cognition=CognitionRuntimeSettings(
            mode=cognition_mode,
            pass1=runtime_policy.cognition.pass1,
            pass2=runtime_policy.cognition.pass2,
        ),
        memory_retrieval=runtime_policy.memory_retrieval,
        event_retrieval=runtime_policy.event_retrieval,
        continuity=runtime_policy.continuity,
        cognitive_budget=runtime_policy.cognitive_budget,
    )

    try:
        provider_config = ProviderRuntimeConfig(
            adapter=provider_adapter,
            backend=provider_backend,
            base_url=provider_base_url,
            model=provider_model,
            api_key=provider_api_key_ref,
        )
    except ValueError as exc:
        _invalid_value("provider.base_url", str(exc))

    config = RuntimeConfig(
        format_version=format_version,
        profiles=profiles,
        provider=provider_config,
        server=ServerRuntimeConfig(host=server_host, port=server_port),
        runtime=runtime_policy,
    )
    return ResolvedRuntimeConfig(
        config=config,
        secrets=secrets,
        provenance=provenance,
        secret_effective=secret_effective,
        config_path=selected_path,
        config_path_source=selected_path_source,
        calibration_profile=calibration_profile,
    )


def _profile_override_requested(
    overrides: RuntimeConfigOverrides,
    environ: Mapping[str, str],
) -> bool:
    return (
        overrides.profile_name is not None
        or overrides.profile_root is not None
        or "RELAYLM_PROFILE_NAME" in environ
        or "RELAYLM_PROFILE_ROOT" in environ
    )


def _discover_config_path(
    *,
    config_path: str | Path | None,
    environ: Mapping[str, str],
) -> tuple[Path | None, ConfigSource | None]:
    if config_path is not None:
        if isinstance(config_path, str) and not config_path.strip():
            raise RuntimeConfigResolutionError(
                RuntimeConfigErrorCode.DISCOVERY_ERROR,
                field="config_path",
                message="explicit config path must not be empty",
            )
        try:
            return Path(config_path).expanduser(), ConfigSource.CLI
        except TypeError as exc:
            raise RuntimeConfigResolutionError(
                RuntimeConfigErrorCode.DISCOVERY_ERROR,
                field="config_path",
                message="explicit config path must be a path-like value",
            ) from exc
        except RuntimeError as exc:
            raise RuntimeConfigResolutionError(
                RuntimeConfigErrorCode.DISCOVERY_ERROR,
                field="config_path",
                message="selected runtime config home directory cannot be resolved",
            ) from exc

    if RUNTIME_CONFIG_PATH_ENV not in environ:
        return None, None
    raw_path = environ[RUNTIME_CONFIG_PATH_ENV]
    if not isinstance(raw_path, str):
        raise RuntimeConfigResolutionError(
            RuntimeConfigErrorCode.DISCOVERY_ERROR,
            field="config_path",
            message=f"{RUNTIME_CONFIG_PATH_ENV} must be a string path",
        )
    if not raw_path.strip():
        raise RuntimeConfigResolutionError(
            RuntimeConfigErrorCode.DISCOVERY_ERROR,
            field="config_path",
            message=f"{RUNTIME_CONFIG_PATH_ENV} must not be empty",
        )
    try:
        return Path(raw_path).expanduser(), ConfigSource.ENV
    except RuntimeError as exc:
        raise RuntimeConfigResolutionError(
            RuntimeConfigErrorCode.DISCOVERY_ERROR,
            field="config_path",
            message="selected runtime config home directory cannot be resolved",
        ) from exc


def _load_config_mapping(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeConfigResolutionError(
            RuntimeConfigErrorCode.PARSE_ERROR,
            field="config_path",
            message="runtime configuration must be UTF-8",
        ) from exc
    except OSError as exc:
        raise RuntimeConfigResolutionError(
            RuntimeConfigErrorCode.READ_ERROR,
            field="config_path",
            message=f"cannot read selected runtime config: {path}",
        ) from exc

    try:
        loaded = yaml.load(text, Loader=_UniqueKeyLoader)
    except _DuplicateKeyError as exc:
        raise RuntimeConfigResolutionError(
            RuntimeConfigErrorCode.PARSE_ERROR,
            field="config_path",
            message="duplicate YAML key is not allowed",
        ) from exc
    except yaml.YAMLError as exc:
        raise RuntimeConfigResolutionError(
            RuntimeConfigErrorCode.PARSE_ERROR,
            field="config_path",
            message="runtime configuration YAML is invalid",
        ) from exc

    if not isinstance(loaded, dict):
        _invalid_type("runtime_config", "runtime configuration root must be a mapping")
    return loaded


def _validate_file_shape(
    raw: dict[str, Any],
    *,
    calibration_profile: CalibrationProfile | None,
) -> None:
    if "format_version" not in raw:
        _missing("format_version")
    version = raw["format_version"]
    if isinstance(version, bool) or not isinstance(version, int):
        _invalid_type("format_version", "must be integer 1")
    if version != RUNTIME_CONFIG_FORMAT_VERSION:
        raise RuntimeConfigResolutionError(
            RuntimeConfigErrorCode.UNSUPPORTED_FORMAT_VERSION,
            field="format_version",
            message=f"unsupported runtime format version: {version}",
        )

    _reject_unknown(
        raw,
        "",
        {"format_version", "profiles", "provider", "server", "runtime"},
    )
    if "profiles" not in raw:
        _missing("profiles")
    _parse_profiles(raw["profiles"])

    if "provider" in raw:
        provider = _mapping(raw["provider"], "provider")
        _reject_unknown(
            provider,
            "provider",
            {"adapter", "backend", "base_url", "model", "api_key"},
        )
        if "adapter" in provider:
            adapter = _string(provider["adapter"], "provider.adapter")
            if adapter != DEFAULT_PROVIDER_ADAPTER:
                _invalid_value("provider.adapter", "unsupported provider adapter")
        if "backend" in provider:
            _backend_value(provider["backend"], "provider.backend")
        if "base_url" in provider:
            base_url = _string(provider["base_url"], "provider.base_url")
            try:
                validate_provider_base_url_secret_boundary(base_url)
            except ValueError as exc:
                _invalid_value("provider.base_url", str(exc))
        if "model" in provider:
            _string(provider["model"], "provider.model")
        if "api_key" in provider:
            secret = _mapping(provider["api_key"], "provider.api_key")
            _require_exact_keys(secret, "provider.api_key", {"env"})
            _secret_reference(secret["env"], field="provider.api_key.env")

    if "server" in raw:
        server = _mapping(raw["server"], "server")
        _reject_unknown(server, "server", {"host", "port"})
        if "host" in server:
            _string(server["host"], "server.host")
        if "port" in server:
            port = _integer(server["port"], "server.port")
            _validate_port(port, "server.port")

    if "runtime" in raw:
        runtime = _mapping(raw["runtime"], "runtime")
        _reject_unknown(
            runtime,
            "runtime",
            {
                "calibration_profile",
                "cognition",
                "memory_retrieval",
                "event_retrieval",
                "continuity",
                "cognitive_budget",
            },
        )
        if "calibration_profile" in runtime:
            _string(runtime["calibration_profile"], "runtime.calibration_profile")
        _parse_runtime_policy(runtime, calibration_profile=calibration_profile)


def _parse_profiles(raw: object) -> tuple[CognitiveProfileConfig, ...]:
    if not isinstance(raw, list):
        _invalid_type("profiles", "must be a sequence")
    if not raw:
        _invalid_value("profiles", "must contain at least one Cognitive Profile")

    result: list[CognitiveProfileConfig] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        path = f"profiles[{index}]"
        mapping = _mapping(item, path)
        _reject_unknown(mapping, path, {"name", "root", "provider"})
        if "name" not in mapping:
            _missing(f"{path}.name")
        if "root" not in mapping:
            _missing(f"{path}.root")
        name = _string(mapping["name"], f"{path}.name")
        root = _string(mapping["root"], f"{path}.root")
        if name in seen:
            _invalid_value(f"{path}.name", "duplicate Cognitive Profile name")
        seen.add(name)

        provider_override = CognitiveProfileProviderConfig()
        if "provider" in mapping:
            provider_path = f"{path}.provider"
            provider = _mapping(mapping["provider"], provider_path)
            _reject_unknown(provider, provider_path, {"model"})
            model = None
            if "model" in provider:
                model = _string(provider["model"], f"{provider_path}.model")
            provider_override = CognitiveProfileProviderConfig(model=model)

        result.append(
            CognitiveProfileConfig(
                name=name,
                root=root,
                provider=provider_override,
            )
        )
    return tuple(result)


def _parse_runtime_policy(
    raw: object,
    *,
    calibration_profile: CalibrationProfile | None = None,
) -> RuntimePolicyConfig:
    runtime = _mapping(raw, "runtime")
    cognition = (
        _parse_cognition(runtime["cognition"])
        if "cognition" in runtime
        else CognitionRuntimeSettings()
    )
    memory = (
        _parse_memory_retrieval(runtime["memory_retrieval"])
        if "memory_retrieval" in runtime
        else None
    )
    event = (
        _parse_event_retrieval(runtime["event_retrieval"])
        if "event_retrieval" in runtime
        else None
    )
    continuity = (
        _parse_continuity(runtime["continuity"])
        if "continuity" in runtime
        else None
    )
    cognitive_budget = (
        _parse_cognitive_budget(
            runtime["cognitive_budget"], calibration_profile=calibration_profile
        )
        if "cognitive_budget" in runtime
        else None
    )
    return RuntimePolicyConfig(
        calibration_profile=None,
        cognition=cognition,
        memory_retrieval=memory,
        event_retrieval=event,
        continuity=continuity,
        cognitive_budget=cognitive_budget,
    )


def _parse_cognition(raw: object) -> CognitionRuntimeSettings:
    path = "runtime.cognition"
    mapping = _mapping(raw, path)
    _reject_unknown(mapping, path, {"mode", "pass1", "pass2"})
    mode_raw = mapping.get("mode", CognitionExecutionMode.TWO_PASS.value)
    mode_text = _string(mode_raw, f"{path}.mode")
    try:
        mode = CognitionExecutionMode(mode_text)
    except ValueError:
        _invalid_value(f"{path}.mode", "unsupported cognition execution mode")
    pass1 = _parse_cognition_pass(mapping.get("pass1", {}), f"{path}.pass1")
    pass2 = _parse_cognition_pass(mapping.get("pass2", {}), f"{path}.pass2")
    return CognitionRuntimeSettings(mode=mode, pass1=pass1, pass2=pass2)


def _parse_cognition_pass(raw: object, path: str) -> CognitionPassRequest:
    mapping = _mapping(raw, path)
    _reject_unknown(
        mapping,
        path,
        {
            "reasoning_mode",
            "reasoning_budget",
            "temperature",
            "top_p",
            "max_output_tokens",
            "structured_output_mode",
        },
    )
    if "structured_output_mode" in mapping and path.endswith(".pass1"):
        raise RuntimeConfigResolutionError(
            RuntimeConfigErrorCode.INVALID_COMBINATION,
            field=f"{path}.structured_output_mode",
            message="structured output mode applies only to Pass 2 extraction",
        )
    reasoning_mode = None
    if "reasoning_mode" in mapping:
        raw_mode = _string(mapping["reasoning_mode"], f"{path}.reasoning_mode")
        try:
            reasoning_mode = CognitionReasoningMode(raw_mode)
        except ValueError:
            _invalid_value(
                f"{path}.reasoning_mode",
                "unsupported cognition reasoning mode",
            )
    structured_output_mode = None
    if "structured_output_mode" in mapping:
        raw_mode = _string(
            mapping["structured_output_mode"],
            f"{path}.structured_output_mode",
        )
        try:
            structured_output_mode = CognitionStructuredOutputMode(raw_mode)
        except ValueError:
            _invalid_value(
                f"{path}.structured_output_mode",
                "unsupported cognition structured output mode",
            )
    reasoning_budget = (
        _integer(mapping["reasoning_budget"], f"{path}.reasoning_budget")
        if "reasoning_budget" in mapping
        else None
    )
    temperature = (
        _number(mapping["temperature"], f"{path}.temperature")
        if "temperature" in mapping
        else None
    )
    top_p = (
        _number(mapping["top_p"], f"{path}.top_p")
        if "top_p" in mapping
        else None
    )
    max_output_tokens = (
        _integer(mapping["max_output_tokens"], f"{path}.max_output_tokens")
        if "max_output_tokens" in mapping
        else None
    )
    try:
        return CognitionPassRequest(
            reasoning_mode=reasoning_mode,
            reasoning_budget=reasoning_budget,
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_output_tokens,
            structured_output_mode=structured_output_mode,
        )
    except (TypeError, ValueError) as exc:
        _invalid_value(path, str(exc))


def _parse_memory_retrieval(raw: object) -> MemoryRetrievalRuntimeConfig:
    path = "runtime.memory_retrieval"
    mapping = _mapping(raw, path)
    _require_exact_keys(mapping, path, {"max_chunks", "max_chars"})
    max_chunks = _integer(mapping["max_chunks"], f"{path}.max_chunks")
    max_chars = _integer(mapping["max_chars"], f"{path}.max_chars")
    try:
        return MemoryRetrievalRuntimeConfig(max_chunks=max_chunks, max_chars=max_chars)
    except ValueError as exc:
        _invalid_value(path, str(exc))


def _parse_event_retrieval(raw: object) -> EventRetrievalRuntimeConfig:
    path = "runtime.event_retrieval"
    mapping = _mapping(raw, path)
    _require_exact_keys(mapping, path, {"max_events", "max_chars"})
    max_events = _integer(mapping["max_events"], f"{path}.max_events")
    max_chars = _integer(mapping["max_chars"], f"{path}.max_chars")
    try:
        return EventRetrievalRuntimeConfig(max_events=max_events, max_chars=max_chars)
    except ValueError as exc:
        _invalid_value(path, str(exc))


def _parse_continuity(raw: object) -> ContinuityRuntimeSettings:
    path = "runtime.continuity"
    mapping = _mapping(raw, path)
    _require_exact_keys(mapping, path, {"max_items", "lifetime_revisions"})
    max_items = _integer(mapping["max_items"], f"{path}.max_items")
    lifetime = _integer(mapping["lifetime_revisions"], f"{path}.lifetime_revisions")
    try:
        return ContinuityRuntimeSettings(
            max_items=max_items,
            lifetime_revisions=lifetime,
        )
    except ValueError as exc:
        _invalid_value(path, str(exc))


def _parse_cognitive_budget(
    raw: object,
    *,
    calibration_profile: CalibrationProfile | None = None,
) -> ExplicitCognitiveBudgetConfig:
    path = "runtime.cognitive_budget"
    mapping = _mapping(raw, path)
    _reject_unknown(mapping, path, {"total", "policy", "token_counter"})
    for required in ("policy", "token_counter"):
        if required not in mapping:
            _missing(f"{path}.{required}")

    total_path = f"{path}.total"
    if "total" not in mapping:
        if calibration_profile is None:
            _missing(total_path)
        total_raw = {}
    else:
        total_raw = _mapping(mapping["total"], total_path)
        _reject_unknown(
            total_raw,
            total_path,
            {"model_context_window", "reserved_output_tokens"},
        )
    model_context_window = _calibrated_total_leaf(
        total_raw,
        "model_context_window",
        calibration_profile=calibration_profile,
    )
    reserved_output_tokens = _calibrated_total_leaf(
        total_raw,
        "reserved_output_tokens",
        calibration_profile=calibration_profile,
    )
    try:
        total = TotalBudgetConfig(
            model_context_window=model_context_window,
            reserved_output_tokens=reserved_output_tokens,
        )
    except ValueError as exc:
        _invalid_value(total_path, str(exc))

    return ExplicitCognitiveBudgetConfig(
        total=total,
        policy=_parse_budget_policy(mapping["policy"], f"{path}.policy"),
        token_counter=_parse_token_counter(
            mapping["token_counter"],
            f"{path}.token_counter",
        ),
    )


def _calibrated_total_leaf(
    total: dict[str, Any],
    name: str,
    *,
    calibration_profile: CalibrationProfile | None,
) -> int:
    path = f"runtime.cognitive_budget.total.{name}"
    if name in total:
        return _integer(total[name], path)
    if calibration_profile is None:
        _missing(path)
    if name == "model_context_window":
        return calibration_profile.target_window
    if name == "reserved_output_tokens":
        return calibration_profile.output_allowance
    raise AssertionError(f"unsupported calibrated total leaf: {name}")


def _parse_budget_policy(raw: object, path: str) -> BudgetDegradationPolicy:
    mapping = _mapping(raw, path)
    _require_exact_keys(mapping, path, {"initial_plan", "steps"})

    plan_path = f"{path}.initial_plan"
    plan_raw = _mapping(mapping["initial_plan"], plan_path)
    required_layers = {
        "canonical_state",
        "working_context",
        "retrieved_memory",
        "event_evidence",
    }
    _reject_unknown(plan_raw, plan_path, required_layers | {"package_knowledge"})
    for required in required_layers:
        if required not in plan_raw:
            _missing(f"{plan_path}.{required}")
    try:
        canonical_state = _parse_count_envelope(
            plan_raw["canonical_state"],
            f"{plan_path}.canonical_state",
        )
        working_context = _parse_count_character_envelope(
            plan_raw["working_context"],
            f"{plan_path}.working_context",
        )
        retrieved_memory = _parse_count_character_envelope(
            plan_raw["retrieved_memory"],
            f"{plan_path}.retrieved_memory",
        )
        event_evidence = _parse_count_character_envelope(
            plan_raw["event_evidence"],
            f"{plan_path}.event_evidence",
        )
        package_knowledge = (
            _parse_count_character_envelope(
                plan_raw["package_knowledge"],
                f"{plan_path}.package_knowledge",
            )
            if "package_knowledge" in plan_raw
            else CountCharacterEnvelope(0, 0, 0, 0)
        )
    except RuntimeConfigResolutionError as exc:
        if exc.code is RuntimeConfigErrorCode.INVALID_VALUE:
            _invalid_value(path, "invalid owner-defined budget envelope")
        raise

    plan = BudgetPlan(
        canonical_state=canonical_state,
        working_context=working_context,
        retrieved_memory=retrieved_memory,
        event_evidence=event_evidence,
        package_knowledge=package_knowledge,
    )

    steps_raw = mapping["steps"]
    if not isinstance(steps_raw, list):
        _invalid_type(f"{path}.steps", "must be a sequence")
    steps: list[BudgetDegradationStep] = []
    for index, item in enumerate(steps_raw):
        step_path = f"{path}.steps.{index}"
        step_raw = _mapping(item, step_path)
        _require_exact_keys(step_raw, step_path, {"layer", "target"})
        layer_name = _string(step_raw["layer"], f"{step_path}.layer")
        try:
            layer = BudgetLayer(layer_name)
        except ValueError:
            _invalid_value(f"{step_path}.layer", "unsupported budget layer")
        if layer is BudgetLayer.CANONICAL_STATE:
            target = _parse_count_envelope(step_raw["target"], f"{step_path}.target")
        else:
            target = _parse_count_character_envelope(
                step_raw["target"],
                f"{step_path}.target",
            )
        steps.append(BudgetDegradationStep(layer=layer, target=target))

    try:
        return BudgetDegradationPolicy(initial_plan=plan, steps=tuple(steps))
    except (TypeError, ValueError) as exc:
        _invalid_value(path, str(exc))


def _parse_count_envelope(raw: object, path: str) -> CountEnvelope:
    mapping = _mapping(raw, path)
    _require_exact_keys(mapping, path, {"max_items", "floor_items"})
    max_items = _integer(mapping["max_items"], f"{path}.max_items")
    floor_items = _integer(mapping["floor_items"], f"{path}.floor_items")
    try:
        return CountEnvelope(max_items=max_items, floor_items=floor_items)
    except ValueError as exc:
        _invalid_value(path, str(exc))


def _parse_count_character_envelope(
    raw: object,
    path: str,
) -> CountCharacterEnvelope:
    mapping = _mapping(raw, path)
    _require_exact_keys(
        mapping,
        path,
        {"max_items", "floor_items", "max_chars", "floor_chars"},
    )
    max_items = _integer(mapping["max_items"], f"{path}.max_items")
    floor_items = _integer(mapping["floor_items"], f"{path}.floor_items")
    max_chars = _integer(mapping["max_chars"], f"{path}.max_chars")
    floor_chars = _integer(mapping["floor_chars"], f"{path}.floor_chars")
    try:
        return CountCharacterEnvelope(
            max_items=max_items,
            floor_items=floor_items,
            max_chars=max_chars,
            floor_chars=floor_chars,
        )
    except ValueError as exc:
        _invalid_value(path, str(exc))


def _parse_token_counter(raw: object, path: str) -> TokenCounterCapabilityConfig:
    mapping = _mapping(raw, path)
    _require_exact_keys(mapping, path, {"capability", "mode"})
    capability = _string(mapping["capability"], f"{path}.capability")
    mode_name = _string(mapping["mode"], f"{path}.mode")
    try:
        mode = TokenCountMode(mode_name)
    except ValueError:
        _invalid_value(f"{path}.mode", "unsupported token accounting mode")
    return TokenCounterCapabilityConfig(capability=capability, mode=mode)


def _resolve_provider_secret(
    *,
    overrides: RuntimeConfigOverrides,
    environ: Mapping[str, str],
    raw: dict[str, Any],
) -> tuple[SecretEnvReference | None, RuntimeSecretInputs, EffectiveConfigSecret]:
    if overrides.provider_api_key_env is not None:
        ref = _secret_reference(overrides.provider_api_key_env, field="provider.api_key")
        material = _referenced_secret(environ, ref.env)
        return _secret_result(ref, material, ConfigSource.CLI)

    if _RAW_PROVIDER_API_KEY_ENV in environ:
        material = environ[_RAW_PROVIDER_API_KEY_ENV]
        if not isinstance(material, str) or not material.strip():
            raise RuntimeConfigResolutionError(
                RuntimeConfigErrorCode.SECRET_UNAVAILABLE,
                field="provider.api_key",
                message=f"{_RAW_PROVIDER_API_KEY_ENV} is present but empty",
            )
        return (
            None,
            RuntimeSecretInputs(provider_api_key=material),
            EffectiveConfigSecret(
                configured=True,
                source=ConfigSource.ENV,
                material_source=ConfigSource.ENV,
            ),
        )

    file_secret = _file_value(raw, "provider", "api_key")
    if file_secret is not _MISSING:
        assert isinstance(file_secret, dict)
        ref = _secret_reference(file_secret["env"], field="provider.api_key")
        material = _referenced_secret(environ, ref.env)
        return _secret_result(ref, material, ConfigSource.CONFIG_FILE)

    return (
        None,
        RuntimeSecretInputs(),
        EffectiveConfigSecret(configured=False, source=None, material_source=None),
    )


def _secret_result(
    ref: SecretEnvReference,
    material: str,
    source: ConfigSource,
) -> tuple[SecretEnvReference, RuntimeSecretInputs, EffectiveConfigSecret]:
    return (
        ref,
        RuntimeSecretInputs(provider_api_key=material),
        EffectiveConfigSecret(
            configured=True,
            source=source,
            material_source=ConfigSource.ENV,
        ),
    )


def _secret_reference(value: object, *, field: str) -> SecretEnvReference:
    if not isinstance(value, str):
        _invalid_type(field, "secret reference must be an environment variable name")
    try:
        return SecretEnvReference(env=value)
    except ValueError as exc:
        _invalid_value(field, str(exc))


def _referenced_secret(environ: Mapping[str, str], name: str) -> str:
    if name not in environ:
        raise RuntimeConfigResolutionError(
            RuntimeConfigErrorCode.SECRET_UNAVAILABLE,
            field="provider.api_key",
            message=f"referenced environment variable is unavailable: {name}",
        )
    value = environ[name]
    if not isinstance(value, str) or not value.strip():
        raise RuntimeConfigResolutionError(
            RuntimeConfigErrorCode.SECRET_UNAVAILABLE,
            field="provider.api_key",
            message=f"referenced environment variable is empty: {name}",
        )
    return value


def _resolve_backend_leaf(
    path: str,
    *,
    cli_value: object,
    env_name: str,
    environ: Mapping[str, str],
    file_value: object,
    provenance: dict[str, EffectiveConfigValue],
    default: OpenAICompatibleBackendId,
) -> OpenAICompatibleBackendId:
    value, source = _choose_leaf(
        cli_value=cli_value,
        env_name=env_name,
        environ=environ,
        file_value=file_value,
        default=default,
    )
    if isinstance(value, OpenAICompatibleBackendId):
        resolved = value
    else:
        resolved = _backend_value(value, path)
    _record(provenance, path, resolved, source)
    return resolved


def _resolve_string_leaf(
    path: str,
    *,
    cli_value: object,
    env_name: str,
    environ: Mapping[str, str],
    file_value: object,
    provenance: dict[str, EffectiveConfigValue],
    required: bool = False,
    default: object = _MISSING,
) -> str:
    value, source = _choose_leaf(
        cli_value=cli_value,
        env_name=env_name,
        environ=environ,
        file_value=file_value,
        default=default,
    )
    if value is _MISSING:
        if required:
            _missing(path)
        raise AssertionError(f"unresolved configuration leaf: {path}")
    resolved = _string(value, path)
    _record(provenance, path, resolved, source)
    return resolved


def _resolve_optional_string_leaf(
    path: str,
    *,
    cli_value: object,
    env_name: str,
    environ: Mapping[str, str],
    file_value: object,
    provenance: dict[str, EffectiveConfigValue],
) -> str | None:
    value, source = _choose_leaf(
        cli_value=cli_value,
        env_name=env_name,
        environ=environ,
        file_value=file_value,
        default=_MISSING,
    )
    if value is _MISSING:
        provenance.pop(path, None)
        return None
    resolved = _string(value, path)
    _record(provenance, path, resolved, source)
    return resolved


def _resolve_calibration_profile(name: str | None) -> CalibrationProfile | None:
    if name is None:
        return None
    profile = CALIBRATION_PROFILES.get(name)
    if profile is None:
        _invalid_value("runtime.calibration_profile", "unsupported calibration profile")
    return profile


def _record_calibration_profile_provenance(
    provenance: dict[str, EffectiveConfigValue],
    profile: CalibrationProfile,
) -> None:
    source = ConfigSource.CANONICAL_DEFAULT
    _record(
        provenance,
        "runtime.calibration_profile.target_window",
        profile.target_window,
        source,
    )
    _record(
        provenance,
        "runtime.calibration_profile.output_allowance",
        profile.output_allowance,
        source,
    )
    _record(
        provenance,
        "runtime.calibration_profile.authority",
        profile.authority,
        source,
    )


def _record_calibrated_budget_provenance(
    raw: dict[str, Any],
    *,
    calibration_profile: CalibrationProfile | None,
    provenance: dict[str, EffectiveConfigValue],
) -> None:
    if calibration_profile is None:
        return
    cognitive_budget = _file_value(raw, "runtime", "cognitive_budget")
    if not isinstance(cognitive_budget, dict):
        return
    total = cognitive_budget.get("total")
    if not isinstance(total, dict):
        total = {}
    for name in ("model_context_window", "reserved_output_tokens"):
        if name in total:
            continue
        value = (
            calibration_profile.target_window
            if name == "model_context_window"
            else calibration_profile.output_allowance
        )
        _record(
            provenance,
            f"runtime.cognitive_budget.total.{name}",
            value,
            ConfigSource.CANONICAL_DEFAULT,
        )


def _resolve_int_leaf(
    path: str,
    *,
    cli_value: object,
    env_name: str,
    environ: Mapping[str, str],
    file_value: object,
    provenance: dict[str, EffectiveConfigValue],
    default: int,
) -> int:
    value, source = _choose_leaf(
        cli_value=cli_value,
        env_name=env_name,
        environ=environ,
        file_value=file_value,
        default=default,
    )
    if source is ConfigSource.ENV:
        if not isinstance(value, str) or not _INTEGER_TEXT_RE.fullmatch(value):
            _invalid_type(path, f"{env_name} must be an unsigned integer string")
        resolved = int(value)
    else:
        resolved = _integer(value, path)
    _record(provenance, path, resolved, source)
    return resolved


def _choose_leaf(
    *,
    cli_value: object,
    env_name: str,
    environ: Mapping[str, str],
    file_value: object,
    default: object,
) -> tuple[object, ConfigSource]:
    if cli_value is not None:
        return cli_value, ConfigSource.CLI
    if env_name in environ:
        return environ[env_name], ConfigSource.ENV
    if file_value is not _MISSING:
        return file_value, ConfigSource.CONFIG_FILE
    if default is not _MISSING:
        return default, ConfigSource.CANONICAL_DEFAULT
    return _MISSING, ConfigSource.CANONICAL_DEFAULT


def _file_value(raw: dict[str, Any], *path: str) -> object:
    current: object = raw
    for component in path:
        if not isinstance(current, dict) or component not in current:
            return _MISSING
        current = current[component]
    return current


def _collect_file_provenance(
    raw: dict[str, Any],
    provenance: dict[str, EffectiveConfigValue],
) -> None:
    def visit(value: object, path: str) -> None:
        if path == "provider.api_key" or path.startswith("provider.api_key."):
            return
        if isinstance(value, dict):
            for key, nested in value.items():
                nested_path = str(key) if not path else f"{path}.{key}"
                visit(nested, nested_path)
            return
        if isinstance(value, list):
            for index, nested in enumerate(value):
                visit(nested, f"{path}.{index}")
            return
        if path:
            _record(provenance, path, value, ConfigSource.CONFIG_FILE)

    visit(raw, "")


def _record(
    provenance: dict[str, EffectiveConfigValue],
    path: str,
    value: object,
    source: ConfigSource,
) -> None:
    provenance[path] = EffectiveConfigValue(value=value, source=source)


def _mapping(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _invalid_type(path, "must be a mapping")
    for key in value:
        if not isinstance(key, str):
            _invalid_type(path, "mapping keys must be strings")
    return value


def _reject_unknown(
    mapping: dict[str, Any],
    path: str,
    allowed: set[str],
) -> None:
    for key in mapping:
        if not isinstance(key, str):
            _invalid_type(path or "runtime_config", "mapping keys must be strings")
        if key not in allowed:
            field_path = key if not path else f"{path}.{key}"
            raise RuntimeConfigResolutionError(
                RuntimeConfigErrorCode.UNKNOWN_FIELD,
                field=field_path,
                message="unknown runtime configuration field",
            )


def _require_exact_keys(
    mapping: dict[str, Any],
    path: str,
    required: set[str],
) -> None:
    _reject_unknown(mapping, path, required)
    for key in sorted(required):
        if key not in mapping:
            _missing(f"{path}.{key}")


def _string(value: object, path: str) -> str:
    if not isinstance(value, str):
        _invalid_type(path, "must be a string")
    if not value.strip():
        _invalid_value(path, "must be a non-empty string")
    return value


def _backend_value(value: object, path: str) -> OpenAICompatibleBackendId:
    raw = _string(value, path)
    try:
        return resolve_openai_compatible_backend(raw).id
    except ValueError as exc:
        _invalid_value(path, str(exc))


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _invalid_type(path, "must be an integer")
    return value


def _number(value: object, path: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _invalid_type(path, "must be a number")
    return value


def _validate_port(value: int, path: str) -> None:
    if not 1 <= value <= 65535:
        _invalid_value(path, "must be between 1 and 65535")


def _missing(path: str) -> None:
    raise RuntimeConfigResolutionError(
        RuntimeConfigErrorCode.MISSING_REQUIRED,
        field=path,
        message="required runtime configuration value is missing",
    )


def _invalid_type(path: str, message: str) -> None:
    raise RuntimeConfigResolutionError(
        RuntimeConfigErrorCode.INVALID_TYPE,
        field=path,
        message=message,
    )


def _invalid_value(path: str, message: str) -> None:
    raise RuntimeConfigResolutionError(
        RuntimeConfigErrorCode.INVALID_VALUE,
        field=path,
        message=message,
    )


def _diagnostic_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    return value
