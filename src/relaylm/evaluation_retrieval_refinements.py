from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.context import compile_cognitive_input
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.event_retrieval import (
    EventDiscoveryIndex,
    select_event_evidence,
    select_event_evidence_with_diagnostics,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_retrieval import (
    MemoryChunk,
    select_memory_chunks,
    select_memory_chunks_with_diagnostics,
)
from relaylm.state import CanonicalState, StateRecord
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    EventRetrievalBudget,
    MemoryRetrievalBudget,
    run_user_turn_with_retrieval_diagnostics,
)


class _AggregateEvaluationProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        self.inputs.append(cognitive_input)
        return CognitiveOutput(response="ok")


def _make_turn_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(
        "# Evaluation Character\n\nBe honest and grounded.\n",
        encoding="utf-8",
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: evaluation\n  name: Evaluation\n",
        encoding="utf-8",
    )
    (root / "memory" / "MEMORY.md").write_text(
        "# Coffee\n\ncoffee alpha\n\n# Tea\n\ntea beta\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    character.append_event(
        Event.create(
            type="message",
            actor="user",
            payload={"content": "coffee earlier"},
            event_id="prior-user",
            timestamp="2026-08-17T09:00:00+00:00",
        )
    )
    character.append_event(
        Event.create(
            type="message",
            actor="assistant",
            payload={"content": "coffee reply"},
            event_id="prior-assistant",
            timestamp="2026-08-17T09:01:00+00:00",
        )
    )
    return character


def _event(event_id: str, content: str, *, minute: int = 0) -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T10:{minute:02d}:00+00:00",
    )


