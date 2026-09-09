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
LLAMA_CPP_THINKING_CHAT_COUNTER_VERSION = "1"


class LlamaCppThinkingChatInputCounter(LlamaCppChatInputCounter):
    """Exact llama.cpp counter for the qualified Gemma thinking-control body.

    The parent counter owns the transport, framing method and runtime binding.
    This specialization only admits the exact additional request field used by
    the current llama-server qualification path and preserves it unchanged in
    both full and empty-content counting requests.
    """

    @property
    def evidence_identity(self) -> SerializedInputCounterIdentity:
        base = super().evidence_identity
        parameters = dict(base.parameters)
        parameters["thinking_control"] = "chat_template_kwargs.enable_thinking=false"
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
        template_kwargs = body.pop("chat_template_kwargs", None)
        payload = super()._validated_payload(body)
        if template_kwargs is None:
            return payload
        if not isinstance(template_kwargs, Mapping):
            raise LlamaCppInputCounterError(
                "llama.cpp chat_template_kwargs must be an object"
            )
        if set(template_kwargs) != {"enable_thinking"}:
            raise LlamaCppInputCounterError(
                "llama.cpp exact counter supports only "
                "chat_template_kwargs.enable_thinking"
            )
        enable_thinking = template_kwargs.get("enable_thinking")
        if enable_thinking is not False:
            raise LlamaCppInputCounterError(
                "current llama.cpp qualification counter requires "
                "chat_template_kwargs.enable_thinking=false"
            )
        payload["chat_template_kwargs"] = {"enable_thinking": False}
        return payload
