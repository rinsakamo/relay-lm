from __future__ import annotations

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import _extraction_request_body
from relaylm.state import STATE_CLASS_DEFINITIONS


def test_pass2_exposes_identity_fact_boundary_without_fixture_teaching() -> None:
    cognitive_input = CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "I need to correct one stable profile detail."},
            event_id="evt-now",
            timestamp="2026-09-07T00:00:00+00:00",
        ),
    )
    body = _extraction_request_body(
        model="gemma",
        extraction_input=CognitionExtractionInput(
            cognitive_input=cognitive_input,
            assistant_response="Thanks for the correction.",
        ),
        decoding={},
    )

    messages = body["messages"]
    assert isinstance(messages, list)
    content = messages[1]["content"]
    assert isinstance(content, str)

    identity_definition = STATE_CLASS_DEFINITIONS["user.identity"]
    fact_definition = STATE_CLASS_DEFINITIONS["user.fact"]
    assert identity_definition in content
    assert fact_definition in content
    assert "self-identifying information" in identity_definition
    assert "same attribute is corrected" in identity_definition
    assert "ordinary current factual information" in fact_definition
    assert "not self-identifying information" in fact_definition
    assert "generic fallback for user.identity" in fact_definition

    for fixture_specific_text in (
        "response-transcript-fidelity-v1",
        "ユウ",
        "ユウト",
    ):
        assert fixture_specific_text not in content
