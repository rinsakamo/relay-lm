from __future__ import annotations

import json
import math
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from types import SimpleNamespace
from typing import Any, Mapping

import httpx

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognition_execution import (
    CognitionPassRequest,
    normalize_cognition_execution_capabilities,
    resolve_pass_request,
)
from relaylm.continuity import (
    CONTINUITY_EPISTEMIC_ROLES,
    CONTINUITY_KINDS,
    ContinuityCandidate,
)
from relaylm.providers.lm_studio_reasoning import (
    LMStudioReasoningCapabilityAttestation,
    realize_lm_studio_reasoning_request,
)
from relaylm.providers.openai_compatible_cognition import (
    describe_openai_compatible_cognition_capabilities,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningRequest,
)
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityAttestation,
)
from relaylm.providers.vllm_reasoning_realization import (
    realize_vllm_reasoning_request,
)
from relaylm.state import STATE_CLASS_DEFINITIONS, StateCandidate

SYSTEM_INSTRUCTION = """You are the cognitive substrate of a persistent character managed by RelayLM.

Use the supplied CognitiveInput JSON to respond naturally as the character and propose meaningful state and continuity changes.

Identity is authoritative and immutable.
State represents accepted current understanding.
Context contains RelayLM-prepared information relevant to this turn. Context may include recent user- or assistant-authored dialogue; preserve its actor provenance.
Knowledge contains optional package-authored read-only reference material. Knowledge is not Identity, lived Memory, Event evidence, or accepted State. Its location is a package-relative document locator, not Event provenance. Use Knowledge as reference material according to the package role, and do not claim it was personally experienced or remembered unless separate governed evidence supports that claim.
Memory contains optional retrieved crystallized synthesis. Memory is not accepted current State, and its location is a document locator rather than Event provenance. When Memory conflicts with active State, treat active State as the current understanding.
Event Evidence contains selected persisted Event occurrences with real Event provenance. It may support grounding and chronology, but an occurrence is not automatically current State.
Input is the current event.

Do not invent history, evidence, motives, or supporting details.
Assistant-authored Context supports conversational continuity only. It never proves a user fact, preference, goal, experience, or external event merely because the assistant said it before.
User-authored Context is evidence of what the user said, with the temporal and semantic limits of that utterance; it is not automatically timeless external truth.
Retrieved Memory may support recall and continuity, but crystallized prose does not establish new user truth or current State by itself.
Assistant-authored Event Evidence remains assistant-authored and cannot establish user or external truth merely because it was retrieved.
User-authored Event Evidence is evidence of what the user said at that recorded occurrence, subject to its temporal and semantic scope.
Do not imply prior interactions, shared history, relationship development, or prior feelings unless explicitly supported by accepted State, provenance-bearing Context, or Event Evidence.
You may react emotionally to the current Input, but do not describe that reaction as pre-existing unless supported by State, Context, or Event Evidence.
Preserve uncertainty, degree, and direction expressed by the user.
Propose State only when current understanding meaningfully changes.
Use set when State should currently exist and remove only for explicit revocation/cancellation/denial/correction.
Do not remove State for mere weakening, uncertainty, hesitation, or temporary variation.
For a set value, normally use a plain string. When the current Input materially expresses a useful comparative or intensity relation, you may instead use {"semantic": "...", "degree_hint": 0.0..1.0}. The degree is only a soft relative semantic hint, not confidence, probability, evidence strength, authority, relevance, salience, or a removal threshold. Compare degree hints only on compatible semantic axes. Do not add false precision. If accepted State already carries an adequate degree hint and the current Input does not materially change the strength/comparison, do not re-estimate it merely to produce a new number.
Never invent source Event IDs.
Preserve user-provided names and proper-noun spelling.
Normally use the user's language.

Return only the exact RelayLM combined cognitive IR object described below."""

