from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)
from relaylm.providers.openai_compatible import (
    WIRE_SCHEMA,
    OpenAICompatibleProvider,
    ProviderProtocolError,
    _iter_sse_data,
    _parse_stream_event,
    _resolve_cognition_pass_request,
    _vllm_reasoning_fields,
    parse_wire_output,
    serialize_cognitive_input,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningRequest,
)
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityAttestation,
)


CONVERSATION_SYSTEM_INSTRUCTION = """You are the conversation pass of a persistent character managed by RelayLM.

Use the supplied CognitiveInput JSON to produce only the complete natural-language response shown to the user.
Identity is authoritative and immutable. State is accepted current understanding. Context, Memory, Event Evidence, and Input retain the authority/provenance roles supplied by RelayLM.
Preserve persona, current-context coherence, uncertainty, degree, user-provided names, and normally the user's language.
Assistant-authored material may support conversational continuity but does not prove user facts or external truth.
Do not invent history, evidence, motives, shared experiences, or supporting details.
This pass does not produce StateCandidate or ContinuityCandidate proposals; structured extraction is a separate RelayLM pass.

Return only the complete natural-language response. Do not wrap it in JSON or add metadata."""

EXTRACTION_SYSTEM_INSTRUCTION = """You are the immediate structured-cognition pass of a persistent character managed by RelayLM.

Produce only StateCandidate and ContinuityCandidate proposals for the supplied originating turn. There is no user-visible response in this pass.

Authority ordering is strict:
user/source evidence > accepted typed RelayLM State/Context/Continuity > assistant-response interpretation.
The supplied `assistant_response` is interpretive context only and must never self-certify a user fact, preference, goal, experience, external truth, prior event, or source provenance.

Use the exact existing State class/key vocabulary when the supplied accepted State already establishes it. Preserve correction, negation, supersession, uncertainty, degree, transient-vs-durable distinctions, and source provenance. Propose durable State only when current understanding meaningfully changes. Use Continuity for bounded referent/unresolved/active-task meaning rather than promoting short-lived dialogue state into durable State.
Never invent source Event IDs. Candidate sources must come from Event IDs present in the supplied `cognitive_input`; the assistant response itself is not a source Event.
A proposal has no authority merely because this pass emitted it; RelayLM validates all proposals deterministically.

Return only the required structured output."""

EXTRACTION_WIRE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["state_candidates", "continuity_candidates"],
    "properties": {
        "state_candidates": WIRE_SCHEMA["properties"]["state_candidates"],
        "continuity_candidates": WIRE_SCHEMA["properties"]["continuity_candidates"],
    },
}


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
                response.raise_for_status()
                async for data in _iter_sse_data(response):
                    if data == "[DONE]":
                        saw_done = True
                        break
                    content, finish_reason = _parse_stream_event(data)
                    if content is not None:
                        response_text += content
                        if content:
                            await emit_response_delta(content)
                    if finish_reason is not None:
                        saw_finish = True
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
        return CognitionConversationOutput(response=response_text)

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
        return _parse_extraction_completion(envelope)

    async def _post_two_pass(self, *, body: dict[str, Any]) -> Any:
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderProtocolError(f"upstream request failed: {exc}") from exc


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
            {"role": "system", "content": CONVERSATION_SYSTEM_INSTRUCTION},
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
    payload = {
        "cognitive_input": serialize_cognitive_input(extraction_input.cognitive_input),
        "assistant_response": extraction_input.assistant_response,
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "relaylm_structured_cognition_output",
                "strict": True,
                "schema": EXTRACTION_WIRE_SCHEMA,
            },
        },
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


def _parse_conversation_completion(envelope: Any) -> CognitionConversationOutput:
    content = _completion_content(envelope)
    if not content.strip():
        raise ProviderProtocolError("provider conversation content must not be empty")
    return CognitionConversationOutput(response=content)


def _parse_extraction_completion(envelope: Any) -> CognitionExtractionOutput:
    content = _completion_content(envelope)
    try:
        wire = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProviderProtocolError(
            "provider extraction content is not valid JSON"
        ) from exc
    if not isinstance(wire, dict) or set(wire) != {
        "state_candidates",
        "continuity_candidates",
    }:
        raise ProviderProtocolError(
            "extraction wire output must contain exactly state_candidates and "
            "continuity_candidates"
        )

    normalized = parse_wire_output(
        {
            "utterance": "internal extraction",
            "state_candidates": wire["state_candidates"],
            "continuity_candidates": wire["continuity_candidates"],
        }
    )
    return CognitionExtractionOutput(
        state_candidates=normalized.state_candidates,
        continuity_candidates=normalized.continuity_candidates,
    )


def _completion_content(envelope: Any) -> str:
    if not isinstance(envelope, dict):
        raise ProviderProtocolError("provider response must be an object")
    choices = envelope.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderProtocolError("provider response choices must be a non-empty array")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise ProviderProtocolError("provider choice must be an object")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ProviderProtocolError("provider message must be an object")
    content = message.get("content")
    if not isinstance(content, str):
        raise ProviderProtocolError("provider message content must be a string")
    return content
