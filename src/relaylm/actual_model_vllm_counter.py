from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from relaylm.actual_model_targets import ActualModelRepositorySnapshotTarget
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.providers.openai_compatible_budget import SerializedInputCounterIdentity
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityAttestation,
)


VLLM_SERVING_COUNTER_CAPABILITY = "vllm.serving-tokenizer.serialized-input.v1"
VLLM_SERVING_COUNTER_IMPLEMENTATION = "vllm-tokenize-endpoint-counter"
VLLM_SERVING_COUNTER_VERSION = "1"
VLLM_RENDERER_METHOD = "chat-completion-effective-template-kwargs-v1"
VLLM_FRAMING_METHOD = "same-message-shape-empty-content-v1"

PostJSON = Callable[[str, Mapping[str, Any], str | None], object]


class VLLMServingTokenizerCounterError(ValueError):
    """The live vLLM serving tokenizer cannot prove the declared exact count."""


@dataclass(frozen=True, slots=True)
class VLLMServingTokenizerCounter:
    """Count current RelayLM provider input with the exact live vLLM renderer.

    RelayLM's production OpenAI-compatible request builder remains the input
    serialization authority. This host-only adapter removes controls that vLLM
    applies after chat rendering, reconstructs only the chat-template kwargs
    that vLLM derives from the current proven reasoning controls, and delegates
    tokenization to the live ``/tokenize`` endpoint.
    """

    base_url: str
    target: ActualModelRepositorySnapshotTarget
    reasoning_capability: VLLMReasoningCapabilityAttestation
    expected_max_model_len: int
    api_key: str | None = None
    post_json: PostJSON | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.target, ActualModelRepositorySnapshotTarget):
            raise TypeError("target must be ActualModelRepositorySnapshotTarget")
        if not isinstance(
            self.reasoning_capability,
            VLLMReasoningCapabilityAttestation,
        ):
            raise TypeError(
                "reasoning_capability must be VLLMReasoningCapabilityAttestation"
            )
        if (
            self.reasoning_capability.target_id != self.target.target_id
            or self.reasoning_capability.target_revision != self.target.revision
        ):
            raise VLLMServingTokenizerCounterError(
                "vLLM reasoning capability does not match the frozen target"
            )
        if (
            self.reasoning_capability.model_artifact_identity
            != self.target.model_artifact_identity
        ):
            raise VLLMServingTokenizerCounterError(
                "vLLM reasoning capability model artifact does not match target"
            )
        if isinstance(self.expected_max_model_len, bool) or not isinstance(
            self.expected_max_model_len,
            int,
        ):
            raise TypeError("expected_max_model_len must be an integer")
        if self.expected_max_model_len <= 0:
            raise ValueError("expected_max_model_len must be positive")
        live_max_model_len = self.reasoning_capability.backend_attestation.max_model_len
        if live_max_model_len != self.expected_max_model_len:
            raise VLLMServingTokenizerCounterError(
                "vLLM backend max_model_len does not match expected_max_model_len"
            )
        if self.post_json is not None and not callable(self.post_json):
            raise TypeError("post_json must be callable or None")
        _tokenize_url(self.base_url)

    @property
    def evidence_identity(self) -> SerializedInputCounterIdentity:
        parameters = {
            "backend": "vllm",
            "backend_version": self.reasoning_capability.backend_version,
            "chat_template_identity": self.target.chat_template_identity,
            "context_limit": self.expected_max_model_len,
            "framing_method": VLLM_FRAMING_METHOD,
            "renderer_method": VLLM_RENDERER_METHOD,
            "request_model": self.reasoning_capability.request_model,
            "target_id": self.target.target_id,
        }
        return SerializedInputCounterIdentity(
            capability=VLLM_SERVING_COUNTER_CAPABILITY,
            implementation=VLLM_SERVING_COUNTER_IMPLEMENTATION,
            version=VLLM_SERVING_COUNTER_VERSION,
            mode=TokenCountMode.EXACT,
            tokenizer_identity=self.target.tokenizer_identity,
            parameters=tuple(sorted(parameters.items())),
        )

    def count_input(
        self,
        model_input: Mapping[str, Any],
    ) -> SerializedInputTokenCount:
        full_payload = self._tokenize_payload(model_input)
        framing_payload = dict(full_payload)
        framing_payload["messages"] = [
            {"role": message["role"], "content": ""}
            for message in full_payload["messages"]
        ]

        loader = self.post_json or _post_json
        url = _tokenize_url(self.base_url)
        total = _parse_tokenize_count(
            loader(url, full_payload, self.api_key),
            expected_max_model_len=self.expected_max_model_len,
        )
        framing = _parse_tokenize_count(
            loader(url, framing_payload, self.api_key),
            expected_max_model_len=self.expected_max_model_len,
        )
        try:
            return SerializedInputTokenCount(
                total_input_tokens=total,
                required_input_framing_tokens=framing,
                mode=TokenCountMode.EXACT,
            )
        except (TypeError, ValueError) as exc:
            raise VLLMServingTokenizerCounterError(
                f"invalid vLLM serving-tokenizer accounting: {exc}"
            ) from exc

    def _tokenize_payload(
        self,
        model_input: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(model_input, Mapping):
            raise TypeError("model_input must be a mapping")
        allowed = {
            "model",
            "messages",
            "temperature",
            "top_p",
            "seed",
            "max_tokens",
            "response_format",
            "reasoning_effort",
            "thinking_token_budget",
            "chat_template_kwargs",
        }
        unknown = sorted(set(model_input) - allowed)
        if unknown:
            raise VLLMServingTokenizerCounterError(
                "unsupported vLLM model-input fields: " + ", ".join(unknown)
            )

        model = model_input.get("model")
        if model != self.reasoning_capability.request_model:
            raise VLLMServingTokenizerCounterError(
                "vLLM model-input model does not match attested request model"
            )
        messages = _plain_messages(model_input.get("messages"))
        template_kwargs = _template_kwargs(model_input.get("chat_template_kwargs"))

        reasoning_effort = model_input.get("reasoning_effort")
        if reasoning_effort is not None:
            if reasoning_effort != "none":
                raise VLLMServingTokenizerCounterError(
                    "unsupported vLLM reasoning_effort for exact product counter"
                )
            if template_kwargs.get("enable_thinking") is True:
                raise VLLMServingTokenizerCounterError(
                    "reasoning_effort none conflicts with enable_thinking true"
                )
            template_kwargs["reasoning_effort"] = "none"
            template_kwargs.setdefault("enable_thinking", False)

        thinking_token_budget = model_input.get("thinking_token_budget")
        if thinking_token_budget is not None:
            if (
                isinstance(thinking_token_budget, bool)
                or not isinstance(thinking_token_budget, int)
                or thinking_token_budget <= 0
            ):
                raise VLLMServingTokenizerCounterError(
                    "thinking_token_budget must be a positive integer"
                )
            if template_kwargs.get("enable_thinking") is not True:
                raise VLLMServingTokenizerCounterError(
                    "bounded vLLM input requires enable_thinking true"
                )

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "add_generation_prompt": True,
            "return_token_strs": False,
        }
        if template_kwargs:
            payload["chat_template_kwargs"] = template_kwargs
        return payload


