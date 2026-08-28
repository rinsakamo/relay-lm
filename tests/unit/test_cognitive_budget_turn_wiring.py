from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest

from relaylm.budget import (
    BudgetDegradationPolicy,
    BudgetDegradationStep,
    BudgetLayer,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
    TotalBudgetConfig,
)
from relaylm.budget_enforcement import (
    BudgetEnforcementFailureReason,
    CognitiveBudgetExceeded,
    SerializedInputTokenCount,
    TokenCountMode,
)
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.state import CanonicalState, StateRecord
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import MemoryRetrievalBudget, run_user_turn, run_user_turn_streaming


def _make_character(root: Path, *, state: CanonicalState | None = None) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    character = CharacterDirectory(root)
    character.save_state(state or CanonicalState())
    return character


class _RecordingProvider:
    def __init__(self) -> None:
        self.generate_calls = 0
        self.stream_calls = 0
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.generate_calls += 1
        self.inputs.append(cognitive_input)
        return CognitiveOutput(response="ok", state_candidates=())

    async def stream_generate(self, cognitive_input: CognitiveInput, emit) -> CognitiveOutput:
        self.stream_calls += 1
        self.inputs.append(cognitive_input)
        await emit("ok")
        return CognitiveOutput(response="ok", state_candidates=())


@dataclass
class _SequenceCounter:
    totals: list[int]

    def __post_init__(self) -> None:
        self.inputs: list[CognitiveInput] = []

    def count_serialized_input(
        self,
        cognitive_input: CognitiveInput,
    ) -> SerializedInputTokenCount:
        self.inputs.append(cognitive_input)
        return SerializedInputTokenCount(
            total_input_tokens=self.totals[len(self.inputs) - 1],
            required_input_framing_tokens=10,
            mode=TokenCountMode.EXACT,
        )


def _zero_plan() -> BudgetPlan:
    return BudgetPlan(
        canonical_state=CountEnvelope(0, 0),
        working_context=CountCharacterEnvelope(0, 0, 0, 0),
        retrieved_memory=CountCharacterEnvelope(0, 0, 0, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
    )


def _state_degradation_policy() -> BudgetDegradationPolicy:
    initial = BudgetPlan(
        canonical_state=CountEnvelope(1, 0),
        working_context=CountCharacterEnvelope(0, 0, 0, 0),
        retrieved_memory=CountCharacterEnvelope(0, 0, 0, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
    )
    return BudgetDegradationPolicy(
        initial_plan=initial,
        steps=(
            BudgetDegradationStep(
                BudgetLayer.CANONICAL_STATE,
                CountEnvelope(0, 0),
            ),
        ),
    )


def _runtime(
    counter: _SequenceCounter,
    *,
    policy: BudgetDegradationPolicy | None = None,
) -> CognitiveBudgetRuntimeConfig:
    return CognitiveBudgetRuntimeConfig(
        total=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
        policy=policy or BudgetDegradationPolicy(initial_plan=_zero_plan(), steps=()),
        token_counter=counter,
    )


def _state() -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="s1",
                state_class="user.preference",
                key="tea",
                value="likes",
                sources=("old",),
            ),
        )
    )


def test_budgeted_buffered_turn_generates_once_after_hard_fit(tmp_path: Path) -> None:
    character = _make_character(tmp_path, state=_state())
    provider = _RecordingProvider()
    counter = _SequenceCounter([50, 70])

    result = asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="hello",
            cognitive_budget=_runtime(counter),
        )
    )

    assert result.response == "ok"
    assert provider.generate_calls == 1
    assert provider.stream_calls == 0
    assert len(provider.inputs) == 1
    supplied = provider.inputs[0]
    assert supplied.identity.content.startswith("# ReLM")
    assert supplied.input.payload["content"] == "hello"
    assert supplied.state == ()
    assert supplied.context == ()
    assert supplied.memory == ()
    assert supplied.event_evidence == ()
    assert len(counter.inputs) == 2
    assert result.state == _state()
    assert CharacterDirectory(tmp_path).load_state() == _state()
    assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == [
        "user",
        "assistant",
    ]


def test_budget_pressure_recompiles_before_single_generation(tmp_path: Path) -> None:
    character = _make_character(tmp_path, state=_state())
    provider = _RecordingProvider()
    counter = _SequenceCounter([50, 90, 70])

    asyncio.run(
        run_user_turn(
            character=character,
            provider=provider,
            content="tea please",
            cognitive_budget=_runtime(counter, policy=_state_degradation_policy()),
        )
    )

    assert len(counter.inputs) == 3
    assert counter.inputs[1].state == _state().states
    assert counter.inputs[2].state == ()
    assert provider.generate_calls == 1
    assert len(provider.inputs) == 1
    assert provider.inputs[0].state == ()
    assert CharacterDirectory(tmp_path).load_state() == _state()


def test_protected_floor_failure_occurs_before_provider_generation(tmp_path: Path) -> None:
    character = _make_character(tmp_path, state=_state())
    provider = _RecordingProvider()
    counter = _SequenceCounter([81])

    with pytest.raises(CognitiveBudgetExceeded) as raised:
        asyncio.run(
            run_user_turn(
                character=character,
                provider=provider,
                content="hello",
                cognitive_budget=_runtime(counter),
            )
        )

    assert raised.value.reason is BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT
    assert provider.generate_calls == 0
    assert provider.stream_calls == 0
    assert len(counter.inputs) == 1
    assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == ["user"]
    assert CharacterDirectory(tmp_path).load_state() == _state()


def test_degradation_exhaustion_occurs_before_provider_generation(tmp_path: Path) -> None:
    character = _make_character(tmp_path, state=_state())
    provider = _RecordingProvider()
    counter = _SequenceCounter([50, 90, 85])

    with pytest.raises(CognitiveBudgetExceeded) as raised:
        asyncio.run(
            run_user_turn(
                character=character,
                provider=provider,
                content="hello",
                cognitive_budget=_runtime(counter, policy=_state_degradation_policy()),
            )
        )

    assert raised.value.reason is BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED
    assert provider.generate_calls == 0
    assert provider.stream_calls == 0
    assert len(counter.inputs) == 3
    assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == ["user"]
    assert CharacterDirectory(tmp_path).load_state() == _state()


def test_budgeted_turn_rejects_legacy_retrieval_budget_before_event_append(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = _RecordingProvider()

    with pytest.raises(ValueError, match="cannot be combined"):
        asyncio.run(
            run_user_turn(
                character=character,
                provider=provider,
                content="hello",
                memory_budget=MemoryRetrievalBudget(max_chunks=0, max_chars=0),
                cognitive_budget=_runtime(_SequenceCounter([50, 70])),
            )
        )

    assert provider.generate_calls == 0
    assert tuple(CharacterDirectory(tmp_path).iter_events()) == ()


def test_budgeted_streaming_turn_streams_exactly_once_after_fit(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = _RecordingProvider()
    counter = _SequenceCounter([50, 70])
    deltas: list[str] = []

    async def emit(delta: str) -> None:
        deltas.append(delta)

    result = asyncio.run(
        run_user_turn_streaming(
            character=character,
            provider=provider,
            content="hello",
            emit_response_delta=emit,
            cognitive_budget=_runtime(counter),
        )
    )

    assert result.response == "ok"
    assert provider.generate_calls == 0
    assert provider.stream_calls == 1
    assert len(provider.inputs) == 1
    assert len(counter.inputs) == 2
    assert deltas == ["ok"]
    assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == [
        "user",
        "assistant",
    ]
