from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Mapping

import httpx

from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError


_LM_STUDIO_NATIVE_API = "lmstudio-native-chat-v1"
_ALLOWED_REASONING = frozenset({"off", "low", "medium", "high", "on"})


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise StructureProposalError(f"{label} must be an object")
    return value


def _require_non_negative_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise StructureProposalError(f"{label} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class LMStudioNativeTransportIdentity:
    model: str
    model_instance_id: str
    timeout_seconds: float
    reasoning: str
    max_output_tokens: int
    context_length: int
    temperature: float | None
    top_p: float | None
    store: bool = False

    def to_mapping(self) -> dict[str, object]:
        return {
            "api": _LM_STUDIO_NATIVE_API,
            "model": self.model,
            "model_instance_id": self.model_instance_id,
            "timeout_seconds": self.timeout_seconds,
            "reasoning": self.reasoning,
            "max_output_tokens": self.max_output_tokens,
            "context_length": self.context_length,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "store": self.store,
        }


class LMStudioNativeExperimentClient:
    """Bounded LM Studio native REST adapter for #2211 S2 physical smoke.

    This adapter exists because the S2 experiment needs an explicit, provider-visible
    reasoning/output contract. It intentionally does not reinterpret hidden reasoning as
    the requested answer. The declared S2 path uses ``reasoning='off'`` and requires one
    non-empty visible message in the native response.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        model_instance_id: str,
        context_length: int,
        timeout_seconds: float = 300.0,
        max_output_tokens: int = 512,
        reasoning: str = "off",
        temperature: int | float | None = None,
        top_p: int | float | None = None,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise StructureProposalError("LM Studio base_url must be non-empty")
        if not isinstance(model, str) or not model.strip():
            raise StructureProposalError("LM Studio model must be non-empty")
        if not isinstance(model_instance_id, str) or not model_instance_id.strip():
            raise StructureProposalError("LM Studio model_instance_id must be non-empty")
        if isinstance(context_length, bool) or not isinstance(context_length, int):
            raise StructureProposalError("LM Studio context_length must be an integer")
        if context_length <= 0:
            raise StructureProposalError("LM Studio context_length must be positive")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise StructureProposalError("LM Studio timeout_seconds must be numeric")
        if timeout_seconds <= 0:
            raise StructureProposalError("LM Studio timeout_seconds must be positive")
        if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int):
            raise StructureProposalError("LM Studio max_output_tokens must be an integer")
        if max_output_tokens <= 0:
            raise StructureProposalError("LM Studio max_output_tokens must be positive")
        if reasoning not in _ALLOWED_REASONING:
            raise StructureProposalError("unsupported LM Studio reasoning setting")
        if reasoning != "off":
            raise StructureProposalError(
                "#2211 S2 LM Studio native client requires reasoning='off'"
            )
        for name, value in (("temperature", temperature), ("top_p", top_p)):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
            ):
                raise StructureProposalError(f"LM Studio {name} must be numeric or null")
        if api_key is not None and not isinstance(api_key, str):
            raise TypeError("api_key must be a string or null")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.model_instance_id = model_instance_id
        self.context_length = context_length
        self.timeout_seconds = float(timeout_seconds)
        self.max_output_tokens = max_output_tokens
        self.reasoning = reasoning
        self.temperature = None if temperature is None else float(temperature)
        self.top_p = None if top_p is None else float(top_p)
        self.api_key = api_key
        self.provider_attempts = 0
        self.provider_completions = 0
        self._client = http_client or httpx.Client(timeout=self.timeout_seconds)
        self._owns_client = http_client is None

    @property
    def transport_identity(self) -> dict[str, object]:
        return LMStudioNativeTransportIdentity(
            model=self.model,
            model_instance_id=self.model_instance_id,
            timeout_seconds=self.timeout_seconds,
            reasoning=self.reasoning,
            max_output_tokens=self.max_output_tokens,
            context_length=self.context_length,
            temperature=self.temperature,
            top_p=self.top_p,
        ).to_mapping()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _normalize_messages(
        self,
        messages: tuple[dict[str, str], ...],
    ) -> tuple[str, str]:
        if len(messages) != 2:
            raise StructureProposalError(
                "#2211 LM Studio native S2 expects exactly system + user messages"
            )
        system, user = messages
        if set(system) != {"role", "content"} or set(user) != {"role", "content"}:
            raise StructureProposalError("each S2 message must contain exactly role/content")
        if system.get("role") != "system" or user.get("role") != "user":
            raise StructureProposalError(
                "#2211 LM Studio native S2 expects system then user roles"
            )
        system_content = system.get("content")
        user_content = user.get("content")
        if not isinstance(system_content, str) or not system_content.strip():
            raise StructureProposalError("S2 system content must be non-empty")
        if not isinstance(user_content, str) or not user_content.strip():
            raise StructureProposalError("S2 user content must be non-empty")
        return system_content, user_content

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        system_prompt, user_input = self._normalize_messages(messages)
        body: dict[str, object] = {
            "model": self.model,
            "input": user_input,
            "system_prompt": system_prompt,
            "stream": False,
            "reasoning": self.reasoning,
            "max_output_tokens": self.max_output_tokens,
            "context_length": self.context_length,
            "store": False,
        }
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if self.top_p is not None:
            body["top_p"] = self.top_p

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.provider_attempts += 1
        try:
            response = self._client.post(
                f"{self.base_url}/api/v1/chat",
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
            raise StructureProposalError("LM Studio native response is not valid JSON") from exc
        root = _require_mapping(envelope, label="LM Studio native response")
        observed_instance = root.get("model_instance_id")
        if observed_instance != self.model_instance_id:
            raise StructureProposalError("LM Studio response model_instance_id drifted")

        output = root.get("output")
        if not isinstance(output, list):
            raise StructureProposalError("LM Studio native output must be an array")
        messages_out: list[str] = []
        reasoning_items: list[str] = []
        for index, raw_item in enumerate(output):
            item = _require_mapping(raw_item, label=f"LM Studio output[{index}]")
            item_type = item.get("type")
            if item_type == "message":
                content = item.get("content")
                if not isinstance(content, str):
                    raise StructureProposalError("LM Studio message content must be a string")
                messages_out.append(content)
            elif item_type == "reasoning":
                content = item.get("content")
                if not isinstance(content, str):
                    raise StructureProposalError("LM Studio reasoning content must be a string")
                reasoning_items.append(content)
            else:
                raise StructureProposalError(
                    "LM Studio S2 response must not contain tools or non-message output"
                )
        if any(item.strip() for item in reasoning_items):
            raise StructureProposalError(
                "LM Studio returned reasoning content despite reasoning='off'"
            )
        if len(messages_out) != 1 or not messages_out[0].strip():
            raise StructureProposalError(
                "LM Studio S2 response must contain exactly one non-empty visible message"
            )

        stats = _require_mapping(root.get("stats"), label="LM Studio native stats")
        input_tokens = _require_non_negative_int(
            stats.get("input_tokens"), label="input_tokens"
        )
        output_tokens = _require_non_negative_int(
            stats.get("total_output_tokens"), label="total_output_tokens"
        )
        reasoning_tokens = _require_non_negative_int(
            stats.get("reasoning_output_tokens"), label="reasoning_output_tokens"
        )
        if reasoning_tokens != 0:
            raise StructureProposalError(
                "LM Studio reported reasoning tokens despite reasoning='off'"
            )
        response_id = root.get("response_id")
        if response_id is not None and (
            not isinstance(response_id, str) or not response_id.strip()
        ):
            raise StructureProposalError("LM Studio response_id must be null or non-empty")

        self.provider_completions += 1
        return ExperimentCompletion(
            content=messages_out[0],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_id=response_id,
        )
