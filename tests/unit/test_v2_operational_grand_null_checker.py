from tools.v2_operational_grand_null_checker import (
    GroundingWitness,
    answer_probe,
    canonical_map,
    compose_maps,
    deadline_admissible,
    finite_function_exists,
    finite_sets_isomorphic,
    grounding_probe,
    partition_refines,
    resource_transition,
    run_checks,
    terminal_probe,
    threshold_counterexample,
)


def test_selected_operational_grand_null_gates_pass() -> None:
    results = run_checks()
    assert [result.gate for result in results] == [
        "C0",
        "C3",
        "C4",
        "C5",
        "C6",
        "C7",
        "C8",
        "C11",
        "C12",
        "C13",
        "C15",
    ]
    assert all(result.passed for result in results)


def test_c0_threshold_closeness_is_not_forced_transitive() -> None:
    assert threshold_counterexample((0.0, 0.75, 1.5), 1.0) is not None


def test_c5_resource_boundary_blocks_false_composition() -> None:
    remaining = resource_transition(1, 1)
    assert remaining == 0
    assert resource_transition(remaining, 1) is None


def test_c6_mutual_reachability_is_not_isomorphism() -> None:
    assert finite_function_exists(2, 1)
    assert finite_function_exists(1, 2)
    assert not finite_sets_isomorphic(2, 1)


def test_c7_restricted_probe_agreement_is_not_yoneda() -> None:
    assert terminal_probe(1) == terminal_probe(2)
    assert not finite_sets_isomorphic(1, 2)


def test_c8_answer_probe_does_not_reflect_grounding() -> None:
    grounded = GroundingWitness("same", True, True)
    self_authenticated = GroundingWitness("same", True, False)

    assert answer_probe(grounded) == answer_probe(self_authenticated)
    assert grounding_probe(grounded) != grounding_probe(self_authenticated)


def test_c11_rejects_non_monotone_frame_change() -> None:
    coarse = {"z1": "a0", "z2": "a1"}
    changed = {"z1": "b0", "z2": "b0"}
    assert not partition_refines(changed, coarse)


def test_c12_canonical_nested_quotient_maps_are_coherent() -> None:
    fine = {"a": "a", "b": "b", "c": "c"}
    middle = {"a": "ab", "b": "ab", "c": "c"}
    coarse = {"a": "all", "b": "all", "c": "all"}

    fine_to_middle = canonical_map(fine, middle)
    middle_to_coarse = canonical_map(middle, coarse)
    fine_to_coarse = canonical_map(fine, coarse)

    assert compose_maps(fine_to_middle, middle_to_coarse) == fine_to_coarse


def test_c13_reachability_does_not_eliminate_deadline() -> None:
    assert deadline_admissible(1, 10)
    assert not deadline_admissible(100, 10)