def _plain_messages(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise VLLMServingTokenizerCounterError(
            "vLLM model-input messages must be a non-empty list"
        )
    messages: list[dict[str, str]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise VLLMServingTokenizerCounterError(
                f"vLLM message[{index}] must be an object"
            )
        unknown = sorted(set(raw) - {"role", "content"})
        if unknown:
            raise VLLMServingTokenizerCounterError(
                f"unsupported vLLM message[{index}] fields: " + ", ".join(unknown)
            )
        role = raw.get("role")
        content = raw.get("content")
        if not isinstance(role, str) or not role.strip():
            raise VLLMServingTokenizerCounterError(
                f"vLLM message[{index}].role must be a non-empty string"
            )
        if not isinstance(content, str):
            raise VLLMServingTokenizerCounterError(
                f"vLLM message[{index}].content must be a string"
            )
        messages.append({"role": role, "content": content})
    return messages


def _template_kwargs(value: object) -> dict[str, str | int | bool]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise VLLMServingTokenizerCounterError(
            "chat_template_kwargs must be an object"
        )
    result: dict[str, str | int | bool] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not key.strip():
            raise VLLMServingTokenizerCounterError(
                "chat_template_kwargs keys must be non-empty strings"
            )
        if not isinstance(raw, (str, int, bool)):
            raise VLLMServingTokenizerCounterError(
                "chat_template_kwargs values must be strings, integers, or booleans"
            )
        result[key] = raw
    return result


def _parse_tokenize_count(
    response: object,
    *,
    expected_max_model_len: int,
) -> int:
    if not isinstance(response, Mapping):
        raise VLLMServingTokenizerCounterError(
            "vLLM /tokenize response must be an object"
        )
    count = response.get("count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise VLLMServingTokenizerCounterError(
            "vLLM /tokenize count must be a non-negative integer"
        )
    max_model_len = response.get("max_model_len")
    if max_model_len != expected_max_model_len:
        raise VLLMServingTokenizerCounterError(
            "vLLM /tokenize max_model_len does not match expected_max_model_len"
        )
    return count


def _tokenize_url(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise VLLMServingTokenizerCounterError(
            "vLLM base_url must be a non-empty string"
        )
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise VLLMServingTokenizerCounterError(
            "vLLM base_url must be an HTTP(S) URL"
        )
    origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
    return f"{origin}/tokenize"


def _post_json(
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
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise VLLMServingTokenizerCounterError(
                    f"vLLM /tokenize returned HTTP {response.status}"
                )
            return json.loads(response.read().decode("utf-8"))
    except VLLMServingTokenizerCounterError:
        raise
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise VLLMServingTokenizerCounterError(
            f"vLLM /tokenize request failed: {exc}"
        ) from exc
