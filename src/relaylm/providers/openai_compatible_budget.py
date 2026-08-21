from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput, CognitionPassRequest
from relaylm.providers.openai_compatible import (
    _request_body,
    _resolve_cognition_pass_request,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningRequest,
)
from relaylm.providers.openai_compatible_two_pass import (
    _conversation_request_body,
    _extraction_request_body,
)
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityAttestation,
)


OpenAICompatibleTokenCountFunction = Callable[
    [Mapping[str, Any]],
    SerializedInputTokenCount,
]
CounterEvidenceValue = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class SerializedInputCounterIdentity:
    """Secret-free, reproducible identity for one serialized-input counter."""

    capability: str
    implementation: str
    version: str
    mode: TokenCountMode
    tokenizer_identity: str
    parameters: tuple[tuple[str, CounterEvidenceValue], ...] = ()
    format_version: int = 1

    def __post_init__(self) -> None:
        if self.format_version != 1:
            raise ValueError(
                f"unsupported serialized-input counter identity format_version: {self.format_version}"
            )
        for name in (
            "capability",
            "implementation",
            "version",
            "tokenizer_identity",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.mode, TokenCountMode):
            raise TypeError("mode must be TokenCountMode")
        keys = tuple(key for key, _ in self.parameters)
        if len(set(keys)) != len(keys):
            raise ValueError("counter identity parameter keys must be unique")
        if keys != tuple(sorted(keys)):
            raise ValueError("counter identity parameter keys must be sorted")
        for key, value in self.parameters:
            if not isinstance(key, str) or not key.strip():
                raise ValueError("counter identity parameter keys must be non-empty strings")
            if _is_sensitive_identity_key(key):
                raise ValueError(f"counter identity must not persist sensitive field: {key}")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("counter identity parameters must be finite")
            if not isinstance(value, (str, int, float, bool)) and value is not None:
                raise TypeError("counter identity parameters must be JSON scalar values")

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "capability": self.capability,
            "implementation": self.implementation,
            "version": self.version,
            "mode": self.mode.value,
            "tokenizer_identity": self.tokenizer_identity,
            "parameters": dict(self.parameters),
        }


def _is_sensitive_identity_key(key: str) -> bool:
    lowered = key.casefold()
    return any(
        marker in lowered
        for marker in ("api_key", "passkey", "password", "secret", "token", "base_url")
    )


def _count_model_input(
    *,
    request_body: Mapping[str, Any],
    count_input: OpenAICompatibleTokenCountFunction,
    evidence_identity: SerializedInputCounterIdentity | None,
) -> SerializedInputTokenCount:
    model_input = {
        key: value
        for key, value in request_body.items()
        if key != "stream"
    }
    count = count_input(model_input)
    if not isinstance(count, SerializedInputTokenCount):
        raise TypeError("count_input must return SerializedInputTokenCount")
    if evidence_identity is not None and count.mode is not evidence_identity.mode:
        raise ValueError(
            "serialized-input counter result mode does not match evidence identity"
        )
    return count


@dataclass(frozen=True, slots=True)
class OpenAICompatibleSerializedInputCounter:
    """Count the exact model-input shape produced by the single-pass adapter.

    Production `_resolve_cognition_pass_request` and `_request_body` remain the
    authorities for per-pass decoding/reasoning realization and serialization.
    The transport-only `stream` field is removed before the caller-supplied
    model/tokenizer-specific counter receives the input mapping.
    """

    model: str
    count_input: OpenAICompatibleTokenCountFunction
    decoding_config: OpenAICompatibleDecodingConfig = field(
        default_factory=OpenAICompatibleDecodingConfig
    )
    decoding_capabilities: OpenAICompatibleDecodingCapabilities = field(
        default_factory=OpenAICompatibleDecodingCapabilities
    )
    vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None
    evidence_identity: SerializedInputCounterIdentity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty string")
        if not callable(self.count_input):
            raise TypeError("count_input must be callable")
        if not isinstance(self.decoding_config, OpenAICompatibleDecodingConfig):
            raise TypeError("decoding_config must be OpenAICompatibleDecodingConfig")
        if not isinstance(
            self.decoding_capabilities,
            OpenAICompatibleDecodingCapabilities,
        ):
            raise TypeError(
                "decoding_capabilities must be OpenAICompatibleDecodingCapabilities"
            )
        self.decoding_capabilities.require(self.decoding_config)
        if self.vllm_reasoning_capability is not None and not isinstance(
            self.vllm_reasoning_capability,
            VLLMReasoningCapabilityAttestation,
        ):
            raise TypeError(
                "vllm_reasoning_capability must be VLLMReasoningCapabilityAttestation or None"
            )
        if (
            self.vllm_reasoning_capability is not None
            and self.vllm_reasoning_capability.request_model != self.model
        ):
            raise ValueError(
                "vLLM reasoning capability request_model must match counter model"
            )
        if self.evidence_identity is not None and not isinstance(
            self.evidence_identity,
            SerializedInputCounterIdentity,
        ):
            raise TypeError(
                "evidence_identity must be SerializedInputCounterIdentity or None"
            )

    def count_serialized_input(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
        vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
    ) -> SerializedInputTokenCount:
        capability = vllm_reasoning_capability or self.vllm_reasoning_capability
        decoding_config, effective_reasoning = _resolve_cognition_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            decoding_config=self.decoding_config,
            decoding_capabilities=self.decoding_capabilities,
            vllm_reasoning_capability=capability,
        )
        request_body = _request_body(
            model=self.model,
            cognitive_input=cognitive_input,
            stream=False,
            decoding_config=decoding_config,
            reasoning_request=effective_reasoning,
            vllm_reasoning_capability=capability,
        )
        return _count_model_input(
            request_body=request_body,
            count_input=self.count_input,
            evidence_identity=self.evidence_identity,
        )


