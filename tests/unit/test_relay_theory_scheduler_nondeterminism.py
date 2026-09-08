from fractions import Fraction

import pytest

from tools.relay_theory_scheduler_nondeterminism import (
    Alternative,
    ChoiceState,
    behavior_equivalent,
    exact_convex_hulls_equal,
    exact_distribution,
    flattened_max_probability,
    in_exact_convex_hull,
    induced_distribution,
    max_outcome_probability,
    max_probability_for_owner,
    partition_is_representative_independent,
    policy_factorizes_through_quotient,
    policy_is_observation_based,
    run_scheduler_comparison,
    scheduler_behavior_partition,
)


def delta(outcome: str):
    return exact_distribution({outcome: Fraction(1)})


def half():
    return exact_distribution({"L": Fraction(1, 2), "R": Fraction(1, 2)})


def test_scheduler_comparison_passes() -> None:
    results = run_scheduler_comparison()

    assert [result.name for result in results] == [
        "ONE_RESOLVED_KERNEL_LOSES_CHOICE",
        "SCHEDULER_CLASS_CHANGES_QUOTIENT",
        "RANDOMIZED_SEMANTICS_USES_EXACT_CONVEX_CLOSURE",
        "HISTORY_VISIBLE_CHOICE_BREAKS_STATE_QUOTIENT",
        "PARTIAL_INFORMATION_RESTRICTS_ADMISSIBLE_POLICY",
        "CHOICE_OWNERSHIP_IS_NOT_ONE_SCHEDULER",
        "SCHEDULER_RELATIVE_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
    ]
    assert all(result.passed for result in results)


def test_exact_probability_and_scheduler_weights_reject_float() -> None:
    with pytest.raises(TypeError, match="fractions.Fraction"):
        exact_distribution({"L": 1.0})  # type: ignore[dict-item]

    state = ChoiceState(
        "s",
        (
            Alternative("a", delta("L")),
            Alternative("b", delta("R")),
        ),
    )
    with pytest.raises(TypeError, match="fractions.Fraction"):
        induced_distribution(
            state,
            {"a": 0.5, "b": 0.5},  # type: ignore[dict-item]
        )


def test_one_scheduler_resolution_does_not_identify_nondeterministic_process() -> None:
    selectable = ChoiceState(
        "s",
        (
            Alternative("a", delta("L")),
            Alternative("b", delta("R")),
        ),
    )
    fixed_mixture = ChoiceState("t", (Alternative("c", half()),))

    assert induced_distribution(
        selectable,
        {"a": Fraction(1, 2), "b": Fraction(1, 2)},
    ) == half()
    assert max_outcome_probability(selectable, "L", "randomized") == 1
    assert max_outcome_probability(fixed_mixture, "L", "randomized") == Fraction(
        1, 2
    )


def test_scheduler_class_changes_exact_behavioral_quotient() -> None:
    extremes = ChoiceState(
        "s",
        (
            Alternative("a", delta("L")),
            Alternative("b", delta("R")),
        ),
    )
    explicit_mixture = ChoiceState(
        "u",
        (
            Alternative("a", delta("L")),
            Alternative("b", delta("R")),
            Alternative("m", half()),
        ),
    )

    assert not behavior_equivalent(extremes, explicit_mixture, "deterministic")
    assert behavior_equivalent(extremes, explicit_mixture, "randomized")


def test_randomized_scheduler_semantics_uses_exact_convex_closure() -> None:
    left = (delta("L"), delta("R"))
    right = (delta("L"), delta("R"), half())
    outside = exact_distribution({"C": Fraction(1)})

    assert in_exact_convex_hull(half(), left)
    assert exact_convex_hulls_equal(left, right)
    assert not in_exact_convex_hull(outside, left)


def test_history_sensitive_policy_must_factor_through_state_quotient() -> None:
    h1 = ("start", "left")
    h2 = ("start", "right")
    policy = {h1: "a", h2: "b"}

    assert not policy_factorizes_through_quotient(
        policy,
        {h1: "collapsed", h2: "collapsed"},
    )
    assert policy_factorizes_through_quotient(
        policy,
        {h1: "left", h2: "right"},
    )


def test_partial_information_restricts_admissible_history_policy() -> None:
    h1 = ("start", "left")
    h2 = ("start", "right")
    policy = {h1: "a", h2: "b"}

    assert not policy_is_observation_based(
        policy,
        {h1: "same", h2: "same"},
    )
    assert policy_is_observation_based(
        policy,
        {h1: "left", h2: "right"},
    )


def test_flattening_choice_ownership_grants_false_control() -> None:
    system = ChoiceState(
        "owned",
        (
            Alternative("self-safe", half(), owner="SELF"),
            Alternative("world-good", delta("L"), owner="WORLD"),
            Alternative("world-bad", delta("R"), owner="WORLD"),
        ),
    )

    assert max_probability_for_owner(system, "SELF", "L") == Fraction(1, 2)
    assert flattened_max_probability(system, "L") == 1


def test_scheduler_relative_quotient_is_representative_independent() -> None:
    s = ChoiceState(
        "s",
        (
            Alternative("a", delta("L")),
            Alternative("b", delta("R")),
        ),
    )
    u = ChoiceState(
        "u",
        (
            Alternative("a", delta("L")),
            Alternative("b", delta("R")),
            Alternative("m", half()),
        ),
    )
    t = ChoiceState("t", (Alternative("c", half()),))
    states = (s, u, t)
    observations = {state.name: ("phase=start",) for state in states}

    deterministic = scheduler_behavior_partition(
        states,
        observations,
        "deterministic",
    )
    randomized = scheduler_behavior_partition(
        states,
        observations,
        "randomized",
    )

    assert deterministic["s"] != deterministic["u"]
    assert randomized["s"] == randomized["u"]
    assert partition_is_representative_independent(
        states,
        observations,
        randomized,
        "randomized",
    )
