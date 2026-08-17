from __future__ import annotations

from dataclasses import dataclass

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
    BudgetEnforcementOutcome,
    CognitiveBudgetExceeded,
    SerializedInputTokenCount,
    TokenCountMode,
    enforce_serialized_input_budget,
)
from relaylm.cognitive import CognitiveInput
from relaylm.events import Event
from relaylm.identity import Identity


def _input(label: str) -> CognitiveInput:
    return CognitiveInput(
        identity=Identity(f"# {label}"),
        state_classes=(),
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": label},
            event_id=f"evt-{label}",
            timestamp="2026-08-17T00:00:00+00:00",
        ),
    )


def _plan() -> BudgetPlan:
    return BudgetPlan(
        canonical_state=CountEnvelope(max_items=1, floor_items=1),
        working_context=CountCharacterEnvelope(0, 0, 0, 0),
        retrieved_memory=CountCharacterEnvelope(2, 0, 200, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
    )


def _policy() -> BudgetDegradationPolicy:
    return BudgetDegradationPolicy(
        initial_plan=_plan(),
        steps=(
            BudgetDegradationStep(
                BudgetLayer.RETRIEVED_MEMORY,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
        ),
    )


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
        total = self.totals[len(self.inputs) - 1]
        return SerializedInputTokenCount(
            total_input_tokens=total,
            required_input_framing_tokens=10,
            mode=TokenCountMode.EXACT,
        )


def test_initial_fit_returns_input_without_pressure() -> None:
    policy = BudgetDegradationPolicy(initial_plan=_plan(), steps=())
    compiled: list[BudgetPlan] = []
    counter = _SequenceCounter([70])

    def compile_input(plan: BudgetPlan) -> CognitiveInput:
        compiled.append(plan)
        return _input("initial")

    result = enforce_serialized_input_budget(
        config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
        policy=policy,
        compile_cognitive_input=compile_input,
        token_counter=counter,
    )

    assert compiled == [policy.initial_plan]
    assert len(counter.inputs) == 1
    assert result.cognitive_input.input.payload["content"] == "initial"
    assert result.degradation_step_count == 0
    assert result.outcome is BudgetEnforcementOutcome.FIT
    assert result.pressure_occurred is False


def test_overflow_recompiles_with_next_explicit_plan_until_fit() -> None:
    policy = _policy()
    compiled: list[BudgetPlan] = []
    counter = _SequenceCounter([90, 75])

    def compile_input(plan: BudgetPlan) -> CognitiveInput:
        compiled.append(plan)
        return _input(f"plan-{len(compiled)}")

    result = enforce_serialized_input_budget(
        config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
        policy=policy,
        compile_cognitive_input=compile_input,
        token_counter=counter,
    )

    assert compiled == [policy.initial_plan, policy.final_plan]
    assert len(counter.inputs) == 2
    assert result.plan == policy.final_plan
    assert result.cognitive_input.input.payload["content"] == "plan-2"
    assert result.count.total_input_tokens == 75
    assert result.degradation_step_count == 1
    assert result.outcome is BudgetEnforcementOutcome.DEGRADED_FIT
    assert result.pressure_occurred is True


def test_exhausted_policy_raises_bounded_failure_without_terminal_recount() -> None:
    policy = _policy()
    compiled: list[BudgetPlan] = []
    counter = _SequenceCounter([90, 85])

    def compile_input(plan: BudgetPlan) -> CognitiveInput:
        compiled.append(plan)
        return _input(f"plan-{len(compiled)}")

    with pytest.raises(CognitiveBudgetExceeded) as raised:
        enforce_serialized_input_budget(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            policy=policy,
            compile_cognitive_input=compile_input,
            token_counter=counter,
        )

    error = raised.value
    assert compiled == [policy.initial_plan, policy.final_plan]
    assert len(counter.inputs) == 2
    assert error.reason is BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED
    assert error.final_plan == policy.final_plan
    assert error.final_count.total_input_tokens == 85
    assert error.degradation_step_count == 1
    assert "overflow_tokens=5" in str(error)
    assert not hasattr(error, "cognitive_input")


def test_same_plan_and_counts_produce_same_enforcement_sequence() -> None:
    policy = _policy()

    def run_once() -> tuple[BudgetEnforcementOutcome, tuple[BudgetPlan, ...], int]:
        compiled: list[BudgetPlan] = []
        counter = _SequenceCounter([90, 75])

        def compile_input(plan: BudgetPlan) -> CognitiveInput:
            compiled.append(plan)
            return _input(f"plan-{len(compiled)}")

        result = enforce_serialized_input_budget(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            policy=policy,
            compile_cognitive_input=compile_input,
            token_counter=counter,
        )
        return result.outcome, tuple(compiled), result.count.total_input_tokens

    assert run_once() == run_once()


def test_enforcement_rejects_untyped_compiler_and_counter_results() -> None:
    policy = BudgetDegradationPolicy(initial_plan=_plan(), steps=())

    with pytest.raises(TypeError, match="compile_cognitive_input"):
        enforce_serialized_input_budget(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            policy=policy,
            compile_cognitive_input=lambda _: "not-input",  # type: ignore[arg-type,return-value]
            token_counter=_SequenceCounter([10]),
        )

    class BadCounter:
        def count_serialized_input(self, _: CognitiveInput) -> int:
            return 10

    with pytest.raises(TypeError, match="SerializedInputTokenCount"):
        enforce_serialized_input_budget(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            policy=policy,
            compile_cognitive_input=lambda _: _input("valid"),
            token_counter=BadCounter(),  # type: ignore[arg-type]
        )