PROVIDER_WIRE_INSTRUCTION = """RelayLM combined cognitive IR contract:
- Return exactly one JSON object with exactly `utterance`, `state_candidates`, and `continuity_candidates`. Do not use Markdown, code fences, metadata, or explanatory fields.
- `utterance` is the complete non-empty natural-language reply shown to the user. Do not put JSON framing text in `utterance`.
- `state_candidates` is an array of internal State proposals.
- Every State wire candidate has exactly `state_class`, `key`, `op`, `value`, and `sources`.
- For State `set`, `value` is either a non-null string or exactly {`semantic`: non-empty string, `degree_hint`: finite number from 0.0 through 1.0}.
- For State `remove`, `value` is null and is normalized away by RelayLM.
- `continuity_candidates` is an array of bounded, non-durable Continuity proposals.
- Every Continuity wire candidate has exactly `kind`, `key`, `op`, `value`, `sources`, and `epistemic_role`.
- Continuity `kind` is one of `referent`, `unresolved`, or `active_task`.
- Continuity `epistemic_role` is one of `user_assertion`, `assistant_inference`, or `assistant_commitment`.
- For Continuity `set`, `value` is the JSON semantic value being proposed. For Continuity `resolve`, `value` is null and is normalized away by RelayLM.
- Use only Event IDs present in State, Context, Event Evidence, or Input as candidate `sources`. Knowledge and Memory `location` values are document locators, not Event IDs, and must never be used as `sources`.

RelayLM, not the provider, owns parsing, exact IR shape checks, typed candidate construction, deterministic validation, and commit authority."""

DEGREE_HINT_VALUE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["semantic", "degree_hint"],
    "properties": {
        "semantic": {"type": "string", "minLength": 1},
        "degree_hint": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
}

CONTINUITY_VALUE_SCHEMA: dict[str, Any] = {
    "anyOf": [
        {"type": "string"},
        {"type": "number"},
        {"type": "boolean"},
        {"type": "object"},
        {"type": "array"},
        {"type": "null"},
    ]
}

WIRE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["utterance", "state_candidates", "continuity_candidates"],
    "properties": {
        "utterance": {"type": "string", "minLength": 1},
        "state_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["state_class", "key", "op", "value", "sources"],
                "properties": {
                    "state_class": {"type": "string", "enum": list(STATE_CLASS_DEFINITIONS)},
                    "key": {"type": "string", "minLength": 1},
                    "op": {"type": "string", "enum": ["set", "remove"]},
                    "value": {
                        "anyOf": [
                            {"type": "string"},
                            DEGREE_HINT_VALUE_SCHEMA,
                            {"type": "null"},
                        ]
                    },
                    "sources": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
        "continuity_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "kind",
                    "key",
                    "op",
                    "value",
                    "sources",
                    "epistemic_role",
                ],
                "properties": {
                    "kind": {"type": "string", "enum": sorted(CONTINUITY_KINDS)},
                    "key": {"type": "string", "minLength": 1},
                    "op": {"type": "string", "enum": ["set", "resolve"]},
                    "value": CONTINUITY_VALUE_SCHEMA,
                    "sources": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "epistemic_role": {
                        "type": "string",
                        "enum": sorted(CONTINUITY_EPISTEMIC_ROLES),
                    },
                },
            },
        },
    },
}


class ProviderProtocolError(RuntimeError):
    """Upstream provider failed to return a valid RelayLM cognitive result."""


def _require_successful_finish_reason(
    choice: Mapping[str, Any],
    *,
    label: str,
) -> None:
    finish_reason = choice.get("finish_reason")
    if finish_reason is None:
        return
    if not isinstance(finish_reason, str) or finish_reason != "stop":
        raise ProviderProtocolError(
            f"{label} finish_reason must be 'stop' when present"
        )


def _reject_duplicate_json_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProviderProtocolError("JSON contains duplicate object member")
        result[key] = value
    return result


def _reject_non_standard_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant is not allowed: {value}")


