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
    assert "turn_interpretation" not in extraction_suffix
    for removed_field in (
        "`user_meaning`",
        "`change_signals`",
        "`self_meaning`",
        "`assistant_effects`",
        "`continuity_signals`",
    ):
        assert removed_field not in extraction_suffix

    ordered_markers = (
        "`state_candidates`",
        "`continuity_candidates`",
    )
    positions = [extraction_suffix.index(item) for item in ordered_markers]
    assert positions == sorted(positions)

    assert "State wire is `{state_class,key,op,value,sources}`." in extraction_suffix
    assert (
        "Continuity wire is `{kind,key,op,value,sources,epistemic_role}`."
        in extraction_suffix
    )
    assert "<OUTPUT_SCHEMA>" not in extraction_suffix
    assert '"additionalProperties"' not in extraction_suffix
    assert (
        "Return exactly one JSON object with `state_candidates` and `continuity_candidates`, "
        "with no extra keys or prose." in extraction_suffix
    )
    assert "response_format" not in conversation
    assert "response_format" not in extraction


def test_pass2_prompt_defines_compact_continuity_taxonomy_without_examples() -> None:
    _, extraction = _request_bodies()
    extraction_messages = extraction["messages"]
    assert isinstance(extraction_messages, list)
    extraction_content = extraction_messages[1]["content"]
    assert isinstance(extraction_content, str)

    assert "Evaluate these meanings independently" in extraction_content
    assert "`referent` is a specific cross-turn reference target" in extraction_content
    assert "`unresolved` is an open question or unknown value" in extraction_content
    assert "`active_task` is unfinished work" in extraction_content
    assert "Resolution of one Continuity kind does not automatically resolve another." in (
        extraction_content
    )
    assert "Every new Continuity transition must be grounded in the current Input Event." in (
        extraction_content
    )
    assert "current Input Event ID `evt-now`" in extraction_content

    for removed_example in (
        '"current_document"',
        '"document_author"',
        '"verify_document_author"',
        '"preferred_beverage"',
    ):
        assert removed_example not in extraction_content


def test_pass2_prompt_projects_continuity_as_principle_level_lifecycle() -> None:
    _, extraction = _request_bodies()
    extraction_messages = extraction["messages"]
    assert isinstance(extraction_messages, list)
    extraction_content = extraction_messages[1]["content"]
    assert isinstance(extraction_content, str)

    assert "New useful meaning -> `set`." in extraction_content
    assert "Unchanged accepted meaning -> no candidate." in extraction_content
    assert (
        "A meaning explicitly resolved, completed, replaced, dismissed, or invalidated -> `resolve`."
        in extraction_content
    )
    assert "Reuse the accepted lifecycle key" in extraction_content
    assert "Resolution of one Continuity kind does not automatically resolve another." in (
        extraction_content
    )
    assert "Do not promote model inference into higher authority merely because it is plausible." in (
        extraction_content
    )
    assert "bare intention to discuss or continue" not in extraction_content
    assert "future-reference plan" not in extraction_content
    assert "Before concluding there are no Continuity candidates" not in extraction_content


def test_extraction_parser_admits_direct_candidate_wire() -> None:
    wire = {
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
    "wire",
    [
        {
            "turn_interpretation": {},
            "state_candidates": [],
            "continuity_candidates": [],
        },
        {"state_candidates": []},
        {
            "state_candidates": [],
            "continuity_candidates": [],
            "extra": [],
        },
    ],
)
def test_extraction_parser_rejects_noncanonical_top_level_shape(
    wire: dict[str, object],
) -> None:
    envelope = {
        "choices": [
            {
                "message": {"content": json.dumps(wire, ensure_ascii=False)},
                "finish_reason": "stop",
            }
        ]
    }

    with pytest.raises(ProviderProtocolError, match="state_candidates"):
        _parse_extraction_completion(envelope)
