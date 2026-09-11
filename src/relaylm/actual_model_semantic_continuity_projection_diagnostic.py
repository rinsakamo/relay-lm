"""Evaluation-only projection probe from formed epistemic meaning to Continuity IR.

This module holds semantic formation fixed and tests only the next model-facing
boundary: whether source-grounded observations that already exist can be mapped
into RelayLM's canonical Continuity candidate grammar.  It does not participate
in production cognition, lifecycle validation, materialization, or scoring.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Sequence
from typing import Any

from relaylm.actual_model_epistemic_formation_diagnostic import EpistemicFormationItem
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionCompletionMetadata,
    CognitionExtractionOutput,
    CognitionPassRequest,
    CognitionStructuredOutputMode,
)
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    WIRE_SCHEMA,
    _load_cognitive_wire_json,
    _parse_candidate_collections,
)
from relaylm.providers.openai_compatible_two_pass import _completion_content_and_metadata


PROJECTION_DIAGNOSTIC_NAME = "semantic-continuity-projection"
PROJECTION_SCHEMA_NAME = "relaylm_semantic_continuity_projection"
PROJECTION_CONDITION_ID = "semantic-continuity-projection-v1"

PROJECTION_SYSTEM_INSTRUCTION = (
    "You are running a narrow mapping test over supplied source-grounded semantic "
    "observations.\n"
    "The observations are empirical model-reported observations, not authoritative facts.\n"
    "Project only the supplied observations into the existing RelayLM Continuity candidate "
    "grammar. Do not discover additional meanings and do not emit State.\n"
    "Use only supplied evidence and return exactly the JSON object required by the schema."
)

PROJECTION_INSTRUCTION = """Map only the supplied formed epistemic observations into RelayLM Continuity candidates when justified by their meaning.

Canonical Continuity kinds:
- `referent`: a specific subject or entity that upcoming dialogue may refer back to.
- `unresolved`: an explicit open question or unknown value that remains to be resolved.
- `active_task`: an unfinished action, process, or goal expected to continue.

Canonical candidate fields:
- `kind`: one of `referent`, `unresolved`, `active_task`.
- `key`: a short stable semantic identity for the meaning; do not copy an evaluator key because none is supplied.
- `op`: `set` for a newly represented current meaning, or `resolve` only for an already represented meaning that the supplied evidence explicitly closes.
- `value`: the semantic value for `set`; null for `resolve`.
- `sources`: use only the supplied current input Event ID.
- `epistemic_role`: `user_assertion` for meaning explicitly established by the user input, `assistant_inference` for assistant-derived interpretation, or `assistant_commitment` for an assistant commitment.

Do not infer another observation, do not reconstruct a Pass 1 response, and do not add a candidate merely because a Continuity kind exists. If a supplied observation does not justify any canonical mapping, emit no candidate for it.

