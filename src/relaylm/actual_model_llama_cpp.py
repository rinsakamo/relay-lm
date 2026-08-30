from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.providers.openai_compatible_budget import SerializedInputCounterIdentity


LLAMA_CPP_CHAT_COUNTER_CAPABILITY = "llama_cpp.chat-input.serialized-input.v1"
LLAMA_CPP_CHAT_COUNTER_IMPLEMENTATION = "llama-cpp-chat-completions-input-counter"
LLAMA_CPP_CHAT_COUNTER_VERSION = "1"
LLAMA_CPP_RENDERER_METHOD = "chat-completions-input-tokens-v1"
LLAMA_CPP_FRAMING_METHOD = "same-message-shape-empty-content-v1"

_HEX_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

PostJSON = Callable[[str, Mapping[str, Any], str | None], object]


class LlamaCppRuntimeAttestationError(ValueError):
    """The observed llama.cpp server cannot prove the requested runtime identity."""


class LlamaCppInputCounterError(ValueError):
    """The llama.cpp chat input-token surface cannot prove an exact count."""


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


def attest_llama_cpp_runtime(
    *,
    props: Mapping[str, Any],
    slots: Sequence[Mapping[str, Any]],
    upstream_revision: str,
    expected_build_info: str,
    expected_model_alias: str,
    expected_model_path: str,
    artifact_sha256: str,
    context_shift_enabled: bool,
) -> LlamaCppRuntimeIdentity:
    """Bind live `/props` + `/slots` facts to an explicit expected runtime.

    This helper is intentionally host-only and non-generative. It does not
    register llama.cpp with RelayLM runtime assembly or infer capability from a
    model name. Context shift is rejected because #1992 qualification requires
    context exhaustion to fail rather than silently replace prior context.
    """

    if not isinstance(props, Mapping):
        raise TypeError("props must be a mapping")
    if not isinstance(slots, Sequence) or isinstance(slots, (str, bytes)):
        raise TypeError("slots must be a sequence of mappings")
    if not isinstance(context_shift_enabled, bool):
        raise TypeError("context_shift_enabled must be bool")
    if context_shift_enabled:
        raise LlamaCppRuntimeAttestationError(
            "llama.cpp context shift must be disabled for qualification"
        )
    if not _HEX_REVISION_RE.fullmatch(upstream_revision):
        raise LlamaCppRuntimeAttestationError(
            "llama.cpp upstream revision must be a lowercase 40-hex commit"
        )
    _require_non_empty(expected_build_info, "expected_build_info")
    _require_non_empty(expected_model_alias, "expected_model_alias")
    _require_non_empty(expected_model_path, "expected_model_path")
    if not _SHA256_RE.fullmatch(artifact_sha256):
        raise LlamaCppRuntimeAttestationError(
            "llama.cpp artifact sha256 must be a lowercase digest"
        )

    build_info = _require_string(props.get("build_info"), "props.build_info")
    if build_info != expected_build_info:
        raise LlamaCppRuntimeAttestationError(
            "llama.cpp build_info does not match expected build identity"
        )
    if upstream_revision not in build_info and upstream_revision[:7] not in build_info:
        raise LlamaCppRuntimeAttestationError(
            "llama.cpp build_info does not identify the expected upstream revision"
        )

    model_alias = _require_string(props.get("model_alias"), "props.model_alias")
    if model_alias != expected_model_alias:
        raise LlamaCppRuntimeAttestationError(
            "llama.cpp model alias does not match expected request model"
        )
    model_path = _require_string(props.get("model_path"), "props.model_path")
    if model_path != expected_model_path:
        raise LlamaCppRuntimeAttestationError(
            "llama.cpp model path does not match expected GGUF artifact"
        )
    model_ftype = _require_string(props.get("model_ftype"), "props.model_ftype")
    chat_template = _require_string(
        props.get("chat_template"),
        "props.chat_template",
    )

    settings = props.get("default_generation_settings")
    if not isinstance(settings, Mapping):
        raise LlamaCppRuntimeAttestationError(
            "llama.cpp props.default_generation_settings must be an object"
        )
    context_limit = _require_positive_int(
        settings.get("n_ctx"),
        "props.default_generation_settings.n_ctx",
    )
    total_slots = _require_positive_int(props.get("total_slots"), "props.total_slots")
    if len(slots) != total_slots:
        raise LlamaCppRuntimeAttestationError(
            "llama.cpp /slots count does not match props.total_slots"
        )

    seen_slot_ids: set[int] = set()
    for index, slot in enumerate(slots):
        if not isinstance(slot, Mapping):
            raise LlamaCppRuntimeAttestationError(
                f"llama.cpp slot[{index}] must be an object"
            )
        slot_id = slot.get("id")
        if isinstance(slot_id, bool) or not isinstance(slot_id, int) or slot_id < 0:
            raise LlamaCppRuntimeAttestationError(
                f"llama.cpp slot[{index}].id must be a non-negative integer"
            )
        if slot_id in seen_slot_ids:
            raise LlamaCppRuntimeAttestationError("llama.cpp slot IDs must be unique")
        seen_slot_ids.add(slot_id)
        slot_context = _require_positive_int(
            slot.get("n_ctx"),
            f"slots[{index}].n_ctx",
        )
        if slot_context != context_limit:
            raise LlamaCppRuntimeAttestationError(
                "llama.cpp slot context does not match props context limit"
            )

    return LlamaCppRuntimeIdentity(
        upstream_revision=upstream_revision,
        build_info=build_info,
        model_alias=model_alias,
        model_path=model_path,
        model_ftype=model_ftype,
        artifact_sha256=artifact_sha256,
        chat_template_sha256=hashlib.sha256(chat_template.encode("utf-8")).hexdigest(),
        context_limit=context_limit,
        total_slots=total_slots,
        context_shift_enabled=False,
    )


