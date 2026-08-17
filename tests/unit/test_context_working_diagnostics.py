from __future__ import annotations

import json
from dataclasses import asdict

from relaylm.context import compile_cognitive_input_with_diagnostics
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState


def _message(event_id: str, actor: str, content: str, second: int) -> Event:
    return Event.create(
        type="message",
        actor=actor,
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T09:10:{second:02d}+00:00",
    )


def _history() -> tuple[Event, Event, Event, Event, Event]:
    return (
        _message("old-user-secret", "user", "old question", 0),
        _message("old-assistant-secret", "assistant", "old answer", 1),
        _message("new-user-secret", "user", "new question", 2),
        _message("new-assistant-secret", "assistant", "new answer", 3),
        _message("current-secret", "user", "current question", 4),
    )


def test_working_context_diagnostics_separate_window_orphan_and_character_evictions() -> None:
    old_user, old_assistant, new_user, new_assistant, current = _history()
    identity = Identity("# ReLM\nBe grounded.")

    event_window = compile_cognitive_input_with_diagnostics(
        identity=identity,
        state=CanonicalState(),
        current_event=current,
        recent_events=(old_user, old_assistant, new_user, new_assistant, current),
        max_working_context_events=3,
        max_working_context_chars=1000,
    )
    newest_pair_chars = len(new_user.payload["content"]) + len(new_assistant.payload["content"])
    char_budget = compile_cognitive_input_with_diagnostics(
        identity=identity,
        state=CanonicalState(),
        current_event=current,
        recent_events=(old_user, old_assistant, new_user, new_assistant, current),
        max_working_context_events=6,
        max_working_context_chars=newest_pair_chars,
    )

    assert [diagnostic.layer for diagnostic in event_window.diagnostics] == [
        "canonical_state",
        "working_context",
        "retrieved_memory",
        "event_evidence",
    ]

    window_diagnostic = event_window.diagnostics[1]
    assert window_diagnostic.mode == "budget_filtered"
    assert window_diagnostic.eligible_count == 4
    assert window_diagnostic.selected_count == 2
    assert window_diagnostic.evicted_count == 2
    assert window_diagnostic.budget_unit == "events"
    assert window_diagnostic.budget_limit == 3
    assert window_diagnostic.budget_used == 2
    assert window_diagnostic.budget_pressure is True
    assert window_diagnostic.character_budget_limit == 1000
    assert window_diagnostic.character_budget_used == newest_pair_chars
    assert window_diagnostic.current_event_excluded_count == 1
    assert window_diagnostic.evicted_event_window_count == 1
    assert window_diagnostic.evicted_orphan_assistant_count == 1
    assert window_diagnostic.evicted_character_budget_count == 0

    char_diagnostic = char_budget.diagnostics[1]
    assert char_diagnostic.mode == "budget_filtered"
    assert char_diagnostic.eligible_count == 4
    assert char_diagnostic.selected_count == 2
    assert char_diagnostic.evicted_count == 2
    assert char_diagnostic.budget_limit == 6
    assert char_diagnostic.character_budget_limit == newest_pair_chars
    assert char_diagnostic.character_budget_used == newest_pair_chars
    assert char_diagnostic.evicted_event_window_count == 0
    assert char_diagnostic.evicted_orphan_assistant_count == 0
    assert char_diagnostic.evicted_character_budget_count == 2

    serialized = json.dumps(
        [asdict(window_diagnostic), asdict(char_diagnostic)], ensure_ascii=False
    )
    for forbidden in (
        "old-user-secret",
        "old-assistant-secret",
        "new-user-secret",
        "new-assistant-secret",
        "current-secret",
        "old question",
        "new question",
        "current question",
    ):
        assert forbidden not in serialized


def test_working_context_zero_character_budget_reports_character_eviction() -> None:
    old_user, old_assistant, new_user, new_assistant, current = _history()

    result = compile_cognitive_input_with_diagnostics(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=current,
        recent_events=(old_user, old_assistant, new_user, new_assistant, current),
        max_working_context_events=6,
        max_working_context_chars=0,
    )
    diagnostic = result.diagnostics[1]

    assert result.cognitive_input.context == ()
    assert diagnostic.mode == "zero_budget"
    assert diagnostic.eligible_count == 4
    assert diagnostic.selected_count == 0
    assert diagnostic.evicted_count == 4
    assert diagnostic.evicted_event_window_count == 0
    assert diagnostic.evicted_orphan_assistant_count == 0
    assert diagnostic.evicted_character_budget_count == 4
    assert diagnostic.character_budget_limit == 0
    assert diagnostic.character_budget_used == 0
