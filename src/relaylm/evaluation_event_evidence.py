from __future__ import annotations

import tempfile
from pathlib import Path

from relaylm.cognitive import CognitiveInput, CognitiveOutput
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
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import EventRetrievalBudget, run_user_turn


def _message(*, event_id: str, actor: str, content: str, second: int) -> Event:
    return Event.create(
        type="message",
        actor=actor,
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T06:50:{second:02d}+00:00",
    )


class _RecordingProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        self.inputs.append(cognitive_input)
        return CognitiveOutput("ok")


class _CountingCharacter(CharacterDirectory):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.iter_events_calls = 0

    def iter_events(self):
        self.iter_events_calls += 1
        return super().iter_events()


def _make_character(root: Path, *, counting: bool = False) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(
        "# Evaluation Character\n\nBe honest and grounded.\n",
        encoding="utf-8",
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: event-eval\n  name: Event Eval\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}\n', encoding="utf-8"
    )
    cls = _CountingCharacter if counting else CharacterDirectory
    return cls(root)


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


async def evaluate_ordinary_turn_event_retrieval() -> EvaluationScenarioResult:
    with tempfile.TemporaryDirectory(prefix="relaylm-event-turn-eval-") as temporary:
        root = Path(temporary)
        character = _make_character(root, counting=True)
        assert isinstance(character, _CountingCharacter)
        target = Event.create(
            type="message",
            actor="user",
            payload={"content": "Rin mentioned coffee before."},
        )
        character.append_event(target)
        for index in range(7):
            character.append_event(
                Event.create(
                    type="message",
                    actor="user",
                    payload={"content": f"unrelated weather note {index}"},
                )
            )
        provider = _RecordingProvider()
        result = await run_user_turn(
            character=character,
            provider=provider,
            content="What did I say about coffee?",
            event_budget=EventRetrievalBudget(max_events=1, max_chars=200),
        )
        supplied = provider.inputs[0]
        retrieved_ids = [item.event_id for item in supplied.event_evidence]
        context_sources = {
            source for item in supplied.context for source in item.sources
        }
        current_duplicate_count = retrieved_ids.count(result.user_event.id)
        explicit_iter_events_calls = character.iter_events_calls

    with tempfile.TemporaryDirectory(prefix="relaylm-event-default-eval-") as temporary:
        root = Path(temporary)
        default_character = _make_character(root)
        default_character.append_event(
            Event.create(
                type="message",
                actor="user",
                payload={"content": "Coffee preference was discussed."},
            )
        )
        default_provider = _RecordingProvider()
        await run_user_turn(
            character=default_character,
            provider=default_provider,
            content="Coffee history?",
        )
        default_event_evidence_count = len(default_provider.inputs[0].event_evidence)

    checks = (
        EvaluationCheck(
            check_id="explicit_budget_retrieves_older_relevant_event",
            boundary="event_retrieval",
            passed=retrieved_ids == [target.id]
            and target.id not in context_sources,
            expected=target.id,
            observed=",".join(retrieved_ids) or "none",
        ),
        EvaluationCheck(
            check_id="current_event_is_not_duplicated_as_evidence",
            boundary="event_provenance",
            passed=current_duplicate_count == 0,
            expected=0,
            observed=current_duplicate_count,
        ),
        EvaluationCheck(
            check_id="ordinary_turn_calls_provider_once",
            boundary="ordinary_turn",
            passed=provider.calls == 1,
            expected=1,
            observed=provider.calls,
        ),
        EvaluationCheck(
            check_id="pre_generation_snapshot_is_shared_with_working_context",
            boundary="event_journal",
            passed=explicit_iter_events_calls == 2,
            expected=2,
            observed=explicit_iter_events_calls,
        ),
        EvaluationCheck(
            check_id="omitted_budget_preserves_empty_event_evidence",
            boundary="ordinary_turn",
            passed=default_event_evidence_count == 0,
            expected=0,
            observed=default_event_evidence_count,
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="ordinary_turn_event_retrieval",
        checks=checks,
        metrics={
            "provider_calls": provider.calls,
            "retrieved_event_count": len(retrieved_ids),
            "current_duplicate_count": current_duplicate_count,
            "explicit_iter_events_calls": explicit_iter_events_calls,
            "default_event_evidence_count": default_event_evidence_count,
        },
    )