@dataclass(frozen=True, slots=True)
class LlamaCppChatInputCounter:
    """Count exact RelayLM Chat Completions input through llama.cpp itself.

    The llama.cpp `/v1/chat/completions/input_tokens` endpoint consumes the same
    Chat Completions request body shape used for generation. The counter sends
    one full request body and one body with only message contents emptied, so
    RelayLM receives both total serialized input and required framing counts.

    The helper is deliberately not registered with production runtime assembly.
    """

    base_url: str
    runtime_identity: LlamaCppRuntimeIdentity
    api_key: str | None = None
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
            "chat_template_sha256": identity.chat_template_sha256,
            "context_limit": identity.context_limit,
            "context_shift": identity.context_shift_enabled,
            "counter_transport": LLAMA_CPP_RENDERER_METHOD,
            "framing_method": LLAMA_CPP_FRAMING_METHOD,
            "model_alias": identity.model_alias,
            "model_ftype": identity.model_ftype,
            "model_path": identity.model_path,
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

    def count_input(
        self,
        model_input: Mapping[str, Any],
    ) -> SerializedInputTokenCount:
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
        }
        unknown = sorted(set(model_input) - allowed)
        if unknown:
            raise LlamaCppInputCounterError(
                "unsupported llama.cpp model-input fields for exact counting: "
                + ", ".join(unknown)
            )

        model = model_input.get("model")
        if model != self.runtime_identity.model_alias:
            raise LlamaCppInputCounterError(
                "llama.cpp model-input model does not match attested model alias"
            )
        messages = _plain_messages(model_input.get("messages"))
        payload = dict(model_input)
        payload["messages"] = messages
        return payload


def _plain_messages(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise LlamaCppInputCounterError(
            "llama.cpp model-input messages must be a non-empty list"
        )
    messages: list[dict[str, str]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise LlamaCppInputCounterError(
                f"llama.cpp message[{index}] must be an object"
            )
        unknown = sorted(set(raw) - {"role", "content"})
        if unknown:
            raise LlamaCppInputCounterError(
                f"unsupported llama.cpp message[{index}] fields: "
                + ", ".join(unknown)
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
        raise LlamaCppInputCounterError(
            "llama.cpp base_url must be a non-empty string"
        )
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise LlamaCppInputCounterError(
            "llama.cpp base_url must be an HTTP(S) URL"
        )
    if parsed.username is not None or parsed.password is not None:
        raise LlamaCppInputCounterError(
            "llama.cpp base_url must not contain credentials"
        )
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
        (
            parsed.scheme,
            parsed.netloc,
            f"{path}/chat/completions/input_tokens",
            "",
            "",
        )
    )


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


def _require_non_empty(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LlamaCppRuntimeAttestationError(f"{name} must be a non-empty string")
    return value


def _require_string(value: object, name: str) -> str:
    return _require_non_empty(value, name)


def _require_positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LlamaCppRuntimeAttestationError(f"{name} must be a positive integer")
    return value
