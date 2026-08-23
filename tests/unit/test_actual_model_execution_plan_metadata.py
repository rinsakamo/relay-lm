from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_evaluation import ActualModelRunManifest
from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionPlan,
    _stable_execution_id,
    _stable_plan_id,
    run_actual_model_scenario_definition,
)
from relaylm.actual_model_execution_artifacts import (
    ActualModelExecutionArtifactError,
    write_actual_model_execution_result,
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
    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        return CognitiveOutput(response="grounded response")


def _manifest() -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="89a72256182a681a1f46c867d8d9a0071cf88cca",
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
        condition_id="baseline",
        provider_capabilities=("state_candidates",),
        replicate_id="0",
    )


def _stable_plan_id_for(plan: ActualModelScenarioExecutionPlan) -> str:
    return _stable_plan_id(
        scenario_set_version=plan.scenario_set_version,
        scenario_set_revision=plan.scenario_set_revision,
        character_fixture_id=plan.character_fixture_id,
        character_fixture_revision=plan.character_fixture_revision,
        definition=plan.definition,
        manifest=plan.manifest,
    )


@pytest.mark.parametrize(
    ("field", "forged_value"),
    (
        ("scenario_set_version", "forged-scenario-set-v1"),
        ("character_fixture_id", "forged-character"),
        ("character_fixture_revision", "forged-revision"),
    ),
)
def test_execution_writer_rejects_plan_metadata_drift_from_manifest(
    tmp_path: Path,
    field: str,
    forged_value: str,
) -> None:
    result = asyncio.run(
        run_actual_model_scenario_definition(
            scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
            scenario_id="response-persona-correction-v1",
            fixture_root=_FIXTURE_ROOT,
            workspace_root=tmp_path / "run",
            provider=_Provider(),
            manifest=_manifest(),
        )
    )
    forged_plan = replace(result.plan, **{field: forged_value})
    forged_plan = replace(
        forged_plan,
        plan_id=_stable_plan_id_for(forged_plan),
    )
    forged = replace(
        result,
        plan=forged_plan,
        execution_id=_stable_execution_id(
            plan=forged_plan,
            run_id=result.run_id,
        ),
    )
    assert forged.plan.plan_id != result.plan.plan_id
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelExecutionArtifactError,
        match="execution plan metadata does not match run manifest",
    ):
        write_actual_model_execution_result(
            result=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()
