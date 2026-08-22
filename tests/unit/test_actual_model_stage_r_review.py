from __future__ import annotations

import pytest

from relaylm.actual_model_review import (
    STAGE_R_REVIEW_PROTOCOL_VERSION,
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
