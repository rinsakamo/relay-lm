from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    ActualModelRunManifest,
    ExplicitContinuityRuntimeConfiguration,
)
from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionError,
    plan_actual_model_scenario_execution,
    run_actual_model_scenario_definition,
)
from relaylm.actual_model_restart import ActualModelRestartEvidence
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
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(response=f"response-{self.calls}")


def _manifest(
    *,
    scenario_set_version: str = "actual-model-foundation-v1",
    character_fixture_id: str = "actual-model-foundation-v1",
    provider_capabilities: tuple[str, ...] = ("state_candidates",),
    continuity_runtime: ExplicitContinuityRuntimeConfiguration | None = None,
    execution_path: str = "buffered",
) -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="4b4f9dd39db072a75e328044fbf6eb762584a5b1",
        character_fixture_id=character_fixture_id,
        character_fixture_revision=character_fixture_revision(_FIXTURE_ROOT),
        provider_identity="test-provider",
        adapter_identity="test-provider:v1",
        model_artifact="test/model@sha256:111",
        tokenizer_identity="test/tokenizer@sha256:222",
        effective_context_window=8192,
        decoding_configuration=(("temperature", 0.0),),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version=scenario_set_version,
        condition_id="baseline",
        continuity_runtime=continuity_runtime,
        execution_path=execution_path,  # type: ignore[arg-type]
        provider_capabilities=provider_capabilities,
    )


def test_plan_binds_loaded_scenario_set_fixture_and_manifest_identity() -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    manifest = _manifest()

    plan = plan_actual_model_scenario_execution(
        scenario_set=scenario_set,
        scenario_id="response-persona-correction-v1",
        fixture_root=_FIXTURE_ROOT,
        manifest=manifest,
    )

    assert plan.plan_id.startswith("amp-")
    assert plan.scenario_set_version == scenario_set.scenario_set_version
    assert plan.scenario_set_revision == scenario_set.revision
    assert plan.character_fixture_revision == manifest.character_fixture_revision
    assert plan.definition.scenario.scenario_id == "response-persona-correction-v1"
    assert plan.to_mapping()["scenario_definition"] == plan.definition.to_mapping()


def test_state_only_definition_executes_real_fixture_path_without_rewriting_scenario(
    tmp_path: Path,
) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    provider = _Provider()
    result = asyncio.run(
        run_actual_model_scenario_definition(
            scenario_set=scenario_set,
            scenario_id="response-persona-correction-v1",
            fixture_root=_FIXTURE_ROOT,
            workspace_root=tmp_path / "run",
            provider=provider,
            manifest=_manifest(),
        )
    )

    assert provider.calls == 3
    assert isinstance(result.evidence, ActualModelEvidence)
    assert result.evidence.scenario == scenario_set.scenario(
        "response-persona-correction-v1"
    ).scenario
    assert result.execution_id.startswith("amx-")
    assert result.run_id == result.evidence.run_id
    assert result.to_mapping()["score"] is None


def test_missing_required_capability_fails_before_workspace_or_generation(
    tmp_path: Path,
) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    provider = _Provider()
    workspace = tmp_path / "run"

    with pytest.raises(
        ActualModelScenarioExecutionError,
        match="missing scenario-required provider capabilities: continuity_candidates",
    ):
        asyncio.run(
            run_actual_model_scenario_definition(
                scenario_set=scenario_set,
                scenario_id="continuity-lifecycle-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=workspace,
                provider=provider,
                manifest=_manifest(),
            )
        )

    assert provider.calls == 0
    assert not workspace.exists()


def test_continuity_capability_requires_explicit_runtime_identity_before_generation(
    tmp_path: Path,
) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    provider = _Provider()

    with pytest.raises(
        ActualModelScenarioExecutionError,
        match="require explicit Continuity Runtime identity",
    ):
        asyncio.run(
            run_actual_model_scenario_definition(
                scenario_set=scenario_set,
                scenario_id="continuity-lifecycle-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "run",
                provider=provider,
                manifest=_manifest(
                    provider_capabilities=(
                        "state_candidates",
                        "continuity_candidates",
                    )
                ),
            )
        )
    assert provider.calls == 0


def test_restart_definition_routes_through_restart_evidence_with_fixture_owned_split(
    tmp_path: Path,
) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    provider = _Provider()
    manifest = _manifest(
        provider_capabilities=("state_candidates", "continuity_candidates"),
        continuity_runtime=ExplicitContinuityRuntimeConfiguration(
            max_items=4,
            lifetime_revisions=3,
        ),
    )

    result = asyncio.run(
        run_actual_model_scenario_definition(
            scenario_set=scenario_set,
            scenario_id="restart-durable-vs-temporary-v1",
            fixture_root=_FIXTURE_ROOT,
            workspace_root=tmp_path / "restart-run",
            provider=provider,
            manifest=manifest,
        )
    )

    assert provider.calls == 3
    assert isinstance(result.evidence, ActualModelRestartEvidence)
    assert result.evidence.manifest.restart_after_turn_count == 2
    assert result.plan.definition.restart_after_turn_count == 2
    assert result.evidence.boundary.continuity_after_restart == {
        "max_items": 4,
        "revision": 0,
        "items": [],
    }


def test_scenario_set_version_drift_is_rejected_before_generation(tmp_path: Path) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    provider = _Provider()

    with pytest.raises(
        ActualModelScenarioExecutionError,
        match="scenario_set_version does not match",
    ):
        asyncio.run(
            run_actual_model_scenario_definition(
                scenario_set=scenario_set,
                scenario_id="response-persona-correction-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "run",
                provider=provider,
                manifest=_manifest(scenario_set_version="other-scenario-set"),
            )
        )
    assert provider.calls == 0


def test_streaming_identity_requires_declared_and_implemented_streaming(
    tmp_path: Path,
) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    provider = _Provider()

    with pytest.raises(
        ActualModelScenarioExecutionError,
        match="requires provider capability 'streaming'",
    ):
        asyncio.run(
            run_actual_model_scenario_definition(
                scenario_set=scenario_set,
                scenario_id="response-persona-correction-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "run-a",
                provider=provider,
                manifest=_manifest(execution_path="streaming"),
            )
        )

    with pytest.raises(
        ActualModelScenarioExecutionError,
        match="no stream_generate implementation",
    ):
        asyncio.run(
            run_actual_model_scenario_definition(
                scenario_set=scenario_set,
                scenario_id="response-persona-correction-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "run-b",
                provider=provider,
                manifest=_manifest(
                    execution_path="streaming",
                    provider_capabilities=("state_candidates", "streaming"),
                ),
            )
        )
    assert provider.calls == 0
