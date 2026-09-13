from __future__ import annotations

import json

import pytest

from relaylm.v2_cognitive_ir_role_specificity import (
    ARCHITECTURE_CONSEQUENCE,
    CATEGORY_CONTEXT_KEY,
    CATEGORY_FORBIDDEN_ROLE_TERMS,
    CATEGORY_RELATION_KEYS,
    CATEGORY_SURFACE,
    CONFIRMATORY_CONTRASTS,
    DESCRIPTIVE_ONLY_CONTRAST,
    FAMILY_COUNT,
    FORBIDDEN_RESCUE_COUNTS,
    FUNCTION_CONTEXT_KEY,
    FUNCTION_RELATION_KEYS,
    FUNCTION_SURFACE,
    INPUT_TOKEN_REQUESTS,
    MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS,
    OPAQUE_CONTEXT_KEY,
    OPAQUE_RELATION_KEYS,
    OPAQUE_SURFACE,
    OUTPUT_FIELDS,
    PHYSICAL_EXECUTION_AUTHORIZED,
    SEMANTIC_COMPLETIONS,
    SURFACES,
    PairedTable,
    RoleSpecificityError,
    build_reconstruction_messages,
    classify_result,
    confirmatory_analysis,
    decode_surface,
    derive_family_seed,
    descriptive_function_vs_opaque,
    exact_two_sided_sign_p,
    historical_family_seeds,
    holm_bonferroni,
    measurement_admitted,
    paired_accuracy_difference,
    parse_wire_shape,
    prepare_synthetic_mechanism_control,
    preregistered_seeds,
    response_format,
    score_reconstruction,
    semantic_call_plan,
    validate_repository_binding,
)


EXPECTED_SEEDS = (
    1354493995435995612,
    9833615014476118996,
    3142346486847826547,
    9625589539731917173,
    17119089084889279077,
    14055896410855990078,
    14302460460329278576,
    13551954365116518689,
    3425367760729974771,
    1165152704257406843,
    17714910313158651467,
    11200894301460465028,
    3673137915158134533,
    10326751659384825141,
    11973988930426162551,
    17805596145874618418,
    1331810321505728738,
    13634674195613174190,
    17805847430786968542,
    16954491509574216495,
    11567083099892448085,
    2426411893906039076,
    2330927249830779756,
    6534530795745639562,
)


def _truth() -> dict[str, object]:
    return {
        "operation": "affine_permutation",
        "permutation": [2, 0, 3, 1],
        "offsets": [1, 2, 0, 3],
        "modulus": 10,
        "provenance_handles": ["src-a", "src-b"],
    }


def _json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _admitted(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "semantic_equal_families": 24,
        "provider_attempts": 72,
        "provider_completions": 72,
        "wire_shape_valid": 72,
        "input_count_attempts": 144,
        "input_count_completions": 144,
        "rescue_counts": dict(FORBIDDEN_RESCUE_COUNTS),
        "truncation_failures": 0,
        "identity_checks_passed": True,
    }
    values.update(overrides)
    return values


def _one_direction_discordants(count: int) -> list[tuple[bool, bool]]:
    return [(True, False)] * count + [(False, False)] * (
        FAMILY_COUNT - count
    )


def test_seed_rule_is_exact_unique_and_fresh_against_all_lx1_history() -> None:
    assert preregistered_seeds() == EXPECTED_SEEDS
    assert tuple(derive_family_seed(index) for index in range(24)) == EXPECTED_SEEDS
    assert len(set(EXPECTED_SEEDS)) == FAMILY_COUNT
    assert set(EXPECTED_SEEDS).isdisjoint(historical_family_seeds())
    with pytest.raises(RoleSpecificityError):
        derive_family_seed(-1)
    with pytest.raises(RoleSpecificityError):
        derive_family_seed(24)
    with pytest.raises(RoleSpecificityError):
        derive_family_seed(True)


