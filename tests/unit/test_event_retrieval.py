from __future__ import annotations

import pytest

from relaylm.event_retrieval import select_event_evidence
from relaylm.events import Event


def _event(
    event_id: str,
    *,
    content: str,
    actor: str = "user",
    event_type: str = "message",
    timestamp: str = "2026-08-17T00:00:00+00:00",
) -> Event:
    return Event(
        id=event_id,
        type=event_type,
        actor=actor,
        timestamp=timestamp,
        payload={"content": content},
    )


def test_selects_only_positive_relevant_message_events() -> None:
    events = (
        _event("tea", content="Rin likes tea."),
        _event("coffee", content="Rin prefers coffee now."),
        _event("travel", content="Rin visited Fukuoka."),
    )

    selected = select_event_evidence(
        events=events,
        query="What did I say about coffee?",
        max_events=2,
        max_chars=200,
    )

    assert selected == (events[1],)


def test_irrelevant_events_have_no_zero_match_fallback() -> None:
    events = (
        _event("tea", content="Rin likes tea."),
        _event("travel", content="Rin visited Fukuoka."),
    )

    selected = select_event_evidence(
        events=events,
        query="astronomy",
        max_events=2,
        max_chars=200,
    )

    assert selected == ()


def test_explicitly_excluded_current_event_is_not_returned() -> None:
    prior = _event("prior", content="Coffee is good.")
    current = _event("current", content="Coffee coffee coffee.")

    selected = select_event_evidence(
        events=(prior, current),
        query="coffee",
        max_events=1,
        max_chars=200,
        exclude_event_ids=(current.id,),
    )

    assert selected == (prior,)


def test_oversized_relevant_event_is_skipped_not_truncated() -> None:
    oversized = _event(
        "oversized",
        content="Coffee " + "details " * 30,
    )
    summary = _event("summary", content="Coffee summary.")

    selected = select_event_evidence(
        events=(oversized, summary),
        query="coffee",
        max_events=2,
        max_chars=len(summary.payload["content"]),
    )

    assert selected == (summary,)
    assert selected[0].payload["content"] == "Coffee summary."


def test_higher_relevance_controls_admission_but_output_restores_chronology() -> None:
    older = _event("older", content="Coffee preference changed.")
    middle = _event("middle", content="Coffee was mentioned.")
    newer = _event("newer", content="Preference for coffee was confirmed.")

    selected = select_event_evidence(
        events=(older, middle, newer),
        query="coffee preference",
        max_events=2,
        max_chars=300,
    )

    assert selected == (older, newer)


def test_equal_relevance_prefers_newer_occurrence_at_cutoff() -> None:
    older = _event("older", content="Coffee note.")
    newer = _event("newer", content="Coffee update.")

    selected = select_event_evidence(
        events=(older, newer),
        query="coffee",
        max_events=1,
        max_chars=200,
    )

    assert selected == (newer,)


def test_exact_token_matching_does_not_match_substrings() -> None:
    likes = _event("likes", content="Rin likes tea.")
    dislikes = _event("dislikes", content="Rin dislikes coffee.")

    selected = select_event_evidence(
        events=(dislikes, likes),
        query="likes",
        max_events=2,
        max_chars=200,
    )

    assert selected == (likes,)


def test_non_message_and_blank_content_events_are_ineligible() -> None:
    non_message = _event("tool", content="coffee", event_type="tool")
    blank = _event("blank", content="   ")
    valid = _event("valid", content="coffee")

    selected = select_event_evidence(
        events=(non_message, blank, valid),
        query="coffee",
        max_events=3,
        max_chars=100,
    )

    assert selected == (valid,)


def test_zero_and_negative_budgets_are_explicit_and_input_is_unchanged() -> None:
    events = (_event("coffee", content="Coffee note."),)
    original = events

    assert select_event_evidence(
        events=events,
        query="coffee",
        max_events=0,
        max_chars=100,
    ) == ()
    assert select_event_evidence(
        events=events,
        query="coffee",
        max_events=1,
        max_chars=0,
    ) == ()
    assert events == original

    with pytest.raises(ValueError, match="max_events must not be negative"):
        select_event_evidence(
            events=events,
            query="coffee",
            max_events=-1,
            max_chars=100,
        )
    with pytest.raises(ValueError, match="max_chars must not be negative"):
        select_event_evidence(
            events=events,
            query="coffee",
            max_events=1,
            max_chars=-1,
        )
