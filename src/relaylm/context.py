from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState, STATE_CLASS_DEFINITIONS


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
) -> CognitiveInput:
    """Build bounded cognitive context from RelayLM-owned authorities."""

    if max_working_context_events < 0:
        raise ValueError("max_working_context_events must not be negative")
    if max_working_context_chars < 0:
        raise ValueError("max_working_context_chars must not be negative")

    active_state = tuple(
        record
        for record in state.states
        if record.status == "active" and record.valid_to is None
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
