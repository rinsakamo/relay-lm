from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from relaylm.cognitive import CognitiveInput, ContextItem, EventEvidenceItem, RetrievedMemoryItem
from relaylm.continuity import ContinuityContext
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_retrieval import MemoryChunk
from relaylm.memory_shadow import memory_chunk_is_shadowed
from relaylm.retrieval_lexical import lexical_query_terms
from relaylm.state import CanonicalState, STATE_CLASS_DEFINITIONS, StateRecord


DEFAULT_WORKING_CONTEXT_MAX_EVENTS = 6
DEFAULT_WORKING_CONTEXT_MAX_CHARS = 4000
_PROJECTED_CONTINUITY_KINDS = frozenset({"referent", "unresolved", "active_task"})
_SUBJECTIVE_CORE_STATE_CLASSES = frozenset({"self.belief", "relationship.state"})
_STATE_ADMISSION_PRIORITY = {
    "anchor": 0,
    "subjective_core": 1,
    "context_linked": 2,
    "lexical": 3,
}


@dataclass(frozen=True, slots=True)
class ContextSelectionDiagnostics:
    layer: str
    mode: str
    eligible_count: int
    selected_count: int
    evicted_count: int
    budget_unit: str
    budget_limit: int | None
    budget_used: int
    budget_pressure: bool
    selected_lexical_match_count: int = 0
    selected_fallback_count: int = 0
    evicted_budget_limit_count: int = 0
    authority_suppressed_count: int = 0
    current_event_excluded_count: int = 0
    redundancy_overlap_count: int = 0
    character_budget_limit: int | None = None
    character_budget_used: int = 0
    evicted_event_window_count: int = 0
    evicted_character_budget_count: int = 0
    evicted_orphan_assistant_count: int = 0


@dataclass(frozen=True, slots=True)
class StateContextSelectionDiagnostics(ContextSelectionDiagnostics):
    relevance_admitted_count: int = 0
    relevance_culled_count: int = 0
    anchor_admitted_count: int = 0
    subjective_core_admitted_count: int = 0
    context_linked_admitted_count: int = 0
    lexical_admitted_count: int = 0
    budget_evicted_count: int = 0


@dataclass(frozen=True, slots=True)
class CognitiveCompilationResult:
    cognitive_input: CognitiveInput
    diagnostics: tuple[ContextSelectionDiagnostics, ...]


@dataclass(frozen=True, slots=True)
class _StateWorkingSetCandidate:
    index: int
    record: StateRecord
    reason: str
    relevance_score: int


@dataclass(frozen=True, slots=True)
class _StateWorkingSet:
    eligible: tuple[StateRecord, ...]
    admitted: tuple[_StateWorkingSetCandidate, ...]
    selected: tuple[_StateWorkingSetCandidate, ...]


