from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import (
    character_fixture_revision,
    load_actual_model_evidence_mapping,
    write_actual_model_evidence,
)
from relaylm.actual_model_cognitive_budget import ExplicitCognitiveBudgetConfiguration
from relaylm.actual_model_comparison import stable_condition_comparison_id
from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ActualModelScenario,
    ExplicitBudgetConfiguration,
    ExplicitContinuityRuntimeConfiguration,
    run_actual_model_scenario,
)
from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionError,
    plan_actual_model_scenario_execution,
    run_actual_model_scenario_definition,
)
from relaylm.actual_model_quality import QUALITY_RUBRIC_VERSION
from relaylm.actual_model_scenarios import (
    ActualModelScenarioDefinition,
    ActualModelScenarioSet,
)
from relaylm.budget import (
    BudgetDegradationPolicy,
    BudgetDegradationStep,
    BudgetLayer,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
    TotalBudgetConfig,
)
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory


class _SequenceCounter:
    def __init__(self, counts: list[SerializedInputTokenCount]) -> None:
        self.counts = counts
        self.calls = 0

    def count_serialized_input(self, _: CognitiveInput) -> SerializedInputTokenCount:
        if self.calls >= len(self.counts):
            raise AssertionError("unexpected serialized-input count")
        result = self.counts[self.calls]
        self.calls += 1
        return result


class _Provider:
    def __init__(self) -> None:
        self.buffered_calls = 0
        self.streaming_calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.buffered_calls += 1
        return CognitiveOutput(response="ok")

    async def stream_generate(self, _: CognitiveInput, emit) -> CognitiveOutput:
        self.streaming_calls += 1
        await emit("ok")
        return CognitiveOutput(response="ok")

    @property
    def calls(self) -> int:
        return self.buffered_calls + self.streaming_calls


def _count(
    total: int,
    *,
    mode: TokenCountMode = TokenCountMode.EXACT,
) -> SerializedInputTokenCount:
    return SerializedInputTokenCount(
        total_input_tokens=total,
        required_input_framing_tokens=5,
        mode=mode,
    )


def _plan(*, memory_chars: int = 100) -> BudgetPlan:
    zero_chars = CountCharacterEnvelope(
        max_items=0,
        floor_items=0,
        max_chars=0,
        floor_chars=0,
    )
    return BudgetPlan(
        canonical_state=CountEnvelope(max_items=0, floor_items=0),
        working_context=zero_chars,
        retrieved_memory=CountCharacterEnvelope(
            max_items=1,
            floor_items=0,
            max_chars=memory_chars,
            floor_chars=0,
        ),
        event_evidence=zero_chars,
    )


def _policy(*, degradable: bool = False, memory_chars: int = 100) -> BudgetDegradationPolicy:
    steps: tuple[BudgetDegradationStep, ...] = ()
    if degradable:
        steps = (
            BudgetDegradationStep(
                layer=BudgetLayer.RETRIEVED_MEMORY,
                target=CountCharacterEnvelope(
                    max_items=0,
                    floor_items=0,
                    max_chars=0,
                    floor_chars=0,
                ),
            ),
        )
    return BudgetDegradationPolicy(
        initial_plan=_plan(memory_chars=memory_chars),
        steps=steps,
    )


def _runtime(
    counts: list[SerializedInputTokenCount],
    *,
    policy: BudgetDegradationPolicy | None = None,
) -> tuple[CognitiveBudgetRuntimeConfig, _SequenceCounter]:
    counter = _SequenceCounter(counts)
    return (
        CognitiveBudgetRuntimeConfig(
            total=TotalBudgetConfig(
                model_context_window=100,
                reserved_output_tokens=10,
            ),
            policy=policy or _policy(),
            token_counter=counter,
        ),
        counter,
    )


def _manifest(
    *,
    runtime: CognitiveBudgetRuntimeConfig | None = None,
    condition_id: str = "baseline",
    execution_path: str = "buffered",
    continuity_runtime: ExplicitContinuityRuntimeConfiguration | None = None,
) -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="a" * 40,
        character_fixture_id="budget-fixture",
        character_fixture_revision="sha256:fixture",
        provider_identity="provider-instance",
        adapter_identity="openai_compatible",
        model_artifact="org/model@sha256:111",
        tokenizer_identity="tokenizer@sha256:222",
        effective_context_window=100,
        decoding_configuration=(),
        structured_output_schema_version="relaylm_cognitive_output",
        scenario_set_version="budget-set-v1",
        condition_id=condition_id,
        cognitive_budget=(
            ExplicitCognitiveBudgetConfiguration.from_runtime(runtime)
            if runtime is not None
            else None
        ),
        continuity_runtime=continuity_runtime,
        execution_path=execution_path,  # type: ignore[arg-type]
        provider_capabilities=(
            ("state_candidates", "streaming")
            if execution_path == "streaming"
            else ("state_candidates",)
        ),
    )


