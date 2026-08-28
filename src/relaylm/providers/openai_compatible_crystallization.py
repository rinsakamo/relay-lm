from __future__ import annotations

import json
import math
from typing import Any, Mapping

import httpx

from relaylm.crystallization import CrystallizationInput, CrystallizationOutput
from relaylm.memory_provenance import (
    MemoryProvenanceSource,
    MemoryProvenanceSourceKind,
    MemoryTemporalScope,
    MemoryUnit,
)
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    _reject_duplicate_json_members,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.state import STATE_CLASS_DEFINITIONS, StateCandidate


SYSTEM_INSTRUCTION = """You are the off-turn memory crystallizer for RelayLM.

Perform long-horizon semantic consolidation over the supplied Identity, Canonical State, bounded persisted Events, and optional prior MEMORY.md. Produce durable portable Markdown memory; do not merely summarize the recent conversation chronologically.

Identity is authoritative and immutable.
Canonical State is the accepted current machine understanding, not irreversible truth.
Events are occurrence/provenance evidence and preserve actor authority.
Prior MEMORY.md is readable prior synthesis, not Event evidence and not Canonical State authority.

Preserve corrections, supersession, uncertainty, comparative meaning, and current-versus-historical distinctions. When later user evidence clearly corrects an earlier understanding, represent the corrected current understanding without erasing the historical occurrence. Do not flatten historical and current claims into one timeless statement.

Assistant-authored Events may support the character's own conversational history, but assistant-authored Events never certify user facts, preferences, goals, experiences, or external facts merely because the assistant said them. User-authored Events are evidence of what the user said at that occurrence, subject to temporal and semantic scope.

Prefer durable information that can matter across later conversations. Do not promote short-lived referents, unresolved questions, or active tasks into durable memory merely because they are recent. Avoid redundant durable concepts and duplicate aliases when the evidence permits one coherent representation.

When Canonical State already represents the same concept, reuse its exact `state_class + key` if you need to propose a correction. Emit a State candidate only when accepted current understanding genuinely needs a supported change; otherwise emit no State candidate. A State candidate remains only a proposal and will be checked by RelayLM's deterministic Validator.

When Canonical State contains a temporary active task or goal and later user Event evidence explicitly establishes completion, cancellation, or that it should no longer remain a future goal, do not replace its active value with durable semantic `completed`. If corrective State output is warranted, prefer `remove` for that exact existing `state_class + key`; preserve the Event history, and omit short-lived task mechanics from long-horizon MEMORY unless the event has independently durable significance.

When correcting an existing exact `state_class + key`, preserve the existing plain-string versus degree-hint representation form unless supplied current evidence materially requires new or changed comparative/intensity semantics. Never introduce `degree_hint` as confidence, evidence strength, importance, or stylistic emphasis. Avoid false precision. A categorical current-value correction represented adequately by a string should remain a string unless actual semantic evidence requires a graded representation.

Never invent Event IDs. State-candidate `sources` may use only Event IDs present in the supplied `events` array. State IDs, Markdown headings, MEMORY locations, and prior MEMORY prose are not Event sources.

MEMORY is proposed as structured semantic units, not as model-authored Markdown. Each unit contains only `heading`, human-readable `content`, `temporal_scope` (`current`, `historical`, or `unknown`), and typed `sources` whose references may name supplied Event IDs or State IDs. Do not emit `memory_id`, `derivation_id`, or `relaylm-memory` control comments. RelayLM derives stable metadata only from canonical supplied State/Event authority and renders the final portable MEMORY.md. If current/historical classification or canonical source identity is not supported, leave the unit unknown rather than guessing from prose, dates, tense, or Markdown layout.

Organize MEMORY around stable semantic units rather than transient wording or arbitrary heading choices. When current and historical aspects of one concept are both durable, keep their semantic units and stable logical identities coherent across updates; do not split or merge them solely because of Markdown organization. RelayLM, not the model, derives those identities from canonical typed sources. Propose only genuinely durable units; RelayLM evaluates each proposal independently and does not use a deterministic temporary-task classifier.

Preserve user-provided names and proper-noun spelling. Keep Markdown readable to a human and useful in Obsidian-compatible files.

Return only the required structured output."""