async def evaluate_boolean_state_memory_authority() -> EvaluationScenarioResult:
    state = CanonicalState(
        states=(
            StateRecord(
                state_id="notifications-state",
                state_class="user.fact",
                key="notifications_enabled",
                value=True,
                sources=("source-notifications",),
            ),
        )
    )
    stale = MemoryChunk(
        heading_path=("Profile Notes",),
        location="memory/MEMORY.md#profile-notes",
        content="## Profile Notes\n\nnotifications_enabled = false",
    )
    current = MemoryChunk(
        heading_path=("Notifications Enabled",),
        location="memory/MEMORY.md#notifications-enabled",
        content="## Notifications Enabled\n\ntrue",
    )
    history = MemoryChunk(
        heading_path=("Notification History",),
        location="memory/MEMORY.md#notification-history",
        content=(
            "## Notification History\n\n"
            "Notifications were disabled during a past quiet period."
        ),
    )
    compiled = compile_cognitive_input(
        identity=Identity("# Evaluation Character\nBe grounded."),
        state=state,
        current_event=_event("current", "What do you remember?"),
        retrieved_memory=(stale, current, history),
    )
    selected_locations = tuple(item.location for item in compiled.memory)

    checks = (
        EvaluationCheck(
            check_id="opposite_boolean_suppressed",
            boundary="context_compiler",
            passed=stale.location not in selected_locations,
            expected=False,
            observed=stale.location in selected_locations,
        ),
        EvaluationCheck(
            check_id="current_boolean_retained",
            boundary="context_compiler",
            passed=current.location in selected_locations,
            expected=True,
            observed=current.location in selected_locations,
        ),
        EvaluationCheck(
            check_id="unaddressed_history_retained",
            boundary="context_compiler",
            passed=history.location in selected_locations,
            expected=True,
            observed=history.location in selected_locations,
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="boolean_state_memory_authority",
        checks=checks,
        metrics={
            "input_memory_count": 3,
            "selected_memory_count": len(compiled.memory),
            "suppressed_memory_count": 3 - len(compiled.memory),
        },
    )


async def evaluate_retrieval_aggregate_diagnostics() -> EvaluationScenarioResult:
    provider = _AggregateEvaluationProvider()
    with tempfile.TemporaryDirectory(prefix="relaylm-aggregate-eval-") as temporary:
        root = Path(temporary)
        configured_character = _make_turn_character(root / "configured")
        zero_character = _make_turn_character(root / "zero")

        configured = await run_user_turn_with_retrieval_diagnostics(
            character=configured_character,
            provider=provider,
            content="coffee",
            memory_budget=MemoryRetrievalBudget(max_chunks=1, max_chars=1000),
            event_budget=EventRetrievalBudget(max_events=1, max_chars=1000),
        )
        zero = await run_user_turn_with_retrieval_diagnostics(
            character=zero_character,
            provider=provider,
            content="coffee",
        )

    memory = configured.retrieval.memory
    event = configured.retrieval.event
    assert memory is not None
    assert event is not None
    aggregate = configured.retrieval.aggregate
    expected_usage = (
        memory.selector.character_budget_used + event.selector.character_budget_used
    )
    expected_pressure_count = sum(
        (
            memory.selector.character_budget_pressure,
            event.selector.character_budget_pressure,
        )
    )
    expected_any_pressure = (
        memory.selector.character_budget_pressure
        or event.selector.character_budget_pressure
    )
    zero_mapping = asdict(zero.retrieval.aggregate)
    expected_zero = {
        "enabled_layer_count": 0,
        "configured_character_budget_total": 0,
        "selected_character_usage_total": 0,
        "character_budget_pressured_layer_count": 0,
        "any_character_budget_pressure": False,
    }

    checks = (
        EvaluationCheck(
            check_id="enabled_layers_aggregated",
            boundary="turn_diagnostics",
            passed=aggregate.enabled_layer_count == 2,
            expected=2,
            observed=aggregate.enabled_layer_count,
        ),
        EvaluationCheck(
            check_id="configured_character_budget_aggregated",
            boundary="turn_diagnostics",
            passed=aggregate.configured_character_budget_total == 2000,
            expected=2000,
            observed=aggregate.configured_character_budget_total,
        ),
        EvaluationCheck(
            check_id="selected_character_usage_aggregated",
            boundary="turn_diagnostics",
            passed=aggregate.selected_character_usage_total == expected_usage,
            expected=expected_usage,
            observed=aggregate.selected_character_usage_total,
        ),
        EvaluationCheck(
            check_id="pressure_flags_aggregated",
            boundary="turn_diagnostics",
            passed=(
                aggregate.character_budget_pressured_layer_count
                == expected_pressure_count
                and aggregate.any_character_budget_pressure is expected_any_pressure
            ),
            expected=f"{expected_pressure_count}:{expected_any_pressure}",
            observed=(
                f"{aggregate.character_budget_pressured_layer_count}:"
                f"{aggregate.any_character_budget_pressure}"
            ),
        ),
        EvaluationCheck(
            check_id="zero_layer_aggregate_is_empty",
            boundary="turn_diagnostics",
            passed=zero_mapping == expected_zero,
            expected=True,
            observed=zero_mapping == expected_zero,
        ),
        EvaluationCheck(
            check_id="provider_called_once_per_turn",
            boundary="provider",
            passed=provider.calls == 2,
            expected=2,
            observed=provider.calls,
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="retrieval_aggregate_diagnostics",
        checks=checks,
        metrics={
            "provider_calls": provider.calls,
            "enabled_layer_count": aggregate.enabled_layer_count,
            "configured_character_budget_total": (
                aggregate.configured_character_budget_total
            ),
            "selected_character_usage_total": aggregate.selected_character_usage_total,
            "character_budget_pressured_layer_count": (
                aggregate.character_budget_pressured_layer_count
            ),
            "zero_enabled_layer_count": zero.retrieval.aggregate.enabled_layer_count,
        },
    )


async def evaluate_cjk_retrieval_relevance() -> EvaluationScenarioResult:
    memory = """# Memory

## 飲み物

最近はコーヒーが好きです。

## 旅行

先週は福岡に行きました。
"""
    query = "コーヒーが好き"
    memory_plain = select_memory_chunks(
        memory_markdown=memory,
        query=query,
        max_chunks=2,
        max_chars=500,
    )
    memory_diagnostic = select_memory_chunks_with_diagnostics(
        memory_markdown=memory,
        query=query,
        max_chunks=2,
        max_chars=500,
    )

    relevant_event = _event("event-coffee", "最近はコーヒーが好きです。", minute=1)
    unrelated_event = _event("event-trip", "先週は福岡に行きました。", minute=2)
    events = (relevant_event, unrelated_event)
    event_plain = select_event_evidence(
        events=events,
        query=query,
        max_events=2,
        max_chars=500,
    )
    event_indexed = select_event_evidence(
        events=EventDiscoveryIndex(events),
        query=query,
        max_events=2,
        max_chars=500,
    )
    event_diagnostic = select_event_evidence_with_diagnostics(
        events=events,
        query=query,
        max_events=2,
        max_chars=500,
    )
    latin_false_positive = select_event_evidence(
        events=(_event("event-dislikes", "Rin dislikes tea.", minute=3),),
        query="likes",
        max_events=1,
        max_chars=200,
    )

    memory_heading = (
        memory_plain[0].heading_path[-1] if len(memory_plain) == 1 else "none"
    )
    event_ids = tuple(event.id for event in event_plain)
    indexed_ids = tuple(event.id for event in event_indexed)

    checks = (
        EvaluationCheck(
            check_id="memory_cjk_match",
            boundary="memory_retrieval",
            passed=len(memory_plain) == 1 and memory_heading == "飲み物",
            expected="飲み物",
            observed=memory_heading,
        ),
        EvaluationCheck(
            check_id="memory_unrelated_omitted",
            boundary="memory_retrieval",
            passed=all(chunk.heading_path[-1] != "旅行" for chunk in memory_plain),
            expected=False,
            observed=any(chunk.heading_path[-1] == "旅行" for chunk in memory_plain),
        ),
        EvaluationCheck(
            check_id="memory_diagnostic_selection_equivalent",
            boundary="memory_retrieval",
            passed=memory_diagnostic.chunks == memory_plain,
            expected=True,
            observed=memory_diagnostic.chunks == memory_plain,
        ),
        EvaluationCheck(
            check_id="event_cjk_match",
            boundary="event_retrieval",
            passed=event_ids == ("event-coffee",),
            expected="event-coffee",
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
            check_id="event_diagnostic_selection_equivalent",
            boundary="event_retrieval",
            passed=event_diagnostic.events == event_plain,
            expected=True,
            observed=event_diagnostic.events == event_plain,
        ),
        EvaluationCheck(
            check_id="latin_substring_protection",
            boundary="event_retrieval",
            passed=latin_false_positive == (),
            expected=0,
            observed=len(latin_false_positive),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="cjk_retrieval_relevance",
        checks=checks,
        metrics={
            "memory_selected_count": len(memory_plain),
            "event_selected_count": len(event_plain),
            "indexed_event_selected_count": len(event_indexed),
        },
    )
