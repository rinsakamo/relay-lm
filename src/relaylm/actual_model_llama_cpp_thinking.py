from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from relaylm.actual_model_llama_cpp import (
    LlamaCppChatInputCounter,
    LlamaCppInputCounterError,
)
from relaylm.providers.openai_compatible_budget import SerializedInputCounterIdentity


LLAMA_CPP_THINKING_CHAT_COUNTER_CAPABILITY = (
    "llama_cpp.chat-input.serialized-input.thinking-v1"
)
LLAMA_CPP_THINKING_CHAT_COUNTER_VERSION = "2"


class LlamaCppThinkingChatInputCounter(LlamaCppChatInputCounter):
    """Exact llama.cpp counter for the qualified reasoning-OFF body.

    The parent counter owns the transport, framing method and runtime binding.
    This specialization admits only the exact additional request fields used by
    the current llama-server qualification path and preserves them unchanged in
    both full and empty-content counting requests.
    """

    @property
    def evidence_identity(self) -> SerializedInputCounterIdentity:
        base = super().evidence_identity
        parameters = dict(base.parameters)
        parameters["thinking_control"] = "reasoning_effort=none"
        parameters["stream_control"] = "stream=false"
        return SerializedInputCounterIdentity(
            capability=LLAMA_CPP_THINKING_CHAT_COUNTER_CAPABILITY,
            implementation=base.implementation,
            version=LLAMA_CPP_THINKING_CHAT_COUNTER_VERSION,
            mode=base.mode,
            tokenizer_identity=base.tokenizer_identity,
            parameters=tuple(sorted(parameters.items())),
        )

    def _validated_payload(self, model_input: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(model_input, Mapping):
            raise TypeError("model_input must be a mapping")
        body = dict(model_input)
        has_reasoning_effort = "reasoning_effort" in body
        reasoning_effort = body.pop("reasoning_effort", None)
        has_stream = "stream" in body
        stream = body.pop("stream", None)
        payload = super()._validated_payload(body)

        if has_reasoning_effort:
            if reasoning_effort != "none":
                raise LlamaCppInputCounterError(
                    "current llama.cpp qualification counter requires "
                    "reasoning_effort=none"
                )
            payload["reasoning_effort"] = "none"

        if has_stream:
            if stream is not False:
                raise LlamaCppInputCounterError(
                    "current llama.cpp qualification counter requires stream=false"
                )
            payload["stream"] = False
        return payload
