from fractions import Fraction

import pytest

from tools.v2_operational_probabilistic_bisimulation import (
    ProbLTS,
    ProbTransition,
    bernoulli_record_probability,
    compose_two_step_distribution,
    equivalent,
    probabilistic_bisimulation_partition,
    quotient_prob_lts,
    run_stochastic_comparison,
    stable_probabilistic_partition,
    state_distribution,
    support_lts,
    support_successors,
    total_variation_distance,
    validate_prob_lts,
)
from tools.v2_operational_representation_comparison import free_category_morphisms


def test_stochastic_comparison_passes() -> None:
    results = run_stochastic_comparison()
    assert [result.name for result in results] == [
        "SUPPORT_EQUALITY_LOSES_STOCHASTIC_LAW",
        "FINITE_RECORD_COMPATIBILITY_IS_NOT_KERNEL_IDENTITY",
        "RICH_LABELS_SURVIVE_STOCHASTIC_QUOTIENT",
        "PROBABILISTIC_BISIMULATION_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
        "KERNEL_COMPOSITION_REMAINS_TRANSITION_DERIVABLE",
        "ORDINARY_PATH_CATEGORY_FORGETS_PROBABILITY",
    ]
    assert all(result.passed for result in results)


def test_exact_probability_type_rejects_float_input() -> None:
    invalid = ProbLTS(
        ("s", "o"),
        (ProbTransition("s", "respond", "o", 1.0),),  # type: ignore[arg-type]
    )

    with pytest.raises(TypeError, match="fractions.Fraction"):
        validate_prob_lts(invalid)


def test_probabilities_must_normalize_per_state_and_rich_label() -> None:
    invalid = ProbLTS(
        ("s", "o0", "o1"),
        (
            ProbTransition("s", "respond", "o0", Fraction(1, 2)),
            ProbTransition("s", "respond", "o1", Fraction(1, 4)),
        ),
    )

    with pytest.raises(ValueError, match="sum exactly to 1"):
        validate_prob_lts(invalid)


def test_same_support_does_not_imply_same_stochastic_law() -> None:
    system = ProbLTS(
        ("p", "q", "o0", "o1"),
        (
            ProbTransition("p", "respond", "o0", Fraction(1, 2)),
            ProbTransition("p", "respond", "o1", Fraction(1, 2)),
            ProbTransition("q", "respond", "o0", Fraction(3, 4)),
            ProbTransition("q", "respond", "o1", Fraction(1, 4)),
        ),
    )
    observations = {
        "p": ("phase=start",),
        "q": ("phase=start",),
        "o0": ("output=0",),
        "o1": ("output=1",),
    }
    partition = probabilistic_bisimulation_partition(system, observations)
    p_law = dict(state_distribution(system, "p", ("respond", 0, 0)))
    q_law = dict(state_distribution(system, "q", ("respond", 0, 0)))

    assert support_successors(system, "p") == support_successors(system, "q")
    assert total_variation_distance(p_law, q_law) == Fraction(1, 4)
    assert not equivalent(partition, "p", "q")


def test_one_finite_record_can_fit_distinct_exact_kernels() -> None:
    record = (True, False, True, True)

    assert bernoulli_record_probability(Fraction(1, 2), record) > 0
    assert bernoulli_record_probability(Fraction(3, 4), record) > 0
    assert Fraction(1, 2) != Fraction(3, 4)


def test_exact_probabilistic_bisimulation_gives_stable_quotient() -> None:
    system = ProbLTS(
        ("x0", "x1", "a0", "a1", "b0", "b1"),
        (
            ProbTransition("x0", "respond", "a0", Fraction(1, 3)),
            ProbTransition("x0", "respond", "b0", Fraction(2, 3)),
            ProbTransition("x1", "respond", "a1", Fraction(1, 3)),
            ProbTransition("x1", "respond", "b1", Fraction(2, 3)),
        ),
    )
    observations = {
        "x0": ("phase=start",),
        "x1": ("phase=start",),
        "a0": ("output=A",),
        "a1": ("output=A",),
        "b0": ("output=B",),
        "b1": ("output=B",),
    }
    partition = probabilistic_bisimulation_partition(system, observations)
    quotient = quotient_prob_lts(system, observations, partition)

    assert equivalent(partition, "x0", "x1")
    assert equivalent(partition, "a0", "a1")
    assert equivalent(partition, "b0", "b1")
    assert stable_probabilistic_partition(system, observations, partition)
    assert len(quotient.states) == 3


def test_duration_remains_part_of_stochastic_equivalence() -> None:
    system = ProbLTS(
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
    observations = {
        "r0": ("phase=start",),
        "r1": ("phase=start",),
        "z0": ("phase=done",),
        "z1": ("phase=done",),
    }
    partition = probabilistic_bisimulation_partition(system, observations)

    assert not equivalent(partition, "r0", "r1")


def test_two_step_stochastic_kernel_composes_exactly() -> None:
    system = ProbLTS(
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

    assert compose_two_step_distribution(
        system,
        "s",
        ("choose", 0, 0),
        ("emit", 0, 0),
    ) == (
        ("o0", Fraction(1, 3)),
        ("o1", Fraction(2, 3)),
    )


def test_ordinary_support_path_category_forgets_probability() -> None:
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

    assert free_category_morphisms(
        support_lts(law_a), 1
    ) == free_category_morphisms(support_lts(law_b), 1)
    assert state_distribution(
        law_a, "s", ("respond", 0, 0)
    ) != state_distribution(law_b, "s", ("respond", 0, 0))