@dataclass(frozen=True, slots=True)
class OpenAICompatibleTwoPassSerializedInputCounter:
    """Count exact current two-pass provider model-input mappings.

    Production request builders remain the serialization authority. The counter
    resolves the same per-pass decoding/reasoning request as the provider, then
    removes only the transport-only `stream` field before delegating token
    semantics to the caller-supplied model/tokenizer-specific counter.
    """

    model: str
    count_input: OpenAICompatibleTokenCountFunction
    decoding_config: OpenAICompatibleDecodingConfig = field(
        default_factory=OpenAICompatibleDecodingConfig
    )
    decoding_capabilities: OpenAICompatibleDecodingCapabilities = field(
        default_factory=OpenAICompatibleDecodingCapabilities
    )
    vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None
    evidence_identity: SerializedInputCounterIdentity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty string")
        if not callable(self.count_input):
            raise TypeError("count_input must be callable")
        if not isinstance(self.decoding_config, OpenAICompatibleDecodingConfig):
            raise TypeError("decoding_config must be OpenAICompatibleDecodingConfig")
        if not isinstance(
            self.decoding_capabilities,
            OpenAICompatibleDecodingCapabilities,
        ):
            raise TypeError(
                "decoding_capabilities must be OpenAICompatibleDecodingCapabilities"
            )
        self.decoding_capabilities.require(self.decoding_config)
        if self.vllm_reasoning_capability is not None and not isinstance(
            self.vllm_reasoning_capability,
            VLLMReasoningCapabilityAttestation,
        ):
            raise TypeError(
                "vllm_reasoning_capability must be VLLMReasoningCapabilityAttestation or None"
            )
        if (
            self.vllm_reasoning_capability is not None
            and self.vllm_reasoning_capability.request_model != self.model
        ):
            raise ValueError(
                "vLLM reasoning capability request_model must match counter model"
            )
        if self.evidence_identity is not None and not isinstance(
            self.evidence_identity,
            SerializedInputCounterIdentity,
        ):
            raise TypeError(
                "evidence_identity must be SerializedInputCounterIdentity or None"
            )

    def count_conversation_input(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
        vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
    ) -> SerializedInputTokenCount:
        capability = vllm_reasoning_capability or self.vllm_reasoning_capability
        decoding_config, effective_reasoning = _resolve_cognition_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            decoding_config=self.decoding_config,
            decoding_capabilities=self.decoding_capabilities,
            vllm_reasoning_capability=capability,
        )
        request_body = _conversation_request_body(
            model=self.model,
            cognitive_input=cognitive_input,
            stream=False,
            decoding=decoding_config.to_mapping(),
            reasoning_request=effective_reasoning,
            vllm_reasoning_capability=capability,
        )
        return _count_model_input(
            request_body=request_body,
            count_input=self.count_input,
            evidence_identity=self.evidence_identity,
        )

    def count_extraction_input(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
        vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
    ) -> SerializedInputTokenCount:
        capability = vllm_reasoning_capability or self.vllm_reasoning_capability
        decoding_config, effective_reasoning = _resolve_cognition_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            decoding_config=self.decoding_config,
            decoding_capabilities=self.decoding_capabilities,
            vllm_reasoning_capability=capability,
        )
        request_body = _extraction_request_body(
            model=self.model,
            extraction_input=extraction_input,
            decoding=decoding_config.to_mapping(),
            reasoning_request=effective_reasoning,
            vllm_reasoning_capability=capability,
        )
        return _count_model_input(
            request_body=request_body,
            count_input=self.count_input,
            evidence_identity=self.evidence_identity,
        )
