from __future__ import annotations

from relaylm.v2_transfer_actual_model import build_source_learning_messages
from tools.v2_transfer_r2_source_learning_forensic import (
    R2_FROZEN_PREREGISTRATION_COMMIT,
    forensic_report,
)
from tools.v2_transfer_r2_prereg import generate_families


def test_frozen_r2_source_packets_are_uniquely_identifiable_after_four_examples() -> None:
    report = forensic_report(R2_FROZEN_PREREGISTRATION_COMMIT)

    assert len(report.families) == 16
    assert all(item.source_candidate_counts[-1] == 1 for item in report.families)
    assert report.source_unique_after_four == 16
    assert report.source_max_candidates_after_four == 1


def test_frozen_r2_source_prefix_counts_match_the_exact_seed_set() -> None:
    report = forensic_report(R2_FROZEN_PREREGISTRATION_COMMIT)

    assert [item.source_candidate_counts for item in report.families] == [
        (24, 4, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 2, 1, 1),
        (24, 2, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 1, 1, 1),
        (24, 2, 1, 1),
        (24, 2, 1, 1),
        (24, 6, 2, 1),
        (24, 2, 1, 1),
    ]


def test_frozen_r2_target_packets_are_uniquely_identifiable_at_three_examples() -> None:
    report = forensic_report(R2_FROZEN_PREREGISTRATION_COMMIT)

    assert report.target_unique_after_three == 16
    assert all(item.target_candidate_counts[-1] == 1 for item in report.families)
    assert [item.target_candidate_counts for item in report.families] == [
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
        (240000, 24, 1, 1),
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
        (240000, 24, 2, 1),
        (240000, 24, 2, 1),
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
        (240000, 24, 1, 1),
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
        (240000, 24, 2, 1),
        (240000, 24, 1, 1),
    ]


def test_source_prompt_does_not_define_the_permutation_direction_equation() -> None:
    family = generate_families(R2_FROZEN_PREREGISTRATION_COMMIT)[0]
    system = build_source_learning_messages(family)[0]["content"]

    # The frozen prompt names the fields and shapes, but never states the
    # evaluator convention y[i] = x[permutation[i]] + offsets[i] (mod modulus).
    assert "permutation" in system
    assert "offsets" in system
    assert "y[" not in system
    assert "x[" not in system
    assert "mod" not in system.lower()
