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
            observed=",".join(f"{key}:{value}" for key, value in sorted(direct_scores.items())),
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


def _degree_chunk(*, name: str, heading: str, content: str) -> MemoryChunk:
    return MemoryChunk(
        heading_path=(heading,),
        location=f"memory/MEMORY.md#{name}",
        content=f"## {heading}\n\n{content}",
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
