from tools.v2_operational_representation_comparison import (
    LTS,
    Transition,
    enabled_under_deadline,
    free_category_morphisms,
    has_cycle,
    labeled_paths,
    quotient_lts,
    run_comparison,
    time_unroll,
    transition_congruence,
    underlying_graph,
)


def test_operational_representation_comparison_passes() -> None:
    results = run_comparison()
    assert [result.name for result in results] == [
        "PLAIN_GRAPH_LOSES_OPERATIONAL_LABELS",
        "PLAIN_GRAPH_LOSES_ACTION_IDENTITY",
        "FREE_CATEGORY_IS_DERIVED_PATH_CLOSURE",
        "QUOTIENT_REQUIRES_TRANSITION_CONGRUENCE",
        "CONGRUENT_QUOTIENT_REMAINS_LTS_DERIVABLE",
        "DAG_IS_TIME_UNROLLED_HISTORY_PROJECTION",
    ]
    assert all(result.passed for result in results)


def test_plain_graph_forgets_deadline_relevant_duration() -> None:
    fast = LTS(("A", "B"), (Transition("A", "go", "B", duration=1),))
    slow = LTS(("A", "B"), (Transition("A", "go", "B", duration=100),))

    assert underlying_graph(fast) == underlying_graph(slow)
    assert enabled_under_deadline(fast, 10) != enabled_under_deadline(slow, 10)


def test_free_category_paths_are_generated_by_lts_paths() -> None:
    lts = LTS(
        ("X", "Y", "Z"),
        (
            Transition("X", "a", "Y"),
            Transition("Y", "b", "Z"),
        ),
    )

    assert labeled_paths(lts, 2) == free_category_morphisms(lts, 2)


def test_non_congruent_state_merge_is_rejected_before_category_derivation() -> None:
    lts = LTS(
        ("x0", "x1", "y", "z"),
        (
            Transition("x0", "go", "y"),
            Transition("x1", "go", "z"),
        ),
    )
    partition = {"x0": "X", "x1": "X", "y": "Y", "z": "Z"}

    assert not transition_congruence(lts, partition)

    try:
        quotient_lts(lts, partition)
    except ValueError as exc:
        assert "congruence" in str(exc)
    else:
        raise AssertionError("non-congruent quotient must be rejected")


def test_duration_difference_prevents_operational_state_merge() -> None:
    lts = LTS(
        ("x0", "x1", "y0", "y1"),
        (
            Transition("x0", "go", "y0", duration=1, cost=1),
            Transition("x1", "go", "y1", duration=100, cost=1),
        ),
    )
    partition = {"x0": "X", "x1": "X", "y0": "Y", "y1": "Y"}

    assert not transition_congruence(lts, partition)


def test_congruent_quotient_is_a_well_defined_lts() -> None:
    lts = LTS(
        ("x0", "x1", "y0", "y1"),
        (
            Transition("x0", "go", "y0"),
            Transition("x1", "go", "y1"),
        ),
    )
    partition = {"x0": "X", "x1": "X", "y0": "Y", "y1": "Y"}

    assert transition_congruence(lts, partition)
    assert quotient_lts(lts, partition) == LTS(
        ("X", "Y"),
        (Transition("X", "go", "Y"),),
    )


def test_time_unrolling_projects_a_cycle_to_a_dag() -> None:
    lts = LTS(
        ("X", "Y"),
        (
            Transition("X", "tick", "Y"),
            Transition("Y", "tick", "X"),
        ),
    )
    edges = tuple((transition.src, transition.dst) for transition in lts.transitions)
    states, unrolled_edges = time_unroll(lts, 3)

    assert has_cycle(lts.states, edges)
    assert not has_cycle(tuple(states), tuple(unrolled_edges))
