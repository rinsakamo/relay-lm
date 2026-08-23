from __future__ import annotations

from pathlib import Path

import pytest

from relaylm.events import Event
from relaylm.state import CanonicalState, StateCandidate, StateRecord
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.validation import apply_state_candidates


def _event() -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "source"},
        event_id="event-user-1",
        timestamp="2026-08-23T07:30:00+00:00",
    )


@pytest.mark.parametrize(
    "value",
    (
        ("a", "b"),
        {1: "one"},
    ),
)
def test_validator_rejects_python_only_state_values(value: object) -> None:
    event = _event()
    candidate = StateCandidate.set(
        state_class="user.fact",
        key="json-domain",
        value=value,
        sources=(event.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(),
        candidates=(candidate,),
        events={event.id: event},
    )

    assert result.state.states == ()
    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "non_json_value"


@pytest.mark.parametrize(
    "value",
    (
        ("a", "b"),
        {1: "one"},
    ),
)
def test_python_only_state_values_fail_before_persistence_mutation(
    tmp_path: Path,
    value: object,
) -> None:
    character = CharacterDirectory(tmp_path)
    character.memory_path.mkdir(parents=True)
    character.state_path.write_text(
        '{"format_version":1,"states":[]}\n', encoding="utf-8"
    )
    before = character.state_path.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="stable JSON persistence shape"):
        state = CanonicalState(
            states=(
                StateRecord(
                    state_id="state-1",
                    state_class="user.fact",
                    key="json-domain",
                    value=value,
                    sources=("event-user-1",),
                ),
            )
        )
        character.save_state(state)

    assert character.state_path.read_text(encoding="utf-8") == before
    assert not (tmp_path / "memory" / ".state.json.tmp").exists()


def test_valid_nested_json_state_value_round_trips_without_shape_change(
    tmp_path: Path,
) -> None:
    character = CharacterDirectory(tmp_path)
    value = {
        "steps": [1, True, None, {"label": "done"}],
        "score": 0.5,
    }
    state = CanonicalState(
        states=(
            StateRecord(
                state_id="state-1",
                state_class="user.fact",
                key="json-domain",
                value=value,
                sources=("event-user-1",),
            ),
        )
    )

    character.save_state(state)
    loaded = character.load_state()

    assert loaded.states[0].value == value
    assert isinstance(loaded.states[0].value["steps"], list)
    assert isinstance(loaded.states[0].value["steps"][3], dict)