PROVIDER_WIRE_INSTRUCTION = """Provider wire requirements:
- `memory_units` is a non-empty array of semantic MEMORY unit proposals.
- Each MEMORY unit contains exactly `heading`, `content`, `temporal_scope`, and `sources`.
- Do not emit `memory_id`, `derivation_id`, or `relaylm-memory` control comments; RelayLM owns metadata and Markdown projection.
- `heading` and `content` are human-readable proposal text, not machine identity.
- `sources` contains typed `event` or `state` references; do not invent IDs.
- `state_candidates` is an array of optional corrective State proposals.
- Every State wire candidate contains exactly `state_class`, `key`, `op`, `value`, and `sources`.
- `state_class` uses the RelayLM State class registry described below.
- For State `set`, `value` is either a non-null string or exactly {`semantic`: non-empty string, `degree_hint`: finite number from 0.0 through 1.0}.
- For State `remove`, `value` is null and is normalized away by the adapter.
- Candidate `sources` is a non-empty array containing only Event IDs present in the supplied `events` array.
- There is no Continuity proposal channel in crystallization output.

State class registry:
""" + "\n".join(
    f"- `{state_class}`: {definition}"
    for state_class, definition in STATE_CLASS_DEFINITIONS.items()
)

DEGREE_HINT_VALUE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["semantic", "degree_hint"],
    "properties": {
        "semantic": {"type": "string", "minLength": 1},
        "degree_hint": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
}


def _state_candidate_wire_branch(
    *,
    op: str,
    value_schema: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["state_class", "key", "op", "value", "sources"],
        "properties": {
            "state_class": {"type": "string", "enum": list(STATE_CLASS_DEFINITIONS)},
            "key": {"type": "string", "minLength": 1},
            "op": {"type": "string", "enum": [op]},
            "value": value_schema,
            "sources": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "minLength": 1},
            },
        },
    }


STATE_CANDIDATE_WIRE_SCHEMA: dict[str, Any] = {
    "anyOf": [
        _state_candidate_wire_branch(
            op="set",
            value_schema={
                "anyOf": [
                    {"type": "string"},
                    DEGREE_HINT_VALUE_SCHEMA,
                ]
            },
        ),
        _state_candidate_wire_branch(
            op="remove",
            value_schema={"type": "null"},
        ),
    ],
}

MEMORY_UNIT_WIRE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["heading", "content", "temporal_scope", "sources"],
    "properties": {
        "heading": {"type": "string", "minLength": 1},
        "content": {"type": "string", "minLength": 1},
        "temporal_scope": {
            "type": "string",
            "enum": [scope.value for scope in MemoryTemporalScope],
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "reference_id"],
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [kind.value for kind in MemoryProvenanceSourceKind],
                    },
                    "reference_id": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}

WIRE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["memory_units", "state_candidates"],
    "properties": {
        "memory_units": {
            "type": "array",
            "minItems": 1,
            "items": MEMORY_UNIT_WIRE_SCHEMA,
        },
        "state_candidates": {
            "type": "array",
            "items": STATE_CANDIDATE_WIRE_SCHEMA,
        },
    },
}


