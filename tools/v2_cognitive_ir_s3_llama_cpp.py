from __future__ import annotations

from collections.abc import Mapping
import json

import httpx

from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_ir_s2_host import S2HostError
from tools.v2_cognitive_ir_s2_selected_llama_cpp import (
    LlamaCppThinkingOffInputCounter,
    S2_SELECTED_LLAMA_CPP_ENDPOINT,
    S2_SELECTED_LLAMA_CPP_REASONING_EFFORT,
    S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS,
    _require_selected_base_url,
)


S3_LLAMA_CPP_ENDPOINT = S2_SELECTED_LLAMA_CPP_ENDPOINT
S3_LLAMA_CPP_TIMEOUT_SECONDS = S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS
S3_LLAMA_CPP_REASONING_EFFORT = S2_SELECTED_LLAMA_CPP_REASONING_EFFORT
S3_LLAMA_CPP_CONTEXT_LENGTH = 8192
S3_LLAMA_CPP_MAX_OUTPUT_TOKENS = 512

_RULE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "permutation": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0, "maximum": 3},
            "minItems": 4,
            "maxItems": 4,
            "uniqueItems": True,
        },
        "offsets": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0, "maximum": 9},
            "minItems": 4,
            "maxItems": 4,
        },
        "modulus": {"type": "integer", "const": 10},
    },
    "required": ["permutation", "offsets", "modulus"],
    "additionalProperties": False,
}
_VECTOR_SCHEMA: dict[str, object] = {
    "type": "array",
    "items": {"type": "integer", "minimum": 0, "maximum": 9},
    "minItems": 4,
    "maxItems": 4,
}
_INDEX_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"index": {"type": "integer", "minimum": 0, "maximum": 3}},
    "required": ["index"],
    "additionalProperties": False,
}


