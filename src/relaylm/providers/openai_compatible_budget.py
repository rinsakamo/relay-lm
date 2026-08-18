from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.cognitive import CognitiveInput
from relaylm.providers.openai_compatible import _request_body
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig


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


@dataclass(frozen=True, slots=True)
class OpenAICompatibleSerializedInputCounter:
    """Count the model-input shape produced by the OpenAI-compatible adapter.

    The caller supplies the configured provider/model-specific tokenizer or
    conservative bounded estimator. RelayLM defines no generic token heuristic.

    The adapter's existing `_request_body` is the serialization authority. The
    transport-only `stream` flag is removed before the model-input mapping is
    passed to the counter, so buffered and streaming generation share the same
    token-accounting input. Explicit provider decoding controls are carried into
    the counted request shape unchanged; the supplied counter decides whether
    they affect its provider/model-specific accounting.
    """

    model: str
    count_input: OpenAICompatibleTokenCountFunction
    decoding_config: OpenAICompatibleDecodingConfig = field(
        default_factory=OpenAICompatibleDecodingConfig
    )
    evidence_identity: SerializedInputCounterIdentity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty string")
        if not callable(self.count_input):
            raise TypeError("count_input must be callable")
        if not isinstance(self.decoding_config, OpenAICompatibleDecodingConfig):
            raise TypeError("decoding_config must be OpenAICompatibleDecodingConfig")
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
    ) -> SerializedInputTokenCount:
        request_body = _request_body(
            model=self.model,
            cognitive_input=cognitive_input,
            stream=False,
            decoding_config=self.decoding_config,
        )
        model_input = {
            key: value
            for key, value in request_body.items()
            if key != "stream"
        }
        count = self.count_input(model_input)
        if not isinstance(count, SerializedInputTokenCount):
            raise TypeError("count_input must return SerializedInputTokenCount")
        if (
            self.evidence_identity is not None
            and count.mode is not self.evidence_identity.mode
        ):
            raise ValueError(
                "serialized-input counter result mode does not match evidence identity"
            )
        return count