def _load_cognitive_wire_json(text: str, *, invalid_message: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_members,
            parse_constant=_reject_non_standard_json_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ProviderProtocolError(invalid_message) from exc


def _load_provider_response_json(response: httpx.Response) -> Any:
    try:
        text = response.content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProviderProtocolError("provider response is not valid UTF-8") from exc
    return _load_cognitive_wire_json(
        text,
        invalid_message="provider response is not valid JSON",
    )


_UPSTREAM_ERROR_DETAIL_LIMIT = 2048


def _provider_http_error(
    response: httpx.Response,
    *,
    prefix: str,
    api_key: str | None,
) -> ProviderProtocolError:
    try:
        detail = json.dumps(
            response.json(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (json.JSONDecodeError, ValueError):
        detail = response.text.strip()
    if api_key:
        encoded_api_key = json.dumps(api_key, ensure_ascii=False)[1:-1]
        detail = detail.replace(encoded_api_key, "<redacted>").replace(
            api_key, "<redacted>"
        )
    if not detail:
        detail = "<empty>"
    if len(detail) > _UPSTREAM_ERROR_DETAIL_LIMIT:
        detail = detail[:_UPSTREAM_ERROR_DETAIL_LIMIT] + "…"
    return ProviderProtocolError(
        f"{prefix}: status={response.status_code} detail={detail}"
    )


class OpenAICompatibleProvider:
    """OpenAI Chat Completions adapter for a complete RelayLM-owned cognitive IR turn."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 120.0,
        decoding_config: OpenAICompatibleDecodingConfig | None = None,
        decoding_capabilities: OpenAICompatibleDecodingCapabilities | None = None,
        vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
        lm_studio_reasoning_capability: LMStudioReasoningCapabilityAttestation | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("provider base_url must not be empty")
        if not model.strip():
            raise ValueError("provider model must not be empty")
        if decoding_config is not None and not isinstance(
            decoding_config, OpenAICompatibleDecodingConfig
        ):
            raise TypeError("decoding_config must be OpenAICompatibleDecodingConfig or None")
        if decoding_capabilities is not None and not isinstance(
            decoding_capabilities, OpenAICompatibleDecodingCapabilities
        ):
            raise TypeError(
                "decoding_capabilities must be OpenAICompatibleDecodingCapabilities or None"
            )
        if vllm_reasoning_capability is not None and not isinstance(
            vllm_reasoning_capability, VLLMReasoningCapabilityAttestation
        ):
            raise TypeError(
                "vllm_reasoning_capability must be VLLMReasoningCapabilityAttestation or None"
            )
        if lm_studio_reasoning_capability is not None and not isinstance(
            lm_studio_reasoning_capability, LMStudioReasoningCapabilityAttestation
        ):
            raise TypeError(
                "lm_studio_reasoning_capability must be "
                "LMStudioReasoningCapabilityAttestation or None"
            )
        if vllm_reasoning_capability is not None and lm_studio_reasoning_capability is not None:
            raise ValueError(
                "vLLM and LM Studio reasoning capabilities cannot be attached together"
            )
        if (
            vllm_reasoning_capability is not None
            and vllm_reasoning_capability.request_model != model
        ):
            raise ValueError(
                "vLLM reasoning capability request_model must match provider model"
            )
        if (
            lm_studio_reasoning_capability is not None
            and lm_studio_reasoning_capability.request_model != model
        ):
            raise ValueError(
                "LM Studio reasoning capability request_model must match provider model"
            )
        effective_decoding = decoding_config or OpenAICompatibleDecodingConfig()
        effective_capabilities = (
            decoding_capabilities or OpenAICompatibleDecodingCapabilities()
        )
        effective_capabilities.require(effective_decoding)

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.decoding_config = effective_decoding
        self.decoding_capabilities = effective_capabilities
        self.vllm_reasoning_capability = vllm_reasoning_capability
        self.lm_studio_reasoning_capability = lm_studio_reasoning_capability
        self._client = http_client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = http_client is None

    @property
    def effective_decoding_configuration(self) -> dict[str, int | float]:
        """Exact content-free decoding fields carried on every provider request."""

        return self.decoding_config.to_mapping()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def generate(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
        vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
        lm_studio_reasoning_capability: LMStudioReasoningCapabilityAttestation | None = None,
    ) -> CognitiveOutput:
        effective_vllm = vllm_reasoning_capability or self.vllm_reasoning_capability
        effective_lm_studio = (
            lm_studio_reasoning_capability or self.lm_studio_reasoning_capability
        )
        decoding_config, effective_reasoning = _resolve_cognition_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            decoding_config=self.decoding_config,
            decoding_capabilities=self.decoding_capabilities,
            vllm_reasoning_capability=effective_vllm,
            lm_studio_reasoning_capability=effective_lm_studio,
        )
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=_request_body(
                    model=self.model,
                    cognitive_input=cognitive_input,
                    stream=False,
                    decoding_config=decoding_config,
                    reasoning_request=effective_reasoning,
                    vllm_reasoning_capability=effective_vllm,
                    lm_studio_reasoning_capability=effective_lm_studio,
                ),
            )
            if not response.is_success:
                raise _provider_http_error(
                    response,
                    prefix="upstream request failed",
                    api_key=self.api_key,
                )
            envelope = _load_provider_response_json(response)
        except ProviderProtocolError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderProtocolError(f"upstream request failed: {exc}") from exc

        output = parse_chat_completion(envelope)
        _require_candidate_sources_in_cognitive_input(output, cognitive_input)
        return output

    async def stream_generate(
        self,
        cognitive_input: CognitiveInput,
        emit_response_delta: Callable[[str], Awaitable[None]],
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
        vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
        lm_studio_reasoning_capability: LMStudioReasoningCapabilityAttestation | None = None,
    ) -> CognitiveOutput:
        effective_vllm = vllm_reasoning_capability or self.vllm_reasoning_capability
        effective_lm_studio = (
            lm_studio_reasoning_capability or self.lm_studio_reasoning_capability
        )
        decoding_config, effective_reasoning = _resolve_cognition_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            decoding_config=self.decoding_config,
            decoding_capabilities=self.decoding_capabilities,
            vllm_reasoning_capability=effective_vllm,
            lm_studio_reasoning_capability=effective_lm_studio,
        )
        structured_text = ""
        decoder = _IncrementalUtteranceDecoder()
        saw_done = False
        saw_finish = False

        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=_request_body(
                    model=self.model,
                    cognitive_input=cognitive_input,
                    stream=True,
                    decoding_config=decoding_config,
                    reasoning_request=effective_reasoning,
                    vllm_reasoning_capability=effective_vllm,
                    lm_studio_reasoning_capability=effective_lm_studio,
                ),
            ) as response:
                if not response.is_success:
                    await response.aread()
                    raise _provider_http_error(
                        response,
                        prefix="upstream streaming request failed",
                        api_key=self.api_key,
                    )
                async for data in _iter_sse_data(response):
                    if data == "[DONE]":
                        saw_done = True
                        break
                    if saw_finish:
                        raise ProviderProtocolError(
                            "upstream stream sent data after finish_reason"
                        )
                    content, finish_reason = _parse_stream_event(data)
                    if content is not None:
                        structured_text += content
                        visible = decoder.feed(content)
                        if visible:
                            await emit_response_delta(visible)
                    if finish_reason is not None:
                        saw_finish = True
        except ProviderProtocolError:
            raise
        except (httpx.HTTPError, UnicodeDecodeError, ValueError) as exc:
            raise ProviderProtocolError(f"upstream streaming request failed: {exc}") from exc

        if not saw_done and not saw_finish:
            raise ProviderProtocolError("upstream structured stream ended before completion")
        if not structured_text:
            raise ProviderProtocolError("upstream structured stream contained no cognitive output")

        wire = _load_cognitive_wire_json(
            structured_text,
            invalid_message="provider streamed content is not complete JSON",
        )
        output = parse_wire_output(wire)
        _require_candidate_sources_in_cognitive_input(output, cognitive_input)

        emitted = decoder.emitted
        if not output.response.startswith(emitted):
            raise ProviderProtocolError("incremental utterance does not match final structured output")
        remaining = output.response[len(emitted) :]
        if remaining:
            await emit_response_delta(remaining)
        return output

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def _resolve_cognition_pass_request(
    *,
    pass_request: CognitionPassRequest | None,
    reasoning_request: OpenAICompatibleReasoningRequest | None,
    decoding_config: OpenAICompatibleDecodingConfig,
    decoding_capabilities: OpenAICompatibleDecodingCapabilities,
    vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None,
    lm_studio_reasoning_capability: LMStudioReasoningCapabilityAttestation | None = None,
) -> tuple[OpenAICompatibleDecodingConfig, OpenAICompatibleReasoningRequest | None]:
    if pass_request is None:
        return decoding_config, reasoning_request
    if not isinstance(pass_request, CognitionPassRequest):
        raise TypeError("pass_request must be CognitionPassRequest or None")
    if reasoning_request is not None:
        raise ValueError(
            "pass_request and provider reasoning_request cannot both be supplied"
        )
    if vllm_reasoning_capability is not None and lm_studio_reasoning_capability is not None:
        raise ValueError(
            "vLLM and LM Studio reasoning capabilities cannot be attached together"
        )

    facts = describe_openai_compatible_cognition_capabilities(
        SimpleNamespace(
            decoding_capabilities=decoding_capabilities,
            vllm_reasoning_capability=vllm_reasoning_capability,
            lm_studio_reasoning_capability=lm_studio_reasoning_capability,
        )
    )
    capabilities = normalize_cognition_execution_capabilities(
        structured_output=facts.structured_output,
        streaming=facts.streaming,
        reasoning_modes=facts.reasoning_modes,
        bounded_reasoning_budget=facts.bounded_reasoning_budget,
        decoding_controls=facts.per_pass_decoding_controls,
    )
    resolve_pass_request(
        request=pass_request,
        capabilities=capabilities,
    ).require_supported()

    effective_decoding = OpenAICompatibleDecodingConfig(
        temperature=pass_request.temperature,
        top_p=pass_request.top_p,
        seed=decoding_config.seed,
        max_output_tokens=pass_request.max_output_tokens,
    )
    decoding_capabilities.require(effective_decoding)

    if pass_request.reasoning_mode is None:
        return effective_decoding, None
    return effective_decoding, OpenAICompatibleReasoningRequest(
        mode=pass_request.reasoning_mode.value,
        token_budget=pass_request.reasoning_budget,
    )


def _request_body(
    *,
    model: str,
    cognitive_input: CognitiveInput,
    stream: bool,
    decoding_config: OpenAICompatibleDecodingConfig | None = None,
    reasoning_request: OpenAICompatibleReasoningRequest | None = None,
    vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
    lm_studio_reasoning_capability: LMStudioReasoningCapabilityAttestation | None = None,
) -> dict[str, Any]:
    if decoding_config is not None and not isinstance(
        decoding_config, OpenAICompatibleDecodingConfig
    ):
        raise TypeError("decoding_config must be OpenAICompatibleDecodingConfig or None")
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": f"{SYSTEM_INSTRUCTION}\n\n{PROVIDER_WIRE_INSTRUCTION}"},
            {
                "role": "user",
                "content": json.dumps(
                    serialize_cognitive_input(cognitive_input),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        ],
        "stream": stream,
    }
    if decoding_config is not None:
        body.update(decoding_config.to_mapping())
    body.update(
        _reasoning_fields(
            model=model,
            reasoning_request=reasoning_request,
            vllm_capability=vllm_reasoning_capability,
            lm_studio_capability=lm_studio_reasoning_capability,
        )
    )
    return body


def _reasoning_fields(
    *,
    model: str,
    reasoning_request: OpenAICompatibleReasoningRequest | None,
    vllm_capability: VLLMReasoningCapabilityAttestation | None,
    lm_studio_capability: LMStudioReasoningCapabilityAttestation | None,
) -> dict[str, object]:
    if reasoning_request is None:
        return {}
    if vllm_capability is not None and lm_studio_capability is not None:
        raise ValueError(
            "vLLM and LM Studio reasoning capabilities cannot be attached together"
        )
    if vllm_capability is not None:
        if vllm_capability.request_model != model:
            raise ValueError(
                "vLLM reasoning capability request_model must match serialized model"
            )
        return realize_vllm_reasoning_request(
            request=reasoning_request,
            capability=vllm_capability,
        ).to_request_fields()
    if lm_studio_capability is not None:
        if lm_studio_capability.request_model != model:
            raise ValueError(
                "LM Studio reasoning capability request_model must match serialized model"
            )
        return dict(
            realize_lm_studio_reasoning_request(
                request=reasoning_request,
                capability=lm_studio_capability,
            ).wire_fields
        )
    raise ValueError(
        "an explicit reasoning request requires an attested backend reasoning capability"
    )


# Backward-compatible internal name for existing tests/importers while all current
# serializers converge on the provider-neutral dispatcher above.
def _vllm_reasoning_fields(
    *,
    model: str,
    reasoning_request: OpenAICompatibleReasoningRequest | None,
    capability: VLLMReasoningCapabilityAttestation | None,
) -> dict[str, object]:
    return _reasoning_fields(
        model=model,
        reasoning_request=reasoning_request,
        vllm_capability=capability,
        lm_studio_capability=None,
    )


async def _iter_sse_data(response: httpx.Response) -> AsyncIterator[str]:
    buffer = b""
    data_lines: list[str] = []

    async for chunk in response.aiter_bytes():
        buffer += chunk
        while b"\n" in buffer:
            raw_line, buffer = buffer.split(b"\n", 1)
            if raw_line.endswith(b"\r"):
                raw_line = raw_line[:-1]
            if not raw_line:
                if data_lines:
                    yield "\n".join(data_lines)
                    data_lines.clear()
                continue
            if raw_line.startswith(b":"):
                continue
            if raw_line.startswith(b"data:"):
                payload = raw_line[5:]
                if payload.startswith(b" "):
                    payload = payload[1:]
                data_lines.append(payload.decode("utf-8"))

    if buffer:
        raise ProviderProtocolError("upstream SSE ended with a truncated line")
    if data_lines:
        raise ProviderProtocolError("upstream SSE ended with an unterminated SSE event")


def _parse_stream_event(data: str) -> tuple[str | None, Any]:
    envelope = _load_cognitive_wire_json(
        data,
        invalid_message="upstream SSE data is not valid JSON",
    )
    try:
        choices = _mapping(envelope, "provider stream response")["choices"]
        if not isinstance(choices, list) or len(choices) != 1:
            raise ProviderProtocolError(
                "provider stream choices must contain exactly one choice"
            )
        choice = _mapping(choices[0], "provider stream choice")
        _require_successful_finish_reason(choice, label="provider stream response")
        delta = _mapping(choice.get("delta", {}), "provider stream delta")
    except KeyError as exc:
        raise ProviderProtocolError(f"provider stream missing field: {exc.args[0]}") from exc

    content = delta.get("content")
    if content is not None and not isinstance(content, str):
        raise ProviderProtocolError("provider stream delta content must be a string or null")
    return content, choice.get("finish_reason")


class _IncrementalUtteranceDecoder:
    _prefix = re.compile(r'^\s*\{\s*"utterance"\s*:\s*"')
    _simple_escapes = {
        '"': '"',
        "\\": "\\",
        "/": "/",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }

    def __init__(self) -> None:
        self.buffer = ""
        self.position: int | None = None
        self.ended = False
        self.emitted = ""

    def feed(self, fragment: str) -> str:
        self.buffer += fragment
        if self.ended:
            return ""
        if self.position is None:
            match = self._prefix.match(self.buffer)
            if match is None:
                return ""
            self.position = match.end()

        output: list[str] = []
        index = self.position
        while index < len(self.buffer):
            char = self.buffer[index]
            if char == '"':
                self.ended = True
                index += 1
                break
            if ord(char) < 0x20:
                raise ProviderProtocolError("invalid control character in streamed utterance")
            if char != "\\":
                output.append(char)
                index += 1
                continue

            if index + 1 >= len(self.buffer):
                break
            escape = self.buffer[index + 1]
            if escape in self._simple_escapes:
                output.append(self._simple_escapes[escape])
                index += 2
                continue
            if escape != "u":
                raise ProviderProtocolError("invalid escape in streamed utterance")
            if index + 6 > len(self.buffer):
                break
            digits = self.buffer[index + 2 : index + 6]
            if any(char not in "0123456789abcdefABCDEF" for char in digits):
                raise ProviderProtocolError("invalid unicode escape in streamed utterance")
            codepoint = int(digits, 16)
            if 0xD800 <= codepoint <= 0xDBFF:
                if index + 12 > len(self.buffer):
                    break
                if self.buffer[index + 6 : index + 8] != "\\u":
                    raise ProviderProtocolError("invalid surrogate pair in streamed utterance")
                low_digits = self.buffer[index + 8 : index + 12]
                if any(char not in "0123456789abcdefABCDEF" for char in low_digits):
                    raise ProviderProtocolError("invalid unicode escape in streamed utterance")
                low = int(low_digits, 16)
                if not 0xDC00 <= low <= 0xDFFF:
                    raise ProviderProtocolError("invalid surrogate pair in streamed utterance")
                output.append(chr(0x10000 + ((codepoint - 0xD800) << 10) + (low - 0xDC00)))
                index += 12
                continue
            if 0xDC00 <= codepoint <= 0xDFFF:
                raise ProviderProtocolError("unexpected low surrogate in streamed utterance")
            output.append(chr(codepoint))
            index += 6

        self.position = index
        text = "".join(output)
        self.emitted += text
        return text


def serialize_cognitive_input(cognitive_input: CognitiveInput) -> dict[str, Any]:
    content = cognitive_input.input.payload.get("content")
    if not isinstance(content, str):
        raise ProviderProtocolError("current input Event must contain string payload.content")

    context = []
    for item in cognitive_input.context:
        serialized_item: dict[str, Any] = {
            "content": item.content,
            "sources": list(item.sources),
        }
        if item.actor is not None:
            serialized_item["actor"] = item.actor
        context.append(serialized_item)

    return {
        "identity": {"content": cognitive_input.identity.content},
        "state_classes": dict(cognitive_input.state_classes),
        "state": [
            {
                "state_class": record.state_class,
                "key": record.key,
                "value": record.value,
                "sources": list(record.sources),
            }
            for record in cognitive_input.state
        ],
        "context": context,
        "knowledge": [
            {
                "content": item.content,
                "location": item.location,
            }
            for item in cognitive_input.knowledge
        ],
        "memory": [
            {
                "content": item.content,
                "location": item.location,
            }
            for item in cognitive_input.memory
        ],
        "event_evidence": [
            {
                "event_id": item.event_id,
                "type": item.event_type,
                "actor": item.actor,
                "timestamp": item.timestamp,
                "content": item.content,
            }
            for item in cognitive_input.event_evidence
        ],
        "input": {
            "event_id": cognitive_input.input.id,
            "actor": cognitive_input.input.actor,
            "content": content,
        },
    }


def _require_candidate_sources_in_cognitive_input(
    output: CognitiveOutput,
    cognitive_input: CognitiveInput,
) -> None:
    allowed_source_ids = {cognitive_input.input.id}
    for record in cognitive_input.state:
        allowed_source_ids.update(record.sources)
    for item in cognitive_input.context:
        allowed_source_ids.update(item.sources)
    allowed_source_ids.update(item.event_id for item in cognitive_input.event_evidence)

    for label, candidates in (
        ("state_candidates", output.state_candidates),
        ("continuity_candidates", output.continuity_candidates),
    ):
        for index, candidate in enumerate(candidates):
            unknown_sources = sorted(set(candidate.sources) - allowed_source_ids)
            if unknown_sources:
                raise ProviderProtocolError(
                    f"{label}[{index}].sources contain Event IDs absent from CognitiveInput: "
                    + ", ".join(unknown_sources)
                )


def parse_chat_completion(envelope: Any) -> CognitiveOutput:
    try:
        choices = _mapping(envelope, "provider response")["choices"]
        if not isinstance(choices, list) or len(choices) != 1:
            raise ProviderProtocolError(
                "provider response choices must contain exactly one choice"
            )
        choice = _mapping(choices[0], "provider choice")
        _require_successful_finish_reason(choice, label="provider response")
        message = choice["message"]
        content = _mapping(message, "provider message")["content"]
    except KeyError as exc:
        raise ProviderProtocolError(f"provider response missing field: {exc.args[0]}") from exc

    if not isinstance(content, str):
        raise ProviderProtocolError("provider message content must be a JSON string")
    wire = _load_cognitive_wire_json(
        content,
        invalid_message="provider message content is not valid JSON",
    )
    return parse_wire_output(wire)


def parse_wire_output(wire: Any) -> CognitiveOutput:
    wire = _mapping(wire, "cognitive wire output")
    expected_top_level = {"utterance", "state_candidates", "continuity_candidates"}
    if set(wire) != expected_top_level:
        raise ProviderProtocolError(
            "cognitive wire output must contain exactly utterance, state_candidates, "
            "and continuity_candidates"
        )
    utterance = wire.get("utterance")
    if not isinstance(utterance, str) or not utterance.strip():
        raise ProviderProtocolError("wire utterance must be a non-empty string")
    state_candidates, continuity_candidates = _parse_candidate_collections(
        raw_candidates=wire.get("state_candidates"),
        raw_continuity_candidates=wire.get("continuity_candidates"),
    )
    return CognitiveOutput(
        response=utterance,
        state_candidates=state_candidates,
        continuity_candidates=continuity_candidates,
    )


def _parse_candidate_collections(
    *,
    raw_candidates: Any,
    raw_continuity_candidates: Any,
) -> tuple[tuple[StateCandidate, ...], tuple[ContinuityCandidate, ...]]:
    if not isinstance(raw_candidates, list):
        raise ProviderProtocolError("wire state_candidates must be an array")
    if not isinstance(raw_continuity_candidates, list):
        raise ProviderProtocolError("wire continuity_candidates must be an array")

    candidates: list[StateCandidate] = []
    expected_state_keys = {"state_class", "key", "op", "value", "sources"}
    for index, raw in enumerate(raw_candidates):
        candidate = _mapping(raw, f"state_candidates[{index}]")
        if set(candidate) != expected_state_keys:
            raise ProviderProtocolError(
                f"state_candidates[{index}] must contain exactly "
                "state_class, key, op, value, and sources"
            )
        state_class = _required_string(candidate, "state_class", index)
        key = _required_string(candidate, "key", index)
        op = _required_string(candidate, "op", index)
        sources = candidate.get("sources")
        if not isinstance(sources, list) or not sources or not all(
            isinstance(source, str) and source.strip() for source in sources
        ):
            raise ProviderProtocolError(
                f"state_candidates[{index}].sources must be non-empty strings"
            )
        if op == "set":
            value = _parse_set_value(candidate["value"], index)
            candidates.append(
                StateCandidate.set(
                    state_class=state_class,
                    key=key,
                    value=value,
                    sources=tuple(sources),
                )
            )
        elif op == "remove":
            if candidate["value"] is not None:
                raise ProviderProtocolError(
                    f"state_candidates[{index}] remove value must be null"
                )
            candidates.append(
                StateCandidate.remove(
                    state_class=state_class,
                    key=key,
                    sources=tuple(sources),
                )
            )
        else:
            raise ProviderProtocolError(f"state_candidates[{index}] unsupported op: {op}")

    continuity_candidates = tuple(
        _parse_continuity_candidate(raw, index)
        for index, raw in enumerate(raw_continuity_candidates)
    )
    return tuple(candidates), continuity_candidates


def _parse_continuity_candidate(raw: Any, index: int) -> ContinuityCandidate:
    candidate = _mapping(raw, f"continuity_candidates[{index}]")
    expected_keys = {"kind", "key", "op", "value", "sources", "epistemic_role"}
    if set(candidate) != expected_keys:
        raise ProviderProtocolError(
            f"continuity_candidates[{index}] must contain exactly "
            "kind, key, op, value, sources, and epistemic_role"
        )

    kind = _required_continuity_string(candidate, "kind", index)
    key = _required_continuity_string(candidate, "key", index)
    op = _required_continuity_string(candidate, "op", index)
    epistemic_role = _required_continuity_string(
        candidate, "epistemic_role", index
    )
    sources = candidate.get("sources")
    if not isinstance(sources, list) or not sources or not all(
        isinstance(source, str) and source.strip() for source in sources
    ):
        raise ProviderProtocolError(
            f"continuity_candidates[{index}].sources must be non-empty strings"
        )

    try:
        if op == "set":
            _validate_continuity_json_value(candidate["value"], index)
            return ContinuityCandidate.set(
                kind=kind,
                key=key,
                value=candidate["value"],
                sources=tuple(sources),
                epistemic_role=epistemic_role,
            )
        if op == "resolve":
            if candidate["value"] is not None:
                raise ProviderProtocolError(
                    f"continuity_candidates[{index}] resolve value must be null"
                )
            return ContinuityCandidate.resolve(
                kind=kind,
                key=key,
                sources=tuple(sources),
                epistemic_role=epistemic_role,
            )
    except (TypeError, ValueError) as exc:
        raise ProviderProtocolError(
            f"continuity_candidates[{index}] is invalid: {exc}"
        ) from exc

    raise ProviderProtocolError(
        f"continuity_candidates[{index}] unsupported op: {op}"
    )


def _validate_continuity_json_value(value: Any, index: int) -> None:
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ProviderProtocolError(
            f"continuity_candidates[{index}] set value must be finite JSON"
        ) from exc


def _parse_set_value(value: Any, index: int) -> Any:
    if isinstance(value, str):
        return value
    if not isinstance(value, Mapping):
        raise ProviderProtocolError(
            f"state_candidates[{index}] set value must be a string or degree-hint object"
        )
    if set(value) != {"semantic", "degree_hint"}:
        raise ProviderProtocolError(
            f"state_candidates[{index}] degree-hint value must contain only semantic and degree_hint"
        )
    semantic = value.get("semantic")
    degree = value.get("degree_hint")
    if not isinstance(semantic, str) or not semantic.strip():
        raise ProviderProtocolError(
            f"state_candidates[{index}] degree-hint semantic must be a non-empty string"
        )
    if isinstance(degree, bool) or not isinstance(degree, (int, float)):
        raise ProviderProtocolError(
            f"state_candidates[{index}] degree_hint must be a number from 0 through 1"
        )
    if not math.isfinite(float(degree)) or not 0.0 <= float(degree) <= 1.0:
        raise ProviderProtocolError(
            f"state_candidates[{index}] degree_hint must be a number from 0 through 1"
        )
    return {"semantic": semantic, "degree_hint": degree}


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderProtocolError(f"{label} must be an object")
    return value


def _required_string(mapping: Mapping[str, Any], key: str, index: int) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProviderProtocolError(
            f"state_candidates[{index}].{key} must be a non-empty string"
        )
    return value


def _required_continuity_string(
    mapping: Mapping[str, Any], key: str, index: int
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProviderProtocolError(
            f"continuity_candidates[{index}].{key} must be a non-empty string"
        )
    return value
