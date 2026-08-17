from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from relaylm.events import Event


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

    if max_events < 0:
        raise ValueError("max_events must not be negative")
    if max_chars < 0:
        raise ValueError("max_chars must not be negative")
    if max_events == 0 or max_chars == 0:
        return ()

    query_terms = frozenset(
        term for term in _lexical_terms(query) if len(term) >= 2
    )
    if not query_terms:
        return ()

    excluded = frozenset(exclude_event_ids)
    candidates: list[tuple[int, Event, str, int]] = []
    for index, event in enumerate(events):
        if event.id in excluded or event.type != "message":
            continue
        content = event.payload.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        content_terms = frozenset(_lexical_terms(content))
        score = sum(1 for term in query_terms if term in content_terms)
        if score <= 0:
            continue
        candidates.append((index, event, content, score))

    ranked = sorted(candidates, key=lambda item: (-item[3], -item[0]))

    selected: list[tuple[int, Event]] = []
    used_chars = 0
    for index, event, content, _score in ranked:
        if len(selected) >= max_events:
            break
        cost = len(content)
        if cost > max_chars - used_chars:
            continue
        selected.append((index, event))
        used_chars += cost

    selected.sort(key=lambda item: item[0])
    return tuple(event for _, event in selected)


def _lexical_terms(text: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", text).casefold().replace("_", " ")
    return tuple(term for term in re.split(r"[^\w]+", normalized) if term)
