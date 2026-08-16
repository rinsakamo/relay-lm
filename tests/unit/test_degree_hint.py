from __future__ import annotations

import math

import pytest

from relaylm.cognitive import CognitiveInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    WIRE_SCHEMA,
    parse_wire_output,
    serialize_cognitive_input,
)
from relaylm.state import CanonicalState, STATE_CLASS_DEFINITIONS, StateCandidate, StateRecord
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.validation import apply_state_candidates


def _wire_value(value: object) -> dict[str, object]:
    return {
        "utterance": "了解。",
        "state_candidates": [
            {
                "state_class": "user.preference",
                "key": "coffee",
                "op": "set",
                "value": value,
                "sources": ["evt-now"],
            }
        ],
    }


def _user_event(event_id: str = "evt-now") -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "最近は紅茶よりコーヒーの方が好き"},
        event_id=event_id,
        timestamp="2026-08-17T00:00:00+00:00",
    )


def test_wire_keeps_plain_string_state_values_backward_compatible() -> None:
    output = parse_wire_output(_wire_value("likes"))

    assert output.state_candidates[0].value == "likes"


@pytest.mark.parametrize("degree", [0.0, 0.65, 1.0])
def test_wire_accepts_bounded_degree_hint(degree: float) -> None:
    output = parse_wire_output(
        _wire_value({"semantic": "likes", "degree_hint": degree})
    )

    assert output.state_candidates[0].value == {
        "semantic": "likes",
        "degree_hint": degree,
    }


@pytest.mark.parametrize(
    "value",
    [
        {"semantic": "likes"},
        {"degree_hint": 0.8},
        {"semantic": "", "degree_hint": 0.8},
        {"semantic": "likes", "degree_hint": -0.01},
        {"semantic": "likes", "degree_hint": 1.01},
        {"semantic": "likes", "degree_hint": True},
        {"semantic": "likes", "degree_hint": float("nan")},
        {"semantic": "likes", "degree_hint": 0.8, "confidence": 0.9},
    ],
)
def test_wire_rejects_malformed_degree_hint(value: object) -> None:
    with pytest.raises(ProviderProtocolError):
        parse_wire_output(_wire_value(value))


def test_strict_wire_schema_exposes_degree_hint_as_optional_set_value_shape() -> None:
    value_schema = WIRE_SCHEMA["properties"]["state_candidates"]["items"]["properties"]["value"]
    degree_schema = value_schema["anyOf"][1]

    assert degree_schema["required"] == ["semantic", "degree_hint"]
    assert degree_schema["properties"]["degree_hint"] == {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0,
    }


def test_validator_rejects_malformed_reserved_degree_hint_from_non_wire_provider() -> None:
    event = _user_event()
    candidate = StateCandidate.set(
        state_class="user.preference",
        key="coffee",
        value={"semantic": "likes", "degree_hint": 1.2},
        sources=(event.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(),
        candidates=(candidate,),
        events={event.id: event},
        required_source_ids=frozenset({event.id}),
    )

    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "invalid_degree_hint_value"
    assert result.state.states == ()


def test_degree_weakening_is_a_set_replacement_not_removal() -> None:
    event = _user_event()
    initial = StateRecord(
        state_id="tea-old",
        state_class="user.preference",
        key="tea",
        value={"semantic": "likes", "degree_hint": 0.75},
        sources=("old-event",),
    )
    candidate = StateCandidate.set(
        state_class="user.preference",
        key="tea",
        value={"semantic": "likes", "degree_hint": 0.6},
        sources=(event.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(states=(initial,)),
        candidates=(candidate,),
        events={event.id: event},
        required_source_ids=frozenset({event.id}),
    )

    assert result.decisions[0].action == "replace"
    assert len(result.state.states) == 1
    assert result.state.states[0].key == "tea"
    assert result.state.states[0].value == {"semantic": "likes", "degree_hint": 0.6}


def test_degree_hint_round_trips_through_state_storage_and_cognitive_input(tmp_path) -> None:
    value = {"semantic": "likes", "degree_hint": 0.85}
    record = StateRecord(
        state_id="coffee-current",
        state_class="user.preference",
        key="coffee",
        value=value,
        sources=("evt-old",),
    )
    character = CharacterDirectory(tmp_path)
    character.save_state(CanonicalState(states=(record,)))

    loaded = character.load_state()
    assert loaded.states[0].value == value

    cognitive = CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=loaded.states,
        context=(),
        input=_user_event(),
    )
    serialized = serialize_cognitive_input(cognitive)

    assert serialized["state"][0]["value"] == value


def test_non_finite_unreserved_json_value_still_fails_closed() -> None:
    event = _user_event()
    candidate = StateCandidate.set(
        state_class="user.fact",
        key="measurement",
        value={"raw": math.inf},
        sources=(event.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(),
        candidates=(candidate,),
        events={event.id: event},
        required_source_ids=frozenset({event.id}),
    )

    assert result.decisions[0].reason == "non_json_value"
