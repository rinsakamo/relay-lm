from __future__ import annotations

from dataclasses import dataclass

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


async def evaluate_protected_serialized_floor() -> EvaluationScenarioResult:
    config = TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20)
    policy = BudgetDegradationPolicy(initial_plan=_plan(), steps=())

    overflow_counter = _SequenceCounter([81])
    overflow_full_compiles: list[BudgetPlan] = []
    overflow_failure: CognitiveBudgetExceeded | None = None

    def compile_overflow_full(plan: BudgetPlan) -> CognitiveInput:
        overflow_full_compiles.append(plan)
        return _input("overflow-full")

    try:
        enforce_total_cognitive_budget(
            config=config,
            policy=policy,
            compile_protected_cognitive_input=lambda: _input("protected-overflow"),
            compile_cognitive_input=compile_overflow_full,
            token_counter=overflow_counter,
        )
    except CognitiveBudgetExceeded as error:
        overflow_failure = error

    fit_counter = _SequenceCounter([50, 70])
    fit_full_compiles: list[BudgetPlan] = []

    def compile_fit_full(plan: BudgetPlan) -> CognitiveInput:
        fit_full_compiles.append(plan)
        return _input("full-fit")

    fit_result = enforce_total_cognitive_budget(
        config=config,
        policy=policy,
        compile_protected_cognitive_input=lambda: _input("protected-fit"),
        compile_cognitive_input=compile_fit_full,
        token_counter=fit_counter,
    )

    direct_counter = _SequenceCounter([80])
    direct_count = enforce_protected_serialized_input_floor(
        config=config,
        protected_cognitive_input=_input("protected-direct"),
        token_counter=direct_counter,
    )

    invalid_projection_rejected = False
    try:
        enforce_protected_serialized_input_floor(
            config=config,
            protected_cognitive_input="bad",  # type: ignore[arg-type]
            token_counter=_SequenceCounter([1]),
        )
    except TypeError:
        invalid_projection_rejected = True

    class _BadCounter:
        def count_serialized_input(self, _: CognitiveInput) -> int:
            return 1

    invalid_counter_rejected = False
    try:
        enforce_protected_serialized_input_floor(
            config=config,
            protected_cognitive_input=_input("protected-bad-counter"),
            token_counter=_BadCounter(),  # type: ignore[arg-type]
        )
    except TypeError:
        invalid_counter_rejected = True

    invalid_compiler_rejected = False
    try:
        enforce_total_cognitive_budget(
            config=config,
            policy=policy,
            compile_protected_cognitive_input=lambda: "bad",  # type: ignore[arg-type,return-value]
            compile_cognitive_input=lambda _: _input("unused-full"),
            token_counter=_SequenceCounter([1]),
        )
    except TypeError:
        invalid_compiler_rejected = True

    invalid_rejections = (
        invalid_projection_rejected,
        invalid_counter_rejected,
        invalid_compiler_rejected,
    )

    checks = (
        EvaluationCheck(
            check_id="protected_overflow_stops_before_full_plan_compilation",
            boundary="cognitive_budget",
            passed=(
                overflow_failure is not None
                and overflow_full_compiles == []
                and len(overflow_counter.inputs) == 1
                and overflow_counter.inputs[0].input.payload["content"]
                == "protected-overflow"
            ),
            expected=0,
            observed=len(overflow_full_compiles),
        ),
        EvaluationCheck(
            check_id="protected_fit_precedes_full_serialized_enforcement",
            boundary="cognitive_budget",
            passed=(
                len(fit_counter.inputs) == 2
                and fit_counter.inputs[0].input.payload["content"] == "protected-fit"
                and fit_counter.inputs[1].input.payload["content"] == "full-fit"
                and fit_full_compiles == [policy.initial_plan]
                and fit_result.outcome is BudgetEnforcementOutcome.FIT
                and fit_result.count.total_input_tokens == 70
            ),
            expected="protected-fit,full-fit",
            observed=",".join(
                str(item.input.payload["content"]) for item in fit_counter.inputs
            ),
        ),
        EvaluationCheck(
            check_id="direct_guard_returns_authoritative_count",
            boundary="cognitive_budget",
            passed=(
                direct_count.total_input_tokens == 80
                and direct_count.mode is TokenCountMode.EXACT
                and len(direct_counter.inputs) == 1
            ),
            expected=80,
            observed=direct_count.total_input_tokens,
        ),
        EvaluationCheck(
            check_id="protected_failure_metadata_is_content_free",
            boundary="cognitive_budget",
            passed=(
                overflow_failure is not None
                and overflow_failure.reason
                is BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT
                and overflow_failure.final_plan is None
                and overflow_failure.final_count.total_input_tokens == 81
                and overflow_failure.degradation_step_count == 0
                and "overflow_tokens=1" in str(overflow_failure)
                and not hasattr(overflow_failure, "cognitive_input")
            ),
            expected="protected_floor_exceeds_context",
            observed=(
                overflow_failure.reason.value
                if overflow_failure is not None
                else "missing_failure"
            ),
        ),
        EvaluationCheck(
            check_id="invalid_protected_projection_and_counter_results_are_rejected",
            boundary="cognitive_budget",
            passed=all(invalid_rejections),
            expected=3,
            observed=sum(invalid_rejections),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="protected_serialized_floor",
        checks=checks,
        metrics={
            "direct_guard_call_count": 3,
            "total_enforcement_call_count": 3,
            "protected_overflow_count": int(overflow_failure is not None),
            "full_compile_after_protected_overflow_count": len(
                overflow_full_compiles
            ),
            "invalid_input_rejection_count": sum(invalid_rejections),
        },
    )
