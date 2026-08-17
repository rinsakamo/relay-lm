from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from relaylm.events import Event
from relaylm.retrieval_lexical import lexical_query_terms, lexical_terms


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


class EventDiscoveryIndex:
    """Rebuildable process-local lexical lookup over already validated Events.

    The index is acceleration only. Event Journal validation and lifecycle ownership
    remain with the persistence boundary that constructs and invalidates it.
    """

    _NON_MESSAGE = "non_message"
    _BLANK = "blank"
    _ELIGIBLE = "eligible"

    def __init__(self, events: Iterable[Event] = ()) -> None:
        self._events: list[Event] = []
        self._term_indexes: dict[str, list[int]] = {}
        self._id_indexes: dict[str, list[int]] = {}
        self._classifications: list[str] = []
        self._non_message_count = 0
        self._blank_content_count = 0
        self._eligible_message_count = 0
        for event in events:
            self.append(event)

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def non_message_count(self) -> int:
        return self._non_message_count

    @property
    def blank_content_count(self) -> int:
        return self._blank_content_count

    @property
    def eligible_message_count(self) -> int:
        return self._eligible_message_count

    def append(self, event: Event) -> None:
        """Extend the derived lookup for one already-authoritative owned append."""

        index = len(self._events)
        self._events.append(event)
        self._id_indexes.setdefault(event.id, []).append(index)

        if event.type != "message":
            self._classifications.append(self._NON_MESSAGE)
            self._non_message_count += 1
            return

        content = event.payload.get("content")
        if not isinstance(content, str) or not content.strip():
            self._classifications.append(self._BLANK)
            self._blank_content_count += 1
            return

        self._classifications.append(self._ELIGIBLE)
        self._eligible_message_count += 1
        for term in frozenset(lexical_terms(content)):
            self._term_indexes.setdefault(term, []).append(index)

    def event_at(self, index: int) -> Event:
        return self._events[index]

    def indexes_for_event_ids(self, event_ids: Iterable[str]) -> frozenset[int]:
        indexes: set[int] = set()
        for event_id in event_ids:
            indexes.update(self._id_indexes.get(event_id, ()))
        return frozenset(indexes)

    def classification_at(self, index: int) -> str:
        return self._classifications[index]

    def candidate_scores(self, query_terms: Iterable[str]) -> dict[int, int]:
        scores: dict[int, int] = {}
        for term in frozenset(query_terms):
            for index in self._term_indexes.get(term, ()):
                scores[index] = scores.get(index, 0) + 1
        return scores


def select_event_evidence(
    *,
    events: Iterable[Event] | EventDiscoveryIndex,
    query: str,
    max_events: int,
    max_chars: int,
    exclude_event_ids: Iterable[str] = (),
) -> tuple[Event, ...]:
    """Select bounded relevant persisted message Events as occurrence evidence.

    The source is expected to represent Event Journal chronology. Selection is
    relevance-first, uses source order as the deterministic recency tie-break, and
    restores the selected Events to source chronology before returning them. A
    derived ``EventDiscoveryIndex`` avoids full-snapshot inspection while retaining
    the same selector semantics.
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
    events: Iterable[Event] | EventDiscoveryIndex,
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
    events: Iterable[Event] | EventDiscoveryIndex,
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

    query_terms = lexical_query_terms(query)
    if not query_terms:
        return _empty_retrieval_result(
            mode="no_query_terms",
            max_events=max_events,
            max_chars=max_chars,
        )

    excluded = frozenset(exclude_event_ids)
    if isinstance(events, EventDiscoveryIndex):
        return _select_indexed_event_evidence(
            source=events,
            query_terms=query_terms,
            max_events=max_events,
            max_chars=max_chars,
            excluded=excluded,
        )
    return _select_iterable_event_evidence(
        events=events,
        query_terms=query_terms,
        max_events=max_events,
        max_chars=max_chars,
        excluded=excluded,
    )


def _select_indexed_event_evidence(
    *,
    source: EventDiscoveryIndex,
    query_terms: frozenset[str],
    max_events: int,
    max_chars: int,
    excluded: frozenset[str],
) -> EventRetrievalResult:
    excluded_indexes = source.indexes_for_event_ids(excluded)
    excluded_non_message = 0
    excluded_blank = 0
    excluded_eligible = 0
    for index in excluded_indexes:
        classification = source.classification_at(index)
        if classification == EventDiscoveryIndex._NON_MESSAGE:
            excluded_non_message += 1
        elif classification == EventDiscoveryIndex._BLANK:
            excluded_blank += 1
        else:
            excluded_eligible += 1

    scores = source.candidate_scores(query_terms)
    for index in excluded_indexes:
        scores.pop(index, None)

    candidates: list[tuple[int, Event, str, int]] = []
    for index, score in scores.items():
        event = source.event_at(index)
        content = event.payload["content"]
        candidates.append((index, event, content, score))

    return _rank_and_admit_candidates(
        candidates=candidates,
        input_event_count=source.event_count,
        excluded_event_count=len(excluded_indexes),
        non_message_count=source.non_message_count - excluded_non_message,
        blank_content_count=source.blank_content_count - excluded_blank,
        eligible_message_count=source.eligible_message_count - excluded_eligible,
        max_events=max_events,
        max_chars=max_chars,
    )


def _select_iterable_event_evidence(
    *,
    events: Iterable[Event],
    query_terms: frozenset[str],
    max_events: int,
    max_chars: int,
    excluded: frozenset[str],
) -> EventRetrievalResult:
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
        content_terms = frozenset(lexical_terms(content))
        score = sum(1 for term in query_terms if term in content_terms)
        if score <= 0:
            continue
        candidates.append((index, event, content, score))

    return _rank_and_admit_candidates(
        candidates=candidates,
        input_event_count=input_event_count,
        excluded_event_count=excluded_event_count,
        non_message_count=non_message_count,
        blank_content_count=blank_content_count,
        eligible_message_count=eligible_message_count,
        max_events=max_events,
        max_chars=max_chars,
    )


def _rank_and_admit_candidates(
    *,
    candidates: list[tuple[int, Event, str, int]],
    input_event_count: int,
    excluded_event_count: int,
    non_message_count: int,
    blank_content_count: int,
    eligible_message_count: int,
    max_events: int,
    max_chars: int,
) -> EventRetrievalResult:
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
