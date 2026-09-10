from __future__ import annotations

import json

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import serialize_cognitive_input
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


def _model_facing_cognitive_input(message: str) -> tuple[dict[str, object], str]:
    prefix = "<COGNITIVE_INPUT>\n"
    suffix = "\n</COGNITIVE_INPUT>"
    start = message.index(prefix) + len(prefix)
    end = message.index(suffix, start)
    serialized = message[start:end]
    payload = json.loads(serialized)
    assert isinstance(payload, dict)
    return payload, serialized


def test_current_input_lexical_source_is_exact_in_both_passes() -> None:
    content = 'Keep the café label "XR-17/β" as the same reference next turn.'
    cognitive_input = _input(content)
    canonical = serialize_cognitive_input(cognitive_input)

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

    assert "current_input_lexical_source" not in canonical
    expected_projection = dict(canonical)
    expected_projection["current_input_lexical_source"] = {"content": content}

    for user_message in (conversation_user, extraction_user):
        model_facing, serialized = _model_facing_cognitive_input(user_message)
        assert model_facing == expected_projection
        assert model_facing["input"]["content"] == content
        assert model_facing["current_input_lexical_source"] == {"content": content}
        assert serialized.count('"current_input_lexical_source"') == 1
        assert "<CURRENT_INPUT_LEXICAL_SOURCE>" not in user_message

    assert "</COGNITIVE_INPUT>\n\n<PASS>\nCONVERSATION" in conversation_user
    assert "</COGNITIVE_INPUT>\n\n<PASS>\nEXTRACTION" in extraction_user

    for request in (conversation, extraction):
        system_message = request["messages"][0]["content"]
        assert isinstance(system_message, str)
        assert "adds no authority beyond that current Input Event" in system_message
        assert "preserve its lexical identity" in system_message

    assert "not from a paraphrased Pass 1 response" in extraction_user
    assert "current_input_lexical_source.content" in extraction_user

    semantic_messages = (
        conversation["messages"][0]["content"],
        conversation_user,
        extraction["messages"][0]["content"],
        extraction_user,
    )
    fixture_specific_text = (
        "\u673a",
        "\u6a5f",
        "continuity-" + "lifecycle-v1",
    )
    for text in fixture_specific_text:
        for message in semantic_messages:
            assert text not in message
