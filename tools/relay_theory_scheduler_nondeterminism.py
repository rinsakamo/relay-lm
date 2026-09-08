"""Exact finite scheduler-sensitive nondeterminism apparatus for Relay Theory #2353.

This is deterministic research falsification apparatus, not RelayLM runtime or
architecture authority. It attacks the single stochastic-kernel minimum earned
at #2209 / PR #2346 by allowing selectable exact probability laws.

The scope is intentionally bounded:

- finite one-step outcome distributions;
- exact ``fractions.Fraction`` probability mass;
- deterministic versus randomized scheduler semantics;
- exact convex-hull comparison without floating-point approximation;
- deterministic history-sensitive policy visibility;
- explicit choice ownership as an anti-flattening discriminator.

It does not assume that an MDP, scheduler, convex set, stochastic game, or
Markov category is a primitive of Relay Theory.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from typing import Literal

Distribution = tuple[tuple[str, Fraction], ...]
SchedulerClass = Literal["deterministic", "randomized"]
Observation = tuple[str, ...]
History = tuple[str, ...]


@dataclass(frozen=True)
class Alternative:
    name: str
    distribution: Distribution
    owner: str = "scheduler"


@dataclass(frozen=True)
class ChoiceState:
    name: str
    alternatives: tuple[Alternative, ...]


@dataclass(frozen=True)
class SchedulerResult:
    name: str
    passed: bool
    detail: str


def exact_distribution(weights: Mapping[str, Fraction]) -> Distribution:
    """Build a normalized exact rational distribution."""
    if not weights:
        raise ValueError("distribution must contain at least one outcome")

    cleaned: list[tuple[str, Fraction]] = []
    total = Fraction(0)
    for outcome, probability_mass in weights.items():
        if not isinstance(probability_mass, Fraction):
            raise TypeError(
                "probability must be fractions.Fraction for exact semantics"
            )
        if probability_mass < 0 or probability_mass > 1:
            raise ValueError("probabilities must lie in [0, 1]")
        total += probability_mass
        if probability_mass:
            cleaned.append((outcome, probability_mass))

    if total != 1:
        raise ValueError("distribution probabilities must sum exactly to 1")
    return tuple(sorted(cleaned))


def _validated_distribution(distribution: Distribution) -> Distribution:
    seen: set[str] = set()
    weights: dict[str, Fraction] = {}
    for outcome, probability_mass in distribution:
        if outcome in seen:
            raise ValueError("distribution outcomes must be unique")
        seen.add(outcome)
        weights[outcome] = probability_mass
    return exact_distribution(weights)


def validate_choice_state(state: ChoiceState) -> None:
    if not state.alternatives:
        raise ValueError("choice state must expose at least one alternative")

    names: set[str] = set()
    for alternative in state.alternatives:
        if alternative.name in names:
            raise ValueError("alternative names must be unique within a state")
        names.add(alternative.name)
        if not alternative.owner:
            raise ValueError("alternative owner must be non-empty")
        _validated_distribution(alternative.distribution)


def probability(distribution: Distribution, outcome: str) -> Fraction:
    return dict(_validated_distribution(distribution)).get(outcome, Fraction(0))


def induced_distribution(
    state: ChoiceState,
    scheduler_weights: Mapping[str, Fraction],
) -> Distribution:
    """Resolve a randomized scheduler into one exact stochastic law."""
    validate_choice_state(state)
    alternatives = {
        alternative.name: alternative for alternative in state.alternatives
    }
    unknown = set(scheduler_weights) - set(alternatives)
    if unknown:
        raise ValueError(f"unknown scheduler alternatives: {sorted(unknown)}")
    if not scheduler_weights:
        raise ValueError("scheduler must assign weight to at least one alternative")

    total_weight = Fraction(0)
    outcome_weights: dict[str, Fraction] = {}
    for name, weight in scheduler_weights.items():
        if not isinstance(weight, Fraction):
            raise TypeError("scheduler weights must be fractions.Fraction")
        if weight < 0 or weight > 1:
            raise ValueError("scheduler weights must lie in [0, 1]")
        total_weight += weight
        for outcome, probability_mass in _validated_distribution(
            alternatives[name].distribution
        ):
            outcome_weights[outcome] = (
                outcome_weights.get(outcome, Fraction(0))
                + weight * probability_mass
            )

    if total_weight != 1:
        raise ValueError("scheduler weights must sum exactly to 1")
    return exact_distribution(outcome_weights)


def deterministic_laws(state: ChoiceState) -> tuple[Distribution, ...]:
    validate_choice_state(state)
    return tuple(
        sorted(
            {
                _validated_distribution(alternative.distribution)
                for alternative in state.alternatives
            },
            key=repr,
        )
    )


def _vector(
    distribution: Distribution,
    outcomes: Sequence[str],
) -> tuple[Fraction, ...]:
    weights = dict(_validated_distribution(distribution))
    return tuple(weights.get(outcome, Fraction(0)) for outcome in outcomes)


def _solve_unique(
    matrix: Sequence[Sequence[Fraction]],
    rhs: Sequence[Fraction],
    nvars: int,
) -> tuple[Fraction, ...] | None:
    """Solve an exact overdetermined linear system when the solution is unique."""
    augmented = [
        [Fraction(value) for value in row] + [Fraction(value_rhs)]
        for row, value_rhs in zip(matrix, rhs, strict=True)
    ]
    pivot_rows: dict[int, int] = {}
    next_row = 0

    for col in range(nvars):
        pivot = next(
            (
                row
                for row in range(next_row, len(augmented))
                if augmented[row][col]
            ),
            None,
        )
        if pivot is None:
            continue

        augmented[next_row], augmented[pivot] = (
            augmented[pivot],
            augmented[next_row],
        )
        scale = augmented[next_row][col]
        augmented[next_row] = [value / scale for value in augmented[next_row]]

        for row in range(len(augmented)):
            if row == next_row:
                continue
            factor = augmented[row][col]
            if factor:
                augmented[row] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(
                        augmented[row], augmented[next_row], strict=True
                    )
                ]

        pivot_rows[col] = next_row
        next_row += 1

    for row in augmented:
        if all(value == 0 for value in row[:nvars]) and row[nvars] != 0:
            return None
    if len(pivot_rows) != nvars:
        return None

    solution = [Fraction(0) for _ in range(nvars)]
    for col, row in pivot_rows.items():
        solution[col] = augmented[row][nvars]
    return tuple(solution)


def in_exact_convex_hull(
    target: Distribution,
    generators: Sequence[Distribution],
) -> bool:
    """Test exact rational convex-hull membership for a finite generator set.

    A feasible point in a finite probability simplex has a representation on
    an affinely independent subset. We enumerate bounded supports and solve the
    resulting systems exactly with ``Fraction`` rather than enumerating
    randomized scheduler probabilities or approximating real mixtures.
    """
    target = _validated_distribution(target)
    canonical_generators = tuple(
        _validated_distribution(item) for item in generators
    )
    if not canonical_generators:
        return False

    outcomes = tuple(
        sorted(
            {
                outcome
                for distribution in (target, *canonical_generators)
                for outcome, _ in distribution
            }
        )
    )
    target_vector = _vector(target, outcomes)
    generator_vectors = tuple(
        _vector(item, outcomes) for item in canonical_generators
    )

    # Probability vectors over d outcomes live in an affine space of
    # dimension at most d - 1, so at most d affinely independent generators
    # are needed for an exact witness.
    max_support = min(len(generator_vectors), max(1, len(outcomes)))

    for support_size in range(1, max_support + 1):
        for indices in combinations(range(len(generator_vectors)), support_size):
            selected = tuple(generator_vectors[index] for index in indices)
            matrix = [[Fraction(1) for _ in selected]]
            matrix.extend(
                [
                    [vector[row] for vector in selected]
                    for row in range(len(outcomes))
                ]
            )
            rhs = [Fraction(1), *target_vector]
            solution = _solve_unique(matrix, rhs, support_size)
            if solution is None or any(weight < 0 for weight in solution):
                continue
            if sum(solution, Fraction(0)) != 1:
                continue

            reconstructed = tuple(
                sum(
                    (
                        solution[col] * selected[col][row]
                        for col in range(support_size)
                    ),
                    Fraction(0),
                )
                for row in range(len(outcomes))
            )
            if reconstructed == target_vector:
                return True

    return False


def exact_convex_hulls_equal(
    left: Sequence[Distribution],
    right: Sequence[Distribution],
) -> bool:
    left_canonical = tuple(_validated_distribution(item) for item in left)
    right_canonical = tuple(_validated_distribution(item) for item in right)
    if not left_canonical or not right_canonical:
        return not left_canonical and not right_canonical

    return all(
        in_exact_convex_hull(item, right_canonical) for item in left_canonical
    ) and all(
        in_exact_convex_hull(item, left_canonical) for item in right_canonical
    )


def behavior_equivalent(
    left: ChoiceState,
    right: ChoiceState,
    scheduler_class: SchedulerClass,
) -> bool:
    """Compare hidden-action one-step behavior under declared scheduler semantics."""
    left_laws = deterministic_laws(left)
    right_laws = deterministic_laws(right)
    if scheduler_class == "deterministic":
        return left_laws == right_laws
    if scheduler_class == "randomized":
        return exact_convex_hulls_equal(left_laws, right_laws)
    raise ValueError(f"unknown scheduler class: {scheduler_class}")


def max_outcome_probability(
    state: ChoiceState,
    outcome: str,
    scheduler_class: SchedulerClass = "deterministic",
) -> Fraction:
    """Return the best attainable one-step outcome probability.

    For a linear outcome objective, randomized mixtures cannot exceed the best
    deterministic extreme point, so both supported scheduler classes share
    the same maximum in this bounded setting.
    """
    if scheduler_class not in {"deterministic", "randomized"}:
        raise ValueError(f"unknown scheduler class: {scheduler_class}")
    laws = deterministic_laws(state)
    return max(probability(law, outcome) for law in laws)


def policy_factorizes_through_quotient(
    policy: Mapping[History, str],
    quotient_state: Mapping[History, str],
) -> bool:
    """Check whether a deterministic history policy survives a quotient."""
    decisions: dict[str, str] = {}
    for history, action in policy.items():
        if history not in quotient_state:
            raise ValueError(f"missing quotient state for history: {history!r}")
        block = quotient_state[history]
        existing = decisions.setdefault(block, action)
        if existing != action:
            return False
    return True


def policy_is_observation_based(
    policy: Mapping[History, str],
    visible_observation: Mapping[History, str],
) -> bool:
    """Check that a deterministic policy uses only declared visible information."""
    decisions: dict[str, str] = {}
    for history, action in policy.items():
        if history not in visible_observation:
            raise ValueError(
                f"missing visible observation for history: {history!r}"
            )
        observation = visible_observation[history]
        existing = decisions.setdefault(observation, action)
        if existing != action:
            return False
    return True


def max_probability_for_owner(
    state: ChoiceState,
    owner: str,
    outcome: str,
) -> Fraction:
    """Project attainable alternatives to one declared choice authority."""
    validate_choice_state(state)
    controlled = [
        _validated_distribution(alternative.distribution)
        for alternative in state.alternatives
        if alternative.owner == owner
    ]
    if not controlled:
        raise ValueError(f"owner {owner!r} controls no alternatives")
    return max(probability(law, outcome) for law in controlled)


def flattened_max_probability(state: ChoiceState, outcome: str) -> Fraction:
    """Expose the anti-model that grants one chooser every alternative."""
    return max_outcome_probability(state, outcome, "deterministic")


def scheduler_behavior_partition(
    states: Sequence[ChoiceState],
    observations: Mapping[str, Observation],
    scheduler_class: SchedulerClass,
) -> dict[str, str]:
    """Build a bounded exact one-step scheduler-relative behavioral quotient."""
    names = [state.name for state in states]
    if len(set(names)) != len(names):
        raise ValueError("state names must be unique")

    for state in states:
        validate_choice_state(state)
        if state.name not in observations:
            raise ValueError(f"missing observation for state {state.name!r}")

    partition: dict[str, str] = {}
    representatives: list[ChoiceState] = []
    for state in states:
        block: str | None = None
        for index, representative in enumerate(representatives):
            if observations[state.name] != observations[representative.name]:
                continue
            if behavior_equivalent(state, representative, scheduler_class):
                block = f"b{index}"
                break
        if block is None:
            representatives.append(state)
            block = f"b{len(representatives) - 1}"
        partition[state.name] = block

    return partition


def partition_is_representative_independent(
    states: Sequence[ChoiceState],
    observations: Mapping[str, Observation],
    partition: Mapping[str, str],
    scheduler_class: SchedulerClass,
) -> bool:
    """Verify that every quotient block has one scheduler-relative behavior."""
    by_name = {state.name: state for state in states}
    for name, block in partition.items():
        if name not in by_name:
            raise ValueError(f"partition references unknown state {name!r}")
        members = [
            candidate
            for candidate, member_block in partition.items()
            if member_block == block
        ]
        for other in members:
            if observations[name] != observations[other]:
                return False
            if not behavior_equivalent(
                by_name[name], by_name[other], scheduler_class
            ):
                return False
    return True


def _delta(outcome: str) -> Distribution:
    return exact_distribution({outcome: Fraction(1)})


def _half() -> Distribution:
    return exact_distribution(
        {"L": Fraction(1, 2), "R": Fraction(1, 2)}
    )


def run_scheduler_comparison() -> tuple[SchedulerResult, ...]:
    """Run the bounded #2353 N0-N6 exact falsification transaction."""
    s = ChoiceState(
        "s",
        (
            Alternative("a", _delta("L")),
            Alternative("b", _delta("R")),
        ),
    )
    t = ChoiceState("t", (Alternative("c", _half()),))
    u = ChoiceState(
        "u",
        (
            Alternative("a", _delta("L")),
            Alternative("b", _delta("R")),
            Alternative("m", _half()),
        ),
    )

    mixed_from_s = induced_distribution(
        s,
        {"a": Fraction(1, 2), "b": Fraction(1, 2)},
    )
    n0 = mixed_from_s == _half() and max_outcome_probability(
        s, "L", "randomized"
    ) != max_outcome_probability(t, "L", "randomized")

    deterministic_equal = behavior_equivalent(s, u, "deterministic")
    randomized_equal = behavior_equivalent(s, u, "randomized")
    n1_n2 = not deterministic_equal and randomized_equal

    h1 = ("start", "left")
    h2 = ("start", "right")
    policy = {h1: "a", h2: "b"}
    quotient = {h1: "q", h2: "q"}
    n3 = not policy_factorizes_through_quotient(policy, quotient)

    hidden_observation = {h1: "same", h2: "same"}
    full_observation = {h1: "left", h2: "right"}
    n4 = not policy_is_observation_based(
        policy, hidden_observation
    ) and policy_is_observation_based(policy, full_observation)

    ownership = ChoiceState(
        "owned",
        (
            Alternative("self-safe", _half(), owner="SELF"),
            Alternative("world-good", _delta("L"), owner="WORLD"),
            Alternative("world-bad", _delta("R"), owner="WORLD"),
        ),
    )
    n5 = (
        max_probability_for_owner(ownership, "SELF", "L") == Fraction(1, 2)
        and flattened_max_probability(ownership, "L") == 1
    )

    states = (s, u, t)
    observations = {state.name: ("phase=start",) for state in states}
    randomized_partition = scheduler_behavior_partition(
        states, observations, "randomized"
    )
    deterministic_partition = scheduler_behavior_partition(
        states, observations, "deterministic"
    )
    n6 = (
        randomized_partition["s"] == randomized_partition["u"]
        and deterministic_partition["s"] != deterministic_partition["u"]
        and partition_is_representative_independent(
            states,
            observations,
            randomized_partition,
            "randomized",
        )
    )

    return (
        SchedulerResult(
            "ONE_RESOLVED_KERNEL_LOSES_CHOICE",
            n0,
            "one randomized resolution matches a kernel while attainable "
            "extrema differ",
        ),
        SchedulerResult(
            "SCHEDULER_CLASS_CHANGES_QUOTIENT",
            n1_n2,
            "deterministic choice sees an extra mixed alternative; randomized "
            "choice absorbs it",
        ),
        SchedulerResult(
            "RANDOMIZED_SEMANTICS_USES_EXACT_CONVEX_CLOSURE",
            randomized_equal,
            "finite rational generator sets are compared by exact convex-hull "
            "equality",
        ),
        SchedulerResult(
            "HISTORY_VISIBLE_CHOICE_BREAKS_STATE_QUOTIENT",
            n3,
            "a history-sensitive policy does not factor through a quotient "
            "that erases its discriminator",
        ),
        SchedulerResult(
            "PARTIAL_INFORMATION_RESTRICTS_ADMISSIBLE_POLICY",
            n4,
            "the same policy is inadmissible when its distinguishing histories "
            "share one visible observation",
        ),
        SchedulerResult(
            "CHOICE_OWNERSHIP_IS_NOT_ONE_SCHEDULER",
            n5,
            "flattening WORLD alternatives into SELF control increases SELF's "
            "attainable maximum",
        ),
        SchedulerResult(
            "SCHEDULER_RELATIVE_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
            n6,
            "the bounded one-step quotient is stable only relative to the "
            "declared scheduler semantics",
        ),
    )
