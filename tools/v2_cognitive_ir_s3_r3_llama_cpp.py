from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

import httpx

from relaylm.v2_cognitive_ir_s3_r3 import S3_R3_MAX_OUTPUT_TOKENS
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_ir_s3_llama_cpp import (
    S3LlamaCppClient,
    S3_LLAMA_CPP_REASONING_EFFORT,
    S3_LLAMA_CPP_TIMEOUT_SECONDS,
)


class S3R3LlamaCppClient(S3LlamaCppClient):
    """S3-R3 transport: uniform 1024 ceiling plus fail-closed diagnostics."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        call_plan: tuple[str, ...],
        timeout_seconds: float = S3_LLAMA_CPP_TIMEOUT_SECONDS,
        max_output_tokens: int = S3_R3_MAX_OUTPUT_TOKENS,
        temperature: int | float = 0.0,
        seed: int | None = None,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            model=model,
            call_plan=call_plan,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            seed=seed,
            api_key=api_key,
            http_client=http_client,
        )
        self.last_failure_metadata: dict[str, object] | None = None

    @staticmethod
    def _safe_non_negative_integer(value: object) -> int | None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return None
        return value

    @classmethod
    def _non_stop_metadata(
        cls,
        *,
        question_id: str,
        choice: Mapping[str, object],
        envelope: Mapping[str, object],
    ) -> dict[str, object]:
        message = choice.get("message")
        message_map = message if isinstance(message, Mapping) else {}
        reasoning_values = [
            message_map[key]
            for key in ("reasoning", "reasoning_content")
            if key in message_map
        ]
        if not reasoning_values:
            reasoning_status = "absent"
        elif all(
            value is None or (isinstance(value, str) and not value.strip())
            for value in reasoning_values
        ):
            reasoning_status = "empty"
        else:
            reasoning_status = "nonempty_or_malformed"

        content = message_map.get("content")
        if isinstance(content, str):
            encoded = content.encode("utf-8")
            content_chars: int | None = len(content)
            content_bytes: int | None = len(encoded)
            content_sha256: str | None = hashlib.sha256(encoded).hexdigest()
        else:
            content_chars = None
            content_bytes = None
            content_sha256 = None

        usage = envelope.get("usage")
        usage_map = usage if isinstance(usage, Mapping) else {}
        details = usage_map.get("completion_tokens_details")
        details_map = details if isinstance(details, Mapping) else {}
        return {
            "question_id": question_id,
            "finish_reason": choice.get("finish_reason"),
            "prompt_tokens": cls._safe_non_negative_integer(
                usage_map.get("prompt_tokens")
            ),
            "completion_tokens": cls._safe_non_negative_integer(
                usage_map.get("completion_tokens")
            ),
            "reasoning_tokens": cls._safe_non_negative_integer(
                details_map.get("reasoning_tokens")
            ),
            "reasoning_field_status": reasoning_status,
            "content_chars": content_chars,
            "content_bytes": content_bytes,
            "content_sha256": content_sha256,
        }

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        self.last_failure_metadata = None
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
            metadata = self._non_stop_metadata(
                question_id=question_id,
                choice=choice,
                envelope=envelope,
            )
            self.last_failure_metadata = metadata
            encoded = json.dumps(
                metadata,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            raise StructureProposalError(
                "S3 provider choice did not finish with stop: "
                f"{choice.get('finish_reason')!r}; failure_metadata={encoded}"
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
                raise StructureProposalError(
                    "completion_tokens_details must be an object or null"
                )
            if "reasoning_tokens" in details:
                reasoning_tokens = self._non_negative_integer(
                    details.get("reasoning_tokens"), label="reasoning_tokens"
                )
                if reasoning_tokens != 0:
                    raise StructureProposalError(
                        "S3 reasoning-off verification failed: "
                        f"reasoning_tokens={reasoning_tokens}"
                    )
        response_id = envelope.get("id")
        if response_id is not None and not isinstance(response_id, str):
            raise StructureProposalError(
                "S3 provider response id must be a string or null"
            )

        self.provider_completions += 1
        self._call_index += 1
        return ExperimentCompletion(
            content=content,
            input_tokens=exact_count.total_input_tokens,
            output_tokens=completion_tokens,
            response_id=response_id,
        )
