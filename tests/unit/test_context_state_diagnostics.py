from __future__ import annotations

import json
from dataclasses import asdict

from relaylm.context import compile_cognitive_input_with_diagnostics
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState, StateRecord


def _current(content: str = "Help me choose coffee today") -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": content},
        event_id="current-sensitive-id",
        timestamp="2026-08-17T02:00:00+00:00",
    )


def _record(state_id: str, state_class: str, key: str, value: object) -> StateRecord:
    return StateRecord(
        state_id=state_id,
        state_class=state_class,
        key=key,
        value=value,
        sources=(f"source-{state_id}",),
    )


def _state() -> CanonicalState:
    return CanonicalState(
        states=(
            _record("tea-secret", "user.preference", "tea", "likes"),
            _record("coffee-secret", "user.preference", "coffee", "likes"),
            _record("preferred-secret", "user.preference", "preferred_beverage", "coffee"),
            _record("home-secret", "user.fact", "residence_location", "Fukuoka"),
        )
    )


def _compile(*, max_state_records: int | None, content: str = "Help me choose coffee today"):
    return compile_cognitive_input_with_diagnostics(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current(content),
        max_state_records=max_state_records,
    )


def test_diagnostics_report_content_free_lexical_budget_pressure() -> None:
    result = _compile(max_state_records=2)
    diagnostic = result.diagnostics[0]

    assert [record.key for record in result.cognitive_input.state] == [
        "coffee",
        "preferred_beverage",
    ]
    assert asdict(diagnostic) == {
        "layer": "canonical_state",
        "mode": "lexical_ranked",
        "eligible_count": 4,
        "selected_count": 2,
        "evicted_count": 2,
        "budget_unit": "records",
        "budget_limit": 2,
        "budget_used": 2,
        "budget_pressure": True,
        "selected_lexical_match_count": 2,
        "selected_fallback_count": 0,
        "evicted_budget_limit_count": 2,
        "authority_suppressed_count": 0,
        "current_event_excluded_count": 0,
        "redundancy_overlap_count": 0,
        "character_budget_limit": None,
        "character_budget_used": 0,
        "evicted_event_window_count": 0,
        "evicted_character_budget_count": 0,
        "evicted_orphan_assistant_count": 0,
    }

    serialized = json.dumps(asdict(diagnostic), ensure_ascii=False)
    for forbidden in (
        "coffee",
        "preferred_beverage",
        "Fukuoka",
        "tea-secret",
        "coffee-secret",
        "source-coffee-secret",
        "current-sensitive-id",
    ):
        assert forbidden not in serialized


def test_diagnostics_count_zero_match_fallback_without_leaking_records() -> None:
    diagnostic = _compile(
        max_state_records=2,
        content="Tell me something unrelated about weather",
    ).diagnostics[0]

    assert diagnostic.mode == "lexical_ranked"
    assert diagnostic.selected_lexical_match_count == 0
    assert diagnostic.selected_fallback_count == 2
    assert diagnostic.evicted_budget_limit_count == 2


def test_diagnostics_report_unbounded_projection_without_pressure() -> None:
    diagnostic = _compile(max_state_records=None).diagnostics[0]

    assert diagnostic.layer == "canonical_state"
    assert diagnostic.mode == "unbounded"
    assert diagnostic.eligible_count == 4
    assert diagnostic.selected_count == 4
    assert diagnostic.evicted_count == 0
    assert diagnostic.budget_limit is None
    assert diagnostic.budget_used == 4
    assert diagnostic.budget_pressure is False
    assert diagnostic.selected_lexical_match_count == 0
    assert diagnostic.selected_fallback_count == 0
    assert diagnostic.evicted_budget_limit_count == 0
    assert diagnostic.authority_suppressed_count == 0
    assert diagnostic.current_event_excluded_count == 0
    assert diagnostic.redundancy_overlap_count == 0
    assert diagnostic.character_budget_limit is None
    assert diagnostic.character_budget_used == 0
    assert diagnostic.evicted_event_window_count == 0
    assert diagnostic.evicted_character_budget_count == 0
    assert diagnostic.evicted_orphan_assistant_count == 0


def test_diagnostics_report_zero_budget_as_budget_eviction() -> None:
    result = _compile(max_state_records=0)
    diagnostic = result.diagnostics[0]

    assert result.cognitive_input.state == ()
    assert diagnostic.mode == "zero_budget"
    assert diagnostic.selected_count == 0
    assert diagnostic.evicted_count == 4
    assert diagnostic.budget_used == 0
    assert diagnostic.budget_pressure is True
    assert diagnostic.evicted_budget_limit_count == 4


def test_diagnostics_report_within_budget_without_ranking() -> None:
    diagnostic = _compile(max_state_records=10).diagnostics[0]

    assert diagnostic.mode == "within_budget"
    assert diagnostic.selected_count == 4
    assert diagnostic.evicted_count == 0
    assert diagnostic.budget_limit == 10
    assert diagnostic.budget_pressure is False
    assert diagnostic.selected_lexical_match_count == 0
    assert diagnostic.selected_fallback_count == 0
    assert diagnostic.evicted_budget_limit_count == 0
