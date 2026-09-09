from __future__ import annotations

from tools.v2_transfer_q1_target_range import (
    CALIBRATION_SELECTED,
    CANDIDATES,
    EVIDENCE_LEVELS,
    NO_MEASURABLE_TARGET_RANGE,
    CalibrationOutcome,
    build_manifest,
    calibration_call_plan,
    calibration_seeds,
    candidate_rule_count,
    generate_family,
    qualification_call_plan,
    qualification_seeds,
    select_calibration_candidate,
)
from tools.v2_transfer_qualification import PASS, classify_q1
from tools.v2_transfer_q1_target_range import q1_result

ANCHOR = "1" * 40


def _outcome(candidate_id: str, endpoint: int) -> CalibrationOutcome:
    return CalibrationOutcome(candidate_id, 4, (0, 1, min(2, endpoint), endpoint), endpoint)


def test_frozen_ladder_plans_and_seed_domains() -> None:
    assert [x.candidate_id for x in CANDIDATES] == [
        "C0_W2_OFFSET_ONLY",
        "C1_W2_PERMUTATION_OFFSETS",
        "C2_W3_PERMUTATION_OFFSETS",
        "C3_W4_PERMUTATION_OFFSETS",
    ]
    calibration = calibration_call_plan(ANCHOR)
    assert len(calibration) == 64
    assert [x.call_index for x in calibration] == list(range(64))
    for candidate in CANDIDATES:
        cal = calibration_seeds(ANCHOR, candidate.candidate_id)
        heldout = qualification_seeds(ANCHOR, candidate.candidate_id)
        assert len(cal) == 4 and len(heldout) == 8
        assert set(cal).isdisjoint(heldout)
        assert len(qualification_call_plan(ANCHOR, candidate.candidate_id)) == 32
        for seed in cal + heldout:
            assert candidate_rule_count(generate_family(seed, candidate.candidate_id), 3) == 1


def test_selector_uses_first_passing_candidate_after_complete_ladder() -> None:
    outcomes = (
        _outcome(CANDIDATES[0].candidate_id, 4),
        _outcome(CANDIDATES[1].candidate_id, 1),
        _outcome(CANDIDATES[2].candidate_id, 3),
        _outcome(CANDIDATES[3].candidate_id, 2),
    )
    selected = select_calibration_candidate(outcomes)
    assert selected.status == CALIBRATION_SELECTED
    assert selected.selected_candidate_id == CANDIDATES[1].candidate_id
    no_range = tuple(_outcome(x.candidate_id, 0) for x in CANDIDATES)
    assert select_calibration_candidate(no_range).status == NO_MEASURABLE_TARGET_RANGE


def test_prompt_declares_equation_and_never_supplies_source_or_oracle() -> None:
    for candidate in CANDIDATES:
        family = generate_family(calibration_seeds(ANCHOR, candidate.candidate_id)[0], candidate.candidate_id)
        payload = family.payload(3)
        semantics = payload["transformation_family"]
        assert "y[i] = (x[permutation[i]] + offsets[i]) mod modulus" in semantics
        encoded = str(payload).lower()
        assert "oracle" not in encoded
        assert "source" not in encoded
        assert len(payload["examples"]) == 3


def test_heldout_manifest_has_predeclared_q1_q2_q3_thresholds() -> None:
    manifest = build_manifest(ANCHOR, CANDIDATES[1].candidate_id, "sha256:" + "a" * 64)
    assert manifest.target_evidence_levels == EVIDENCE_LEVELS
    assert manifest.thresholds.q1_min_endpoint_rate == 0.25
    assert manifest.thresholds.q1_max_endpoint_rate == 0.875
    assert manifest.thresholds.q2_min_exact_structure_rate == 0.50
    assert manifest.thresholds.q2_min_behavioral_rate == 0.75
    assert manifest.thresholds.q3_min_shared_gain == 0.25
    assert manifest.thresholds.q3_min_interaction == 0.20
    result = q1_result(manifest, "evidence:q1", (0, 2, 4, 5))
    assert result.structure_origin == "NONE"
    assert result.replaced_seed_count == 0
    assert classify_q1(manifest, result) == PASS
