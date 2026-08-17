from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)


OPENAI_COMPATIBLE_PROVIDER_IDENTITY_FORMAT_VERSION = 1
OPENAI_COMPATIBLE_ADAPTER_IDENTITY = "openai_compatible"
OPENAI_COMPATIBLE_STRUCTURED_OUTPUT_SCHEMA_NAME = "relaylm_cognitive_output"
OPENAI_COMPATIBLE_STRUCTURED_SEMANTIC_CHANNELS = (
    "response",
    "state_candidates",
    "continuity_candidates",
)


class OpenAICompatibleProviderIdentitySource(Protocol):
    model: str
    decoding_config: OpenAICompatibleDecodingConfig
    decoding_capabilities: OpenAICompatibleDecodingCapabilities


@dataclass(frozen=True, slots=True)
class OpenAICompatibleProviderCapabilities:
    """Stable content-free capability surface for the canonical adapter."""

    structured_semantic_channels: tuple[str, ...]
    supported_decoding_controls: tuple[str, ...]
    buffered: bool
    streaming: bool
    seed_control_supported: bool

    @property
    def capability_tokens(self) -> tuple[str, ...]:
        tokens = set(self.structured_semantic_channels)
        if self.buffered:
            tokens.add("buffered")
        if self.streaming:
            tokens.add("streaming")
        tokens.update(self.supported_decoding_controls)
        return tuple(sorted(tokens))

    def to_mapping(self) -> dict[str, object]:
        return {
            "capability_tokens": list(self.capability_tokens),
            "structured_semantic_channels": list(self.structured_semantic_channels),
            "supported_decoding_controls": list(self.supported_decoding_controls),
            "buffered": self.buffered,
            "streaming": self.streaming,
            "seed_control_supported": self.seed_control_supported,
        }


@dataclass(frozen=True, slots=True)
class OpenAICompatibleProviderIdentity:
    """Stable secret-free identity for adapter capabilities and request configuration."""

    adapter_identity: str
    model: str
    structured_output_schema_name: str
    decoding_configuration: tuple[tuple[str, int | float], ...]
    capabilities: OpenAICompatibleProviderCapabilities
    format_version: int = OPENAI_COMPATIBLE_PROVIDER_IDENTITY_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != OPENAI_COMPATIBLE_PROVIDER_IDENTITY_FORMAT_VERSION:
            raise ValueError(
                f"unsupported provider identity format_version: {self.format_version}"
            )
        if self.adapter_identity != OPENAI_COMPATIBLE_ADAPTER_IDENTITY:
            raise ValueError(f"unsupported adapter identity: {self.adapter_identity}")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("provider identity model must be a non-empty string")
        if self.structured_output_schema_name != OPENAI_COMPATIBLE_STRUCTURED_OUTPUT_SCHEMA_NAME:
            raise ValueError(
                "provider identity structured-output schema name is not canonical"
            )
        if not isinstance(self.capabilities, OpenAICompatibleProviderCapabilities):
            raise TypeError(
                "provider identity capabilities must be OpenAICompatibleProviderCapabilities"
            )
        keys = tuple(key for key, _ in self.decoding_configuration)
        if len(set(keys)) != len(keys):
            raise ValueError("provider identity decoding keys must be unique")
        if tuple(sorted(self.decoding_configuration)) != self.decoding_configuration:
            raise ValueError("provider identity decoding configuration must be sorted")

    @property
    def provider_capabilities(self) -> tuple[str, ...]:
        """Tokens directly consumable by #1386 capability preflight."""

        return self.capabilities.capability_tokens

    @property
    def effective_decoding_configuration(self) -> dict[str, int | float]:
        return dict(self.decoding_configuration)

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "adapter_identity": self.adapter_identity,
            "model": self.model,
            "structured_output_schema_name": self.structured_output_schema_name,
            "decoding_configuration": self.effective_decoding_configuration,
            "capabilities": self.capabilities.to_mapping(),
        }


def describe_openai_compatible_provider(
    provider: OpenAICompatibleProviderIdentitySource,
) -> OpenAICompatibleProviderIdentity:
    """Describe the canonical adapter without secrets, endpoint data, or semantic payload."""

    model = getattr(provider, "model", None)
    decoding_config = getattr(provider, "decoding_config", None)
    decoding_capabilities = getattr(provider, "decoding_capabilities", None)
    if not isinstance(model, str) or not model.strip():
        raise TypeError("provider identity source must expose a non-empty model")
    if not isinstance(decoding_config, OpenAICompatibleDecodingConfig):
        raise TypeError(
            "provider identity source must expose OpenAICompatibleDecodingConfig"
        )
    if not isinstance(
        decoding_capabilities, OpenAICompatibleDecodingCapabilities
    ):
        raise TypeError(
            "provider identity source must expose OpenAICompatibleDecodingCapabilities"
        )

    supported_decoding_controls = tuple(
        sorted(decoding_capabilities.supported_controls)
    )
    capabilities = OpenAICompatibleProviderCapabilities(
        structured_semantic_channels=OPENAI_COMPATIBLE_STRUCTURED_SEMANTIC_CHANNELS,
        supported_decoding_controls=supported_decoding_controls,
        buffered=True,
        streaming=True,
        seed_control_supported="seed" in decoding_capabilities.supported_controls,
    )
    return OpenAICompatibleProviderIdentity(
        adapter_identity=OPENAI_COMPATIBLE_ADAPTER_IDENTITY,
        model=model,
        structured_output_schema_name=OPENAI_COMPATIBLE_STRUCTURED_OUTPUT_SCHEMA_NAME,
        decoding_configuration=tuple(sorted(decoding_config.to_mapping().items())),
        capabilities=capabilities,
    )
