from __future__ import annotations

import json
import math
from typing import Any, Mapping

import httpx

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.state import STATE_CLASS_DEFINITIONS, StateCandidate

SYSTEM_INSTRUCTION = """You are the cognitive substrate of a persistent character managed by RelayLM.

Use the supplied CognitiveInput JSON to respond naturally as the character and propose meaningful state changes.

Identity is authoritative and immutable.
State represents accepted current understanding.
Context contains RelayLM-prepared information relevant to this turn. Context may include recent user- or assistant-authored dialogue; preserve its actor provenance.
Input is the current event.

Do not invent history, evidence, motives, or supporting details.
Assistant-authored Context supports conversational continuity only. It never proves a user fact, preference, goal, experience, or external event merely because the assistant said it before.
User-authored Context is evidence of what the user said, with the temporal and semantic limits of that utterance; it is not automatically timeless external truth.
Do not imply prior interactions, shared history, relationship development, or prior feelings unless explicitly supported by accepted State or provenance-bearing Context.
You may react emotionally to the current Input, but do not describe that reaction as pre-existing unless supported by State or Context.
Preserve uncertainty, degree, and direction expressed by the user.
Propose State only when current understanding meaningfully changes.
Use set when State should currently exist and remove only for explicit revocation/cancellation/denial/correction.
Do not remove State for mere weakening, uncertainty, hesitation, or temporary variation.
For a set value, normally use a plain string. When the current Input materially expresses a useful comparative or intensity relation, you may instead use {"semantic": "...", "degree_hint": 0.0..1.0}. The degree is only a soft relative semantic hint, not confidence, probability, evidence strength, authority, relevance, salience, or a removal threshold. Compare degree hints only on compatible semantic axes. Do not add false precision. If accepted State already carries an adequate degree hint and the current Input does not materially change the strength/comparison, do not re-estimate it merely to produce a new number.
Never invent source Event IDs.
Preserve user-provided names and proper-noun spelling.
Normally use the user's language.

Return only the required structured output."""

PROVIDER_WIRE_INSTRUCTION = """Provider wire requirements:
- `utterance` is the complete non-empty natural-language reply shown to the user. Do not put JSON framing text in `utterance`.
- `state_candidates` is an array of internal State proposals.
- Every wire candidate includes `state_class`, `key`, `op`, `value`, and `sources`.
- For `set`, `value` is either a non-null string or exactly {`semantic`: non-empty string, `degree_hint`: finite number from 0.0 through 1.0}.
- For `remove`, `value` is null and is normalized away by the adapter.
- Use only Event IDs present in the supplied CognitiveInput."""

DEGREE_HINT_VALUE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["semantic", "degree_hint"],
    "properties": {
        "semantic": {"type": "string", "minLength": 1},
        "degree_hint": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
}

WIRE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["utterance", "state_candidates"],
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
    },
}


class ProviderProtocolError(RuntimeError):
    """Upstream provider failed to return a valid RelayLM cognitive result."""


class OpenAICompatibleProvider:
    """OpenAI Chat Completions adapter for a complete structured cognitive turn."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 120.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("provider base_url must not be empty")
        if not model.strip():
            raise ValueError("provider model must not be empty")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self._client = http_client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = http_client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        request_body = {
            "model": self.model,
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
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "relaylm_cognitive_output",
                    "strict": True,
                    "schema": WIRE_SCHEMA,
                },
            },
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=request_body,
            )
            response.raise_for_status()
            envelope = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderProtocolError(f"upstream request failed: {exc}") from exc

        return parse_chat_completion(envelope)


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
        "input": {
            "event_id": cognitive_input.input.id,
            "actor": cognitive_input.input.actor,
            "content": content,
        },
    }


def parse_chat_completion(envelope: Any) -> CognitiveOutput:
    try:
        choices = _mapping(envelope, "provider response")["choices"]
        if not isinstance(choices, list) or not choices:
            raise ProviderProtocolError("provider response choices must be a non-empty array")
        message = _mapping(choices[0], "provider choice")["message"]
        content = _mapping(message, "provider message")["content"]
    except KeyError as exc:
        raise ProviderProtocolError(f"provider response missing field: {exc.args[0]}") from exc

    if not isinstance(content, str):
        raise ProviderProtocolError("provider message content must be a JSON string")
    try:
        wire = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProviderProtocolError("provider message content is not valid JSON") from exc
    return parse_wire_output(wire)


def parse_wire_output(wire: Any) -> CognitiveOutput:
    wire = _mapping(wire, "cognitive wire output")
    utterance = wire.get("utterance")
    if not isinstance(utterance, str) or not utterance.strip():
        raise ProviderProtocolError("wire utterance must be a non-empty string")
    raw_candidates = wire.get("state_candidates")
    if not isinstance(raw_candidates, list):
        raise ProviderProtocolError("wire state_candidates must be an array")

    candidates: list[StateCandidate] = []
    for index, raw in enumerate(raw_candidates):
        candidate = _mapping(raw, f"state_candidates[{index}]")
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
        if "value" not in candidate:
            raise ProviderProtocolError(f"state_candidates[{index}] missing value")
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

    return CognitiveOutput(response=utterance, state_candidates=tuple(candidates))


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
