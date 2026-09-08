from fractions import Fraction

import pytest

from tools.relay_theory_local_global_compatibility import (
    GlobalWitness,
    LocalFamily,
    PairContextLaw,
    anti_chain,
    anti_chain_witness,
    anti_correlated_pair,
    anti_triangle,
    canonical_pair_law,
    context_permutation_equivalent,
    equality_triangle,
    equality_witness,
    local_signature,
    marginalize_global_witness,
    overlap_consistent,
    rename_family,
    run_local_global_compatibility,
    singleton_marginal,
    support_obstruction_proves_nonextendable,
    supported_global_assignments,
    validate_family,
    verify_global_witness,
)


def test_local_global_summary_passes_with_strict_booleans() -> None:
    results = run_local_global_compatibility()

    assert [result.name for result in results] == [
        "LOCAL_LAWS_ARE_EXACT_AND_VALID",
        "ANTI_TRIANGLE_IS_OVERLAP_CONSISTENT",
        "ANTI_TRIANGLE_HAS_EMPTY_GLOBAL_SUPPORT",
        "SUPPORT_OBSTRUCTION_PROVES_NONEXTENDABLE",
        "EQUALITY_TRIANGLE_HAS_EXACT_GLOBAL_WITNESS",
        "EDGE_ABLATION_RESTORES_EXACT_GLOBAL_WITNESS",
        "CONTEXT_EXPANSION_CAN_BREAK_GLOBAL_REALIZABILITY",
        "WORLD_RENAMING_PRESERVES_COMPATIBILITY_VERDICT",
        "CONTEXT_ORDER_IS_GAUGE",
        "EXPLICIT_WITNESS_RECONSTRUCTS_EVERY_LOCAL_LAW",
    ]
    assert all(type(result.passed) is bool for result in results)
    assert all(result.passed for result in results)


def test_anti_triangle_is_locally_valid_and_overlap_consistent() -> None:
    family = anti_triangle()
    fair = (("0", Fraction(1, 2)), ("1", Fraction(1, 2)))

    validate_family(family)
    assert overlap_consistent(family)
    for context_law in family.contexts:
        assert canonical_pair_law(context_law.law) == context_law.law
        for world in context_law.context:
            assert singleton_marginal(context_law, world) == fair


def test_anti_triangle_has_no_supported_global_assignment() -> None:
    family = anti_triangle()

    assert supported_global_assignments(family) == ()
    assert support_obstruction_proves_nonextendable(family)


def test_equality_triangle_has_verified_exact_global_witness() -> None:
    family = equality_triangle()
    witness = equality_witness()

    assert overlap_consistent(family)
    assert supported_global_assignments(family) == (("0", "0", "0"), ("1", "1", "1"))
    assert verify_global_witness(family, witness)

    by_context = {context_law.context: context_law.law for context_law in family.contexts}
    for context, law in by_context.items():
        assert marginalize_global_witness(witness, context) == law


def test_removing_one_odd_cycle_edge_restores_global_realizability() -> None:
    chain = anti_chain()
    witness = anti_chain_witness()

    assert overlap_consistent(chain)
    assert supported_global_assignments(chain) == (("0", "1", "0"), ("1", "0", "1"))
    assert verify_global_witness(chain, witness)


def test_adding_third_locally_consistent_context_breaks_global_realizability() -> None:
    chain = anti_chain()
    triangle = anti_triangle()

    assert local_signature(chain) == tuple(
        entry
        for entry in local_signature(triangle)
        if frozenset(entry[0]) != frozenset(("A", "C"))
    )
    assert verify_global_witness(chain, anti_chain_witness())
    assert overlap_consistent(triangle)
    assert support_obstruction_proves_nonextendable(triangle)


def test_world_renaming_and_context_order_are_gauge_for_bounded_verdict() -> None:
    source = anti_triangle()
    renamed = rename_family(
        source,
        {"A": "X", "B": "Y", "C": "Z"},
        name="renamed",
    )
    reordered = LocalFamily("reordered", source.worlds, tuple(reversed(source.contexts)))

    assert overlap_consistent(renamed)
    assert support_obstruction_proves_nonextendable(renamed)
    assert context_permutation_equivalent(source, reordered)
    assert support_obstruction_proves_nonextendable(reordered)


def test_invalid_local_laws_fail_closed() -> None:
    with pytest.raises(TypeError, match="fractions.Fraction"):
        canonical_pair_law(((('0', '1'), 0.5), (('1', '0'), 0.5)))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="must be unique"):
        canonical_pair_law(
            ((('0', '1'), Fraction(1, 2)), (('0', '1'), Fraction(1, 2)))
        )

    with pytest.raises(ValueError, match="sum exactly to 1"):
        canonical_pair_law(((('0', '1'), Fraction(1, 2)),))

    with pytest.raises(ValueError, match="binary pairs"):
        canonical_pair_law(((('0', '2'), Fraction(1)),))

    with pytest.raises(ValueError, match="must be distinct"):
        validate_family(
            LocalFamily(
                "degenerate-context",
                ("A", "B", "C"),
                (PairContextLaw(("A", "A"), ((('0', '0'), Fraction(1)),)),),
            )
        )

    with pytest.raises(ValueError, match="undeclared world"):
        validate_family(
            LocalFamily(
                "unknown-world",
                ("A", "B", "C"),
                (anti_correlated_pair(("A", "D")),),
            )
        )

    with pytest.raises(ValueError, match="unique up to coordinate order"):
        validate_family(
            LocalFamily(
                "duplicate-context",
                ("A", "B", "C"),
                (
                    anti_correlated_pair(("A", "B")),
                    anti_correlated_pair(("B", "A")),
                ),
            )
        )


def test_invalid_global_witnesses_fail_or_are_rejected_exactly() -> None:
    family = equality_triangle()

    with pytest.raises(TypeError, match="fractions.Fraction"):
        verify_global_witness(
            family,
            GlobalWitness(
                ("A", "B", "C"),
                ((('0', '0', '0'), 1.0),),  # type: ignore[arg-type]
            ),
        )

    wrong_worlds = GlobalWitness(
        ("A", "B", "D"),
        ((('0', '0', '0'), Fraction(1, 2)), (('1', '1', '1'), Fraction(1, 2))),
    )
    assert not verify_global_witness(family, wrong_worlds)

    wrong_law = GlobalWitness(
        ("A", "B", "C"),
        ((('0', '0', '0'), Fraction(1)),),
    )
    assert not verify_global_witness(family, wrong_law)


def test_nonempty_support_is_not_used_as_general_extension_proof() -> None:
    """The bounded detector reports support only; positive existence uses a witness."""
    chain = anti_chain()

    assert supported_global_assignments(chain)
    assert not support_obstruction_proves_nonextendable(chain)
    assert verify_global_witness(chain, anti_chain_witness())
