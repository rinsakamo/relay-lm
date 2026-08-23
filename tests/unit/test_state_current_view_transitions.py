from __future__ import annotations

import pytest

from relaylm.events import Event
from relaylm.state import CanonicalState, StateCandidate, StateRecord
from relaylm.validation import apply_state_candidates


def _current_event() -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "今は東京に住んでいる"},
        event_id="evt-current",
        timestamp="2026-08-23T00:00:00+00:00",
    )


@pytest.mark.parametrize(
    ("status", "valid_to"),
    (
        ("active", "2026-08-01T00:00:00+00:00"),
        ("inactive", None),
    ),
)
def test_non_current_same_slot_does_not_satisfy_existing_current_slot(
    status: str,
    valid_to: str | None,
) -> None:
    historical = StateRecord(
        state_id="state-historical",
        state_class="user.fact",
        key="residence_location",
        value="Tokyo",
        status=status,
        valid_from="2026-07-01T00:00:00+00:00",
        valid_to=valid_to,
        sources=("evt-old",),
    )
    event = _current_event()
    candidate = StateCandidate.set(
        state_class="user.fact",
        key="residence_location",
        value="Tokyo",
        sources=(event.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(states=(historical,)),
        candidates=(candidate,),
        events={event.id: event},
        required_source_ids=frozenset({event.id}),
    )

    assert result.decisions[0].status == "accepted"
    assert result.decisions[0].action == "create"
    assert historical in result.state.states
    current_records = tuple(
        record
        for record in result.state.states
        if record.status == "active" and record.valid_to is None
    )
    assert len(current_records) == 1
    assert current_records[0].state_class == "user.fact"
    assert current_records[0].key == "residence_location"
    assert current_records[0].value == "Tokyo"
    assert current_records[0].sources == (event.id,)


def test_remove_only_removes_current_view_record_and_preserves_non_current_same_slot() -> None:
    current = StateRecord(
        state_id="state-current",
        state_class="user.fact",
        key="residence_location",
        value="Osaka",
        valid_from="2026-08-10T00:00:00+00:00",
        sources=("evt-osaka",),
    )
    historical = StateRecord(
        state_id="state-historical",
        state_class="user.fact",
        key="residence_location",
        value="Tokyo",
        valid_from="2026-07-01T00:00:00+00:00",
        valid_to="2026-08-09T23:59:59+00:00",
        sources=("evt-tokyo",),
    )
    event = _current_event()
    candidate = StateCandidate.remove(
        state_class="user.fact",
        key="residence_location",
        sources=(event.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(states=(current, historical)),
        candidates=(candidate,),
        events={event.id: event},
        required_source_ids=frozenset({event.id}),
    )

    assert result.decisions[0].status == "accepted"
    assert result.decisions[0].action == "remove"
    assert result.state.states == (historical,)


@pytest.mark.parametrize(
    ("existing_value", "candidate_value"),
    (
        (True, 1),
        (False, 0),
        ([True], [1]),
        ({"nested": [False]}, {"nested": [0]}),
    ),
)
def test_json_boolean_number_type_changes_replace_current_state(
    existing_value: object,
    candidate_value: object,
) -> None:
    current = StateRecord(
        state_id="state-current",
        state_class="user.fact",
        key="typed_value",
        value=existing_value,
        sources=("evt-old",),
    )
    event = _current_event()
    candidate = StateCandidate.set(
        state_class="user.fact",
        key="typed_value",
        value=candidate_value,
        sources=(event.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(states=(current,)),
        candidates=(candidate,),
        events={event.id: event},
        required_source_ids=frozenset({event.id}),
    )

    assert result.changed is True
    assert result.decisions[0].status == "accepted"
    assert result.decisions[0].action == "replace"
    assert result.state.states[0].value == candidate_value
    assert type(result.state.states[0].value) is type(candidate_value)
    assert result.state.states[0].sources == (event.id,)


def test_json_numeric_values_remain_equal_across_int_and_float_representation() -> None:
    current = StateRecord(
        state_id="state-current",
        state_class="user.fact",
        key="numeric_value",
        value=1,
        sources=("evt-old",),
    )
    event = _current_event()
    candidate = StateCandidate.set(
        state_class="user.fact",
        key="numeric_value",
        value=1.0,
        sources=(event.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(states=(current,)),
        candidates=(candidate,),
        events={event.id: event},
        required_source_ids=frozenset({event.id}),
    )

    assert result.changed is False
    assert result.decisions[0].status == "noop"
    assert result.state.states == (current,)