def compile_cognitive_input(
    *,
    identity: Identity,
    state: CanonicalState,
    current_event: Event,
    recent_events: Iterable[Event] = (),
    continuity_context: ContinuityContext | None = None,
    retrieved_memory: Iterable[MemoryChunk] = (),
    event_evidence: Iterable[Event] = (),
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

    continuity = _project_accepted_continuity(continuity_context)
    working_context = _select_working_context(
        recent_events=recent_events,
        current_event=current_event,
        max_events=max_working_context_events,
        max_chars=max_working_context_chars,
    )
    active_state = _select_active_state(
        state=state,
        current_event=current_event,
        continuity=continuity,
        working_context=working_context,
        max_records=max_state_records,
    )
    filtered_memory = _filter_retrieved_memory_against_active_state(
        retrieved_memory=retrieved_memory,
        state=state,
    )
    memory = tuple(
        RetrievedMemoryItem(content=chunk.content, location=chunk.location)
        for chunk in filtered_memory
    )
    evidence = _project_event_evidence(
        event_evidence=event_evidence,
        current_event=current_event,
        working_context=working_context,
    )
    return CognitiveInput(
        identity=identity,
        state_classes=STATE_CLASS_DEFINITIONS,
        state=active_state,
        context=continuity + working_context,
        input=current_event,
        memory=memory,
        event_evidence=evidence,
    )


def compile_cognitive_input_with_diagnostics(
    *,
    identity: Identity,
    state: CanonicalState,
    current_event: Event,
    recent_events: Iterable[Event] = (),
    continuity_context: ContinuityContext | None = None,
    retrieved_memory: Iterable[MemoryChunk] = (),
    event_evidence: Iterable[Event] = (),
    max_working_context_events: int = DEFAULT_WORKING_CONTEXT_MAX_EVENTS,
    max_working_context_chars: int = DEFAULT_WORKING_CONTEXT_MAX_CHARS,
    max_state_records: int | None = None,
) -> CognitiveCompilationResult:
    """Build cognitive input plus opt-in content-free selection diagnostics."""

    recent_event_sequence = tuple(recent_events)
    retrieved_memory_sequence = tuple(retrieved_memory)
    event_evidence_sequence = tuple(event_evidence)
    projected_continuity = _project_accepted_continuity(continuity_context)
    cognitive_input = compile_cognitive_input(
        identity=identity,
        state=state,
        current_event=current_event,
        recent_events=recent_event_sequence,
        continuity_context=continuity_context,
        retrieved_memory=retrieved_memory_sequence,
        event_evidence=event_evidence_sequence,
        max_working_context_events=max_working_context_events,
        max_working_context_chars=max_working_context_chars,
        max_state_records=max_state_records,
    )
    selected_working_context = cognitive_input.context[len(projected_continuity) :]
    return CognitiveCompilationResult(
        cognitive_input=cognitive_input,
        diagnostics=(
            _diagnose_active_state_selection(
                state=state,
                current_event=current_event,
                continuity=projected_continuity,
                working_context=selected_working_context,
                max_records=max_state_records,
                selected_state=cognitive_input.state,
            ),
            _diagnose_working_context_selection(
                recent_events=recent_event_sequence,
                current_event=current_event,
                selected_context=selected_working_context,
                max_events=max_working_context_events,
                max_chars=max_working_context_chars,
            ),
            _diagnose_retrieved_memory_projection(
                retrieved_memory=retrieved_memory_sequence,
                selected_memory=cognitive_input.memory,
            ),
            _diagnose_event_evidence_projection(
                event_evidence=event_evidence_sequence,
                current_event=current_event,
                selected_evidence=cognitive_input.event_evidence,
                working_context=selected_working_context,
            ),
        ),
    )


def _select_active_state(
    *,
    state: CanonicalState,
    current_event: Event,
    continuity: tuple[ContextItem, ...],
    working_context: tuple[ContextItem, ...],
    max_records: int | None,
) -> tuple[StateRecord, ...]:
    working_set = _build_state_working_set(
        state=state,
        current_event=current_event,
        continuity=continuity,
        working_context=working_context,
        max_records=max_records,
    )
    return tuple(candidate.record for candidate in working_set.selected)


def _build_state_working_set(
    *,
    state: CanonicalState,
    current_event: Event,
    continuity: tuple[ContextItem, ...],
    working_context: tuple[ContextItem, ...],
    max_records: int | None,
) -> _StateWorkingSet:
    eligible = tuple(
        record
        for record in state.states
        if record.status == "active" and record.valid_to is None
    )
    current_content = current_event.payload.get("content")
    direct_query = current_content if isinstance(current_content, str) else ""
    context_query = "\n".join(
        item.content for item in continuity + working_context if item.content.strip()
    )
    context_source_ids = {
        source
        for item in continuity + working_context
        for source in item.sources
    }

    admitted: list[_StateWorkingSetCandidate] = []
    for index, record in enumerate(eligible):
        direct_score = _state_lexical_score(record, direct_query)
        context_score = _state_lexical_score(record, context_query)
        if record.state_class == "user.identity":
            reason = "anchor"
        elif record.state_class in _SUBJECTIVE_CORE_STATE_CLASSES:
            reason = "subjective_core"
        elif context_source_ids.intersection(record.sources) or context_score > 0:
            reason = "context_linked"
        elif direct_score > 0:
            reason = "lexical"
        else:
            continue
        admitted.append(
            _StateWorkingSetCandidate(
                index=index,
                record=record,
                reason=reason,
                relevance_score=max(direct_score, context_score),
            )
        )

    admitted_tuple = tuple(admitted)
    if max_records is None:
        selected = admitted_tuple
    elif max_records == 0:
        selected = ()
    elif len(admitted_tuple) <= max_records:
        selected = admitted_tuple
    else:
        ranked = sorted(
            admitted_tuple,
            key=lambda candidate: (
                _STATE_ADMISSION_PRIORITY[candidate.reason],
                -candidate.relevance_score,
                candidate.index,
            ),
        )
        selected_indices = {
            candidate.index for candidate in ranked[:max_records]
        }
        selected = tuple(
            candidate
            for candidate in admitted_tuple
            if candidate.index in selected_indices
        )

    return _StateWorkingSet(
        eligible=eligible,
        admitted=admitted_tuple,
        selected=selected,
    )


def _diagnose_active_state_selection(
    *,
    state: CanonicalState,
    current_event: Event,
    continuity: tuple[ContextItem, ...],
    working_context: tuple[ContextItem, ...],
    max_records: int | None,
    selected_state: tuple[StateRecord, ...],
) -> StateContextSelectionDiagnostics:
    working_set = _build_state_working_set(
        state=state,
        current_event=current_event,
        continuity=continuity,
        working_context=working_context,
        max_records=max_records,
    )
    selected_count = len(selected_state)
    relevance_admitted_count = len(working_set.admitted)
    relevance_culled_count = len(working_set.eligible) - relevance_admitted_count
    budget_evicted_count = relevance_admitted_count - selected_count
    evicted_count = relevance_culled_count + budget_evicted_count

    if max_records == 0:
        mode = "zero_budget"
    elif budget_evicted_count:
        mode = "relevance_ranked_budgeted"
    else:
        mode = "relevance_filtered"

    selected_indices = {candidate.index for candidate in working_set.selected}
    selected_lexical_match_count = sum(
        1
        for candidate in working_set.admitted
        if candidate.index in selected_indices and candidate.relevance_score > 0
    )

    return StateContextSelectionDiagnostics(
        layer="canonical_state",
        mode=mode,
        eligible_count=len(working_set.eligible),
        selected_count=selected_count,
        evicted_count=evicted_count,
        budget_unit="records",
        budget_limit=max_records,
        budget_used=selected_count,
        budget_pressure=budget_evicted_count > 0,
        selected_lexical_match_count=selected_lexical_match_count,
        selected_fallback_count=0,
        evicted_budget_limit_count=budget_evicted_count,
        relevance_admitted_count=relevance_admitted_count,
        relevance_culled_count=relevance_culled_count,
        anchor_admitted_count=sum(
            candidate.reason == "anchor" for candidate in working_set.admitted
        ),
        subjective_core_admitted_count=sum(
            candidate.reason == "subjective_core"
            for candidate in working_set.admitted
        ),
        context_linked_admitted_count=sum(
            candidate.reason == "context_linked"
            for candidate in working_set.admitted
        ),
        lexical_admitted_count=sum(
            candidate.reason == "lexical" for candidate in working_set.admitted
        ),
        budget_evicted_count=budget_evicted_count,
    )


def _diagnose_working_context_selection(
    *,
    recent_events: tuple[Event, ...],
    current_event: Event,
    selected_context: tuple[ContextItem, ...],
    max_events: int,
    max_chars: int,
) -> ContextSelectionDiagnostics:
    current_event_excluded_count = sum(
        1 for event in recent_events if event.id == current_event.id
    )
    eligible_events = tuple(
        event
        for event in recent_events
        if event.id != current_event.id
        and event.type == "message"
        and event.actor in {"user", "assistant"}
        and isinstance(event.payload.get("content"), str)
        and bool(event.payload["content"].strip())
    )
    eligible_count = len(eligible_events)
    selected_count = len(selected_context)

    if max_events == 0:
        window: tuple[Event, ...] = ()
    else:
        window = eligible_events[-max_events:]
    event_window_evicted_count = eligible_count - len(window)

    orphan_assistant_count = 0
    if max_chars > 0:
        index = len(window) - 1
        while index >= 0:
            event = window[index]
            if event.actor == "assistant":
                if index == 0 or window[index - 1].actor != "user":
                    orphan_assistant_count += 1
                    index -= 1
                    continue
                index -= 2
                continue
            index -= 1

    after_window_and_orphan_count = len(window) - orphan_assistant_count
    character_budget_evicted_count = max(
        0,
        after_window_and_orphan_count - selected_count,
    )
    evicted_count = eligible_count - selected_count
    character_budget_used = sum(len(item.content) for item in selected_context)

    if max_events == 0 or max_chars == 0:
        mode = "zero_budget"
    elif evicted_count > 0:
        mode = "budget_filtered"
    else:
        mode = "within_budget"

    return ContextSelectionDiagnostics(
        layer="working_context",
        mode=mode,
        eligible_count=eligible_count,
        selected_count=selected_count,
        evicted_count=evicted_count,
        budget_unit="events",
        budget_limit=max_events,
        budget_used=selected_count,
        budget_pressure=evicted_count > 0,
        current_event_excluded_count=current_event_excluded_count,
        character_budget_limit=max_chars,
        character_budget_used=character_budget_used,
        evicted_event_window_count=event_window_evicted_count,
        evicted_character_budget_count=character_budget_evicted_count,
        evicted_orphan_assistant_count=orphan_assistant_count,
    )


def _diagnose_retrieved_memory_projection(
    *,
    retrieved_memory: tuple[MemoryChunk, ...],
    selected_memory: tuple[RetrievedMemoryItem, ...],
) -> ContextSelectionDiagnostics:
    eligible_count = len(retrieved_memory)
    selected_count = len(selected_memory)
    suppressed_count = eligible_count - selected_count
    return ContextSelectionDiagnostics(
        layer="retrieved_memory",
        mode="authority_filtered" if suppressed_count else "pass_through",
        eligible_count=eligible_count,
        selected_count=selected_count,
        evicted_count=suppressed_count,
        budget_unit="chunks",
        budget_limit=None,
        budget_used=selected_count,
        budget_pressure=False,
        authority_suppressed_count=suppressed_count,
    )


def _diagnose_event_evidence_projection(
    *,
    event_evidence: tuple[Event, ...],
    current_event: Event,
    selected_evidence: tuple[EventEvidenceItem, ...],
    working_context: tuple[ContextItem, ...],
) -> ContextSelectionDiagnostics:
    selected_count = len(selected_evidence)
    current_event_excluded_count = sum(
        1 for event in event_evidence if event.id == current_event.id
    )
    working_context_source_ids = {
        source
        for item in working_context
        for source in item.sources
    }
    redundancy_overlap_count = sum(
        1
        for event in event_evidence
        if event.id != current_event.id and event.id in working_context_source_ids
    )
    if current_event_excluded_count and redundancy_overlap_count:
        mode = "current_event_and_working_context_deduplicated"
    elif current_event_excluded_count:
        mode = "current_event_deduplicated"
    elif redundancy_overlap_count:
        mode = "working_context_deduplicated"
    else:
        mode = "pass_through"

    return ContextSelectionDiagnostics(
        layer="event_evidence",
        mode=mode,
        eligible_count=len(event_evidence),
        selected_count=selected_count,
        evicted_count=len(event_evidence) - selected_count,
        budget_unit="events",
        budget_limit=None,
        budget_used=selected_count,
        budget_pressure=False,
        current_event_excluded_count=current_event_excluded_count,
        redundancy_overlap_count=redundancy_overlap_count,
    )


def _project_accepted_continuity(
    continuity_context: ContinuityContext | None,
) -> tuple[ContextItem, ...]:
    if continuity_context is None:
        return ()

    return tuple(
        ContextItem(
            content=json.dumps(
                {
                    "continuity": {
                        "kind": item.kind,
                        "key": item.key,
                        "value": _continuity_value_for_projection(item.value),
                        "epistemic_role": item.epistemic_role,
                    }
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
            sources=item.sources,
        )
        for item in continuity_context.items
        if item.kind in _PROJECTED_CONTINUITY_KINDS
    )


def _continuity_value_for_projection(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _continuity_value_for_projection(nested)
            for key, nested in value.items()
        }
    if isinstance(value, tuple):
        return [_continuity_value_for_projection(nested) for nested in value]
    return value


def _project_event_evidence(
    *,
    event_evidence: Iterable[Event],
    current_event: Event,
    working_context: tuple[ContextItem, ...],
) -> tuple[EventEvidenceItem, ...]:
    working_context_source_ids = {
        source
        for item in working_context
        for source in item.sources
    }
    projected: list[EventEvidenceItem] = []
    for event in event_evidence:
        if event.id == current_event.id or event.id in working_context_source_ids:
            continue
        content = event.payload.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                "event evidence Event must contain non-empty string payload.content"
            )
        projected.append(
            EventEvidenceItem(
                event_id=event.id,
                event_type=event.type,
                actor=event.actor,
                timestamp=event.timestamp,
                content=content,
            )
        )
    return tuple(projected)


def _filter_retrieved_memory_against_active_state(
    *,
    retrieved_memory: Iterable[MemoryChunk],
    state: CanonicalState,
) -> tuple[MemoryChunk, ...]:
    """Suppress lower-authority current/unknown explicit State shadows against active State."""

    active_state = tuple(
        record
        for record in state.states
        if record.status == "active" and record.valid_to is None
    )
    if not active_state:
        return tuple(retrieved_memory)

    return tuple(
        chunk
        for chunk in retrieved_memory
        if not memory_chunk_is_shadowed(chunk=chunk, active_state=active_state)
    )


def _state_lexical_score(record: StateRecord, query: str) -> int:
    query_terms = lexical_query_terms(query)
    if not query_terms:
        return 0

    key_overlap = _bounded_state_feature_overlap(query_terms, record.key)
    if key_overlap:
        return 100 + min(key_overlap, 9)

    value_overlap = sum(
        _bounded_state_feature_overlap(query_terms, value_text)
        for value_text in _value_lexical_strings(record.value)
    )
    if value_overlap:
        return 10 + min(value_overlap, 9)

    class_tail = record.state_class.rsplit(".", 1)[-1]
    class_overlap = _bounded_state_feature_overlap(query_terms, class_tail)
    if class_overlap:
        return 1 + min(class_overlap, 8)
    return 0


def _bounded_state_feature_overlap(query_terms: frozenset[str], text: str) -> int:
    field_terms = lexical_query_terms(text)
    overlap = query_terms.intersection(field_terms)
    if not overlap:
        return 0
    if any(term.isascii() for term in overlap):
        return len(overlap)
    if len(overlap) >= 2 or overlap == field_terms:
        return len(overlap)
    return 0


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
