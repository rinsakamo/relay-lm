from __future__ import annotations

from dataclasses import dataclass

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
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
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
        return SerializedInputTokenCount(
            total_input_tokens=self.totals[len(self.inputs) - 1],
            required_input_framing_tokens=10,
            mode=TokenCountMode.EXACT,
        )


def _run_degraded_sequence() -> tuple[str, tuple[int, ...], int]:
    policy = _policy()
    compiled: list[BudgetPlan] = []
    counter = _SequenceCounter([90, 75])

    def compile_input(plan: BudgetPlan) -> CognitiveInput:
        compiled.append(plan)
        return _input(f"deterministic-{len(compiled)}")

    result = enforce_serialized_input_budget(
        config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
        policy=policy,
        compile_cognitive_input=compile_input,
        token_counter=counter,
    )
    return (
        result.outcome.value,
        tuple(plan.retrieved_memory.max_items for plan in compiled),
        result.count.total_input_tokens,
    )


async def evaluate_serialized_fit_enforcement() -> EvaluationScenarioResult:
    initial_policy = BudgetDegradationPolicy(initial_plan=_plan(), steps=())
    initial_compiled: list[BudgetPlan] = []
    initial_counter = _SequenceCounter([70])

    def compile_initial(plan: BudgetPlan) -> CognitiveInput:
        initial_compiled.append(plan)
        return _input("initial")

    initial_result = enforce_serialized_input_budget(
        config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
        policy=initial_policy,
        compile_cognitive_input=compile_initial,
        token_counter=initial_counter,
    )

    degraded_policy = _policy()
    degraded_compiled: list[BudgetPlan] = []
    degraded_counter = _SequenceCounter([90, 75])

    def compile_degraded(plan: BudgetPlan) -> CognitiveInput:
        degraded_compiled.append(plan)
        return _input(f"degraded-{len(degraded_compiled)}")

    degraded_result = enforce_serialized_input_budget(
        config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
        policy=degraded_policy,
        compile_cognitive_input=compile_degraded,
        token_counter=degraded_counter,
    )

    failure_compiled: list[BudgetPlan] = []
    failure_counter = _SequenceCounter([90, 85])
    failure: CognitiveBudgetExceeded | None = None

    def compile_failure(plan: BudgetPlan) -> CognitiveInput:
        failure_compiled.append(plan)
        return _input(f"failure-{len(failure_compiled)}")

    try:
        enforce_serialized_input_budget(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            policy=degraded_policy,
            compile_cognitive_input=compile_failure,
            token_counter=failure_counter,
        )
    except CognitiveBudgetExceeded as error:
        failure = error

    deterministic_first = _run_degraded_sequence()
    deterministic_second = _run_degraded_sequence()

    invalid_compiler_rejected = False
    try:
        enforce_serialized_input_budget(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            policy=initial_policy,
            compile_cognitive_input=lambda _: "not-input",  # type: ignore[arg-type,return-value]
            token_counter=_SequenceCounter([10]),
        )
    except TypeError:
        invalid_compiler_rejected = True

    class _BadCounter:
        def count_serialized_input(self, _: CognitiveInput) -> int:
            return 10

    invalid_counter_rejected = False
    try:
        enforce_serialized_input_budget(
            config=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
            policy=initial_policy,
            compile_cognitive_input=lambda _: _input("valid"),
            token_counter=_BadCounter(),  # type: ignore[arg-type]
        )
    except TypeError:
        invalid_counter_rejected = True

    checks = (
        EvaluationCheck(
            check_id="initial_fit_returns_without_pressure",
            boundary="cognitive_budget",
            passed=(
                initial_compiled == [initial_policy.initial_plan]
                and len(initial_counter.inputs) == 1
                and initial_result.outcome is BudgetEnforcementOutcome.FIT
                and not initial_result.pressure_occurred
                and initial_result.degradation_step_count == 0
                and initial_result.count.total_input_tokens == 70
            ),
            expected="fit",
            observed=initial_result.outcome.value,
        ),
        EvaluationCheck(
            check_id="overflow_recompiles_with_explicit_degraded_plan",
            boundary="cognitive_budget",
            passed=(
                degraded_compiled
                == [degraded_policy.initial_plan, degraded_policy.final_plan]
                and len(degraded_counter.inputs) == 2
                and degraded_result.plan == degraded_policy.final_plan
                and degraded_result.count.total_input_tokens == 75
                and degraded_result.degradation_step_count == 1
                and degraded_result.outcome is BudgetEnforcementOutcome.DEGRADED_FIT
                and degraded_result.pressure_occurred
            ),
            expected="degraded_fit",
            observed=degraded_result.outcome.value,
        ),
        EvaluationCheck(
            check_id="degradation_exhaustion_raises_bounded_failure",
            boundary="cognitive_budget",
            passed=(
                failure is not None
                and failure_compiled
                == [degraded_policy.initial_plan, degraded_policy.final_plan]
                and len(failure_counter.inputs) == 2
                and failure.reason
                is BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED
                and failure.final_plan == degraded_policy.final_plan
                and failure.final_count.total_input_tokens == 85
                and failure.degradation_step_count == 1
                and "overflow_tokens=5" in str(failure)
                and not hasattr(failure, "cognitive_input")
            ),
            expected=True,
            observed=failure is not None,
        ),
        EvaluationCheck(
            check_id="same_inputs_produce_same_enforcement_sequence",
            boundary="cognitive_budget",
            passed=deterministic_first == deterministic_second,
            expected=True,
            observed=deterministic_first == deterministic_second,
        ),
        EvaluationCheck(
            check_id="untyped_compiler_and_counter_results_are_rejected",
            boundary="cognitive_budget",
            passed=invalid_compiler_rejected and invalid_counter_rejected,
            expected=2,
            observed=sum((invalid_compiler_rejected, invalid_counter_rejected)),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="serialized_fit_enforcement",
        checks=checks,
        metrics={
            "enforcement_call_count": 7,
            "fit_case_count": 3,
            "degraded_fit_case_count": 2,
            "bounded_failure_count": int(failure is not None),
            "invalid_result_rejection_count": sum(
                (invalid_compiler_rejected, invalid_counter_rejected)
            ),
        },
    )
