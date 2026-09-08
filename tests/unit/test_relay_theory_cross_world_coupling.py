from fractions import Fraction

import pytest

from tools.relay_theory_cross_world_coupling import (
    ResponseModel,
    ResponseType,
    affine_soft_signature,
    behavior_equivalent,
    behavior_partition,
    counterfactual_equality_probability,
    downstream_copy_counterfactual_joint,
    downstream_copy_single_world_signature,
    flip_response_model,
    hard_single_world_signature,
    independent_world_counterfactual_joint,
    invariant_response_model,
    observational_law,
    partition_is_representative_independent,
    potential_outcome_marginal,
    rename_response_type_labels,
    run_cross_world_coupling_comparison,
    same_unit_counterfactual_joint,
    soft_intervention_law,
    validate_response_model,
)


def test_cross_world_coupling_comparison_passes_with_strict_booleans() -> None:
    results = run_cross_world_coupling_comparison()

    assert [result.name for result in results] == [
        "OBSERVATIONAL_LAW_MATCHES",
        "COMPLETE_BINARY_HARD_INTERVENTION_FAMILY_MATCHES",
        "ENTIRE_BERNOULLI_SOFT_INTERVENTION_FAMILY_MATCHES_SYMBOLICALLY",
        "POTENTIAL_OUTCOME_MARGINALS_MATCH",
        "SAME_UNIT_CROSS_WORLD_COUPLING_DIFFERS",
        "UNIT_ALIGNMENT_IS_OPERATIONAL_STRUCTURE",
        "COUPLING_IS_GAUGE_ONLY_IN_SINGLE_WORLD_FRAME",
        "RESPONSE_TYPE_LABELS_ARE_GAUGE",
        "DOWNSTREAM_CONTEXT_PRESERVES_FRAME_RELATIVE_DISTINCTION",
        "FRAME_RELATIVE_QUOTIENTS_ARE_REPRESENTATIVE_INDEPENDENT",
    ]
    assert all(type(result.passed) is bool for result in results)
    assert all(result.passed for result in results)


def test_observational_and_complete_hard_single_world_interfaces_match() -> None:
    invariant = invariant_response_model()
    flip = flip_response_model()

    assert observational_law(invariant) == observational_law(flip)
    assert hard_single_world_signature(invariant) == hard_single_world_signature(flip)


def test_soft_intervention_family_matches_symbolically_for_x_and_y() -> None:
    invariant = invariant_response_model()
    flip = flip_response_model()

    assert affine_soft_signature(invariant, "X") == affine_soft_signature(flip, "X")
    assert affine_soft_signature(invariant, "Y") == affine_soft_signature(flip, "Y")

    for target in ("X", "Y"):
        for q in (Fraction(1, 7), Fraction(2, 5), Fraction(11, 13)):
            assert soft_intervention_law(invariant, target, q) == soft_intervention_law(
                flip, target, q
            )


def test_potential_outcome_marginals_match_but_same_unit_joint_differs() -> None:
    invariant = invariant_response_model()
    flip = flip_response_model()

    assert potential_outcome_marginal(invariant, "0") == potential_outcome_marginal(
        flip, "0"
    )
    assert potential_outcome_marginal(invariant, "1") == potential_outcome_marginal(
        flip, "1"
    )
    assert same_unit_counterfactual_joint(invariant) == (
        (("0", "0"), Fraction(1, 2)),
        (("1", "1"), Fraction(1, 2)),
    )
    assert same_unit_counterfactual_joint(flip) == (
        (("0", "1"), Fraction(1, 2)),
        (("1", "0"), Fraction(1, 2)),
    )
    assert counterfactual_equality_probability(invariant) == 1
    assert counterfactual_equality_probability(flip) == 0


def test_redrawing_response_type_independently_is_not_same_unit_alignment() -> None:
    invariant = invariant_response_model()
    flip = flip_response_model()

    fresh_invariant = independent_world_counterfactual_joint(invariant)
    fresh_flip = independent_world_counterfactual_joint(flip)

    assert fresh_invariant == fresh_flip
    assert fresh_invariant == (
        (("0", "0"), Fraction(1, 4)),
        (("0", "1"), Fraction(1, 4)),
        (("1", "0"), Fraction(1, 4)),
        (("1", "1"), Fraction(1, 4)),
    )
    assert fresh_invariant != same_unit_counterfactual_joint(invariant)
    assert fresh_flip != same_unit_counterfactual_joint(flip)


def test_equivalence_is_frame_relative() -> None:
    invariant = invariant_response_model()
    flip = flip_response_model()

    assert behavior_equivalent(invariant, flip, "single_world")
    assert not behavior_equivalent(invariant, flip, "cross_world")


def test_response_type_labels_are_gauge_even_in_cross_world_frame() -> None:
    invariant = invariant_response_model()
    renamed = rename_response_type_labels(
        invariant,
        {"u0": "alpha", "u1": "beta"},
        name="renamed",
    )

    assert behavior_equivalent(invariant, renamed, "cross_world")


def test_downstream_copy_preserves_single_world_equivalence_and_cross_world_split() -> None:
    invariant = invariant_response_model()
    flip = flip_response_model()

    assert downstream_copy_single_world_signature(
        invariant
    ) == downstream_copy_single_world_signature(flip)
    assert downstream_copy_counterfactual_joint(
        invariant
    ) != downstream_copy_counterfactual_joint(flip)


def test_single_and_cross_world_partitions_are_representative_independent() -> None:
    invariant = invariant_response_model()
    renamed = rename_response_type_labels(
        invariant,
        {"u0": "left", "u1": "right"},
        name="renamed",
    )
    flip = flip_response_model()
    models = (invariant, renamed, flip)

    single = behavior_partition(models, "single_world")
    cross = behavior_partition(models, "cross_world")

    assert single["invariant"] == single["renamed"] == single["flip"]
    assert cross["invariant"] == cross["renamed"]
    assert cross["invariant"] != cross["flip"]
    assert partition_is_representative_independent(models, single, "single_world")
    assert partition_is_representative_independent(models, cross, "cross_world")


def test_response_model_requires_exact_normalized_fraction_mass() -> None:
    bad_float = ResponseModel(
        "float",
        ((ResponseType("u", "0", "0"), 1.0),),  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="fractions.Fraction"):
        validate_response_model(bad_float)

    bad_total = ResponseModel(
        "bad-total",
        (
            (ResponseType("u0", "0", "0"), Fraction(1, 3)),
            (ResponseType("u1", "1", "1"), Fraction(1, 3)),
        ),
    )
    with pytest.raises(ValueError, match="sum exactly to 1"):
        validate_response_model(bad_total)


def test_unknown_frame_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown frame"):
        behavior_equivalent(
            invariant_response_model(),
            flip_response_model(),
            "multiverse",  # type: ignore[arg-type]
        )
