from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlsplit

from relaylm.budget import BudgetDegradationPolicy, TotalBudgetConfig
from relaylm.budget_enforcement import TokenCountMode
from relaylm.cognitive import CognitionExecutionMode
from relaylm.cognition_execution import CognitionPassRequest
from relaylm.providers.openai_compatible_backend import OpenAICompatibleBackendId


RUNTIME_CONFIG_FORMAT_VERSION = 1
RUNTIME_CONFIG_PATH_ENV = "RELAYLM_CONFIG"
UNKNOWN_FIELD_POLICY = "error"
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = 8090

_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ConfigSource(str, Enum):
    """Observable source of one resolved runtime-configuration leaf."""

    CLI = "cli"
    ENV = "env"
    CONFIG_FILE = "config_file"
    CANONICAL_DEFAULT = "canonical_default"


CONFIG_PRECEDENCE = (
    ConfigSource.CLI,
    ConfigSource.ENV,
    ConfigSource.CONFIG_FILE,
    ConfigSource.CANONICAL_DEFAULT,
)


class RuntimeConfigErrorCode(str, Enum):
    """Stable release-facing configuration/preflight error categories."""

    DISCOVERY_ERROR = "discovery_error"
    READ_ERROR = "read_error"
    PARSE_ERROR = "parse_error"
    UNSUPPORTED_FORMAT_VERSION = "unsupported_format_version"
    UNKNOWN_FIELD = "unknown_field"
    INVALID_TYPE = "invalid_type"
    INVALID_VALUE = "invalid_value"
    MISSING_REQUIRED = "missing_required"
    INVALID_COMBINATION = "invalid_combination"
    SECRET_UNAVAILABLE = "secret_unavailable"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    CHARACTER_INVALID = "character_invalid"
    PROVIDER_INVALID = "provider_invalid"


def validate_provider_base_url_secret_boundary(base_url: str) -> None:
    """Reject provider endpoint credentials without taking URL-shape ownership."""

    try:
        parsed_base_url = urlsplit(base_url)
    except ValueError:
        return
    if parsed_base_url.username is not None or parsed_base_url.password is not None:
        raise ValueError("provider.base_url must not contain credentials")


@dataclass(frozen=True, slots=True)
class SecretEnvReference:
    """Persistable reference to a secret, never the secret value itself."""

    env: str

    def __post_init__(self) -> None:
        if not isinstance(self.env, str) or not _ENV_NAME_RE.fullmatch(self.env):
            raise ValueError("secret env must be a valid environment variable name")


@dataclass(frozen=True, slots=True)
class RuntimeSecretInputs:
    """Process-local resolved secret material kept outside RuntimeConfig diagnostics."""

    provider_api_key: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.provider_api_key is not None:
            _require_non_empty_string("provider_api_key", self.provider_api_key)


@dataclass(frozen=True, slots=True)
class CognitiveProfileProviderConfig:
    """Profile-local physical provider overrides supported by Core 1.0."""

    model: str | None = None

    def __post_init__(self) -> None:
        if self.model is not None:
            _require_non_empty_string("profiles[].provider.model", self.model)


@dataclass(frozen=True, slots=True)
class CognitiveProfileConfig:
    """Public Cognitive Profile identity bound to one Cognitive Package root."""

    name: str
    root: str
    provider: CognitiveProfileProviderConfig = field(
        default_factory=CognitiveProfileProviderConfig
    )

    def __post_init__(self) -> None:
        _require_non_empty_string("profiles[].name", self.name)
        _require_non_empty_string("profiles[].root", self.root)
        if not isinstance(self.provider, CognitiveProfileProviderConfig):
            raise TypeError("profiles[].provider must be CognitiveProfileProviderConfig")


