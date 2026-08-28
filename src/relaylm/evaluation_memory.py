from __future__ import annotations

import tempfile
from pathlib import Path

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.context import compile_cognitive_input
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_retrieval import MemoryChunk, select_memory_chunks
from relaylm.providers.openai_compatible import serialize_cognitive_input
from relaylm.state import CanonicalState, StateRecord
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory
from relaylm.turn import MemoryRetrievalBudget, run_user_turn


_MEMORY = """# Memory

## Preferences

Rin likes tea.

## Coffee

Rin currently prefers coffee over tea.

## Travel

Rin visited Fukuoka last year.
"""


class _RecordingMemoryProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        self.inputs.append(cognitive_input)
        return CognitiveOutput("ok")


class _ExplodingMemoryReadCharacter(CharacterDirectory):
    def load_memory_markdown(self) -> str | None:
        raise AssertionError("MEMORY.md must not be read without an explicit budget")


class _FailingMemoryReadCharacter(CharacterDirectory):
    def load_memory_markdown(self) -> str | None:
        raise CharacterDataError("cannot read MEMORY.md: intentional evaluation failure")


def _make_memory_character(
    root: Path,
    *,
    cls: type[CharacterDirectory] = CharacterDirectory,
) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(
        "# Evaluation Character\n\nBe honest and grounded.\n", encoding="utf-8"
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: evaluation\n  name: Evaluation\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}\n', encoding="utf-8"
    )
    (root / "memory" / "MEMORY.md").write_text(_MEMORY, encoding="utf-8")
    return cls(root)


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


