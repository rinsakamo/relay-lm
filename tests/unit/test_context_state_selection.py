from __future__ import annotations

import pytest

from relaylm.context import compile_cognitive_input
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState, StateRecord


def _current(content: str = "Help me choose coffee today") -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": content},
        event_id="current",
        timestamp="2026-08-17T01:45:00+00:00",
    )


def _record(
    state_id: str,
    state_class: str,
    key: str,
    value: object,
    *,
    status: str = "active",
    valid_to: str | None = None,
) -> StateRecord:
    return StateRecord(
        state_id=state_id,
        state_class=state_class,
        key=key,
        value=value,
        sources=(f"source-{state_id}",),
        status=status,
        valid_to=valid_to,
    )


def _state() -> CanonicalState:
    return CanonicalState(
        states=(
            _record("tea", "user.preference", "tea", "likes"),
            _record("coffee", "user.preference", "coffee", "likes"),
            _record(
                "preferred",
                "user.preference",
                "preferred_beverage",
                "coffee",
            ),
            _record("home", "user.fact", "residence_location", "Fukuoka"),
            _record(
                "closed-coffee",
                "user.preference",
                "coffee_machine",
                "likes",
                status="closed",
                valid_to="2026-08-01T00:00:00+00:00",
            ),
        )
    )


def test_explicit_state_cap_prefers_lexically_relevant_active_records() -> None:
    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current(),
        max_state_records=2,
    )

    assert [(record.key, record.value) for record in compiled.state] == [
        ("coffee", "likes"),
        ("preferred_beverage", "coffee"),
    ]
    assert all(record.status == "active" and record.valid_to is None for record in compiled.state)


def test_state_cap_does_not_treat_substrings_as_specific_lexical_matches() -> None:
    state = CanonicalState(
        states=(
            _record("tea", "user.preference", "tea", "likes"),
            _record("dinner", "user.preference", "dinner_choice", "steak"),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current("Let's have steak tonight"),
        max_state_records=1,
    )

    assert [(record.key, record.value) for record in compiled.state] == [
        ("dinner_choice", "steak")
    ]


def test_state_cap_preserves_exact_multi_token_key_phrase_matching() -> None:
    state = CanonicalState(
        states=(
            _record("tea", "user.preference", "tea", "likes"),
            _record(
                "preferred",
                "user.preference",
                "preferred_beverage",
                "unknown",
            ),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current("What is my preferred beverage?"),
        max_state_records=1,
    )

    assert [record.key for record in compiled.state] == ["preferred_beverage"]


def test_state_selection_preserves_existing_behavior_without_cap() -> None:
    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current(),
    )

    assert [record.key for record in compiled.state] == [
        "tea",
        "coffee",
        "preferred_beverage",
        "residence_location",
    ]


def test_zero_state_cap_does_not_evict_identity_current_input_or_working_context() -> None:
    prior = Event.create(
        type="message",
        actor="user",
        payload={"content": "Earlier context"},
        event_id="prior",
        timestamp="2026-08-17T01:44:00+00:00",
    )
    current = _current()
    identity = Identity("# ReLM\nBe grounded.")

    compiled = compile_cognitive_input(
        identity=identity,
        state=_state(),
        current_event=current,
        recent_events=(prior, current),
        max_state_records=0,
    )

    assert compiled.identity is identity
    assert compiled.input is current
    assert compiled.state == ()
    assert [(item.actor, item.content) for item in compiled.context] == [
        ("user", "Earlier context")
    ]


def test_zero_match_fallback_is_deterministic_and_preserves_state_order() -> None:
    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current("Tell me something unrelated about weather"),
        max_state_records=2,
    )

    assert [record.key for record in compiled.state] == ["tea", "coffee"]


def test_negative_state_cap_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_state_records must not be negative"):
        compile_cognitive_input(
            identity=Identity("# ReLM\nBe grounded."),
            state=_state(),
            current_event=_current(),
            max_state_records=-1,
        )
