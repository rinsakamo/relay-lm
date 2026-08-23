from __future__ import annotations

from pathlib import Path

import pytest

from relaylm.actual_model_quality import LabeledProposalMetrics, ProposalChannelMetrics
from relaylm.actual_model_review import (
    ActualModelExecutionReview,
    ActualModelExecutionReviewError,
    CharacterRealizationObservation,
    StageRReviewObservation,
    required_stage_r_review_dimensions,
    write_actual_model_execution_review,
)


def test_review_writer_rejects_non_content_derived_review_id(tmp_path: Path) -> None:
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
        review_id="amv-not-content-derived",
        execution_id="amx-" + "a" * 64,
        run_id="amr-" + "b" * 64,
        scenario_set_revision="sha256:" + "c" * 64,
        scenario_id="scenario-v1",
        scenario_family="state_candidate_quality",
        reviewer_identity="reviewer-a",
        turn_ratings=(),
        proposal_metrics=LabeledProposalMetrics(
            state=empty_channel,
            continuity=empty_channel,
        ),
        stage_r_observations=tuple(
            StageRReviewObservation(dimension=dimension, outcome="not_rated")
            for dimension in required_stage_r_review_dimensions()
        ),
        character_realization_observations=(
            CharacterRealizationObservation(turn_index=1, outcome="normal"),
        ),
    )

    with pytest.raises(
        ActualModelExecutionReviewError,
        match="review_id does not match review evidence",
    ):
        write_actual_model_execution_review(
            review=review,
            artifact_root=tmp_path,
        )

    assert list(tmp_path.iterdir()) == []
