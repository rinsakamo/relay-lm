from __future__ import annotations

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import (
    _conversation_request_body,
    _extraction_request_body,
)
from relaylm.state import STATE_CLASS_DEFINITIONS


def _input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe precise."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={
                "content": (
                    "Keep the red folder as the same reference target when we continue."
                )
            },
            event_id="evt-now",
            timestamp="2026-09-07T00:00:00+00:00",
        ),
    )


def test_pass1_and_pass2_preserve_referent_semantic_identity_without_fixture_teaching() -> None:
    cognitive_input = _input()
    conversation = _conversation_request_body(
        model="gemma",
        cognitive_input=cognitive_input,
        stream=False,
        decoding={},
    )
    extraction = _extraction_request_body(
        model="gemma",
        extraction_input=CognitionExtractionInput(
            cognitive_input=cognitive_input,
            assistant_response="We can keep referring to that same folder.",
        ),
        decoding={},
    )

    conversation_system = conversation["messages"][0]["content"]
    extraction_system = extraction["messages"][0]["content"]
    extraction_user = extraction["messages"][1]["content"]
    assert isinstance(conversation_system, str)
    assert isinstance(extraction_system, str)
    assert isinstance(extraction_user, str)

    for system_prompt in (conversation_system, extraction_system):
        assert "meaning-bearing referential terms" in system_prompt
        assert "referenced entity" in system_prompt

    assert "same target the user established" in extraction_user
    assert "semantically different term" in extraction_user

    for fixture_specific_text in (
        "continuity-lifecycle-v1",
        "机",
        "機",
    ):
        assert fixture_specific_text not in conversation_system
        assert fixture_specific_text not in extraction_user
