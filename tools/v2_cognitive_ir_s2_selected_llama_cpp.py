from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import httpx

from relaylm.actual_model_llama_cpp import (
    LlamaCppRuntimeIdentity,
    attest_llama_cpp_runtime,
)
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.v2_cognitive_ir_s2_selected import (
    S2_SELECTED_EXAMPLES_VISIBLE,
    S2_SELECTED_PHYSICAL_CALLS,
    S2_SELECTED_REGIME,
    S2_SELECTED_STEP_INDEX,
    generate_selected_s2_family,
    selected_s2_preregistration,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_ir_s2_host import S2HostError, probe_s2_git_repository
from tools.v2_cognitive_ir_s2_host_v2 import S2HostV2Result, run_s2_host_smoke_v2


S2_SELECTED_LLAMA_CPP_CALL_PLAN = (
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
S2_SELECTED_LLAMA_CPP_CONTEXT_LENGTH = 8192
S2_SELECTED_LLAMA_CPP_ENDPOINT = "http://127.0.0.1:1234/v1"
S2_SELECTED_LLAMA_CPP_REASONING_EFFORT = "none"
S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS = 1800.0

_HEX_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

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


class LlamaCppThinkingOffInputCounter:
    """Exact selected-S2 accounting through llama.cpp's input-token surface.

    The full counting request preserves the exact generation body, including
    ``reasoning_effort=none``. The framing request changes only message content
    to empty strings. This experiment-local adapter intentionally does not widen
    the generic v1-era llama.cpp counter contract.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        http_client: httpx.Client,
    ) -> None:
        _require_selected_base_url(base_url)
        if not isinstance(model, str) or not model.strip():
            raise S2HostError("llama.cpp request model must be non-empty")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = http_client
        self.request_attempts = 0
        self.request_completions = 0

    @staticmethod
    def _messages(value: object) -> list[dict[str, str]]:
        if not isinstance(value, list) or not value:
            raise S2HostError("llama.cpp counted messages must be a non-empty array")
        normalized: list[dict[str, str]] = []
        for index, raw in enumerate(value):
            if not isinstance(raw, Mapping):
                raise S2HostError(f"llama.cpp counted message[{index}] must be an object")
            if set(raw) != {"role", "content"}:
                raise S2HostError(
                    f"llama.cpp counted message[{index}] must contain exactly role/content"
                )
            role = raw.get("role")
            content = raw.get("content")
            if not isinstance(role, str) or not role.strip():
                raise S2HostError(f"llama.cpp counted message[{index}].role is invalid")
            if not isinstance(content, str):
                raise S2HostError(f"llama.cpp counted message[{index}].content is invalid")
            normalized.append({"role": role, "content": content})
        return normalized

    def _validated_body(self, body: Mapping[str, object]) -> dict[str, object]:
        if not isinstance(body, Mapping):
            raise TypeError("llama.cpp counted body must be a mapping")
        allowed = {
            "model",
            "messages",
            "stream",
            "temperature",
            "top_p",
            "seed",
            "max_tokens",
            "response_format",
            "reasoning_effort",
        }
        unknown = sorted(set(body) - allowed)
        if unknown:
            raise S2HostError(
                "unsupported llama.cpp selected-S2 counted fields: " + ", ".join(unknown)
            )
        if body.get("model") != self.model:
            raise S2HostError("counted request model does not match selected-S2 transport")
        if body.get("stream") is not False:
            raise S2HostError("selected-S2 exact counting requires stream=false")
        if body.get("reasoning_effort") != S2_SELECTED_LLAMA_CPP_REASONING_EFFORT:
            raise S2HostError(
                'selected-S2 exact counting requires reasoning_effort="none"'
            )
        payload = dict(body)
        payload["messages"] = self._messages(body.get("messages"))
        return payload

    @staticmethod
    def _input_tokens(response: object) -> int:
        if not isinstance(response, Mapping):
            raise S2HostError("llama.cpp input-token response must be an object")
        value = response.get("input_tokens")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise S2HostError("llama.cpp input_tokens must be a non-negative integer")
        return value

    def _post(self, body: Mapping[str, object]) -> int:
        self.request_attempts += 1
        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions/input_tokens",
                json=dict(body),
            )
        except httpx.HTTPError as exc:
            raise S2HostError(f"llama.cpp exact input counting failed: {exc}") from exc
        if not response.is_success:
            raise S2HostError(
                f"llama.cpp exact input counting returned HTTP {response.status_code}"
            )
        try:
            payload = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise S2HostError("llama.cpp input-token response is not valid JSON") from exc
        value = self._input_tokens(payload)
        self.request_completions += 1
        return value

    def count_input(self, body: Mapping[str, object]) -> SerializedInputTokenCount:
        full = self._validated_body(body)
        messages = full["messages"]
        if not isinstance(messages, list):
            raise AssertionError("validated messages must be a list")
        framing = dict(full)
        framing["messages"] = [
            {"role": item["role"], "content": ""}
            for item in messages
        ]
        total = self._post(full)
        framing_count = self._post(framing)
        try:
            return SerializedInputTokenCount(
                total_input_tokens=total,
                required_input_framing_tokens=framing_count,
                mode=TokenCountMode.EXACT,
            )
        except (TypeError, ValueError) as exc:
            raise S2HostError(f"invalid selected-S2 exact input accounting: {exc}") from exc


class SelectedS2LlamaCppClient:
    """OpenAI-compatible selected-S2 client for one pinned llama.cpp runtime.

    Thinking is disabled by the top-level OpenAI-compatible
    ``reasoning_effort=none`` field. The pinned llama.cpp implementation is part
    of the runtime identity; response-side reasoning fields are supplementary
    fail-closed checks when the server exposes them.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS,
        max_output_tokens: int = 512,
        temperature: int | float = 0.0,
        seed: int | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        _require_selected_base_url(base_url)
        if not isinstance(model, str) or not model.strip():
            raise S2HostError("provider model must be non-empty")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise S2HostError("timeout_seconds must be numeric")
        if timeout_seconds < S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS:
            raise S2HostError(
                f"selected-S2 llama.cpp timeout must be >= {S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS:g}s"
            )
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
        self._counter = LlamaCppThinkingOffInputCounter(
            base_url=self.base_url,
            model=self.model,
            http_client=self._client,
        )

    @property
    def transport_identity(self) -> dict[str, object]:
        return {
            "api": "openai-chat-completions-selected-s2-llama-cpp-v1",
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "seed": self.seed,
            "reasoning": "off",
            "reasoning_control": "openai-top-level-reasoning_effort",
            "reasoning_effort": S2_SELECTED_LLAMA_CPP_REASONING_EFFORT,
            "reasoning_verification": (
                "explicit-request+pinned-llama.cpp-semantics;"
                "response-reasoning-fields-supplementary"
            ),
            "exact_input_accounting": (
                "chat-completions-input-tokens-full+empty-message-framing-v1"
            ),
            "structured_output_plan": {
                "form-p2": "plain_text",
                "form-p3": "plain_text",
                "form-p4": "strict_json_schema_rule",
                "probe-p0..p6": "strict_json_schema_integer_array",
            },
        }

    @property
    def input_count_attempts(self) -> int:
        return self._counter.request_attempts

    @property
    def input_count_completions(self) -> int:
        return self._counter.request_completions

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
        if self._call_index >= len(S2_SELECTED_LLAMA_CPP_CALL_PLAN):
            raise StructureProposalError("selected S2 attempted an undeclared extra provider call")
        question_id = S2_SELECTED_LLAMA_CPP_CALL_PLAN[self._call_index]
        normalized_messages = self._validate_messages(messages)

        body: dict[str, object] = {
            "model": self.model,
            "messages": normalized_messages,
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "reasoning_effort": S2_SELECTED_LLAMA_CPP_REASONING_EFFORT,
        }
        response_format = self._response_format(question_id)
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
        if prompt_tokens != exact_count.total_input_tokens:
            raise StructureProposalError(
                "provider prompt_tokens disagree with llama.cpp exact input-token accounting"
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
                        f"reasoning-off supplementary verification failed: reasoning_tokens={reasoning_tokens}"
                    )

        response_id = envelope.get("id")
        if response_id is not None and not isinstance(response_id, str):
            raise StructureProposalError("provider response id must be a string or null")

        self.provider_completions += 1
        self._call_index += 1
        return ExperimentCompletion(
            content=content,
            input_tokens=exact_count.total_input_tokens,
            output_tokens=completion_tokens,
            response_id=response_id,
        )


def _require_selected_base_url(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise S2HostError("provider base_url must be non-empty")
    normalized = base_url.rstrip("/")
    if normalized != S2_SELECTED_LLAMA_CPP_ENDPOINT:
        raise S2HostError(
            f"selected-S2 llama.cpp endpoint must be {S2_SELECTED_LLAMA_CPP_ENDPOINT}"
        )
    parsed = urlsplit(normalized)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port != 1234:
        raise S2HostError("selected-S2 llama.cpp endpoint must be loopback-only")
    return normalized


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise S2HostError(f"cannot hash selected-S2 material {path}") from exc
    return digest.hexdigest()


def _require_controller_identity(value: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise S2HostError("controller llama.cpp identity must be an object")
    required = {
        "upstream_revision",
        "build_info",
        "binary_path",
        "binary_sha256",
        "model_path",
        "artifact_sha256",
        "context_shift_enabled",
        "launch",
        "hardware",
        "capacity_evidence",
    }
    if set(value) != required:
        missing = sorted(required - set(value))
        extra = sorted(set(value) - required)
        raise S2HostError(
            f"controller llama.cpp identity shape mismatch; missing={missing}, extra={extra}"
        )
    revision = value.get("upstream_revision")
    if not isinstance(revision, str) or not _HEX_REVISION_RE.fullmatch(revision):
        raise S2HostError("controller upstream_revision must be lowercase 40-hex")
    build_info = value.get("build_info")
    if not isinstance(build_info, str) or not build_info.strip():
        raise S2HostError("controller build_info must be non-empty")
    for name in ("binary_path", "model_path"):
        item = value.get(name)
        if not isinstance(item, str) or not item.strip():
            raise S2HostError(f"controller {name} must be non-empty")
    for name in ("binary_sha256", "artifact_sha256"):
        item = value.get(name)
        if not isinstance(item, str) or not _SHA256_RE.fullmatch(item):
            raise S2HostError(f"controller {name} must be lowercase sha256")
    if value.get("context_shift_enabled") is not False:
        raise S2HostError("selected-S2 llama.cpp requires context shift disabled")
    for name in ("launch", "hardware", "capacity_evidence"):
        item = value.get(name)
        if not isinstance(item, Mapping) or not item:
            raise S2HostError(f"controller {name} must be a non-empty object")
    copied = json.loads(
        json.dumps(dict(value), ensure_ascii=False, sort_keys=True, allow_nan=False)
    )
    if not isinstance(copied, dict):
        raise AssertionError("controller identity copy is not an object")
    return copied


def _get_json(client: httpx.Client, url: str, *, label: str) -> object:
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        raise S2HostError(f"llama.cpp {label} probe failed: {exc}") from exc
    if not response.is_success:
        raise S2HostError(f"llama.cpp {label} probe returned HTTP {response.status_code}")
    try:
        return response.json()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise S2HostError(f"llama.cpp {label} response is not valid JSON") from exc


def _model_ids(value: object) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        raise S2HostError("llama.cpp /v1/models response must be an object")
    data = value.get("data")
    if not isinstance(data, list) or not data:
        raise S2HostError("llama.cpp /v1/models data must be a non-empty array")
    ids: list[str] = []
    for index, item in enumerate(data):
        if not isinstance(item, Mapping):
            raise S2HostError(f"llama.cpp model[{index}] must be an object")
        model_id = item.get("id")
        if not isinstance(model_id, str) or not model_id.strip():
            raise S2HostError(f"llama.cpp model[{index}].id must be non-empty")
        ids.append(model_id)
    return tuple(ids)


def _attestation_mapping(identity: LlamaCppRuntimeIdentity) -> dict[str, object]:
    value = asdict(identity)
    if not isinstance(value, dict):
        raise AssertionError("llama.cpp runtime attestation must serialize to an object")
    return value


def probe_llama_cpp_selected_s2_binding(
    *,
    base_url: str,
    model: str,
    controller_identity: Mapping[str, object],
    http_client: httpx.Client | None = None,
) -> dict[str, object]:
    """Host-side read-only validation of the material WSL llama.cpp binding."""

    base = _require_selected_base_url(base_url)
    controller = _require_controller_identity(controller_identity)
    client = http_client or httpx.Client(timeout=30.0)
    owns_client = http_client is None
    try:
        root = base[: -len("/v1")]
        health = _get_json(client, f"{root}/health", label="health")
        if not isinstance(health, Mapping) or health.get("status") != "ok":
            raise S2HostError("llama.cpp health status must be ok")

        models = _model_ids(_get_json(client, f"{base}/models", label="models"))
        if model not in models:
            raise S2HostError("requested model alias is absent from fresh /v1/models")

        props = _get_json(client, f"{root}/props", label="props")
        slots = _get_json(client, f"{root}/slots", label="slots")
        if not isinstance(props, Mapping):
            raise S2HostError("llama.cpp /props response must be an object")
        if not isinstance(slots, list):
            raise S2HostError("llama.cpp /slots response must be an array")

        binary_sha = _sha256_file(str(controller["binary_path"]))
        if binary_sha != controller["binary_sha256"]:
            raise S2HostError("llama.cpp binary sha256 changed after controller assembly")
        artifact_sha = _sha256_file(str(controller["model_path"]))
        if artifact_sha != controller["artifact_sha256"]:
            raise S2HostError("GGUF artifact sha256 changed after controller assembly")

        runtime = attest_llama_cpp_runtime(
            props=props,
            slots=slots,
            upstream_revision=str(controller["upstream_revision"]),
            expected_build_info=str(controller["build_info"]),
            expected_model_alias=model,
            expected_model_path=str(controller["model_path"]),
            artifact_sha256=str(controller["artifact_sha256"]),
            context_shift_enabled=bool(controller["context_shift_enabled"]),
        )
        if runtime.context_limit != S2_SELECTED_LLAMA_CPP_CONTEXT_LENGTH:
            raise S2HostError(
                f"selected-regime S2 requires context_length={S2_SELECTED_LLAMA_CPP_CONTEXT_LENGTH}"
            )
        return {
            "model": model,
            "runtime_attestation": _attestation_mapping(runtime),
        }
    finally:
        if owns_client:
            client.close()


def run_llama_cpp_selected_s2_transaction(
    *,
    base_url: str,
    model: str,
    repository_root: str | Path,
    artifact_root: str | Path,
    controller_identity: Mapping[str, object],
    api_key: str | None = None,
) -> S2HostV2Result:
    """Run one fresh selected-regime #2211 S2 transaction on WSL llama.cpp.

    This is a host entrypoint, not a controller. The caller must first assemble
    fresh controller observations under #2363. This function then revalidates
    the material llama.cpp binding before the S2 host freezes identity and
    authorizes the exact ten-call semantic protocol.
    """

    if len(S2_SELECTED_LLAMA_CPP_CALL_PLAN) != S2_SELECTED_PHYSICAL_CALLS:
        raise AssertionError("selected-S2 llama.cpp call plan diverged from preregistration")
    _require_selected_base_url(base_url)
    controller = _require_controller_identity(controller_identity)

    repository = probe_s2_git_repository(repository_root)
    if not repository.clean:
        raise S2HostError("repository checkout is dirty")

    family = generate_selected_s2_family()
    preregistration = selected_s2_preregistration()
    if preregistration.planned_provider_calls != S2_SELECTED_PHYSICAL_CALLS:
        raise AssertionError("selected-S2 preregistration call count diverged")

    client = SelectedS2LlamaCppClient(
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout_seconds=S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS,
        max_output_tokens=512,
        temperature=0.0,
        seed=None,
    )
    try:
        initial = probe_llama_cpp_selected_s2_binding(
            base_url=base_url,
            model=model,
            controller_identity=controller,
        )
        runtime_attestation = initial["runtime_attestation"]
        if not isinstance(runtime_attestation, Mapping):
            raise S2HostError("llama.cpp runtime attestation must be an object")

        identity: dict[str, object] = {
            "repository": {
                "commit": repository.commit,
                "tree": repository.tree,
                "clean_required": True,
            },
            "model": model,
            "backend": "llama.cpp-openai-compatible",
            "runtime": {
                "controller": controller,
                "attested": dict(runtime_attestation),
            },
            "runtime_attestation": dict(runtime_attestation),
            "transport": dict(client.transport_identity),
            "retry_policy": {"automatic_retry": False, "semantic_retry": False},
            "live_binding_fields": ["model", "runtime_attestation"],
            "execution_order": list(S2_SELECTED_LLAMA_CPP_CALL_PLAN),
            "selected_s2_preregistration": asdict(preregistration),
            "selected_task_regime": S2_SELECTED_REGIME,
            "claim_status": "NON_CITABLE_S2_SMOKE",
            "citable": False,
        }

        def live_binding_probe() -> dict[str, object]:
            return probe_llama_cpp_selected_s2_binding(
                base_url=base_url,
                model=model,
                controller_identity=controller,
            )

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
