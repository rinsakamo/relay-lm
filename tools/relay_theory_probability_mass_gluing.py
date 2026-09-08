"""Exact full-support probability-mass gluing apparatus for Relay Theory #2382.

Research falsification only. This bounded three-bit fixture reuses #2379 local/global
contracts and separates support compatibility from exact probability compatibility.
It uses one exhaustively certified binary disagreement inequality plus one exact sharp
boundary witness; it is not a general marginal-polytope solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product

from tools.relay_theory_local_global_compatibility import (
    GlobalWitness,
    LocalFamily,
    PairContextLaw,
    canonical_pair_law,
    overlap_consistent,
    rename_family,
    supported_global_assignments,
    verify_global_witness,
)

TripleOutcome = tuple[str, str, str]


@dataclass(frozen=True)
class MassGluingResult:
    name: str
    passed: bool
    detail: str = ""


def symmetric_full_support_pair(
    context: tuple[str, str], *, mismatch_probability: Fraction
) -> PairContextLaw:
    if not isinstance(mismatch_probability, Fraction):
        raise TypeError("mismatch_probability must be fractions.Fraction")
    if mismatch_probability <= 0 or mismatch_probability >= 1:
        raise ValueError("full-support mismatch_probability must lie strictly in (0, 1)")

    mismatch_cell = mismatch_probability / 2
    equal_cell = (1 - mismatch_probability) / 2
    law = (
        (("0", "0"), equal_cell),
        (("0", "1"), mismatch_cell),
        (("1", "0"), mismatch_cell),
        (("1", "1"), equal_cell),
    )
    return PairContextLaw(context, canonical_pair_law(law))


def symmetric_triangle(
    mismatch_probability: Fraction, *, name: str
) -> LocalFamily:
    return LocalFamily(
        name,
        ("A", "B", "C"),
        (
            symmetric_full_support_pair(
                ("A", "B"), mismatch_probability=mismatch_probability
            ),
            symmetric_full_support_pair(
                ("B", "C"), mismatch_probability=mismatch_probability
            ),
            symmetric_full_support_pair(
                ("A", "C"), mismatch_probability=mismatch_probability
            ),
        ),
    )


def pair_mismatch_probability(context_law: PairContextLaw) -> Fraction:
    return sum(
        (mass for outcome, mass in canonical_pair_law(context_law.law) if outcome[0] != outcome[1]),
        Fraction(0),
    )


def disagreement_vector(family: LocalFamily) -> tuple[Fraction, ...]:
    return tuple(pair_mismatch_probability(context_law) for context_law in family.contexts)


def disagreement_sum(family: LocalFamily) -> Fraction:
    return sum(disagreement_vector(family), Fraction(0))


def disagreement_count(assignment: TripleOutcome) -> int:
    if len(assignment) != 3 or any(bit not in {"0", "1"} for bit in assignment):
        raise ValueError("assignment must be a binary triple")
    a, b, c = assignment
    return int(a != b) + int(b != c) + int(a != c)


def pointwise_disagreement_profile() -> tuple[tuple[TripleOutcome, int], ...]:
    return tuple(
        (
            (assignment[0], assignment[1], assignment[2]),
            disagreement_count((assignment[0], assignment[1], assignment[2])),
        )
        for assignment in product(("0", "1"), repeat=3)
    )


def exact_triangle_bound() -> Fraction:
    profile = pointwise_disagreement_profile()
    return Fraction(max(count for _, count in profile), 1)


def disagreement_certificate_rejects(family: LocalFamily) -> bool:
    """Sufficient exact non-extendability certificate for the bounded fixture."""
    if not overlap_consistent(family):
        return False
    return disagreement_sum(family) > exact_triangle_bound()


def all_eight_assignments_are_support_compatible(family: LocalFamily) -> bool:
    expected = tuple(
        (assignment[0], assignment[1], assignment[2])
        for assignment in product(("0", "1"), repeat=3)
    )
    return supported_global_assignments(family) == expected


def sharp_boundary_witness() -> GlobalWitness:
    sixth = Fraction(1, 6)
    return GlobalWitness(
        ("A", "B", "C"),
        (
            (("0", "0", "1"), sixth),
            (("0", "1", "0"), sixth),
            (("0", "1", "1"), sixth),
            (("1", "0", "0"), sixth),
            (("1", "0", "1"), sixth),
            (("1", "1", "0"), sixth),
        ),
    )


def negative_family(name: str = "mismatch-three-quarters") -> LocalFamily:
    return symmetric_triangle(Fraction(3, 4), name=name)


def boundary_family(name: str = "mismatch-two-thirds") -> LocalFamily:
    return symmetric_triangle(Fraction(2, 3), name=name)


def run_probability_mass_gluing() -> tuple[MassGluingResult, ...]:
    negative = negative_family()
    boundary = boundary_family()
    witness = sharp_boundary_witness()

    renamed_negative = rename_family(
        negative,
        {"A": "X", "B": "Y", "C": "Z"},
        name="renamed-negative",
    )
    reordered_negative = LocalFamily(
        "reordered-negative",
        negative.worlds,
        tuple(reversed(negative.contexts)),
    )

    profile = pointwise_disagreement_profile()
    results = (
        MassGluingResult(
            "NEGATIVE_LOCAL_LAWS_ARE_OVERLAP_CONSISTENT",
            overlap_consistent(negative),
        ),
        MassGluingResult(
            "NEGATIVE_SUPPORT_IS_MAXIMALLY_PERMISSIVE",
            all_eight_assignments_are_support_compatible(negative),
        ),
        MassGluingResult(
            "NEGATIVE_DISAGREEMENTS_ARE_EXACTLY_THREE_QUARTERS",
            disagreement_vector(negative)
            == (Fraction(3, 4), Fraction(3, 4), Fraction(3, 4)),
            str(disagreement_vector(negative)),
        ),
        MassGluingResult(
            "POINTWISE_BINARY_DISAGREEMENT_BOUND_IS_TWO",
            {count for _, count in profile} == {0, 2}
            and exact_triangle_bound() == Fraction(2),
            str(profile),
        ),
        MassGluingResult(
            "MASS_CERTIFICATE_REJECTS_FULL_SUPPORT_NEGATIVE",
            disagreement_sum(negative) == Fraction(9, 4)
            and disagreement_certificate_rejects(negative),
            f"sum={disagreement_sum(negative)} bound={exact_triangle_bound()}",
        ),
        MassGluingResult(
            "BOUNDARY_LOCAL_LAWS_ARE_OVERLAP_CONSISTENT_AND_FULL_SUPPORT",
            overlap_consistent(boundary)
            and all_eight_assignments_are_support_compatible(boundary),
        ),
        MassGluingResult(
            "BOUNDARY_WITNESS_RECONSTRUCTS_EVERY_LOCAL_LAW",
            verify_global_witness(boundary, witness),
        ),
        MassGluingResult(
            "BOUNDARY_SATURATES_DISAGREEMENT_INEQUALITY",
            disagreement_vector(boundary)
            == (Fraction(2, 3), Fraction(2, 3), Fraction(2, 3))
            and disagreement_sum(boundary) == exact_triangle_bound(),
            f"sum={disagreement_sum(boundary)} bound={exact_triangle_bound()}",
        ),
        MassGluingResult(
            "WORLD_RENAMING_PRESERVES_MASS_OBSTRUCTION",
            overlap_consistent(renamed_negative)
            and all_eight_assignments_are_support_compatible(renamed_negative)
            and disagreement_certificate_rejects(renamed_negative),
        ),
        MassGluingResult(
            "CONTEXT_ORDER_IS_GAUGE_FOR_MASS_OBSTRUCTION",
            overlap_consistent(reordered_negative)
            and all_eight_assignments_are_support_compatible(reordered_negative)
            and disagreement_sum(reordered_negative) == disagreement_sum(negative)
            and disagreement_certificate_rejects(reordered_negative),
        ),
    )
    return results
