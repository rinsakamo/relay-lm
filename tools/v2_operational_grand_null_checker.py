"""Deterministic finite witnesses for selected #2209 Operational Grand Null gates.

This is falsification apparatus, not RelayLM runtime or architecture authority.
A gate PASS means the checker detected the intended counterexample/invariant.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Callable, Mapping, Sequence


@dataclass(frozen=True)
class CheckResult:
    gate: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class GroundingWitness:
    answer: str
    claims_authentic: bool
    independently_authenticated: bool


@dataclass(frozen=True)
class SubstrateWitness:
    interface_behavior: tuple[str, ...]
    internal_iso_classes: int


@dataclass(frozen=True)
class ClaimEvidence:
    claim: str
    return_value: str
    independently_authenticated: bool
    claim_relevant: bool


Partition = Mapping[str, str]
State = Mapping[str, int]
Context = Callable[[State], int]
Arrow = tuple[str, str, str]


def threshold_counterexample(
    values: Sequence[float], epsilon: float
) -> tuple[float, float, float] | None:
    for x, y, z in product(values, repeat=3):
        if abs(x - y) <= epsilon and abs(y - z) <= epsilon and abs(x - z) > epsilon:
            return x, y, z
    return None


def partition_refines(fine: Partition, coarse: Partition) -> bool:
    if set(fine) != set(coarse):
        raise ValueError("partitions must cover the same domain")
    return all(
        fine[x] != fine[y] or coarse[x] == coarse[y]
        for x, y in product(fine, repeat=2)
    )


def canonical_map(fine: Partition, coarse: Partition) -> dict[str, str]:
    if not partition_refines(fine, coarse):
        raise ValueError("fine partition does not refine coarse partition")
    result: dict[str, str] = {}
    for point, fine_class in fine.items():
        result.setdefault(fine_class, coarse[point])
        if result[fine_class] != coarse[point]:
            raise AssertionError("canonical quotient map is not well-defined")
    return result


def compose_maps(first: Mapping[str, str], second: Mapping[str, str]) -> dict[str, str]:
    return {source: second[middle] for source, middle in first.items()}


def contextually_equivalent(left: State, right: State, contexts: Sequence[Context]) -> bool:
    return all(context(left) == context(right) for context in contexts)


def representative_independent(
    representatives: Sequence[State], continuations: Sequence[Context]
) -> bool:
    return all(
        len({continuation(rep) for rep in representatives}) == 1
        for continuation in continuations
    )


def resource_transition(remaining: int, cost: int) -> int | None:
    if remaining < 0 or cost < 0:
        raise ValueError("remaining resource and cost must be non-negative")
    if cost > remaining:
        return None
    return remaining - cost


def deadline_admissible(duration: int, deadline: int) -> bool:
    if duration < 0 or deadline < 0:
        raise ValueError("duration and deadline must be non-negative")
    return duration <= deadline


def finite_function_exists(source_size: int, target_size: int) -> bool:
    if source_size < 0 or target_size < 0:
        raise ValueError("finite-set cardinalities must be non-negative")
    return source_size == 0 or target_size > 0


def finite_sets_isomorphic(left_size: int, right_size: int) -> bool:
    if left_size < 0 or right_size < 0:
        raise ValueError("finite-set cardinalities must be non-negative")
    return left_size == right_size


def terminal_probe(_: int) -> str:
    return "*"


def answer_probe(witness: GroundingWitness) -> tuple[str, bool]:
    return witness.answer, witness.claims_authentic


def grounding_probe(witness: GroundingWitness) -> bool:
    return witness.independently_authenticated


def substrate_interface_probe(witness: SubstrateWitness) -> tuple[str, ...]:
    return witness.interface_behavior


def finite_discrete_categories_equivalent(
    left: SubstrateWitness, right: SubstrateWitness
) -> bool:
    if left.internal_iso_classes < 0 or right.internal_iso_classes < 0:
        raise ValueError("finite discrete-category sizes must be non-negative")
    return left.internal_iso_classes == right.internal_iso_classes


def g1_non_self_authentication(evidence: ClaimEvidence) -> bool:
    return evidence.independently_authenticated


def minimum_grounding_gate(evidence: ClaimEvidence) -> bool:
    return evidence.independently_authenticated and evidence.claim_relevant


def object_preserving_arrow_map_possible(source: Sequence[Arrow], target: Sequence[Arrow]) -> bool:
    target_endpoints = {(src, dst) for _, src, dst in target}
    return all((src, dst) in target_endpoints for _, src, dst in source)


def run_checks() -> tuple[CheckResult, ...]:
    c0_witness = threshold_counterexample((0.0, 0.75, 1.5), 1.0)

    p = {"visible": 0, "hidden": 0}
    q = {"visible": 0, "hidden": 1}

    def visible(state: State) -> int:
        return state["visible"]

    def reveal_hidden(state: State) -> int:
        return state["hidden"]

    coarse_first = ("X", "X")
    coarse_second = ("X", "X")
    coarse_composable = coarse_first[1] == coarse_second[0]
    first_budget = resource_transition(1, 1)
    second_budget = resource_transition(first_budget, 1) if first_budget is not None else None

    set_a_size = 2
    set_b_size = 1
    a_reaches_b = finite_function_exists(set_a_size, set_b_size)
    b_reaches_a = finite_function_exists(set_b_size, set_a_size)
    a_b_isomorphic = finite_sets_isomorphic(set_a_size, set_b_size)
    restricted_probe_agrees = terminal_probe(set_a_size) == terminal_probe(set_b_size)

    grounded = GroundingWitness(
        answer="same answer",
        claims_authentic=True,
        independently_authenticated=True,
    )
    self_authenticated = GroundingWitness(
        answer="same answer",
        claims_authentic=True,
        independently_authenticated=False,
    )
    answer_probe_agrees = answer_probe(grounded) == answer_probe(self_authenticated)
    grounding_probe_differs = grounding_probe(grounded) != grounding_probe(self_authenticated)

    substrate_a = SubstrateWitness(interface_behavior=("task:ok",), internal_iso_classes=1)
    substrate_b = SubstrateWitness(interface_behavior=("task:ok",), internal_iso_classes=2)
    substrate_interface_agrees = (
        substrate_interface_probe(substrate_a) == substrate_interface_probe(substrate_b)
    )
    whole_categories_equivalent = finite_discrete_categories_equivalent(
        substrate_a, substrate_b
    )

    external_nonce = ClaimEvidence(
        claim="WORLD temperature > 30 C",
        return_value="nonce=847291",
        independently_authenticated=True,
        claim_relevant=False,
    )
    nonce_passes_g1 = g1_non_self_authentication(external_nonce)
    nonce_passes_minimum_grounding = minimum_grounding_gate(external_nonce)

    omega = {"z1": "a0", "z2": "a1"}
    omega_prime = {"z1": "b0", "z2": "b0"}

    e2 = {"a": "a", "b": "b", "c": "c"}
    e1 = {"a": "ab", "b": "ab", "c": "c"}
    e0 = {"a": "all", "b": "all", "c": "all"}
    pi21 = canonical_map(e2, e1)
    pi10 = canonical_map(e1, e0)
    pi20 = canonical_map(e2, e0)

    fast_reachability = {("A", "B")}
    slow_reachability = {("A", "B")}
    fast_admissible = deadline_admissible(1, 10)
    slow_admissible = deadline_admissible(100, 10)

    coarse_actions: tuple[Arrow, ...] = (
        ("id_X", "X", "X"),
        ("id_Y", "Y", "Y"),
    )
    rich_actions = coarse_actions + (("f", "X", "Y"),)

    return (
        CheckResult(
            "C0",
            c0_witness is not None,
            f"epsilon-threshold non-transitivity witness={c0_witness}",
        ),
        CheckResult(
            "C3",
            contextually_equivalent(p, q, (visible,))
            and not contextually_equivalent(p, q, (visible, reveal_hidden)),
            "endpoint/readout equality breaks under an admissible hidden-reading context",
        ),
        CheckResult(
            "C4",
            not representative_independent((p, q), (reveal_hidden,)),
            "quotient continuation depends on representative",
        ),
        CheckResult(
            "C5",
            coarse_composable and first_budget == 0 and second_budget is None,
            "coarse endpoints compose, but remaining-budget typing rejects the second unit-cost action",
        ),
        CheckResult(
            "C6",
            a_reaches_b and b_reaches_a and not a_b_isomorphic,
            "finite sets of sizes 2 and 1 have morphisms both ways but are not isomorphic",
        ),
        CheckResult(
            "C7",
            restricted_probe_agrees and not a_b_isomorphic,
            "terminal probe identifies non-isomorphic finite sets; restricted probe agreement is not Yoneda",
        ),
        CheckResult(
            "C8",
            answer_probe_agrees and grounding_probe_differs,
            "same answer/authentic claim hides a difference in independent authentication",
        ),
        CheckResult(
            "C9",
            substrate_interface_agrees and not whole_categories_equivalent,
            "declared interface behavior agrees although finite discrete realization categories are not equivalent",
        ),
        CheckResult(
            "C10",
            nonce_passes_g1 and not nonce_passes_minimum_grounding,
            "independently authenticated external nonce is claim-irrelevant; G1 alone is insufficient",
        ),
        CheckResult(
            "C11",
            not partition_refines(omega_prime, omega),
            "changed observation family merges a distinction; it is not monotone refinement",
        ),
        CheckResult(
            "C12",
            partition_refines(e2, e1)
            and partition_refines(e1, e0)
            and compose_maps(pi21, pi10) == pi20,
            "canonical maps over nested exact quotients compose coherently",
        ),
        CheckResult(
            "C13",
            fast_reachability == slow_reachability
            and fast_admissible
            and not slow_admissible,
            "same A -> B reachability has different operational validity under a deadline",
        ),
        CheckResult(
            "C15",
            object_preserving_arrow_map_possible(coarse_actions, rich_actions)
            and not object_preserving_arrow_map_possible(rich_actions, coarse_actions),
            "action expansion is covariant; a single contravariant frame map cannot absorb new arrows",
        ),
    )


def main() -> int:
    results = run_checks()
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.gate}: {result.detail}")
    passed = sum(result.passed for result in results)
    print(f"{passed}/{len(results)} gates passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
