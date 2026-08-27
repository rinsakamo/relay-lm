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
    CognitionStructuredOutputMode,
)
from relaylm.providers.openai_compatible import (
    WIRE_SCHEMA,
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
from relaylm.providers.openai_compatible_cognition import (
    describe_openai_compatible_cognition_capabilities,
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

EXTRACTION_WIRE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "state_candidates",
        "continuity_candidates",
    ],
    "properties": {
        "state_candidates": WIRE_SCHEMA["properties"]["state_candidates"],
        "continuity_candidates": WIRE_SCHEMA["properties"]["continuity_candidates"],
    },
}

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
        _require_plain_pass1(pass_request)
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
        _require_plain_pass1(pass_request)
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
        structured_output_mode = _resolve_extraction_structured_output_mode(
            pass_request=pass_request,
            provider=self,
        )
        envelope = await self._post_two_pass(
            body=_extraction_request_body(
                model=self.model,
                extraction_input=extraction_input,
                decoding=decoding_config.to_mapping(),
                reasoning_request=effective_reasoning,
                vllm_reasoning_capability=effective_capability,
                structured_output_mode=structured_output_mode,
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


def _require_plain_pass1(pass_request: CognitionPassRequest | None) -> None:
    if pass_request is not None and pass_request.structured_output_mode is not None:
        raise ValueError("structured_output_mode applies only to Pass 2 extraction")


def _resolve_extraction_structured_output_mode(
    *,
    pass_request: CognitionPassRequest | None,
    provider: OpenAICompatibleProvider,
) -> CognitionStructuredOutputMode:
    requested = (
        None if pass_request is None else pass_request.structured_output_mode
    )
    if requested is None or requested is CognitionStructuredOutputMode.PLAIN:
        return CognitionStructuredOutputMode.PLAIN
    if requested is CognitionStructuredOutputMode.NATIVE:
        return CognitionStructuredOutputMode.NATIVE
    if requested is not CognitionStructuredOutputMode.AUTO:
        raise TypeError("unsupported structured output mode")
    capabilities = describe_openai_compatible_cognition_capabilities(provider)
    return (
        CognitionStructuredOutputMode.NATIVE
        if capabilities.structured_output
        else CognitionStructuredOutputMode.PLAIN
    )


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
    structured_output_mode: CognitionStructuredOutputMode = CognitionStructuredOutputMode.PLAIN,
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
    if structured_output_mode is CognitionStructuredOutputMode.NATIVE:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "relaylm_structured_cognition_output",
                "strict": True,
                "schema": EXTRACTION_WIRE_SCHEMA,
            },
        }
    elif structured_output_mode is not CognitionStructuredOutputMode.PLAIN:
        raise ValueError("extraction structured output mode must resolve before request")
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
    source_id = extraction_input.originating_event_id
    like_example = json.dumps(
        {
            "state_class": "user.preference",
            "key": "coffee",
            "op": "set",
            "value": "likes",
            "sources": [source_id],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    preferred_example = json.dumps(
        {
            "state_class": "user.preference",
            "key": "preferred_beverage",
            "op": "set",
            "value": "coffee",
            "sources": [source_id],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    remove_example = json.dumps(
        {
            "state_class": "user.preference",
            "key": "coffee",
            "op": "remove",
            "value": None,
            "sources": [source_id],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    referent_example = json.dumps(
        {
            "kind": "referent",
            "key": "current_document",
            "op": "set",
            "value": "the draft",
            "sources": [source_id],
            "epistemic_role": "user_assertion",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    unresolved_example = json.dumps(
        {
            "kind": "unresolved",
            "key": "document_author",
            "op": "set",
            "value": "author not yet known",
            "sources": [source_id],
            "epistemic_role": "user_assertion",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    active_task_example = json.dumps(
        {
            "kind": "active_task",
            "key": "verify_document_author",
            "op": "set",
            "value": "verify the document author",
            "sources": [source_id],
            "epistemic_role": "user_assertion",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""EXTRACTION

<PASS_1_RESPONSE_JSON>
{response_json}
</PASS_1_RESPONSE_JSON>

Interpret this originating turn as this character, then project only grounded State and bounded Continuity proposals.
Emit `state_candidates`, then `continuity_candidates`.

Projection rules:
- Durable State gate: emit State only when the current Input presents the candidate meaning as sufficiently asserted, committed, or otherwise established for persistent current understanding.
- Tentative, hypothetical, merely possible, guessed, hedged, or explicitly self-uncertain meaning stays uncommitted: emit no durable State for that meaning.
- Apply this gate by meaning regardless of language or state_class; do not use surface keywords or grammatical patterns as the gate.
- Epistemic uncertainty is not degree_hint; degree_hint remains semantic intensity only. A later resolved assertion may establish State normally.
- State wire: `{{state_class,key,op,value,sources}}`. `state_class` must be a key in CognitiveInput.state_classes. `op` is `set` or `remove`. For `set`, value is a string or `{{"semantic":string,"degree_hint":0..1}}`; degree_hint is intensity, not confidence. For `remove`, value is null; remove only for explicit revocation, cancellation, denial, correction, or termination.
- State `key` is the stable subject or dimension within its `state_class`; `value` is the accepted semantic value for that key. Preserve an established class/key pair when current State already provides one rather than inventing a synonym.
- State examples demonstrate representation only; never copy example values, keys, or claims unless current evidence supports that exact meaning:
  - Liking a subject: `{like_example}`
  - A preference dimension whose value is the subject: `{preferred_example}`
  - Explicit revocation of an accepted subject preference: `{remove_example}`
- Continuity wire: `{{kind,key,op,value,sources,epistemic_role}}`. `op` is `set` or `resolve`; set value is finite JSON and resolve value is null. Carry Continuity only when it is useful for upcoming coherence.
- Continuity meanings (classify independently):
  - `referent`: a specific subject or entity that upcoming dialogue may refer back to.
  - `unresolved`: an explicit open question or unknown value that remains to be resolved.
  - `active_task`: an unfinished action, process, or goal expected to continue.
- Emit every distinct useful Continuity meaning present; do not choose only one best kind.
- New items use a short stable semantic `key`; exact first-introduction wording is not globally canonical.
- Continuity transition decision:
  - new useful meaning -> emit `set` with a new stable key.
  - unchanged accepted meaning -> emit no candidate.
  - changed or resolved accepted meaning -> reuse its existing lifecycle key.
- Before concluding there are no Continuity candidates, check `unresolved` independently: if this turn newly establishes an explicit open question or unknown value, emit a new `unresolved` set when no accepted unresolved item already represents that open issue, even when related accepted `referent` or `active_task` meanings are unchanged.
- An explicitly maintained unknown value is itself an `unresolved` meaning when no accepted unresolved item already represents it. Do not require a new `active_task`, a question form, or a change to an existing task before emitting it.
- Unchanged accepted `referent` or `active_task` meanings do not suppress a distinct newly established `unresolved` meaning.
- If related accepted referent/task meanings are unchanged and the current Event newly establishes an unknown value with no accepted unresolved item, emit only the new `unresolved` set as applicable.
- A `referent` identifies the reference target; new descriptive facts about the same target do not supersede it unless the referential target itself changes.
- For ordinary-turn Continuity, every new set/resolve transition must include the current Input Event ID `{source_id}` in `sources`; prior Continuity/context sources describe existing context but cannot substitute for current evidence of a new transition.
- Resolve only when the current turn actually resolves or completes an existing item; reuse that item's `kind` + `key`, set value to null, and ground the resolution in the current Input Event.
- Continuity examples demonstrate representation only; never copy their keys, values, or claims unless current evidence supports that exact meaning:
  - Referent: `{referent_example}`
  - Unresolved transition example: `{unresolved_example}`
  - Active task: `{active_task_example}`
- Never use `resolve` as `kind`; keep `kind` as `referent`, `unresolved`, or `active_task`.
- `kind` and `epistemic_role` are separate enum axes; `unresolved` is a `kind` only and must never be used as `epistemic_role`.
- `epistemic_role` must be exactly `user_assertion`, `assistant_inference`, or `assistant_commitment`.
- `sources` are non-empty Event IDs present in CognitiveInput; never invent IDs. Pass 1 response is interpretive context only and must never self-certify user facts/preferences/goals/experience, external truth, prior events, or source provenance.

Exact top-level shape:
`{{"state_candidates":[],"continuity_candidates":[]}}`

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
        "state_candidates",
        "continuity_candidates",
    }:
        raise ProviderProtocolError(
            "extraction wire output must contain exactly state_candidates "
            "and continuity_candidates"
        )
    state_candidates, continuity_candidates = _parse_candidate_collections(
        raw_candidates=wire["state_candidates"],
        raw_continuity_candidates=wire["continuity_candidates"],
    )
    return CognitionExtractionOutput(
        state_candidates=state_candidates,
        continuity_candidates=continuity_candidates,
        completion=completion,
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
