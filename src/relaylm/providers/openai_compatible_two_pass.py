from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionCompletionMetadata,
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)
from relaylm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderProtocolError,
    _iter_sse_data,
    _load_cognitive_wire_json,
    _load_provider_response_json,
    _parse_candidate_collections,
    _parse_stream_event,
    _provider_http_error,
    _require_candidate_sources_in_cognitive_input,
    _require_successful_finish_reason,
    _resolve_cognition_pass_request,
    _vllm_reasoning_fields,
    serialize_cognitive_input,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningRequest,
)
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityAttestation,
)


COMMON_SYSTEM_INSTRUCTION = """You are the cognitive substrate of a persistent character managed by RelayLM.

Use the supplied CognitiveInput as this character's current cognitive context.

Identity defines who this character is and the subjective lens through which meaning is understood.
Identity is authoritative and immutable.
State is the character's accepted current understanding.

Context, Memory, Event Evidence, and Input retain the authority and provenance supplied by RelayLM.
Interpret the current turn through the character's Identity and accepted State.

Assistant-authored material may support interpretation and conversational continuity, but does not by itself establish user facts or external truth.

Preserve uncertainty, degree, correction, negation, supersession, and source provenance.
Do not invent history, evidence, motives, shared experiences, or supporting details.
Preserve user-provided names and normally use the user's language."""

CONVERSATION_PASS_SUFFIX = """CONVERSATION

Respond as this character."""

TURN_INTERPRETATION_FIELDS = (
    "user_meaning",
    "change_signals",
    "self_meaning",
    "assistant_effects",
    "unresolved",
    "continuity_signals",
)

_EXTRACTION_JSON_FENCE_PREFIX = "```json\n"
_EXTRACTION_JSON_FENCE_SUFFIX = "\n```"


class OpenAICompatibleTwoPassProvider(OpenAICompatibleProvider):
    """Two-pass capability extension of the canonical OpenAI-compatible adapter."""

    async def generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
        vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
    ) -> CognitionConversationOutput:
        effective_capability = (
            vllm_reasoning_capability or self.vllm_reasoning_capability
        )
        decoding_config, effective_reasoning = _resolve_cognition_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            decoding_config=self.decoding_config,
            decoding_capabilities=self.decoding_capabilities,
            vllm_reasoning_capability=effective_capability,
        )
        envelope = await self._post_two_pass(
            body=_conversation_request_body(
                model=self.model,
                cognitive_input=cognitive_input,
                stream=False,
                decoding=decoding_config.to_mapping(),
                reasoning_request=effective_reasoning,
                vllm_reasoning_capability=effective_capability,
            ),
            boundary="conversation",
        )
        return _parse_conversation_completion(envelope)

    async def stream_generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        emit_response_delta: Callable[[str], Awaitable[None]],
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
        vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
    ) -> CognitionConversationOutput:
        effective_capability = (
            vllm_reasoning_capability or self.vllm_reasoning_capability
        )
        decoding_config, effective_reasoning = _resolve_cognition_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            decoding_config=self.decoding_config,
            decoding_capabilities=self.decoding_capabilities,
            vllm_reasoning_capability=effective_capability,
        )
        response_text = ""
        saw_done = False
        saw_finish = False
        terminal_finish_reason: str | None = None

        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=_conversation_request_body(
                    model=self.model,
                    cognitive_input=cognitive_input,
                    stream=True,
                    decoding=decoding_config.to_mapping(),
                    reasoning_request=effective_reasoning,
                    vllm_reasoning_capability=effective_capability,
                ),
            ) as response:
                if not response.is_success:
                    await response.aread()
                    raise _provider_http_error(
                        response,
                        prefix="upstream conversation streaming request failed",
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
                        response_text += content
                        if content:
                            await emit_response_delta(content)
                    if finish_reason is not None:
                        saw_finish = True
                        terminal_finish_reason = finish_reason
        except ProviderProtocolError:
            raise
        except (httpx.HTTPError, UnicodeDecodeError, ValueError) as exc:
            raise ProviderProtocolError(
                f"upstream conversation streaming request failed: {exc}"
            ) from exc

        if not saw_done and not saw_finish:
            raise ProviderProtocolError(
                "upstream conversation stream ended before completion"
            )
        if not response_text.strip():
            raise ProviderProtocolError(
                "upstream conversation stream contained no visible response"
            )
        return CognitionConversationOutput(
            response=response_text,
            completion=CognitionCompletionMetadata(
                finish_reason=terminal_finish_reason,
            ),
        )

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
        vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
    ) -> CognitionExtractionOutput:
        effective_capability = (
            vllm_reasoning_capability or self.vllm_reasoning_capability
        )
        decoding_config, effective_reasoning = _resolve_cognition_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            decoding_config=self.decoding_config,
            decoding_capabilities=self.decoding_capabilities,
            vllm_reasoning_capability=effective_capability,
        )
        envelope = await self._post_two_pass(
            body=_extraction_request_body(
                model=self.model,
                extraction_input=extraction_input,
                decoding=decoding_config.to_mapping(),
                reasoning_request=effective_reasoning,
                vllm_reasoning_capability=effective_capability,
            ),
            boundary="extraction",
        )
        output = _parse_extraction_completion(envelope)
        _require_candidate_sources_in_cognitive_input(
            output,
            extraction_input.cognitive_input,
        )
        return output

    async def _post_two_pass(
        self,
        *,
        body: dict[str, Any],
        boundary: str,
    ) -> Any:
        prefix = f"upstream {boundary} request failed"
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            )
            if not response.is_success:
                raise _provider_http_error(
                    response,
                    prefix=prefix,
                    api_key=self.api_key,
                )
            return _load_provider_response_json(response)
        except ProviderProtocolError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderProtocolError(f"{prefix}: {exc}") from exc