def _scenario(*, family: str = "cognitive_pressure_robustness") -> ActualModelScenario:
    return ActualModelScenario(
        scenario_id="budget-evidence",
        family=family,  # type: ignore[arg-type]
        turns=("budgeted turn",),
        version="1",
    )


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# Budget Fixture\n\nStay grounded.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: budget-fixture\n  name: Budget Fixture\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _scenario_set(scenario: ActualModelScenario) -> ActualModelScenarioSet:
    return ActualModelScenarioSet(
        scenario_set_version="budget-set-v1",
        quality_rubric_version=QUALITY_RUBRIC_VERSION,
        character_fixture_id="budget-fixture",
        scenarios=(
            ActualModelScenarioDefinition(
                scenario=scenario,
                proposal_labels=(),
                required_provider_capabilities=(),
                restart_after_turn_count=(1 if scenario.family == "restart_quality" else None),
            ),
        ),
    )


def test_manifest_carries_total_policy_identity_and_rejects_legacy_overlap() -> None:
    runtime, _ = _runtime([_count(20), _count(40)], policy=_policy(degradable=True))
    manifest = _manifest(runtime=runtime)
    mapping = manifest.to_mapping()["cognitive_budget"]

    assert mapping["model_context_window"] == 100
    assert mapping["reserved_output_tokens"] == 10
    assert mapping["initial_plan"]["retrieved_memory"]["floor_chars"] == 0
    assert mapping["degradation_steps"][0]["layer"] == "retrieved_memory"
    assert mapping["degradation_steps"][0]["tier"] == 3

    with pytest.raises(ValueError, match="cannot be combined"):
        replace(
            manifest,
            budgets=ExplicitBudgetConfiguration(
                memory_max_chunks=1,
                memory_max_chars=100,
            ),
        )
    with pytest.raises(ValueError, match="must match effective_context_window"):
        replace(manifest, effective_context_window=99)


def test_buffered_and_streaming_success_preserve_runtime_count_mode(tmp_path: Path) -> None:
    buffered_runtime, buffered_counter = _runtime([_count(20), _count(40)])
    buffered_provider = _Provider()
    buffered = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(tmp_path / "buffered"),
            provider=buffered_provider,
            manifest=_manifest(runtime=buffered_runtime),
            scenario=_scenario(),
            cognitive_budget=buffered_runtime,
        )
    )
    assert buffered_provider.buffered_calls == 1
    assert buffered_counter.calls == 2
    buffered_diag = buffered.turns[0].cognitive_budget
    assert buffered_diag is not None
    assert buffered_diag.outcome == "fit"
    assert buffered_diag.count_mode == "exact"
    assert buffered_diag.final_input_tokens == 40
    assert buffered_diag.final_cognitive_input_tokens == 35

    streaming_runtime, streaming_counter = _runtime(
        [
            _count(20, mode=TokenCountMode.CONSERVATIVE_ESTIMATE),
            _count(45, mode=TokenCountMode.CONSERVATIVE_ESTIMATE),
        ]
    )
    streaming_provider = _Provider()
    streaming = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(tmp_path / "streaming"),
            provider=streaming_provider,
            manifest=_manifest(runtime=streaming_runtime, execution_path="streaming"),
            scenario=_scenario(),
            cognitive_budget=streaming_runtime,
        )
    )
    assert streaming_provider.streaming_calls == 1
    assert streaming_counter.calls == 2
    streaming_diag = streaming.turns[0].cognitive_budget
    assert streaming_diag is not None
    assert streaming_diag.count_mode == "conservative_estimate"
    assert streaming_diag.final_input_tokens == 45


def test_degraded_fit_preserves_tier_reduction_observation(tmp_path: Path) -> None:
    runtime, counter = _runtime(
        [_count(20), _count(95), _count(80)],
        policy=_policy(degradable=True),
    )
    provider = _Provider()
    evidence = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(tmp_path),
            provider=provider,
            manifest=_manifest(runtime=runtime),
            scenario=_scenario(),
            cognitive_budget=runtime,
        )
    )

    assert provider.calls == 1
    assert counter.calls == 3
    diagnostics = evidence.turns[0].cognitive_budget
    assert diagnostics is not None
    assert diagnostics.outcome == "degraded_fit"
    assert diagnostics.pressure_occurred is True
    assert diagnostics.degradation_step_count == 1
    assert [item.to_mapping() for item in diagnostics.tier_reductions] == [
        {"tier": 3, "reduction_step_count": 1, "reduced_layer_count": 1}
    ]
    assert diagnostics.final_input_tokens == 80


