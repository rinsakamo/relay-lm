from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_quality import LabeledProposalMetrics, ProposalChannelMetrics
from relaylm.actual_model_review import (
    ACTUAL_MODEL_REVIEW_FORMAT_VERSION,
    LEGACY_ACTUAL_MODEL_REVIEW_FORMAT_VERSION,
    LEGACY_STAGE_R_REVIEW_PROTOCOL_VERSION,
    PRE_CLAIM_SCOPE_ACTUAL_MODEL_REVIEW_FORMAT_VERSION,
    PRE_CLAIM_SCOPE_STAGE_R_REVIEW_PROTOCOL_VERSION,
    STAGE_R_REVIEW_PROTOCOL_VERSION,
    ActualModelExecutionReview,
    ActualModelExecutionReviewError,
    CharacterRealizationObservation,
    StageRReviewObservation,
    normalize_character_realization_observations,
    required_stage_r_review_dimensions,
    write_actual_model_execution_review,
)


def _empty_metrics() -> LabeledProposalMetrics:
    channel = ProposalChannelMetrics(
        expected_count=0,
        observed_count=0,
        true_positive_count=0,
        false_positive_count=0,
        false_negative_count=0,
        precision=None,
        recall=None,
    )
    return LabeledProposalMetrics(state=channel, continuity=channel)


def _stage_r_passes() -> tuple[StageRReviewObservation, ...]:
    return tuple(
        StageRReviewObservation(dimension=dimension, outcome="pass")
        for dimension in required_stage_r_review_dimensions()
    )


def test_current_review_versions_preserve_both_historical_identity_generations() -> None:
    assert LEGACY_ACTUAL_MODEL_REVIEW_FORMAT_VERSION == 2
    assert LEGACY_STAGE_R_REVIEW_PROTOCOL_VERSION == "actual-model-stage-r-review-v1"
    assert PRE_CLAIM_SCOPE_ACTUAL_MODEL_REVIEW_FORMAT_VERSION == 3
    assert (
        PRE_CLAIM_SCOPE_STAGE_R_REVIEW_PROTOCOL_VERSION
        == "actual-model-stage-r-review-v2"
    )
    assert ACTUAL_MODEL_REVIEW_FORMAT_VERSION == 4
    assert STAGE_R_REVIEW_PROTOCOL_VERSION == "actual-model-stage-r-review-v3"


def test_character_realization_outcomes_are_not_pass_fail_aliases() -> None:
    observations = normalize_character_realization_observations(
        (
            CharacterRealizationObservation(
                turn_index=1,
                outcome="odd_but_character_plausible",
                note="surprising but consistent with the frozen Character",
            ),
            CharacterRealizationObservation(
                turn_index=2,
                outcome="out_of_character",
            ),
            CharacterRealizationObservation(
                turn_index=3,
                outcome="system_defect",
            ),
            CharacterRealizationObservation(
                turn_index=4,
                outcome="normal",
            ),
        ),
        turn_count=4,
    )

    assert tuple(item.outcome for item in observations) == (
        "odd_but_character_plausible",
        "out_of_character",
        "system_defect",
        "normal",
    )


def test_character_realization_requires_exact_turn_coverage() -> None:
    complete = (
        CharacterRealizationObservation(turn_index=1, outcome="normal"),
        CharacterRealizationObservation(turn_index=2, outcome="normal"),
    )
    assert normalize_character_realization_observations(
        tuple(reversed(complete)),
        turn_count=2,
    ) == complete

    with pytest.raises(ValueError, match="cover every evidence turn exactly once"):
        normalize_character_realization_observations(complete[:1], turn_count=2)

    with pytest.raises(ValueError, match="must not duplicate turns"):
        normalize_character_realization_observations(
            (complete[0], complete[0]),
            turn_count=2,
        )

    with pytest.raises(ValueError, match="cover every evidence turn exactly once"):
        normalize_character_realization_observations(
            (
                CharacterRealizationObservation(turn_index=1, outcome="normal"),
                CharacterRealizationObservation(turn_index=3, outcome="normal"),
            ),
            turn_count=2,
        )


def test_review_serializes_character_realization_separately_from_stage_r_dimensions() -> None:
    review = ActualModelExecutionReview(
        review_id="amv-character-realization-test",
        execution_id="ame-character-realization-test",
        run_id="amr-character-realization-test",
        scenario_set_revision="sha256:scenario-set",
        scenario_id="character-realization-test",
        scenario_family="response_persona_continuity",
        reviewer_identity="test-reviewer",
        turn_ratings=(),
        proposal_metrics=_empty_metrics(),
        stage_r_observations=_stage_r_passes(),
        character_realization_observations=(
            CharacterRealizationObservation(
                turn_index=1,
                outcome="odd_but_character_plausible",
            ),
        ),
        claim_scope="regression",
    )

    mapping = review.to_mapping()
    assert mapping["claim_scope"] == "regression"
    assert mapping["score"] is None
    assert mapping["stage_r_review"]["observations"][0]["outcome"] == "pass"
    assert mapping["character_realization"]["observations"] == [
        {
            "turn_index": 1,
            "outcome": "odd_but_character_plausible",
            "note": None,
        }
    ]


def test_character_realization_is_part_of_content_derived_review_identity(
    tmp_path: Path,
) -> None:
    review = ActualModelExecutionReview(
        review_id="amv-not-content-derived",
        execution_id="ame-character-realization-test",
        run_id="amr-character-realization-test",
        scenario_set_revision="sha256:scenario-set",
        scenario_id="character-realization-test",
        scenario_family="response_persona_continuity",
        reviewer_identity="test-reviewer",
        turn_ratings=(),
        proposal_metrics=_empty_metrics(),
        stage_r_observations=_stage_r_passes(),
        character_realization_observations=(
            CharacterRealizationObservation(turn_index=1, outcome="normal"),
        ),
        claim_scope="regression",
    )

    with pytest.raises(
        ActualModelExecutionReviewError,
        match="review_id does not match review evidence",
    ):
        write_actual_model_execution_review(
            review=replace(
                review,
                character_realization_observations=(
                    CharacterRealizationObservation(
                        turn_index=1,
                        outcome="out_of_character",
                    ),
                ),
            ),
            artifact_root=tmp_path,
        )

    assert list(tmp_path.iterdir()) == []
