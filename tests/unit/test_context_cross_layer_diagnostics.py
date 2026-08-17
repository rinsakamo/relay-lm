from __future__ import annotations

import json
from dataclasses import asdict

from relaylm.context import compile_cognitive_input_with_diagnostics
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_retrieval import MemoryChunk
from relaylm.state import CanonicalState, StateRecord


def _event(event_id: str, actor: str, content: str, second: int) -> Event:
    return Event.create(
        type="message",
        actor=actor,
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T08:50:{second:02d}+00:00",
    )


def test_cross_layer_diagnostics_report_only_compiler_owned_counts() -> None:
    older = _event("older-secret", "user", "older coffee note", 0)
    prior_user = _event("prior-user-secret", "user", "coffee again", 1)
    prior_assistant = _event("prior-assistant-secret", "assistant", "got it", 2)
    current = _event("current-secret", "user", "coffee now", 3)
    state = CanonicalState(
        states=(
            StateRecord(
                state_id="state-secret",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
                sources=("source-secret",),
            ),
        )
    )
    stale_location = MemoryChunk(
        heading_path=("Memory", "Residence Location"),
        location="memory/MEMORY.md#secret-location",
        content="## Residence Location\n\nHokkaido",
    )
    trip_history = MemoryChunk(
        heading_path=("Memory", "Trip History"),
        location="memory/MEMORY.md#secret-trip",
        content="## Trip History\n\nVisited Hokkaido",
    )

    result = compile_cognitive_input_with_diagnostics(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=current,
        recent_events=(older, prior_user, prior_assistant, current),
        retrieved_memory=(stale_location, trip_history),
        event_evidence=(older, prior_user, current),
        max_working_context_events=2,
    )

    assert [diagnostic.layer for diagnostic in result.diagnostics] == [
        "canonical_state",
        "retrieved_memory",
        "event_evidence",
    ]

    memory_diagnostic = result.diagnostics[1]
    assert memory_diagnostic.mode == "authority_filtered"
    assert memory_diagnostic.eligible_count == 2
    assert memory_diagnostic.selected_count == 1
    assert memory_diagnostic.evicted_count == 1
    assert memory_diagnostic.authority_suppressed_count == 1
    assert memory_diagnostic.current_event_excluded_count == 0
    assert memory_diagnostic.redundancy_overlap_count == 0
    assert memory_diagnostic.budget_limit is None
    assert memory_diagnostic.budget_pressure is False

    event_diagnostic = result.diagnostics[2]
    assert event_diagnostic.mode == "current_event_deduplicated"
    assert event_diagnostic.eligible_count == 3
    assert event_diagnostic.selected_count == 2
    assert event_diagnostic.evicted_count == 1
    assert event_diagnostic.current_event_excluded_count == 1
    assert event_diagnostic.authority_suppressed_count == 0
    assert event_diagnostic.redundancy_overlap_count == 1
    assert event_diagnostic.budget_limit is None
    assert event_diagnostic.budget_pressure is False

    serialized = json.dumps([asdict(item) for item in result.diagnostics], ensure_ascii=False)
    for forbidden in (
        "residence_location",
        "Fukuoka",
        "Hokkaido",
        "state-secret",
        "source-secret",
        "older-secret",
        "prior-user-secret",
        "current-secret",
        "secret-location",
        "secret-trip",
    ):
        assert forbidden not in serialized


def test_cross_layer_diagnostics_report_passthrough_without_false_suppression() -> None:
    current = _event("current-sensitive", "user", "hello", 4)
    memory = MemoryChunk(
        heading_path=("Memory", "Trip History"),
        location="memory/MEMORY.md#trip",
        content="## Trip History\n\nVisited Kyoto",
    )
    evidence = _event("evidence-sensitive", "user", "hello before", 3)

    result = compile_cognitive_input_with_diagnostics(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=current,
        retrieved_memory=(memory,),
        event_evidence=(evidence,),
    )

    memory_diagnostic = result.diagnostics[1]
    event_diagnostic = result.diagnostics[2]
    assert memory_diagnostic.mode == "pass_through"
    assert memory_diagnostic.eligible_count == 1
    assert memory_diagnostic.selected_count == 1
    assert memory_diagnostic.evicted_count == 0
    assert memory_diagnostic.authority_suppressed_count == 0
    assert event_diagnostic.mode == "pass_through"
    assert event_diagnostic.eligible_count == 1
    assert event_diagnostic.selected_count == 1
    assert event_diagnostic.evicted_count == 0
    assert event_diagnostic.current_event_excluded_count == 0
    assert event_diagnostic.redundancy_overlap_count == 0
