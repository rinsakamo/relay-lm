from __future__ import annotations

import dataclasses

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
    CognitiveBudgetDiagnostics,
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
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
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


async def evaluate_total_budget_diagnostics() -> EvaluationScenarioResult:
    policy = _policy()

    fit_config = TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20)
    fit_diagnostics = diagnostics_for_budget_result(
        config=fit_config,
        policy=policy,
        result=BudgetEnforcementResult(
            cognitive_input=_input(),
            plan=policy.initial_plan,
            count=_count(70, framing=15),
            degradation_step_count=0,
        ),
    )

    degraded_config = TotalBudgetConfig(
        model_context_window=120,
        reserved_output_tokens=20,
    )
    degraded_diagnostics = diagnostics_for_budget_result(
        config=degraded_config,
        policy=policy,
        result=BudgetEnforcementResult(
            cognitive_input=_input(),
            plan=policy.plan_after_steps(3),
            count=_count(
                90,
                framing=20,
                mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
            ),
            degradation_step_count=3,
        ),
    )

    protected_failure = CognitiveBudgetExceeded(
        reason=BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT,
        config=fit_config,
        final_plan=None,
        final_count=_count(81, framing=30),
        degradation_step_count=0,
    )
    protected_diagnostics = diagnostics_for_budget_failure(
        config=fit_config,
        policy=policy,
        failure=protected_failure,
    )

    exhausted_failure = CognitiveBudgetExceeded(
        reason=BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED,
        config=fit_config,
        final_plan=policy.final_plan,
        final_count=_count(85),
        degradation_step_count=len(policy.steps),
    )
    exhausted_diagnostics = diagnostics_for_budget_failure(
        config=fit_config,
        policy=policy,
        failure=exhausted_failure,
    )

    clamp_config = TotalBudgetConfig(model_context_window=32, reserved_output_tokens=20)
    clamp_failure = CognitiveBudgetExceeded(
        reason=BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT,
        config=clamp_config,
        final_plan=None,
        final_count=_count(20, framing=20),
        degradation_step_count=0,
    )
    clamp_diagnostics = diagnostics_for_budget_failure(
        config=clamp_config,
        policy=BudgetDegradationPolicy(initial_plan=_plan(), steps=()),
        failure=clamp_failure,
    )

    mismatched_config_rejected = False
    try:
        diagnostics_for_budget_failure(
            config=TotalBudgetConfig(
                model_context_window=101,
                reserved_output_tokens=20,
            ),
            policy=policy,
            failure=exhausted_failure,
        )
    except ValueError:
        mismatched_config_rejected = True

    invalid_step_count_rejected = False
    try:
        diagnostics_for_budget_result(
            config=fit_config,
            policy=policy,
            result=BudgetEnforcementResult(
                cognitive_input=_input(),
                plan=policy.final_plan,
                count=_count(70),
                degradation_step_count=len(policy.steps) + 1,
            ),
        )
    except ValueError:
        invalid_step_count_rejected = True

    diagnostic_field_names = {
        field.name for field in dataclasses.fields(CognitiveBudgetDiagnostics)
    }
    forbidden_content_fields = {
        "cognitive_input",
        "state",
        "continuity",
        "memory",
        "event",
        "identity",
        "content",
    }
    content_field_count = len(diagnostic_field_names & forbidden_content_fields)

    checks = (
        EvaluationCheck(
            check_id="fit_reports_capacity_counts_and_exact_mode",
            boundary="cognitive_budget",
            passed=(
                fit_diagnostics.model_context_window == 100
                and fit_diagnostics.effective_context_capacity == 80
                and fit_diagnostics.reserved_output_tokens == 20
                and fit_diagnostics.required_input_framing_tokens == 15
                and fit_diagnostics.final_input_tokens == 70
                and fit_diagnostics.final_cognitive_input_tokens == 55
                and fit_diagnostics.available_cognitive_capacity == 65
                and not fit_diagnostics.pressure_occurred
                and fit_diagnostics.degradation_step_count == 0
                and fit_diagnostics.reduced_layer_count == 0
                and fit_diagnostics.reduced_tier_count == 0
                and fit_diagnostics.tier_reductions == ()
                and fit_diagnostics.outcome is CognitiveBudgetDiagnosticOutcome.FIT
                and fit_diagnostics.failure_reason is None
                and fit_diagnostics.count_mode is TokenCountMode.EXACT
            ),
            expected="fit/exact",
            observed=f"{fit_diagnostics.outcome.value}/{fit_diagnostics.count_mode.value}",
        ),
        EvaluationCheck(
            check_id="degraded_fit_aggregates_layers_tiers_and_estimate_mode",
            boundary="cognitive_budget",
            passed=(
                degraded_diagnostics.outcome
                is CognitiveBudgetDiagnosticOutcome.DEGRADED_FIT
                and degraded_diagnostics.pressure_occurred
                and degraded_diagnostics.degradation_step_count == 3
                and degraded_diagnostics.reduced_layer_count == 3
                and degraded_diagnostics.reduced_tier_count == 2
                and tuple(item.tier for item in degraded_diagnostics.tier_reductions)
                == (3, 2)
                and degraded_diagnostics.tier_reductions[0].reduction_step_count == 2
                and degraded_diagnostics.tier_reductions[0].reduced_layer_count == 2
                and degraded_diagnostics.tier_reductions[1].reduction_step_count == 1
                and degraded_diagnostics.tier_reductions[1].reduced_layer_count == 1
                and degraded_diagnostics.count_mode
                is TokenCountMode.CONSERVATIVE_ESTIMATE
            ),
            expected="3 reductions across tiers 3,2",
            observed=(
                f"{degraded_diagnostics.degradation_step_count} reductions across tiers "
                + ",".join(
                    str(item.tier) for item in degraded_diagnostics.tier_reductions
                )
            ),
        ),
        EvaluationCheck(
            check_id="bounded_failures_preserve_reason_and_reduction_counts",
            boundary="cognitive_budget",
            passed=(
                protected_diagnostics.outcome
                is CognitiveBudgetDiagnosticOutcome.BOUNDED_FAILURE
                and protected_diagnostics.failure_reason
                is BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT
                and protected_diagnostics.degradation_step_count == 0
                and protected_diagnostics.reduced_layer_count == 0
                and protected_diagnostics.reduced_tier_count == 0
                and exhausted_diagnostics.outcome
                is CognitiveBudgetDiagnosticOutcome.BOUNDED_FAILURE
                and exhausted_diagnostics.failure_reason
                is BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED
                and exhausted_diagnostics.degradation_step_count == 4
                and exhausted_diagnostics.reduced_layer_count == 4
                and exhausted_diagnostics.reduced_tier_count == 3
                and tuple(item.tier for item in exhausted_diagnostics.tier_reductions)
                == (3, 2, 1)
            ),
            expected="protected:0; exhausted:4",
            observed=(
                f"protected:{protected_diagnostics.degradation_step_count}; "
                f"exhausted:{exhausted_diagnostics.degradation_step_count}"
            ),
        ),
        EvaluationCheck(
            check_id="diagnostics_surface_remains_content_free",
            boundary="cognitive_budget",
            passed=(
                content_field_count == 0
                and "secret semantic payload" not in repr(fit_diagnostics)
                and "secret semantic payload" not in repr(degraded_diagnostics)
            ),
            expected=0,
            observed=content_field_count,
        ),
        EvaluationCheck(
            check_id="available_cognitive_capacity_clamps_at_zero",
            boundary="cognitive_budget",
            passed=(
                clamp_diagnostics.effective_context_capacity == 12
                and clamp_diagnostics.required_input_framing_tokens == 20
                and clamp_diagnostics.available_cognitive_capacity == 0
            ),
            expected=0,
            observed=clamp_diagnostics.available_cognitive_capacity,
        ),
        EvaluationCheck(
            check_id="mismatched_config_and_invalid_step_count_are_rejected",
            boundary="cognitive_budget",
            passed=mismatched_config_rejected and invalid_step_count_rejected,
            expected=2,
            observed=sum(
                (mismatched_config_rejected, invalid_step_count_rejected)
            ),
        ),
    )

    successful_diagnostics = (fit_diagnostics, degraded_diagnostics)
    failure_diagnostics = (
        protected_diagnostics,
        exhausted_diagnostics,
        clamp_diagnostics,
    )
    return EvaluationScenarioResult(
        scenario_id="total_budget_diagnostics",
        checks=checks,
        metrics={
            "result_diagnostics_call_count": 3,
            "failure_diagnostics_call_count": 4,
            "successful_outcome_count": len(successful_diagnostics),
            "bounded_failure_outcome_count": len(failure_diagnostics),
            "content_field_count": content_field_count,
            "invalid_input_rejection_count": sum(
                (mismatched_config_rejected, invalid_step_count_rejected)
            ),
        },
    )