def _common_cognitive_prefix(cognitive_input: CognitiveInput) -> str:
    serialized = json.dumps(
        serialize_cognitive_input(cognitive_input),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        "<COGNITIVE_INPUT>\n"
        f"{serialized}\n"
        "</COGNITIVE_INPUT>\n\n"
        "<PASS>\n"
    )


def _conversation_request_body(
    *,
    model: str,
    cognitive_input: CognitiveInput,
    stream: bool,
    decoding: dict[str, int | float],
    reasoning_request: OpenAICompatibleReasoningRequest | None = None,
    vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": COMMON_SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": _common_cognitive_prefix(cognitive_input)
                + CONVERSATION_PASS_SUFFIX,
            },
        ],
        "stream": stream,
    }
    body.update(decoding)
    body.update(
        _vllm_reasoning_fields(
            model=model,
            reasoning_request=reasoning_request,
            capability=vllm_reasoning_capability,
        )
    )
    return body


def _extraction_request_body(
    *,
    model: str,
    extraction_input: CognitionExtractionInput,
    decoding: dict[str, int | float],
    reasoning_request: OpenAICompatibleReasoningRequest | None = None,
    vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": COMMON_SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": _common_cognitive_prefix(extraction_input.cognitive_input)
                + _extraction_pass_suffix(extraction_input),
            },
        ],
        "stream": False,
    }
    body.update(decoding)
    body.update(
        _vllm_reasoning_fields(
            model=model,
            reasoning_request=reasoning_request,
            capability=vllm_reasoning_capability,
        )
    )
    return body


