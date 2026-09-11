from __future__ import annotations

import copy
import json

import pytest

from relaylm.actual_model_epistemic_formation_diagnostic import EpistemicFormationItem
from relaylm.actual_model_semantic_continuity_projection_diagnostic import (
    PROJECTION_INSTRUCTION,
    PROJECTION_SCHEMA,
    PROJECTION_SCHEMA_NAME,
    PROJECTION_SYSTEM_INSTRUCTION,
    build_semantic_continuity_projection_request_body,
    parse_semantic_continuity_projection_wire,
    serialize_semantic_continuity_projection_input,
)
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError, WIRE_SCHEMA
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.state import STATE_CLASS_DEFINITIONS


FORBIDDEN_FIXTURE_TERMS = (
    "机",
    "青い箱",
    "box_contents_question",
    "それの中身は何だと思う？まだ開けていないから、答えは未解決のままにして。",
)


class _BodyProvider:
    model = "gemma-local"

    def _resolve_llama_cpp_pass_request(self, *, pass_request, reasoning_request):
        assert reasoning_request is None
        assert pass_request.reasoning_mode is CognitionReasoningMode.OFF
        assert pass_request.structured_output_mode is CognitionStructuredOutputMode.NATIVE
        return (
            OpenAICompatibleDecodingConfig(
                temperature=pass_request.temperature,
                top_p=pass_request.top_p,
            ),
            OpenAICompatibleReasoningRequest(mode="off", token_budget=None),
        )

    def _llama_cpp_reasoning_fields(self, request):
        assert request is not None
        assert request.mode == "off"
        assert request.token_budget is None
        return {"reasoning_effort": "none"}


def _input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# Test\nBe precise."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "What is inside it? The answer is still unknown."},
            event_id="evt-current",
            timestamp="2026-09-11T00:00:00+00:00",
        ),
    )


def _observation() -> EpistemicFormationItem:
    return EpistemicFormationItem(
        subject_span="What is inside it?",
        unknown_evidence_span="The answer is still unknown.",
        source_event_id="evt-current",
    )


def test_projection_instruction_and_schema_are_fixture_independent() -> None:
    prompt = f"{PROJECTION_SYSTEM_INSTRUCTION}\n{PROJECTION_INSTRUCTION}"
    schema_text = json.dumps(PROJECTION_SCHEMA, ensure_ascii=False)
    for term in FORBIDDEN_FIXTURE_TERMS:
        assert term not in prompt
        assert term not in schema_text

    assert set(PROJECTION_SCHEMA["properties"]) == {"continuity_candidates"}
    assert PROJECTION_SCHEMA["properties"]["continuity_candidates"] == copy.deepcopy(
        WIRE_SCHEMA["properties"]["continuity_candidates"]
    )
    assert "state_candidates" not in schema_text
    assert "PASS_1" not in prompt


def test_projection_input_preserves_only_current_event_and_formed_observation() -> None:
    serialized = serialize_semantic_continuity_projection_input(
        cognitive_input=_input(),
        observations=(_observation(),),
    )
    assert set(serialized) == {"input", "formed_epistemic_observations"}
    assert serialized["input"] == {
        "event_id": "evt-current",
        "actor": "user",
        "content": "What is inside it? The answer is still unknown.",
    }
    assert serialized["formed_epistemic_observations"] == [
        {
            "subject_span": "What is inside it?",
            "unknown_evidence_span": "The answer is still unknown.",
            "source_event_id": "evt-current",
        }
    ]


def test_projection_observation_grounding_fails_closed_before_request() -> None:
    wrong_source = EpistemicFormationItem(
        subject_span="What is inside it?",
        unknown_evidence_span="The answer is still unknown.",
        source_event_id="evt-other",
    )
    with pytest.raises(ProviderProtocolError, match="source_event_id"):
        serialize_semantic_continuity_projection_input(
            cognitive_input=_input(),
            observations=(wrong_source,),
        )

    wrong_span = EpistemicFormationItem(
        subject_span="not present",
        unknown_evidence_span="The answer is still unknown.",
        source_event_id="evt-current",
    )
    with pytest.raises(ProviderProtocolError, match="subject_span"):
        serialize_semantic_continuity_projection_input(
            cognitive_input=_input(),
            observations=(wrong_span,),
        )


def test_request_is_native_reasoning_off_without_state_or_pass1() -> None:
    body = build_semantic_continuity_projection_request_body(
        provider=_BodyProvider(),
        cognitive_input=_input(),
        observations=(_observation(),),
        pass_request=CognitionPassRequest(
            reasoning_mode=CognitionReasoningMode.OFF,
            structured_output_mode=CognitionStructuredOutputMode.NATIVE,
        ),
    )
    assert body["reasoning_effort"] == "none"
    assert body["stream"] is False
    assert body["response_format"]["json_schema"]["name"] == PROJECTION_SCHEMA_NAME
    assert body["response_format"]["json_schema"]["schema"] == PROJECTION_SCHEMA
    request_text = json.dumps(body, ensure_ascii=False)
    assert "state_candidates" not in request_text
    assert "PASS_1_RESPONSE" not in request_text
    for term in FORBIDDEN_FIXTURE_TERMS:
        assert term not in request_text


def test_projection_wire_reuses_canonical_candidate_parser() -> None:
    wire = {
        "continuity_candidates": [
            {
                "kind": "unresolved",
                "key": "inside_question",
                "op": "set",
                "value": "The contents remain unknown.",
                "sources": ["evt-current"],
                "epistemic_role": "user_assertion",
            }
        ]
    }
    output = parse_semantic_continuity_projection_wire(
        wire=wire,
        cognitive_input=_input(),
    )
    assert output.state_candidates == ()
    assert len(output.continuity_candidates) == 1
    candidate = output.continuity_candidates[0]
    assert candidate.kind == "unresolved"
    assert candidate.key == "inside_question"
    assert candidate.op == "set"
    assert candidate.sources == ("evt-current",)
    assert candidate.epistemic_role == "user_assertion"


def test_projection_wire_rejects_extra_top_level_and_noncurrent_sources() -> None:
    with pytest.raises(ProviderProtocolError, match="exactly continuity_candidates"):
        parse_semantic_continuity_projection_wire(
            wire={"continuity_candidates": [], "extra": True},
            cognitive_input=_input(),
        )

    wrong_source = {
        "continuity_candidates": [
            {
                "kind": "unresolved",
                "key": "inside_question",
                "op": "set",
                "value": "The contents remain unknown.",
                "sources": ["evt-other"],
                "epistemic_role": "user_assertion",
            }
        ]
    }
    with pytest.raises(ProviderProtocolError, match="current input Event ID"):
        parse_semantic_continuity_projection_wire(
            wire=wrong_source,
            cognitive_input=_input(),
        )
