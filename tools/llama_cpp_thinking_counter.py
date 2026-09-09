from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from relaylm.actual_model_llama_cpp import (
    LlamaCppChatInputCounter,
    LlamaCppInputCounterError,
)
from relaylm.providers.openai_compatible_budget import SerializedInputCounterIdentity


LLAMA_CPP_GEMMA_THINKING_COUNTER_VERSION = "2"
LLAMA_CPP_GEMMA_THINKING_REQUEST_EXTENSION = (
    "chat_template_kwargs.enable_thinking:bool"
)


class LlamaCppGemmaThinkingChatInputCounter(LlamaCppChatInputCounter):
    """Exact llama.cpp counter that preserves Gemma request-time Thinking control.

    This is an actual-model qualification helper only. It deliberately extends
    the existing fail-closed llama.cpp request boundary by exactly one field:

        chat_template_kwargs = {"enable_thinking": <bool>}

    It does not register a production backend or infer a reasoning setting.
    The caller remains responsible for requiring ``False`` when the qualified
    scientific condition is explicit Thinking OFF.
    """

    @property
    def evidence_identity(self) -> SerializedInputCounterIdentity:
        base = super().evidence_identity
        parameters = dict(base.parameters)
        parameters["request_extension"] = LLAMA_CPP_GEMMA_THINKING_REQUEST_EXTENSION
        return SerializedInputCounterIdentity(
            capability=base.capability,
            implementation=base.implementation,
            version=LLAMA_CPP_GEMMA_THINKING_COUNTER_VERSION,
            mode=base.mode,
            tokenizer_identity=base.tokenizer_identity,
            parameters=tuple(sorted(parameters.items())),
            format_version=base.format_version,
        )

    def _validated_payload(self, model_input: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(model_input, Mapping):
            return super()._validated_payload(model_input)

        base_input = dict(model_input)
        has_extension = "chat_template_kwargs" in base_input
        raw_extension = base_input.pop("chat_template_kwargs", None)
        payload = super()._validated_payload(base_input)

        if not has_extension:
            return payload
        if not isinstance(raw_extension, Mapping):
            raise LlamaCppInputCounterError(
                "llama.cpp chat_template_kwargs must be an object"
            )
        unknown = sorted(set(raw_extension) - {"enable_thinking"})
        if unknown:
            raise LlamaCppInputCounterError(
                "unsupported llama.cpp chat_template_kwargs fields: "
                + ", ".join(unknown)
            )
        if set(raw_extension) != {"enable_thinking"}:
            raise LlamaCppInputCounterError(
                "llama.cpp chat_template_kwargs must contain exactly enable_thinking"
            )
        enable_thinking = raw_extension.get("enable_thinking")
        if not isinstance(enable_thinking, bool):
            raise LlamaCppInputCounterError(
                "llama.cpp chat_template_kwargs.enable_thinking must be bool"
            )

        payload["chat_template_kwargs"] = {"enable_thinking": enable_thinking}
        return payload