async def evaluate_ordinary_turn_memory_retrieval() -> EvaluationScenarioResult:
    with tempfile.TemporaryDirectory(prefix="relaylm-memory-turn-eval-") as temporary:
        root = Path(temporary)
        character = _make_memory_character(root)
        provider = _RecordingMemoryProvider()
        await run_user_turn(
            character=character,
            provider=provider,
            content="What do you remember about coffee?",
            memory_budget=MemoryRetrievalBudget(max_chunks=1, max_chars=200),
        )
        selected_memory = provider.inputs[0].memory if provider.inputs else ()

    with tempfile.TemporaryDirectory(prefix="relaylm-memory-default-eval-") as temporary:
        root = Path(temporary)
        default_character = _make_memory_character(
            root, cls=_ExplodingMemoryReadCharacter
        )
        default_provider = _RecordingMemoryProvider()
        await run_user_turn(
            character=default_character,
            provider=default_provider,
            content="What do you remember about coffee?",
        )
        default_memory = default_provider.inputs[0].memory if default_provider.inputs else ()

    with tempfile.TemporaryDirectory(prefix="relaylm-memory-failure-eval-") as temporary:
        root = Path(temporary)
        failing_character = _make_memory_character(
            root, cls=_FailingMemoryReadCharacter
        )
        failing_provider = _RecordingMemoryProvider()
        failure_observed = False
        try:
            await run_user_turn(
                character=failing_character,
                provider=failing_provider,
                content="What do you remember about coffee?",
                memory_budget=MemoryRetrievalBudget(max_chunks=1, max_chars=200),
            )
        except CharacterDataError as exc:
            failure_observed = "intentional evaluation failure" in str(exc)
        reopened = CharacterDirectory(root)
        failed_events = list(reopened.iter_events())
        failed_state = reopened.load_state()

    checks = (
        EvaluationCheck(
            check_id="explicit_budget_projects_relevant_memory",
            boundary="memory_retrieval",
            passed=len(selected_memory) == 1
            and selected_memory[0].location == "memory/MEMORY.md#memory/coffee",
            expected=1,
            observed=len(selected_memory),
        ),
        EvaluationCheck(
            check_id="successful_turn_calls_provider_once",
            boundary="ordinary_turn",
            passed=provider.calls == 1,
            expected=1,
            observed=provider.calls,
        ),
        EvaluationCheck(
            check_id="omitted_budget_preserves_no_retrieval_behavior",
            boundary="ordinary_turn",
            passed=default_provider.calls == 1 and default_memory == (),
            expected=0,
            observed=len(default_memory),
        ),
        EvaluationCheck(
            check_id="memory_read_failure_skips_provider",
            boundary="ordinary_turn",
            passed=failure_observed and failing_provider.calls == 0,
            expected=0,
            observed=failing_provider.calls,
        ),
        EvaluationCheck(
            check_id="memory_read_failure_preserves_user_only",
            boundary="persistence",
            passed=[event.actor for event in failed_events] == ["user"]
            and failed_state.states == (),
            expected="user",
            observed=",".join(event.actor for event in failed_events) or "none",
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="ordinary_turn_memory_retrieval",
        checks=checks,
        metrics={
            "successful_provider_calls": provider.calls,
            "selected_memory_count": len(selected_memory),
            "default_memory_count": len(default_memory),
            "failed_retrieval_provider_calls": failing_provider.calls,
            "failed_retrieval_event_count": len(failed_events),
        },
    )


async def evaluate_state_memory_authority_filter() -> EvaluationScenarioResult:
    identity = Identity("# Evaluation Character\nBe grounded.")
    current = Event.create(
        type="message",
        actor="user",
        payload={"content": "What do you remember about tea?"},
        event_id="current-authority-event",
        timestamp="2026-08-17T06:05:00+00:00",
    )

    def record(
        *,
        state_id: str,
        state_class: str,
        key: str,
        value: object,
    ) -> StateRecord:
        return StateRecord(
            state_id=state_id,
            state_class=state_class,
            key=key,
            value=value,
            sources=("source-event",),
        )

    def chunk(*, heading: str, content: str) -> MemoryChunk:
        slug = heading.casefold().replace(" ", "-")
        return MemoryChunk(
            heading_path=("Memory", heading),
            location=f"memory/MEMORY.md#memory/{slug}",
            content=f"## {heading}\n\n{content}",
        )

    residence_state = CanonicalState(
        states=(
            record(
                state_id="residence",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
            ),
        )
    )
    stale_residence = chunk(
        heading="Residence Location",
        content="Rin lives in Hokkaido.",
    )
    compatible_residence = chunk(
        heading="Residence Location",
        content="Rin lives in Fukuoka.",
    )
    trip_history = chunk(
        heading="Trip History",
        content="Rin once stayed in Hokkaido.",
    )

    stale = compile_cognitive_input(
        identity=identity,
        state=residence_state,
        current_event=current,
        retrieved_memory=(stale_residence,),
    )
    compatible = compile_cognitive_input(
        identity=identity,
        state=residence_state,
        current_event=current,
        retrieved_memory=(compatible_residence,),
    )
    capped = compile_cognitive_input(
        identity=identity,
        state=residence_state,
        current_event=current,
        retrieved_memory=(stale_residence,),
        max_state_records=0,
    )
    historical = compile_cognitive_input(
        identity=identity,
        state=residence_state,
        current_event=current,
        retrieved_memory=(trip_history,),
    )

    coffee_state = CanonicalState(
        states=(
            record(
                state_id="coffee-liking",
                state_class="user.preference",
                key="coffee",
                value="likes",
            ),
        )
    )
    substring_conflict = compile_cognitive_input(
        identity=identity,
        state=coffee_state,
        current_event=current,
        retrieved_memory=(chunk(heading="Coffee", content="Rin dislikes coffee."),),
    )

    comparative_state = CanonicalState(
        states=(
            record(
                state_id="tea-liking",
                state_class="user.preference",
                key="tea",
                value="likes",
            ),
            record(
                state_id="preferred-beverage",
                state_class="user.preference",
                key="preferred_beverage",
                value="coffee",
            ),
        )
    )
    comparative = compile_cognitive_input(
        identity=identity,
        state=comparative_state,
        current_event=current,
        retrieved_memory=(
            chunk(
                heading="Preferred Beverage",
                content="Tea is Rin's preferred beverage.",
            ),
            chunk(heading="Tea", content="Rin likes tea."),
        ),
    )
    preserved_tea_state_count = sum(
        1
        for state_record in comparative.state
        if state_record.key == "tea" and state_record.value == "likes"
    )

    checks = (
        EvaluationCheck(
            check_id="stale_explicit_key_memory_is_suppressed",
            boundary="context_authority",
            passed=stale.memory == (),
            expected=0,
            observed=len(stale.memory),
        ),
        EvaluationCheck(
            check_id="compatible_current_value_memory_is_retained",
            boundary="context_authority",
            passed=len(compatible.memory) == 1,
            expected=1,
            observed=len(compatible.memory),
        ),
        EvaluationCheck(
            check_id="authority_uses_full_active_state_before_residency_cap",
            boundary="canonical_state",
            passed=capped.state == () and capped.memory == (),
            expected=0,
            observed=len(capped.memory),
        ),
        EvaluationCheck(
            check_id="unrelated_historical_heading_is_retained",
            boundary="context_authority",
            passed=len(historical.memory) == 1,
            expected=1,
            observed=len(historical.memory),
        ),
        EvaluationCheck(
            check_id="lexical_value_matching_is_not_substring_matching",
            boundary="context_authority",
            passed=substring_conflict.memory == (),
            expected=0,
            observed=len(substring_conflict.memory),
        ),
        EvaluationCheck(
            check_id="comparative_preference_shadow_preserves_weaker_positive_state",
            boundary="canonical_state",
            passed=len(comparative.memory) == 1
            and comparative.memory[0].location.endswith("/tea")
            and preserved_tea_state_count == 1,
            expected=1,
            observed=preserved_tea_state_count,
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="state_memory_authority_filter",
        checks=checks,
        metrics={
            "stale_memory_count": len(stale.memory),
            "compatible_memory_count": len(compatible.memory),
            "capped_state_memory_count": len(capped.memory),
            "historical_memory_count": len(historical.memory),
            "substring_conflict_memory_count": len(substring_conflict.memory),
            "comparative_memory_count": len(comparative.memory),
            "preserved_tea_state_count": preserved_tea_state_count,
        },
    )
