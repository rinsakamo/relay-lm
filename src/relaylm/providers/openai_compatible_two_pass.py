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
            )
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
            )
        )
        output = _parse_extraction_completion(envelope)
        _require_candidate_sources_in_cognitive_input(
            output,
            extraction_input.cognitive_input,
        )
        return output

    async def _post_two_pass(self, *, body: dict[str, Any]) -> Any:
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            )
            if not response.is_success:
                raise _provider_http_error(
                    response,
                    prefix="upstream request failed",
                    api_key=self.api_key,
                )
            return _load_provider_response_json(response)
        except ProviderProtocolError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderProtocolError(f"upstream request failed: {exc}") from exc


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
    schema_json = json.dumps(
        _extraction_output_schema(extraction_input.cognitive_input),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""EXTRACTION

<PASS_1_RESPONSE_JSON>
{response_json}
</PASS_1_RESPONSE_JSON>

Construct the structured cognition result for this originating turn.

First construct `turn_interpretation` in exactly this order:

1. `user_meaning`
   What this character understands the user to mean in the current turn.
   This is the character's subjective understanding through Identity, accepted State,
   and the supplied context, not merely a literal summary of the user's words.

2. `change_signals`
   Meaningful changes relative to accepted current understanding, including new meaning,
   correction, revocation, supersession, strengthening, weakening, or other updates.

3. `self_meaning`
   What the interpreted meaning means to this character itself, including personally,
   emotionally, relationally, or in terms of the character's own beliefs, goals, or condition.

4. `assistant_effects`
   Meanings introduced by the Pass 1 response that may matter to cognition or continuation,
   such as a question, proposal, commitment, or intentionally unfinished interaction.

5. `unresolved`
   Meanings that should not yet be decided because the supplied evidence leaves them
   ambiguous, incomplete, underspecified, or open to multiple interpretations.

6. `continuity_signals`
   Meanings worth carrying across upcoming turns for coherent interaction, such as
   a referent, unresolved thread, or active task.

Each field is an array of concise semantic statements.
Use an empty array when there is nothing meaningful to record.

After constructing `turn_interpretation`, propose `state_candidates` and `continuity_candidates`.

`turn_interpretation` is interpretation, not accepted State and not authority by itself.
Propose State only when an adequately grounded and sufficiently resolved meaning represents a meaningful durable change in the character's accepted current understanding.
Do not propose a State change merely because a meaning appears in `turn_interpretation`.
When accepted State already establishes a State class/key vocabulary, preserve it.

Use `set` when State should now exist or its semantic value should meaningfully change.
Use `remove` only for explicit revocation, cancellation, denial, correction, or termination.
Weakening, uncertainty, hesitation, or temporary variation alone do not imply removal.

Preserve uncertainty and degree.
Use a degree hint only when the current turn materially expresses a useful comparative or intensity relation.
A degree hint is semantic intensity, not confidence, probability, evidence strength, authority, or salience.

Propose Continuity only when carrying the meaning across upcoming turns would materially improve conversational coherence.
An item in `unresolved` does not by itself require an `unresolved` ContinuityCandidate.
Use Continuity for `referent`, `unresolved`, or `active_task` meaning under the supplied current context.

The supplied Pass 1 response is interpretive context only.
It must never self-certify a user fact, preference, goal, experience, external truth, prior event, or source provenance.

Preserve the existing RelayLM source semantics.
Candidate `sources` must use Event IDs available in the supplied CognitiveInput.
Never invent Event IDs.
A proposal has no authority merely because this pass emitted it; RelayLM validates all proposals deterministically.

Construct the JSON object in this order:
1. `turn_interpretation.user_meaning`
2. `turn_interpretation.change_signals`
3. `turn_interpretation.self_meaning`
4. `turn_interpretation.assistant_effects`
5. `turn_interpretation.unresolved`
6. `turn_interpretation.continuity_signals`
7. `state_candidates`
8. `continuity_candidates`

<OUTPUT_SCHEMA>
{schema_json}
</OUTPUT_SCHEMA>

Return exactly one JSON object matching the supplied schema."""


def _extraction_output_schema(cognitive_input: CognitiveInput) -> dict[str, Any]:
    string_array = {
        "type": "array",
        "items": {"type": "string", "minLength": 1},
    }
    degree_hint = {
        "type": "object",
        "additionalProperties": False,
        "required": ["semantic", "degree_hint"],
        "properties": {
            "semantic": {"type": "string", "minLength": 1},
            "degree_hint": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "turn_interpretation",
            "state_candidates",
            "continuity_candidates",
        ],
        "properties": {
            "turn_interpretation": {
                "type": "object",
                "additionalProperties": False,
                "required": list(TURN_INTERPRETATION_FIELDS),
                "properties": {
                    field: string_array for field in TURN_INTERPRETATION_FIELDS
                },
            },
            "state_candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["state_class", "key", "op", "value", "sources"],
                    "properties": {
                        "state_class": {
                            "type": "string",
                            "enum": list(cognitive_input.state_classes),
                        },
                        "key": {"type": "string", "minLength": 1},
                        "op": {"type": "string", "enum": ["set", "remove"]},
                        "value": {
                            "anyOf": [
                                {"type": "string"},
                                degree_hint,
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
                        "kind": {
                            "type": "string",
                            "enum": ["referent", "unresolved", "active_task"],
                        },
                        "key": {"type": "string", "minLength": 1},
                        "op": {"type": "string", "enum": ["set", "resolve"]},
                        "value": {},
                        "sources": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "epistemic_role": {
                            "type": "string",
                            "enum": [
                                "user_assertion",
                                "assistant_inference",
                                "assistant_commitment",
                            ],
                        },
                    },
                },
            },
        },
    }


def _parse_conversation_completion(envelope: Any) -> CognitionConversationOutput:
    content, completion = _completion_content_and_metadata(envelope)
    if not content.strip():
        raise ProviderProtocolError("provider conversation content must not be empty")
    return CognitionConversationOutput(response=content, completion=completion)


def _parse_extraction_completion(envelope: Any) -> CognitionExtractionOutput:
    content, completion = _completion_content_and_metadata(envelope)
    wire = _load_cognitive_wire_json(
        content,
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
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise ProviderProtocolError(
                f"turn_interpretation.{field} must contain non-empty strings"
            )


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