@dataclass(frozen=True, slots=True)
class ProviderRuntimeConfig:
    """Release-facing provider selection without provider-wire reinterpretation."""

    adapter: str
    base_url: str
    model: str
    backend: OpenAICompatibleBackendId = OpenAICompatibleBackendId.GENERIC
    api_key: SecretEnvReference | None = None

    def __post_init__(self) -> None:
        if self.adapter != "openai_compatible":
            raise ValueError(f"unsupported provider adapter: {self.adapter}")
        if not isinstance(self.backend, OpenAICompatibleBackendId):
            raise TypeError("provider.backend must be OpenAICompatibleBackendId")
        _require_non_empty_string("provider.base_url", self.base_url)
        validate_provider_base_url_secret_boundary(self.base_url)
        _require_non_empty_string("provider.model", self.model)
        if self.api_key is not None and not isinstance(self.api_key, SecretEnvReference):
            raise TypeError("provider.api_key must be SecretEnvReference or None")


@dataclass(frozen=True, slots=True)
class ServerRuntimeConfig:
    """Release-owned server bind settings; loopback remains the safe default."""

    host: str = DEFAULT_SERVER_HOST
    port: int = DEFAULT_SERVER_PORT

    def __post_init__(self) -> None:
        _require_non_empty_string("server.host", self.host)
        if isinstance(self.port, bool) or not isinstance(self.port, int):
            raise TypeError("server.port must be an integer")
        if not 1 <= self.port <= 65535:
            raise ValueError("server.port must be between 1 and 65535")


@dataclass(frozen=True, slots=True)
class MemoryRetrievalRuntimeConfig:
    """Serializable carriage for the existing MEMORY retrieval budget controls."""

    max_chunks: int
    max_chars: int

    def __post_init__(self) -> None:
        _require_non_negative_int("memory_retrieval.max_chunks", self.max_chunks)
        _require_non_negative_int("memory_retrieval.max_chars", self.max_chars)


@dataclass(frozen=True, slots=True)
class EventRetrievalRuntimeConfig:
    """Serializable carriage for the existing Event retrieval budget controls."""

    max_events: int
    max_chars: int

    def __post_init__(self) -> None:
        _require_non_negative_int("event_retrieval.max_events", self.max_events)
        _require_non_negative_int("event_retrieval.max_chars", self.max_chars)


@dataclass(frozen=True, slots=True)
class ContinuityRuntimeSettings:
    """Explicit lifecycle inputs already required by ContinuityRuntime."""

    max_items: int
    lifetime_revisions: int

    def __post_init__(self) -> None:
        _require_positive_int("continuity.max_items", self.max_items)
        _require_positive_int("continuity.lifetime_revisions", self.lifetime_revisions)


@dataclass(frozen=True, slots=True)
class TokenCounterCapabilityConfig:
    """Declared assembly capability for #1387 serialized-input accounting."""

    capability: str
    mode: TokenCountMode

    def __post_init__(self) -> None:
        _require_non_empty_string("token_counter.capability", self.capability)
        if not isinstance(self.mode, TokenCountMode):
            raise TypeError("token_counter.mode must be TokenCountMode")


@dataclass(frozen=True, slots=True)
class ExplicitCognitiveBudgetConfig:
    """Authority-preserving carriage of existing #1387 owner types."""

    total: TotalBudgetConfig
    policy: BudgetDegradationPolicy
    token_counter: TokenCounterCapabilityConfig

    def __post_init__(self) -> None:
        if not isinstance(self.total, TotalBudgetConfig):
            raise TypeError("cognitive_budget.total must be TotalBudgetConfig")
        if not isinstance(self.policy, BudgetDegradationPolicy):
            raise TypeError("cognitive_budget.policy must be BudgetDegradationPolicy")
        if not isinstance(self.token_counter, TokenCounterCapabilityConfig):
            raise TypeError("cognitive_budget.token_counter must be TokenCounterCapabilityConfig")


@dataclass(frozen=True, slots=True)
class CognitionRuntimeSettings:
    """Release carriage of #1533 topology and already-resolved per-pass intent."""

    mode: CognitionExecutionMode = CognitionExecutionMode.TWO_PASS
    pass1: CognitionPassRequest = field(default_factory=CognitionPassRequest)
    pass2: CognitionPassRequest = field(default_factory=CognitionPassRequest)

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CognitionExecutionMode):
            raise TypeError("cognition.mode must be CognitionExecutionMode")
        if not isinstance(self.pass1, CognitionPassRequest):
            raise TypeError("cognition.pass1 must be CognitionPassRequest")
        if not isinstance(self.pass2, CognitionPassRequest):
            raise TypeError("cognition.pass2 must be CognitionPassRequest")


