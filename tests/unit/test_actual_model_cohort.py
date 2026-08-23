from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_cohort import (
    ActualModelCohortError,
    ActualModelExecutionTarget,
    load_actual_model_model_cohort_mapping,
    run_actual_model_model_cohort,
    write_actual_model_model_cohort,
)
from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ExplicitBudgetConfiguration,
    ExplicitContinuityRuntimeConfiguration,
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
    model_artifact: str,
    provider_identity: str,
    tokenizer_identity: str,
    effective_context_window: int,
    decoding_temperature: float,
    provider_capabilities: tuple[str, ...] = ("state_candidates",),
    continuity_runtime: ExplicitContinuityRuntimeConfiguration | None = None,
    budgets: ExplicitBudgetConfiguration | None = None,
) -> ActualModelRunManifest:
    return ActualModelRunManifest(
        relaylm_commit="a301b9c327f2bdb23da8c5c99be6b6dffbd141ea",
        character_fixture_id="actual-model-foundation-v1",
        character_fixture_revision=character_fixture_revision(_FIXTURE_ROOT),
        provider_identity=provider_identity,
        adapter_identity=f"{provider_identity}:v1",
        model_artifact=model_artifact,
        tokenizer_identity=tokenizer_identity,
        effective_context_window=effective_context_window,
        decoding_configuration=(("temperature", decoding_temperature),),
        structured_output_schema_version="cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v1",
        condition_id="baseline",
        budgets=budgets or ExplicitBudgetConfiguration(),
        continuity_runtime=continuity_runtime,
        provider_capabilities=provider_capabilities,
        replicate_id="0",
    )


def _targets() -> tuple[ActualModelExecutionTarget, ...]:
    return (
        ActualModelExecutionTarget(
            label="model-a",
            provider=_Provider("a"),
            manifest=_manifest(
                model_artifact="vendor/model-a@sha256:111",
                provider_identity="provider-a",
                tokenizer_identity="tokenizer-a@sha256:aaa",
                effective_context_window=8192,
                decoding_temperature=0.0,
            ),
        ),
        ActualModelExecutionTarget(
            label="model-b",
            provider=_Provider("b"),
            manifest=_manifest(
                model_artifact="vendor/model-b@sha256:222",
                provider_identity="provider-b",
                tokenizer_identity="tokenizer-b@sha256:bbb",
                effective_context_window=16384,
                decoding_temperature=0.2,
            ),
        ),
    )


def test_same_semantic_scenario_executes_against_two_exact_models(tmp_path: Path) -> None:
    scenario_set = load_actual_model_scenario_set(_SCENARIO_SET_PATH)
    targets = _targets()

    cohort = asyncio.run(
        run_actual_model_model_cohort(
            scenario_set=scenario_set,
            scenario_id="response-persona-correction-v1",
            fixture_root=_FIXTURE_ROOT,
            workspace_root=tmp_path / "cohort",
            targets=targets,
        )
    )

    assert cohort.cohort_id.startswith("amm-")
    assert cohort.scenario_set_revision == scenario_set.revision
    assert tuple(member.label for member in cohort.members) == ("model-a", "model-b")
    assert {
        member.execution.plan.definition.scenario for member in cohort.members
    } == {scenario_set.scenario("response-persona-correction-v1").scenario}
    assert tuple(target.provider.calls for target in targets) == (3, 3)
    assert cohort.to_mapping()["ranking"] is None
    assert cohort.to_mapping()["score"] is None


def test_model_specific_identity_can_differ_but_runtime_condition_must_match() -> None:
    targets = _targets()
    assert targets[0].manifest.model_artifact != targets[1].manifest.model_artifact
    assert (
        targets[0].manifest.effective_context_window
        != targets[1].manifest.effective_context_window
    )
    assert (
        targets[0].manifest.decoding_configuration
        != targets[1].manifest.decoding_configuration
    )

    drifted = replace(
        targets[1],
        manifest=replace(
            targets[1].manifest,
            budgets=ExplicitBudgetConfiguration(
                memory_max_chunks=1,
                memory_max_chars=100,
            ),
        ),
    )
    with pytest.raises(ValueError, match="RelayLM/runtime condition must match"):
        asyncio.run(
            run_actual_model_model_cohort(
                scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
                scenario_id="response-persona-correction-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=Path("unused"),
                targets=(targets[0], drifted),
            )
        )


