from __future__ import annotations

import re
import unicodedata
from collections import deque
from collections.abc import Iterable
from typing import Any

from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState, STATE_CLASS_DEFINITIONS, StateRecord


DEFAULT_WORKING_CONTEXT_MAX_EVENTS = 6
DEFAULT_WORKING_CONTEXT_MAX_CHARS = 4000


def compile_cognitive_input(
    *,
    identity: Identity,
    state: CanonicalState,
    current_event: Event,
    recent_events: Iterable[Event] = (),
    max_working_context_events: int = DEFAULT_WORKING_CONTEXT_MAX_EVENTS,
    max_working_context_chars: int = DEFAULT_WORKING_CONTEXT_MAX_CHARS,
    max_state_records: int | None = None,
) -> CognitiveInput:
    """Build bounded cognitive context from RelayLM-owned authorities."""

    if max_working_context_events < 0:
        raise ValueError("max_working_context_events must not be negative")
    if max_working_context_chars < 0:
        raise ValueError("max_working_context_chars must not be negative")
    if max_state_records is not None and max_state_records < 0:
        raise ValueError("max_state_records must not be negative")

    active_state = _select_active_state(
        state=state,
        current_event=current_event,
        max_records=max_state_records,
    )
    working_context = _select_working_context(
        recent_events=recent_events,
        current_event=current_event,
        max_events=max_working_context_events,
        max_chars=max_working_context_chars,
    )
    return CognitiveInput(
        identity=identity,
        state_classes=STATE_CLASS_DEFINITIONS,
        state=active_state,
        context=working_context,
        input=current_event,
    )


def _select_active_state(
    *,
    state: CanonicalState,
    current_event: Event,
    max_records: int | None,
) -> tuple[StateRecord, ...]:
    """Select eligible active State, applying lexical ranking only under an explicit cap."""

    active_state = tuple(
        record
        for record in state.states
        if record.status == "active" and record.valid_to is None
    )
    if max_records is None or len(active_state) <= max_records:
        return active_state
    if max_records == 0:
        return ()

    content = current_event.payload.get("content")
    query = _normalize_lexical_text(content if isinstance(content, str) else "")
    ranked = sorted(
        enumerate(active_state),
        key=lambda item: (-_state_lexical_score(item[1], query), item[0]),
    )
    selected_indices = sorted(index for index, _ in ranked[:max_records])
    return tuple(active_state[index] for index in selected_indices)


def _state_lexical_score(record: StateRecord, query: str) -> int:
    if not query:
        return 0

    score = 0
    key = _normalize_lexical_text(record.key)
    key_phrase = key.replace("_", " ")
    if (key and key in query) or (key_phrase and key_phrase in query):
        score += 8
    for term in _lexical_terms(record.key):
        if len(term) >= 2 and term in query:
            score += 4

    for value_text in _value_lexical_strings(record.value):
        normalized_value = _normalize_lexical_text(value_text)
        if normalized_value and normalized_value in query:
            score += 3
        for term in _lexical_terms(value_text):
            if len(term) >= 2 and term in query:
                score += 2

    class_tail = record.state_class.rsplit(".", 1)[-1]
    if _normalize_lexical_text(class_tail) in query:
        score += 1
    return score


def _value_lexical_strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        return tuple(
            text
            for nested in value.values()
            for text in _value_lexical_strings(nested)
        )
    if isinstance(value, (list, tuple)):
        return tuple(
            text
            for nested in value
            for text in _value_lexical_strings(nested)
        )
    if value is None or isinstance(value, bool):
        return ()
    if isinstance(value, (int, float)):
        return (str(value),)
    return ()


def _normalize_lexical_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def _lexical_terms(text: str) -> tuple[str, ...]:
    normalized = _normalize_lexical_text(text).replace("_", " ")
    return tuple(term for term in re.split(r"[^\w]+", normalized) if term)


def _select_working_context(
    *,
    recent_events: Iterable[Event],
    current_event: Event,
    max_events: int,
    max_chars: int,
) -> tuple[ContextItem, ...]:
    """Select bounded recent dialogue without treating prompt residence as authority."""

    if max_events == 0 or max_chars == 0:
        return ()

    candidates: deque[Event] = deque(maxlen=max_events)
    for event in recent_events:
        if event.id == current_event.id:
            continue
        if event.type != "message" or event.actor not in {"user", "assistant"}:
            continue
        content = event.payload.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        candidates.append(event)

    events = tuple(candidates)
    exchanges_newest_first: list[tuple[Event, ...]] = []
    index = len(events) - 1
    while index >= 0:
        event = events[index]
        if event.actor == "assistant":
            if index == 0 or events[index - 1].actor != "user":
                index -= 1
                continue
            exchanges_newest_first.append((events[index - 1], event))
            index -= 2
            continue
        exchanges_newest_first.append((event,))
        index -= 1

    selected_exchanges: list[tuple[ContextItem, ...]] = []
    used_chars = 0
    for exchange in exchanges_newest_first:
        cost = sum(len(event.payload["content"]) for event in exchange)
        if cost > max_chars - used_chars:
            break
        selected_exchanges.append(
            tuple(
                ContextItem(
                    content=event.payload["content"],
                    sources=(event.id,),
                    actor=event.actor,
                )
                for event in exchange
            )
        )
        used_chars += cost

    return tuple(
        item
        for exchange in reversed(selected_exchanges)
        for item in exchange
    )