class OpenAICompatibleCrystallizer:
    """Non-streaming OpenAI Chat Completions adapter for one off-turn consolidation pass."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 120.0,
        decoding_config: OpenAICompatibleDecodingConfig | None = None,
        decoding_capabilities: OpenAICompatibleDecodingCapabilities | None = None,
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
        self._client = http_client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = http_client is None

    @property
    def effective_decoding_configuration(self) -> dict[str, int | float]:
        """Exact content-free decoding fields carried on every crystallization request."""

        return self.decoding_config.to_mapping()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def generate(
        self, crystallization_input: CrystallizationInput
    ) -> CrystallizationOutput:
        allowed_source_ids = frozenset(event.id for event in crystallization_input.events)
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=_request_body(
                    model=self.model,
                    crystallization_input=crystallization_input,
                    decoding_config=self.decoding_config,
                ),
            )
            response.raise_for_status()
            envelope = json.loads(
                response.content,
                object_pairs_hook=_reject_duplicate_json_members,
            )
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise ProviderProtocolError(f"upstream crystallization request failed: {exc}") from exc

        return parse_crystallization_chat_completion(
            envelope,
            allowed_source_ids=allowed_source_ids,
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def _request_body(
    *,
    model: str,
    crystallization_input: CrystallizationInput,
    decoding_config: OpenAICompatibleDecodingConfig | None = None,
) -> dict[str, Any]:
    if decoding_config is not None and not isinstance(
        decoding_config, OpenAICompatibleDecodingConfig
    ):
        raise TypeError("decoding_config must be OpenAICompatibleDecodingConfig or None")

    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": f"{SYSTEM_INSTRUCTION}\n\n{PROVIDER_WIRE_INSTRUCTION}",
            },
            {
                "role": "user",
                "content": json.dumps(
                    serialize_crystallization_input(crystallization_input),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                ),
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "relaylm_crystallization_output",
                "strict": True,
                "schema": WIRE_SCHEMA,
            },
        },
        "stream": False,
    }
    if decoding_config is not None:
        body.update(decoding_config.to_mapping())
    return body


def serialize_crystallization_input(
    crystallization_input: CrystallizationInput,
) -> dict[str, Any]:
    return {
        "identity": {"content": crystallization_input.identity.content},
        "state": [
            {
                "state_id": record.state_id,
                "state_class": record.state_class,
                "key": record.key,
                "value": record.value,
                "sources": list(record.sources),
                "status": record.status,
                "valid_from": record.valid_from,
                "valid_to": record.valid_to,
            }
            for record in crystallization_input.state.states
        ],
        "events": [
            {
                "id": event.id,
                "type": event.type,
                "actor": event.actor,
                "timestamp": event.timestamp,
                "payload": event.payload,
            }
            for event in crystallization_input.events
        ],
        "prior_memory": crystallization_input.prior_memory,
    }


def parse_crystallization_chat_completion(
    envelope: Any,
    *,
    allowed_source_ids: frozenset[str],
) -> CrystallizationOutput:
    try:
        choices = _mapping(envelope, "provider crystallization response")["choices"]
        if not isinstance(choices, list) or not choices:
            raise ProviderProtocolError(
                "provider crystallization response choices must be a non-empty array"
            )
        message = _mapping(choices[0], "provider crystallization choice")["message"]
        content = _mapping(message, "provider crystallization message")["content"]
    except KeyError as exc:
        raise ProviderProtocolError(
            f"provider crystallization response missing field: {exc.args[0]}"
        ) from exc

    if not isinstance(content, str):
        raise ProviderProtocolError(
            "provider crystallization message content must be a JSON string"
        )
    try:
        wire = json.loads(
            content,
            object_pairs_hook=_reject_duplicate_json_members,
        )
    except json.JSONDecodeError as exc:
        raise ProviderProtocolError(
            "provider crystallization message content is not valid JSON"
        ) from exc

    return parse_crystallization_wire_output(
        wire,
        allowed_source_ids=allowed_source_ids,
    )


def parse_crystallization_wire_output(
    wire: Any,
    *,
    allowed_source_ids: frozenset[str],
) -> CrystallizationOutput:
    wire = _mapping(wire, "crystallization wire output")
    if set(wire) != {"memory_units", "state_candidates"}:
        raise ProviderProtocolError(
            "crystallization wire output must contain exactly memory_units and state_candidates"
        )

    raw_units = wire.get("memory_units")
    if not isinstance(raw_units, list) or not raw_units:
        raise ProviderProtocolError("wire memory_units must be a non-empty array")
    memory_units = tuple(
        _parse_memory_unit(raw, index=index)
        for index, raw in enumerate(raw_units)
    )

    raw_candidates = wire.get("state_candidates")
    if not isinstance(raw_candidates, list):
        raise ProviderProtocolError("wire state_candidates must be an array")

    candidates = tuple(
        _parse_state_candidate(
            raw,
            index=index,
            allowed_source_ids=allowed_source_ids,
        )
        for index, raw in enumerate(raw_candidates)
    )
    return CrystallizationOutput(
        memory_units=memory_units,
        state_candidates=candidates,
    )


def _parse_memory_unit(raw: Any, *, index: int) -> MemoryUnit:
    unit = _mapping(raw, f"memory_units[{index}]")
    expected_keys = {"heading", "content", "temporal_scope", "sources"}
    if set(unit) != expected_keys:
        raise ProviderProtocolError(
            f"memory_units[{index}] must contain exactly heading, content, temporal_scope, and sources"
        )
    heading = unit.get("heading")
    content = unit.get("content")
    temporal_scope = unit.get("temporal_scope")
    if not isinstance(heading, str) or not heading.strip():
        raise ProviderProtocolError(f"memory_units[{index}].heading must be a non-empty string")
    if not isinstance(content, str) or not content.strip():
        raise ProviderProtocolError(f"memory_units[{index}].content must be a non-empty string")
    try:
        scope = MemoryTemporalScope(temporal_scope)
    except (TypeError, ValueError) as exc:
        raise ProviderProtocolError(
            f"memory_units[{index}].temporal_scope must be current, historical, or unknown"
        ) from exc
    raw_sources = unit.get("sources")
    if not isinstance(raw_sources, list):
        raise ProviderProtocolError(f"memory_units[{index}].sources must be an array")
    sources: list[MemoryProvenanceSource] = []
    for source_index, raw_source in enumerate(raw_sources):
        source = _mapping(raw_source, f"memory_units[{index}].sources[{source_index}]")
        if set(source) != {"kind", "reference_id"}:
            raise ProviderProtocolError(
                f"memory_units[{index}].sources[{source_index}] must contain exactly kind and reference_id"
            )
        kind = source.get("kind")
        reference_id = source.get("reference_id")
        try:
            typed_kind = MemoryProvenanceSourceKind(kind)
            sources.append(
                MemoryProvenanceSource(
                    kind=typed_kind,
                    reference_id=reference_id,
                )
            )
        except (TypeError, ValueError) as exc:
            raise ProviderProtocolError(
                f"memory_units[{index}].sources[{source_index}] must contain a valid typed reference"
            ) from exc
    try:
        return MemoryUnit(
            heading=heading,
            content=content,
            temporal_scope=scope,
            sources=tuple(sources),
        )
    except (TypeError, ValueError) as exc:
        raise ProviderProtocolError(f"memory_units[{index}] is invalid: {exc}") from exc


def _parse_state_candidate(
    raw: Any,
    *,
    index: int,
    allowed_source_ids: frozenset[str],
) -> StateCandidate:
    candidate = _mapping(raw, f"state_candidates[{index}]")
    expected_keys = {"state_class", "key", "op", "value", "sources"}
    if set(candidate) != expected_keys:
        raise ProviderProtocolError(
            f"state_candidates[{index}] must contain exactly state_class, key, op, value, and sources"
        )

    state_class = _required_string(candidate, "state_class", index)
    if state_class not in STATE_CLASS_DEFINITIONS:
        raise ProviderProtocolError(
            f"state_candidates[{index}] unsupported state_class: {state_class}"
        )
    key = _required_string(candidate, "key", index)
    op = _required_string(candidate, "op", index)

    sources = candidate.get("sources")
    if not isinstance(sources, list) or not sources or not all(
        isinstance(source, str) and source.strip() for source in sources
    ):
        raise ProviderProtocolError(
            f"state_candidates[{index}].sources must be non-empty strings"
        )
    unknown_sources = sorted(set(sources) - allowed_source_ids)
    if unknown_sources:
        raise ProviderProtocolError(
            f"state_candidates[{index}].sources contain Event IDs absent from crystallization input: "
            + ", ".join(unknown_sources)
        )

    if op == "set":
        value = _parse_set_value(candidate["value"], index)
        return StateCandidate.set(
            state_class=state_class,
            key=key,
            value=value,
            sources=tuple(sources),
        )
    if op == "remove":
        if candidate["value"] is not None:
            raise ProviderProtocolError(
                f"state_candidates[{index}] remove value must be null"
            )
        return StateCandidate.remove(
            state_class=state_class,
            key=key,
            sources=tuple(sources),
        )
    raise ProviderProtocolError(f"state_candidates[{index}] unsupported op: {op}")


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
