from tools.v2_operational_grand_null_checker import (
    canonical_map,
    compose_maps,
    partition_refines,
    run_checks,
    threshold_counterexample,
)


def test_selected_operational_grand_null_gates_pass() -> None:
    results = run_checks()
    assert [result.gate for result in results] == ["C0", "C3", "C4", "C11", "C12", "C15"]
    assert all(result.passed for result in results)


def test_c0_threshold_closeness_is_not_forced_transitive() -> None:
    assert threshold_counterexample((0.0, 0.75, 1.5), 1.0) is not None


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
