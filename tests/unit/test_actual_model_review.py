from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ExplicitContinuityRuntimeConfiguration,
    ProductQualityObservation,
)
from relaylm.actual_model_execution import run_actual_model_scenario_definition
from relaylm.actual_model_quality import (
    TurnQualityRating,
    required_quality_axes,
)
from relaylm.actual_model_review import (
    load_actual_model_execution_review_mapping,
    review_actual_model_execution,
    write_actual_model_execution_review,
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
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(response=f"response-{self.calls}")


def _manifest(*, restart: bool = False) -> ActualModelRunManifest:
    capabilities = ("state_candidates",)
    continuity = None
    if restart:
        capabilities = ("state_candidates", "continuity_candidates")
        continuity = ExplicitContinuityRuntimeConfiguration(
            max_items=4,
            lifetime_revisions=3,
        )
    return ActualModelRunManifest(
        relaylm_commit="1e0b1aa906b26f42323ab2076b7343cf97393023",
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
        continuity_runtime=continuity,
        provider_capabilities=capabilities,
    )


def _ratings(*, family: str, turn_count: int) -> tuple[TurnQualityRating, ...]:
    axes = required_quality_axes(family)
    return tuple(
        TurnQualityRating(
            turn_index=turn_index,
            observations=tuple(
                ProductQualityObservation(
                    axis=axis,
                    outcome="pass",
                    note=f"turn {turn_index}: {axis}",
                )
                for axis in axes
            ),
        )
        for turn_index in range(1, turn_count + 1)
    )


async def _run(
    *,
    workspace_root: Path,
    scenario_id: str,
    restart: bool = False,
):
    return await run_actual_model_scenario_definition(
        scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
        scenario_id=scenario_id,
        fixture_root=_FIXTURE_ROOT,
        workspace_root=workspace_root,
        provider=_Provider(),
        manifest=_manifest(restart=restart),
    )


def test_review_binds_human_rubric_and_fixture_proposal_metrics_without_mutating_execution(
    tmp_path: Path,
) -> None:
    result = asyncio.run(
        _run(
            workspace_root=tmp_path / "run",
            scenario_id="response-persona-correction-v1",
        )
    )
    before = result.to_json()
    review = review_actual_model_execution(
        result=result,
        reviewer_identity="rater-a",
        ratings=_ratings(
            family="response_persona_continuity",
            turn_count=3,
        ),
    )

    assert result.to_json() == before
    assert review.review_id.startswith("amv-")
    assert review.execution_id == result.execution_id
    assert review.run_id == result.run_id
    assert review.scenario_set_revision == result.plan.scenario_set_revision
    assert tuple(rating.turn_index for rating in review.turn_ratings) == (1, 2, 3)
    assert review.proposal_metrics.state.expected_count == 2
    assert review.proposal_metrics.state.observed_count == 0
    assert review.proposal_metrics.state.false_negative_count == 2
    assert review.proposal_metrics.state.precision is None
    assert review.proposal_metrics.state.recall == 0.0
    assert review.to_mapping()["score"] is None


def test_review_requires_exact_family_rubric_coverage(tmp_path: Path) -> None:
    result = asyncio.run(
        _run(
            workspace_root=tmp_path / "run",
            scenario_id="state-correction-comparison-inference-v1",
        )
    )
    incomplete = _ratings(family="state_candidate_quality", turn_count=3)

    with pytest.raises(ValueError, match="cover every evidence turn exactly once"):
        review_actual_model_execution(
            result=result,
            reviewer_identity="rater-a",
            ratings=incomplete,
        )


def test_restart_review_uses_original_global_turn_indexes_and_fixture_labels(
    tmp_path: Path,
) -> None:
    result = asyncio.run(
        _run(
            workspace_root=tmp_path / "restart-run",
            scenario_id="restart-durable-vs-temporary-v1",
            restart=True,
        )
    )
    review = review_actual_model_execution(
        result=result,
        reviewer_identity="rater-a",
        ratings=_ratings(family="restart_quality", turn_count=3),
    )

    assert tuple(rating.turn_index for rating in review.turn_ratings) == (1, 2, 3)
    assert review.scenario_id == "restart-durable-vs-temporary-v1"
    assert review.proposal_metrics.state.expected_count == 1
    assert review.proposal_metrics.state.false_negative_count == 1
    assert review.proposal_metrics.continuity.expected_count == 1
    assert review.proposal_metrics.continuity.false_negative_count == 1


def test_reviewer_identity_is_part_of_review_identity(tmp_path: Path) -> None:
    result = asyncio.run(
        _run(
            workspace_root=tmp_path / "run",
            scenario_id="response-persona-correction-v1",
        )
    )
    ratings = _ratings(family="response_persona_continuity", turn_count=3)

    first = review_actual_model_execution(
        result=result,
        reviewer_identity="rater-a",
        ratings=ratings,
    )
    second = review_actual_model_execution(
        result=result,
        reviewer_identity="rater-b",
        ratings=ratings,
    )

    assert first.execution_id == second.execution_id
    assert first.review_id != second.review_id


def test_review_sidecar_is_immutable_idempotent_and_machine_loadable(tmp_path: Path) -> None:
    result = asyncio.run(
        _run(
            workspace_root=tmp_path / "run",
            scenario_id="response-persona-correction-v1",
        )
    )
    review = review_actual_model_execution(
        result=result,
        reviewer_identity="rater-a",
        ratings=_ratings(family="response_persona_continuity", turn_count=3),
    )
    artifact_root = tmp_path / "reviews"

    first = write_actual_model_execution_review(
        review=review,
        artifact_root=artifact_root,
    )
    second = write_actual_model_execution_review(
        review=review,
        artifact_root=artifact_root,
    )
    loaded = load_actual_model_execution_review_mapping(first)

    assert first == second
    assert first.name == f"{review.review_id}.review.json"
    assert loaded["review_id"] == review.review_id
    assert loaded["execution_id"] == result.execution_id
    assert loaded["quality_rubric_version"] == "actual-model-quality-v1"
    assert loaded["score"] is None
