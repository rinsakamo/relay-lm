"""Exact finite local-to-global compatibility apparatus for Relay Theory #2379.

Research falsification only. The bounded fixture asks whether individually valid,
overlap-consistent pairwise laws over three binary worlds admit one global joint.
It proves one support obstruction and verifies explicit positive witnesses; it does
not solve the general marginal polytope or assume sheaf/category structure.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, product

Bit = str
PairOutcome = tuple[Bit, Bit]
TripleOutcome = tuple[Bit, Bit, Bit]
PairLaw = tuple[tuple[PairOutcome, Fraction], ...]
GlobalLaw = tuple[tuple[TripleOutcome, Fraction], ...]
SingleLaw = tuple[tuple[Bit, Fraction], ...]


@dataclass(frozen=True)
class PairContextLaw:
    context: tuple[str, str]
    law: PairLaw


@dataclass(frozen=True)
class LocalFamily:
    name: str
    worlds: tuple[str, str, str]
    contexts: tuple[PairContextLaw, ...]


@dataclass(frozen=True)
class GlobalWitness:
    worlds: tuple[str, str, str]
    joint: GlobalLaw


@dataclass(frozen=True)
class CompatibilityResult:
    name: str
    passed: bool
    detail: str = ""


def _validate_fraction(mass: Fraction) -> None:
    if not isinstance(mass, Fraction):
        raise TypeError("exact probability mass must be fractions.Fraction")
    if mass < 0 or mass > 1:
        raise ValueError("probability mass must lie in [0, 1]")


def canonical_pair_law(law: PairLaw) -> PairLaw:
    seen: set[PairOutcome] = set()
    total = Fraction(0)
    cleaned: list[tuple[PairOutcome, Fraction]] = []
    for outcome, mass in law:
        if len(outcome) != 2 or any(bit not in {"0", "1"} for bit in outcome):
            raise ValueError("pair outcomes must be binary pairs")
        if outcome in seen:
            raise ValueError("pair outcomes must be unique")
        seen.add(outcome)
        _validate_fraction(mass)
        total += mass
        if mass:
            cleaned.append((outcome, mass))
    if total != 1:
        raise ValueError("pair probability mass must sum exactly to 1")
    return tuple(sorted(cleaned, key=repr))


def validate_pair_context(context_law: PairContextLaw, worlds: Sequence[str]) -> None:
    left, right = context_law.context
    if left == right:
        raise ValueError("pair context worlds must be distinct")
    if left not in worlds or right not in worlds:
        raise ValueError("pair context contains undeclared world")
    canonical_pair_law(context_law.law)


def validate_family(family: LocalFamily) -> None:
    if len(set(family.worlds)) != 3:
        raise ValueError("bounded fixture requires exactly three unique worlds")
    if not family.contexts:
        raise ValueError("local family must contain at least one context")

    seen_contexts: set[frozenset[str]] = set()
    for context_law in family.contexts:
        validate_pair_context(context_law, family.worlds)
        context_key = frozenset(context_law.context)
        if context_key in seen_contexts:
            raise ValueError("pair contexts must be unique up to coordinate order")
        seen_contexts.add(context_key)


def singleton_marginal(context_law: PairContextLaw, world: str) -> SingleLaw:
    validate_pair_context(context_law, context_law.context)
    if world not in context_law.context:
        raise ValueError("world is not present in pair context")
    index = context_law.context.index(world)
    weights = {"0": Fraction(0), "1": Fraction(0)}
    for outcome, mass in canonical_pair_law(context_law.law):
        weights[outcome[index]] += mass
    return tuple(sorted(weights.items()))


def overlap_consistent(family: LocalFamily) -> bool:
    validate_family(family)
    for left, right in combinations(family.contexts, 2):
        overlap = set(left.context) & set(right.context)
        for world in overlap:
            if singleton_marginal(left, world) != singleton_marginal(right, world):
                return False
    return True


def positive_support(context_law: PairContextLaw) -> frozenset[PairOutcome]:
    return frozenset(outcome for outcome, mass in canonical_pair_law(context_law.law) if mass)


def supported_global_assignments(family: LocalFamily) -> tuple[TripleOutcome, ...]:
    """Enumerate global assignments surviving every local positive-support constraint."""
    validate_family(family)
    index = {world: position for position, world in enumerate(family.worlds)}
    compatible: list[TripleOutcome] = []
    for assignment in product(("0", "1"), repeat=3):
        triple: TripleOutcome = (assignment[0], assignment[1], assignment[2])
        if all(
            (
                triple[index[context_law.context[0]]],
                triple[index[context_law.context[1]]],
            )
            in positive_support(context_law)
            for context_law in family.contexts
        ):
            compatible.append(triple)
    return tuple(compatible)


def support_obstruction_proves_nonextendable(family: LocalFamily) -> bool:
    return overlap_consistent(family) and not supported_global_assignments(family)


def canonical_global_law(witness: GlobalWitness) -> GlobalLaw:
    if len(set(witness.worlds)) != 3:
        raise ValueError("global witness requires exactly three unique worlds")
    seen: set[TripleOutcome] = set()
    total = Fraction(0)
    cleaned: list[tuple[TripleOutcome, Fraction]] = []
    for outcome, mass in witness.joint:
        if len(outcome) != 3 or any(bit not in {"0", "1"} for bit in outcome):
            raise ValueError("global outcomes must be binary triples")
        if outcome in seen:
            raise ValueError("global outcomes must be unique")
        seen.add(outcome)
        _validate_fraction(mass)
        total += mass
        if mass:
            cleaned.append((outcome, mass))
    if total != 1:
        raise ValueError("global probability mass must sum exactly to 1")
    return tuple(sorted(cleaned, key=repr))


def marginalize_global_witness(
    witness: GlobalWitness, context: tuple[str, str]
) -> PairLaw:
    joint = canonical_global_law(witness)
    if context[0] == context[1]:
        raise ValueError("pair context worlds must be distinct")
    if any(world not in witness.worlds for world in context):
        raise ValueError("pair context contains undeclared witness world")
    index = {world: position for position, world in enumerate(witness.worlds)}
    weights: dict[PairOutcome, Fraction] = {}
    for outcome, mass in joint:
        projected = (outcome[index[context[0]]], outcome[index[context[1]]])
        weights[projected] = weights.get(projected, Fraction(0)) + mass
    return canonical_pair_law(tuple(weights.items()))


def verify_global_witness(family: LocalFamily, witness: GlobalWitness) -> bool:
    validate_family(family)
    canonical_global_law(witness)
    if set(family.worlds) != set(witness.worlds):
        return False
    return all(
        marginalize_global_witness(witness, context_law.context)
        == canonical_pair_law(context_law.law)
        for context_law in family.contexts
    )


def anti_correlated_pair(context: tuple[str, str]) -> PairContextLaw:
    half = Fraction(1, 2)
    return PairContextLaw(context, ((('0', '1'), half), (('1', '0'), half)))


def equal_pair(context: tuple[str, str]) -> PairContextLaw:
    half = Fraction(1, 2)
    return PairContextLaw(context, ((('0', '0'), half), (('1', '1'), half)))


def anti_triangle(name: str = "anti-triangle") -> LocalFamily:
    return LocalFamily(
        name,
        ("A", "B", "C"),
        (
            anti_correlated_pair(("A", "B")),
            anti_correlated_pair(("B", "C")),
            anti_correlated_pair(("A", "C")),
        ),
    )


def anti_chain(name: str = "anti-chain") -> LocalFamily:
    return LocalFamily(
        name,
        ("A", "B", "C"),
        (
            anti_correlated_pair(("A", "B")),
            anti_correlated_pair(("B", "C")),
        ),
    )


def equality_triangle(name: str = "equality-triangle") -> LocalFamily:
    return LocalFamily(
        name,
        ("A", "B", "C"),
        (
            equal_pair(("A", "B")),
            equal_pair(("B", "C")),
            equal_pair(("A", "C")),
        ),
    )


def equality_witness() -> GlobalWitness:
    half = Fraction(1, 2)
    return GlobalWitness(
        ("A", "B", "C"),
        ((('0', '0', '0'), half), (('1', '1', '1'), half)),
    )


def anti_chain_witness() -> GlobalWitness:
    half = Fraction(1, 2)
    return GlobalWitness(
        ("A", "B", "C"),
        ((('0', '1', '0'), half), (('1', '0', '1'), half)),
    )


def rename_family(
    family: LocalFamily,
    mapping: Mapping[str, str],
    *,
    name: str,
) -> LocalFamily:
    validate_family(family)
    if set(mapping) != set(family.worlds):
        raise ValueError("world rename mapping must cover every world exactly once")
    renamed_worlds = tuple(mapping[world] for world in family.worlds)
    if len(set(renamed_worlds)) != 3:
        raise ValueError("renamed world labels must be unique")
    renamed_contexts = tuple(
        PairContextLaw(
            (mapping[context_law.context[0]], mapping[context_law.context[1]]),
            context_law.law,
        )
        for context_law in family.contexts
    )
    renamed = LocalFamily(name, renamed_worlds, renamed_contexts)
    validate_family(renamed)
    return renamed


def local_signature(family: LocalFamily) -> tuple[tuple[tuple[str, str], PairLaw], ...]:
    """Canonical local signature independent of context-list ordering."""
    validate_family(family)
    entries = [
        (context_law.context, canonical_pair_law(context_law.law))
        for context_law in family.contexts
    ]
    return tuple(sorted(entries, key=repr))


def context_permutation_equivalent(left: LocalFamily, right: LocalFamily) -> bool:
    return left.worlds == right.worlds and local_signature(left) == local_signature(right)


def run_local_global_compatibility() -> tuple[CompatibilityResult, ...]:
    anti = anti_triangle()
    chain = anti_chain()
    equal = equality_triangle()
    equal_witness = equality_witness()
    chain_witness = anti_chain_witness()

    renamed = rename_family(
        anti,
        {"A": "X", "B": "Y", "C": "Z"},
        name="renamed-anti",
    )

    reordered = LocalFamily(
        "anti-reordered",
        anti.worlds,
        tuple(reversed(anti.contexts)),
    )

    results = (
        CompatibilityResult(
            "LOCAL_LAWS_ARE_EXACT_AND_VALID",
            all(
                canonical_pair_law(context_law.law) == context_law.law
                for family in (anti, chain, equal)
                for context_law in family.contexts
            ),
        ),
        CompatibilityResult(
            "ANTI_TRIANGLE_IS_OVERLAP_CONSISTENT",
            overlap_consistent(anti),
        ),
        CompatibilityResult(
            "ANTI_TRIANGLE_HAS_EMPTY_GLOBAL_SUPPORT",
            supported_global_assignments(anti) == (),
        ),
        CompatibilityResult(
            "SUPPORT_OBSTRUCTION_PROVES_NONEXTENDABLE",
            support_obstruction_proves_nonextendable(anti),
        ),
        CompatibilityResult(
            "EQUALITY_TRIANGLE_HAS_EXACT_GLOBAL_WITNESS",
            verify_global_witness(equal, equal_witness),
        ),
        CompatibilityResult(
            "EDGE_ABLATION_RESTORES_EXACT_GLOBAL_WITNESS",
            overlap_consistent(chain)
            and bool(supported_global_assignments(chain))
            and verify_global_witness(chain, chain_witness),
        ),
        CompatibilityResult(
            "CONTEXT_EXPANSION_CAN_BREAK_GLOBAL_REALIZABILITY",
            verify_global_witness(chain, chain_witness)
            and support_obstruction_proves_nonextendable(anti),
        ),
        CompatibilityResult(
            "WORLD_RENAMING_PRESERVES_COMPATIBILITY_VERDICT",
            overlap_consistent(renamed)
            and support_obstruction_proves_nonextendable(renamed),
        ),
        CompatibilityResult(
            "CONTEXT_ORDER_IS_GAUGE",
            context_permutation_equivalent(anti, reordered)
            and support_obstruction_proves_nonextendable(reordered),
        ),
        CompatibilityResult(
            "EXPLICIT_WITNESS_RECONSTRUCTS_EVERY_LOCAL_LAW",
            verify_global_witness(equal, equal_witness)
            and verify_global_witness(chain, chain_witness),
        ),
    )
    return results
