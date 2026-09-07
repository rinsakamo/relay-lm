from __future__ import annotations

from copy import deepcopy

import pytest

from relaylm.v2_cognitive_ir_calibration import (
    CALIBRATION_DIFFICULTIES,
    CALIBRATION_SEEDS,
    generate_calibration_case,
)
from tools.v2_cognitive_ir_calibration_forensic import FORENSIC_CLAIM_STATUS
from tools.v2_cognitive_ir_calibration_operator_forensic import (
    CalibrationOperatorForensicError,
    OPERATOR_FORENSIC_CLAIM_STATUS,
    analyze_operator_conventions,
)


def _rule_mapping(rule):
    return {
        "permutation": list(rule.permutation),
        "offsets": list(rule.offsets),
        "modulus": rule.modulus,
    }


def _source_report():
    cells = []
    for difficulty in CALIBRATION_DIFFICULTIES:
        for seed in CALIBRATION_SEEDS:
            case = generate_calibration_case(seed=seed, difficulty=difficulty)
            rule = _rule_mapping(case.rule)
            cells.append(
                {
                    "difficulty": difficulty,
                    "seed": seed,
                    "true_rule": rule,
                    "query": list(case.query),
                    "expected_answer": list(case.expected_output),
                    "C0": {"answer": list(case.expected_output)},
                    "C1": {"rule": deepcopy(rule)},
                    "C2": {
                        "rule": deepcopy(rule),
                        "answer": list(case.expected_output),
                    },
                }
            )
    return {
        "claim_status": FORENSIC_CLAIM_STATUS,
        "citable": False,
        "provider_calls_added": 0,
        "run_id": "cal-test",
        "identity_fingerprint": "sha256:test",
        "source_selected_difficulty": None,
        "interpretation_boundary": {
            "causal_effect_claims": False,
            "s2_authorized": False,
            "architecture_consequence": "NONE",
        },
        "cells": cells,
    }


def _cell(report, difficulty, seed):
    return next(
        cell
        for cell in report["cells"]
        if cell["difficulty"] == difficulty and cell["seed"] == seed
    )


def _source_cell(source, difficulty, seed):
    return next(
        cell
        for cell in source["cells"]
        if cell["difficulty"] == difficulty and cell["seed"] == seed
    )


def _inverse(permutation):
    inverse = [0] * len(permutation)
    for output_index, input_index in enumerate(permutation):
        inverse[input_index] = output_index
    return inverse


def test_operator_forensic_preserves_non_citable_boundary():
    report = analyze_operator_conventions(_source_report())

    assert report["claim_status"] == OPERATOR_FORENSIC_CLAIM_STATUS
    assert report["citable"] is False
    assert report["provider_calls_added"] == 0
    assert report["interpretation_boundary"] == {
        "descriptive_hypothesis_matching_only": True,
        "operator_error_cause_proven": False,
        "model_capability_ordering_proven": False,
        "threshold_retuning_authorized": False,
        "s2_authorized": False,
        "architecture_consequence": "NONE",
    }
    assert len(report["cells"]) == 24


def test_inverse_mapping_and_identity_collapse_are_descriptive_relations():
    source = _source_report()

    d1_seed = 1617203301
    d1 = _source_cell(source, "D1_PERMUTATION_ONLY_RANDOM", d1_seed)
    true_permutation = d1["true_rule"]["permutation"]
    inverse = _inverse(true_permutation)
    assert inverse != true_permutation
    d1["C1"]["rule"]["permutation"] = inverse

    d2_seed = CALIBRATION_SEEDS[0]
    d2 = _source_cell(source, "D2_FULL_DIAGNOSTIC", d2_seed)
    d2["C1"]["rule"]["permutation"] = [0, 1, 2, 3]

    report = analyze_operator_conventions(source)

    d1_result = _cell(report, "D1_PERMUTATION_ONLY_RANDOM", d1_seed)
    assert "INVERSE_MAPPING_CANDIDATE" in d1_result["C1"]["permutation_relation"]["relations"]

    d2_result = _cell(report, "D2_FULL_DIAGNOSTIC", d2_seed)
    assert "IDENTITY_COLLAPSE_CANDIDATE" in d2_result["C1"]["permutation_relation"]["relations"]


def test_c0_answer_can_match_one_swapped_permutation_without_reported_rule():
    source = _source_report()
    difficulty = "D1_PERMUTATION_ONLY_RANDOM"
    seed = 841092688
    raw = _source_cell(source, difficulty, seed)
    case = generate_calibration_case(seed=seed, difficulty=difficulty)
    permutation = list(case.rule.permutation)
    permutation[1], permutation[3] = permutation[3], permutation[1]
    raw["C0"]["answer"] = [case.query[index] for index in permutation]

    report = analyze_operator_conventions(source)
    result = _cell(report, difficulty, seed)

    assert [1, 3] in result["C0"]["answer_hypotheses"][
        "single_position_swap_permutation_matches"
    ]


def test_c2_reports_whether_answer_is_consistent_with_its_own_wrong_rule():
    source = _source_report()
    difficulty = "D1_PERMUTATION_ONLY_RANDOM"
    seed = 1617203301
    raw = _source_cell(source, difficulty, seed)
    case = generate_calibration_case(seed=seed, difficulty=difficulty)
    inverse = tuple(_inverse(list(case.rule.permutation)))
    raw["C2"]["rule"]["permutation"] = list(inverse)
    raw["C2"]["answer"] = [case.query[index] for index in inverse]

    report = analyze_operator_conventions(source)
    result = _cell(report, difficulty, seed)

    assert result["C2"]["rule_correct"] is False
    assert result["C2"]["answer_hypotheses"]["reported_rule_self_consistent"] is True
    assert "REPORTED_RULE" in result["C2"]["answer_hypotheses"]["exact_named_matches"]


def test_wrong_sign_offset_answer_is_matched_without_claiming_cause():
    source = _source_report()
    difficulty = "D0_OFFSET_ONLY_RANDOM"
    seed = CALIBRATION_SEEDS[0]
    raw = _source_cell(source, difficulty, seed)
    case = generate_calibration_case(seed=seed, difficulty=difficulty)
    actual = [
        (case.query[index] - case.rule.offsets[index]) % case.rule.modulus
        for index in range(4)
    ]
    raw["C0"]["answer"] = actual

    report = analyze_operator_conventions(source)
    result = _cell(report, difficulty, seed)

    assert "NEGATIVE_OFFSETS" in result["C0"]["answer_hypotheses"]["exact_named_matches"]
    assert report["interpretation_boundary"]["operator_error_cause_proven"] is False


def test_adjacent_modulus_search_is_bounded_to_nine_and_eleven():
    report = analyze_operator_conventions(_source_report())
    for cell in report["cells"]:
        for probe in ("C0", "C2"):
            matches = cell[probe]["answer_hypotheses"]["adjacent_modulus_matches"]
            assert set(matches).issubset({9, 11})


def test_source_integrity_drift_fails_closed():
    source = _source_report()
    source["provider_calls_added"] = 1

    with pytest.raises(CalibrationOperatorForensicError, match="provider calls"):
        analyze_operator_conventions(source)
