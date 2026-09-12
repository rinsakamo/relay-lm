from __future__ import annotations

import json

import pytest

from relaylm.v2_cognitive_ir_semantic_reconstruction import (
    ARCHITECTURE_CONSEQUENCE,
    ARMS,
    COST_FIELDS,
    FAMILY_COUNT,
    FORBIDDEN_RESCUE_COUNTS,
    PHYSICAL_EXECUTION_AUTHORIZED,
    ReconstructionCost,
    PairedTable,
    SemanticReconstructionBindingError,
    build_reconstruction_messages,
    classify_result,
    derive_family_seed,
    exact_two_sided_sign_p,
    historical_family_seeds,
    paired_accuracy_difference,
    paired_table,
    parse_reconstruction,
    prepare_mechanism_control,
    preregistered_seeds,
    score_reconstruction,
    semantic_call_plan,
    validate_repository_binding,
)


EXPECTED_SEEDS = (
    9956924523623791395,
    12636623151296898040,
    12266820603447285202,
    7866723780596040138,
    5538785497352014992,
    14661894768007893618,
    14233256902077195329,
    10640421078216137770,
    17497337198250531927,
    17776681887804158630,
    3017503477655879406,
    6306960725878714224,
    7043084044370672592,
    5557238527396371894,
    880484847178636564,
    12180688960586963577,
)


def _truth() -> dict[str, object]:
    return {
        "operation": "affine_permutation",
        "permutation": [2, 0, 3, 1],
        "offsets": [1, 2, 0, 3],
        "modulus": 10,
        "provenance_handles": ["src-a", "src-b"],
    }


def test_seed_rule_is_exact_unique_and_fresh_against_current_history() -> None:
    assert preregistered_seeds() == EXPECTED_SEEDS
    assert tuple(derive_family_seed(index) for index in range(16)) == EXPECTED_SEEDS
    assert len(set(EXPECTED_SEEDS)) == FAMILY_COUNT
    assert set(EXPECTED_SEEDS).isdisjoint(historical_family_seeds())
    with pytest.raises(SemanticReconstructionBindingError):
        derive_family_seed(-1)
    with pytest.raises(SemanticReconstructionBindingError):
        derive_family_seed(16)
    with pytest.raises(SemanticReconstructionBindingError):
        derive_family_seed(True)


def test_mechanism_control_changes_surface_not_semantics() -> None:
    control = prepare_mechanism_control(_truth())
    p4 = json.loads(control.serialized_by_arm[ARMS[0]])
    p6 = json.loads(control.serialized_by_arm[ARMS[1]])

    assert control.canonical_truth == _truth()
    assert control.serialized_by_arm[ARMS[0]] != control.serialized_by_arm[ARMS[1]]
    assert set(p4) == {"memory", "structure"}
    assert set(p6) == {"context", "relation"}
    assert p4["memory"]["origin_refs"] == p6["context"]["refs"]
    assert control.semantic_digest


def test_model_interface_is_arm_symmetric_except_representation_bytes() -> None:
    control = prepare_mechanism_control(_truth())
    p4_messages = build_reconstruction_messages(control.serialized_by_arm[ARMS[0]])
    p6_messages = build_reconstruction_messages(control.serialized_by_arm[ARMS[1]])

    assert p4_messages[0] == p6_messages[0]
    assert p4_messages[1]["role"] == p6_messages[1]["role"] == "user"
    assert p4_messages[1]["content"] != p6_messages[1]["content"]
    assert "src-a" not in p4_messages[0]["content"]
    assert "src-a" not in p6_messages[0]["content"]


def test_strict_parser_and_scoring_keep_diagnostics_separate() -> None:
    truth = _truth()
    exact = json.dumps(truth)
    score = score_reconstruction(exact, truth)
    assert score.parse_valid
    assert score.full_payload_exact
    assert score.core_rule_exact
    assert score.provenance_exact

    wrong_provenance = dict(truth)
    wrong_provenance["provenance_handles"] = ["wrong"]
    diagnostic = score_reconstruction(json.dumps(wrong_provenance), truth)
    assert diagnostic.parse_valid
    assert not diagnostic.full_payload_exact
    assert diagnostic.core_rule_exact
    assert not diagnostic.provenance_exact

    invalid = score_reconstruction("not-json", truth)
    assert not invalid.parse_valid
    assert not invalid.full_payload_exact

    with pytest.raises(SemanticReconstructionBindingError):
        parse_reconstruction(
            '{"operation":"affine_permutation","operation":"affine_permutation",'
            '"permutation":[0,1,2,3],"offsets":[1,2,3,0],"modulus":10,'
            '"provenance_handles":["src-a"]}'
        )
    with pytest.raises(SemanticReconstructionBindingError):
        parse_reconstruction(json.dumps({"operation": "affine_permutation"}))
    with pytest.raises(SemanticReconstructionBindingError):
        parse_reconstruction("[]")