def test_cohort_requires_two_distinct_exact_model_artifacts(tmp_path: Path) -> None:
    targets = _targets()
    same_model = replace(
        targets[1],
        manifest=replace(
            targets[1].manifest,
            model_artifact=targets[0].manifest.model_artifact,
        ),
    )
    with pytest.raises(ValueError, match="distinct exact model_artifacts"):
        asyncio.run(
            run_actual_model_model_cohort(
                scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
                scenario_id="response-persona-correction-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "cohort",
                targets=(targets[0], same_model),
            )
        )


def test_all_targets_preflight_before_any_model_generation(tmp_path: Path) -> None:
    runtime = ExplicitContinuityRuntimeConfiguration(
        max_items=4,
        lifetime_revisions=3,
    )
    first_provider = _Provider("a")
    second_provider = _Provider("b")
    targets = (
        ActualModelExecutionTarget(
            label="model-a",
            provider=first_provider,
            manifest=_manifest(
                model_artifact="vendor/model-a@sha256:111",
                provider_identity="provider-a",
                tokenizer_identity="tokenizer-a",
                effective_context_window=8192,
                decoding_temperature=0.0,
                provider_capabilities=(
                    "state_candidates",
                    "continuity_candidates",
                ),
                continuity_runtime=runtime,
            ),
        ),
        ActualModelExecutionTarget(
            label="model-b",
            provider=second_provider,
            manifest=_manifest(
                model_artifact="vendor/model-b@sha256:222",
                provider_identity="provider-b",
                tokenizer_identity="tokenizer-b",
                effective_context_window=8192,
                decoding_temperature=0.0,
                provider_capabilities=("state_candidates",),
                continuity_runtime=runtime,
            ),
        ),
    )

    with pytest.raises(ValueError, match="missing scenario-required provider capabilities"):
        asyncio.run(
            run_actual_model_model_cohort(
                scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
                scenario_id="continuity-lifecycle-v1",
                fixture_root=_FIXTURE_ROOT,
                workspace_root=tmp_path / "cohort",
                targets=targets,
            )
        )

    assert first_provider.calls == 0
    assert second_provider.calls == 0
    assert not (tmp_path / "cohort").exists()


def test_cohort_artifact_is_citable_and_idempotent(tmp_path: Path) -> None:
    cohort = asyncio.run(
        run_actual_model_model_cohort(
            scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
            scenario_id="response-persona-correction-v1",
            fixture_root=_FIXTURE_ROOT,
            workspace_root=tmp_path / "cohort",
            targets=_targets(),
        )
    )
    artifact_root = tmp_path / "artifacts"

    first = write_actual_model_model_cohort(
        cohort=cohort,
        artifact_root=artifact_root,
    )
    second = write_actual_model_model_cohort(
        cohort=cohort,
        artifact_root=artifact_root,
    )
    loaded = load_actual_model_model_cohort_mapping(first)

    assert first == second
    assert first.name == f"{cohort.cohort_id}.cohort.json"
    assert loaded["cohort_id"] == cohort.cohort_id
    assert loaded["scenario_set"]["revision"] == cohort.scenario_set_revision
    assert len(loaded["members"]) == 2
    assert loaded["ranking"] is None
    assert loaded["score"] is None


def test_cohort_writer_rejects_non_content_derived_cohort_id(tmp_path: Path) -> None:
    cohort = asyncio.run(
        run_actual_model_model_cohort(
            scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
            scenario_id="response-persona-correction-v1",
            fixture_root=_FIXTURE_ROOT,
            workspace_root=tmp_path / "cohort",
            targets=_targets(),
        )
    )
    forged = replace(cohort, cohort_id="amm-not-content-derived")
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelCohortError,
        match="cohort_id does not match cohort evidence",
    ):
        write_actual_model_model_cohort(
            cohort=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()
