from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from relaylm.budget_enforcement import SerializedInputTokenCount
from relaylm.cognitive import CognitiveInput
from relaylm.providers.openai_compatible import _request_body
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig


OpenAICompatibleTokenCountFunction = Callable[
    [Mapping[str, Any]],
    SerializedInputTokenCount,
]


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

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty string")
        if not callable(self.count_input):
            raise TypeError("count_input must be callable")
        if not isinstance(self.decoding_config, OpenAICompatibleDecodingConfig):
            raise TypeError("decoding_config must be OpenAICompatibleDecodingConfig")

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
        return count
