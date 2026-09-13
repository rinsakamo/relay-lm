from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

from relaylm.actual_model_llama_cpp import LlamaCppInputCounterError
from relaylm.actual_model_llama_cpp_thinking import LlamaCppThinkingChatInputCounter
from relaylm.crystallization import CrystallizationInput, CrystallizationOutput
from relaylm.providers.llama_cpp_reasoning import (
    LlamaCppReasoningCapabilityAttestation,
    realize_llama_cpp_reasoning_request,
)
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    _reject_duplicate_json_members,
)
from relaylm.providers.openai_compatible_crystallization import (
    OpenAICompatibleCrystallizer,
    _request_body,
    parse_crystallization_chat_completion,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningRequest,
)
from relaylm.providers.openai_request_observation import observe_model_facing_request


LLAMA_CPP_CRYSTALLIZATION_ADAPTER_IDENTITY = (
    "relaylm.providers.LlamaCppOpenAICompatibleCrystallizer:v1"
)
LLAMA_CPP_CRYSTALLIZATION_REQUEST_TIMEOUT_SECONDS = 600.0


class LlamaCppCrystallizationProviderError(ProviderProtocolError):
    """The llama.cpp crystallization wire could not be used fail-closed."""


class LlamaCppOpenAICompatibleCrystallizer(OpenAICompatibleCrystallizer):
    """Current llama.cpp carriage for the existing off-turn crystallization core.

    The generic adapter still owns the crystallization prompt, serialization,
    native JSON-Schema, and parser. This adapter adds only the current llama.cpp
    reasoning realization and exact same-body input-token accounting.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        input_counter: LlamaCppThinkingChatInputCounter,
        llama_cpp_reasoning_capability: LlamaCppReasoningCapabilityAttestation,
        api_key: str | None = None,
        timeout: float = LLAMA_CPP_CRYSTALLIZATION_REQUEST_TIMEOUT_SECONDS,
        decoding_config: Any = None,
        decoding_capabilities: Any = None,
        http_client: httpx.AsyncClient | None = None,
        observation_root: str | Path | None = None,
    ) -> None:
        if not isinstance(input_counter, LlamaCppThinkingChatInputCounter):
            raise TypeError(
                "input_counter must be LlamaCppThinkingChatInputCounter"
            )
        if not isinstance(
            llama_cpp_reasoning_capability,
            LlamaCppReasoningCapabilityAttestation,
        ):
            raise TypeError(
                "llama_cpp_reasoning_capability must be "
                "LlamaCppReasoningCapabilityAttestation"
            )
        if input_counter.runtime_identity.model_alias != model:
            raise ValueError(
                "llama.cpp input counter model alias must match crystallizer model"
            )
        if llama_cpp_reasoning_capability.request_model != model:
            raise ValueError(
                "llama.cpp reasoning capability request_model must match crystallizer model"
            )

        super().__init__(
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout=timeout,
            decoding_config=decoding_config,
            decoding_capabilities=decoding_capabilities,
            reasoning_request=None,
            vllm_reasoning_capability=None,
            lm_studio_reasoning_capability=None,
            http_client=http_client,
        )
        self.input_counter = input_counter
        self.llama_cpp_reasoning_capability = llama_cpp_reasoning_capability
        self.observation_root = (
            Path(observation_root).resolve() if observation_root is not None else None
        )
        self.generation_request_count = 0
        self.input_counter_request_count = 0
        self.input_count_artifacts: list[Path] = []
        self.completion_artifacts: list[Path] = []

    @property
    def reasoning_realization(self) -> dict[str, object]:
        return realize_llama_cpp_reasoning_request(
            request=OpenAICompatibleReasoningRequest(mode="off"),
            capability=self.llama_cpp_reasoning_capability,
        ).to_mapping()

    async def generate(
        self, crystallization_input: CrystallizationInput
    ) -> CrystallizationOutput:
        allowed_source_ids = frozenset(
            event.id for event in crystallization_input.events
        )
        try:
            body = _request_body(
                model=self.model,
                crystallization_input=crystallization_input,
                decoding_config=self.decoding_config,
            )
            realization = realize_llama_cpp_reasoning_request(
                request=OpenAICompatibleReasoningRequest(mode="off"),
                capability=self.llama_cpp_reasoning_capability,
            )
            body.update(realization.to_request_fields())
        except (TypeError, ValueError) as exc:
            raise LlamaCppCrystallizationProviderError(
                f"cannot construct attested llama.cpp crystallization request: {exc}"
            ) from exc

        try:
            input_count = self.input_counter.count_input(body)
        except (LlamaCppInputCounterError, TypeError, ValueError) as exc:
            raise LlamaCppCrystallizationProviderError(
                f"llama.cpp exact input accounting failed: {exc}"
            ) from exc
        self.input_counter_request_count += 2
        self._record_input_count(body=body, input_count=input_count)

        # The exact object constructed above is passed to both the counter and
        # the generation transport. No second body builder or control merge is
        # allowed between those operations.
        observe_model_facing_request(body)
        self.generation_request_count += 1
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            envelope = json.loads(
                response.content,
                object_pairs_hook=_reject_duplicate_json_members,
            )
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise LlamaCppCrystallizationProviderError(
                f"upstream llama.cpp crystallization request failed: {exc}"
            ) from exc

        self._record_completion(envelope)
        return parse_crystallization_chat_completion(
            envelope,
            allowed_source_ids=allowed_source_ids,
        )

    def _record_input_count(self, *, body: Mapping[str, Any], input_count: Any) -> None:
        if self.observation_root is None:
            return
        sequence = len(self.input_count_artifacts) + 1
        path = self.observation_root / f"{sequence:04d}-crystallization-input-count.json"
        _write_json_create_once(
            path,
            {
                "format_version": 1,
                "sequence_index": sequence,
                "request_body_sha256": _body_digest(body),
                "request_controls": {
                    key: body[key]
                    for key in (
                        "model",
                        "temperature",
                        "top_p",
                        "seed",
                        "max_tokens",
                        "stream",
                        "reasoning_effort",
                        "response_format",
                    )
                    if key in body
                },
                "counter_identity": self.input_counter.evidence_identity.to_mapping(),
                "total_input_tokens": input_count.total_input_tokens,
                "required_input_framing_tokens": input_count.required_input_framing_tokens,
                "cognitive_input_tokens": input_count.cognitive_input_tokens,
                "mode": input_count.mode.value,
            },
        )
        self.input_count_artifacts.append(path)

    def _record_completion(self, envelope: Any) -> None:
        if self.observation_root is None:
            return
        sequence = len(self.completion_artifacts) + 1
        path = self.observation_root / f"{sequence:04d}-crystallization-completion.json"
        choices = envelope.get("choices") if isinstance(envelope, Mapping) else None
        choice = choices[0] if isinstance(choices, list) and choices else None
        message = choice.get("message") if isinstance(choice, Mapping) else None
        usage = envelope.get("usage") if isinstance(envelope, Mapping) else None
        details = usage.get("completion_tokens_details") if isinstance(usage, Mapping) else None
        reasoning_tokens = (
            details.get("reasoning_tokens")
            if isinstance(details, Mapping)
            else None
        )
        if not isinstance(reasoning_tokens, int) or isinstance(reasoning_tokens, bool):
            reasoning_tokens = None
        _write_json_create_once(
            path,
            {
                "format_version": 1,
                "sequence_index": sequence,
                "finish_reason": (
                    choice.get("finish_reason") if isinstance(choice, Mapping) else None
                ),
                "system_fingerprint": (
                    envelope.get("system_fingerprint")
                    if isinstance(envelope, Mapping)
                    else None
                ),
                "reasoning": {
                    "reasoning": _field_status(message, "reasoning"),
                    "reasoning_content": _field_status(message, "reasoning_content"),
                    "reasoning_tokens": reasoning_tokens,
                },
            },
        )
        self.completion_artifacts.append(path)


def _field_status(value: object, key: str) -> str:
    if not isinstance(value, Mapping) or key not in value:
        return "absent"
    item = value[key]
    if item is None:
        return "empty"
    if isinstance(item, str):
        return "empty" if not item.strip() else "nonempty"
    if isinstance(item, (list, tuple, dict, set, frozenset, bytes, bytearray)):
        return "empty" if not item else "nonempty"
    return "nonempty"


def _body_digest(body: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            dict(body),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _write_json_create_once(path: Path, value: object) -> None:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    ) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        try:
            existing = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise LlamaCppCrystallizationProviderError(
                f"cannot read existing observation artifact: {exc}"
            ) from exc
        if existing != payload:
            raise LlamaCppCrystallizationProviderError(
                f"observation artifact already exists with different content: {path}"
            )