@pytest.mark.parametrize(
    ("counts", "policy", "reason", "steps"),
    [
        ([_count(95)], _policy(), "protected_floor_exceeds_context", 0),
        (
            [_count(20), _count(95), _count(92)],
            _policy(degradable=True),
            "degradation_exhausted",
            1,
        ),
    ],
)
def test_bounded_failure_is_citable_without_fake_model_output(
    tmp_path: Path,
    counts: list[SerializedInputTokenCount],
    policy: BudgetDegradationPolicy,
    reason: str,
    steps: int,
) -> None:
    runtime, counter = _runtime(counts, policy=policy)
    provider = _Provider()
    evidence = asyncio.run(
        run_actual_model_scenario(
            character=_make_character(tmp_path / "character"),
            provider=provider,
            manifest=_manifest(runtime=runtime),
            scenario=_scenario(),
            cognitive_budget=runtime,
        )
    )

    assert provider.calls == 0
    assert counter.calls == len(counts)
    assert evidence.turns == ()
    assert evidence.bounded_failure is not None
    diagnostics = evidence.bounded_failure.cognitive_budget
    assert diagnostics.outcome == "bounded_failure"
    assert diagnostics.failure_reason == reason
    assert diagnostics.degradation_step_count == steps
    assert evidence.bounded_failure.to_mapping()["provider_generation_occurred"] is False

    path = write_actual_model_evidence(
        evidence=evidence,
        artifact_root=tmp_path / "evidence",
    )
    loaded = load_actual_model_evidence_mapping(path)
    assert loaded["bounded_failure"]["cognitive_budget"]["failure_reason"] == reason


def test_runtime_identity_mismatch_fails_before_provider_generation(tmp_path: Path) -> None:
    declared, _ = _runtime([_count(20), _count(40)], policy=_policy(memory_chars=100))
    supplied, _ = _runtime([_count(20), _count(40)], policy=_policy(memory_chars=80))
    provider = _Provider()

    with pytest.raises(ValueError, match="does not match the run manifest"):
        asyncio.run(
            run_actual_model_scenario(
                character=_make_character(tmp_path),
                provider=provider,
                manifest=_manifest(runtime=declared),
                scenario=_scenario(),
                cognitive_budget=supplied,
            )
        )
    assert provider.calls == 0


def test_condition_identity_supports_total_budget_delta_and_rejects_mixed_mode() -> None:
    baseline_runtime, _ = _runtime([_count(20), _count(40)], policy=_policy(memory_chars=100))
    pressure_runtime, _ = _runtime([_count(20), _count(40)], policy=_policy(memory_chars=40))
    baseline = _manifest(runtime=baseline_runtime, condition_id="baseline")
    pressure = _manifest(runtime=pressure_runtime, condition_id="pressure")

    assert stable_condition_comparison_id(
        baseline_manifest=baseline,
        pressure_manifest=pressure,
        scenario=_scenario(),
    ).startswith("amc-")

    with pytest.raises(ValueError, match="same budget-control mode"):
        stable_condition_comparison_id(
            baseline_manifest=baseline,
            pressure_manifest=replace(
                pressure,
                cognitive_budget=None,
                budgets=ExplicitBudgetConfiguration(
                    memory_max_chunks=1,
                    memory_max_chars=40,
                ),
            ),
            scenario=_scenario(),
        )


def test_canonical_execution_passes_budget_runtime_and_rejects_missing_before_workspace(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture"
    _make_character(fixture)
    runtime, counter = _runtime([_count(20), _count(40)])
    scenario = _scenario()
    scenario_set = _scenario_set(scenario)
    manifest = replace(
        _manifest(runtime=runtime),
        character_fixture_revision=character_fixture_revision(fixture),
    )
    provider = _Provider()

    result = asyncio.run(
        run_actual_model_scenario_definition(
            scenario_set=scenario_set,
            scenario_id=scenario.scenario_id,
            fixture_root=fixture,
            workspace_root=tmp_path / "workspace",
            provider=provider,
            manifest=manifest,
            cognitive_budget=runtime,
        )
    )
    assert provider.calls == 1
    assert counter.calls == 2
    assert result.evidence.turns[0].cognitive_budget is not None

    missing_workspace = tmp_path / "missing-runtime"
    with pytest.raises(ValueError, match="requires supplied CognitiveBudgetRuntimeConfig"):
        asyncio.run(
            run_actual_model_scenario_definition(
                scenario_set=scenario_set,
                scenario_id=scenario.scenario_id,
                fixture_root=fixture,
                workspace_root=missing_workspace,
                provider=_Provider(),
                manifest=manifest,
            )
        )
    assert not missing_workspace.exists()


def test_restart_preflight_rejects_total_budget_bridge(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    _make_character(fixture)
    runtime, _ = _runtime([_count(20), _count(40)])
    scenario = ActualModelScenario(
        scenario_id="restart-budget",
        family="restart_quality",
        turns=("before", "after"),
        version="1",
    )
    manifest = replace(
        _manifest(
            runtime=runtime,
            continuity_runtime=ExplicitContinuityRuntimeConfiguration(
                max_items=2,
                lifetime_revisions=2,
            ),
        ),
        character_fixture_revision=character_fixture_revision(fixture),
    )

    with pytest.raises(
        ActualModelScenarioExecutionError,
        match="do not support total cognitive-budget evidence",
    ):
        plan_actual_model_scenario_execution(
            scenario_set=_scenario_set(scenario),
            scenario_id=scenario.scenario_id,
            fixture_root=fixture,
            manifest=manifest,
        )
