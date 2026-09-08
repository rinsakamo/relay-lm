"""Finite stochastic-kernel comparison for RelayLM 2.0 #2209.

This is deterministic research falsification apparatus, not runtime or
architecture authority. It tests whether distribution-valued operational
signatures force a deeper primitive than the current richly labeled
transition-system candidate.

The model is intentionally bounded: finite states, exact rational
probabilities, and one normalized successor distribution per
(state, action, duration, cost) label. Multiple distinct labels may be
enabled, but this is not a full MDP / probabilistic-automaton semantics with
scheduler-sensitive nondeterminism.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction

from tools.v2_operational_representation_comparison import (
    LTS,
    Transition,
    free_category_morphisms,
)

Observation = tuple[str, ...]
ObservationFamily = Mapping[str, Observation]
Partition = Mapping[str, str]
RichLabel = tuple[str, int, int]
BlockDistribution = tuple[tuple[str, Fraction], ...]
KernelSignature = tuple[tuple[RichLabel, BlockDistribution], ...]
SampleRecord = tuple[bool, ...]


@dataclass(frozen=True)
class ProbTransition:
    src: str
    action: str
    dst: str
    probability: Fraction
    duration: int = 0
    cost: int = 0


@dataclass(frozen=True)
class ProbLTS:
    states: tuple[str, ...]
    transitions: tuple[ProbTransition, ...]


@dataclass(frozen=True)
class StochasticResult:
    name: str
    passed: bool
    detail: str


def rich_label(transition: ProbTransition) -> RichLabel:
    return transition.action, transition.duration, transition.cost


def validate_prob_lts(system: ProbLTS) -> None:
    if len(set(system.states)) != len(system.states):
        raise ValueError("states must be unique")

    state_set = set(system.states)
    totals: dict[tuple[str, RichLabel], Fraction] = {}
    for transition in system.transitions:
        if transition.src not in state_set or transition.dst not in state_set:
            raise ValueError("every transition endpoint must be a declared state")
        if not isinstance(transition.probability, Fraction):
            raise TypeError("probability must be fractions.Fraction for exact semantics")
        if transition.probability <= 0 or transition.probability > 1:
            raise ValueError("transition probabilities must lie in (0, 1]")
        if transition.duration < 0 or transition.cost < 0:
            raise ValueError("duration and cost must be non-negative")

        key = (transition.src, rich_label(transition))
        totals[key] = totals.get(key, Fraction(0)) + transition.probability

    for key, total in totals.items():
        if total != 1:
            raise ValueError(
                f"successor probabilities for {key!r} must sum exactly to 1"
            )


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


def enabled_labels(system: ProbLTS, state: str) -> tuple[RichLabel, ...]:
    if state not in system.states:
        raise ValueError("state must be declared")
    return tuple(
        sorted(
            {
                rich_label(transition)
                for transition in system.transitions
                if transition.src == state
            }
        )
    )


def _state_distribution(
    system: ProbLTS, state: str, label: RichLabel
) -> BlockDistribution:
    distribution: dict[str, Fraction] = {}
    for transition in system.transitions:
        if transition.src == state and rich_label(transition) == label:
            distribution[transition.dst] = (
                distribution.get(transition.dst, Fraction(0))
                + transition.probability
            )
    return tuple(sorted(distribution.items()))


def state_distribution(
    system: ProbLTS, state: str, label: RichLabel
) -> BlockDistribution:
    validate_prob_lts(system)
    return _state_distribution(system, state, label)


def _block_distribution(
    system: ProbLTS,
    state: str,
    label: RichLabel,
    partition: Partition,
) -> BlockDistribution:
    distribution: dict[str, Fraction] = {}
    for target, probability in _state_distribution(system, state, label):
        block = partition[target]
        distribution[block] = (
            distribution.get(block, Fraction(0)) + probability
        )
    return tuple(sorted(distribution.items()))


def _kernel_signature(
    system: ProbLTS, state: str, partition: Partition
) -> KernelSignature:
    return tuple(
        (
            label,
            _block_distribution(system, state, label, partition),
        )
        for label in enabled_labels(system, state)
    )


def probabilistic_bisimulation_partition(
    system: ProbLTS, observations: ObservationFamily
) -> dict[str, str]:
    validate_prob_lts(system)
    if set(observations) != set(system.states):
        raise ValueError("observations must cover every state exactly once")

    partition = _canonical_partition(system.states, observations)
    while True:
        signatures = {
            state: (
                observations[state],
                _kernel_signature(system, state, partition),
            )
            for state in system.states
        }
        refined = _canonical_partition(system.states, signatures)
        if refined == partition:
            return refined
        partition = refined


def equivalent(partition: Partition, left: str, right: str) -> bool:
    return partition[left] == partition[right]


def stable_probabilistic_partition(
    system: ProbLTS,
    observations: ObservationFamily,
    partition: Partition,
) -> bool:
    validate_prob_lts(system)
    if set(observations) != set(system.states):
        raise ValueError("observations must cover every state")
    if set(partition) != set(system.states):
        raise ValueError("partition must cover every state")

    states = tuple(system.states)
    for left in states:
        for right in states:
            if not equivalent(partition, left, right):
                continue
            if observations[left] != observations[right]:
                return False
            if _kernel_signature(system, left, partition) != _kernel_signature(
                system, right, partition
            ):
                return False
    return True


def quotient_prob_lts(
    system: ProbLTS,
    observations: ObservationFamily,
    partition: Partition,
) -> ProbLTS:
    if not stable_probabilistic_partition(system, observations, partition):
        raise ValueError("partition is not an exact probabilistic bisimulation")

    blocks = tuple(sorted(set(partition.values())))
    transitions: list[ProbTransition] = []

    for block in blocks:
        members = sorted(
            state for state in system.states if partition[state] == block
        )
        representative = members[0]
        for label in enabled_labels(system, representative):
            for target_block, probability in _block_distribution(
                system, representative, label, partition
            ):
                transitions.append(
                    ProbTransition(
                        block,
                        label[0],
                        target_block,
                        probability,
                        duration=label[1],
                        cost=label[2],
                    )
                )

    return ProbLTS(
        blocks,
        tuple(
            sorted(
                transitions,
                key=lambda item: (
                    item.src,
                    item.action,
                    item.dst,
                    item.duration,
                    item.cost,
                    item.probability,
                ),
            )
        ),
    )


def support_successors(
    system: ProbLTS, state: str
) -> frozenset[tuple[RichLabel, str]]:
    validate_prob_lts(system)
    return frozenset(
        (rich_label(transition), transition.dst)
        for transition in system.transitions
        if transition.src == state
    )


def support_lts(system: ProbLTS) -> LTS:
    validate_prob_lts(system)
    transitions = {
        Transition(
            transition.src,
            transition.action,
            transition.dst,
            duration=transition.duration,
            cost=transition.cost,
        )
        for transition in system.transitions
    }
    return LTS(
        system.states,
        tuple(
            sorted(
                transitions,
                key=lambda item: (
                    item.src,
                    item.action,
                    item.dst,
                    item.duration,
                    item.cost,
                ),
            )
        ),
    )


def total_variation_distance(
    left: Mapping[str, Fraction], right: Mapping[str, Fraction]
) -> Fraction:
    support = set(left) | set(right)
    return Fraction(1, 2) * sum(
        abs(left.get(item, Fraction(0)) - right.get(item, Fraction(0)))
        for item in support
    )


def bernoulli_record_probability(
    success_probability: Fraction, record: SampleRecord
) -> Fraction:
    if success_probability < 0 or success_probability > 1:
        raise ValueError("success probability must lie in [0, 1]")
    probability = Fraction(1)
    for success in record:
        probability *= (
            success_probability if success else 1 - success_probability
        )
    return probability


def compose_two_step_distribution(
    system: ProbLTS,
    start: str,
    first_label: RichLabel,
    second_label: RichLabel,
) -> BlockDistribution:
    validate_prob_lts(system)
    first = _state_distribution(system, start, first_label)
    if not first:
        raise ValueError("first label is not enabled at start state")

    result: dict[str, Fraction] = {}
    for middle, first_probability in first:
        second = _state_distribution(system, middle, second_label)
        if not second:
            raise ValueError(
                "second label must be enabled at every reached middle state"
            )
        for target, second_probability in second:
            result[target] = (
                result.get(target, Fraction(0))
                + first_probability * second_probability
            )

    return tuple(sorted(result.items()))


def run_stochastic_comparison() -> tuple[StochasticResult, ...]:
    law_system = ProbLTS(
        ("p", "q", "o0", "o1"),
        (
            ProbTransition("p", "respond", "o0", Fraction(1, 2)),
            ProbTransition("p", "respond", "o1", Fraction(1, 2)),
            ProbTransition("q", "respond", "o0", Fraction(3, 4)),
            ProbTransition("q", "respond", "o1", Fraction(1, 4)),
        ),
    )
    law_observations = {
        "p": ("phase=start",),
        "q": ("phase=start",),
        "o0": ("output=0",),
        "o1": ("output=1",),
    }
    law_partition = probabilistic_bisimulation_partition(
        law_system, law_observations
    )
    p_distribution = dict(
        state_distribution(law_system, "p", ("respond", 0, 0))
    )
    q_distribution = dict(
        state_distribution(law_system, "q", ("respond", 0, 0))
    )
    tv_distance = total_variation_distance(
        p_distribution, q_distribution
    )

    record = (True, False, True, True)
    p_record_probability = bernoulli_record_probability(Fraction(1, 2), record)
    q_record_probability = bernoulli_record_probability(Fraction(3, 4), record)

    label_system = ProbLTS(
        ("r0", "r1", "z0", "z1"),
        (
            ProbTransition(
                "r0", "go", "z0", Fraction(1), duration=1, cost=1
            ),
            ProbTransition(
                "r1", "go", "z1", Fraction(1), duration=100, cost=1
            ),
        ),
    )
    label_observations = {
        "r0": ("phase=start",),
        "r1": ("phase=start",),
        "z0": ("phase=done",),
        "z1": ("phase=done",),
    }
    label_partition = probabilistic_bisimulation_partition(
        label_system, label_observations
    )

    quotient_source = ProbLTS(
        ("x0", "x1", "a0", "a1", "b0", "b1"),
        (
            ProbTransition("x0", "respond", "a0", Fraction(1, 3)),
            ProbTransition("x0", "respond", "b0", Fraction(2, 3)),
            ProbTransition("x1", "respond", "a1", Fraction(1, 3)),
            ProbTransition("x1", "respond", "b1", Fraction(2, 3)),
        ),
    )
    quotient_observations = {
        "x0": ("phase=start",),
        "x1": ("phase=start",),
        "a0": ("output=A",),
        "a1": ("output=A",),
        "b0": ("output=B",),
        "b1": ("output=B",),
    }
    quotient_partition = probabilistic_bisimulation_partition(
        quotient_source, quotient_observations
    )
    quotient_stable = stable_probabilistic_partition(
        quotient_source,
        quotient_observations,
        quotient_partition,
    )
    quotient = quotient_prob_lts(
        quotient_source,
        quotient_observations,
        quotient_partition,
    )

    composition_system = ProbLTS(
        ("s", "m0", "m1", "o0", "o1"),
        (
            ProbTransition("s", "choose", "m0", Fraction(1, 3)),
            ProbTransition("s", "choose", "m1", Fraction(2, 3)),
            ProbTransition("m0", "emit", "o0", Fraction(1, 2)),
            ProbTransition("m0", "emit", "o1", Fraction(1, 2)),
            ProbTransition("m1", "emit", "o0", Fraction(1, 4)),
            ProbTransition("m1", "emit", "o1", Fraction(3, 4)),
        ),
    )
    composed = compose_two_step_distribution(
        composition_system,
        "s",
        ("choose", 0, 0),
        ("emit", 0, 0),
    )

    law_a = ProbLTS(
        ("s", "o0", "o1"),
        (
            ProbTransition("s", "respond", "o0", Fraction(1, 2)),
            ProbTransition("s", "respond", "o1", Fraction(1, 2)),
        ),
    )
    law_b = ProbLTS(
        ("s", "o0", "o1"),
        (
            ProbTransition("s", "respond", "o0", Fraction(3, 4)),
            ProbTransition("s", "respond", "o1", Fraction(1, 4)),
        ),
    )
    support_category_agrees = free_category_morphisms(
        support_lts(law_a), 1
    ) == free_category_morphisms(support_lts(law_b), 1)
    exact_law_differs = state_distribution(
        law_a, "s", ("respond", 0, 0)
    ) != state_distribution(law_b, "s", ("respond", 0, 0))

    return (
        StochasticResult(
            "SUPPORT_EQUALITY_LOSES_STOCHASTIC_LAW",
            support_successors(law_system, "p")
            == support_successors(law_system, "q")
            and not equivalent(law_partition, "p", "q")
            and tv_distance == Fraction(1, 4),
            "same labeled support hides a nonzero exact response-law distance",
        ),
        StochasticResult(
            "FINITE_RECORD_COMPATIBILITY_IS_NOT_KERNEL_IDENTITY",
            p_record_probability > 0
            and q_record_probability > 0
            and Fraction(1, 2) != Fraction(3, 4),
            "one finite record can have nonzero likelihood under distinct kernels",
        ),
        StochasticResult(
            "RICH_LABELS_SURVIVE_STOCHASTIC_QUOTIENT",
            not equivalent(label_partition, "r0", "r1"),
            "equal successor observations do not erase deadline-relevant duration",
        ),
        StochasticResult(
            "PROBABILISTIC_BISIMULATION_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
            equivalent(quotient_partition, "x0", "x1")
            and equivalent(quotient_partition, "a0", "a1")
            and equivalent(quotient_partition, "b0", "b1")
            and quotient_stable
            and len(quotient.states) == 3,
            "equivalent representatives induce the same exact block-valued kernel",
        ),
        StochasticResult(
            "KERNEL_COMPOSITION_REMAINS_TRANSITION_DERIVABLE",
            composed
            == (
                ("o0", Fraction(1, 3)),
                ("o1", Fraction(2, 3)),
            ),
            "two-step response laws compose exactly by finite kernel multiplication",
        ),
        StochasticResult(
            "ORDINARY_PATH_CATEGORY_FORGETS_PROBABILITY",
            support_category_agrees and exact_law_differs,
            "the same support-path category can encode different stochastic laws",
        ),
    )


def main() -> int:
    results = run_stochastic_comparison()
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}: {result.detail}")

    passed = sum(result.passed for result in results)
    print(f"{passed}/{len(results)} stochastic comparisons passed")
    if passed == len(results):
        print(
            "VERDICT: finite exact evidence favors richly labeled stochastic "
            "kernels + declared observations + exact probabilistic bisimulation; "
            "ordinary support-path categories forget probability, while "
            "probability-aware categorical structure remains optional derived IR"
        )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
