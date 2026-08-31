from __future__ import annotations

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import _extraction_request_body
from relaylm.state import STATE_CLASS_DEFINITIONS


def test_pass2_prompt_keeps_continuity_lifecycles_independent() -> None:
    cognitive_input = CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "The question is resolved and the task is done."},
            event_id="evt-now",
            timestamp="2026-08-28T00:00:00+00:00",
        ),
    )
    request = _extraction_request_body(
        model="gemma",
        extraction_input=CognitionExtractionInput(
            cognitive_input=cognitive_input,
            assistant_response="Understood.",
        ),
        decoding={},
    )

    messages = request["messages"]
    assert isinstance(messages, list)
    content = messages[1]["content"]
    assert isinstance(content, str)

    assert (
        "Evaluate each dependency on its own lifecycle; an unchanged related dependency "
        "does not suppress a newly established one." in content
    )
    assert (
        "A meaning explicitly resolved, completed, replaced, dismissed, or invalidated -> "
        "`resolve`." in content
    )
    assert "Reuse the accepted lifecycle key" in content
    assert "Resolution of one Continuity kind does not automatically resolve another." in content
