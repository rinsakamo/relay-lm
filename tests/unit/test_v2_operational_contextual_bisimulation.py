from tools.v2_operational_contextual_bisimulation import (
    equivalent,
    partition_refines,
    run_contextual_comparison,
    stable_observed_partition,
    strong_bisimulation_partition,
    trace_signatures,
)
from tools.v2_operational_representation_comparison import LTS, Transition


def test_contextual_bisimulation_comparison_passes() -> None:
    results = run_contextual_comparison()
    assert [result.name for result in results] == [
        "TRACE_EQUALITY_IS_WEAKER_THAN_BISIMULATION",
        "FUTURE_CONTEXT_SPLITS_ENDPOINT_EQUIVALENCE",
        "BISIMULATION_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
        "PROBE_REFINEMENT_SPLITS_EQUIVALENCE_MONOTONICALLY",
        "CATEGORY_REMAINS_DERIVED_AFTER_BISIMULATION_QUOTIENT",
    ]
    assert all(result.passed for result in results)


def test_trace_equivalent_branching_processes_need_not_be_bisimilar() -> None:
    lts = LTS(
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
    observations = {state: () for state in lts.states}
    partition = strong_bisimulation_partition(lts, observations)

    assert trace_signatures(lts, "p", 2) == trace_signatures(lts, "q", 2)
    assert not equivalent(partition, "p", "q")


def test_future_declared_context_breaks_visible_endpoint_merge() -> None:
    lts = LTS(
        ("y0", "y1", "o0", "o1"),
        (
            Transition("y0", "read", "o0"),
            Transition("y1", "read", "o1"),
        ),
    )
    observations = {
        "y0": ("visible=0",),
        "y1": ("visible=0",),
        "o0": ("output=0",),
        "o1": ("output=1",),
    }
    flawed = {"y0": "Y", "y1": "Y", "o0": "O0", "o1": "O1"}
    partition = strong_bisimulation_partition(lts, observations)

    assert observations["y0"] == observations["y1"]
    assert not equivalent(partition, "y0", "y1")
    assert not stable_observed_partition(lts, observations, flawed)


def test_bisimulation_partition_is_representative_independent() -> None:
    lts = LTS(
        ("x0", "x1", "z0", "z1"),
        (
            Transition("x0", "go", "z0", duration=2, cost=1),
            Transition("x1", "go", "z1", duration=2, cost=1),
        ),
    )
    observations = {
        "x0": ("phase=x",),
        "x1": ("phase=x",),
        "z0": ("phase=z",),
        "z1": ("phase=z",),
    }
    partition = strong_bisimulation_partition(lts, observations)

    assert equivalent(partition, "x0", "x1")
    assert equivalent(partition, "z0", "z1")
    assert stable_observed_partition(lts, observations, partition)


def test_probe_refinement_splits_without_action_expansion() -> None:
    lts = LTS(("u0", "u1"), ())
    coarse = {"u0": ("visible=0",), "u1": ("visible=0",)}
    fine = {
        "u0": ("visible=0", "audit=left"),
        "u1": ("visible=0", "audit=right"),
    }
    coarse_partition = strong_bisimulation_partition(lts, coarse)
    fine_partition = strong_bisimulation_partition(lts, fine)

    assert equivalent(coarse_partition, "u0", "u1")
    assert not equivalent(fine_partition, "u0", "u1")
    assert partition_refines(fine_partition, coarse_partition)
