from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

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
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
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


async def evaluate_cognitive_budget_turn_diagnostics() -> EvaluationScenarioResult:
    with TemporaryDirectory(prefix="relaylm-eval-budget-diag-fit-") as temp:
        provider = _Provider()
        counter = _SequenceCounter([50, 70])
        result = await run_user_turn_with_cognitive_budget_diagnostics(
            character=_make_character(Path(temp)),
            provider=provider,
            content="hello",
            cognitive_budget=_runtime(counter),
        )
        diagnostics = result.cognitive_budget
        buffered_fit_ok = (
            result.turn.response == "ok"
            and provider.generate_calls == 1
            and provider.stream_calls == 0
            and len(counter.inputs) == 2
            and diagnostics.outcome is CognitiveBudgetDiagnosticOutcome.FIT
            and diagnostics.model_context_window == 100
            and diagnostics.effective_context_capacity == 80
            and diagnostics.reserved_output_tokens == 20
            and diagnostics.required_input_framing_tokens == 10
            and diagnostics.final_input_tokens == 70
            and diagnostics.available_cognitive_capacity == 70
            and not diagnostics.pressure_occurred
            and diagnostics.degradation_step_count == 0
            and diagnostics.count_mode is TokenCountMode.EXACT
        )
        buffered_fit_provider_calls = provider.generate_calls + provider.stream_calls

    with TemporaryDirectory(prefix="relaylm-eval-budget-diag-pressure-") as temp:
        provider = _Provider()
        counter = _SequenceCounter([50, 90, 70])
        result = await run_user_turn_with_cognitive_budget_diagnostics(
            character=_make_character(Path(temp)),
            provider=provider,
            content="hello",
            cognitive_budget=_runtime(counter, policy=_one_state_step_policy()),
        )
        diagnostics = result.cognitive_budget
        degraded_fit_ok = (
            provider.generate_calls == 1
            and provider.stream_calls == 0
            and len(counter.inputs) == 3
            and diagnostics.outcome
            is CognitiveBudgetDiagnosticOutcome.DEGRADED_FIT
            and diagnostics.pressure_occurred
            and diagnostics.degradation_step_count == 1
            and diagnostics.reduced_layer_count == 1
            and diagnostics.reduced_tier_count == 1
            and len(diagnostics.tier_reductions) == 1
            and diagnostics.tier_reductions[0].tier == 1
        )
        degraded_provider_calls = provider.generate_calls + provider.stream_calls

    with TemporaryDirectory(prefix="relaylm-eval-budget-diag-protected-") as temp:
        provider = _Provider()
        counter = _SequenceCounter([81])
        protected_failure: CognitiveBudgetExceededWithDiagnostics | None = None
        try:
            await run_user_turn_with_cognitive_budget_diagnostics(
                character=_make_character(Path(temp)),
                provider=provider,
                content="secret user content",
                cognitive_budget=_runtime(counter),
            )
        except CognitiveBudgetExceededWithDiagnostics as error:
            protected_failure = error
        protected_failure_ok = (
            protected_failure is not None
            and isinstance(protected_failure, CognitiveBudgetExceeded)
            and provider.generate_calls == 0
            and provider.stream_calls == 0
            and protected_failure.reason
            is BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT
            and protected_failure.diagnostics.outcome
            is CognitiveBudgetDiagnosticOutcome.BOUNDED_FAILURE
            and protected_failure.diagnostics.failure_reason
            is BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT
            and protected_failure.diagnostics.final_input_tokens == 81
            and protected_failure.diagnostics.degradation_step_count == 0
            and "secret user content" not in repr(protected_failure.diagnostics)
            and "secret user content" not in str(protected_failure)
        )
        protected_provider_calls = provider.generate_calls + provider.stream_calls

    with TemporaryDirectory(prefix="relaylm-eval-budget-diag-exhausted-") as temp:
        provider = _Provider()
        counter = _SequenceCounter([50, 90, 85])
        exhausted_failure: CognitiveBudgetExceededWithDiagnostics | None = None
        try:
            await run_user_turn_with_cognitive_budget_diagnostics(
                character=_make_character(Path(temp)),
                provider=provider,
                content="hello",
                cognitive_budget=_runtime(
                    counter,
                    policy=_one_state_step_policy(),
                ),
            )
        except CognitiveBudgetExceededWithDiagnostics as error:
            exhausted_failure = error
        exhaustion_ok = (
            exhausted_failure is not None
            and provider.generate_calls == 0
            and provider.stream_calls == 0
            and exhausted_failure.reason
            is BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED
            and exhausted_failure.diagnostics.failure_reason
            is BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED
            and exhausted_failure.diagnostics.degradation_step_count == 1
            and exhausted_failure.diagnostics.reduced_layer_count == 1
            and exhausted_failure.diagnostics.reduced_tier_count == 1
        )
        exhausted_provider_calls = provider.generate_calls + provider.stream_calls

    with TemporaryDirectory(prefix="relaylm-eval-budget-diag-stream-") as temp:
        provider = _Provider()
        counter = _SequenceCounter([50, 70])
        deltas: list[str] = []

        async def emit(delta: str) -> None:
            deltas.append(delta)

        result = await run_user_turn_streaming_with_cognitive_budget_diagnostics(
            character=_make_character(Path(temp)),
            provider=provider,
            content="hello",
            emit_response_delta=emit,
            cognitive_budget=_runtime(counter),
        )
        streaming_fit_ok = (
            result.cognitive_budget.outcome is CognitiveBudgetDiagnosticOutcome.FIT
            and provider.generate_calls == 0
            and provider.stream_calls == 1
            and len(counter.inputs) == 2
            and deltas == ["ok"]
        )
        streaming_provider_calls = provider.generate_calls + provider.stream_calls

    checks = (
        EvaluationCheck(
            check_id="buffered_fit_returns_content_free_diagnostics_after_one_generation",
            boundary="turn_runtime",
            passed=buffered_fit_ok,
            expected=1,
            observed=buffered_fit_provider_calls,
        ),
        EvaluationCheck(
            check_id="buffered_pressure_returns_degraded_fit_counts",
            boundary="turn_runtime",
            passed=degraded_fit_ok,
            expected=1,
            observed=degraded_provider_calls,
        ),
        EvaluationCheck(
            check_id="protected_failure_preserves_failure_family_and_content_free_diagnostics",
            boundary="turn_runtime",
            passed=protected_failure_ok,
            expected=0,
            observed=protected_provider_calls,
        ),
        EvaluationCheck(
            check_id="degradation_failure_exposes_reduction_counts_before_generation",
            boundary="turn_runtime",
            passed=exhaustion_ok,
            expected=0,
            observed=exhausted_provider_calls,
        ),
        EvaluationCheck(
            check_id="streaming_fit_returns_diagnostics_after_one_stream_generation",
            boundary="turn_runtime",
            passed=streaming_fit_ok,
            expected=1,
            observed=streaming_provider_calls,
        ),
    )
    provider_generation_count = sum(
        (
            buffered_fit_provider_calls,
            degraded_provider_calls,
            protected_provider_calls,
            exhausted_provider_calls,
            streaming_provider_calls,
        )
    )
    return EvaluationScenarioResult(
        scenario_id="cognitive_budget_turn_diagnostics",
        checks=checks,
        metrics={
            "diagnostic_turn_call_count": 5,
            "buffered_diagnostic_turn_call_count": 4,
            "streaming_diagnostic_turn_call_count": 1,
            "provider_generation_count": provider_generation_count,
            "bounded_failure_count": sum(
                (protected_failure is not None, exhausted_failure is not None)
            ),
            "fit_outcome_count": sum((buffered_fit_ok, streaming_fit_ok)),
            "degraded_fit_outcome_count": int(degraded_fit_ok),
        },
    )
