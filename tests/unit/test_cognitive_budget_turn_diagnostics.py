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
from relaylm.budget_diagnostics import (
    CognitiveBudgetDiagnosticOutcome,
    CognitiveBudgetExceededWithDiagnostics,
)
from relaylm.budget_enforcement import (
    BudgetEnforcementFailureReason,
    CognitiveBudgetExceeded,
    SerializedInputTokenCount,
    TokenCountMode,
)
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    run_user_turn_streaming_with_cognitive_budget_diagnostics,
    run_user_turn_with_cognitive_budget_diagnostics,
)


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


class _Provider:
    def __init__(self) -> None:
        self.generate_calls = 0
        self.stream_calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.generate_calls += 1
        return CognitiveOutput(response="ok", state_candidates=())

    async def stream_generate(self, _: CognitiveInput, emit) -> CognitiveOutput:
        self.stream_calls += 1
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


def _one_state_step_policy() -> BudgetDegradationPolicy:
    return BudgetDegradationPolicy(
        initial_plan=BudgetPlan(
            canonical_state=CountEnvelope(1, 0),
            working_context=CountCharacterEnvelope(0, 0, 0, 0),
            retrieved_memory=CountCharacterEnvelope(0, 0, 0, 0),
            event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
        ),
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


def test_buffered_budget_diagnostics_return_fit_after_one_generation(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = _Provider()
    counter = _SequenceCounter([50, 70])

    result = asyncio.run(
        run_user_turn_with_cognitive_budget_diagnostics(
            character=character,
            provider=provider,
            content="hello",
            cognitive_budget=_runtime(counter),
        )
    )

    diagnostics = result.cognitive_budget
    assert result.turn.response == "ok"
    assert provider.generate_calls == 1
    assert provider.stream_calls == 0
    assert len(counter.inputs) == 2
    assert diagnostics.outcome is CognitiveBudgetDiagnosticOutcome.FIT
    assert diagnostics.model_context_window == 100
    assert diagnostics.effective_context_capacity == 80
    assert diagnostics.reserved_output_tokens == 20
    assert diagnostics.required_input_framing_tokens == 10
    assert diagnostics.final_input_tokens == 70
    assert diagnostics.available_cognitive_capacity == 70
    assert diagnostics.pressure_occurred is False
    assert diagnostics.degradation_step_count == 0
    assert diagnostics.count_mode is TokenCountMode.EXACT


def test_buffered_budget_diagnostics_return_degraded_fit_counts(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = _Provider()
    counter = _SequenceCounter([50, 90, 70])

    result = asyncio.run(
        run_user_turn_with_cognitive_budget_diagnostics(
            character=character,
            provider=provider,
            content="hello",
            cognitive_budget=_runtime(counter, policy=_one_state_step_policy()),
        )
    )

    diagnostics = result.cognitive_budget
    assert provider.generate_calls == 1
    assert len(counter.inputs) == 3
    assert diagnostics.outcome is CognitiveBudgetDiagnosticOutcome.DEGRADED_FIT
    assert diagnostics.pressure_occurred is True
    assert diagnostics.degradation_step_count == 1
    assert diagnostics.reduced_layer_count == 1
    assert diagnostics.reduced_tier_count == 1
    assert diagnostics.tier_reductions[0].tier == 1


def test_budget_failure_raises_same_family_with_content_free_diagnostics(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = _Provider()
    counter = _SequenceCounter([81])

    with pytest.raises(CognitiveBudgetExceededWithDiagnostics) as raised:
        asyncio.run(
            run_user_turn_with_cognitive_budget_diagnostics(
                character=character,
                provider=provider,
                content="secret user content",
                cognitive_budget=_runtime(counter),
            )
        )

    failure = raised.value
    assert isinstance(failure, CognitiveBudgetExceeded)
    assert provider.generate_calls == 0
    assert provider.stream_calls == 0
    assert failure.reason is BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT
    assert failure.diagnostics.outcome is CognitiveBudgetDiagnosticOutcome.BOUNDED_FAILURE
    assert failure.diagnostics.failure_reason is BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT
    assert failure.diagnostics.final_input_tokens == 81
    assert failure.diagnostics.degradation_step_count == 0
    assert "secret user content" not in repr(failure.diagnostics)
    assert "secret user content" not in str(failure)


def test_degradation_failure_exposes_reduction_counts_without_generation(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = _Provider()
    counter = _SequenceCounter([50, 90, 85])

    with pytest.raises(CognitiveBudgetExceededWithDiagnostics) as raised:
        asyncio.run(
            run_user_turn_with_cognitive_budget_diagnostics(
                character=character,
                provider=provider,
                content="hello",
                cognitive_budget=_runtime(counter, policy=_one_state_step_policy()),
            )
        )

    diagnostics = raised.value.diagnostics
    assert provider.generate_calls == 0
    assert diagnostics.failure_reason is BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED
    assert diagnostics.degradation_step_count == 1
    assert diagnostics.reduced_layer_count == 1
    assert diagnostics.reduced_tier_count == 1


def test_streaming_budget_diagnostics_preserve_one_generation(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = _Provider()
    counter = _SequenceCounter([50, 70])
    deltas: list[str] = []

    async def emit(delta: str) -> None:
        deltas.append(delta)

    result = asyncio.run(
        run_user_turn_streaming_with_cognitive_budget_diagnostics(
            character=character,
            provider=provider,
            content="hello",
            emit_response_delta=emit,
            cognitive_budget=_runtime(counter),
        )
    )

    assert result.cognitive_budget.outcome is CognitiveBudgetDiagnosticOutcome.FIT
    assert provider.generate_calls == 0
    assert provider.stream_calls == 1
    assert len(counter.inputs) == 2
    assert deltas == ["ok"]
