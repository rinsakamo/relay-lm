from __future__ import annotations

import json

import pytest

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_two_pass import (
    _conversation_request_body,
    _extraction_request_body,
    _parse_extraction_completion,
)
from relaylm.state import STATE_CLASS_DEFINITIONS


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "最近コーヒーを飲んでる"},
            event_id="evt-now",
            timestamp="2026-08-20T00:00:00+00:00",
        ),
    )


def _request_bodies() -> tuple[dict[str, object], dict[str, object]]:
    cognitive_input = _cognitive_input()
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
            assistant_response="最近はコーヒーを飲んでるんだね。",
        ),
        decoding={},
    )
    return conversation, extraction


def test_two_pass_requests_share_exact_common_prefix_before_pass_suffix() -> None:
    conversation, extraction = _request_bodies()

    conversation_messages = conversation["messages"]
    extraction_messages = extraction["messages"]
    assert isinstance(conversation_messages, list)
    assert isinstance(extraction_messages, list)
    assert conversation_messages[0] == extraction_messages[0]

    conversation_content = conversation_messages[1]["content"]
    extraction_content = extraction_messages[1]["content"]
    assert isinstance(conversation_content, str)
    assert isinstance(extraction_content, str)

    marker = "<PASS>\n"
    assert marker in conversation_content
    assert marker in extraction_content
    conversation_prefix, conversation_suffix = conversation_content.split(marker, 1)
    extraction_prefix, extraction_suffix = extraction_content.split(marker, 1)

    assert conversation_prefix == extraction_prefix
    assert conversation_suffix == "CONVERSATION\n\nRespond as this character."
    assert extraction_suffix.startswith("EXTRACTION\n")
    for field in (
        "turn_interpretation",
        "user_meaning",
        "change_signals",
        "self_meaning",
        "assistant_effects",
        "unresolved",
        "continuity_signals",
    ):
        assert field in extraction_suffix
    assert "Return exactly one JSON object matching the supplied schema." in extraction_suffix
    assert "response_format" not in conversation
    assert "response_format" not in extraction


def test_extraction_parser_admits_exact_non_authoritative_turn_interpretation() -> None:
    wire = {
        "turn_interpretation": {
            "user_meaning": ["最近コーヒーを飲む頻度が増えている"],
            "change_signals": ["飲料習慣について新しい変化が示されている"],
            "self_meaning": [],
            "assistant_effects": [],
            "unresolved": ["コーヒーが好きになったかは不明"],
            "continuity_signals": [],
        },
        "state_candidates": [],
        "continuity_candidates": [],
    }
    envelope = {
        "choices": [
            {
                "message": {"content": json.dumps(wire, ensure_ascii=False)},
                "finish_reason": "stop",
            }
        ]
    }

    output = _parse_extraction_completion(envelope)

    assert output.state_candidates == ()
    assert output.continuity_candidates == ()


@pytest.mark.parametrize(
    "turn_interpretation",
    [
        {
            "user_meaning": [],
            "change_signals": [],
            "self_meaning": [],
            "assistant_effects": [],
            "unresolved": [],
        },
        {
            "user_meaning": [],
            "change_signals": [],
            "self_meaning": [],
            "assistant_effects": [],
            "unresolved": [],
            "continuity_signals": [],
            "extra": [],
        },
        {
            "user_meaning": "not-an-array",
            "change_signals": [],
            "self_meaning": [],
            "assistant_effects": [],
            "unresolved": [],
            "continuity_signals": [],
        },
    ],
)
def test_extraction_parser_rejects_invalid_turn_interpretation_shape(
    turn_interpretation: object,
) -> None:
    wire = {
        "turn_interpretation": turn_interpretation,
        "state_candidates": [],
        "continuity_candidates": [],
    }
    envelope = {
        "choices": [
            {
                "message": {"content": json.dumps(wire, ensure_ascii=False)},
                "finish_reason": "stop",
            }
        ]
    }

    with pytest.raises(ProviderProtocolError, match="turn_interpretation"):
        _parse_extraction_completion(envelope)
