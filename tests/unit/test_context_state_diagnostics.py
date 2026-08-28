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
            _record("home-secret", "user.fact", "residence_location", "Fukuoka"),
            _record("belief-secret", "self.belief", "working_style", "candid correction"),
            _record("identity-secret", "user.identity", "name", "Rin"),
            _record("relationship-secret", "relationship.state", "collaboration", "iterative"),
            _record("coffee-secret", "user.preference", "coffee", "likes"),
        )
    )


def _compile(
    *,
    max_state_records: int | None,
    content: str = "Help me choose coffee today",
):
    return compile_cognitive_input_with_diagnostics(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current(content),
        max_state_records=max_state_records,
    )


def test_diagnostics_separate_relevance_culling_from_budget_eviction() -> None:
    result = _compile(max_state_records=3)
    diagnostic = result.diagnostics[0]

    assert [record.key for record in result.cognitive_input.state] == [
        "working_style",
        "name",
        "collaboration",
    ]
    assert asdict(diagnostic) == {
        "layer": "canonical_state",
        "mode": "relevance_ranked_budgeted",
        "eligible_count": 5,
        "selected_count": 3,
        "evicted_count": 2,
        "budget_unit": "records",
        "budget_limit": 3,
        "budget_used": 3,
        "budget_pressure": True,
        "selected_lexical_match_count": 0,
        "selected_fallback_count": 0,
        "evicted_budget_limit_count": 1,
        "authority_suppressed_count": 0,
        "current_event_excluded_count": 0,
        "redundancy_overlap_count": 0,
        "character_budget_limit": None,
        "character_budget_used": 0,
        "evicted_event_window_count": 0,
        "evicted_character_budget_count": 0,
        "evicted_orphan_assistant_count": 0,
        "relevance_admitted_count": 4,
        "relevance_culled_count": 1,
        "anchor_admitted_count": 1,
        "subjective_core_admitted_count": 2,
        "context_linked_admitted_count": 0,
        "lexical_admitted_count": 1,
        "budget_evicted_count": 1,
    }

    serialized = json.dumps(asdict(diagnostic), ensure_ascii=False)
    for forbidden in (
        "coffee",
        "collaboration",
        "Fukuoka",
        "belief-secret",
        "identity-secret",
        "source-coffee-secret",
        "current-sensitive-id",
        "candid correction",
        "iterative",
    ):
        assert forbidden not in serialized


def test_relevance_culling_without_cap_is_not_budget_pressure() -> None:
    result = _compile(max_state_records=None)
    diagnostic = result.diagnostics[0]

    assert [record.key for record in result.cognitive_input.state] == [
        "working_style",
        "name",
        "collaboration",
        "coffee",
    ]
    assert diagnostic.layer == "canonical_state"
    assert diagnostic.mode == "relevance_filtered"
    assert diagnostic.eligible_count == 5
    assert diagnostic.relevance_admitted_count == 4
    assert diagnostic.relevance_culled_count == 1
    assert diagnostic.selected_count == 4
    assert diagnostic.evicted_count == 1
    assert diagnostic.budget_limit is None
    assert diagnostic.budget_used == 4
    assert diagnostic.budget_pressure is False
    assert diagnostic.budget_evicted_count == 0
    assert diagnostic.evicted_budget_limit_count == 0
    assert diagnostic.selected_fallback_count == 0


def test_zero_budget_reports_relevance_and_budget_stages_separately() -> None:
    result = _compile(max_state_records=0)
    diagnostic = result.diagnostics[0]

    assert result.cognitive_input.state == ()
    assert diagnostic.mode == "zero_budget"
    assert diagnostic.eligible_count == 5
    assert diagnostic.relevance_admitted_count == 4
    assert diagnostic.relevance_culled_count == 1
    assert diagnostic.selected_count == 0
    assert diagnostic.evicted_count == 5
    assert diagnostic.budget_used == 0
    assert diagnostic.budget_pressure is True
    assert diagnostic.budget_evicted_count == 4
    assert diagnostic.evicted_budget_limit_count == 4


def test_spare_capacity_never_appears_as_zero_match_fallback() -> None:
    diagnostic = _compile(
        max_state_records=10,
        content="Tell me something unrelated about weather",
    ).diagnostics[0]

    assert diagnostic.mode == "relevance_filtered"
    assert diagnostic.relevance_admitted_count == 3
    assert diagnostic.relevance_culled_count == 2
    assert diagnostic.selected_count == 3
    assert diagnostic.selected_fallback_count == 0
    assert diagnostic.budget_evicted_count == 0
    assert diagnostic.budget_pressure is False