@dataclass(frozen=True, slots=True)
class RuntimePolicyConfig:
    """Release configuration for existing runtime controls."""

    calibration_profile: str | None = None
    cognition: CognitionRuntimeSettings = field(default_factory=CognitionRuntimeSettings)
    memory_retrieval: MemoryRetrievalRuntimeConfig | None = None
    event_retrieval: EventRetrievalRuntimeConfig | None = None
    continuity: ContinuityRuntimeSettings | None = None
    cognitive_budget: ExplicitCognitiveBudgetConfig | None = None

    def __post_init__(self) -> None:
        if self.calibration_profile is not None:
            _require_non_empty_string(
                "runtime.calibration_profile", self.calibration_profile
            )
        if not isinstance(self.cognition, CognitionRuntimeSettings):
            raise TypeError("runtime.cognition must be CognitionRuntimeSettings")
        _require_optional_type(
            "runtime.memory_retrieval",
            self.memory_retrieval,
            MemoryRetrievalRuntimeConfig,
        )
        _require_optional_type(
            "runtime.event_retrieval",
            self.event_retrieval,
            EventRetrievalRuntimeConfig,
        )
        _require_optional_type(
            "runtime.continuity",
            self.continuity,
            ContinuityRuntimeSettings,
        )
        _require_optional_type(
            "runtime.cognitive_budget",
            self.cognitive_budget,
            ExplicitCognitiveBudgetConfig,
        )


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Version-1 non-secret resolved runtime configuration contract."""

    format_version: int
    profiles: tuple[CognitiveProfileConfig, ...]
    provider: ProviderRuntimeConfig
    server: ServerRuntimeConfig = field(default_factory=ServerRuntimeConfig)
    runtime: RuntimePolicyConfig = field(default_factory=RuntimePolicyConfig)

    def __post_init__(self) -> None:
        if isinstance(self.format_version, bool) or not isinstance(self.format_version, int):
            raise TypeError("runtime format_version must be integer 1")
        if self.format_version != RUNTIME_CONFIG_FORMAT_VERSION:
            raise ValueError(f"unsupported runtime format_version: {self.format_version}")
        if not isinstance(self.profiles, tuple) or not self.profiles:
            raise TypeError("profiles must be a non-empty tuple of CognitiveProfileConfig")
        seen: set[str] = set()
        for profile in self.profiles:
            if not isinstance(profile, CognitiveProfileConfig):
                raise TypeError("profiles must contain CognitiveProfileConfig")
            if profile.name in seen:
                raise ValueError(f"duplicate cognitive profile name: {profile.name}")
            seen.add(profile.name)
        if not isinstance(self.provider, ProviderRuntimeConfig):
            raise TypeError("provider must be ProviderRuntimeConfig")
        if not isinstance(self.server, ServerRuntimeConfig):
            raise TypeError("server must be ServerRuntimeConfig")
        if not isinstance(self.runtime, RuntimePolicyConfig):
            raise TypeError("runtime must be RuntimePolicyConfig")


@dataclass(frozen=True, slots=True)
class EffectiveConfigValue:
    """One non-secret effective value plus observable source provenance."""

    value: object
    source: ConfigSource

    def __post_init__(self) -> None:
        if not isinstance(self.source, ConfigSource):
            raise TypeError("effective config source must be ConfigSource")


@dataclass(frozen=True, slots=True)
class EffectiveConfigSecret:
    """Secret-free diagnostic for selected reference and material provenance."""

    configured: bool
    source: ConfigSource | None
    material_source: ConfigSource | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.configured, bool):
            raise TypeError("configured must be bool")
        if self.source is not None and not isinstance(self.source, ConfigSource):
            raise TypeError("effective secret source must be ConfigSource or None")
        if self.material_source is not None and not isinstance(
            self.material_source, ConfigSource
        ):
            raise TypeError("effective secret material_source must be ConfigSource or None")


def _require_non_empty_string(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_non_negative_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _require_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _require_optional_type(name: str, value: object, expected: type[object]) -> None:
    if value is not None and not isinstance(value, expected):
        raise TypeError(f"{name} must be {expected.__name__} or None")
