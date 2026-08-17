from __future__ import annotations

from relaylm.context import compile_cognitive_input
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.event_retrieval import EventDiscoveryIndex, select_event_evidence
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_retrieval import MemoryChunk, select_memory_chunks
from relaylm.state import CanonicalState, StateRecord


def _event(event_id: str, content: str, *, minute: int = 0) -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T12:{minute:02d}:00+00:00",
    )


def _degree_chunk(*, name: str, heading: str, content: str) -> MemoryChunk:
    return MemoryChunk(
        heading_path=(heading,),
        location=f"memory/MEMORY.md#{name}",
        content=f"## {heading}\n\n{content}",
    )


async def evaluate_distinct_query_feature_relevance() -> EvaluationScenarioResult:
    memory = """# Memory

## Coffee

Coffee note.

## Fukuoka Trip

Fukuoka trip notes.
"""
    query = "coffee coffee coffee fukuoka trip"
    selected_memory = select_memory_chunks(
        memory_markdown=memory,
        query=query,
        max_chunks=1,
        max_chars=500,
    )

    coffee = _event("coffee", "Coffee note.", minute=1)
    fukuoka_trip = _event("fukuoka-trip", "Fukuoka trip notes.", minute=2)
    events = (coffee, fukuoka_trip)
    index = EventDiscoveryIndex(events)
    selected_events = select_event_evidence(
        events=events,
        query=query,
        max_events=1,
        max_chars=500,
    )
    indexed_events = select_event_evidence(
        events=index,
        query=query,
        max_events=1,
        max_chars=500,
    )
    direct_scores = index.candidate_scores(("coffee", "coffee", "fukuoka", "trip"))

    memory_heading = (
        selected_memory[0].heading_path[-1] if len(selected_memory) == 1 else "none"
    )
    event_ids = tuple(event.id for event in selected_events)
    indexed_ids = tuple(event.id for event in indexed_events)

    checks = (
        EvaluationCheck(
            check_id="memory_distinct_overlap_wins",
            boundary="memory_retrieval",
            passed=memory_heading == "Fukuoka Trip",
            expected="Fukuoka Trip",
            observed=memory_heading,
        ),
        EvaluationCheck(
            check_id="event_distinct_overlap_wins",
            boundary="event_retrieval",
            passed=event_ids == ("fukuoka-trip",),
            expected="fukuoka-trip",
            observed=",".join(event_ids) if event_ids else "none",
        ),
        EvaluationCheck(
            check_id="event_iterable_indexed_equivalent",
            boundary="event_retrieval",
            passed=indexed_ids == event_ids,
            expected=True,
            observed=indexed_ids == event_ids,
        ),
        EvaluationCheck(
            check_id="index_candidate_scores_deduplicate_query_features",
            boundary="event_discovery_index",
            passed=direct_scores == {0: 1, 1: 2},
            expected="0:1,1:2",
            observed=",".join(f"{key}:{value}" for key, value in direct_scores.items()),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="distinct_query_feature_relevance",
        checks=checks,
        metrics={
            "memory_selected_count": len(selected_memory),
            "event_selected_count": len(selected_events),
            "indexed_event_selected_count": len(indexed_events),
            "direct_index_candidate_count": len(direct_scores),
        },
    )


async def evaluate_degree_state_memory_authority() -> EvaluationScenarioResult:
    state = CanonicalState(
        states=(
            StateRecord(
                state_id="tea-current",
                state_class="user.preference",
                key="tea",
                value={"semantic": "likes", "degree_hint": 0.85},
                sources=("source-event",),
            ),
        )
    )
    stale_heading = _degree_chunk(
        name="tea-stale-degree",
        heading="Tea",
        content="Rin likes tea.\ndegree_hint: 0.65",
    )
    matching_heading = _degree_chunk(
        name="tea-current-degree",
        heading="Tea",
        content="Rin likes tea.\ndegree_hint = 0.85",
    )
    semantic_conflict = _degree_chunk(
        name="tea-semantic-conflict",
        heading="Tea",
        content="Rin dislikes tea.\ndegree_hint: 0.85",
    )
    inline_stale = _degree_chunk(
        name="profile-inline-stale",
        heading="Profile Notes",
        content="tea: likes; degree_hint: 0.65",
    )
    other_key_degree = _degree_chunk(
        name="profile-other-key-degree",
        heading="Profile Notes",
        content="tea: likes\ncoffee: likes; degree_hint: 0.65",
    )
    history = _degree_chunk(
        name="preference-history",
        heading="Preference History",
        content="An old tea survey recorded degree_hint: 0.65.",
    )
    supplied = (
        stale_heading,
        matching_heading,
        semantic_conflict,
        inline_stale,
        other_key_degree,
        history,
    )
    compiled = compile_cognitive_input(
        identity=Identity("# Evaluation Character\nBe grounded."),
        state=state,
        current_event=_event("current", "What do you remember about tea?"),
        retrieved_memory=supplied,
    )
    selected_locations = tuple(item.location for item in compiled.memory)

    checks = (
        EvaluationCheck(
            check_id="stale_heading_degree_suppressed",
            boundary="context_compiler",
            passed=stale_heading.location not in selected_locations,
            expected=False,
            observed=stale_heading.location in selected_locations,
        ),
        EvaluationCheck(
            check_id="matching_heading_degree_retained",
            boundary="context_compiler",
            passed=matching_heading.location in selected_locations,
            expected=True,
            observed=matching_heading.location in selected_locations,
        ),
        EvaluationCheck(
            check_id="matching_number_does_not_rescue_semantic_conflict",
            boundary="context_compiler",
            passed=semantic_conflict.location not in selected_locations,
            expected=False,
            observed=semantic_conflict.location in selected_locations,
        ),
        EvaluationCheck(
            check_id="inline_degree_is_same_line_scoped",
            boundary="context_compiler",
            passed=inline_stale.location not in selected_locations,
            expected=False,
            observed=inline_stale.location in selected_locations,
        ),
        EvaluationCheck(
            check_id="other_key_degree_not_borrowed",
            boundary="context_compiler",
            passed=other_key_degree.location in selected_locations,
            expected=True,
            observed=other_key_degree.location in selected_locations,
        ),
        EvaluationCheck(
            check_id="unaddressed_degree_history_retained",
            boundary="context_compiler",
            passed=history.location in selected_locations,
            expected=True,
            observed=history.location in selected_locations,
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="degree_state_memory_authority",
        checks=checks,
        metrics={
            "input_memory_count": len(supplied),
            "selected_memory_count": len(compiled.memory),
            "suppressed_memory_count": len(supplied) - len(compiled.memory),
        },
    )
