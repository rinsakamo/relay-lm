from __future__ import annotations

from relaylm.context import compile_cognitive_input
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_retrieval import MemoryChunk, select_memory_chunks
from relaylm.providers.openai_compatible import serialize_cognitive_input
from relaylm.state import CanonicalState, StateRecord


_MEMORY = """# Memory

## Preferences

Rin likes tea.

## Coffee

Rin currently prefers coffee over tea.

## Travel

Rin visited Fukuoka last year.
"""


async def evaluate_memory_heading_retrieval() -> EvaluationScenarioResult:
    relevant = select_memory_chunks(
        memory_markdown=_MEMORY,
        query="What did I say about coffee?",
        max_chunks=1,
        max_chars=200,
    )
    irrelevant = select_memory_chunks(
        memory_markdown=_MEMORY,
        query="Tell me about astronomy",
        max_chunks=2,
        max_chars=500,
    )

    oversized_memory = """# Memory

## Coffee details

Coffee preference has a deliberately long explanation that will not fit.

## Coffee summary

Coffee is preferred.
"""
    expected_summary = "## Coffee summary\n\nCoffee is preferred."
    oversized = select_memory_chunks(
        memory_markdown=oversized_memory,
        query="coffee",
        max_chunks=2,
        max_chars=len(expected_summary),
    )

    checks = (
        EvaluationCheck(
            check_id="relevant_memory_selects_complete_heading_section",
            boundary="memory_retrieval",
            passed=len(relevant) == 1
            and relevant[0].heading_path == ("Memory", "Coffee")
            and relevant[0].content == "## Coffee\n\nRin currently prefers coffee over tea.",
            expected="Memory/Coffee",
            observed="/".join(relevant[0].heading_path) if relevant else "none",
        ),
        EvaluationCheck(
            check_id="irrelevant_optional_memory_is_suppressed",
            boundary="memory_retrieval",
            passed=irrelevant == (),
            expected=0,
            observed=len(irrelevant),
        ),
        EvaluationCheck(
            check_id="oversized_chunk_is_skipped_without_truncation",
            boundary="memory_budget",
            passed=len(oversized) == 1
            and oversized[0].heading_path[-1] == "Coffee summary"
            and oversized[0].content == expected_summary,
            expected="Coffee summary",
            observed=oversized[0].heading_path[-1] if oversized else "none",
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="memory_heading_retrieval",
        checks=checks,
        metrics={
            "relevant_selected_count": len(relevant),
            "irrelevant_selected_count": len(irrelevant),
            "oversized_selected_count": len(oversized),
        },
    )


async def evaluate_memory_cognitive_projection() -> EvaluationScenarioResult:
    current = Event.create(
        type="message",
        actor="user",
        payload={"content": "What did I say about coffee?"},
        event_id="current-event",
        timestamp="2026-08-17T04:00:00+00:00",
    )
    chunk = MemoryChunk(
        heading_path=("Memory", "Coffee"),
        location="memory/MEMORY.md#memory/coffee",
        content="## Coffee\n\nRin currently prefers coffee over tea.",
    )
    state = CanonicalState(
        states=(
            StateRecord(
                state_id="tea-state",
                state_class="user.preference",
                key="tea",
                value="likes",
                sources=("old-user-event",),
            ),
        )
    )
    compiled = compile_cognitive_input(
        identity=Identity("# Evaluation Character\nBe grounded."),
        state=state,
        current_event=current,
        retrieved_memory=(chunk,),
    )
    without_memory = compile_cognitive_input(
        identity=Identity("# Evaluation Character\nBe grounded."),
        state=state,
        current_event=current,
    )
    payload = serialize_cognitive_input(compiled)
    without_memory_payload = serialize_cognitive_input(without_memory)

    serialized_sources = [
        source
        for record in payload["state"]
        for source in record.get("sources", [])
    ] + [
        source
        for item in payload["context"]
        for source in item.get("sources", [])
    ]
    source_leak_count = serialized_sources.count(chunk.location)

    checks = (
        EvaluationCheck(
            check_id="selected_memory_projects_into_distinct_layer",
            boundary="context_compiler",
            passed=len(compiled.memory) == 1
            and compiled.memory[0].content == chunk.content
            and compiled.memory[0].location == chunk.location
            and compiled.context == (),
            expected=1,
            observed=len(compiled.memory),
        ),
        EvaluationCheck(
            check_id="provider_serializes_memory_separately",
            boundary="provider_serialization",
            passed=payload["memory"]
            == [{"content": chunk.content, "location": chunk.location}]
            and payload["context"] == [],
            expected=1,
            observed=len(payload["memory"]),
        ),
        EvaluationCheck(
            check_id="memory_location_is_not_event_source",
            boundary="event_provenance",
            passed=source_leak_count == 0
            and payload["input"]["event_id"] == "current-event",
            expected=0,
            observed=source_leak_count,
        ),
        EvaluationCheck(
            check_id="missing_memory_projects_empty_layer",
            boundary="context_compiler",
            passed=without_memory.memory == ()
            and without_memory_payload["memory"] == [],
            expected=0,
            observed=len(without_memory_payload["memory"]),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="memory_cognitive_projection",
        checks=checks,
        metrics={
            "projected_memory_count": len(compiled.memory),
            "working_context_count": len(compiled.context),
            "memory_location_source_leak_count": source_leak_count,
        },
    )
