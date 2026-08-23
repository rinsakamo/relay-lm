from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ExplicitContinuityRuntimeConfiguration,
    ProductQualityObservation,
)
from relaylm.actual_model_execution import (
    _stable_execution_id,
    run_actual_model_scenario_definition,
)
from relaylm.actual_model_quality import (
    LabeledProposalMetrics,
    ProposalChannelMetrics,
    TurnQualityRating,
    required_quality_axes,
)
from relaylm.actual_model_review import (
    ACTUAL_MODEL_REVIEW_FORMAT_VERSION,
    STAGE_R_REVIEW_PROTOCOL_VERSION,
    ActualModelExecutionReview,
    ActualModelExecutionReviewError,
    CharacterRealizationObservation,
    StageRReviewObservation,
    load_actual_model_execution_review_mapping,
    normalize_stage_r_review_observations,
    required_stage_r_review_dimensions,
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


def _manifest(
    *,
    restart: bool = False,
    replicate_id: str = "0",
) -> ActualModelRunManifest:
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
        replicate_id=replicate_id,
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


def _character_realization(
    turn_count: int,
    *,
    outcome: str = "normal",
) -> tuple[CharacterRealizationObservation, ...]:
    return tuple(
        CharacterRealizationObservation(
            turn_index=turn_index,
            outcome=outcome,
        )
        for turn_index in range(1, turn_count + 1)
    )


async def _run(
    *,
    workspace_root: Path,
    scenario_id: str,
    restart: bool = False,
    replicate_id: str = "0",
):
    return await run_actual_model_scenario_definition(
        scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
        scenario_id=scenario_id,
        fixture_root=_FIXTURE_ROOT,
        workspace_root=workspace_root,
        provider=_Provider(),
        manifest=_manifest(restart=restart, replicate_id=replicate_id),
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
        character_realization_observations=_character_realization(3),
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
    mapping = review.to_mapping()
    assert mapping["score"] is None
    assert mapping["stage_r_review"]["protocol_version"] == STAGE_R_REVIEW_PROTOCOL_VERSION
    assert all(
        observation["outcome"] == "not_rated"
        for observation in mapping["stage_r_review"]["observations"]
    )
    assert [
        observation["outcome"]
        for observation in mapping["character_realization"]["observations"]
    ] == ["normal", "normal", "normal"]


def test_review_rejects_source_execution_that_cannot_be_cited(tmp_path: Path) -> None:
    first = asyncio.run(
        _run(
            workspace_root=tmp_path / "run-0",
            scenario_id="response-persona-correction-v1",
            replicate_id="0",
        )
    )
    second = asyncio.run(
        _run(
            workspace_root=tmp_path / "run-1",
            scenario_id="response-persona-correction-v1",
            replicate_id="1",
        )
    )
    mixed = replace(
        first,
        evidence=second.evidence,
        execution_id=_stable_execution_id(
            plan=first.plan,
            run_id=second.run_id,
        ),
    )

    with pytest.raises(
        ActualModelExecutionReviewError,
        match="source execution is not citable",
    ):
        review_actual_model_execution(
            result=mixed,
            reviewer_identity="rater-a",
            ratings=_ratings(
                family="response_persona_continuity",
                turn_count=3,
            ),
            character_realization_observations=_character_realization(3),
        )


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
            character_realization_observations=_character_realization(3),
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
        character_realization_observations=_character_realization(3),
    )

    assert tuple(rating.turn_index for rating in review.turn_ratings) == (1, 2, 3)
    assert tuple(
        observation.turn_index
        for observation in review.character_realization_observations
    ) == (1, 2, 3)
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
    realization = _character_realization(3)

    first = review_actual_model_execution(
        result=result,
        reviewer_identity="rater-a",
        ratings=ratings,
        character_realization_observations=realization,
    )
    second = review_actual_model_execution(
        result=result,
        reviewer_identity="rater-b",
        ratings=ratings,
        character_realization_observations=realization,
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
        character_realization_observations=_character_realization(3),
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
    assert loaded["stage_r_review"]["protocol_version"] == STAGE_R_REVIEW_PROTOCOL_VERSION
    assert loaded["character_realization"]["observations"][0]["outcome"] == "normal"
    assert loaded["score"] is None


def test_stage_r_review_protocol_exposes_required_material_dimensions() -> None:
    assert STAGE_R_REVIEW_PROTOCOL_VERSION == "actual-model-stage-r-review-v2"
    assert required_stage_r_review_dimensions() == (
        "relevance_correctness",
        "naturalness",
        "persona_style_consistency",
        "coherence",
        "governed_context_continuity",
        "verbosity_fit",
        "language_preservation",
        "multilingual_code_switch_robustness",
        "unsupported_recall",
        "protocol_schema_validity",
        "semantic_precision_recall",
        "grounding",
        "source_subject_attribution",
        "assistant_to_user_contamination",
        "correction_supersession",
        "negation_polarity",
        "uncertainty_preservation",
        "comparative_degree_preservation",
        "transient_durable_classification",
        "canonical_class_key_reuse",
        "noop_correctness",
        "proposal_churn",
        "hallucinated_proposals",
        "source_event_validity",
    )


def test_stage_r_review_requires_exact_independent_dimension_coverage() -> None:
    observations = tuple(
        StageRReviewObservation(
            dimension=dimension,
            outcome="pass",
            note=f"reviewed: {dimension}",
        )
        for dimension in required_stage_r_review_dimensions()
    )

    normalized = normalize_stage_r_review_observations(observations)
    assert tuple(item.dimension for item in normalized) == required_stage_r_review_dimensions()

    with pytest.raises(ValueError, match="cover every required Stage R review dimension"):
        normalize_stage_r_review_observations(observations[:-1])

    duplicate = observations + (observations[0],)
    with pytest.raises(ValueError, match="must not duplicate dimensions"):
        normalize_stage_r_review_observations(duplicate)


def test_stage_r_review_dimensions_are_citable_without_a_composite_score() -> None:
    observations = tuple(
        StageRReviewObservation(
            dimension=dimension,
            outcome="fail" if dimension == "grounding" else "pass",
        )
        for dimension in required_stage_r_review_dimensions()
    )
    empty_channel = ProposalChannelMetrics(
        expected_count=0,
        observed_count=0,
        true_positive_count=0,
        false_positive_count=0,
        false_negative_count=0,
        precision=None,
        recall=None,
    )
    review = ActualModelExecutionReview(
        review_id="amv-stage-r-test",
        execution_id="ame-stage-r-test",
        run_id="amr-stage-r-test",
        scenario_set_revision="sha256:scenario-set",
        scenario_id="stage-r-test",
        scenario_family="state_candidate_quality",
        reviewer_identity="test-reviewer",
        turn_ratings=(),
        proposal_metrics=LabeledProposalMetrics(
            state=empty_channel,
            continuity=empty_channel,
        ),
        stage_r_observations=normalize_stage_r_review_observations(observations),
        character_realization_observations=(
            CharacterRealizationObservation(turn_index=1, outcome="system_defect"),
        ),
    )

    mapping = review.to_mapping()
    assert ACTUAL_MODEL_REVIEW_FORMAT_VERSION == 3
    assert mapping["score"] is None
    assert mapping["stage_r_review"]["protocol_version"] == STAGE_R_REVIEW_PROTOCOL_VERSION
    by_dimension = {
        item["dimension"]: item["outcome"]
        for item in mapping["stage_r_review"]["observations"]
    }
    assert by_dimension["grounding"] == "fail"
    assert len(by_dimension) == len(required_stage_r_review_dimensions())
    assert mapping["character_realization"]["observations"][0]["outcome"] == "system_defect"
