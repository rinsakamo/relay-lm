from __future__ import annotations

import dataclasses

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
    diagnostics_for_budget_failure,
    diagnostics_for_budget_result,
)
from relaylm.budget_enforcement import (
    BudgetEnforcementFailureReason,
    BudgetEnforcementResult,
    CognitiveBudgetExceeded,
    SerializedInputTokenCount,
    TokenCountMode,
)
from relaylm.cognitive import CognitiveInput
from relaylm.events import Event
from relaylm.identity import Identity


def _input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM"),
        state_classes=(),
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "secret semantic payload"},
            event_id="evt-now",
            timestamp="2026-08-17T00:00:00+00:00",
        ),
    )


def _plan() -> BudgetPlan:
    return BudgetPlan(
        canonical_state=CountEnvelope(4, 1),
        working_context=CountCharacterEnvelope(2, 0, 200, 0),
        retrieved_memory=CountCharacterEnvelope(2, 0, 200, 0),
        event_evidence=CountCharacterEnvelope(1, 0, 100, 0),
    )


def _policy() -> BudgetDegradationPolicy:
    return BudgetDegradationPolicy(
        initial_plan=_plan(),
        steps=(
            BudgetDegradationStep(
                BudgetLayer.RETRIEVED_MEMORY,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.EVENT_EVIDENCE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.WORKING_CONTEXT,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.CANONICAL_STATE,
                CountEnvelope(1, 1),
            ),
        ),
    )


def _count(
    total: int,
    *,
    framing: int = 20,
    mode: TokenCountMode = TokenCountMode.EXACT,
) -> SerializedInputTokenCount:
    return SerializedInputTokenCount(
        total_input_tokens=total,
        required_input_framing_tokens=framing,
        mode=mode,
    )


def test_fit_diagnostics_report_capacity_counts_and_exact_mode() -> None:
    config = TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20)
    policy = _policy()
    result = BudgetEnforcementResult(
        cognitive_input=_input(),
        plan=policy.initial_plan,
        count=_count(70, framing=15),
        degradation_step_count=0,
    )

    diagnostics = diagnostics_for_budget_result(
        config=config,
        policy=policy,
        result=result,
    )

    assert diagnostics.model_context_window == 100
    assert diagnostics.effective_context_capacity == 80
    assert diagnostics.reserved_output_tokens == 20
    assert diagnostics.required_input_framing_tokens == 15
    assert diagnostics.final_input_tokens == 70
    assert diagnostics.final_cognitive_input_tokens == 55
    assert diagnostics.available_cognitive_capacity == 65
    assert diagnostics.pressure_occurred is False
    assert diagnostics.degradation_step_count == 0
    assert diagnostics.reduced_layer_count == 0
    assert diagnostics.reduced_tier_count == 0
    assert diagnostics.tier_reductions == ()
    assert diagnostics.outcome is CognitiveBudgetDiagnosticOutcome.FIT
    assert diagnostics.failure_reason is None
    assert diagnostics.count_mode is TokenCountMode.EXACT


def test_degraded_fit_diagnostics_aggregate_reduced_layers_and_tiers() -> None:
    config = TotalBudgetConfig(model_context_window=120, reserved_output_tokens=20)
    policy = _policy()
    result = BudgetEnforcementResult(
        cognitive_input=_input(),
        plan=policy.plan_after_steps(3),
        count=_count(90, framing=20, mode=TokenCountMode.CONSERVATIVE_ESTIMATE),
        degradation_step_count=3,
    )

    diagnostics = diagnostics_for_budget_result(
        config=config,
        policy=policy,
        result=result,
    )

    assert diagnostics.outcome is CognitiveBudgetDiagnosticOutcome.DEGRADED_FIT
    assert diagnostics.pressure_occurred is True
    assert diagnostics.degradation_step_count == 3
    assert diagnostics.reduced_layer_count == 3
    assert diagnostics.reduced_tier_count == 2
    assert [item.tier for item in diagnostics.tier_reductions] == [3, 2]
    assert diagnostics.tier_reductions[0].reduction_step_count == 2
    assert diagnostics.tier_reductions[0].reduced_layer_count == 2
    assert diagnostics.tier_reductions[1].reduction_step_count == 1
    assert diagnostics.tier_reductions[1].reduced_layer_count == 1
    assert diagnostics.count_mode is TokenCountMode.CONSERVATIVE_ESTIMATE


