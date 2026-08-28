from __future__ import annotations

import pytest

from relaylm.context import compile_cognitive_input
from relaylm.continuity import ContinuityContext, ContinuityItem
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


def _message(event_id: str, content: str, *, actor: str = "user") -> Event:
    return Event.create(
        type="message",
        actor=actor,
        payload={"content": content},
        event_id=event_id,
        timestamp="2026-08-17T01:44:00+00:00",
    )


def _record(
    state_id: str,
    state_class: str,
    key: str,
    value: object,
    *,
    sources: tuple[str, ...] | None = None,
    status: str = "active",
    valid_to: str | None = None,
) -> StateRecord:
    return StateRecord(
        state_id=state_id,
        state_class=state_class,
        key=key,
        value=value,
        sources=sources if sources is not None else (f"source-{state_id}",),
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


def _continuity(*, source: str, value: object = "blue box") -> ContinuityContext:
    return ContinuityContext(
        max_items=4,
        revision=1,
        items=(
            ContinuityItem(
                item_id="continuity-item",
                kind="referent",
                key="current_object",
                value=value,
                sources=(source,),
                epistemic_role="user_assertion",
                accepted_revision=1,
                expires_revision=3,
            ),
        ),
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
    assert all(
        record.status == "active" and record.valid_to is None
        for record in compiled.state
    )


def test_unrelated_active_state_is_culled_without_budget_pressure() -> None:
    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current(),
    )

    assert [record.key for record in compiled.state] == [
        "coffee",
        "preferred_beverage",
    ]


def test_identity_anchor_and_subjective_core_are_admitted_without_lexical_match() -> None:
    state = CanonicalState(
        states=(
            _record("goal", "self.goal", "finish_release", True),
            _record("belief", "self.belief", "working_style", "candid correction helps"),
            _record("identity", "user.identity", "name", "Rin"),
            _record("relationship", "relationship.state", "collaboration", "iterative"),
            _record("commitment", "relationship.commitment", "next_review", "Friday"),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current("Tell me about the weather"),
    )

    assert [(record.state_class, record.key) for record in compiled.state] == [
        ("self.belief", "working_style"),
        ("user.identity", "name"),
        ("relationship.state", "collaboration"),
    ]


def test_zero_state_cap_still_removes_anchor_and_subjective_core_projection() -> None:
    state = CanonicalState(
        states=(
            _record("identity", "user.identity", "name", "Rin"),
            _record("belief", "self.belief", "working_style", "candid"),
            _record("relationship", "relationship.state", "collaboration", "iterative"),
        )
    )
    prior = _message("prior", "Earlier context")
    current = _current()
    identity = Identity("# ReLM\nBe grounded.")

    compiled = compile_cognitive_input(
        identity=identity,
        state=state,
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


def test_working_context_source_link_admits_state_without_current_keyword_match() -> None:
    prior = _message("prior-residence", "Earlier we discussed where I live.")
    state = CanonicalState(
        states=(
            _record(
                "residence",
                "user.fact",
                "residence_location",
                "Fukuoka",
                sources=(prior.id,),
            ),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current("Continue from there."),
        recent_events=(prior,),
    )

    assert [record.key for record in compiled.state] == ["residence_location"]


def test_continuity_source_link_admits_state_without_current_keyword_match() -> None:
    state = CanonicalState(
        states=(
            _record(
                "box",
                "user.fact",
                "box_color",
                "blue",
                sources=("box-source",),
            ),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current("What about it now?"),
        continuity_context=_continuity(source="box-source"),
    )

    assert [record.key for record in compiled.state] == ["box_color"]


def test_selected_context_content_can_supply_bounded_state_relevance() -> None:
    prior = _message("prior-coffee", "We were comparing Ethiopia coffee beans.")
    state = CanonicalState(
        states=(
            _record("coffee-origin", "user.preference", "coffee_origin", "Ethiopia"),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current("Continue."),
        recent_events=(prior,),
    )

    assert [record.key for record in compiled.state] == ["coffee_origin"]


def test_shared_cjk_features_admit_relevant_state_without_admitting_unrelated_cjk() -> None:
    state = CanonicalState(
        states=(
            _record(
                "coffee",
                "user.preference",
                "coffee_origin",
                "浅煎りのエチオピアコーヒー",
            ),
            _record(
                "music",
                "user.preference",
                "music_mood",
                "静かなピアノ音楽",
            ),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current("エチオピアのコーヒーについて話そう"),
    )

    assert [record.key for record in compiled.state] == ["coffee_origin"]


def test_latin_ascii_substrings_do_not_create_state_relevance() -> None:
    state = CanonicalState(
        states=(
            _record("sentiment", "user.fact", "sentiment", "dislikes"),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current("The literal token is likes"),
    )

    assert compiled.state == ()


def test_partially_filled_cap_does_not_insert_zero_match_fallback() -> None:
    state = CanonicalState(
        states=(
            _record("identity", "user.identity", "name", "Rin"),
            _record("coffee", "user.preference", "coffee", "likes"),
            _record("home", "user.fact", "residence_location", "Fukuoka"),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current("Coffee sounds good."),
        max_state_records=3,
    )

    assert [record.key for record in compiled.state] == ["name", "coffee"]


def test_pressure_priority_is_deterministic_and_projection_returns_canonical_order() -> None:
    prior = _message("linked", "Earlier context with no current keyword.")
    state = CanonicalState(
        states=(
            _record("coffee", "user.preference", "coffee", "likes"),
            _record(
                "linked",
                "user.fact",
                "residence_location",
                "Fukuoka",
                sources=(prior.id,),
            ),
            _record("belief", "self.belief", "working_style", "candid"),
            _record("identity", "user.identity", "name", "Rin"),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current("Coffee?"),
        recent_events=(prior,),
        max_state_records=2,
    )

    assert [(record.state_class, record.key) for record in compiled.state] == [
        ("self.belief", "working_style"),
        ("user.identity", "name"),
    ]


def test_existing_state_slot_stays_resident_for_direct_correction_or_key_reuse() -> None:
    state = CanonicalState(
        states=(
            _record("timezone", "user.fact", "timezone", "JST"),
            _record("unrelated", "user.fact", "favorite_number", 7),
        )
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current("Correction: my timezone is UTC."),
    )

    assert [record.key for record in compiled.state] == ["timezone"]


def test_negative_state_cap_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_state_records must not be negative"):
        compile_cognitive_input(
            identity=Identity("# ReLM\nBe grounded."),
            state=_state(),
            current_event=_current(),
            max_state_records=-1,
        )