Return exactly one JSON object with `continuity_candidates` and no extra keys."""

PROJECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["continuity_candidates"],
    "properties": {
        "continuity_candidates": copy.deepcopy(
            WIRE_SCHEMA["properties"]["continuity_candidates"]
        )
    },
}


def _validated_observations(
    *,
    cognitive_input: CognitiveInput,
    observations: Sequence[EpistemicFormationItem],
) -> tuple[EpistemicFormationItem, ...]:
    if not isinstance(cognitive_input, CognitiveInput):
        raise TypeError("cognitive_input must be CognitiveInput")
    if not isinstance(observations, Sequence) or isinstance(observations, (str, bytes)):
        raise TypeError("observations must be a sequence of EpistemicFormationItem values")
    normalized = tuple(observations)
    if not normalized:
        raise ValueError("projection probe requires at least one formed observation")

    current_content = cognitive_input.input.payload.get("content")
    if not isinstance(current_content, str) or not current_content:
        raise ProviderProtocolError("current input Event must contain string payload.content")
    current_event_id = cognitive_input.input.id

    for index, observation in enumerate(normalized, start=1):
        if not isinstance(observation, EpistemicFormationItem):
            raise TypeError(
                f"projection observation {index} must be EpistemicFormationItem"
            )
        if observation.source_event_id != current_event_id:
            raise ProviderProtocolError(
                f"projection observation {index} source_event_id is not current input"
            )
        if observation.subject_span not in current_content:
            raise ProviderProtocolError(
                f"projection observation {index} subject_span is not an input substring"
            )
        if observation.unknown_evidence_span not in current_content:
            raise ProviderProtocolError(
                f"projection observation {index} unknown_evidence_span is not an input substring"
            )
    return normalized


def serialize_semantic_continuity_projection_input(
    *,
    cognitive_input: CognitiveInput,
    observations: Sequence[EpistemicFormationItem],
) -> dict[str, Any]:
    """Serialize only current evidence plus already formed source-grounded observations."""

    normalized = _validated_observations(
        cognitive_input=cognitive_input,
        observations=observations,
    )
    current_content = cognitive_input.input.payload["content"]
    return {
        "input": {
            "event_id": cognitive_input.input.id,
            "actor": cognitive_input.input.actor,
            "content": current_content,
        },
        "formed_epistemic_observations": [
            {
                "subject_span": observation.subject_span,
                "unknown_evidence_span": observation.unknown_evidence_span,
                "source_event_id": observation.source_event_id,
            }
            for observation in normalized
        ],
    }


def build_semantic_continuity_projection_request_body(
    *,
    provider: Any,
    cognitive_input: CognitiveInput,
    observations: Sequence[EpistemicFormationItem],
    pass_request: CognitionPassRequest,
) -> dict[str, Any]:
    """Build the exact native-schema projection request for current llama.cpp carriage."""

    if not isinstance(pass_request, CognitionPassRequest):
        raise TypeError("pass_request must be CognitionPassRequest")
    if pass_request.structured_output_mode is not CognitionStructuredOutputMode.NATIVE:
        raise ValueError("semantic Continuity projection requires native structured output")

    serialized_input = serialize_semantic_continuity_projection_input(
        cognitive_input=cognitive_input,
        observations=observations,
    )
    decoding, effective_reasoning = provider._resolve_llama_cpp_pass_request(
        pass_request=pass_request,
        reasoning_request=None,
    )
    serialized = json.dumps(
        serialized_input,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    body: dict[str, Any] = {
        "model": provider.model,
        "messages": [
            {"role": "system", "content": PROJECTION_SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": (
                    "<PROJECTION_INPUT>\n"
                    f"{serialized}\n"
                    "</PROJECTION_INPUT>\n\n"
                    f"{PROJECTION_INSTRUCTION}"
                ),
            },
        ],
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": PROJECTION_SCHEMA_NAME,
                "strict": True,
                "schema": PROJECTION_SCHEMA,
            },
        },
    }
    body.update(decoding.to_mapping())
    body.update(provider._llama_cpp_reasoning_fields(effective_reasoning))
    return body


def parse_semantic_continuity_projection_completion(
    *,
    envelope: Any,
    cognitive_input: CognitiveInput,
) -> CognitionExtractionOutput:
    """Parse one provider completion and apply only canonical mechanical checks."""

    content, completion = _completion_content_and_metadata(envelope)
    wire = _load_cognitive_wire_json(
        content,
        invalid_message="semantic Continuity projection content is not valid JSON",
    )
    return parse_semantic_continuity_projection_wire(
        wire=wire,
        cognitive_input=cognitive_input,
        completion=completion,
    )


def parse_semantic_continuity_projection_wire(
    *,
    wire: Any,
    cognitive_input: CognitiveInput,
    completion: CognitionCompletionMetadata | None = None,
) -> CognitionExtractionOutput:
    """Reuse canonical candidate parsing without making a semantic P1/P2 verdict."""

    if not isinstance(wire, dict) or set(wire) != {"continuity_candidates"}:
        raise ProviderProtocolError(
            "semantic Continuity projection must contain exactly continuity_candidates"
        )
    state_candidates, continuity_candidates = _parse_candidate_collections(
        raw_candidates=[],
        raw_continuity_candidates=wire["continuity_candidates"],
    )
    if state_candidates:
        raise AssertionError("projection parser unexpectedly produced State candidates")

    current_event_id = cognitive_input.input.id
    for index, candidate in enumerate(continuity_candidates):
        if any(source != current_event_id for source in candidate.sources):
            raise ProviderProtocolError(
                f"continuity_candidates[{index}].sources must use only current input Event ID"
            )

    return CognitionExtractionOutput(
        state_candidates=(),
        continuity_candidates=continuity_candidates,
        completion=completion or CognitionCompletionMetadata(),
    )
