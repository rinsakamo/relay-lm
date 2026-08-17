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


def _compile(*, max_state_records: int | None):
    return compile_cognitive_input_with_diagnostics(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current(),
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
        "selected_reasons": ({"reason": "lexical_match", "count": 2},),
        "evicted_reasons": ({"reason": "budget_limit", "count": 2},),
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


def test_diagnostics_report_unbounded_projection_without_pressure() -> None:
    result = _compile(max_state_records=None)
    diagnostic = result.diagnostics[0]

    assert diagnostic.layer == "canonical_state"
    assert diagnostic.mode == "unbounded"
    assert diagnostic.eligible_count == 4
    assert diagnostic.selected_count == 4
    assert diagnostic.evicted_count == 0
    assert diagnostic.budget_limit is None
    assert diagnostic.budget_used == 4
    assert diagnostic.budget_pressure is False
    assert [(item.reason, item.count) for item in diagnostic.selected_reasons] == [
        ("eligible_unbounded", 4)
    ]
    assert diagnostic.evicted_reasons == ()


def test_diagnostics_report_zero_budget_as_budget_eviction() -> None:
    result = _compile(max_state_records=0)
    diagnostic = result.diagnostics[0]

    assert result.cognitive_input.state == ()
    assert diagnostic.mode == "zero_budget"
    assert diagnostic.selected_count == 0
    assert diagnostic.evicted_count == 4
    assert diagnostic.budget_used == 0
    assert diagnostic.budget_pressure is True
    assert [(item.reason, item.count) for item in diagnostic.evicted_reasons] == [
        ("budget_limit", 4)
    ]


def test_diagnostics_report_within_budget_without_ranking() -> None:
    result = _compile(max_state_records=10)
    diagnostic = result.diagnostics[0]

    assert diagnostic.mode == "within_budget"
    assert diagnostic.selected_count == 4
    assert diagnostic.evicted_count == 0
    assert diagnostic.budget_limit == 10
    assert diagnostic.budget_pressure is False
    assert [(item.reason, item.count) for item in diagnostic.selected_reasons] == [
        ("within_budget", 4)
    ]
