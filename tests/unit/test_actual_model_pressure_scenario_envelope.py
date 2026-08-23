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
    ActualModelPressureArtifactError,
    _pressure_comparison_identity,
    _stable_pressure_id,
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


def _manifest(*, condition_id: str, pressure: bool) -> ActualModelRunManifest:
    if pressure:
        budgets = ExplicitBudgetConfiguration(
            memory_max_chunks=1,
            memory_max_chars=500,
            event_max_events=1,
            event_max_chars=500,
        )
    else:
        budgets = ExplicitBudgetConfiguration(
            memory_max_chunks=8,
            memory_max_chars=4000,
            event_max_events=8,
            event_max_chars=4000,
        )
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
        provider_capabilities=("state_candidates", "continuity_candidates"),
        replicate_id="0",
    )


def _stable_pressure_id_for(result) -> str:
    return _stable_pressure_id(
        _pressure_comparison_identity(
            format_version=result.format_version,
            scenario_set_version=result.scenario_set_version,
            scenario_set_revision=result.scenario_set_revision,
            definition=result.definition,
            baseline_plan=result.baseline_plan,
            pressure_plan=result.pressure_plan,
            comparison=result.comparison,
        )
    )


@pytest.mark.parametrize(
    ("field", "forged_value"),
    (
        ("scenario_set_version", "forged-scenario-set-v1"),
        ("scenario_set_revision", "forged-scenario-set-revision"),
    ),
)
def test_pressure_writer_rejects_scenario_set_envelope_drift(
    tmp_path: Path,
    field: str,
    forged_value: str,
) -> None:
    result = asyncio.run(
        run_actual_model_scenario_pressure_comparison(
            scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
            scenario_id="cognitive-pressure-shared-semantics-v1",
            fixture_root=_FIXTURE_ROOT,
            workspace_root=tmp_path / "comparison",
            baseline_provider=_Provider("baseline"),
            pressure_provider=_Provider("pressure"),
            baseline_manifest=_manifest(condition_id="baseline", pressure=False),
            pressure_manifest=_manifest(condition_id="pressure", pressure=True),
        )
    )
    forged = replace(result, **{field: forged_value})
    forged = replace(forged, pressure_comparison_id=_stable_pressure_id_for(forged))
    assert forged.pressure_comparison_id != result.pressure_comparison_id
    assert forged.baseline_plan == result.baseline_plan
    assert forged.pressure_plan == result.pressure_plan
    assert forged.comparison == result.comparison
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelPressureArtifactError,
        match="pressure scenario-set envelope does not match embedded plans",
    ):
        write_actual_model_scenario_pressure_comparison(
            comparison=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()
