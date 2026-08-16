from __future__ import annotations

import pytest

from relaylm.context import compile_cognitive_input
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import serialize_cognitive_input
from relaylm.state import CanonicalState, StateCandidate, StateRecord
from relaylm.validation import apply_state_candidates


def _event(*, actor: str = "user", event_id: str = "evt-now") -> Event:
    return Event.create(
        type="message",
        actor=actor,
        payload={"content": "preference update"},
        event_id=event_id,
        timestamp="2026-08-16T13:30:00+00:00",
    )


def test_provider_facing_cognitive_input_exposes_preference_key_grammar() -> None:
    current = _event()
    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe kind."),
        state=CanonicalState(),
        current_event=current,
    )

    payload = serialize_cognitive_input(compiled)
    guidance = payload["state_classes"]["user.preference"]

    assert "specific subject or dimension" in guidance
    assert "preferred_beverage" in guidance
    assert "likes, dislikes, or preference" in guidance
    assert "comparative preference" in guidance


@pytest.mark.parametrize("generic_key", ["likes", "dislikes", "preference"])
def test_validator_rejects_generic_preference_keys(generic_key: str) -> None:
    current = _event()
    candidate = StateCandidate.set(
        state_class="user.preference",
        key=generic_key,
        value="tea, coffee (prefers coffee recently)",
        sources=(current.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(),
        candidates=(candidate,),
        events={current.id: current},
        required_source_ids=frozenset({current.id}),
    )

    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "generic_preference_key"
    assert result.state.states == ()


def test_validator_accepts_atomic_preference_subject_and_dimension_keys() -> None:
    current = _event()
    candidates = (
        StateCandidate.set(
            state_class="user.preference",
            key="tea",
            value="likes",
            sources=(current.id,),
        ),
        StateCandidate.set(
            state_class="user.preference",
            key="coffee",
            value="likes",
            sources=(current.id,),
        ),
        StateCandidate.set(
            state_class="user.preference",
            key="preferred_beverage",
            value="coffee",
            sources=(current.id,),
        ),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(),
        candidates=candidates,
        events={current.id: current},
        required_source_ids=frozenset({current.id}),
    )

    assert [decision.status for decision in result.decisions] == [
        "accepted",
        "accepted",
        "accepted",
    ]
    assert {(record.key, record.value) for record in result.state.states} == {
        ("tea", "likes"),
        ("coffee", "likes"),
        ("preferred_beverage", "coffee"),
    }


def test_validator_reuses_exact_specific_preference_dimension_key() -> None:
    current = _event()
    initial = StateRecord(
        state_id="state-preferred-beverage",
        state_class="user.preference",
        key="preferred_beverage",
        value="tea",
        sources=("evt-old",),
    )
    candidate = StateCandidate.set(
        state_class="user.preference",
        key="preferred_beverage",
        value="coffee",
        sources=(current.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(states=(initial,)),
        candidates=(candidate,),
        events={current.id: current},
        required_source_ids=frozenset({current.id}),
    )

    assert result.decisions[0].status == "accepted"
    assert result.decisions[0].action == "replace"
    assert len(result.state.states) == 1
    assert result.state.states[0].key == "preferred_beverage"
    assert result.state.states[0].value == "coffee"


def test_preference_key_grammar_does_not_bypass_user_source_authority() -> None:
    current = _event(actor="assistant", event_id="evt-assistant")
    candidate = StateCandidate.set(
        state_class="user.preference",
        key="tea",
        value="likes",
        sources=(current.id,),
    )

    result = apply_state_candidates(
        current_state=CanonicalState(),
        candidates=(candidate,),
        events={current.id: current},
        required_source_ids=frozenset({current.id}),
    )

    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "user_state_requires_user_source"
    assert result.state.states == ()
