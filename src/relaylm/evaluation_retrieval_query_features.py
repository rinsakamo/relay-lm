from __future__ import annotations

from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.event_retrieval import EventDiscoveryIndex, select_event_evidence
from relaylm.events import Event
from relaylm.memory_retrieval import select_memory_chunks


def _event(event_id: str, content: str, *, second: int) -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T12:34:{second:02d}+00:00",
    )


async def evaluate_retrieval_query_features() -> EvaluationScenarioResult:
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

    coffee = _event("coffee", "Coffee note.", second=0)
    fukuoka_trip = _event("fukuoka-trip", "Fukuoka trip notes.", second=1)
    events = (coffee, fukuoka_trip)
    selected_events = select_event_evidence(
        events=events,
        query=query,
        max_events=1,
        max_chars=500,
    )
    selected_indexed_events = select_event_evidence(
        events=EventDiscoveryIndex(events),
        query=query,
        max_events=1,
        max_chars=500,
    )

    score_coffee = _event("score-coffee", "Coffee note.", second=2)
    score_coffee_tea = _event(
        "score-coffee-tea",
        "Coffee and tea note.",
        second=3,
    )
    scoring_index = EventDiscoveryIndex((score_coffee, score_coffee_tea))
    candidate_scores = scoring_index.candidate_scores(("coffee", "coffee", "tea"))

    memory_heading = (
        selected_memory[0].heading_path[-1] if selected_memory else "none"
    )
    event_ids = tuple(event.id for event in selected_events)
    indexed_ids = tuple(event.id for event in selected_indexed_events)

    checks = (
        EvaluationCheck(
            check_id="memory_repetition_does_not_outweigh_distinct_overlap",
            boundary="memory_retrieval",
            passed=memory_heading == "Fukuoka Trip",
            expected="Fukuoka Trip",
            observed=memory_heading,
        ),
        EvaluationCheck(
            check_id="event_repetition_does_not_outweigh_distinct_overlap",
            boundary="event_retrieval",
            passed=event_ids == ("fukuoka-trip",),
            expected="fukuoka-trip",
            observed=",".join(event_ids) if event_ids else "none",
        ),
        EvaluationCheck(
            check_id="event_indexed_iterable_selection_converges",
            boundary="event_retrieval",
            passed=indexed_ids == event_ids,
            expected=True,
            observed=indexed_ids == event_ids,
        ),
        EvaluationCheck(
            check_id="index_candidate_scores_deduplicate_query_features",
            boundary="event_discovery_index",
            passed=candidate_scores == {0: 1, 1: 2},
            expected="0:1,1:2",
            observed=",".join(
                f"{index}:{score}" for index, score in sorted(candidate_scores.items())
            ),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="retrieval_query_features",
        checks=checks,
        metrics={
            "memory_selected_count": len(selected_memory),
            "event_selected_count": len(selected_events),
            "indexed_event_selected_count": len(selected_indexed_events),
            "indexed_candidate_count": len(candidate_scores),
            "indexed_max_score": max(candidate_scores.values(), default=0),
        },
    )
