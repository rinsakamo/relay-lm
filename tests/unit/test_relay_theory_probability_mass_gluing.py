from fractions import Fraction
from itertools import product

import pytest

from tools.relay_theory_local_global_compatibility import (
    LocalFamily,
    canonical_pair_law,
    overlap_consistent,
    supported_global_assignments,
    verify_global_witness,
)
from tools.relay_theory_probability_mass_gluing import (
    all_eight_assignments_are_support_compatible,
    boundary_family,
    disagreement_certificate_rejects,
    disagreement_count,
    disagreement_sum,
    disagreement_vector,
    exact_triangle_bound,
    negative_family,
    pair_mismatch_probability,
    pointwise_disagreement_profile,
    run_probability_mass_gluing,
    sharp_boundary_witness,
    symmetric_full_support_pair,
)


def test_probability_mass_gluing_summary_passes_with_strict_booleans() -> None:
    results = run_probability_mass_gluing()

    assert [result.name for result in results] == [
        "NEGATIVE_LOCAL_LAWS_ARE_OVERLAP_CONSISTENT",
        "NEGATIVE_SUPPORT_IS_MAXIMALLY_PERMISSIVE",
        "NEGATIVE_DISAGREEMENTS_ARE_EXACTLY_THREE_QUARTERS",
        "POINTWISE_BINARY_DISAGREEMENT_BOUND_IS_TWO",
        "MASS_CERTIFICATE_REJECTS_FULL_SUPPORT_NEGATIVE",
        "BOUNDARY_LOCAL_LAWS_ARE_OVERLAP_CONSISTENT_AND_FULL_SUPPORT",
        "BOUNDARY_WITNESS_RECONSTRUCTS_EVERY_LOCAL_LAW",
        "BOUNDARY_SATURATES_DISAGREEMENT_INEQUALITY",
        "WORLD_RENAMING_PRESERVES_MASS_OBSTRUCTION",
        "CONTEXT_ORDER_IS_GAUGE_FOR_MASS_OBSTRUCTION",
    ]
    assert all(type(result.passed) is bool for result in results)
    assert all(result.passed for result in results)


def test_negative_family_is_exact_overlap_consistent_and_full_support() -> None:
    family = negative_family()
    all_assignments = tuple(
        (assignment[0], assignment[1], assignment[2])
        for assignment in product(("0", "1"), repeat=3)
    )

    assert overlap_consistent(family)
    assert supported_global_assignments(family) == all_assignments
    assert all_eight_assignments_are_support_compatible(family)
    for context_law in family.contexts:
        assert len(canonical_pair_law(context_law.law)) == 4
        assert all(mass > 0 for _, mass in context_law.law)


def test_negative_pair_mismatch_probabilities_are_exactly_three_quarters() -> None:
    family = negative_family()

    assert disagreement_vector(family) == (
        Fraction(3, 4),
        Fraction(3, 4),
        Fraction(3, 4),
    )
    assert disagreement_sum(family) == Fraction(9, 4)
    assert all(
        pair_mismatch_probability(context_law) == Fraction(3, 4)
        for context_law in family.contexts
    )


def test_pointwise_disagreement_inequality_is_exhaustive_over_all_eight_states() -> None:
    profile = pointwise_disagreement_profile()

    assert len(profile) == 8
    assert {assignment for assignment, _ in profile} == set(
        product(("0", "1"), repeat=3)
    )
    assert {count for _, count in profile} == {0, 2}
    assert max(count for _, count in profile) == 2
    assert exact_triangle_bound() == Fraction(2)


def test_full_support_negative_is_rejected_only_at_mass_level() -> None:
    family = negative_family()

    assert overlap_consistent(family)
    assert all_eight_assignments_are_support_compatible(family)
    assert disagreement_sum(family) == Fraction(9, 4)
    assert disagreement_sum(family) > exact_triangle_bound()
    assert disagreement_certificate_rejects(family)


def test_two_thirds_boundary_has_exact_global_witness_and_saturates_bound() -> None:
    family = boundary_family()
    witness = sharp_boundary_witness()

    assert overlap_consistent(family)
    assert all_eight_assignments_are_support_compatible(family)
    assert disagreement_vector(family) == (
        Fraction(2, 3),
        Fraction(2, 3),
        Fraction(2, 3),
    )
    assert disagreement_sum(family) == Fraction(2)
    assert disagreement_sum(family) == exact_triangle_bound()
    assert not disagreement_certificate_rejects(family)
    assert verify_global_witness(family, witness)


def test_sharp_boundary_witness_is_uniform_over_six_nonconstant_states() -> None:
    witness = sharp_boundary_witness()

    assert len(witness.joint) == 6
    assert all(mass == Fraction(1, 6) for _, mass in witness.joint)
    assert all(len(set(outcome)) == 2 for outcome, _ in witness.joint)
    assert sum((mass for _, mass in witness.joint), Fraction(0)) == Fraction(1)


def test_context_order_does_not_change_exact_mass_certificate() -> None:
    source = negative_family()
    reversed_family = LocalFamily(
        "reversed",
        source.worlds,
        tuple(reversed(source.contexts)),
    )

    assert overlap_consistent(reversed_family)
    assert all_eight_assignments_are_support_compatible(reversed_family)
    assert sorted(disagreement_vector(reversed_family)) == sorted(disagreement_vector(source))
    assert disagreement_sum(reversed_family) == disagreement_sum(source)
    assert disagreement_certificate_rejects(reversed_family)


def test_full_support_pair_constructor_rejects_nonexact_or_boundary_parameters() -> None:
    with pytest.raises(TypeError, match="fractions.Fraction"):
        symmetric_full_support_pair(("A", "B"), mismatch_probability=0.75)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="strictly in"):
        symmetric_full_support_pair(("A", "B"), mismatch_probability=Fraction(0))

    with pytest.raises(ValueError, match="strictly in"):
        symmetric_full_support_pair(("A", "B"), mismatch_probability=Fraction(1))


def test_disagreement_count_rejects_nonbinary_or_wrong_arity() -> None:
    with pytest.raises(ValueError, match="binary triple"):
        disagreement_count(("0", "1"))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="binary triple"):
        disagreement_count(("0", "1", "2"))
