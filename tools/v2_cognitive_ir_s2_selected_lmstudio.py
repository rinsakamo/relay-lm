from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
import json
from pathlib import Path

import httpx

from relaylm.v2_cognitive_ir_s2_selected import (
    S2_SELECTED_EXAMPLES_VISIBLE,
    S2_SELECTED_PHYSICAL_CALLS,
    S2_SELECTED_REGIME,
    S2_SELECTED_STEP_INDEX,
    generate_selected_s2_family,
    selected_s2_preregistration,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_ir_calibration_host import (
    CalibrationHostError,
    probe_lmstudio_native_calibration_binding,
)
from tools.v2_cognitive_ir_s2_host import S2HostError, probe_s2_git_repository
from tools.v2_cognitive_ir_s2_host_v2 import S2HostV2Result, run_s2_host_smoke_v2


_S2_CALL_PLAN = (
    "form-p2",
    "form-p3",
    "form-p4",
    "probe-p0",
    "probe-p1",
    "probe-p2",
    "probe-p3",
    "probe-p4",
    "probe-p5",
    "probe-p6",
)
_REASONING_VERIFICATION = "usage.completion_tokens_details.reasoning_tokens==0"
_SELECTED_MODEL = "google/gemma-4-12b"
_SELECTED_CONTEXT_LENGTH = 8192
_SELECTED_RUNTIME = {
    "architecture": "Gemma4",
    "format": "GGUF",
    "quantization": "Q4_K_M",
    "selected_variant": "google/gemma-4-12b@q4_k_m",
}

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

_TARGET_SCHEMA: dict[str, object] = {
    "type": "array",
    "items": {"type": "integer", "minimum": 0, "maximum": 9},
    "minItems": 4,
    "maxItems": 4,
}


class SelectedS2OpenAIClient:
    """Fail-closed OpenAI-compatible client for the selected #2211 S2 family.

    P2/P3 remain ordinary text formation calls. The machine-readable P4 rule and all
    seven target answers use strict JSON Schema response_format. Every successful
    completion must independently demonstrate effective reasoning-off execution.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 300.0,
        max_output_tokens: int = 512,
        temperature: int | float = 0.0,
        seed: int | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise S2HostError("provider base_url must be non-empty")
        if not isinstance(model, str) or not model.strip():
            raise S2HostError("provider model must be non-empty")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise S2HostError("timeout_seconds must be numeric")
        if timeout_seconds <= 0:
            raise S2HostError("timeout_seconds must be positive")
        if (
            isinstance(max_output_tokens, bool)
            or not isinstance(max_output_tokens, int)
            or max_output_tokens <= 0
        ):
            raise S2HostError("max_output_tokens must be a positive integer")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            raise S2HostError("temperature must be numeric")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise S2HostError("seed must be an integer or null")
        if api_key is not None and not isinstance(api_key, str):
            raise TypeError("api_key must be a string or null")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = float(timeout_seconds)
        self.max_output_tokens = max_output_tokens
        self.temperature = float(temperature)
        self.seed = seed
        self.provider_attempts = 0
        self.provider_completions = 0
        self._call_index = 0
        self._client = http_client or httpx.Client(timeout=self.timeout_seconds)
        self._owns_client = http_client is None

    @property
    def transport_identity(self) -> dict[str, object]:
        return {
            "api": "openai-chat-completions-selected-s2-v1",
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "seed": self.seed,
            "reasoning": "off",
            "reasoning_verification": _REASONING_VERIFICATION,
            "structured_output_plan": {
                "form-p2": "plain_text",
                "form-p3": "plain_text",
                "form-p4": "strict_json_schema_rule",
                "probe-p0..p6": "strict_json_schema_integer_array",
            },
        }

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @staticmethod
    def _validate_messages(messages: tuple[dict[str, str], ...]) -> list[dict[str, str]]:
        if not messages:
            raise S2HostError("messages must not be empty")
        normalized: list[dict[str, str]] = []
        for message in messages:
            if set(message) != {"role", "content"}:
                raise S2HostError("each message must contain exactly role/content")
            role = message["role"]
            content = message["content"]
            if role not in {"system", "user", "assistant"}:
                raise S2HostError("unsupported message role")
            if not isinstance(content, str) or not content:
                raise S2HostError("message content must be non-empty")
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
    def _response_format(question_id: str) -> dict[str, object] | None:
        if question_id in {"form-p2", "form-p3"}:
            return None
        if question_id == "form-p4":
            name = "relaylm2_s2_reusable_rule"
            schema = _RULE_SCHEMA
        elif question_id.startswith("probe-p"):
            name = "relaylm2_s2_target_vector"
            schema = _TARGET_SCHEMA
        else:
            raise S2HostError(f"unexpected S2 question id: {question_id}")
        return {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": True,
                "schema": schema,
            },
        }

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        if self._call_index >= len(_S2_CALL_PLAN):
            raise StructureProposalError("selected S2 attempted an undeclared extra provider call")
        question_id = _S2_CALL_PLAN[self._call_index]
        normalized_messages = self._validate_messages(messages)

        body: dict[str, object] = {
            "model": self.model,
            "messages": normalized_messages,
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
        }
        response_format = self._response_format(question_id)
        if response_format is not None:
            body["response_format"] = response_format
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
            raise StructureProposalError(
                "reasoning-off response exposed non-empty reasoning content"
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise StructureProposalError("provider message content must be non-empty")

        usage = envelope.get("usage")
        if not isinstance(usage, Mapping):
            raise StructureProposalError("provider usage must be an object")
        prompt_tokens = self._non_negative_integer(
            usage.get("prompt_tokens"), label="prompt_tokens"
        )
        completion_tokens = self._non_negative_integer(
            usage.get("completion_tokens"), label="completion_tokens"
        )
        details = usage.get("completion_tokens_details")
        if not isinstance(details, Mapping):
            raise StructureProposalError(
                "reasoning-off verification requires completion_tokens_details"
            )
        reasoning_tokens = self._non_negative_integer(
            details.get("reasoning_tokens"), label="reasoning_tokens"
        )
        if reasoning_tokens != 0:
            raise StructureProposalError(
                f"reasoning-off verification failed: reasoning_tokens={reasoning_tokens}"
            )

        response_id = envelope.get("id")
        if response_id is not None and not isinstance(response_id, str):
            raise StructureProposalError("provider response id must be a string or null")

        self.provider_completions += 1
        self._call_index += 1
        return ExperimentCompletion(
            content=content,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            response_id=response_id,
        )


def _probe_binding(*, base_url: str, model: str, api_key: str | None) -> dict[str, object]:
    try:
        return probe_lmstudio_native_calibration_binding(
            base_url=base_url,
            model=model,
            api_key=api_key,
        )
    except CalibrationHostError as exc:
        raise S2HostError(str(exc)) from exc


def _validate_selected_physical_condition(binding: Mapping[str, object], *, model: str) -> None:
    if model != _SELECTED_MODEL:
        raise S2HostError(
            f"selected-regime S2 is frozen to model {_SELECTED_MODEL!r}"
        )
    if binding.get("model") != _SELECTED_MODEL:
        raise S2HostError("native loaded-model binding does not match selected S2 model")
    if binding.get("context_length") != _SELECTED_CONTEXT_LENGTH:
        raise S2HostError(
            f"selected-regime S2 requires context_length={_SELECTED_CONTEXT_LENGTH}"
        )
    runtime = binding.get("runtime")
    if not isinstance(runtime, Mapping):
        raise S2HostError("native runtime binding must be an object")
    for key, expected in _SELECTED_RUNTIME.items():
        if runtime.get(key) != expected:
            raise S2HostError(
                f"selected-regime S2 runtime mismatch: {key}={runtime.get(key)!r}"
            )


def run_lmstudio_selected_s2_transaction(
    *,
    base_url: str,
    model: str,
    repository_root: str | Path,
    artifact_root: str | Path,
    api_key: str | None = None,
) -> S2HostV2Result:
    """Run the canonical selected-regime #2211 S2 transaction from fresh authority."""

    repository = probe_s2_git_repository(repository_root)
    if not repository.clean:
        raise S2HostError("repository checkout is dirty")

    family = generate_selected_s2_family()
    prereg = selected_s2_preregistration()
    if prereg.planned_provider_calls != len(_S2_CALL_PLAN) != S2_SELECTED_PHYSICAL_CALLS:
        raise AssertionError("selected S2 call-plan constants diverged")

    client = SelectedS2OpenAIClient(
        base_url=f"{base_url.rstrip('/')}/v1",
        model=model,
        api_key=api_key,
        timeout_seconds=300.0,
        max_output_tokens=512,
        temperature=0.0,
        seed=None,
    )
    try:
        binding = _probe_binding(base_url=base_url, model=model, api_key=api_key)
        _validate_selected_physical_condition(binding, model=model)
        transport = dict(client.transport_identity)
        if transport.get("model") != binding.get("model"):
            raise S2HostError(
                "OpenAI-compatible transport model does not match native loaded-model binding"
            )

        identity: dict[str, object] = {
            "repository": {
                "commit": repository.commit,
                "tree": repository.tree,
                "clean_required": True,
            },
            **binding,
            "backend": "lmstudio-openai-compatible",
            "transport": transport,
            "retry_policy": {"automatic_retry": False, "semantic_retry": False},
            "live_binding_fields": [
                "model",
                "model_instance_id",
                "context_length",
                "runtime",
            ],
            "execution_order": list(_S2_CALL_PLAN),
            "selected_s2_preregistration": asdict(prereg),
            "selected_task_regime": S2_SELECTED_REGIME,
        }

        def live_binding_probe() -> dict[str, object]:
            observed = _probe_binding(base_url=base_url, model=model, api_key=api_key)
            _validate_selected_physical_condition(observed, model=model)
            return observed

        return run_s2_host_smoke_v2(
            artifact_root=artifact_root,
            identity=identity,
            repository_root=repository_root,
            live_binding_probe=live_binding_probe,
            client=client,
            family=family,
            step_index=S2_SELECTED_STEP_INDEX,
            examples_visible=S2_SELECTED_EXAMPLES_VISIBLE,
        )
    finally:
        client.close()


__all__ = [
    "SelectedS2OpenAIClient",
    "run_lmstudio_selected_s2_transaction",
]