def test_synthetic_helper_rejects_every_preregistered_seed() -> None:
    for seed in EXPECTED_SEEDS:
        with pytest.raises(RoleSpecificityError):
            prepare_synthetic_mechanism_control(seed, _truth())

    control = prepare_synthetic_mechanism_control(1, _truth())
    assert control.canonical_truth == _truth()
    assert control.semantic_digest
    assert len(set(control.semantic_digest_by_surface.values())) == 1


def test_three_surfaces_are_distinct_semantically_identical_and_order_matched() -> None:
    control = prepare_synthetic_mechanism_control(1, _truth())
    assert tuple(control.serialized_by_surface) == SURFACES
    assert len(set(control.serialized_by_surface.values())) == 3

    payloads = {
        surface: json.loads(control.serialized_by_surface[surface])
        for surface in SURFACES
    }
    for surface, payload in payloads.items():
        assert decode_surface(surface, payload) == _truth()
        assert list(payload) == ["context", "relation"]

    function = payloads[FUNCTION_SURFACE]
    category = payloads[CATEGORY_SURFACE]
    opaque = payloads[OPAQUE_SURFACE]

    assert list(function["context"]) == [FUNCTION_CONTEXT_KEY]
    assert list(function["relation"]) == list(FUNCTION_RELATION_KEYS)
    assert list(category["context"]) == [CATEGORY_CONTEXT_KEY]
    assert list(category["relation"]) == list(CATEGORY_RELATION_KEYS)
    assert list(opaque["context"]) == [OPAQUE_CONTEXT_KEY]
    assert list(opaque["relation"]) == list(OPAQUE_RELATION_KEYS)

    assert list(function["relation"].values()) == [
        _truth()["operation"],
        _truth()["permutation"],
        _truth()["offsets"],
        _truth()["modulus"],
    ]
    assert list(category["relation"].values()) == list(function["relation"].values())
    assert list(opaque["relation"].values()) == list(function["relation"].values())


def test_frozen_key_vocabularies_are_role_safe() -> None:
    assert FUNCTION_CONTEXT_KEY == "source_handles"
    assert FUNCTION_RELATION_KEYS == (
        "transform_kind",
        "index_reordering",
        "additive_shifts",
        "modular_divisor",
    )
    assert CATEGORY_CONTEXT_KEY == "text_list"
    assert CATEGORY_RELATION_KEYS == (
        "text_value",
        "integer_list_one",
        "integer_list_two",
        "integer_value",
    )
    assert OPAQUE_CONTEXT_KEY == "q0"
    assert OPAQUE_RELATION_KEYS == ("q1", "q2", "q3", "q4")

    all_input_keys = {
        FUNCTION_CONTEXT_KEY,
        *FUNCTION_RELATION_KEYS,
        CATEGORY_CONTEXT_KEY,
        *CATEGORY_RELATION_KEYS,
        OPAQUE_CONTEXT_KEY,
        *OPAQUE_RELATION_KEYS,
    }
    assert all_input_keys.isdisjoint(OUTPUT_FIELDS)

    for key in (CATEGORY_CONTEXT_KEY, *CATEGORY_RELATION_KEYS):
        assert all(term not in key.lower() for term in CATEGORY_FORBIDDEN_ROLE_TERMS)


def test_model_instruction_is_surface_symmetric_and_has_no_mapping_legend() -> None:
    control = prepare_synthetic_mechanism_control(1, _truth())
    messages = {
        surface: build_reconstruction_messages(
            control.serialized_by_surface[surface]
        )
        for surface in SURFACES
    }
    systems = {surface: value[0]["content"] for surface, value in messages.items()}
    assert len(set(systems.values())) == 1

    system_text = next(iter(systems.values())).lower()
    for forbidden in (
        "source_handles",
        "transform_kind",
        "index_reordering",
        "additive_shifts",
        "modular_divisor",
        "text_list",
        "text_value",
        "integer_list_one",
        "integer_list_two",
        "integer_value",
        "q0 means",
        "q1 means",
        "category descriptive",
        "opaque",
    ):
        assert forbidden not in system_text


