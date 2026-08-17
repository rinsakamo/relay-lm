from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_evaluation import ActualModelRunManifest
from relaylm.actual_model_execution import run_actual_model_scenario_definition
from relaylm.actual_model_execution_artifacts import (
    ActualModelExecutionArtifactError,
    load_actual_model_execution_mapping,
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


class _ResponseProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(response=self.response)


def _manifest(*, replicate_id: str = "0") -> ActualModelRunManifest:
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
        replicate_id=replicate_id,
    )


async def _run(
    *, workspace_root: Path, response: str, replicate_id: str = "0"
):
    return await run_actual_model_scenario_definition(
        scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
        scenario_id="response-persona-correction-v1",
        fixture_root=_FIXTURE_ROOT,
        workspace_root=workspace_root,
        provider=_ResponseProvider(response),
        manifest=_manifest(replicate_id=replicate_id),
    )


def test_complete_execution_artifact_is_execution_id_addressed_and_loadable(
    tmp_path: Path,
) -> None:
    result = asyncio.run(
        _run(workspace_root=tmp_path / "run", response="grounded response")
    )
    artifact_root = tmp_path / "artifacts"

    path = write_actual_model_execution_result(
        result=result,
        artifact_root=artifact_root,
    )
    loaded = load_actual_model_execution_mapping(path)

    assert path.name == f"{result.execution_id}.json"
    assert loaded["execution_id"] == result.execution_id
    assert loaded["plan"]["scenario_set"]["revision"] == result.plan.scenario_set_revision
    assert loaded["plan"]["scenario_definition"]["id"] == (
        "response-persona-correction-v1"
    )
    assert loaded["evidence"]["run_id"] == result.run_id
    assert loaded["score"] is None


def test_execution_artifact_write_is_idempotent_for_identical_bytes(tmp_path: Path) -> None:
    result = asyncio.run(
        _run(workspace_root=tmp_path / "run", response="same response")
    )
    artifact_root = tmp_path / "artifacts"

    first = write_actual_model_execution_result(
        result=result,
        artifact_root=artifact_root,
    )
    second = write_actual_model_execution_result(
        result=result,
        artifact_root=artifact_root,
    )

    assert second == first
    assert len(tuple(artifact_root.glob("*.json"))) == 1


def test_same_execution_identity_cannot_overwrite_nondeterministic_evidence(
    tmp_path: Path,
) -> None:
    first = asyncio.run(
        _run(workspace_root=tmp_path / "run-a", response="first model response")
    )
    conflicting = asyncio.run(
        _run(workspace_root=tmp_path / "run-b", response="different model response")
    )
    assert conflicting.run_id == first.run_id
    assert conflicting.execution_id == first.execution_id

    artifact_root = tmp_path / "artifacts"
    write_actual_model_execution_result(result=first, artifact_root=artifact_root)
    with pytest.raises(
        ActualModelExecutionArtifactError,
        match="distinct replicate_id",
    ):
        write_actual_model_execution_result(
            result=conflicting,
            artifact_root=artifact_root,
        )


def test_replicate_id_produces_distinct_citable_execution_artifact(tmp_path: Path) -> None:
    first = asyncio.run(
        _run(
            workspace_root=tmp_path / "run-0",
            response="model response",
            replicate_id="0",
        )
    )
    second = asyncio.run(
        _run(
            workspace_root=tmp_path / "run-1",
            response="model response",
            replicate_id="1",
        )
    )

    assert first.run_id != second.run_id
    assert first.execution_id != second.execution_id

    artifact_root = tmp_path / "artifacts"
    first_path = write_actual_model_execution_result(
        result=first,
        artifact_root=artifact_root,
    )
    second_path = write_actual_model_execution_result(
        result=second,
        artifact_root=artifact_root,
    )
    assert first_path != second_path


def test_loader_rejects_non_object_root(tmp_path: Path) -> None:
    path = tmp_path / "not-an-execution.json"
    path.write_text("[]\n", encoding="utf-8")

    with pytest.raises(
        ActualModelExecutionArtifactError,
        match="root must be a JSON object",
    ):
        load_actual_model_execution_mapping(path)
