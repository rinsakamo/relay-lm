from __future__ import annotations

import json
from dataclasses import asdict

from relaylm.event_retrieval import (
    select_event_evidence,
    select_event_evidence_with_diagnostics,
)
from relaylm.events import Event


def _event(
    event_id: str,
    *,
    content: str,
    event_type: str = "message",
) -> Event:
    return Event(
        id=event_id,
        type=event_type,
        actor="user",
        timestamp="2026-08-17T00:00:00+00:00",
        payload={"content": content},
    )


def test_event_retrieval_diagnostics_report_exclusion_and_budget_reasons_without_changing_selection() -> None:
    non_message = _event("tool-secret", content="coffee preference", event_type="tool")
    blank = _event("blank-secret", content="   ")
    excluded = _event("current-secret", content="coffee preference current")
    oversized = _event(
        "oversized-secret",
        content="coffee preference " + "details " * 20,
    )
    older = _event("older-secret", content="coffee note")
    newer = _event("newer-secret", content="coffee update")
    events = (non_message, blank, excluded, oversized, older, newer)
    max_chars = len(newer.payload["content"])

    result = select_event_evidence_with_diagnostics(
        events=events,
        query="coffee preference",
        max_events=1,
        max_chars=max_chars,
        exclude_event_ids=(excluded.id,),
    )
    plain = select_event_evidence(
        events=events,
        query="coffee preference",
        max_events=1,
        max_chars=max_chars,
        exclude_event_ids=(excluded.id,),
    )

    assert result.events == plain == (newer,)

    diagnostic = result.diagnostics
    assert diagnostic.mode == "lexical"
    assert diagnostic.input_event_count == 6
    assert diagnostic.excluded_event_count == 1
    assert diagnostic.non_message_count == 1
    assert diagnostic.blank_content_count == 1
    assert diagnostic.eligible_message_count == 3
    assert diagnostic.positive_candidate_count == 3
    assert diagnostic.selected_count == 1
    assert diagnostic.event_budget_limit == 1
    assert diagnostic.character_budget_limit == max_chars
    assert diagnostic.character_budget_used == max_chars
    assert diagnostic.skipped_character_budget_count == 1
    assert diagnostic.unadmitted_event_limit_count == 1
    assert diagnostic.event_budget_pressure is True
    assert diagnostic.character_budget_pressure is True

    serialized = json.dumps(asdict(diagnostic), ensure_ascii=False)
    for forbidden in (
        "current-secret",
        "oversized-secret",
        "newer-secret",
        "coffee",
        "preference",
    ):
        assert forbidden not in serialized


def test_event_retrieval_zero_budget_does_not_consume_or_infer_unseen_events() -> None:
    def events():
        raise AssertionError("zero-budget retrieval must not consume Events")
        yield _event("unseen-secret", content="coffee")

    result = select_event_evidence_with_diagnostics(
        events=events(),
        query="coffee",
        max_events=0,
        max_chars=100,
        exclude_event_ids=("unseen-secret",),
    )

    assert result.events == ()
    assert result.diagnostics.mode == "zero_budget"
    assert result.diagnostics.input_event_count == 0
    assert result.diagnostics.excluded_event_count == 0
    assert result.diagnostics.positive_candidate_count == 0
    assert result.diagnostics.selected_count == 0
    assert result.diagnostics.event_budget_pressure is False
    assert result.diagnostics.character_budget_pressure is False
