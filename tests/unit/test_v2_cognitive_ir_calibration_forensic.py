from __future__ import annotations

import json

import pytest

from relaylm.v2_cognitive_ir_calibration import (
    CALIBRATION_CLAIM_STATUS,
    CALIBRATION_DIFFICULTIES,
    CALIBRATION_PROBES,
    CALIBRATION_SEEDS,
    generate_calibration_case,
)
from tools.v2_cognitive_ir_calibration_forensic import (
    CalibrationForensicError,
    FORENSIC_CLAIM_STATUS,
    analyze_calibration_artifact,
    analyze_calibration_payloads,
)


def _rule_payload(rule, *, answer=None):
    payload = {
        "permutation": list(rule.permutation),
        "offsets": list(rule.offsets),
        "modulus": rule.modulus,
    }
    if answer is not None:
        payload["answer"] = list(answer)
    return payload


def _payloads_with_one_d0_failure():
    evidence = []
    cells = []
    order = 0
    first_seed = CALIBRATION_SEEDS[0]

    for difficulty in CALIBRATION_DIFFICULTIES:
        for seed in CALIBRATION_SEEDS:
            case = generate_calibration_case(seed=seed, difficulty=difficulty)
            application_answer = case.expected_output
            formation_rule = case.rule
            e2e_rule = case.rule
            e2e_answer = case.expected_output

            if difficulty == "D0_OFFSET_ONLY_RANDOM" and seed == first_seed:
                application_answer = tuple((value + 1) % 10 for value in case.expected_output)
                changed_offsets = list(case.rule.offsets)
                changed_offsets[0] = (changed_offsets[0] + 1) % 10
                formation_rule = type(case.rule)(
                    case.rule.permutation,
                    tuple(changed_offsets),
                    case.rule.modulus,
                )

            contents = {
                "C0_APPLICATION_ONLY": json.dumps({"answer": list(application_answer)}),
                "C1_FORMATION_ONLY": json.dumps(_rule_payload(formation_rule)),
                "C2_END_TO_END": json.dumps(_rule_payload(e2e_rule, answer=e2e_answer)),
            }
            for probe in CALIBRATION_PROBES:
                evidence.append(
                    {
                        "run_id": "cal-test",
                        "identity_fingerprint": "sha256:test",
                        "order": order,
                        "question_id": f"{difficulty}|{seed}|{probe}",
                        "content": contents[probe],
                        "classification": "instrumentation_only",
                    }
                )
                order += 1

            application_correct = application_answer == case.expected_output
            formation_correct = formation_rule == case.rule
            e2e_rule_correct = e2e_rule == case.rule
            e2e_answer_correct = e2e_answer == case.expected_output
            cells.append(
                {
                    "seed": seed,
                    "difficulty": difficulty,
                    "application_correct": application_correct,
                    "formation_correct": formation_correct,
                    "end_to_end_rule_correct": e2e_rule_correct,
                    "end_to_end_answer_correct": e2e_answer_correct,
                    "end_to_end_joint_correct": e2e_rule_correct and e2e_answer_correct,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
            )

    result = {
        "claim_status": CALIBRATION_CLAIM_STATUS,
        "citable": False,
        "provider_calls": 72,
        "selected_difficulty": None,
        "seeds": list(CALIBRATION_SEEDS),
        "difficulties": list(CALIBRATION_DIFFICULTIES),
        "probes": list(CALIBRATION_PROBES),
        "cells": cells,
    }
    return result, tuple(evidence)


def test_forensic_reconstructs_descriptive_failure_geometry_without_calls():
    result, evidence = _payloads_with_one_d0_failure()

    report = analyze_calibration_payloads(result, evidence)

    assert report["claim_status"] == FORENSIC_CLAIM_STATUS
    assert report["citable"] is False
    assert report["provider_calls_added"] == 0
    assert report["run_id"] == "cal-test"
    assert report["identity_fingerprint"] == "sha256:test"

    first = report["cells"][0]
    assert first["difficulty"] == "D0_OFFSET_ONLY_RANDOM"
    assert first["seed"] == CALIBRATION_SEEDS[0]
    assert "APPLICATION_FAILURE" in first["flags"]
    assert "FORMATION_FAILURE" in first["flags"]
    assert "FORMATION_GAIN_WITH_QUERY_CANDIDATE" in first["flags"]
    assert first["C0"]["answer_delta"]["hamming"] == 4
    assert first["C1"]["rule_delta"]["permutation_exact"] is True
    assert first["C1"]["rule_delta"]["offset_hamming"] == 1
    assert first["C2"]["joint_correct"] is True

    cross = report["cross_difficulty"]
    assert (
        f"D0_OFFSET_ONLY_RANDOM|{CALIBRATION_SEEDS[0]}"
        in cross["formation_gain_with_query_candidates"]
    )
    assert any(
        item["earlier"] == "D0_OFFSET_ONLY_RANDOM"
        and item["later"] == "D1_PERMUTATION_ONLY_RANDOM"
        for item in cross["application_nonmonotonic_pairs"]
    )


def test_forensic_fails_if_result_boolean_disagrees_with_visible_evidence():
    result, evidence = _payloads_with_one_d0_failure()
    result["cells"][0]["application_correct"] = True

    with pytest.raises(CalibrationForensicError, match="disagrees with visible evidence"):
        analyze_calibration_payloads(result, evidence)


def test_forensic_fails_if_request_evidence_order_is_not_the_frozen_plan():
    result, evidence = _payloads_with_one_d0_failure()
    evidence = list(evidence)
    evidence[0] = {**evidence[0], "order": 1}

    with pytest.raises(CalibrationForensicError, match="order does not match"):
        analyze_calibration_payloads(result, tuple(evidence))


def test_forensic_reads_completed_artifact_without_modifying_source(tmp_path):
    result, evidence = _payloads_with_one_d0_failure()
    root = tmp_path / "artifact"
    root.mkdir()
    result_path = root / "calibration-result.json"
    evidence_path = root / "request-evidence.jsonl"
    result_text = json.dumps(result, sort_keys=True) + "\n"
    evidence_text = "".join(json.dumps(item, sort_keys=True) + "\n" for item in evidence)
    result_path.write_text(result_text, encoding="utf-8")
    evidence_path.write_text(evidence_text, encoding="utf-8")

    report = analyze_calibration_artifact(root)

    assert report["provider_calls_added"] == 0
    assert result_path.read_text(encoding="utf-8") == result_text
    assert evidence_path.read_text(encoding="utf-8") == evidence_text