def test_protected_floor_failure_diagnostics_are_bounded_and_content_free() -> None:
    config = TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20)
    policy = _policy()
    failure = CognitiveBudgetExceeded(
        reason=BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT,
        config=config,
        final_plan=None,
        final_count=_count(81, framing=30),
        degradation_step_count=0,
    )

    diagnostics = diagnostics_for_budget_failure(
        config=config,
        policy=policy,
        failure=failure,
    )

    assert diagnostics.outcome is CognitiveBudgetDiagnosticOutcome.BOUNDED_FAILURE
    assert diagnostics.failure_reason is BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT
    assert diagnostics.pressure_occurred is True
    assert diagnostics.degradation_step_count == 0
    assert diagnostics.reduced_layer_count == 0
    assert diagnostics.reduced_tier_count == 0
    assert diagnostics.final_input_tokens == 81
    assert diagnostics.available_cognitive_capacity == 50

    names = {field.name for field in dataclasses.fields(diagnostics)}
    assert "cognitive_input" not in names
    assert "state" not in names
    assert "continuity" not in names
    assert "memory" not in names
    assert "event" not in names
    assert "identity" not in names
    assert "content" not in repr(diagnostics)
    assert "secret semantic payload" not in repr(diagnostics)


def test_degradation_exhaustion_reports_all_applied_reductions() -> None:
    config = TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20)
    policy = _policy()
    failure = CognitiveBudgetExceeded(
        reason=BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED,
        config=config,
        final_plan=policy.final_plan,
        final_count=_count(85),
        degradation_step_count=len(policy.steps),
    )

    diagnostics = diagnostics_for_budget_failure(
        config=config,
        policy=policy,
        failure=failure,
    )

    assert diagnostics.failure_reason is BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED
    assert diagnostics.degradation_step_count == 4
    assert diagnostics.reduced_layer_count == 4
    assert diagnostics.reduced_tier_count == 3
    assert [item.tier for item in diagnostics.tier_reductions] == [3, 2, 1]


def test_available_cognitive_capacity_clamps_when_framing_exceeds_context_capacity() -> None:
    config = TotalBudgetConfig(model_context_window=32, reserved_output_tokens=20)
    diagnostics = diagnostics_for_budget_failure(
        config=config,
        policy=BudgetDegradationPolicy(initial_plan=_plan(), steps=()),
        failure=CognitiveBudgetExceeded(
            reason=BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT,
            config=config,
            final_plan=None,
            final_count=_count(20, framing=20),
            degradation_step_count=0,
        ),
    )

    assert diagnostics.effective_context_capacity == 12
    assert diagnostics.available_cognitive_capacity == 0


def test_failure_diagnostics_reject_mismatched_config_and_invalid_step_count() -> None:
    policy = _policy()
    failure = CognitiveBudgetExceeded(
        reason=BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED,
        config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
        final_plan=policy.final_plan,
        final_count=_count(85),
        degradation_step_count=len(policy.steps),
    )

    with pytest.raises(ValueError, match="must match"):
        diagnostics_for_budget_failure(
            config=TotalBudgetConfig(model_context_window=101, reserved_output_tokens=20),
            policy=policy,
            failure=failure,
        )

    impossible_result = BudgetEnforcementResult(
        cognitive_input=_input(),
        plan=policy.final_plan,
        count=_count(70),
        degradation_step_count=len(policy.steps) + 1,
    )
    with pytest.raises(ValueError, match="outside"):
        diagnostics_for_budget_result(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            policy=policy,
            result=impossible_result,
        )
