from __future__ import annotations

from relaylm.context import compile_cognitive_input
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import (
    PROVIDER_WIRE_INSTRUCTION,
    SYSTEM_INSTRUCTION,
    serialize_cognitive_input,
)
from relaylm.state import CanonicalState


def _message(*, event_id: str, actor: str, content: str, second: int) -> Event:
    return Event.create(
        type="message",
        actor=actor,
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T06:50:{second:02d}+00:00",
    )


async def evaluate_event_evidence_cognitive_projection() -> EvaluationScenarioResult:
    user_evidence = _message(
        event_id="user-evidence",
        actor="user",
        content="I used to live in Hokkaido.",
        second=0,
    )
    assistant_evidence = _message(
        event_id="assistant-evidence",
        actor="assistant",
        content="You told me about that move.",
        second=1,
    )
    current = _message(
        event_id="current-event",
        actor="user",
        content="Where did I say I lived before?",
        second=2,
    )

    compiled = compile_cognitive_input(
        identity=Identity("# Evaluation Character\nBe grounded."),
        state=CanonicalState(),
        current_event=current,
        event_evidence=(user_evidence, assistant_evidence, current),
    )
    payload = serialize_cognitive_input(compiled)

    expected_serialized = [
        {
            "event_id": user_evidence.id,
            "type": user_evidence.type,
            "actor": user_evidence.actor,
            "timestamp": user_evidence.timestamp,
            "content": user_evidence.payload["content"],
        },
        {
            "event_id": assistant_evidence.id,
            "type": assistant_evidence.type,
            "actor": assistant_evidence.actor,
            "timestamp": assistant_evidence.timestamp,
            "content": assistant_evidence.payload["content"],
        },
    ]
    projected_ids = [item.event_id for item in compiled.event_evidence]
    serialized_ids = [item["event_id"] for item in payload["event_evidence"]]
    current_duplicate_count = projected_ids.count(current.id)

    checks = (
        EvaluationCheck(
            check_id="selected_events_project_into_distinct_evidence_layer",
            boundary="context_compiler",
            passed=len(compiled.event_evidence) == 2
            and compiled.context == ()
            and compiled.memory == ()
            and compiled.input.id == current.id,
            expected=2,
            observed=len(compiled.event_evidence),
        ),
        EvaluationCheck(
            check_id="event_occurrence_metadata_is_preserved",
            boundary="event_provenance",
            passed=projected_ids == [user_evidence.id, assistant_evidence.id]
            and compiled.event_evidence[0].event_type == user_evidence.type
            and compiled.event_evidence[0].actor == "user"
            and compiled.event_evidence[0].timestamp == user_evidence.timestamp
            and compiled.event_evidence[0].content == user_evidence.payload["content"]
            and compiled.event_evidence[1].actor == "assistant",
            expected="user-evidence,assistant-evidence",
            observed=",".join(projected_ids) or "none",
        ),
        EvaluationCheck(
            check_id="current_input_is_not_duplicated_as_event_evidence",
            boundary="event_provenance",
            passed=current_duplicate_count == 0
            and payload["input"]["event_id"] == current.id,
            expected=0,
            observed=current_duplicate_count,
        ),
        EvaluationCheck(
            check_id="provider_serializes_event_evidence_separately",
            boundary="provider_serialization",
            passed=payload["event_evidence"] == expected_serialized
            and payload["context"] == []
            and payload["memory"] == [],
            expected=2,
            observed=len(payload["event_evidence"]),
        ),
        EvaluationCheck(
            check_id="provider_source_contract_keeps_real_event_ids_distinct_from_memory_locations",
            boundary="event_provenance",
            passed=serialized_ids == [user_evidence.id, assistant_evidence.id]
            and "Event Evidence" in SYSTEM_INSTRUCTION
            and "State, Context, Event Evidence, or Input" in PROVIDER_WIRE_INSTRUCTION
            and "Memory `location` values" in PROVIDER_WIRE_INSTRUCTION,
            expected=True,
            observed=serialized_ids == [user_evidence.id, assistant_evidence.id],
        ),
    )

    return EvaluationScenarioResult(
        scenario_id="event_evidence_cognitive_projection",
        checks=checks,
        metrics={
            "projected_evidence_count": len(compiled.event_evidence),
            "serialized_evidence_count": len(payload["event_evidence"]),
            "current_input_duplicate_count": current_duplicate_count,
            "working_context_count": len(compiled.context),
            "memory_count": len(compiled.memory),
        },
    )
