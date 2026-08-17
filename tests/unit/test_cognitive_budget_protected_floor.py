from __future__ import annotations

from dataclasses import dataclass

import pytest

from relaylm.budget import (
    BudgetDegradationPolicy,
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
    enforce_protected_serialized_input_floor,
    enforce_total_cognitive_budget,
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
        canonical_state=CountEnvelope(0, 0),
        working_context=CountCharacterEnvelope(0, 0, 0, 0),
        retrieved_memory=CountCharacterEnvelope(0, 0, 0, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
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
        return SerializedInputTokenCount(
            total_input_tokens=self.totals[len(self.inputs) - 1],
            required_input_framing_tokens=10,
            mode=TokenCountMode.EXACT,
        )


def test_protected_floor_overflow_fails_before_full_plan_compilation() -> None:
    policy = BudgetDegradationPolicy(initial_plan=_plan(), steps=())
    counter = _SequenceCounter([81])
    full_compile_calls = 0

    def compile_full(_: BudgetPlan) -> CognitiveInput:
        nonlocal full_compile_calls
        full_compile_calls += 1
        return _input("full")

    with pytest.raises(CognitiveBudgetExceeded) as raised:
        enforce_total_cognitive_budget(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            policy=policy,
            compile_protected_cognitive_input=lambda: _input("protected"),
            compile_cognitive_input=compile_full,
            token_counter=counter,
        )

    error = raised.value
    assert error.reason is BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT
    assert error.final_plan is None
    assert error.final_count.total_input_tokens == 81
    assert error.degradation_step_count == 0
    assert "overflow_tokens=1" in str(error)
    assert full_compile_calls == 0
    assert len(counter.inputs) == 1
    assert counter.inputs[0].input.payload["content"] == "protected"


def test_protected_floor_fit_then_enforces_full_serialized_input() -> None:
    policy = BudgetDegradationPolicy(initial_plan=_plan(), steps=())
    counter = _SequenceCounter([50, 70])
    compiled: list[BudgetPlan] = []

    def compile_full(plan: BudgetPlan) -> CognitiveInput:
        compiled.append(plan)
        return _input("full")

    result = enforce_total_cognitive_budget(
        config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
        policy=policy,
        compile_protected_cognitive_input=lambda: _input("protected"),
        compile_cognitive_input=compile_full,
        token_counter=counter,
    )

    assert len(counter.inputs) == 2
    assert counter.inputs[0].input.payload["content"] == "protected"
    assert counter.inputs[1].input.payload["content"] == "full"
    assert compiled == [policy.initial_plan]
    assert result.outcome is BudgetEnforcementOutcome.FIT
    assert result.count.total_input_tokens == 70


def test_direct_protected_floor_guard_returns_authoritative_count() -> None:
    counter = _SequenceCounter([80])
    count = enforce_protected_serialized_input_floor(
        config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
        protected_cognitive_input=_input("protected"),
        token_counter=counter,
    )

    assert count.total_input_tokens == 80
    assert len(counter.inputs) == 1


def test_protected_floor_guard_rejects_untyped_projection_and_counter_result() -> None:
    with pytest.raises(TypeError, match="protected_cognitive_input"):
        enforce_protected_serialized_input_floor(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            protected_cognitive_input="bad",  # type: ignore[arg-type]
            token_counter=_SequenceCounter([1]),
        )

    class BadCounter:
        def count_serialized_input(self, _: CognitiveInput) -> int:
            return 1

    with pytest.raises(TypeError, match="SerializedInputTokenCount"):
        enforce_protected_serialized_input_floor(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            protected_cognitive_input=_input("protected"),
            token_counter=BadCounter(),  # type: ignore[arg-type]
        )


def test_total_enforcement_rejects_untyped_protected_projection() -> None:
    with pytest.raises(TypeError, match="compile_protected_cognitive_input"):
        enforce_total_cognitive_budget(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            policy=BudgetDegradationPolicy(initial_plan=_plan(), steps=()),
            compile_protected_cognitive_input=lambda: "bad",  # type: ignore[arg-type,return-value]
            compile_cognitive_input=lambda _: _input("full"),
            token_counter=_SequenceCounter([1]),
        )
