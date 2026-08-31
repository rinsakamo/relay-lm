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
    positions = [extraction_suffix.index(marker) for marker in ordered_markers]
    assert positions == sorted(positions)

    assert "State wire: `{state_class,key,op,value,sources}`" in extraction_suffix
    assert (
        "Continuity wire: `{kind,key,op,value,sources,epistemic_role}`"
        in extraction_suffix
    )
    assert "<OUTPUT_SCHEMA>" not in extraction_suffix
    assert '"additionalProperties"' not in extraction_suffix
    assert "Return exactly one JSON object with no extra keys." in extraction_suffix
    assert "response_format" not in conversation
    assert "response_format" not in extraction


def test_pass2_prompt_defines_compact_continuity_taxonomy_and_complete_examples() -> None:
    _, extraction = _request_bodies()
    extraction_messages = extraction["messages"]
    assert isinstance(extraction_messages, list)
    extraction_content = extraction_messages[1]["content"]
    assert isinstance(extraction_content, str)

    assert "Continuity meanings (classify independently):" in extraction_content
    assert (
        "`referent`: a specific subject or entity that upcoming dialogue may refer back to."
        in extraction_content
    )
    assert (
        "`unresolved`: an explicit open question or unknown value that remains to be resolved."
        in extraction_content
    )
    assert (
        "`active_task`: an unfinished action, process, or goal expected to continue."
        in extraction_content
    )
    assert (
        "Emit every distinct useful Continuity meaning present; do not choose only one best kind."
        in extraction_content
    )
    assert (
        "New items use a short stable semantic `key`; exact first-introduction wording is not globally canonical."
        in extraction_content
    )
    assert "new useful meaning -> emit `set`" in extraction_content
    assert "unchanged meaning -> emit no candidate" in extraction_content
    assert "current resolution or completion -> emit `resolve`" in extraction_content
    assert (
        "every emitted `set` or `resolve` must include the current Input Event ID `evt-now` in "
        "`sources`"
        in extraction_content
    )

    expected_examples = (
        {
            "kind": "referent",
            "key": "current_document",
            "op": "set",
            "value": "the draft",
            "sources": ["evt-now"],
            "epistemic_role": "user_assertion",
        },
        {
            "kind": "unresolved",
            "key": "document_author",
            "op": "set",
            "value": "author not yet known",
            "sources": ["evt-now"],
            "epistemic_role": "user_assertion",
        },
        {
            "kind": "active_task",
            "key": "verify_document_author",
            "op": "set",
            "value": "verify the document author",
            "sources": ["evt-now"],
            "epistemic_role": "user_assertion",
        },
    )
    for example in expected_examples:
        assert json.dumps(example, ensure_ascii=False, separators=(",", ":")) in extraction_content


def test_pass2_prompt_requires_a_complete_independent_continuity_decision_procedure() -> None:
    _, extraction = _request_bodies()
    extraction_messages = extraction["messages"]
    assert isinstance(extraction_messages, list)
    extraction_content = extraction_messages[1]["content"]
    assert isinstance(extraction_content, str)

    procedure = "Before emitting `continuity_candidates`, complete this independent decision procedure:"
    procedure_start = extraction_content.index(procedure)
    scan_markers = (
        "1. Scan `referent`.",
        "2. Scan `unresolved`.",
        "3. Scan `active_task`.",
    )
    scan_positions = [extraction_content.index(marker, procedure_start) for marker in scan_markers]
    assert scan_positions == sorted(scan_positions)
    assert all(position > procedure_start for position in scan_positions)

    for marker in (
        "new useful meaning -> emit `set`",
        "unchanged meaning -> emit no candidate",
        "current resolution or completion -> emit `resolve`",
    ):
        assert marker in extraction_content

    completion_marker = (
        "Complete all three kind decisions before concluding that `continuity_candidates` is empty"
    )
    assert extraction_content.index(completion_marker) > max(scan_positions)
    assert (
        "a no-op for one kind never suppresses a `set` or `resolve` for another."
        in extraction_content
    )
    assert (
        "use a new stable key unless updating or replacing an accepted item, then reuse its "
        "existing `kind` + `key`."
        in extraction_content
    )
    assert (
        "reuse the accepted `kind` + `key` and set `value` to null."
        in extraction_content
    )
    assert (
        "For `unresolved`, an explicit currently-open question or unknown value is an `unresolved` "
        "meaning when no accepted `unresolved` item already represents it."
        in extraction_content
    )
    assert (
        "Its creation is independent of unchanged related `referent`/`active_task` items and does "
        "not require a new task, interrogative form, or task change."
        in extraction_content
    )
    assert (
        "every emitted `set` or `resolve` must include the current Input Event ID `evt-now` in "
        "`sources`"
        in extraction_content
    )
    assert (
        "new descriptive facts about it, or an expectation that it may not be mentioned next does "
        "not end the referent."
        in extraction_content
    )
    assert (
        "Resolve a `referent` only when the current Input explicitly replaces, dismisses, or "
        "invalidates the reference target itself."
        in extraction_content
    )


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
