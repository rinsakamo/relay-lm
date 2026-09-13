from __future__ import annotations

import json

import pytest

from relaylm.v2_cognitive_ir_semantic_role_binding import (
    ARCHITECTURE_CONSEQUENCE,
    CONFIRMATORY_CONTRASTS,
    FAMILY_COUNT,
    FORBIDDEN_RESCUE_COUNTS,
    INPUT_TOKEN_REQUESTS,
    MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS,
    OPAQUE_SURFACE,
    PHYSICAL_EXECUTION_AUTHORIZED,
    ROLE_EXPLICIT_SURFACE,
    SEMANTIC_COMPLETIONS,
    SURFACES,
    TYPED_SURFACE,
    PairedTable,
    SemanticRoleBindingError,
    build_reconstruction_messages,
    classify_result,
    confirmatory_analysis,
    decode_surface,
    derive_family_seed,
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
    15654331814022513571,
    4130833101943602070,
    3622916488914515460,
    4273720248427486428,
    18160668007000388634,
    14843250857192077735,
    11088695480028396009,
    11414254182996657536,
    12477077697718252131,
    11056450858167514713,
    1800839104214250888,
    848683155329986760,
    12483774499539918009,
    10642988624378895427,
    8735886895768433425,
    17128575628493260920,
    2142049872766640267,
    9379871644288854973,
    12570768637527374551,
    8203497307916611840,
    18393899065632597984,
    4979651136195675617,
    4841571958558377071,
    9290604684278747856,
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
    return [(True, False)] * count + [(False, False)] * (FAMILY_COUNT - count)


def test_seed_rule_is_exact_unique_and_fresh_against_current_history() -> None:
    assert preregistered_seeds() == EXPECTED_SEEDS
    assert tuple(derive_family_seed(index) for index in range(24)) == EXPECTED_SEEDS
    assert len(set(EXPECTED_SEEDS)) == FAMILY_COUNT
    assert set(EXPECTED_SEEDS).isdisjoint(historical_family_seeds())
    with pytest.raises(SemanticRoleBindingError):
        derive_family_seed(-1)
    with pytest.raises(SemanticRoleBindingError):
        derive_family_seed(24)
    with pytest.raises(SemanticRoleBindingError):
        derive_family_seed(True)


def test_synthetic_helper_rejects_every_preregistered_seed() -> None:
    for seed in EXPECTED_SEEDS:
        with pytest.raises(SemanticRoleBindingError):
            prepare_synthetic_mechanism_control(seed, _truth())

    control = prepare_synthetic_mechanism_control(1, _truth())
    assert control.canonical_truth == _truth()
    assert control.semantic_digest


def test_three_surfaces_are_literal_distinct_but_semantically_identical() -> None:
    control = prepare_synthetic_mechanism_control(1, _truth())
    assert tuple(control.serialized_by_surface) == SURFACES
    assert len(set(control.serialized_by_surface.values())) == 3

    payloads = {
        surface: json.loads(control.serialized_by_surface[surface])
        for surface in SURFACES
    }
    for surface, payload in payloads.items():
        assert decode_surface(surface, payload) == _truth()

    typed = payloads[TYPED_SURFACE]
    explicit = payloads[ROLE_EXPLICIT_SURFACE]
    opaque = payloads[OPAQUE_SURFACE]

    assert set(typed) == {"memory", "structure"}
    assert set(explicit) == {"context", "relation"}
    assert set(explicit["context"]) == {"provenance_handles"}
    assert set(explicit["relation"]) == {
        "operation",
        "permutation",
        "offsets",
        "modulus",
    }
    explicit_text = control.serialized_by_surface[ROLE_EXPLICIT_SURFACE].lower()
    assert '"memory"' not in explicit_text
    assert '"structure"' not in explicit_text
    assert "crystal" not in explicit_text

    assert set(opaque["context"]) == {"refs"}
    assert set(opaque["relation"]) == {"kind", "a", "b", "n"}


def test_model_instruction_is_surface_symmetric_and_contains_no_decoder_legend() -> None:
    control = prepare_synthetic_mechanism_control(1, _truth())
    messages = {
        surface: build_reconstruction_messages(control.serialized_by_surface[surface])
        for surface in SURFACES
    }
    systems = {surface: value[0] for surface, value in messages.items()}
    assert len({entry["content"] for entry in systems.values()}) == 1

    system_text = next(iter(systems.values()))["content"].lower()
    for forbidden in (
        "memory",
        "structure",
        "context",
        "relation",
        "a means",
        "b means",
        "typed",
        "opaque",
    ):
        assert forbidden not in system_text

    user_texts = {value[1]["content"] for value in messages.values()}
    assert len(user_texts) == 3


def test_response_format_is_strict_wire_shape_only() -> None:
    strict_format = response_format()
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
    for forbidden in (
        "uniqueItems",
        '"minimum"',
        '"maximum"',
        '"const"',
        '"enum"',
        "P4_MEMORY_PLUS_STRUCTURE",
        "GENERIC_EQUAL_INFORMATION",
        "src-a",
    ):
        assert forbidden not in encoded


@pytest.mark.parametrize(
    "content",
    [
        "",
        "```json\n{}\n```",
        "prefix " + _json(_truth()),
        "[]",
        _json({key: value for key, value in _truth().items() if key != "modulus"}),
        _json({**_truth(), "extra": 1}),
        _json({**_truth(), "operation": 3}),
        _json({**_truth(), "permutation": [0, 1, 2]}),
        _json({**_truth(), "offsets": [0, 1, 2, "3"]}),
        _json({**_truth(), "modulus": True}),
        _json({**_truth(), "provenance_handles": []}),
        (
            '{"operation":"affine_permutation","operation":"other",'
            '"permutation":[0,1,2,3],"offsets":[0,1,2,3],'
            '"modulus":10,"provenance_handles":["p"]}'
        ),
        (
            '{"operation":"affine_permutation","permutation":[0,1,2,3],'
            '"offsets":[0,1,2,3],"modulus":NaN,'
            '"provenance_handles":["p"]}'
        ),
    ],
)
def test_wire_parser_rejects_non_wire_shape_material(content: str) -> None:
    with pytest.raises(SemanticRoleBindingError):
        parse_wire_shape(content)


def test_nonbijective_permutation_is_wire_valid_but_semantic_wrong() -> None:
    wrong = {
        **_truth(),
        "permutation": [0, 0, 0, 0],
    }
    parsed = parse_wire_shape(_json(wrong))
    assert parsed["permutation"] == [0, 0, 0, 0]

    score = score_reconstruction(_json(wrong), _truth())
    assert score.wire_shape_valid
    assert not score.semantic_domain_valid
    assert not score.full_payload_exact
    assert not score.core_rule_exact
    assert score.provenance_exact
    assert score.failure_reason == "semantic_domain: invalid permutation"


def test_valid_but_wrong_semantics_remain_scientific_outcomes() -> None:
    wrong = {
        **_truth(),
        "permutation": [0, 1, 2, 3],
        "offsets": [3, 2, 1, 0],
    }
    score = score_reconstruction(_json(wrong), _truth())
    assert score.wire_shape_valid
    assert score.semantic_domain_valid
    assert not score.full_payload_exact
    assert not score.core_rule_exact
    assert score.provenance_exact
    assert score.failure_reason == "core_mismatch: permutation"


def test_exact_payload_is_wire_domain_and_semantically_exact() -> None:
    score = score_reconstruction(_json(_truth()), _truth())
    assert score.wire_shape_valid
    assert score.semantic_domain_valid
    assert score.full_payload_exact
    assert score.core_rule_exact
    assert score.provenance_exact
    assert score.failure_reason is None


def test_call_ledger_and_zero_rescue_contract_are_exact() -> None:
    plan = semantic_call_plan()
    assert len(plan) == SEMANTIC_COMPLETIONS == 72
    assert len({(index, seed) for index, seed, _ in plan}) == FAMILY_COUNT == 24
    for index, seed in enumerate(EXPECTED_SEEDS):
        assert [(i, s, surface) for i, s, surface in plan if i == index] == [
            (index, seed, TYPED_SURFACE),
            (index, seed, ROLE_EXPLICIT_SURFACE),
            (index, seed, OPAQUE_SURFACE),
        ]

    assert INPUT_TOKEN_REQUESTS == 144
    assert MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS == 2
    assert all(value == 0 for value in FORBIDDEN_RESCUE_COUNTS.values())
    assert not PHYSICAL_EXECUTION_AUTHORIZED
    assert ARCHITECTURE_CONSEQUENCE == "NONE"


def test_measurement_admission_uses_wire_not_semantic_domain_success() -> None:
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


def test_exact_paired_table_and_accuracy_difference_are_direction_symmetric() -> None:
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


def test_confirmatory_analysis_exposes_exactly_h1_h2_and_classifies() -> None:
    role_only = confirmatory_analysis(
        h1_role_explicit_vs_opaque=_one_direction_discordants(7),
        h2_typed_vs_role_explicit=_one_direction_discordants(3),
    )
    assert tuple(role_only) == CONFIRMATORY_CONTRASTS
    assert role_only[CONFIRMATORY_CONTRASTS[0]].raw_p_value == pytest.approx(
        0.015625
    )
    assert role_only[CONFIRMATORY_CONTRASTS[0]].holm_reject
    assert not role_only[CONFIRMATORY_CONTRASTS[1]].holm_reject
    verdict = classify_result(role_only)
    assert verdict.classification == "ROLE_BINDING_ACCESSIBILITY_DIFFERENCE_DETECTED"
    assert verdict.citable_for_accessibility_claim

    both = confirmatory_analysis(
        h1_role_explicit_vs_opaque=_one_direction_discordants(7),
        h2_typed_vs_role_explicit=_one_direction_discordants(7),
    )
    assert (
        classify_result(both).classification
        == "MULTIPLE_SURFACE_ACCESSIBILITY_DIFFERENCES_DETECTED"
    )


def test_non_significance_is_underdetermined_not_equivalence() -> None:
    contrasts = confirmatory_analysis(
        h1_role_explicit_vs_opaque=_one_direction_discordants(3),
        h2_typed_vs_role_explicit=_one_direction_discordants(3),
    )
    verdict = classify_result(contrasts)
    assert verdict.classification == "NO_DECLARED_SURFACE_GAP_DETECTED_AT_THIS_RESOLUTION"
    assert verdict.statistical_status == "UNDERDETERMINED"
    assert verdict.citable_for_accessibility_claim


def test_fail_closed_terminal_classes_preserve_architecture_none() -> None:
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


def test_repository_binding_is_zero_gpu_and_self_consistent() -> None:
    validate_repository_binding()
