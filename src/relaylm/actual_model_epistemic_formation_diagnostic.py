"""Evaluation-only T2 probe for source-grounded epistemic formation.

This module deliberately does not use the production cognition IR wire.  It
uses the repository's context compiler to select the preceding user event and
the current Stage R input, then sends only that bounded evidence to a native
JSON-Schema probe.  Semantic review is a later zero-generation boundary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from relaylm.context import compile_cognitive_input
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionCompletionMetadata,
    CognitionPassRequest,
    CognitionStructuredOutputMode,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    _load_cognitive_wire_json,
)
from relaylm.state import CanonicalState


DIAGNOSTIC_NAME = "epistemic-formation-t2"
DIAGNOSTIC_FORMAT_VERSION = 1
DIAGNOSTIC_SCHEMA_NAME = "relaylm_epistemic_formation_inventory"
DIAGNOSTIC_SCHEMA_VERSION = "relaylm-epistemic-formation-v1"
DIAGNOSTIC_CONDITION_ID = "stage-r-llama-cpp-epistemic-formation-t2-v1"
PRIMARY_SCENARIO_ID = "continuity-lifecycle-v1"
PRIMARY_TURN_INDEX = 2

# These strings are an intentionally small, provider-neutral instruction.  In
# particular, they do not name a Continuity kind, lifecycle operation, fixture
# object, fixture key, or expected transition.
EPISTEMIC_FORMATION_SYSTEM_INSTRUCTION = (
    "You are running a narrow evidence-bound inventory over a supplied current input.\n"
    "Identify any information or question that the current input itself explicitly leaves "
    "not yet known, determined, or answered.\n"
    "Use only supplied current input and context. Do not infer or invent missing facts.\n"
    "Return exactly the JSON object required by the schema."
)

EPISTEMIC_FORMATION_INSTRUCTION = (
    "Inspect the supplied current input. For each information or question that the current "
    "input itself explicitly leaves not yet known, determined, or answered, return one item.\n"
    "Use exact text from the current input for subject_span and unknown_evidence_span.\n"
    "Put the current input event ID in source_event_id.\n"
    "If none exists, return an empty items array.\n"
    "Use only supplied evidence. Do not infer or invent missing facts.\n"
    "Return exactly one JSON object with no extra keys."
)

EPISTEMIC_FORMATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "subject_span",
                    "unknown_evidence_span",
                    "source_event_id",
                ],
                "properties": {
                    "subject_span": {"type": "string", "minLength": 1},
                    "unknown_evidence_span": {"type": "string", "minLength": 1},
                    "source_event_id": {"type": "string", "minLength": 1},
                },
            },
        }
    },
}

# This schema is retained for the later human/independent zero-generation
# review artifact.  It is never sent as a model-facing schema.
EPISTEMIC_FORMATION_REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "format_version",
        "diagnostic",
        "raw_observation_artifact",
        "input_event_id",
        "mechanical_validation",
        "semantic_verdict",
        "review_basis",
    ],
    "properties": {
        "format_version": {"type": "integer", "const": DIAGNOSTIC_FORMAT_VERSION},
        "diagnostic": {"type": "string", "const": DIAGNOSTIC_NAME},
        "raw_observation_artifact": {"type": "string", "minLength": 1},
        "input_event_id": {"type": "string", "minLength": 1},
        "mechanical_validation": {"type": "string", "enum": ["pass", "fail"]},
        "semantic_verdict": {
            "type": "string",
            "enum": [
                "FORMATION_PRESENT",
                "FORMATION_ABSENT",
                "TRANSPORT_PROTOCOL_LIMITATION",
                "not_run",
            ],
        },
        "review_basis": {
            "type": "object",
            "additionalProperties": False,
            "required": ["generation_count", "subject_spans", "evidence_spans"],
            "properties": {
                "generation_count": {"type": "integer", "const": 0},
                "subject_spans": {"type": "array", "items": {"type": "string"}},
                "evidence_spans": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}


@dataclass(frozen=True, slots=True)
class EpistemicFormationItem:
    """One mechanically validated model-reported inventory item."""

    subject_span: str
    unknown_evidence_span: str
    source_event_id: str


@dataclass(frozen=True, slots=True)
class EpistemicFormationOutput:
    """Parsed output retained separately from the later semantic review."""

    items: tuple[EpistemicFormationItem, ...]
    raw_wire: dict[str, Any]
    completion: CognitionCompletionMetadata


def build_t2_epistemic_formation_input(
    *,
    identity: Identity,
    state: CanonicalState,
    scenario: Any,
    scenario_set_revision: str,
) -> CognitiveInput:
    """Construct the T2 input from the current Stage R scenario authority.

    The previous user event is retained as ordinary, provenance-bearing
    working context.  No accepted Continuity item, model-authored Pass 1
    response, T2 label, or T3 event is projected into the diagnostic input.
    """

    if getattr(scenario, "scenario_id", None) != PRIMARY_SCENARIO_ID:
        raise ValueError("epistemic formation probe requires continuity-lifecycle-v1")
    turns = getattr(scenario, "turns", None)
    if not isinstance(turns, tuple) or len(turns) != 3:
        raise ValueError("continuity-lifecycle-v1 must contain exactly three turns")
    if not isinstance(scenario_set_revision, str) or not scenario_set_revision.startswith(
        "sha256:"
    ):
        raise ValueError("scenario_set_revision must be the current sha256 authority")

    # Keep the fixture identity in the binding artifact, not in model-visible
    # provenance IDs; the body must not carry lifecycle vocabulary by accident.
    prefix = f"stage-r:{scenario_set_revision}:primary"
    previous_event = Event.create(
        type="message",
        actor="user",
        payload={"content": turns[0]},
        event_id=f"{prefix}:turn-1",
        timestamp="2026-01-01T00:00:01+00:00",
    )
    current_event = Event.create(
        type="message",
        actor="user",
        payload={"content": turns[1]},
        event_id=f"{prefix}:turn-2",
        timestamp="2026-01-01T00:00:02+00:00",
    )
    return compile_cognitive_input(
        identity=identity,
        state=state,
        current_event=current_event,
        recent_events=(previous_event,),
        # The probe tests formation before lifecycle projection.  Keeping this
        # None is intentional: the prior referential evidence is the T1 user
        # event, not a Continuity IR item.
        continuity_context=None,
    )


def serialize_epistemic_formation_input(cognitive_input: CognitiveInput) -> dict[str, Any]:
    """Serialize only current input and compiler-selected prior context."""

    content = cognitive_input.input.payload.get("content")
    if not isinstance(content, str) or not content:
        raise ProviderProtocolError("current input Event must contain string payload.content")
    context: list[dict[str, Any]] = []
    for item in cognitive_input.context:
        context_item: dict[str, Any] = {
            "content": item.content,
            "sources": list(item.sources),
        }
        if item.actor is not None:
            context_item["actor"] = item.actor
        context.append(context_item)
    return {
        "context": context,
        "input": {
            "event_id": cognitive_input.input.id,
            "actor": cognitive_input.input.actor,
            "content": content,
        },
    }


def build_epistemic_formation_request_body(
    *,
    provider: Any,
    cognitive_input: CognitiveInput,
    pass_request: CognitionPassRequest,
) -> dict[str, Any]:
    """Build the exact native-schema request without production prompt text."""

    if pass_request.structured_output_mode is not CognitionStructuredOutputMode.NATIVE:
        raise ValueError("epistemic formation probe requires native structured output")
    decoding, effective_reasoning = provider._resolve_llama_cpp_pass_request(
        pass_request=pass_request,
        reasoning_request=None,
    )
    serialized = json.dumps(
        serialize_epistemic_formation_input(cognitive_input),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    body: dict[str, Any] = {
        "model": provider.model,
        "messages": [
            {"role": "system", "content": EPISTEMIC_FORMATION_SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": (
                    "<CURRENT_INPUT>\n"
                    f"{serialized}\n"
                    "</CURRENT_INPUT>\n\n"
                    f"{EPISTEMIC_FORMATION_INSTRUCTION}"
                ),
            },
        ],
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": DIAGNOSTIC_SCHEMA_NAME,
                "strict": True,
                "schema": EPISTEMIC_FORMATION_SCHEMA,
            },
        },
    }
    body.update(decoding.to_mapping())
    body.update(provider._llama_cpp_reasoning_fields(effective_reasoning))
    return body


def parse_epistemic_formation_completion(
    *,
    envelope: Any,
    cognitive_input: CognitiveInput,
) -> EpistemicFormationOutput:
    """Parse and mechanically validate one raw native completion."""

    from relaylm.providers.openai_compatible_two_pass import (
        _completion_content_and_metadata,
    )

    content, completion = _completion_content_and_metadata(envelope)
    wire = _load_cognitive_wire_json(
        content,
        invalid_message="epistemic formation content is not valid JSON",
    )
    return parse_epistemic_formation_wire(
        wire=wire,
        cognitive_input=cognitive_input,
        completion=completion,
    )


def parse_epistemic_formation_wire(
    *,
    wire: Any,
    cognitive_input: CognitiveInput,
    completion: CognitionCompletionMetadata | None = None,
) -> EpistemicFormationOutput:
    """Apply only exact shape, event identity, and substring checks."""

    if not isinstance(wire, dict) or set(wire) != {"items"}:
        raise ProviderProtocolError(
            "epistemic formation wire must contain exactly items"
        )
    raw_items = wire["items"]
    if not isinstance(raw_items, list):
        raise ProviderProtocolError("epistemic formation items must be an array")
    current_content = cognitive_input.input.payload.get("content")
    current_event_id = cognitive_input.input.id
    if not isinstance(current_content, str):
        raise ProviderProtocolError("current input content is not a string")

    parsed: list[EpistemicFormationItem] = []
    for index, raw_item in enumerate(raw_items, start=1):
        if not isinstance(raw_item, dict) or set(raw_item) != {
            "subject_span",
            "unknown_evidence_span",
            "source_event_id",
        }:
            raise ProviderProtocolError(
                f"epistemic formation item {index} fields are not exact"
            )
        subject_span = raw_item["subject_span"]
        evidence_span = raw_item["unknown_evidence_span"]
        source_event_id = raw_item["source_event_id"]
        if not all(
            isinstance(value, str) and bool(value)
            for value in (subject_span, evidence_span, source_event_id)
        ):
            raise ProviderProtocolError(
                f"epistemic formation item {index} fields must be non-empty strings"
            )
        if source_event_id != current_event_id:
            raise ProviderProtocolError(
                f"epistemic formation item {index} source_event_id is not current input"
            )
        if subject_span not in current_content:
            raise ProviderProtocolError(
                f"epistemic formation item {index} subject_span is not an input substring"
            )
        if evidence_span not in current_content:
            raise ProviderProtocolError(
                f"epistemic formation item {index} unknown_evidence_span is not an input substring"
            )
        parsed.append(
            EpistemicFormationItem(
                subject_span=subject_span,
                unknown_evidence_span=evidence_span,
                source_event_id=source_event_id,
            )
        )

    return EpistemicFormationOutput(
        items=tuple(parsed),
        raw_wire=json.loads(json.dumps(wire, ensure_ascii=False)),
        completion=completion or CognitionCompletionMetadata(),
    )


def completion_metadata_mapping(
    completion: CognitionCompletionMetadata,
) -> dict[str, int | str | None]:
    return {
        "finish_reason": completion.finish_reason,
        "prompt_tokens": completion.prompt_tokens,
        "completion_tokens": completion.completion_tokens,
        "total_tokens": completion.total_tokens,
        "reasoning_tokens": completion.reasoning_tokens,
    }


def raw_observation_mapping(
    *,
    cognitive_input: CognitiveInput,
    content: str,
    completion: CognitionCompletionMetadata,
    request_body_artifact: str,
) -> dict[str, Any]:
    """Create the raw artifact before parsing or semantic review."""

    current_content = cognitive_input.input.payload.get("content")
    if not isinstance(current_content, str):
        raise ProviderProtocolError("current input content is not a string")
    return {
        "format_version": DIAGNOSTIC_FORMAT_VERSION,
        "diagnostic": DIAGNOSTIC_NAME,
        "request_body_artifact": request_body_artifact,
        "input": {
            "event_id": cognitive_input.input.id,
            "content": current_content,
        },
        "raw_completion": {
            "content": content,
            "completion": completion_metadata_mapping(completion),
        },
        "semantic_review": "not_run",
    }
