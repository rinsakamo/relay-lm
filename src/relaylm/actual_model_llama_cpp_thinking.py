from __future__ import annotations

import json
import urllib.error
import urllib.request
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
LLAMA_CPP_THINKING_CHAT_COUNTER_VERSION = "3"
LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS = 600.0


class LlamaCppThinkingChatInputCounter(LlamaCppChatInputCounter):
    """Exact llama.cpp counter for the qualified reasoning-OFF body.

    The current qualified OpenAI-compatible wire is ``reasoning_effort=none``.
    Generation and exact input counting must preserve that field plus
    ``stream=false`` unchanged. The qualification counter owns a long bounded
    wait for the shared single-slot laboratory; it does not retry a request.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if kwargs.get("post_json") is None:
            kwargs["post_json"] = _qualification_post_json
        super().__init__(*args, **kwargs)

    @property
    def evidence_identity(self) -> SerializedInputCounterIdentity:
        base = super().evidence_identity
        parameters = dict(base.parameters)
        parameters["thinking_control"] = "reasoning_effort=none"
        parameters["stream_control"] = "stream=false"
        parameters["request_timeout_seconds"] = (
            LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS
        )
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


def _qualification_post_json(
    url: str,
    payload: Mapping[str, Any],
    api_key: str | None,
) -> object:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if api_key is not None:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        url,
        data=json.dumps(
            dict(payload),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS,
        ) as response:
            if response.status != 200:
                raise LlamaCppInputCounterError(
                    f"llama.cpp input-token endpoint returned HTTP {response.status}"
                )
            return json.loads(response.read().decode("utf-8"))
    except LlamaCppInputCounterError:
        raise
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise LlamaCppInputCounterError(
            f"llama.cpp input-token request failed: {exc}"
        ) from exc
