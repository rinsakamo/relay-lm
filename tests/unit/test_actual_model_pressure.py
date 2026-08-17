from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ExplicitBudgetConfiguration,
    ExplicitContinuityRuntimeConfiguration,
)
from relaylm.actual_model_pressure import (
    load_actual_model_scenario_pressure_mapping,
    run_actual_model_scenario_pressure_comparison,
    write_actual_model_scenario_pressure_comparison,
)
from relaylm.actual_model_scenarios import load_actual_model_scenario_set
from relaylm.cognitive import CognitiveInput, CognitiveOutput

_REPO_ROOT = Path(__file__).parents[2]
_SCENARIO_SET_PATH = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "scenario_sets"
    / "foundation-v1.json"
)
_FIXTURE_ROOT = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "characters"
    / "foundation-v1"
)


class _Provider:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(response=f"{self.prefix}-{self.calls}")


def _manifest(
    *,
    condition_id: str,
    budgets: ExplicitBudgetConfiguration,
    capabilities: tuple[str, ...] = (
        "state_candidates",
        "continuity_candidates",
    ),
) -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="7f442ad203b74bb0bcac29258a02a425a6cf6e29",
        character_fixture_id="actual-model-foundation-v1",
        character_fixture_revision=character_fixture_revision(_FIXTURE_ROOT),
        provider_identity="test-provider",
        adapter_identity="test-provider:v1",
        model_artifact="test/model@sha256:111",
        tokenizer_identity="test/tokenizer@sha256:222",
        effective_context_window=8192,
        decoding_configuration=(("temperature", 0.0),),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v1",
        condition_id=condition_id,
        budgets=budgets,
        continuity_runtime=ExplicitContinuityRuntimeConfiguration(
            max_items=4,
            lifetime_revisions=3,
        ),
        provider_capabilities=capabilities,
        replicate_id="0",
    )


def _baseline_manifest() -> ActualModelRunManifest:
    return _manifest(
        condition_id="baseline",
        budgets=ExplicitBudgetConfiguration(
            memory_max_chunks=8,
            memory_max_chars=4000,
            event_max_events=8,
            event_max_chars=4000,
        ),
    )


def _pressure_manifest() -> ActualModelRunManifest:
    return _manifest(
        condition_id="pressure",
        budgets=ExplicitBudgetConfiguration(
            memory_max_chunks=1,
            memory_max_chars=500,
            event_max_events=1,
            event_max_chars=500,
        ),
    )


def test_pressure_comparison_binds_full_scenario_definition_and_revision(
    tmp_path: Path,
) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    baseline_provider = _Provider("baseline")
    pressure_provider = _Provider("pressure")

    result = asyncio.run(
        run_actual_model_scenario_pressure_comparison(
            scenario_set=scenario_set,
            scenario_id="cognitive-pressure-shared-semantics-v1",
            fixture_root=_FIXTURE_ROOT,
            workspace_root=tmp_path / "comparison",
            baseline_provider=baseline_provider,
            pressure_provider=pressure_provider,
            baseline_manifest=_baseline_manifest(),
            pressure_manifest=_pressure_manifest(),
        )
    )

    definition = scenario_set.scenario("cognitive-pressure-shared-semantics-v1")
    assert result.pressure_comparison_id.startswith("ampc-")
    assert result.scenario_set_revision == scenario_set.revision
    assert result.definition == definition
    assert result.baseline_plan.definition == definition
    assert result.pressure_plan.definition == definition
    assert result.comparison.scenario == definition.scenario
    assert baseline_provider.calls == 3
    assert pressure_provider.calls == 3
    mapping = result.to_mapping()
    assert mapping["scenario_definition"]["proposal_labels"] == definition.to_mapping()[
        "proposal_labels"
    ]
    assert mapping["comparison"]["score"] is None
    assert mapping["score"] is None


