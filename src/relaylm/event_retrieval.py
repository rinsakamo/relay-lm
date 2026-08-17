from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from relaylm.events import Event


@dataclass(frozen=True, slots=True)
class EventRetrievalDiagnostics:
    """Content-free aggregate observations from one Event retrieval attempt."""

    mode: str
    input_event_count: int
    excluded_event_count: int
    non_message_count: int
    blank_content_count: int
    eligible_message_count: int
    positive_candidate_count: int
    selected_count: int
    event_budget_limit: int
    character_budget_limit: int
    character_budget_used: int
    skipped_character_budget_count: int
    unadmitted_event_limit_count: int
    event_budget_pressure: bool
    character_budget_pressure: bool


@dataclass(frozen=True, slots=True)
class EventRetrievalResult:
    events: tuple[Event, ...]
    diagnostics: EventRetrievalDiagnostics


def select_event_evidence(
    *,
    events: Iterable[Event],
    query: str,
    max_events: int,
    max_chars: int,
    exclude_event_ids: Iterable[str] = (),
) -> tuple[Event, ...]:
    """Select bounded relevant persisted message Events as occurrence evidence.

    The input iterable is expected to be in Event Journal chronology. Selection is
    relevance-first, uses source order as the deterministic recency tie-break, and
    restores the selected Events to source chronology before returning them.
    """

    return _select_event_evidence(
        events=events,
        query=query,
        max_events=max_events,
        max_chars=max_chars,
        exclude_event_ids=exclude_event_ids,
    ).events


def select_event_evidence_with_diagnostics(
    *,
    events: Iterable[Event],
    query: str,
    max_events: int,
    max_chars: int,
    exclude_event_ids: Iterable[str] = (),
) -> EventRetrievalResult:
    """Select Event evidence and return content-free retrieval-stage diagnostics."""

    return _select_event_evidence(
        events=events,
        query=query,
        max_events=max_events,
        max_chars=max_chars,
        exclude_event_ids=exclude_event_ids,
    )


def _select_event_evidence(
    *,
    events: Iterable[Event],
    query: str,
    max_events: int,
    max_chars: int,
    exclude_event_ids: Iterable[str],
) -> EventRetrievalResult:
    if max_events < 0:
        raise ValueError("max_events must not be negative")
    if max_chars < 0:
        raise ValueError("max_chars must not be negative")
    if max_events == 0 or max_chars == 0:
        return _empty_retrieval_result(
            mode="zero_budget",
            max_events=max_events,
            max_chars=max_chars,
        )

    query_terms = frozenset(
        term for term in _lexical_terms(query) if len(term) >= 2
    )
    if not query_terms:
        return _empty_retrieval_result(
            mode="no_query_terms",
            max_events=max_events,
            max_chars=max_chars,
        )

    excluded = frozenset(exclude_event_ids)
    candidates: list[tuple[int, Event, str, int]] = []
    input_event_count = 0
    excluded_event_count = 0
    non_message_count = 0
    blank_content_count = 0
    eligible_message_count = 0
    for index, event in enumerate(events):
        input_event_count += 1
        if event.id in excluded:
            excluded_event_count += 1
            continue
        if event.type != "message":
            non_message_count += 1
            continue
        content = event.payload.get("content")
        if not isinstance(content, str) or not content.strip():
            blank_content_count += 1
            continue
        eligible_message_count += 1
        content_terms = frozenset(_lexical_terms(content))
        score = sum(1 for term in query_terms if term in content_terms)
        if score <= 0:
            continue
        candidates.append((index, event, content, score))

    ranked = sorted(candidates, key=lambda item: (-item[3], -item[0]))

    selected: list[tuple[int, Event]] = []
    used_chars = 0
    skipped_character_budget_count = 0
    unadmitted_event_limit_count = 0
    for index, event, content, _score in ranked:
        if len(selected) >= max_events:
            unadmitted_event_limit_count += 1
            continue
        cost = len(content)
        if cost > max_chars - used_chars:
            skipped_character_budget_count += 1
            continue
        selected.append((index, event))
        used_chars += cost

    selected.sort(key=lambda item: item[0])
    selected_events = tuple(event for _, event in selected)
    return EventRetrievalResult(
        events=selected_events,
        diagnostics=EventRetrievalDiagnostics(
            mode="lexical",
            input_event_count=input_event_count,
            excluded_event_count=excluded_event_count,
            non_message_count=non_message_count,
            blank_content_count=blank_content_count,
            eligible_message_count=eligible_message_count,
            positive_candidate_count=len(ranked),
            selected_count=len(selected_events),
            event_budget_limit=max_events,
            character_budget_limit=max_chars,
            character_budget_used=used_chars,
            skipped_character_budget_count=skipped_character_budget_count,
            unadmitted_event_limit_count=unadmitted_event_limit_count,
            event_budget_pressure=unadmitted_event_limit_count > 0,
            character_budget_pressure=skipped_character_budget_count > 0,
        ),
    )


def _empty_retrieval_result(
    *,
    mode: str,
    max_events: int,
    max_chars: int,
) -> EventRetrievalResult:
    return EventRetrievalResult(
        events=(),
        diagnostics=EventRetrievalDiagnostics(
            mode=mode,
            input_event_count=0,
            excluded_event_count=0,
            non_message_count=0,
            blank_content_count=0,
            eligible_message_count=0,
            positive_candidate_count=0,
            selected_count=0,
            event_budget_limit=max_events,
            character_budget_limit=max_chars,
            character_budget_used=0,
            skipped_character_budget_count=0,
            unadmitted_event_limit_count=0,
            event_budget_pressure=False,
            character_budget_pressure=False,
        ),
    )


def _lexical_terms(text: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", text).casefold().replace("_", " ")
    return tuple(term for term in re.split(r"[^\w]+", normalized) if term)
