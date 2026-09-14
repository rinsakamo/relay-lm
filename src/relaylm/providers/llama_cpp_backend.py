"""Production-owned llama.cpp capability and exact input-count carriage.

This module is deliberately independent from ``actual_model_*`` modules.  It
describes the externally managed llama.cpp process that an installed RelayLM
runtime is configured to use; it does not start that process or perform
discovery.  Physical ``/props`` and ``/slots`` observation remains a later
qualification-owner concern.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionPassRequest,
    CognitionStructuredOutputMode,
    normalize_cognition_execution_capabilities,
    resolve_pass_request,
)
from relaylm.providers.llama_cpp_reasoning import (
    LlamaCppReasoningCapabilityAttestation,
    realize_llama_cpp_reasoning_request,
)
from relaylm.providers.openai_compatible_budget import SerializedInputCounterIdentity
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningRequest,
)
from relaylm.providers.openai_compatible_two_pass import (
    _conversation_request_body,
    _extraction_request_body,
)


LLAMA_CPP_CAPABILITY_FORMAT_VERSION = 1
LLAMA_CPP_SUPPORTED_UPSTREAM_REVISION = (
    "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
)
LLAMA_CPP_SUPPORTED_BUILD = "10874"
LLAMA_CPP_CACHE_POLICY_DISABLED = "disabled"

LLAMA_CPP_CHAT_COUNTER_CAPABILITY = "llama_cpp.chat-input.serialized-input.v1"
LLAMA_CPP_CHAT_COUNTER_IMPLEMENTATION = "llama-cpp-chat-completions-input-counter"
LLAMA_CPP_CHAT_COUNTER_VERSION = "2"
LLAMA_CPP_RENDERER_METHOD = "chat-completions-input-tokens-v1"
LLAMA_CPP_FRAMING_METHOD = "same-message-shape-empty-content-v1"

_HEX_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SUPPORTED_DECODING_CONTROLS = frozenset(
    {"temperature", "top_p", "seed", "max_output_tokens"}
)

PostJSON = Callable[[str, Mapping[str, Any], str | None], object]


class LlamaCppCapabilityError(ValueError):
    """Fail-closed error for an incomplete or mismatched llama.cpp condition."""


class LlamaCppInputCounterError(ValueError):
    """The llama.cpp input-token surface cannot prove an exact count."""


@dataclass(frozen=True, slots=True)
class LlamaCppRuntimeIdentity:
    """Content-free identity facts for one externally managed llama.cpp runtime."""

    upstream_revision: str
    build_info: str
    model_alias: str
    model_path: str
    model_ftype: str
    artifact_sha256: str
    chat_template_sha256: str
    context_limit: int
    total_slots: int
    context_shift_enabled: bool

    def __post_init__(self) -> None:
        if not _HEX_REVISION_RE.fullmatch(self.upstream_revision):
            raise ValueError("upstream_revision must be a lowercase 40-hex commit")
        for name in ("build_info", "model_alias", "model_path", "model_ftype"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        for name in ("artifact_sha256", "chat_template_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{name} must be a lowercase sha256 digest")
        for name in ("context_limit", "total_slots"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.context_shift_enabled, bool):
            raise TypeError("context_shift_enabled must be bool")
        if self.context_shift_enabled:
            raise LlamaCppCapabilityError(
                "llama.cpp context shift must be disabled for the release runtime"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "upstream_revision": self.upstream_revision,
            "build_info": self.build_info,
            "model_alias": self.model_alias,
            "model_path": self.model_path,
            "model_ftype": self.model_ftype,
            "artifact_sha256": self.artifact_sha256,
            "chat_template_sha256": self.chat_template_sha256,
            "context_limit": self.context_limit,
            "total_slots": self.total_slots,
            "context_shift_enabled": self.context_shift_enabled,
        }


@dataclass(frozen=True, slots=True)
class LlamaCppCapabilityAttestation:
    """Explicit installed-runtime capability facts for one llama.cpp condition.

    Nothing in this record is inferred from the backend spelling, model family,
    or GGUF suffix.  The configuration/physical owner supplies each fact.
    """

    runtime_identity: LlamaCppRuntimeIdentity
    reasoning_effort_none_supported: bool
    native_structured_output_supported: bool
    streaming_supported: bool
    decoding_controls: frozenset[str] = field(default_factory=frozenset)
    cache_policy: str = LLAMA_CPP_CACHE_POLICY_DISABLED
    format_version: int = LLAMA_CPP_CAPABILITY_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != LLAMA_CPP_CAPABILITY_FORMAT_VERSION:
            raise ValueError(
                f"unsupported llama.cpp capability format_version: {self.format_version}"
            )
        if not isinstance(self.runtime_identity, LlamaCppRuntimeIdentity):
            raise TypeError("runtime_identity must be LlamaCppRuntimeIdentity")
        for name in (
            "reasoning_effort_none_supported",
            "native_structured_output_supported",
            "streaming_supported",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be bool")
        if not isinstance(self.decoding_controls, frozenset):
            raise TypeError("decoding_controls must be a frozenset")
        unknown = self.decoding_controls - _SUPPORTED_DECODING_CONTROLS
        if unknown:
            raise LlamaCppCapabilityError(
                "unsupported llama.cpp decoding capability: "
                + ", ".join(sorted(unknown))
            )
        if self.cache_policy != LLAMA_CPP_CACHE_POLICY_DISABLED:
            raise LlamaCppCapabilityError(
                "the RelayLM 1.0 llama.cpp cache policy must be disabled"
            )

    @property
    def request_model(self) -> str:
        return self.runtime_identity.model_alias

    @property
    def context_shift_enabled(self) -> bool:
        return self.runtime_identity.context_shift_enabled

    @property
    def counter_capability(self) -> str:
        return LLAMA_CPP_CHAT_COUNTER_CAPABILITY

    @property
    def reasoning_capability(self) -> LlamaCppReasoningCapabilityAttestation:
        return LlamaCppReasoningCapabilityAttestation(
            request_model=self.request_model,
            enable_thinking_supported=self.reasoning_effort_none_supported,
        )

    @property
    def decoding_capabilities(self) -> OpenAICompatibleDecodingCapabilities:
        return OpenAICompatibleDecodingCapabilities(
            supported_controls=self.decoding_controls
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "backend": "llama_cpp",
            "request_model": self.request_model,
            "runtime_identity": self.runtime_identity.to_mapping(),
            "reasoning_effort_none_supported": self.reasoning_effort_none_supported,
            "native_structured_output_supported": self.native_structured_output_supported,
            "streaming_supported": self.streaming_supported,
            "decoding_controls": sorted(self.decoding_controls),
            "cache_policy": self.cache_policy,
            "context_shift": "disabled",
            "token_counter": {
                "capability": self.counter_capability,
                "mode": TokenCountMode.EXACT.value,
                "method": LLAMA_CPP_RENDERER_METHOD,
                "framing": LLAMA_CPP_FRAMING_METHOD,
            },
        }


def build_llama_cpp_capability(
    *,
    upstream_revision: str,
    build_info: str,
    model_alias: str,
    model_path: str,
    model_ftype: str,
    artifact_sha256: str,
    chat_template_sha256: str,
    context_limit: int,
    total_slots: int,
    context_shift_enabled: bool,
    reasoning_effort_none_supported: bool,
    native_structured_output_supported: bool,
    streaming_supported: bool,
    decoding_controls: frozenset[str],
    cache_policy: str,
) -> LlamaCppCapabilityAttestation:
    """Build the typed capability boundary from serializable config values."""

    return LlamaCppCapabilityAttestation(
        runtime_identity=LlamaCppRuntimeIdentity(
            upstream_revision=upstream_revision,
            build_info=build_info,
            model_alias=model_alias,
            model_path=model_path,
            model_ftype=model_ftype,
            artifact_sha256=artifact_sha256,
            chat_template_sha256=chat_template_sha256,
            context_limit=context_limit,
            total_slots=total_slots,
            context_shift_enabled=context_shift_enabled,
        ),
        reasoning_effort_none_supported=reasoning_effort_none_supported,
        native_structured_output_supported=native_structured_output_supported,
        streaming_supported=streaming_supported,
        decoding_controls=decoding_controls,
        cache_policy=cache_policy,
    )


@dataclass(frozen=True, slots=True)
class LlamaCppChatInputCounter:
    """Exact full-body plus empty-message-framing input-token counter."""

    base_url: str
    runtime_identity: LlamaCppRuntimeIdentity
    api_key: str | None = field(default=None, repr=False)
    post_json: PostJSON | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_identity, LlamaCppRuntimeIdentity):
            raise TypeError("runtime_identity must be LlamaCppRuntimeIdentity")
        if self.api_key is not None and (
            not isinstance(self.api_key, str) or not self.api_key
        ):
            raise ValueError("api_key must be a non-empty string or None")
        if self.post_json is not None and not callable(self.post_json):
            raise TypeError("post_json must be callable or None")
        _input_tokens_url(self.base_url)

    @property
    def evidence_identity(self) -> SerializedInputCounterIdentity:
        identity = self.runtime_identity
        parameters = {
            "artifact_sha256": identity.artifact_sha256,
            "backend": "llama_cpp",
            "build_info": identity.build_info,
            "cache_policy": LLAMA_CPP_CACHE_POLICY_DISABLED,
            "chat_template_sha256": identity.chat_template_sha256,
            "context_limit": identity.context_limit,
            "context_shift": identity.context_shift_enabled,
            "counter_transport": LLAMA_CPP_RENDERER_METHOD,
            "framing_method": LLAMA_CPP_FRAMING_METHOD,
            "model_alias": identity.model_alias,
            "model_ftype": identity.model_ftype,
            "model_path": identity.model_path,
            "reasoning_control": "reasoning_effort=none when requested",
            "upstream_revision": identity.upstream_revision,
        }
        return SerializedInputCounterIdentity(
            capability=LLAMA_CPP_CHAT_COUNTER_CAPABILITY,
            implementation=LLAMA_CPP_CHAT_COUNTER_IMPLEMENTATION,
            version=LLAMA_CPP_CHAT_COUNTER_VERSION,
            mode=TokenCountMode.EXACT,
            tokenizer_identity=f"gguf-sha256:{identity.artifact_sha256}",
            parameters=tuple(sorted(parameters.items())),
        )

    def count_input(self, model_input: Mapping[str, Any]) -> SerializedInputTokenCount:
        full_payload = self._validated_payload(model_input)
        framing_payload = dict(full_payload)
        framing_payload["messages"] = [
            {"role": message["role"], "content": ""}
            for message in full_payload["messages"]
        ]

        loader = self.post_json or _post_json
        url = _input_tokens_url(self.base_url)
        total = _parse_input_token_count(loader(url, full_payload, self.api_key))
        framing = _parse_input_token_count(loader(url, framing_payload, self.api_key))
        try:
            return SerializedInputTokenCount(
                total_input_tokens=total,
                required_input_framing_tokens=framing,
                mode=TokenCountMode.EXACT,
            )
        except (TypeError, ValueError) as exc:
            raise LlamaCppInputCounterError(
                f"invalid llama.cpp serialized-input accounting: {exc}"
            ) from exc

    def _validated_payload(self, model_input: Mapping[str, Any]) -> dict[str, Any]:
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
            "cache_prompt",
            "reasoning_effort",
        }
        unknown = sorted(set(model_input) - allowed)
        if unknown:
            raise LlamaCppInputCounterError(
                "unsupported llama.cpp model-input fields for exact counting: "
                + ", ".join(unknown)
            )
        if model_input.get("model") != self.runtime_identity.model_alias:
            raise LlamaCppInputCounterError(
                "llama.cpp model-input model does not match attested model alias"
            )
        if "cache_prompt" in model_input and model_input["cache_prompt"] is not False:
            raise LlamaCppInputCounterError(
                "llama.cpp exact counting requires cache_prompt=false"
            )
        if "reasoning_effort" in model_input and model_input["reasoning_effort"] != "none":
            raise LlamaCppInputCounterError(
                "llama.cpp exact counting supports only reasoning_effort=none"
            )
        payload = dict(model_input)
        payload["messages"] = _plain_messages(model_input.get("messages"))
        return payload


@dataclass(frozen=True, slots=True)
class LlamaCppTwoPassSerializedInputCounter:
    """Counter that uses the same llama.cpp request projection as generation."""

    model: str
    count_input: LlamaCppChatInputCounter
    capability: LlamaCppCapabilityAttestation
    decoding_config: OpenAICompatibleDecodingConfig

    def __post_init__(self) -> None:
        if not isinstance(self.count_input, LlamaCppChatInputCounter):
            raise TypeError("count_input must be LlamaCppChatInputCounter")
        if not isinstance(self.capability, LlamaCppCapabilityAttestation):
            raise TypeError("capability must be LlamaCppCapabilityAttestation")
        if self.model != self.capability.request_model:
            raise LlamaCppCapabilityError(
                "llama.cpp counter model does not match capability request model"
            )
        if self.count_input.runtime_identity != self.capability.runtime_identity:
            raise LlamaCppCapabilityError(
                "llama.cpp counter identity does not match capability identity"
            )
        if not isinstance(self.decoding_config, OpenAICompatibleDecodingConfig):
            raise TypeError("decoding_config must be OpenAICompatibleDecodingConfig")
        self.capability.decoding_capabilities.require(self.decoding_config)

    def count_conversation_input(
        self,
        cognitive_input: Any,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
    ) -> SerializedInputTokenCount:
        decoding, effective_reasoning = resolve_llama_cpp_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            decoding_config=self.decoding_config,
            capability=self.capability,
            streaming=False,
        )
        body = _conversation_request_body(
            model=self.model,
            cognitive_input=cognitive_input,
            stream=False,
            decoding=decoding.to_mapping(),
        )
        body.update(llama_cpp_reasoning_fields(effective_reasoning, self.capability))
        body["cache_prompt"] = False
        body.pop("stream", None)
        return self.count_input.count_input(body)

    def count_extraction_input(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
    ) -> SerializedInputTokenCount:
        decoding, effective_reasoning = resolve_llama_cpp_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            decoding_config=self.decoding_config,
            capability=self.capability,
            streaming=False,
        )
        structured = resolve_llama_cpp_structured_output_mode(
            pass_request=pass_request,
            capability=self.capability,
        )
        body = _extraction_request_body(
            model=self.model,
            extraction_input=extraction_input,
            decoding=decoding.to_mapping(),
            structured_output_mode=structured,
            lifecycle_channel_separation=True,
        )
        body.update(llama_cpp_reasoning_fields(effective_reasoning, self.capability))
        body["cache_prompt"] = False
        body.pop("stream", None)
        return self.count_input.count_input(body)


def resolve_llama_cpp_pass_request(
    *,
    pass_request: CognitionPassRequest | None,
    reasoning_request: OpenAICompatibleReasoningRequest | None,
    decoding_config: OpenAICompatibleDecodingConfig,
    capability: LlamaCppCapabilityAttestation,
    streaming: bool,
) -> tuple[OpenAICompatibleDecodingConfig, OpenAICompatibleReasoningRequest | None]:
    if streaming and not capability.streaming_supported:
        raise LlamaCppCapabilityError(
            "llama.cpp streaming is not attested for this runtime condition"
        )
    if pass_request is None:
        return decoding_config, reasoning_request
    if not isinstance(pass_request, CognitionPassRequest):
        raise TypeError("pass_request must be CognitionPassRequest or None")
    if reasoning_request is not None:
        raise ValueError(
            "pass_request and provider reasoning_request cannot both be supplied"
        )
    capabilities = normalize_cognition_execution_capabilities(
        structured_output=capability.native_structured_output_supported,
        streaming=capability.streaming_supported,
        reasoning_modes=("off",) if capability.reasoning_effort_none_supported else (),
        bounded_reasoning_budget=False,
        decoding_controls=tuple(sorted(capability.decoding_controls)),
    )
    resolve_pass_request(request=pass_request, capabilities=capabilities).require_supported()
    decoding = OpenAICompatibleDecodingConfig(
        temperature=pass_request.temperature,
        top_p=pass_request.top_p,
        seed=decoding_config.seed,
        max_output_tokens=pass_request.max_output_tokens,
    )
    capability.decoding_capabilities.require(decoding)
    if pass_request.reasoning_mode is None:
        return decoding, None
    return decoding, OpenAICompatibleReasoningRequest(
        mode=pass_request.reasoning_mode.value,
        token_budget=pass_request.reasoning_budget,
    )


def resolve_llama_cpp_structured_output_mode(
    *,
    pass_request: CognitionPassRequest | None,
    capability: LlamaCppCapabilityAttestation,
) -> CognitionStructuredOutputMode:
    requested = None if pass_request is None else pass_request.structured_output_mode
    if requested is None or requested is CognitionStructuredOutputMode.PLAIN:
        return CognitionStructuredOutputMode.PLAIN
    if requested is CognitionStructuredOutputMode.AUTO:
        return (
            CognitionStructuredOutputMode.NATIVE
            if capability.native_structured_output_supported
            else CognitionStructuredOutputMode.PLAIN
        )
    if requested is CognitionStructuredOutputMode.NATIVE:
        if not capability.native_structured_output_supported:
            raise LlamaCppCapabilityError(
                "native llama.cpp structured output is not attested"
            )
        return requested
    raise TypeError("unsupported structured output mode")


def llama_cpp_reasoning_fields(
    request: OpenAICompatibleReasoningRequest | None,
    capability: LlamaCppCapabilityAttestation,
) -> dict[str, object]:
    if request is None:
        return {}
    return realize_llama_cpp_reasoning_request(
        request=request,
        capability=capability.reasoning_capability,
    ).to_request_fields()


def _plain_messages(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise LlamaCppInputCounterError(
            "llama.cpp model-input messages must be a non-empty list"
        )
    messages: list[dict[str, str]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise LlamaCppInputCounterError(f"llama.cpp message[{index}] must be an object")
        unknown = sorted(set(raw) - {"role", "content"})
        if unknown:
            raise LlamaCppInputCounterError(
                f"unsupported llama.cpp message[{index}] fields: " + ", ".join(unknown)
            )
        role = raw.get("role")
        content = raw.get("content")
        if not isinstance(role, str) or not role.strip():
            raise LlamaCppInputCounterError(
                f"llama.cpp message[{index}].role must be a non-empty string"
            )
        if not isinstance(content, str):
            raise LlamaCppInputCounterError(
                f"llama.cpp message[{index}].content must be a string"
            )
        messages.append({"role": role, "content": content})
    return messages


def _parse_input_token_count(response: object) -> int:
    if not isinstance(response, Mapping):
        raise LlamaCppInputCounterError(
            "llama.cpp input-token response must be an object"
        )
    count = response.get("input_tokens")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise LlamaCppInputCounterError(
            "llama.cpp input_tokens must be a non-negative integer"
        )
    return count


def _input_tokens_url(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise LlamaCppInputCounterError("llama.cpp base_url must be a non-empty string")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise LlamaCppInputCounterError("llama.cpp base_url must be an HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise LlamaCppInputCounterError("llama.cpp base_url must not contain credentials")
    if parsed.query or parsed.fragment:
        raise LlamaCppInputCounterError(
            "llama.cpp base_url must not contain query or fragment"
        )
    path = parsed.path.rstrip("/")
    if not path.endswith("/v1"):
        raise LlamaCppInputCounterError(
            "llama.cpp base_url must end in /v1 for Chat Completions"
        )
    return urlunsplit(
        (parsed.scheme, parsed.netloc, f"{path}/chat/completions/input_tokens", "", "")
    )


def _post_json(url: str, payload: Mapping[str, Any], api_key: str | None) -> object:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key is not None:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        url,
        data=json.dumps(
            dict(payload), ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
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
