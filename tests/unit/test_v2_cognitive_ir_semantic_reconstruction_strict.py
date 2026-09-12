from __future__ import annotations

import json

import pytest

from relaylm.v2_cognitive_ir_semantic_reconstruction import ARMS
from relaylm.v2_cognitive_ir_semantic_reconstruction_strict import (
    ARCHITECTURE_CONSEQUENCE,
    FAMILY_COUNT,
    FORBIDDEN_RESCUE_COUNTS,
    INPUT_TOKEN_REQUESTS,
    MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS,
    PHYSICAL_EXECUTION_AUTHORIZED,
    SEMANTIC_COMPLETIONS,
    PairedTable,
    StrictSemanticReconstructionBindingError,
    build_reconstruction_messages,
    classify_result,
    derive_family_seed,
    exact_two_sided_sign_p,
    historical_family_seeds,
    measurement_admitted,
    paired_accuracy_difference,
    paired_table,
    prepare_synthetic_mechanism_control,
    preregistered_seeds,
    response_format,
    score_strict_reconstruction,
    semantic_call_plan,
    validate_repository_binding,
)
from relaylm.v2_cognitive_ir_strict_output_interface_qualification import (
    response_format as ifq1_response_format,
)


EXPECTED_SEEDS = (
    2119376073192896066,
    5900211396291341187,
    6562417272095619540,
    1743183614391135573,
    11486944467997928183,
    1875380321048797361,
    5209824376994897406,
    10169014699017748984,
    13998589092333998462,
    17732184759129999589,
    4320389854080250128,
    13604607080207947807,
    15725903139176241685,
    881607889668600904,
    4165698444923983612,
    1782181358929056509,
    18306909319727476566,
    10514593578361279859,
    7419403299707419191,
    9627133514070245039,
    12072445020503408454,
    444507745181474845,
    3092979123399350819,
    12861733434118123756,
)


def _truth() -> dict[str, object]:
    return {
        "operation": "affine_permutation",
        "permutation": [2, 0, 3, 1],
        "offsets": [1, 2, 0, 3],
        "modulus": 10,
        "provenance_handles": ["src-a", "src-b"],
    }


def _admitted(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "semantic_equal_pairs": 24,
        "provider_attempts": 48,
        "provider_completions": 48,
        "strict_parse_valid": 48,
        "input_count_attempts": 96,
        "input_count_completions": 96,
        "rescue_counts": dict(FORBIDDEN_RESCUE_COUNTS),
        "truncation_failures": 0,
        "identity_checks_passed": True,
    }
    values.update(overrides)
    return values


def test_seed_rule_is_exact_unique_and_fresh_against_current_history() -> None:
    assert preregistered_seeds() == EXPECTED_SEEDS
    assert tuple(derive_family_seed(index) for index in range(24)) == EXPECTED_SEEDS
    assert len(set(EXPECTED_SEEDS)) == FAMILY_COUNT
    assert set(EXPECTED_SEEDS).isdisjoint(historical_family_seeds())
    with pytest.raises(StrictSemanticReconstructionBindingError):
        derive_family_seed(-1)
    with pytest.raises(StrictSemanticReconstructionBindingError):
        derive_family_seed(24)
    with pytest.raises(StrictSemanticReconstructionBindingError):
        derive_family_seed(True)


def test_synthetic_helper_rejects_all_preregistered_seeds() -> None:
    for seed in EXPECTED_SEEDS:
        with pytest.raises(StrictSemanticReconstructionBindingError):
            prepare_synthetic_mechanism_control(seed, _truth())

    control = prepare_synthetic_mechanism_control(1, _truth())
    assert control.canonical_truth == _truth()
    assert control.serialized_by_arm[ARMS[0]] != control.serialized_by_arm[ARMS[1]]
    assert control.semantic_digest


def test_response_format_reuses_ifq1_qualified_interface_exactly() -> None:
    strict_format = response_format()
    assert strict_format == ifq1_response_format()
    assert strict_format["type"] == "json_schema"
    json_schema = strict_format["json_schema"]
    assert json_schema["strict"] is True
    schema = json_schema["schema"]
    assert set(schema["required"]) == {
        "operation",
        "permutation",
        "offsets",
        "modulus",
        "provenance_handles",
    }
    assert schema["additionalProperties"] is False
    encoded = json.dumps(strict_format, sort_keys=True)
    for secret in (
        "src-a",
        "src-b",
        "P4_MEMORY_PLUS_STRUCTURE",
        "P6_GENERIC_EQUAL_INFORMATION",
    ):
        assert secret not in encoded


def test_model_interface_is_arm_symmetric_except_representation_bytes() -> None:
    control = prepare_synthetic_mechanism_control(1, _truth())
    p4_messages = build_reconstruction_messages(control.serialized_by_arm[ARMS[0]])
    p6_messages = build_reconstruction_messages(control.serialized_by_arm[ARMS[1]])

    assert p4_messages[0] == p6_messages[0]
    assert p4_messages[1]["role"] == p6_messages[1]["role"] == "user"
    assert p4_messages[1]["content"] != p6_messages[1]["content"]
    assert "src-a" not in p4_messages[0]["content"]
    assert "src-a" not in p6_messages[0]["content"]


