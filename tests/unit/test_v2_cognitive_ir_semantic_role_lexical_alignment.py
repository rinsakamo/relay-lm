from __future__ import annotations

import json

import pytest

from relaylm.v2_cognitive_ir_semantic_role_lexical_alignment import (
    ARCHITECTURE_CONSEQUENCE,
    CONFIRMATORY_CONTRASTS,
    DESCRIPTIVE_CONTEXT_KEY,
    DESCRIPTIVE_ONLY_CONTRAST,
    DESCRIPTIVE_RELATION_KEYS,
    DESCRIPTIVE_SURFACE,
    EXACT_LEXEME_SURFACE,
    FAMILY_COUNT,
    FORBIDDEN_RESCUE_COUNTS,
    INPUT_TOKEN_REQUESTS,
    MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS,
    OPAQUE_SURFACE,
    OUTPUT_FIELDS,
    PHYSICAL_EXECUTION_AUTHORIZED,
    SEMANTIC_COMPLETIONS,
    SURFACES,
    PairedTable,
    SemanticRoleLexicalAlignmentError,
    build_reconstruction_messages,
    classify_result,
    confirmatory_analysis,
    decode_surface,
    derive_family_seed,
    descriptive_exact_vs_opaque,
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
    5830225207128048464,
    16911302777818129912,
    13980793607900472639,
    16840875553335755334,
    14787475204086134501,
    548846918887326884,
    1276626517016150959,
    2290049754807696392,
    8183587323721628938,
    13081739101025839890,
    10454267136968129134,
    12243880576631847139,
    941008711331174497,
    660071743818553173,
    4128876956088511452,
    16235408025481447638,
    14023011150293071491,
    12269094734565832815,
    5116114782399719593,
    6301321863697364414,
    16698929620998923371,
    2396048220916957363,
    17909344098928306057,
    3041208795719742410,
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


def test_seed_rule_is_exact_unique_and_fresh_against_all_rb1_history() -> None:
    assert preregistered_seeds() == EXPECTED_SEEDS
    assert tuple(derive_family_seed(index) for index in range(24)) == EXPECTED_SEEDS
    assert len(set(EXPECTED_SEEDS)) == FAMILY_COUNT
    assert set(EXPECTED_SEEDS).isdisjoint(historical_family_seeds())
    with pytest.raises(SemanticRoleLexicalAlignmentError):
        derive_family_seed(-1)
    with pytest.raises(SemanticRoleLexicalAlignmentError):
        derive_family_seed(24)
    with pytest.raises(SemanticRoleLexicalAlignmentError):
        derive_family_seed(True)


def test_synthetic_helper_rejects_every_preregistered_seed() -> None:
    for seed in EXPECTED_SEEDS:
        with pytest.raises(SemanticRoleLexicalAlignmentError):
            prepare_synthetic_mechanism_control(seed, _truth())

    control = prepare_synthetic_mechanism_control(1, _truth())
    assert control.canonical_truth == _truth()
    assert control.semantic_digest
    assert len(set(control.semantic_digest_by_surface.values())) == 1


def test_three_neutral_surfaces_are_distinct_but_semantically_identical() -> None:
    control = prepare_synthetic_mechanism_control(1, _truth())
    assert tuple(control.serialized_by_surface) == SURFACES
    assert len(set(control.serialized_by_surface.values())) == 3

    payloads = {
        surface: json.loads(control.serialized_by_surface[surface])
        for surface in SURFACES
    }
    for surface, payload in payloads.items():
        assert decode_surface(surface, payload) == _truth()

    exact = payloads[EXACT_LEXEME_SURFACE]
    descriptive = payloads[DESCRIPTIVE_SURFACE]
    opaque = payloads[OPAQUE_SURFACE]

    assert set(exact) == {"context", "relation"}
    assert set(exact["context"]) == {"provenance_handles"}
    assert set(exact["relation"]) == {
        "operation",
        "permutation",
        "offsets",
        "modulus",
    }

    assert set(descriptive) == {"context", "relation"}
    assert set(descriptive["context"]) == {DESCRIPTIVE_CONTEXT_KEY}
    assert set(descriptive["relation"]) == set(DESCRIPTIVE_RELATION_KEYS)
    descriptive_keys = set(descriptive["context"]) | set(descriptive["relation"])
    assert descriptive_keys.isdisjoint(OUTPUT_FIELDS)

    assert set(opaque["context"]) == {"refs"}
    assert set(opaque["relation"]) == {"kind", "a", "b", "n"}


def test_descriptive_surface_has_frozen_nonlexical_role_names() -> None:
    control = prepare_synthetic_mechanism_control(1, _truth())
    descriptive = json.loads(control.serialized_by_surface[DESCRIPTIVE_SURFACE])
    assert descriptive == {
        "context": {"source_handles": ["src-a", "src-b"]},
        "relation": {
            "transform_kind": "affine_permutation",
            "index_reordering": [2, 0, 3, 1],
            "additive_shifts": [1, 2, 0, 3],
            "modular_divisor": 10,
        },
    }


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
        "a means",
        "b means",
        "exact lexeme",
        "descriptive nonlexical",
        "opaque",
    ):
        assert forbidden not in system_text

    user_texts = {value[1]["content"] for value in messages.values()}
    assert len(user_texts) == 3


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
        "index_reordering",
        "additive_shifts",
        "modular_divisor",
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
    assert score.failure_reason == "semantic_domain: invalid permutation"


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
            (index, seed, EXACT_LEXEME_SURFACE),
            (index, seed, DESCRIPTIVE_SURFACE),
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
    lexical_only = confirmatory_analysis(
        h1_exact_vs_descriptive=_one_direction_discordants(7),
        h2_descriptive_vs_opaque=_one_direction_discordants(3),
    )
    assert tuple(lexical_only) == CONFIRMATORY_CONTRASTS
    assert lexical_only[CONFIRMATORY_CONTRASTS[0]].holm_reject
    assert not lexical_only[CONFIRMATORY_CONTRASTS[1]].holm_reject
    assert (
        classify_result(lexical_only).classification
        == "LEXICAL_FORM_ACCESSIBILITY_DIFFERENCE_DETECTED"
    )

    role_only = confirmatory_analysis(
        h1_exact_vs_descriptive=_one_direction_discordants(3),
        h2_descriptive_vs_opaque=_one_direction_discordants(7),
    )
    assert (
        classify_result(role_only).classification
        == "ROLE_DESCRIPTION_ACCESSIBILITY_DIFFERENCE_DETECTED"
    )

    both = confirmatory_analysis(
        h1_exact_vs_descriptive=_one_direction_discordants(7),
        h2_descriptive_vs_opaque=_one_direction_discordants(7),
    )
    assert (
        classify_result(both).classification
        == "MULTIPLE_LEXICAL_ROLE_ACCESSIBILITY_DIFFERENCES_DETECTED"
    )


def test_exact_vs_opaque_is_descriptive_only_with_no_p_value_surface() -> None:
    table = descriptive_exact_vs_opaque(_one_direction_discordants(8))
    assert isinstance(table, PairedTable)
    assert table.left_only == 8
    assert DESCRIPTIVE_ONLY_CONTRAST == "E_VS_O_DESCRIPTIVE_ONLY"
    assert not hasattr(table, "raw_p_value")


def test_non_significance_is_underdetermined_not_equivalence() -> None:
    contrasts = confirmatory_analysis(
        h1_exact_vs_descriptive=_one_direction_discordants(3),
        h2_descriptive_vs_opaque=_one_direction_discordants(3),
    )
    verdict = classify_result(contrasts)
    assert (
        verdict.classification
        == "NO_DECLARED_LEXICAL_ROLE_GAP_DETECTED_AT_THIS_RESOLUTION"
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
    assert failed.architecture_consequence == "NONE"


def test_repository_binding_is_self_consistent_and_zero_physical() -> None:
    validate_repository_binding()
