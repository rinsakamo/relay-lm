from __future__ import annotations

import json
import re
import unicodedata
from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from relaylm.cognitive import CognitiveInput, ContextItem, EventEvidenceItem, RetrievedMemoryItem
from relaylm.continuity import ContinuityContext
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_provenance import MemoryTemporalScope
from relaylm.memory_retrieval import MemoryChunk
from relaylm.state import CanonicalState, STATE_CLASS_DEFINITIONS, StateRecord


DEFAULT_WORKING_CONTEXT_MAX_EVENTS = 6
DEFAULT_WORKING_CONTEXT_MAX_CHARS = 4000
_PROJECTED_CONTINUITY_KINDS = frozenset({"referent", "unresolved", "active_task"})


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
class CognitiveCompilationResult:
    cognitive_input: CognitiveInput
    diagnostics: tuple[ContextSelectionDiagnostics, ...]


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

    active_state = _select_active_state(
        state=state,
        current_event=current_event,
        max_records=max_state_records,
    )
    continuity = _project_accepted_continuity(continuity_context)
    working_context = _select_working_context(
        recent_events=recent_events,
        current_event=current_event,
        max_events=max_working_context_events,
        max_chars=max_working_context_chars,
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


def _diagnose_active_state_selection(
    *,
    state: CanonicalState,
    current_event: Event,
    max_records: int | None,
    selected_state: tuple[StateRecord, ...],
) -> ContextSelectionDiagnostics:
    eligible_count = sum(
        1
        for record in state.states
        if record.status == "active" and record.valid_to is None
    )
    selected_count = len(selected_state)
    evicted_count = eligible_count - selected_count

    if max_records is None:
        mode = "unbounded"
    elif max_records == 0:
        mode = "zero_budget"
    elif eligible_count <= max_records:
        mode = "within_budget"
    else:
        mode = "lexical_ranked"

    lexical_match_count = 0
    fallback_count = 0
    if mode == "lexical_ranked":
        content = current_event.payload.get("content")
        query = _normalize_lexical_text(content if isinstance(content, str) else "")
        lexical_match_count = sum(
            1 for record in selected_state if _state_lexical_score(record, query) > 0
        )
        fallback_count = selected_count - lexical_match_count

    return ContextSelectionDiagnostics(
        layer="canonical_state",
        mode=mode,
        eligible_count=eligible_count,
        selected_count=selected_count,
        evicted_count=evicted_count,
        budget_unit="records",
        budget_limit=max_records,
        budget_used=selected_count,
        budget_pressure=evicted_count > 0,
        selected_lexical_match_count=lexical_match_count,
        selected_fallback_count=fallback_count,
        evicted_budget_limit_count=evicted_count,
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
        if not _memory_chunk_is_shadowed(chunk=chunk, active_state=active_state)
    )


def _memory_chunk_is_shadowed(
    *,
    chunk: MemoryChunk,
    active_state: tuple[StateRecord, ...],
) -> bool:
    if chunk.temporal_authority.temporal_scope is MemoryTemporalScope.HISTORICAL:
        return False

    heading_terms = frozenset(_lexical_terms(" ".join(chunk.heading_path)))

    for record in active_state:
        key_terms = tuple(term for term in _lexical_terms(record.key) if len(term) >= 2)
        heading_addresses_key = bool(key_terms) and all(
            term in heading_terms for term in key_terms
        )
        inline_addresses_key = _contains_explicit_state_key_assignment(
            chunk.content,
            record.key,
        )
        if not heading_addresses_key and not inline_addresses_key:
            if chunk.temporal_authority.temporal_scope is not MemoryTemporalScope.CURRENT:
                continue
            claims = _bounded_freeform_state_key_claims(chunk.content, record.key)
            if isinstance(record.value, bool):
                if any(
                    (claim_value := _explicit_boolean_claim_value(claim)) is not None
                    and claim_value is not record.value
                    for claim in claims
                ):
                    return True
                continue
            degree_value = _reserved_degree_state_value(record.value)
            if degree_value is not None:
                current_semantic, current_degree = degree_value
                for claim in claims:
                    explicit_claim = _explicit_reserved_degree_claim(claim)
                    if explicit_claim is None:
                        continue
                    claimed_semantic, claimed_degree = explicit_claim
                    if (
                        _lexical_terms(claimed_semantic)
                        != _lexical_terms(current_semantic)
                        or claimed_degree != current_degree
                    ):
                        return True
                continue
            current_value = _simple_scalar_state_value_text(record.value)
            if current_value is None:
                continue
            current_terms = _lexical_terms(current_value)
            for claim in claims:
                claim_terms = _lexical_terms(claim)
                if len(claim_terms) > 1 and claim_terms[0] == "not":
                    if claim_terms[1:] == current_terms:
                        return True
                    continue
                if claim_terms != current_terms:
                    return True
            continue

        if isinstance(record.value, bool):
            if heading_addresses_key and inline_addresses_key:
                assignment_values = _explicit_state_key_assignment_values(
                    chunk.content,
                    record.key,
                )
                if len(assignment_values) == 1:
                    assignment_value = _explicit_boolean_claim_value(
                        assignment_values[0]
                    )
                    if assignment_value is not None:
                        if assignment_value is not record.value:
                            return True
                        continue
                elif len(assignment_values) >= 2:
                    assignment_booleans = tuple(
                        _explicit_boolean_claim_value(value)
                        for value in assignment_values
                    )
                    if all(value is not None for value in assignment_booleans):
                        if any(
                            value is not record.value for value in assignment_booleans
                        ):
                            return True
                        continue
            if heading_addresses_key and not inline_addresses_key:
                body_value = _single_atx_heading_body_value(chunk.content)
                if body_value is not None:
                    body_boolean = _explicit_boolean_claim_value(body_value)
                    if body_boolean is not None:
                        if body_boolean is not record.value:
                            return True
                        continue
            if inline_addresses_key and not heading_addresses_key:
                assignment_values = _explicit_state_key_assignment_values(
                    chunk.content,
                    record.key,
                )
                if len(assignment_values) == 1:
                    assignment_value = _explicit_boolean_claim_value(
                        assignment_values[0]
                    )
                    if assignment_value is not None:
                        if assignment_value is not record.value:
                            return True
                        continue
                elif len(assignment_values) >= 2:
                    assignment_booleans = tuple(
                        _explicit_boolean_claim_value(value)
                        for value in assignment_values
                    )
                    if all(value is not None for value in assignment_booleans):
                        if any(
                            value is not record.value for value in assignment_booleans
                        ):
                            return True
                        continue
            if _contains_explicit_opposite_boolean_value(
                chunk.content,
                current_value=record.value,
            ):
                return True
            continue

        degree_value = _reserved_degree_state_value(record.value)
        if degree_value is not None:
            current_semantic, current_degree = degree_value
            if heading_addresses_key and inline_addresses_key:
                assignment_values = _explicit_state_key_assignment_values(
                    chunk.content,
                    record.key,
                )
                if len(assignment_values) == 1:
                    explicit_assignment = _explicit_reserved_degree_claim(
                        assignment_values[0]
                    )
                    if explicit_assignment is not None:
                        assignment_semantic, assignment_degree = explicit_assignment
                        assignment_semantic_terms = _lexical_terms(
                            assignment_semantic
                        )
                        current_semantic_terms = _lexical_terms(current_semantic)
                        if (
                            len(assignment_semantic_terms) > 1
                            and assignment_semantic_terms[0] == "not"
                            and assignment_semantic_terms[1] != "not"
                        ):
                            explicit_degrees = _explicit_degree_hint_assignments(
                                chunk.content,
                                key=record.key,
                                heading_addresses_key=True,
                            )
                            if len(explicit_degrees) == 1:
                                if (
                                    assignment_semantic_terms[1:]
                                    == current_semantic_terms
                                    and assignment_degree == current_degree
                                ):
                                    return True
                                continue
                        if assignment_semantic_terms and (
                            assignment_semantic_terms[0] != "not"
                            and (
                                assignment_semantic_terms != current_semantic_terms
                                or assignment_degree != current_degree
                            )
                        ):
                            return True
                elif len(assignment_values) >= 2:
                    explicit_assignments = tuple(
                        _explicit_reserved_degree_claim(value)
                        for value in assignment_values
                    )
                    if all(
                        assignment is not None
                        and _lexical_terms(assignment[0])[0] != "not"
                        for assignment in explicit_assignments
                    ) and any(
                        _lexical_terms(assignment[0])
                        != _lexical_terms(current_semantic)
                        or assignment[1] != current_degree
                        for assignment in explicit_assignments
                        if assignment is not None
                    ):
                        return True
            if inline_addresses_key and not heading_addresses_key:
                assignment_values = _explicit_state_key_assignment_values(
                    chunk.content,
                    record.key,
                )
                if len(assignment_values) == 1:
                    explicit_assignment = _explicit_reserved_degree_claim(
                        assignment_values[0]
                    )
                    if explicit_assignment is not None:
                        assignment_semantic, assignment_degree = explicit_assignment
                        assignment_semantic_terms = _lexical_terms(assignment_semantic)
                        current_semantic_terms = _lexical_terms(current_semantic)
                        if (
                            len(assignment_semantic_terms) > 1
                            and assignment_semantic_terms[0] == "not"
                            and assignment_semantic_terms[1] != "not"
                        ):
                            if (
                                assignment_semantic_terms[1:]
                                == current_semantic_terms
                                and assignment_degree == current_degree
                            ):
                                return True
                            continue
                        if assignment_semantic_terms[0] != "not" and (
                            assignment_semantic_terms != current_semantic_terms
                            or assignment_degree != current_degree
                        ):
                            return True
                elif len(assignment_values) >= 2:
                    explicit_assignments = tuple(
                        _explicit_reserved_degree_claim(value)
                        for value in assignment_values
                    )
                    if all(
                        assignment is not None
                        and _lexical_terms(assignment[0])[0] != "not"
                        for assignment in explicit_assignments
                    ) and any(
                        _lexical_terms(assignment[0])
                        != _lexical_terms(current_semantic)
                        or assignment[1] != current_degree
                        for assignment in explicit_assignments
                        if assignment is not None
                    ):
                        return True
            if heading_addresses_key and not inline_addresses_key:
                body_value = _single_atx_heading_body_value(chunk.content)
                if body_value is not None:
                    explicit_body = _explicit_reserved_degree_claim(body_value)
                    if explicit_body is not None:
                        body_semantic, body_degree = explicit_body
                        body_semantic_terms = _lexical_terms(body_semantic)
                        current_semantic_terms = _lexical_terms(current_semantic)
                        if (
                            len(body_semantic_terms) > 1
                            and body_semantic_terms[0] == "not"
                            and body_semantic_terms[1] != "not"
                        ):
                            if (
                                body_semantic_terms[1:] == current_semantic_terms
                                and body_degree == current_degree
                            ):
                                return True
                            continue
            if not _contains_lexical_value(chunk.content, current_semantic):
                return True
            explicit_degrees = _explicit_degree_hint_assignments(
                chunk.content,
                key=record.key,
                heading_addresses_key=heading_addresses_key,
            )
            if explicit_degrees and any(
                degree != current_degree for degree in explicit_degrees
            ):
                return True
            continue

        current_scalar = _simple_scalar_state_value_text(record.value)
        if (
            current_scalar is not None
            and heading_addresses_key
            and not inline_addresses_key
        ):
            body_value = _single_atx_heading_body_value(chunk.content)
            if body_value is not None:
                body_terms = _lexical_terms(body_value)
                if len(body_terms) > 1 and body_terms[0] == "not":
                    if body_terms[1:] == _lexical_terms(current_scalar):
                        return True
                    continue

        if (
            current_scalar is not None
            and heading_addresses_key
            and inline_addresses_key
        ):
            assignment_values = _explicit_state_key_assignment_values(
                chunk.content,
                record.key,
            )
            if len(assignment_values) == 1:
                assignment_terms = _lexical_terms(assignment_values[0])
                if assignment_terms:
                    current_terms = _lexical_terms(current_scalar)
                    if len(assignment_terms) > 1 and assignment_terms[0] == "not":
                        if assignment_terms[1:] == current_terms:
                            return True
                        continue
                    if assignment_terms != current_terms:
                        return True
                    continue
            elif len(assignment_values) >= 2:
                assignment_term_sets = tuple(
                    _lexical_terms(value) for value in assignment_values
                )
                if all(assignment_terms for assignment_terms in assignment_term_sets):
                    current_terms = _lexical_terms(current_scalar)
                    for assignment_terms in assignment_term_sets:
                        if len(assignment_terms) > 1 and assignment_terms[0] == "not":
                            if assignment_terms[1:] == current_terms:
                                return True
                            continue
                        if assignment_terms != current_terms:
                            return True
                    continue

        if (
            current_scalar is not None
            and inline_addresses_key
            and not heading_addresses_key
        ):
            assignment_values = _explicit_state_key_assignment_values(
                chunk.content,
                record.key,
            )
            if len(assignment_values) == 1:
                assignment_terms = _lexical_terms(assignment_values[0])
                if len(assignment_terms) > 1 and assignment_terms[0] == "not":
                    if assignment_terms[1:] == _lexical_terms(current_scalar):
                        return True
                    continue
            elif len(assignment_values) >= 2:
                assignment_term_sets = tuple(
                    _lexical_terms(value) for value in assignment_values
                )
                if all(assignment_terms for assignment_terms in assignment_term_sets):
                    current_terms = _lexical_terms(current_scalar)
                    for assignment_terms in assignment_term_sets:
                        if len(assignment_terms) > 1 and assignment_terms[0] == "not":
                            if assignment_terms[1:] == current_terms:
                                return True
                            continue
                        if assignment_terms != current_terms:
                            return True
                    continue

        current_values = tuple(
            value_text
            for value_text in _value_lexical_strings(record.value)
            if _lexical_terms(value_text)
        )
        if not current_values:
            continue
        if not any(
            _contains_lexical_value(chunk.content, value_text)
            for value_text in current_values
        ):
            return True

    return False


def _simple_scalar_state_value_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value if _lexical_terms(value) else None
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _single_atx_heading_body_value(content: str) -> str | None:
    lines = content.splitlines()
    first_nonempty_index = next(
        (index for index, line in enumerate(lines) if line.strip()),
        None,
    )
    if first_nonempty_index is None:
        return None
    if re.fullmatch(r"\s{0,3}#{1,6}\s+\S.*", lines[first_nonempty_index]) is None:
        return None
    body_lines = tuple(
        line.strip()
        for line in lines[first_nonempty_index + 1 :]
        if line.strip()
    )
    if len(body_lines) != 1:
        return None
    return body_lines[0]


def _bounded_freeform_state_key_claims(content: str, key: str) -> tuple[str, ...]:
    key_terms = _lexical_terms(key)
    if not key_terms:
        return ()
    key_pattern = r"[\s_]+".join(re.escape(term) for term in key_terms)
    patterns = (
        re.compile(
            rf"^\s*current\s+{key_pattern}(?!\w)\s+is\s+(.+?)(?:[.!?])?\s*$"
        ),
        re.compile(
            rf"^\s*(?:the\s+)?{key_pattern}(?!\w)\s+is\s+(?:currently|now)\s+"
            r"(.+?)(?:[.!?])?\s*$"
        ),
    )
    normalized_content = _normalize_lexical_text(content)
    return tuple(
        match.group(1).strip()
        for line in normalized_content.splitlines()
        for pattern in patterns
        if (match := pattern.search(line)) is not None
    )


def _explicit_boolean_claim_value(claim: str) -> bool | None:
    terms = _lexical_terms(claim)
    if terms == ("true",):
        return True
    if terms == ("false",):
        return False
    if terms == ("not", "true"):
        return False
    if terms == ("not", "false"):
        return True
    return None


def _explicit_reserved_degree_claim(claim: str) -> tuple[str, float] | None:
    match = re.fullmatch(
        r"\s*(.+?)\s*;\s*degree_hint\s*[:=]\s*"
        r"(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:e[+-]?\d+)?)\s*",
        _normalize_lexical_text(claim),
    )
    if match is None:
        return None
    semantic = match.group(1).strip()
    if not _lexical_terms(semantic):
        return None
    return semantic, float(match.group(2))


def _reserved_degree_state_value(value: Any) -> tuple[str, float] | None:
    if not isinstance(value, dict) or set(value) != {"semantic", "degree_hint"}:
        return None
    semantic = value.get("semantic")
    degree = value.get("degree_hint")
    if not isinstance(semantic, str) or not semantic.strip():
        return None
    if isinstance(degree, bool) or not isinstance(degree, (int, float)):
        return None
    if not 0.0 <= degree <= 1.0:
        return None
    return semantic, float(degree)


def _explicit_degree_hint_assignments(
    content: str,
    *,
    key: str,
    heading_addresses_key: bool,
) -> tuple[float, ...]:
    normalized_content = _normalize_lexical_text(content)
    if heading_addresses_key:
        scopes = (normalized_content,)
    else:
        normalized_key = _normalize_lexical_text(key)
        key_pattern = rf"(?<!\w){re.escape(normalized_key)}\s*[:=]"
        scopes = tuple(
            line
            for line in normalized_content.splitlines()
            if re.search(key_pattern, line) is not None
        )

    return tuple(
        float(match.group(1))
        for scope in scopes
        for match in re.finditer(
            r"(?<!\w)degree_hint\s*[:=]\s*"
            r"(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:e[+-]?\d+)?)(?![\w.])",
            scope,
        )
    )


def _contains_explicit_opposite_boolean_value(content: str, *, current_value: bool) -> bool:
    terms = frozenset(_lexical_terms(content))
    current_term = "true" if current_value else "false"
    opposite_term = "false" if current_value else "true"
    return opposite_term in terms and current_term not in terms


def _explicit_state_key_assignment_values(content: str, key: str) -> tuple[str, ...]:
    normalized_key = _normalize_lexical_text(key)
    if not normalized_key:
        return ()
    normalized_content = _normalize_lexical_text(content)
    pattern = re.compile(rf"(?<!\w){re.escape(normalized_key)}\s*[:=]\s*")
    values: list[str] = []
    for line in normalized_content.splitlines():
        matches = tuple(pattern.finditer(line))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
            values.append(line[match.end() : end].strip())
    return tuple(values)


def _contains_explicit_state_key_assignment(content: str, key: str) -> bool:
    normalized_key = _normalize_lexical_text(key)
    if not normalized_key:
        return False
    normalized_content = _normalize_lexical_text(content)
    return re.search(
        rf"(?<!\w){re.escape(normalized_key)}\s*[:=]",
        normalized_content,
    ) is not None


def _contains_lexical_value(content: str, value_text: str) -> bool:
    content_terms = _lexical_terms(content)
    value_terms = _lexical_terms(value_text)
    if not value_terms or len(value_terms) > len(content_terms):
        return False

    width = len(value_terms)
    return any(
        content_terms[index : index + width] == value_terms
        for index in range(len(content_terms) - width + 1)
    )


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