def test_strict_scoring_preserves_primary_and_diagnostics() -> None:
    truth = _truth()
    exact = score_strict_reconstruction(json.dumps(truth), truth)
    assert exact.strict_parse_valid
    assert exact.full_payload_exact
    assert exact.core_rule_exact
    assert exact.provenance_exact

    wrong_provenance = dict(truth)
    wrong_provenance["provenance_handles"] = ["wrong"]
    diagnostic = score_strict_reconstruction(json.dumps(wrong_provenance), truth)
    assert diagnostic.strict_parse_valid
    assert not diagnostic.full_payload_exact
    assert diagnostic.core_rule_exact
    assert not diagnostic.provenance_exact

    fenced = score_strict_reconstruction(
        "```json\n" + json.dumps(truth) + "\n```",
        truth,
    )
    assert not fenced.strict_parse_valid
    assert not fenced.full_payload_exact


def test_call_ledger_and_zero_rescue_contract_are_exact() -> None:
    plan = semantic_call_plan()
    assert len(plan) == SEMANTIC_COMPLETIONS == 48
    assert len({(index, seed) for index, seed, _ in plan}) == FAMILY_COUNT == 24
    for index, seed in enumerate(EXPECTED_SEEDS):
        assert [(i, s, arm) for i, s, arm in plan if i == index] == [
            (index, seed, ARMS[0]),
            (index, seed, ARMS[1]),
        ]
    assert INPUT_TOKEN_REQUESTS == 96
    assert MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS == 2
    assert all(value == 0 for value in FORBIDDEN_RESCUE_COUNTS.values())
    assert not PHYSICAL_EXECUTION_AUTHORIZED
    assert ARCHITECTURE_CONSEQUENCE == "NONE"


def test_measurement_admission_requires_every_frozen_gate() -> None:
    assert measurement_admitted(**_admitted())

    for key, value in (
        ("semantic_equal_pairs", 23),
        ("provider_attempts", 47),
        ("provider_completions", 47),
        ("strict_parse_valid", 47),
        ("input_count_attempts", 95),
        ("input_count_completions", 95),
        ("truncation_failures", 1),
        ("identity_checks_passed", False),
    ):
        assert not measurement_admitted(**_admitted(**{key: value}))

    rescued = dict(FORBIDDEN_RESCUE_COUNTS)
    rescued["fallback"] = 1
    assert not measurement_admitted(**_admitted(rescue_counts=rescued))


def test_six_one_direction_discordants_are_significant() -> None:
    table = PairedTable(
        both_correct=10,
        p4_only=6,
        p6_only=0,
        both_wrong=8,
    )
    assert exact_two_sided_sign_p(table) == pytest.approx(0.03125)
    assert paired_accuracy_difference(table) == pytest.approx(6 / 24)
    verdict = classify_result(table, measurement_passed=True)
    assert verdict.classification == (
        "CONSUMER_ACCESSIBILITY_DIFFERENCE_DETECTED_WITHIN_DECLARED_SCOPE"
    )
    assert verdict.statistical_status == "SIGNIFICANT_PAIRED_EXACT_TEST"
    assert verdict.citable_for_accessibility_claim
    assert verdict.architecture_consequence == "NONE"


def test_non_significance_is_underdetermined_not_equivalence() -> None:
    table = PairedTable(
        both_correct=0,
        p4_only=3,
        p6_only=0,
        both_wrong=21,
    )
    verdict = classify_result(table, measurement_passed=True)
    assert exact_two_sided_sign_p(table) == pytest.approx(0.25)
    assert verdict.classification == "NO_ACCESSIBILITY_GAP_DETECTED_AT_THIS_RESOLUTION"
    assert verdict.statistical_status == "UNDERDETERMINED"
    assert verdict.citable_for_accessibility_claim

    tied = PairedTable(
        both_correct=12,
        p4_only=0,
        p6_only=0,
        both_wrong=12,
    )
    assert exact_two_sided_sign_p(tied) == 1.0
    assert (
        classify_result(tied, measurement_passed=True).statistical_status
        == "UNDERDETERMINED"
    )


def test_paired_table_builder_and_fail_closed_verdicts() -> None:
    outcomes = [(True, True)] * 9 + [(True, False)] * 4 + [(False, True)] * 2 + [
        (False, False)
    ] * 9
    table = paired_table(outcomes)
    assert table == PairedTable(9, 4, 2, 9)

    invalid = classify_result(None, pre_execution_valid=False)
    assert invalid.classification == "INVALID_BEFORE_PHYSICAL_EXECUTION"
    assert invalid.statistical_status == "INVALID"
    assert not invalid.citable_for_accessibility_claim

    failed = classify_result(None, protocol_failure_after_spend=True)
    assert failed.classification == (
        "MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND"
    )
    assert failed.statistical_status == "UNDERDETERMINED"
    assert not failed.citable_for_accessibility_claim
    assert failed.architecture_consequence == "NONE"

    with pytest.raises(StrictSemanticReconstructionBindingError):
        exact_two_sided_sign_p(PairedTable(0, 1, 0, 0))


def test_repository_binding_is_zero_gpu_and_self_consistent() -> None:
    validate_repository_binding()