def test_response_format_is_identical_strict_wire_shape_only() -> None:
    strict_format = response_format()
    assert strict_format["type"] == "json_schema"
    json_schema = strict_format["json_schema"]
    assert json_schema["strict"] is True
    schema = json_schema["schema"]
    assert set(schema["required"]) == set(OUTPUT_FIELDS)
    assert schema["additionalProperties"] is False

    encoded = json.dumps(strict_format, sort_keys=True)
    for forbidden in (
        "uniqueItems",
        '"minimum"',
        '"maximum"',
        '"const"',
        '"enum"',
        "source_handles",
        "transform_kind",
        "text_list",
        "integer_list_one",
        '"q1"',
    ):
        assert forbidden not in encoded


def test_nonbijective_permutation_remains_wire_valid_domain_invalid() -> None:
    wrong = {**_truth(), "permutation": [0, 0, 0, 0]}
    parsed = parse_wire_shape(_json(wrong))
    assert parsed["permutation"] == [0, 0, 0, 0]

    score = score_reconstruction(_json(wrong), _truth())
    assert score.wire_shape_valid
    assert not score.semantic_domain_valid
    assert not score.full_payload_exact
    assert not score.core_rule_exact
    assert score.provenance_exact


def test_exact_payload_is_wire_domain_and_semantically_exact() -> None:
    score = score_reconstruction(_json(_truth()), _truth())
    assert score.wire_shape_valid
    assert score.semantic_domain_valid
    assert score.full_payload_exact
    assert score.core_rule_exact
    assert score.provenance_exact


def test_call_ledger_and_zero_rescue_contract_are_exact() -> None:
    plan = semantic_call_plan()
    assert len(plan) == SEMANTIC_COMPLETIONS == 72
    assert len({(index, seed) for index, seed, _ in plan}) == FAMILY_COUNT == 24
    for index, seed in enumerate(EXPECTED_SEEDS):
        assert [(i, s, surface) for i, s, surface in plan if i == index] == [
            (index, seed, FUNCTION_SURFACE),
            (index, seed, CATEGORY_SURFACE),
            (index, seed, OPAQUE_SURFACE),
        ]

    assert INPUT_TOKEN_REQUESTS == 144
    assert MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS == 2
    assert all(value == 0 for value in FORBIDDEN_RESCUE_COUNTS.values())
    assert not PHYSICAL_EXECUTION_AUTHORIZED
    assert ARCHITECTURE_CONSEQUENCE == "NONE"


def test_measurement_admission_uses_wire_not_domain_success() -> None:
    assert measurement_admitted(**_admitted())

    domain_wrong = score_reconstruction(
        _json({**_truth(), "permutation": [0, 0, 0, 0]}),
        _truth(),
    )
    assert domain_wrong.wire_shape_valid
    assert not domain_wrong.semantic_domain_valid
    assert measurement_admitted(**_admitted())

    for key, value in (
        ("semantic_equal_families", 23),
        ("provider_attempts", 71),
        ("provider_completions", 71),
        ("wire_shape_valid", 71),
        ("input_count_attempts", 143),
        ("input_count_completions", 143),
        ("truncation_failures", 1),
        ("identity_checks_passed", False),
    ):
        assert not measurement_admitted(**_admitted(**{key: value}))

    rescued = dict(FORBIDDEN_RESCUE_COUNTS)
    rescued["fallback"] = 1
    assert not measurement_admitted(**_admitted(rescue_counts=rescued))


