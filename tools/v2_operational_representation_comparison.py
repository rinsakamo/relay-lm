"""Finite comparison of graph, LTS, category, and DAG views for #2209.

This is research falsification apparatus, not RelayLM runtime or architecture
authority. It asks which representation is sufficient for the current finite
Operational Grand Null witnesses without promoting any representation to an
ontology.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Transition:
    src: str
    action: str
    dst: str
    duration: int = 0
    cost: int = 0


@dataclass(frozen=True)
class LTS:
    states: tuple[str, ...]
    transitions: tuple[Transition, ...]


@dataclass(frozen=True)
class ComparisonResult:
    name: str
    passed: bool
    detail: str


Path = tuple[str, ...]
Partition = Mapping[str, str]
TimedState = tuple[str, int]
TransitionSignature = tuple[str, str, int, int]


def underlying_graph(lts: LTS) -> frozenset[tuple[str, str]]:
    return frozenset((transition.src, transition.dst) for transition in lts.transitions)


def enabled_under_deadline(
    lts: LTS, deadline: int
) -> frozenset[tuple[str, str, str]]:
    if deadline < 0:
        raise ValueError("deadline must be non-negative")
    return frozenset(
        (transition.src, transition.action, transition.dst)
        for transition in lts.transitions
        if transition.duration <= deadline
    )


def labeled_paths(lts: LTS, max_steps: int) -> frozenset[Path]:
    if max_steps < 0:
        raise ValueError("max_steps must be non-negative")
    paths: set[Path] = {(state,) for state in lts.states}
    frontier = set(paths)
    for _ in range(max_steps):
        next_frontier: set[Path] = set()
        for path in frontier:
            for transition in lts.transitions:
                if transition.src == path[-1]:
                    extended = path + (transition.action, transition.dst)
                    if extended not in paths:
                        paths.add(extended)
                        next_frontier.add(extended)
        frontier = next_frontier
        if not frontier:
            break
    return frozenset(paths)


def free_category_morphisms(lts: LTS, max_steps: int) -> frozenset[Path]:
    if max_steps < 0:
        raise ValueError("max_steps must be non-negative")
    morphisms: set[Path] = {(state,) for state in lts.states}
    morphisms.update(
        (transition.src, transition.action, transition.dst)
        for transition in lts.transitions
    )
    changed = True
    while changed:
        changed = False
        current = tuple(morphisms)
        for left, right in product(current, repeat=2):
            left_steps = (len(left) - 1) // 2
            right_steps = (len(right) - 1) // 2
            if left[-1] != right[0] or left_steps + right_steps > max_steps:
                continue
            composite = left + right[1:]
            if composite not in morphisms:
                morphisms.add(composite)
                changed = True
    return frozenset(morphisms)


def transition_congruence(lts: LTS, partition: Partition) -> bool:
    if set(partition) != set(lts.states):
        raise ValueError("partition must cover every LTS state exactly once")

    signatures: dict[str, frozenset[TransitionSignature]] = {}
    for state in lts.states:
        signatures[state] = frozenset(
            (
                transition.action,
                partition[transition.dst],
                transition.duration,
                transition.cost,
            )
            for transition in lts.transitions
            if transition.src == state
        )

    return all(
        partition[left] != partition[right]
        or signatures[left] == signatures[right]
        for left, right in product(lts.states, repeat=2)
    )


def quotient_lts(lts: LTS, partition: Partition) -> LTS:
    if not transition_congruence(lts, partition):
        raise ValueError("partition is not a richly labeled-transition congruence")

    states = tuple(sorted(set(partition.values())))
    transitions = tuple(
        sorted(
            {
                Transition(
                    partition[transition.src],
                    transition.action,
                    partition[transition.dst],
                    transition.duration,
                    transition.cost,
                )
                for transition in lts.transitions
            },
            key=lambda item: (
                item.src,
                item.action,
                item.dst,
                item.duration,
                item.cost,
            ),
        )
    )
    return LTS(states, transitions)


def has_cycle(
    states: Sequence[str] | Sequence[TimedState],
    edges: Sequence[tuple[str, str]] | Sequence[tuple[TimedState, TimedState]],
) -> bool:
    adjacency: dict[object, list[object]] = {state: [] for state in states}
    for source, target in edges:
        adjacency.setdefault(source, []).append(target)

    visiting: set[object] = set()
    visited: set[object] = set()

    def visit(state: object) -> bool:
        if state in visiting:
            return True
        if state in visited:
            return False
        visiting.add(state)
        for target in adjacency.get(state, ()):
            if visit(target):
                return True
        visiting.remove(state)
        visited.add(state)
        return False

    return any(visit(state) for state in states if state not in visited)


def time_unroll(
    lts: LTS, depth: int
) -> tuple[frozenset[TimedState], frozenset[tuple[TimedState, TimedState]]]:
    if depth < 0:
        raise ValueError("depth must be non-negative")
    states: set[TimedState] = {(state, 0) for state in lts.states}
    frontier = set(states)
    edges: set[tuple[TimedState, TimedState]] = set()

    for time in range(depth):
        next_frontier: set[TimedState] = set()
        for state, _ in frontier:
            for transition in lts.transitions:
                if transition.src == state:
                    source = (state, time)
                    target = (transition.dst, time + 1)
                    states.add(source)
                    states.add(target)
                    edges.add((source, target))
                    next_frontier.add(target)
        frontier = next_frontier
        if not frontier:
            break

    return frozenset(states), frozenset(edges)


def run_comparison() -> tuple[ComparisonResult, ...]:
    fast = LTS(("A", "B"), (Transition("A", "go", "B", duration=1),))
    slow = LTS(("A", "B"), (Transition("A", "go", "B", duration=100),))
    graph_agrees = underlying_graph(fast) == underlying_graph(slow)
    deadline_differs = enabled_under_deadline(fast, 10) != enabled_under_deadline(slow, 10)

    parallel_actions = LTS(
        ("A", "B"),
        (
            Transition("A", "read", "B"),
            Transition("A", "delete", "B"),
        ),
    )
    graph_parallel_count = len(underlying_graph(parallel_actions))
    lts_parallel_count = len(parallel_actions.transitions)

    path_lts = LTS(
        ("X", "Y", "Z"),
        (
            Transition("X", "a", "Y"),
            Transition("Y", "b", "Z"),
        ),
    )
    lts_paths = labeled_paths(path_lts, 2)
    category_paths = free_category_morphisms(path_lts, 2)

    bad_lts = LTS(
        ("x0", "x1", "y", "z"),
        (
            Transition("x0", "go", "y"),
            Transition("x1", "go", "z"),
        ),
    )
    bad_partition = {"x0": "X", "x1": "X", "y": "Y", "z": "Z"}
    bad_congruence = transition_congruence(bad_lts, bad_partition)

    label_sensitive_lts = LTS(
        ("x0", "x1", "y0", "y1"),
        (
            Transition("x0", "go", "y0", duration=1, cost=1),
            Transition("x1", "go", "y1", duration=100, cost=1),
        ),
    )
    label_partition = {"x0": "X", "x1": "X", "y0": "Y", "y1": "Y"}
    label_sensitive_congruence = transition_congruence(
        label_sensitive_lts, label_partition
    )

    good_lts = LTS(
        ("x0", "x1", "y0", "y1"),
        (
            Transition("x0", "go", "y0"),
            Transition("x1", "go", "y1"),
        ),
    )
    good_partition = {"x0": "X", "x1": "X", "y0": "Y", "y1": "Y"}
    good_congruence = transition_congruence(good_lts, good_partition)
    quotient = quotient_lts(good_lts, good_partition)
    quotient_expected = LTS(("X", "Y"), (Transition("X", "go", "Y"),))
    quotient_paths_agree = labeled_paths(quotient, 2) == free_category_morphisms(
        quotient, 2
    )

    cyclic_lts = LTS(
        ("X", "Y"),
        (
            Transition("X", "tick", "Y"),
            Transition("Y", "tick", "X"),
        ),
    )
    cyclic_edges = tuple((item.src, item.dst) for item in cyclic_lts.transitions)
    unrolled_states, unrolled_edges = time_unroll(cyclic_lts, 3)

    return (
        ComparisonResult(
            "PLAIN_GRAPH_LOSES_OPERATIONAL_LABELS",
            graph_agrees and deadline_differs,
            "same A->B graph hides 1s versus 100s deadline behavior",
        ),
        ComparisonResult(
            "PLAIN_GRAPH_LOSES_ACTION_IDENTITY",
            graph_parallel_count == 1 and lts_parallel_count == 2,
            "parallel read/delete actions collapse to one unlabeled A->B edge",
        ),
        ComparisonResult(
            "FREE_CATEGORY_IS_DERIVED_PATH_CLOSURE",
            lts_paths == category_paths,
            "finite free-category morphisms equal the action-labeled LTS paths",
        ),
        ComparisonResult(
            "QUOTIENT_REQUIRES_TRANSITION_CONGRUENCE",
            not bad_congruence and not label_sensitive_congruence,
            "state merging fails when target classes or operational edge labels differ",
        ),
        ComparisonResult(
            "CONGRUENT_QUOTIENT_REMAINS_LTS_DERIVABLE",
            good_congruence and quotient == quotient_expected and quotient_paths_agree,
            "valid quotient LTS is well-defined before its free category is derived",
        ),
        ComparisonResult(
            "DAG_IS_TIME_UNROLLED_HISTORY_PROJECTION",
            has_cycle(cyclic_lts.states, cyclic_edges)
            and not has_cycle(tuple(unrolled_states), tuple(unrolled_edges)),
            "cyclic mechanism becomes acyclic only after explicit temporal unrolling",
        ),
    )


def main() -> int:
    results = run_comparison()
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}: {result.detail}")
    passed = sum(result.passed for result in results)
    print(f"{passed}/{len(results)} comparisons passed")
    if passed == len(results):
        print(
            "VERDICT: current finite evidence favors richly labeled transitions + "
            "exact declared transition congruence as the simpler core; category "
            "remains derivable compositional IR, and DAG remains a time-unrolled "
            "history projection"
        )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
