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


def object_preserving_arrow_map_possible(source: Sequence[Arrow], target: Sequence[Arrow]) -> bool:
    target_endpoints = {(src, dst) for _, src, dst in target}
    return all((src, dst) in target_endpoints for _, src, dst in source)


def run_checks() -> tuple[CheckResult, ...]:
    c0_witness = threshold_counterexample((0.0, 0.75, 1.5), 1.0)

    p = {"visible": 0, "hidden": 0}
    q = {"visible": 0, "hidden": 1}
    visible: Context = lambda state: state["visible"]
    reveal_hidden: Context = lambda state: state["hidden"]

    omega = {"z1": "a0", "z2": "a1"}
    omega_prime = {"z1": "b0", "z2": "b0"}

    e2 = {"a": "a", "b": "b", "c": "c"}
    e1 = {"a": "ab", "b": "ab", "c": "c"}
    e0 = {"a": "all", "b": "all", "c": "all"}
    pi21 = canonical_map(e2, e1)
    pi10 = canonical_map(e1, e0)
    pi20 = canonical_map(e2, e0)

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
