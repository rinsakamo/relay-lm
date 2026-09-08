from __future__ import annotations

import json

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import (
    _conversation_request_body,
    _extraction_request_body,
)
from relaylm.state import STATE_CLASS_DEFINITIONS


def _input(content: str) -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe precise."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": content},
            event_id="evt-now",
            timestamp="2026-09-08T00:00:00+00:00",
        ),
    )


def _lexical_payload(message: str) -> dict[str, str]:
    prefix = "<CURRENT_INPUT_LEXICAL_SOURCE>\n"
    suffix = "\n</CURRENT_INPUT_LEXICAL_SOURCE>"
    start = message.index(prefix) + len(prefix)
    end = message.index(suffix, start)
    payload = json.loads(message[start:end])
    assert isinstance(payload, dict)
    assert set(payload) == {"content"}
    assert isinstance(payload["content"], str)
    return payload


def test_current_input_lexical_source_is_exact_in_both_passes() -> None:
    content = 'Keep the café label "XR-17/β" as the same reference next turn.'
    cognitive_input = _input(content)

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
            assistant_response="I can keep referring to that label.",
        ),
        decoding={},
    )

    conversation_user = conversation["messages"][1]["content"]
    extraction_user = extraction["messages"][1]["content"]
    assert isinstance(conversation_user, str)
    assert isinstance(extraction_user, str)

    assert _lexical_payload(conversation_user) == {"content": content}
    assert _lexical_payload(extraction_user) == {"content": content}
    assert conversation_user.count("<CURRENT_INPUT_LEXICAL_SOURCE>") == 1
    assert extraction_user.count("<CURRENT_INPUT_LEXICAL_SOURCE>") == 1

    for user_message in (conversation_user, extraction_user):
        assert "adds no authority beyond the current Input Event" in user_message
        assert "copy its lexical form from this source" in user_message

    assert "not from a paraphrased Pass 1 response" in extraction_user
    assert "accepted Continuity context provides an unambiguous alias" in extraction_user

    for fixture_specific_text in (
        "continuity-lifecycle-v1",
        "机",
        "機",
    ):
        assert fixture_specific_text not in conversation_user
        assert fixture_specific_text not in extraction_user