class S3LlamaCppClient:
    """Exact one-shard S3 llama.cpp transport with no retry surface."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        call_plan: tuple[str, ...],
        timeout_seconds: float = S3_LLAMA_CPP_TIMEOUT_SECONDS,
        max_output_tokens: int = S3_LLAMA_CPP_MAX_OUTPUT_TOKENS,
        temperature: int | float = 0.0,
        seed: int | None = None,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        _require_selected_base_url(base_url)
        if not isinstance(model, str) or not model.strip():
            raise S2HostError("S3 provider model must be non-empty")
        if not call_plan or any(not isinstance(item, str) or not item for item in call_plan):
            raise S2HostError("S3 call plan must be a non-empty string tuple")
        if len(set(call_plan)) != len(call_plan):
            raise S2HostError("S3 call plan question ids must be unique")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise S2HostError("S3 timeout_seconds must be numeric")
        if timeout_seconds < S3_LLAMA_CPP_TIMEOUT_SECONDS:
            raise S2HostError(
                f"S3 llama.cpp timeout must be >= {S3_LLAMA_CPP_TIMEOUT_SECONDS:g}s"
            )
        if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
            raise S2HostError("S3 max_output_tokens must be a positive integer")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            raise S2HostError("S3 temperature must be numeric")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise S2HostError("S3 request seed must be an integer or null")
        if api_key is not None and not isinstance(api_key, str):
            raise TypeError("api_key must be a string or null")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.call_plan = call_plan
        self.timeout_seconds = float(timeout_seconds)
        self.max_output_tokens = max_output_tokens
        self.temperature = float(temperature)
        self.seed = seed
        self.api_key = api_key
        self.provider_attempts = 0
        self.provider_completions = 0
        self._call_index = 0
        self._client = http_client or httpx.Client(timeout=self.timeout_seconds)
        self._owns_client = http_client is None
        self._counter = LlamaCppThinkingOffInputCounter(
            base_url=self.base_url,
            model=self.model,
            http_client=self._client,
        )

    @property
    def input_count_attempts(self) -> int:
        return self._counter.request_attempts

    @property
    def input_count_completions(self) -> int:
        return self._counter.request_completions

    @property
    def transport_identity(self) -> dict[str, object]:
        return {
            "api": "openai-chat-completions-s3-llama-cpp-v1",
            "endpoint": self.base_url,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "seed": self.seed,
            "reasoning": "off",
            "reasoning_control": "openai-top-level-reasoning_effort",
            "reasoning_effort": S3_LLAMA_CPP_REASONING_EFFORT,
            "exact_input_accounting": "chat-completions-input-tokens-full+empty-message-framing-v1",
            "planned_semantic_calls": len(self.call_plan),
        }

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @staticmethod
    def _validate_messages(messages: tuple[dict[str, str], ...]) -> list[dict[str, str]]:
        if not messages:
            raise S2HostError("S3 messages must not be empty")
        normalized: list[dict[str, str]] = []
        for message in messages:
            if set(message) != {"role", "content"}:
                raise S2HostError("each S3 message must contain exactly role/content")
            role = message["role"]
            content = message["content"]
            if role not in {"system", "user", "assistant"}:
                raise S2HostError("unsupported S3 message role")
            if not isinstance(content, str) or not content:
                raise S2HostError("S3 message content must be non-empty")
            normalized.append({"role": role, "content": content})
        return normalized

    @staticmethod
    def _non_negative_integer(value: object, *, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise StructureProposalError(f"{label} must be a non-negative integer")
        return value

    @staticmethod
    def _reasoning_text_is_empty(message: Mapping[str, object]) -> bool:
        for key in ("reasoning", "reasoning_content"):
            value = message.get(key)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return False
        return True

    @staticmethod
    def _response_format(question_id: str, output_kind: str) -> dict[str, object] | None:
        if output_kind == "text":
            return None
        if output_kind == "rule":
            name, schema = "relaylm2_s3_reusable_rule", _RULE_SCHEMA
        elif output_kind == "vector":
            name, schema = "relaylm2_s3_target_vector", _VECTOR_SCHEMA
        elif output_kind == "index":
            name, schema = "relaylm2_s3_option_index", _INDEX_SCHEMA
        else:
            raise S2HostError(f"unsupported S3 output kind for {question_id}: {output_kind}")
        return {
            "type": "json_schema",
            "json_schema": {"name": name, "strict": True, "schema": schema},
        }

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        if self._call_index >= len(self.call_plan):
            raise StructureProposalError("S3 attempted an undeclared extra provider call")
        expected = self.call_plan[self._call_index]
        if question_id != expected:
            raise StructureProposalError(
                f"S3 call order drift: expected {expected!r}, got {question_id!r}"
            )
        normalized_messages = self._validate_messages(messages)
        body: dict[str, object] = {
            "model": self.model,
            "messages": normalized_messages,
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "reasoning_effort": S3_LLAMA_CPP_REASONING_EFFORT,
        }
        response_format = self._response_format(question_id, output_kind)
        if response_format is not None:
            body["response_format"] = response_format
        if self.seed is not None:
            body["seed"] = self.seed

        exact_count = self._counter.count_input(body)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.provider_attempts += 1
        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
            )
        except httpx.HTTPError as exc:
            raise StructureProposalError(f"S3 provider request failed: {exc}") from exc
        if not response.is_success:
            raise StructureProposalError(
                f"S3 provider request failed with status {response.status_code}"
            )
        try:
            envelope = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise StructureProposalError("S3 provider response is not valid JSON") from exc
        if not isinstance(envelope, Mapping):
            raise StructureProposalError("S3 provider response must be an object")
        choices = envelope.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise StructureProposalError("S3 provider response must contain exactly one choice")
        choice = choices[0]
        if not isinstance(choice, Mapping):
            raise StructureProposalError("S3 provider choice must be an object")
        if choice.get("finish_reason") != "stop":
            raise StructureProposalError(
                f"S3 provider choice did not finish with stop: {choice.get('finish_reason')!r}"
            )
        message = choice.get("message")
        if not isinstance(message, Mapping):
            raise StructureProposalError("S3 provider message must be an object")
        if not self._reasoning_text_is_empty(message):
            raise StructureProposalError("S3 reasoning-off response exposed reasoning content")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise StructureProposalError("S3 provider content must be non-empty")

        usage = envelope.get("usage")
        if not isinstance(usage, Mapping):
            raise StructureProposalError("S3 provider usage must be an object")
        prompt_tokens = self._non_negative_integer(
            usage.get("prompt_tokens"), label="prompt_tokens"
        )
        if prompt_tokens != exact_count.total_input_tokens:
            raise StructureProposalError(
                "S3 provider prompt_tokens disagree with exact llama.cpp input accounting"
            )
        completion_tokens = self._non_negative_integer(
            usage.get("completion_tokens"), label="completion_tokens"
        )
        details = usage.get("completion_tokens_details")
        if details is not None:
            if not isinstance(details, Mapping):
                raise StructureProposalError("completion_tokens_details must be an object or null")
            if "reasoning_tokens" in details:
                reasoning_tokens = self._non_negative_integer(
                    details.get("reasoning_tokens"), label="reasoning_tokens"
                )
                if reasoning_tokens != 0:
                    raise StructureProposalError(
                        f"S3 reasoning-off verification failed: reasoning_tokens={reasoning_tokens}"
                    )
        response_id = envelope.get("id")
        if response_id is not None and not isinstance(response_id, str):
            raise StructureProposalError("S3 provider response id must be a string or null")

        self.provider_completions += 1
        self._call_index += 1
        return ExperimentCompletion(
            content=content,
            input_tokens=exact_count.total_input_tokens,
            output_tokens=completion_tokens,
            response_id=response_id,
        )

    def require_complete_plan(self) -> None:
        if self._call_index != len(self.call_plan):
            raise S2HostError(
                f"S3 shard ended before frozen call plan: {self._call_index}/{len(self.call_plan)}"
            )
        if self.provider_attempts != self.provider_completions:
            raise S2HostError("S3 provider attempts/completions diverged")
        if self.input_count_attempts != 2 * self.provider_attempts:
            raise S2HostError("S3 exact input-token instrumentation count drifted")
        if self.input_count_completions != self.input_count_attempts:
            raise S2HostError("S3 exact input-token attempts/completions diverged")