def _extraction_pass_suffix(extraction_input: CognitionExtractionInput) -> str:
    response_json = json.dumps(
        {"content": extraction_input.assistant_response},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""EXTRACTION

<PASS_1_RESPONSE_JSON>
{response_json}
</PASS_1_RESPONSE_JSON>

Interpret this originating turn as this character. Build one JSON object in this order:
1. `user_meaning`: string[] — subjective meaning through Identity, accepted State, and context; not a literal summary.
2. `change_signals`: string[] — new, corrected, revoked, superseded, strengthened, or weakened accepted understanding.
3. `self_meaning`: string[] — personal or relational implications for this character's beliefs, goals, or condition.
4. `assistant_effects`: string[] — relevant question, proposal, commitment, or unfinished effect introduced by Pass 1.
5. `unresolved`: string[] — meaning not justified yet because evidence is ambiguous or incomplete.
6. `continuity_signals`: string[] — bounded meaning useful across upcoming turns.
Empty arrays are valid. Then emit `state_candidates`, then `continuity_candidates`.
Interpretation arrays contain text strings only; never put State/Continuity wire objects in `turn_interpretation`.
`continuity_signals` contains only bounded meaning strings; structured Continuity records belong only in top-level `continuity_candidates`.
Structured State records belong only in top-level `state_candidates`.

Projection rules:
- Interpretation is not authority or State. Propose State only for grounded, sufficiently resolved, meaningful durable change; preserve existing class/key vocabulary.
- State wire: `{{state_class,key,op,value,sources}}`. `state_class` must be a key in CognitiveInput.state_classes. `op` is `set` or `remove`. For `set`, value is a string or `{{"semantic":string,"degree_hint":0..1}}`; degree_hint is intensity, not confidence. For `remove`, value is null; remove only for explicit revocation, cancellation, denial, correction, or termination.
- Continuity wire: `{{kind,key,op,value,sources,epistemic_role}}`. `kind` is `referent`, `unresolved`, or `active_task`; `op` is `set` or `resolve`; set value is finite JSON and resolve value is null; epistemic_role is `user_assertion`, `assistant_inference`, or `assistant_commitment`. Carry only when useful for upcoming coherence; an `unresolved` interpretation is not automatically Continuity.
- Never use `resolve` as `kind`; keep `kind` as `referent`, `unresolved`, or `active_task`.
- Resolve example for an active task: `{{"kind":"active_task","op":"resolve","value":null}}`.
- `sources` are non-empty Event IDs present in CognitiveInput; never invent IDs. Pass 1 response is interpretive context only and must never self-certify user facts/preferences/goals/experience, external truth, prior events, or source provenance.

Exact top-level shape:
`{{"turn_interpretation":{{"user_meaning":[],"change_signals":[],"self_meaning":[],"assistant_effects":[],"unresolved":[],"continuity_signals":[]}},"state_candidates":[],"continuity_candidates":[]}}`

Return exactly one JSON object with no extra keys."""


def _parse_conversation_completion(envelope: Any) -> CognitionConversationOutput:
    content, completion = _completion_content_and_metadata(envelope)
    if not content.strip():
        raise ProviderProtocolError("provider conversation content must not be empty")
    return CognitionConversationOutput(response=content, completion=completion)


def _normalize_extraction_json_content(content: str) -> str:
    """Remove only the exact fenced-JSON presentation wrapper observed in Stage R."""

    if content.startswith(_EXTRACTION_JSON_FENCE_PREFIX) and content.endswith(
        _EXTRACTION_JSON_FENCE_SUFFIX
    ):
        return content[
            len(_EXTRACTION_JSON_FENCE_PREFIX) : -len(_EXTRACTION_JSON_FENCE_SUFFIX)
        ]
    return content


def _parse_extraction_completion(envelope: Any) -> CognitionExtractionOutput:
    content, completion = _completion_content_and_metadata(envelope)
    wire = _load_cognitive_wire_json(
        _normalize_extraction_json_content(content),
        invalid_message="provider extraction content is not valid JSON",
    )
    if not isinstance(wire, dict) or set(wire) != {
        "turn_interpretation",
        "state_candidates",
        "continuity_candidates",
    }:
        raise ProviderProtocolError(
            "extraction wire output must contain exactly turn_interpretation, "
            "state_candidates and continuity_candidates"
        )
    _require_turn_interpretation(wire["turn_interpretation"])
    state_candidates, continuity_candidates = _parse_candidate_collections(
        raw_candidates=wire["state_candidates"],
        raw_continuity_candidates=wire["continuity_candidates"],
    )
    return CognitionExtractionOutput(
        state_candidates=state_candidates,
        continuity_candidates=continuity_candidates,
        completion=completion,
    )


def _require_turn_interpretation(raw: object) -> None:
    if not isinstance(raw, dict) or tuple(raw) != TURN_INTERPRETATION_FIELDS:
        raise ProviderProtocolError(
            "turn_interpretation must contain exactly "
            + ", ".join(TURN_INTERPRETATION_FIELDS)
        )
    for field in TURN_INTERPRETATION_FIELDS:
        values = raw[field]
        if not isinstance(values, list):
            raise ProviderProtocolError(
                f"turn_interpretation.{field} must be an array"
            )
        if not all(isinstance(value, str) for value in values):
            raise ProviderProtocolError(
                f"turn_interpretation.{field} must contain strings"
            )
        # Blank-only strings are semantically absent in this non-authoritative,
        # parse-and-discard scaffold. Candidate/source validation remains strict.


def _completion_content_and_metadata(
    envelope: Any,
) -> tuple[str, CognitionCompletionMetadata]:
    if not isinstance(envelope, dict):
        raise ProviderProtocolError("provider response must be an object")
    choices = envelope.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ProviderProtocolError(
            "provider response choices must contain exactly one choice"
        )
    choice = choices[0]
    if not isinstance(choice, dict):
        raise ProviderProtocolError("provider choice must be an object")
    _require_successful_finish_reason(choice, label="provider response")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ProviderProtocolError("provider message must be an object")
    content = message.get("content")
    if not isinstance(content, str):
        raise ProviderProtocolError("provider message content must be a string")
    return content, _completion_metadata(envelope=envelope, choice=choice)


def _completion_metadata(
    *,
    envelope: dict[str, Any],
    choice: dict[str, Any],
) -> CognitionCompletionMetadata:
    usage = envelope.get("usage")
    usage_mapping = usage if isinstance(usage, dict) else {}
    details = usage_mapping.get("completion_tokens_details")
    details_mapping = details if isinstance(details, dict) else {}
    return CognitionCompletionMetadata(
        finish_reason=(
            choice["finish_reason"]
            if isinstance(choice.get("finish_reason"), str)
            else None
        ),
        prompt_tokens=_optional_nonnegative_int(usage_mapping.get("prompt_tokens")),
        completion_tokens=_optional_nonnegative_int(
            usage_mapping.get("completion_tokens")
        ),
        total_tokens=_optional_nonnegative_int(usage_mapping.get("total_tokens")),
        reasoning_tokens=_optional_nonnegative_int(
            details_mapping.get("reasoning_tokens")
        ),
    )


def _optional_nonnegative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value