def test_call_ledger_and_zero_rescue_contract_are_exact() -> None:
    plan = semantic_call_plan()
    assert len(plan) == 32
    assert len({(index, seed) for index, seed, _ in plan}) == 16
    for index, seed in enumerate(EXPECTED_SEEDS):
        assert [(i, s, arm) for i, s, arm in plan if i == index] == [
            (index, seed, ARMS[0]),
            (index, seed, ARMS[1]),
        ]
    assert all(value == 0 for value in FORBIDDEN_RESCUE_COUNTS.values())
    assert not PHYSICAL_EXECUTION_AUTHORIZED
    assert ARCHITECTURE_CONSEQUENCE == "NONE"


def test_cost_vector_is_frozen_and_one_model_call_per_cell() -> None:
    assert COST_FIELDS == (
        "input_tokens",
        "output_tokens",
        "model_calls",
        "wall_clock_seconds",
        "representation_bytes",
        "representation_tokens",
    )
    ReconstructionCost(
        input_tokens=100,
        output_tokens=20,
        model_calls=1,
        wall_clock_seconds=0.5,
        representation_bytes=200,
        representation_tokens=50,
    ).validate()
    with pytest.raises(SemanticReconstructionBindingError):
        ReconstructionCost(
            input_tokens=100,
            output_tokens=20,
            model_calls=2,
            wall_clock_seconds=0.5,
            representation_bytes=200,
            representation_tokens=50,
        ).validate()


def test_six_one_direction_discordants_are_significant() -> None:
    table = PairedTable(
        both_correct=10,
        p4_only=6,
        p6_only=0,
        both_wrong=0,
    )
    assert exact_two_sided_sign_p(table) == pytest.approx(0.03125)
    assert paired_accuracy_difference(table) == pytest.approx(6 / 16)
    verdict = classify_result(table)
    assert verdict.classification == (
        "CONSUMER_ACCESSIBILITY_DIFFERENCE_DETECTED_WITHIN_DECLARED_SCOPE"
    )
    assert verdict.statistical_status == "SIGNIFICANT_PAIRED_EXACT_TEST"
    assert verdict.architecture_consequence == "NONE"


def test_non_significance_is_underdetermined_not_equivalence() -> None:
    table = PairedTable(
        both_correct=0,
        p4_only=3,
        p6_only=0,
        both_wrong=13,
    )
    verdict = classify_result(table)
    assert exact_two_sided_sign_p(table) == pytest.approx(0.25)
    assert verdict.classification == "NO_ACCESSIBILITY_GAP_DETECTED_AT_THIS_RESOLUTION"
    assert verdict.statistical_status == "UNDERDETERMINED"
    assert verdict.architecture_consequence == "NONE"

    tied = PairedTable(
        both_correct=8,
        p4_only=0,
        p6_only=0,
        both_wrong=8,
    )
    assert exact_two_sided_sign_p(tied) == 1.0
    assert classify_result(tied).statistical_status == "UNDERDETERMINED"


def test_paired_table_builder_and_fail_closed_verdicts() -> None:
    outcomes = [(True, True)] * 7 + [(True, False)] * 4 + [(False, True)] * 2 + [
        (False, False)
    ] * 3
    table = paired_table(outcomes)
    assert table == PairedTable(7, 4, 2, 3)

    invalid = classify_result(None, pre_execution_valid=False)
    assert invalid.classification == "INVALID_BEFORE_PHYSICAL_EXECUTION"
    assert invalid.statistical_status == "INVALID"

    failed = classify_result(None, protocol_failure_after_spend=True)
    assert failed.classification == "PROTOCOL_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND"
    assert failed.statistical_status == "UNDERDETERMINED"
    assert failed.architecture_consequence == "NONE"

    with pytest.raises(SemanticReconstructionBindingError):
        exact_two_sided_sign_p(PairedTable(0, 1, 0, 0))


def test_repository_binding_is_zero_gpu_and_self_consistent() -> None:
    validate_repository_binding()
