from __future__ import annotations

import pytest

from relaylm.actual_model_quality import LabeledProposalMetrics, ProposalChannelMetrics
from relaylm.actual_model_review import (
    ACTUAL_MODEL_REVIEW_FORMAT_VERSION,
    STAGE_R_REVIEW_PROTOCOL_VERSION,
    ActualModelExecutionReview,
    StageRReviewObservation,
    normalize_stage_r_review_observations,
    required_stage_r_review_dimensions,
)


def test_stage_r_review_protocol_exposes_required_material_dimensions() -> None:
    dimensions = required_stage_r_review_dimensions()

    assert STAGE_R_REVIEW_PROTOCOL_VERSION == "actual-model-stage-r-review-v1"
    assert dimensions == (
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
    )

    mapping = review.to_mapping()
    assert ACTUAL_MODEL_REVIEW_FORMAT_VERSION == 2
    assert mapping["score"] is None
    assert mapping["stage_r_review"]["protocol_version"] == STAGE_R_REVIEW_PROTOCOL_VERSION
    by_dimension = {
        item["dimension"]: item["outcome"]
        for item in mapping["stage_r_review"]["observations"]
    }
    assert by_dimension["grounding"] == "fail"
    assert len(by_dimension) == len(required_stage_r_review_dimensions())
