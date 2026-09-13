from __future__ import annotations

import json
from typing import Any

from relaylm.cognitive import CognitiveInput, ContextItem, EventEvidenceItem
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import serialize_cognitive_input
from relaylm.providers.openai_compatible_two_pass import (
    COMMON_SYSTEM_INSTRUCTION,
    _conversation_request_body,
    _extraction_request_body,
)
from relaylm.state import STATE_CLASS_DEFINITIONS, StateRecord


_ORIGINAL_INPUT = 'Keep the café label "XR-17/β" as the same reference next turn.'


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("Synthetic lexical-fidelity identity."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(
            StateRecord(
                state_id="state-1",
                state_class="user.preference",
                key="coffee",
                value="likes",
                sources=("state-event",),
            ),
        ),
        context=(
            ContextItem(
                content="A prior user message.",
                sources=("context-event",),
                actor="user",
            ),
        ),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": _ORIGINAL_INPUT},
            event_id="input-event",
            timestamp="2026-01-01T00:00:00+00:00",
        ),
        event_evidence=(
            EventEvidenceItem(
                event_id="evidence-event",
                event_type="message",
                actor="user",
                timestamp="2025-12-31T00:00:00+00:00",
                content="Recorded label evidence.",
            ),
        ),
    )


def _cognitive_payload(content: str) -> dict[str, Any]:
    start_marker = "<COGNITIVE_INPUT>\n"
    end_marker = "\n</COGNITIVE_INPUT>"
    start = content.index(start_marker) + len(start_marker)
    end = content.index(end_marker, start)
    payload = json.loads(content[start:end])
    assert isinstance(payload, dict)
    return payload


def _request_bodies() -> tuple[dict[str, Any], dict[str, Any]]:
    cognitive_input = _cognitive_input()
    conversation = _conversation_request_body(
        model="synthetic-model",
        cognitive_input=cognitive_input,
        stream=False,
        decoding={"temperature": 0, "top_p": 1},
    )
    extraction = _extraction_request_body(
        model="synthetic-model",
        extraction_input=CognitionExtractionInput(
            cognitive_input=cognitive_input,
            assistant_response="The label remains the same reference.",
        ),
        decoding={"temperature": 0, "top_p": 1},
        lifecycle_channel_separation=True,
    )
    return conversation, extraction


def _request_contents() -> tuple[str, str]:
    conversation, extraction = _request_bodies()
    conversation_content = conversation["messages"][1]["content"]
    extraction_content = extraction["messages"][1]["content"]
    assert isinstance(conversation_content, str)
    assert isinstance(extraction_content, str)
    return conversation_content, extraction_content


def _request_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    conversation_content, extraction_content = _request_contents()
    return (
        _cognitive_payload(conversation_content),
        _cognitive_payload(extraction_content),
    )


def test_canonical_serialization_has_no_model_facing_lexical_source() -> None:
    serialized = serialize_cognitive_input(_cognitive_input())

    assert "current_input_lexical_source" not in serialized
    assert serialized["input"]["event_id"] == "input-event"
    assert serialized["state"][0]["sources"] == ["state-event"]
    assert serialized["context"][0]["sources"] == ["context-event"]
    assert serialized["event_evidence"][0]["event_id"] == "evidence-event"


def test_pass1_and_pass2_expose_exact_lexical_source_with_alias_provenance() -> None:
    conversation, extraction = _request_payloads()

    for payload in (conversation, extraction):
        assert payload["current_input_lexical_source"] == {"content": _ORIGINAL_INPUT}
        assert set(payload["current_input_lexical_source"]) == {"content"}
        assert payload["input"]["event_id"] == "E0"
        assert payload["state"][0]["sources"] == ["E1"]
        assert payload["context"][0]["sources"] == ["E2"]
        assert payload["event_evidence"][0]["event_id"] == "E3"

        provenance_ids = (
            payload["input"]["event_id"],
            *payload["state"][0]["sources"],
            *payload["context"][0]["sources"],
            payload["event_evidence"][0]["event_id"],
        )
        assert provenance_ids == ("E0", "E1", "E2", "E3")
        assert "input-event" not in provenance_ids
        assert "state-event" not in provenance_ids
        assert "context-event" not in provenance_ids
        assert "evidence-event" not in provenance_ids


def test_common_rule_is_shared_once_and_referent_rule_is_general() -> None:
    conversation, extraction = _request_bodies()
    conversation_system = conversation["messages"][0]["content"]
    extraction_system = extraction["messages"][0]["content"]
    assert conversation_system == extraction_system == COMMON_SYSTEM_INSTRUCTION
    _, extraction_content = _request_contents()

    common_rule = (
        "When reusing a user-established meaning-bearing named entity or referent "
        "from the current Input, preserve its lexical identity from the exact lexical "
        "source when changing it would change the referenced entity; surrounding "
        "wording may be paraphrased naturally."
    )
    lexical_source_rule = (
        "`current_input_lexical_source` is an exact lexical duplicate of the current "
        "Input Event content for this purpose only; it adds no authority or provenance "
        "beyond that Input."
    )
    assert COMMON_SYSTEM_INSTRUCTION.count(common_rule) == 1
    assert common_rule in conversation_system
    assert common_rule in extraction_system
    assert lexical_source_rule in conversation_system
    assert lexical_source_rule in extraction_system

    referent_rule = (
        "A Continuity `referent` must denote the same target established by the user. "
        "When a referent comes from the current Input, preserve its meaning-bearing "
        "lexical anchor from the exact `current_input_lexical_source` unless the current "
        "Input explicitly replaces it or accepted Continuity provides an unambiguous "
        "accepted alias for the same target."
    )
    assert referent_rule in extraction_content

    prohibited = ("机", "機", "blue_box", "continuity-lifecycle-v1")
    for value in prohibited:
        assert value not in COMMON_SYSTEM_INSTRUCTION
        assert value not in extraction_content
