from __future__ import annotations

import inspect

import pytest

from relaylm.actual_model_quality import LabeledProposalMetrics, ProposalChannelMetrics
from relaylm.actual_model_review import (
    ACTUAL_MODEL_REVIEW_FORMAT_VERSION,
    STAGE_R_REVIEW_PROTOCOL_VERSION,
    ActualModelExecutionReview,
    CharacterRealizationObservation,
    StageRReviewObservation,
    _stable_review_id,
    normalize_stage_r_review_observations,
    required_stage_r_review_dimensions,
    review_actual_model_execution,
)


def _empty_metrics() -> LabeledProposalMetrics:
    empty = ProposalChannelMetrics(
        expected_count=0,
        observed_count=0,
        true_positive_count=0,
        false_positive_count=0,
        false_negative_count=0,
        precision=None,
        recall=None,
    )
    return LabeledProposalMetrics(state=empty, continuity=empty)


def _stage_r_observations(
    *,
    rated_dimension: str | None = None,
) -> tuple[StageRReviewObservation, ...]:
    return normalize_stage_r_review_observations(
        tuple(
            StageRReviewObservation(
                dimension=dimension,
                outcome="pass" if dimension == rated_dimension else "not_rated",
            )
            for dimension in required_stage_r_review_dimensions()
        )
    )


def _review(
    *,
    claim_scope: str,
    rated_dimension: str | None = None,
) -> ActualModelExecutionReview:
    return ActualModelExecutionReview(
        review_id="amv-claim-scope-test",
        execution_id="ame-claim-scope-test",
        run_id="amr-claim-scope-test",
        scenario_set_revision="sha256:scenario-set",
        scenario_id="claim-scope-test",
        scenario_family="state_candidate_quality",
        reviewer_identity="test-reviewer",
        turn_ratings=(),
        proposal_metrics=_empty_metrics(),
        stage_r_observations=_stage_r_observations(
            rated_dimension=rated_dimension,
        ),
        character_realization_observations=(
            CharacterRealizationObservation(turn_index=1, outcome="normal"),
        ),
        claim_scope=claim_scope,
    )


def _identity(review: ActualModelExecutionReview) -> dict[str, object]:
    mapping = review.to_mapping()
    mapping.pop("review_id")
    mapping.pop("score")
    return mapping


def test_current_review_format_makes_claim_scope_explicit_and_identity_material() -> None:
    assert ACTUAL_MODEL_REVIEW_FORMAT_VERSION == 4
    assert STAGE_R_REVIEW_PROTOCOL_VERSION == "actual-model-stage-r-review-v3"

    regression = _review(claim_scope="regression")
    qualification = _review(
        claim_scope="qualification",
        rated_dimension="grounding",
    )

    assert regression.to_mapping()["claim_scope"] == "regression"
    assert qualification.to_mapping()["claim_scope"] == "qualification"
    assert _stable_review_id(_identity(regression)) != _stable_review_id(
        _identity(qualification)
    )


def test_qualification_scope_rejects_an_entirely_unrated_stage_r_review() -> None:
    with pytest.raises(ValueError, match="qualification.*rated Stage R"):
        _review(claim_scope="qualification")


def test_smoke_scope_cannot_carry_rated_stage_r_qualification_dimensions() -> None:
    smoke = _review(claim_scope="smoke")
    assert smoke.to_mapping()["claim_scope"] == "smoke"

    with pytest.raises(ValueError, match="smoke.*not_rated"):
        _review(claim_scope="smoke", rated_dimension="grounding")


def test_review_claim_scope_is_closed_and_explicit_at_review_construction() -> None:
    with pytest.raises(ValueError, match="unsupported review claim scope"):
        _review(claim_scope="release_gate")

    parameter = inspect.signature(review_actual_model_execution).parameters["claim_scope"]
    assert parameter.default is inspect.Parameter.empty
