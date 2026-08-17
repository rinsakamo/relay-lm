from __future__ import annotations

import json
from dataclasses import asdict

from relaylm.context import compile_cognitive_input_with_diagnostics
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_retrieval import MemoryChunk
from relaylm.state import CanonicalState, StateRecord


def _message(*, event_id: str, actor: str, content: str, second: int) -> Event:
    return Event.create(
        type="message",
        actor=actor,
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T09:00:{second:02d}+00:00",
    )


async def evaluate_cross_layer_context_diagnostics() -> EvaluationScenarioResult:
    older = _message(
        event_id="older-secret",
        actor="user",
        content="older coffee note",
        second=0,
    )
    prior_user = _message(
        event_id="prior-user-secret",
        actor="user",
        content="coffee again",
        second=1,
    )
    prior_assistant = _message(
        event_id="prior-assistant-secret",
        actor="assistant",
        content="got it",
        second=2,
    )
    current = _message(
        event_id="current-secret",
        actor="user",
        content="coffee now",
        second=3,
    )
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
        identity=Identity("# Evaluation Character\nBe grounded.\n"),
        state=state,
        current_event=current,
        recent_events=(older, prior_user, prior_assistant, current),
        retrieved_memory=(stale_location, trip_history),
        event_evidence=(older, prior_user, current),
        max_working_context_events=2,
    )
    layers = tuple(diagnostic.layer for diagnostic in result.diagnostics)
    memory_diagnostic = result.diagnostics[1]
    event_diagnostic = result.diagnostics[2]
    serialized = json.dumps(
        [asdict(diagnostic) for diagnostic in result.diagnostics],
        ensure_ascii=False,
    )
    forbidden = (
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
    )

    checks = (
        EvaluationCheck(
            check_id="compiler_reports_three_owned_diagnostic_layers",
            boundary="context_compiler",
            passed=layers == ("canonical_state", "retrieved_memory", "event_evidence"),
            expected=3,
            observed=len(layers),
        ),
        EvaluationCheck(
            check_id="memory_authority_suppression_is_counted",
            boundary="diagnostics",
            passed=memory_diagnostic.eligible_count == 2
            and memory_diagnostic.selected_count == 1
            and memory_diagnostic.authority_suppressed_count == 1
            and memory_diagnostic.budget_limit is None
            and not memory_diagnostic.budget_pressure,
            expected=1,
            observed=memory_diagnostic.authority_suppressed_count,
        ),
        EvaluationCheck(
            check_id="current_event_evidence_dedup_is_counted",
            boundary="diagnostics",
            passed=event_diagnostic.eligible_count == 3
            and event_diagnostic.selected_count == 2
            and event_diagnostic.current_event_excluded_count == 1,
            expected=1,
            observed=event_diagnostic.current_event_excluded_count,
        ),
        EvaluationCheck(
            check_id="working_context_event_overlap_is_counted_without_suppression",
            boundary="diagnostics",
            passed=event_diagnostic.redundancy_overlap_count == 1
            and len(result.cognitive_input.event_evidence) == 2,
            expected=1,
            observed=event_diagnostic.redundancy_overlap_count,
        ),
        EvaluationCheck(
            check_id="cross_layer_diagnostics_do_not_expose_semantic_payload",
            boundary="diagnostics",
            passed=all(value not in serialized for value in forbidden),
            expected=True,
            observed=all(value not in serialized for value in forbidden),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="cross_layer_context_diagnostics",
        checks=checks,
        metrics={
            "diagnostic_layer_count": len(layers),
            "memory_authority_suppressed_count": memory_diagnostic.authority_suppressed_count,
            "event_current_excluded_count": event_diagnostic.current_event_excluded_count,
            "event_redundancy_overlap_count": event_diagnostic.redundancy_overlap_count,
        },
    )
