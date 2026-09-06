from __future__ import annotations

from collections.abc import Mapping
import json

import httpx

from relaylm.v2_cognitive_ir_calibration import CalibrationError
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError


_REASONING_MODE = "off"
_REASONING_VERIFICATION = "usage.completion_tokens_details.reasoning_tokens==0"


class ReasoningOffOpenAICompatibleStructuredCalibrationClient:
    """OpenAI-compatible structured client that fail-closes unless reasoning is actually off.

    LM Studio's documented Chat Completions surface does not expose a reasoning request field.
    The host therefore keeps the wire request OpenAI-compatible and verifies the effective
    execution condition from the returned usage/accounting plus any exposed reasoning fields.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 300.0,
        max_tokens: int = 128,
        temperature: int | float = 0.0,
        seed: int | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise CalibrationError("provider base_url must be non-empty")
        if not isinstance(model, str) or not model.strip():
            raise CalibrationError("provider model must be non-empty")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise CalibrationError("timeout_seconds must be numeric")
        if timeout_seconds <= 0:
            raise CalibrationError("timeout_seconds must be positive")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
            raise CalibrationError("max_tokens must be a positive integer")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            raise CalibrationError("temperature must be numeric")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise CalibrationError("seed must be an integer or null")
        if api_key is not None and not isinstance(api_key, str):
            raise TypeError("api_key must be a string or null")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = float(timeout_seconds)
        self.max_tokens = max_tokens
        self.temperature = float(temperature)
        self.seed = seed
        self.provider_attempts = 0
        self.provider_completions = 0
        self._client = http_client or httpx.Client(timeout=self.timeout_seconds)
        self._owns_client = http_client is None

    @property
    def transport_identity(self) -> dict[str, object]:
        return {
            "api": "openai-chat-completions-json-schema-v1",
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "seed": self.seed,
            "structured_output": True,
            "reasoning_mode": _REASONING_MODE,
            "reasoning_verification": _REASONING_VERIFICATION,
        }

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @staticmethod
    def _validate_messages(messages: tuple[dict[str, str], ...]) -> list[dict[str, str]]:
        if not messages:
            raise CalibrationError("messages must not be empty")
        normalized: list[dict[str, str]] = []
        for message in messages:
            if set(message) != {"role", "content"}:
                raise CalibrationError("each message must contain exactly role/content")
            role = message["role"]
            content = message["content"]
            if role not in {"system", "user", "assistant"}:
                raise CalibrationError("unsupported message role")
            if not isinstance(content, str) or not content:
                raise CalibrationError("message content must be non-empty")
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

    def complete_structured(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> ExperimentCompletion:
        if not isinstance(schema_name, str) or not schema_name.strip():
            raise CalibrationError("schema_name must be non-empty")
        normalized_messages = self._validate_messages(messages)

        body: dict[str, object] = {
            "model": self.model,
            "messages": normalized_messages,
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": dict(schema),
                },
            },
        }
        if self.seed is not None:
            body["seed"] = self.seed
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
            raise StructureProposalError(f"provider request failed: {exc}") from exc
        if not response.is_success:
            raise StructureProposalError(
                f"provider request failed with status {response.status_code}"
            )
        try:
            envelope = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise StructureProposalError("provider response is not valid JSON") from exc
        if not isinstance(envelope, Mapping):
            raise StructureProposalError("provider response must be an object")

        choices = envelope.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise StructureProposalError("provider response must contain exactly one choice")
        choice = choices[0]
        if not isinstance(choice, Mapping):
            raise StructureProposalError("provider choice must be an object")
        finish_reason = choice.get("finish_reason")
        if finish_reason != "stop":
            raise StructureProposalError(
                f"provider choice did not finish with stop: {finish_reason!r}"
            )

        message = choice.get("message")
        if not isinstance(message, Mapping):
            raise StructureProposalError("provider message must be an object")
        if not self._reasoning_text_is_empty(message):
            raise StructureProposalError("reasoning-off response exposed non-empty reasoning content")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise StructureProposalError("provider message content must be non-empty")

        usage = envelope.get("usage")
        if not isinstance(usage, Mapping):
            raise StructureProposalError("provider usage must be an object")
        prompt_tokens = self._non_negative_integer(
            usage.get("prompt_tokens"),
            label="prompt_tokens",
        )
        completion_tokens = self._non_negative_integer(
            usage.get("completion_tokens"),
            label="completion_tokens",
        )
        details = usage.get("completion_tokens_details")
        if not isinstance(details, Mapping):
            raise StructureProposalError(
                "reasoning-off verification requires completion_tokens_details"
            )
        reasoning_tokens = self._non_negative_integer(
            details.get("reasoning_tokens"),
            label="reasoning_tokens",
        )
        if reasoning_tokens != 0:
            raise StructureProposalError(
                f"reasoning-off verification failed: reasoning_tokens={reasoning_tokens}"
            )

        response_id = envelope.get("id")
        if response_id is not None and not isinstance(response_id, str):
            raise StructureProposalError("provider response id must be a string or null")

        self.provider_completions += 1
        return ExperimentCompletion(
            content=content,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            response_id=response_id,
        )


def build_reasoning_off_lmstudio_calibration_client(
    *,
    base_url: str,
    model: str,
    api_key: str | None = None,
) -> ReasoningOffOpenAICompatibleStructuredCalibrationClient:
    """Build the frozen reasoning-off client for a fresh #2211 physical calibration."""

    return ReasoningOffOpenAICompatibleStructuredCalibrationClient(
        base_url=f"{base_url.rstrip('/')}/v1",
        model=model,
        api_key=api_key,
        timeout_seconds=300.0,
        max_tokens=128,
        temperature=0.0,
        seed=None,
    )
