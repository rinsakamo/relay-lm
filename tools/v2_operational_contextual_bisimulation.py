"""Finite C3/C4 comparison of traces, bisimulation, and contextual quotients.

This is deterministic research falsification apparatus for #2209. It asks
whether the remaining contextual-replacement / representative-independence
requirements force category structure to be primitive, or whether a richly
labeled finite LTS plus an explicitly declared observation family is already
sufficient for the tested cases.

The result is intentionally bounded: strong bisimulation is tested only for
contexts represented by the declared transition and observation interface.
Arbitrary external context constructors still require a separate congruence
proof or an expanded frame.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass

from tools.v2_operational_representation_comparison import (
    LTS,
    Transition,
    free_category_morphisms,
    labeled_paths,
    quotient_lts,
    transition_congruence,
)

Observation = tuple[str, ...]
ObservationFamily = Mapping[str, Observation]
Partition = Mapping[str, str]
RichLabel = tuple[str, int, int]
Trace = tuple[RichLabel, ...]


@dataclass(frozen=True)
class ContextualResult:
    name: str
    passed: bool
    detail: str


def _canonical_partition(
    states: Sequence[str], signatures: Mapping[str, Hashable]
) -> dict[str, str]:
    groups: dict[Hashable, list[str]] = {}
    for state in states:
        groups.setdefault(signatures[state], []).append(state)

    ordered_groups = sorted(tuple(sorted(group)) for group in groups.values())
    partition: dict[str, str] = {}
    for index, group in enumerate(ordered_groups):
        block = f"B{index}"
        for state in group:
            partition[state] = block
    return partition


def rich_label(transition: Transition) -> RichLabel:
    return transition.action, transition.duration, transition.cost


def trace_signatures(lts: LTS, start: str, max_steps: int) -> frozenset[Trace]:
    if start not in lts.states:
        raise ValueError("start must be an LTS state")
    if max_steps < 0:
        raise ValueError("max_steps must be non-negative")

    traces: set[Trace] = {()}
    frontier: set[tuple[str, Trace]] = {(start, ())}
    for _ in range(max_steps):
        next_frontier: set[tuple[str, Trace]] = set()
        for state, trace in frontier:
            for transition in lts.transitions:
                if transition.src != state:
                    continue
                extended = trace + (rich_label(transition),)
                traces.add(extended)
                next_frontier.add((transition.dst, extended))
        frontier = next_frontier
        if not frontier:
            break
    return frozenset(traces)


def strong_bisimulation_partition(
    lts: LTS, observations: ObservationFamily
) -> dict[str, str]:
    if set(observations) != set(lts.states):
        raise ValueError("observations must cover every LTS state exactly once")

    partition = _canonical_partition(lts.states, observations)
    while True:
        signatures: dict[
            str, tuple[Observation, frozenset[tuple[RichLabel, str]]]
        ] = {}
        for state in lts.states:
            successors = frozenset(
                (rich_label(transition), partition[transition.dst])
                for transition in lts.transitions
                if transition.src == state
            )
            signatures[state] = observations[state], successors

        refined = _canonical_partition(lts.states, signatures)
        if refined == partition:
            return refined
        partition = refined


def equivalent(partition: Partition, left: str, right: str) -> bool:
    return partition[left] == partition[right]


def partition_refines(fine: Partition, coarse: Partition) -> bool:
    if set(fine) != set(coarse):
        raise ValueError("partitions must cover the same states")
    states = tuple(fine)
    return all(
        not equivalent(fine, left, right) or equivalent(coarse, left, right)
        for left in states
        for right in states
    )


def stable_observed_partition(
    lts: LTS, observations: ObservationFamily, partition: Partition
) -> bool:
    if set(observations) != set(lts.states) or set(partition) != set(lts.states):
        raise ValueError("observations and partition must cover every LTS state")

    states = tuple(lts.states)
    observation_stable = all(
        not equivalent(partition, left, right)
        or observations[left] == observations[right]
        for left in states
        for right in states
    )
    return observation_stable and transition_congruence(lts, partition)


def run_contextual_comparison() -> tuple[ContextualResult, ...]:
    # Same finite traces, different branching structure.
    branching = LTS(
        ("p", "q", "r", "s", "t", "done"),
        (
            Transition("p", "a", "r"),
            Transition("r", "b", "done"),
            Transition("r", "c", "done"),
            Transition("q", "a", "s"),
            Transition("q", "a", "t"),
            Transition("s", "b", "done"),
            Transition("t", "c", "done"),
        ),
    )
    branching_observations = {state: () for state in branching.states}
    branching_partition = strong_bisimulation_partition(
        branching, branching_observations
    )
    trace_equal = trace_signatures(branching, "p", 2) == trace_signatures(
        branching, "q", 2
    )

    # C3: same immediate visible endpoint, but an admissible future observer
    # reaches observably different results.
    contextual = LTS(
        ("y0", "y1", "o0", "o1"),
        (
            Transition("y0", "read", "o0"),
            Transition("y1", "read", "o1"),
        ),
    )
    contextual_observations = {
        "y0": ("visible=0",),
        "y1": ("visible=0",),
        "o0": ("output=0",),
        "o1": ("output=1",),
    }
    contextual_partition = strong_bisimulation_partition(
        contextual, contextual_observations
    )
    endpoint_only_partition = {
        "y0": "Y",
        "y1": "Y",
        "o0": "O0",
        "o1": "O1",
    }

    # C4: a valid bisimulation quotient is representative-independent at the
    # declared observation/transition interface.
    quotient_source = LTS(
        ("x0", "x1", "z0", "z1"),
        (
            Transition("x0", "go", "z0", duration=2, cost=1),
            Transition("x1", "go", "z1", duration=2, cost=1),
        ),
    )
    quotient_observations = {
        "x0": ("phase=x",),
        "x1": ("phase=x",),
        "z0": ("phase=z",),
        "z1": ("phase=z",),
    }
    quotient_partition = strong_bisimulation_partition(
        quotient_source, quotient_observations
    )
    quotient_stable = stable_observed_partition(
        quotient_source, quotient_observations, quotient_partition
    )
    quotient = quotient_lts(quotient_source, quotient_partition)
    derived_paths_agree = labeled_paths(quotient, 2) == free_category_morphisms(
        quotient, 2
    )

    # Probe refinement is separate from action expansion: keep the LTS fixed
    # and enrich only what the declared observer may distinguish.
    probe_lts = LTS(("u0", "u1"), ())
    coarse_observations = {
        "u0": ("visible=0",),
        "u1": ("visible=0",),
    }
    fine_observations = {
        "u0": ("visible=0", "audit=left"),
        "u1": ("visible=0", "audit=right"),
    }
    coarse_partition = strong_bisimulation_partition(probe_lts, coarse_observations)
    fine_partition = strong_bisimulation_partition(probe_lts, fine_observations)

    return (
        ContextualResult(
            "TRACE_EQUALITY_IS_WEAKER_THAN_BISIMULATION",
            trace_equal and not equivalent(branching_partition, "p", "q"),
            "p and q have the same finite traces but different branching-time replacement structure",
        ),
        ContextualResult(
            "FUTURE_CONTEXT_SPLITS_ENDPOINT_EQUIVALENCE",
            contextual_observations["y0"] == contextual_observations["y1"]
            and not equivalent(contextual_partition, "y0", "y1")
            and not stable_observed_partition(
                contextual, contextual_observations, endpoint_only_partition
            ),
            "same immediate visible endpoint is not safe when a declared later read context distinguishes successors",
        ),
        ContextualResult(
            "BISIMULATION_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
            equivalent(quotient_partition, "x0", "x1")
            and equivalent(quotient_partition, "z0", "z1")
            and quotient_stable,
            "every representative in a bisimulation block has the same declared observation and labeled target-block behavior",
        ),
        ContextualResult(
            "PROBE_REFINEMENT_SPLITS_EQUIVALENCE_MONOTONICALLY",
            equivalent(coarse_partition, "u0", "u1")
            and not equivalent(fine_partition, "u0", "u1")
            and partition_refines(fine_partition, coarse_partition),
            "richer observations split a prior class without changing the executable transition family",
        ),
        ContextualResult(
            "CATEGORY_REMAINS_DERIVED_AFTER_BISIMULATION_QUOTIENT",
            quotient_stable and derived_paths_agree,
            "the stable quotient is already an LTS; its finite free-category paths add no new distinction in this witness",
        ),
    )


def main() -> int:
    results = run_contextual_comparison()
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}: {result.detail}")
    passed = sum(result.passed for result in results)
    print(f"{passed}/{len(results)} contextual comparisons passed")
    if passed == len(results):
        print(
            "VERDICT: within a fully declared finite richly labeled LTS, observed "
            "strong bisimulation supplies the C3/C4 replacement-safe quotient; "
            "category remains a derived compositional IR. External context "
            "constructors still require their own congruence proof or frame expansion."
        )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