def test_exact_paired_statistics_are_direction_symmetric() -> None:
    table = PairedTable(
        both_correct=9,
        left_only=4,
        right_only=2,
        both_wrong=9,
    )
    assert exact_two_sided_sign_p(table) == pytest.approx(0.6875)
    assert paired_accuracy_difference(table) == pytest.approx(2 / 24)

    reverse = PairedTable(
        both_correct=9,
        left_only=2,
        right_only=4,
        both_wrong=9,
    )
    assert exact_two_sided_sign_p(reverse) == pytest.approx(0.6875)
    assert paired_accuracy_difference(reverse) == pytest.approx(-2 / 24)


def test_holm_correction_supports_reject_none_one_or_both() -> None:
    h1, h2 = CONFIRMATORY_CONTRASTS
    none = holm_bonferroni({h1: 0.25, h2: 0.5})
    assert not none[h1][1]
    assert not none[h2][1]

    one = holm_bonferroni({h1: 0.015625, h2: 0.25})
    assert one[h1][0] == pytest.approx(0.03125)
    assert one[h1][1]
    assert not one[h2][1]

    both = holm_bonferroni({h1: 0.015625, h2: 0.015625})
    assert both[h1][1]
    assert both[h2][1]


def test_confirmatory_analysis_exposes_only_h1_h2_and_classifies() -> None:
    role_only = confirmatory_analysis(
        h1_function_vs_category=_one_direction_discordants(7),
        h2_category_vs_opaque=_one_direction_discordants(3),
    )
    assert tuple(role_only) == CONFIRMATORY_CONTRASTS
    assert (
        classify_result(role_only).classification
        == "ROLE_FUNCTION_SPECIFICITY_DIFFERENCE_DETECTED"
    )

    lexical_only = confirmatory_analysis(
        h1_function_vs_category=_one_direction_discordants(3),
        h2_category_vs_opaque=_one_direction_discordants(7),
    )
    assert (
        classify_result(lexical_only).classification
        == "GENERIC_LEXICAL_TRANSPARENCY_DIFFERENCE_DETECTED"
    )

    both = confirmatory_analysis(
        h1_function_vs_category=_one_direction_discordants(7),
        h2_category_vs_opaque=_one_direction_discordants(7),
    )
    assert (
        classify_result(both).classification
        == "MULTIPLE_ROLE_ACCESSIBILITY_COMPONENTS_DETECTED"
    )


def test_function_vs_opaque_is_descriptive_only_with_no_p_value_surface() -> None:
    table = descriptive_function_vs_opaque(_one_direction_discordants(8))
    assert isinstance(table, PairedTable)
    assert table.left_only == 8
    assert DESCRIPTIVE_ONLY_CONTRAST == "F_VS_O_DESCRIPTIVE_ONLY"
    assert not hasattr(table, "raw_p_value")


def test_non_significance_is_underdetermined_not_equivalence() -> None:
    contrasts = confirmatory_analysis(
        h1_function_vs_category=_one_direction_discordants(3),
        h2_category_vs_opaque=_one_direction_discordants(3),
    )
    verdict = classify_result(contrasts)
    assert (
        verdict.classification
        == "NO_DECLARED_ROLE_SPECIFICITY_GAP_DETECTED_AT_THIS_RESOLUTION"
    )
    assert verdict.statistical_status == "UNDERDETERMINED"
    assert verdict.citable_for_accessibility_claim


def test_fail_closed_terminal_classes_preserve_architecture_none() -> None:
    invalid = classify_result(None, pre_execution_valid=False)
    assert invalid.classification == "INVALID_BEFORE_PHYSICAL_EXECUTION"
    assert invalid.statistical_status == "INVALID"
    assert invalid.architecture_consequence == "NONE"

    failed = classify_result(
        None,
        protocol_failure_after_spend=True,
        measurement_passed=False,
    )
    assert (
        failed.classification
        == "MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND"
    )
    assert failed.statistical_status == "UNDERDETERMINED"
    assert not failed.citable_for_accessibility_claim


def test_repository_binding_validation_is_zero_gpu_and_complete() -> None:
    validate_repository_binding()