def test_pressure_target_capability_failure_happens_before_any_generation(
    tmp_path: Path,
) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    baseline_provider = _Provider("baseline")
    pressure_provider = _Provider("pressure")
    pressure = _manifest(
        condition_id="pressure",
        budgets=_pressure_manifest().budgets,
        capabilities=("state_candidates",),
    )

    with pytest.raises(
        ValueError,
        match="missing scenario-required provider capabilities: continuity_candidates",
    ):
        asyncio.run(
            run_actual_model_scenario_pressure_comparison(
                scenario_set=scenario_set,
                scenario_id="cognitive-pressure-shared-semantics-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "comparison",
                baseline_provider=baseline_provider,
                pressure_provider=pressure_provider,
                baseline_manifest=_baseline_manifest(),
                pressure_manifest=pressure,
            )
        )

    assert baseline_provider.calls == 0
    assert pressure_provider.calls == 0
    assert not (tmp_path / "comparison").exists()


def test_non_budget_runtime_drift_is_rejected_before_generation(tmp_path: Path) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    baseline_provider = _Provider("baseline")
    pressure_provider = _Provider("pressure")
    pressure = replace(
        _pressure_manifest(),
        continuity_runtime=ExplicitContinuityRuntimeConfiguration(
            max_items=8,
            lifetime_revisions=3,
        ),
    )

    with pytest.raises(
        ValueError,
        match="may differ only by condition_id and explicit budgets",
    ):
        asyncio.run(
            run_actual_model_scenario_pressure_comparison(
                scenario_set=scenario_set,
                scenario_id="cognitive-pressure-shared-semantics-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "comparison",
                baseline_provider=baseline_provider,
                pressure_provider=pressure_provider,
                baseline_manifest=_baseline_manifest(),
                pressure_manifest=pressure,
            )
        )

    assert baseline_provider.calls == 0
    assert pressure_provider.calls == 0
    assert not (tmp_path / "comparison").exists()


def test_pressure_wrapper_rejects_non_pressure_family_before_generation(
    tmp_path: Path,
) -> None:
    baseline_provider = _Provider("baseline")
    pressure_provider = _Provider("pressure")

    with pytest.raises(ValueError, match="cognitive_pressure_robustness"):
        asyncio.run(
            run_actual_model_scenario_pressure_comparison(
                scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
                scenario_id="response-persona-correction-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "comparison",
                baseline_provider=baseline_provider,
                pressure_provider=pressure_provider,
                baseline_manifest=_baseline_manifest(),
                pressure_manifest=_pressure_manifest(),
            )
        )

    assert baseline_provider.calls == 0
    assert pressure_provider.calls == 0


def test_pressure_comparison_artifact_is_citable_idempotent_and_loadable(
    tmp_path: Path,
) -> None:
    result = asyncio.run(
        run_actual_model_scenario_pressure_comparison(
            scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
            scenario_id="cognitive-pressure-shared-semantics-v1",
            fixture_root=_FIXTURE_ROOT,
            workspace_root=tmp_path / "comparison",
            baseline_provider=_Provider("baseline"),
            pressure_provider=_Provider("pressure"),
            baseline_manifest=_baseline_manifest(),
            pressure_manifest=_pressure_manifest(),
        )
    )
    artifact_root = tmp_path / "artifacts"

    first = write_actual_model_scenario_pressure_comparison(
        comparison=result,
        artifact_root=artifact_root,
    )
    second = write_actual_model_scenario_pressure_comparison(
        comparison=result,
        artifact_root=artifact_root,
    )
    loaded = load_actual_model_scenario_pressure_mapping(first)

    assert first == second
    assert first.name == f"{result.pressure_comparison_id}.pressure.json"
    assert loaded["pressure_comparison_id"] == result.pressure_comparison_id
    assert loaded["scenario_set"]["revision"] == result.scenario_set_revision
    assert loaded["scenario_definition"]["id"] == (
        "cognitive-pressure-shared-semantics-v1"
    )
    assert loaded["score"] is None
