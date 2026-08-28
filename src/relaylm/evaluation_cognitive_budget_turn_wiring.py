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
from relaylm.budget_enforcement import (
    BudgetEnforcementFailureReason,
    CognitiveBudgetExceeded,
    SerializedInputTokenCount,
    TokenCountMode,
)
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
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


async def evaluate_cognitive_budget_turn_wiring() -> EvaluationScenarioResult:
    expected_state = _state()

    with TemporaryDirectory(prefix="relaylm-eval-budget-turn-fit-") as temp:
        root = Path(temp)
        character = _make_character(root, state=expected_state)
        provider = _RecordingProvider()
        counter = _SequenceCounter([50, 70])
        result = await run_user_turn(
            character=character,
            provider=provider,
            content="hello",
            cognitive_budget=_runtime(counter),
        )
        buffered_fit_ok = (
            result.response == "ok"
            and provider.generate_calls == 1
            and provider.stream_calls == 0
            and len(provider.inputs) == 1
            and provider.inputs[0].state == ()
            and provider.inputs[0].context == ()
            and provider.inputs[0].memory == ()
            and provider.inputs[0].event_evidence == ()
            and len(counter.inputs) == 2
            and result.state == expected_state
            and CharacterDirectory(root).load_state() == expected_state
            and [event.actor for event in CharacterDirectory(root).iter_events()]
            == ["user", "assistant"]
        )
        buffered_fit_provider_calls = provider.generate_calls + provider.stream_calls

    with TemporaryDirectory(prefix="relaylm-eval-budget-turn-pressure-") as temp:
        root = Path(temp)
        character = _make_character(root, state=expected_state)
        provider = _RecordingProvider()
        counter = _SequenceCounter([50, 90, 70])
        await run_user_turn(
            character=character,
            provider=provider,
            content="tea please",
            cognitive_budget=_runtime(counter, policy=_state_degradation_policy()),
        )
        pressure_ok = (
            len(counter.inputs) == 3
            and counter.inputs[1].state == expected_state.states
            and counter.inputs[2].state == ()
            and provider.generate_calls == 1
            and provider.stream_calls == 0
            and len(provider.inputs) == 1
            and provider.inputs[0].state == ()
            and CharacterDirectory(root).load_state() == expected_state
        )
        pressure_provider_calls = provider.generate_calls + provider.stream_calls

    with TemporaryDirectory(prefix="relaylm-eval-budget-turn-protected-fail-") as temp:
        root = Path(temp)
        character = _make_character(root, state=expected_state)
        provider = _RecordingProvider()
        counter = _SequenceCounter([81])
        protected_failure: CognitiveBudgetExceeded | None = None
        try:
            await run_user_turn(
                character=character,
                provider=provider,
                content="hello",
                cognitive_budget=_runtime(counter),
            )
        except CognitiveBudgetExceeded as error:
            protected_failure = error
        protected_fail_ok = (
            protected_failure is not None
            and protected_failure.reason
            is BudgetEnforcementFailureReason.PROTECTED_FLOOR_EXCEEDS_CONTEXT
            and provider.generate_calls == 0
            and provider.stream_calls == 0
            and len(counter.inputs) == 1
            and [event.actor for event in CharacterDirectory(root).iter_events()] == ["user"]
            and CharacterDirectory(root).load_state() == expected_state
        )
        protected_fail_provider_calls = provider.generate_calls + provider.stream_calls

    with TemporaryDirectory(prefix="relaylm-eval-budget-turn-exhausted-") as temp:
        root = Path(temp)
        character = _make_character(root, state=expected_state)
        provider = _RecordingProvider()
        counter = _SequenceCounter([50, 90, 85])
        exhausted_failure: CognitiveBudgetExceeded | None = None
        try:
            await run_user_turn(
                character=character,
                provider=provider,
                content="hello",
                cognitive_budget=_runtime(counter, policy=_state_degradation_policy()),
            )
        except CognitiveBudgetExceeded as error:
            exhausted_failure = error
        exhausted_ok = (
            exhausted_failure is not None
            and exhausted_failure.reason
            is BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED
            and provider.generate_calls == 0
            and provider.stream_calls == 0
            and len(counter.inputs) == 3
            and [event.actor for event in CharacterDirectory(root).iter_events()] == ["user"]
            and CharacterDirectory(root).load_state() == expected_state
        )
        exhausted_provider_calls = provider.generate_calls + provider.stream_calls

    with TemporaryDirectory(prefix="relaylm-eval-budget-turn-overlap-") as temp:
        root = Path(temp)
        character = _make_character(root)
        provider = _RecordingProvider()
        overlap_rejected = False
        try:
            await run_user_turn(
                character=character,
                provider=provider,
                content="hello",
                memory_budget=MemoryRetrievalBudget(max_chunks=0, max_chars=0),
                cognitive_budget=_runtime(_SequenceCounter([50, 70])),
            )
        except ValueError as error:
            overlap_rejected = "cannot be combined" in str(error)
        overlap_ok = (
            overlap_rejected
            and provider.generate_calls == 0
            and provider.stream_calls == 0
            and tuple(CharacterDirectory(root).iter_events()) == ()
        )
        overlap_provider_calls = provider.generate_calls + provider.stream_calls

    with TemporaryDirectory(prefix="relaylm-eval-budget-turn-stream-") as temp:
        root = Path(temp)
        character = _make_character(root)
        provider = _RecordingProvider()
        counter = _SequenceCounter([50, 70])
        deltas: list[str] = []

        async def emit(delta: str) -> None:
            deltas.append(delta)

        stream_result = await run_user_turn_streaming(
            character=character,
            provider=provider,
            content="hello",
            emit_response_delta=emit,
            cognitive_budget=_runtime(counter),
        )
        streaming_ok = (
            stream_result.response == "ok"
            and provider.generate_calls == 0
            and provider.stream_calls == 1
            and len(provider.inputs) == 1
            and len(counter.inputs) == 2
            and deltas == ["ok"]
            and [event.actor for event in CharacterDirectory(root).iter_events()]
            == ["user", "assistant"]
        )
        streaming_provider_calls = provider.generate_calls + provider.stream_calls

    checks = (
        EvaluationCheck(
            check_id="buffered_generation_occurs_once_after_fit",
            boundary="turn_runtime",
            passed=buffered_fit_ok,
            expected=1,
            observed=buffered_fit_provider_calls,
        ),
        EvaluationCheck(
            check_id="budget_pressure_recompiles_before_single_generation",
            boundary="turn_runtime",
            passed=pressure_ok,
            expected=1,
            observed=pressure_provider_calls,
        ),
        EvaluationCheck(
            check_id="protected_floor_failure_precedes_generation",
            boundary="turn_runtime",
            passed=protected_fail_ok,
            expected=0,
            observed=protected_fail_provider_calls,
        ),
        EvaluationCheck(
            check_id="degradation_exhaustion_precedes_generation",
            boundary="turn_runtime",
            passed=exhausted_ok,
            expected=0,
            observed=exhausted_provider_calls,
        ),
        EvaluationCheck(
            check_id="legacy_retrieval_budget_is_rejected_before_event_append",
            boundary="turn_runtime",
            passed=overlap_ok,
            expected=0,
            observed=overlap_provider_calls,
        ),
        EvaluationCheck(
            check_id="streaming_generation_occurs_once_after_fit",
            boundary="turn_runtime",
            passed=streaming_ok,
            expected=1,
            observed=streaming_provider_calls,
        ),
    )
    provider_generation_count = sum(
        (
            buffered_fit_provider_calls,
            pressure_provider_calls,
            protected_fail_provider_calls,
            exhausted_provider_calls,
            overlap_provider_calls,
            streaming_provider_calls,
        )
    )
    return EvaluationScenarioResult(
        scenario_id="cognitive_budget_turn_wiring",
        checks=checks,
        metrics={
            "ordinary_turn_call_count": 6,
            "buffered_turn_call_count": 5,
            "streaming_turn_call_count": 1,
            "provider_generation_count": provider_generation_count,
            "budget_failure_before_generation_count": sum(
                (protected_fail_ok, exhausted_ok)
            ),
            "pre_event_configuration_rejection_count": int(overlap_ok),
        },
    )
