from fractions import Fraction

import pytest

from tools.relay_theory_correlation_authority import (
    ConditionalFamily,
    InterventionFamily,
    ResourceDescription,
    best_remote_guess_probability,
    binary_distribution,
    canonical_control_partition,
    common_cause_coupling,
    conditional_best_target_probability,
    deterministic_joint,
    family_contains,
    full_joint_family,
    independent_joint,
    intervention_families_equivalent,
    is_independent_binary_joint,
    joint_marginal,
    match_probability,
    private_fair_randomizers_joint,
    resolve_convex_family,
    resource_behavior_partition,
    resource_operationally_equivalent,
    resource_partition_is_representative_independent,
    run_correlation_authority_comparison,
    shared_fair_bit_joint,
    tensor_independent,
)
from tools.relay_theory_scheduler_nondeterminism import exact_distribution


def test_correlation_authority_comparison_passes() -> None:
    results = run_correlation_authority_comparison()

    assert [result.name for result in results] == [
        "SAME_MARGINALS_LOSE_CORRELATION",
        "COMMON_RANDOMNESS_RECONSTRUCTS_MERGED_JOINT_LAW_FAMILY",
        "COMMON_RANDOMNESS_IS_NOT_COMMUNICATION",
        "PRIVATE_VS_SHARED_RANDOMNESS_DIFFER",
        "PRIVATE_INFORMATION_REQUIRES_FLOW_FOR_REMOTE_CONDITIONING",
        "CONTROL_PARTITION_IS_GAUGE_WHEN_JOINT_INTERVENTION_FAMILY_MATCHES",
        "DYNAMIC_INTERVENTION_SET_SURVIVES_STATIC_PARTITION",
        "CORRELATED_COMPOSITION_DIFFERS_FROM_INDEPENDENT_TENSOR",
        "CORRELATION_RESOURCE_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
        "FIXED_RESOLUTION_RECOVERS_EXACT_STOCHASTIC_LAW",
    ]
    assert all(result.passed for result in results)


def test_binary_probability_rejects_float() -> None:
    with pytest.raises(TypeError, match="fractions.Fraction"):
        binary_distribution(0.5)  # type: ignore[arg-type]


def test_same_marginals_do_not_fix_joint_correlation() -> None:
    independent = private_fair_randomizers_joint()
    shared = shared_fair_bit_joint()

    assert joint_marginal(independent, 0) == joint_marginal(shared, 0)
    assert joint_marginal(independent, 1) == joint_marginal(shared, 1)
    assert is_independent_binary_joint(independent)
    assert not is_independent_binary_joint(shared)
    assert match_probability(independent) == Fraction(1, 2)
    assert match_probability(shared) == 1


def test_independent_product_is_not_silently_convexified() -> None:
    fair = binary_distribution(Fraction(1, 2))
    independent = independent_joint(fair, fair)
    correlated = shared_fair_bit_joint()

    assert is_independent_binary_joint(independent)
    assert not is_independent_binary_joint(correlated)
    assert independent != correlated


def test_common_source_can_reconstruct_full_joint_randomizer_family() -> None:
    merged = full_joint_family("merged")
    split_common = full_joint_family("split-common")

    assert intervention_families_equivalent(merged, split_common)
    assert family_contains(split_common, shared_fair_bit_joint())
    assert family_contains(
        split_common,
        exact_distribution(
            {
                "00": Fraction(1, 3),
                "01": Fraction(1, 6),
                "10": Fraction(1, 6),
                "11": Fraction(1, 3),
            }
        ),
    )


def test_common_randomness_does_not_transmit_private_information() -> None:
    assert (
        best_remote_guess_probability(can_read_hidden=False, shared_seed=True)
        == Fraction(1, 2)
    )
    assert best_remote_guess_probability(can_read_hidden=True, shared_seed=True) == 1
    assert best_remote_guess_probability(can_read_hidden=False, shared_seed=False) == Fraction(
        1, 2
    )


def test_control_partition_can_be_gauge_when_joint_intervention_family_matches() -> None:
    merged = ResourceDescription(
        "merged",
        canonical_control_partition((("x", "y"),)),
        full_joint_family("merged-family"),
        causal_stages=(("x", 0), ("y", 0)),
    )
    split = ResourceDescription(
        "split",
        canonical_control_partition((("x",), ("y",))),
        full_joint_family("split-common-family"),
        causal_stages=(("x", 0), ("y", 0)),
    )

    assert merged.control_partition != split.control_partition
    assert resource_operationally_equivalent(merged, split)


def test_read_edges_prevent_partition_gauge_when_information_flow_differs() -> None:
    family = full_joint_family("family")
    left = ResourceDescription(
        "left",
        canonical_control_partition((("x", "y"),)),
        family,
        read_edges=(("hidden", "x"),),
        causal_stages=(("x", 0), ("y", 0)),
    )
    right = ResourceDescription(
        "right",
        canonical_control_partition((("x",), ("y",))),
        family,
        read_edges=(("hidden", "x"), ("hidden", "y")),
        causal_stages=(("x", 0), ("y", 0)),
    )

    assert not resource_operationally_equivalent(left, right)


def test_dynamic_intervention_family_changes_context_conditioned_capability() -> None:
    dynamic = ConditionalFamily(
        "dynamic",
        (
            (
                "h0",
                InterventionFamily(
                    "h0", (deterministic_joint("0", "0"),), "discrete"
                ),
            ),
            (
                "h1",
                InterventionFamily(
                    "h1", (deterministic_joint("1", "1"),), "discrete"
                ),
            ),
        ),
    )
    static = ConditionalFamily(
        "static",
        (
            (
                "h0",
                InterventionFamily(
                    "h0", (deterministic_joint("0", "0"),), "discrete"
                ),
            ),
            (
                "h1",
                InterventionFamily(
                    "h1", (deterministic_joint("0", "0"),), "discrete"
                ),
            ),
        ),
    )
    contexts = {"h0": Fraction(1, 2), "h1": Fraction(1, 2)}
    targets = {"h0": "00", "h1": "11"}

    assert conditional_best_target_probability(dynamic, contexts, targets) == 1
    assert conditional_best_target_probability(static, contexts, targets) == Fraction(
        1, 2
    )


def test_shared_common_cause_changes_parallel_composition_not_marginals() -> None:
    fair = binary_distribution(Fraction(1, 2))
    independent = tensor_independent(fair, fair)
    correlated = common_cause_coupling(fair)

    assert joint_marginal(independent, 0) == joint_marginal(correlated, 0)
    assert joint_marginal(independent, 1) == joint_marginal(correlated, 1)
    assert independent != correlated
    assert match_probability(independent) == Fraction(1, 2)
    assert match_probability(correlated) == 1


def test_correlation_resource_quotient_is_representative_independent() -> None:
    merged = ResourceDescription(
        "merged",
        canonical_control_partition((("x", "y"),)),
        full_joint_family("merged-family"),
        causal_stages=(("x", 0), ("y", 0)),
    )
    split = ResourceDescription(
        "split",
        canonical_control_partition((("x",), ("y",))),
        full_joint_family("split-family"),
        causal_stages=(("x", 0), ("y", 0)),
    )
    different_information = ResourceDescription(
        "different-information",
        canonical_control_partition((("x",), ("y",))),
        full_joint_family("different-family"),
        read_edges=(("hidden", "y"),),
        causal_stages=(("x", 0), ("y", 0)),
    )
    descriptions = (merged, split, different_information)
    partition = resource_behavior_partition(descriptions)

    assert partition["merged"] == partition["split"]
    assert partition["merged"] != partition["different-information"]
    assert resource_partition_is_representative_independent(descriptions, partition)


def test_fixed_common_source_resolution_returns_one_exact_stochastic_law() -> None:
    family = full_joint_family("common")
    resolved = resolve_convex_family(
        family,
        {0: Fraction(1, 2), 3: Fraction(1, 2)},
    )

    assert resolved == shared_fair_bit_joint()
    assert joint_marginal(resolved, 0) == binary_distribution(Fraction(1, 2))
    assert joint_marginal(resolved, 1) == binary_distribution(Fraction(1, 2))


def test_discrete_and_convex_closure_are_not_interchangeable() -> None:
    vertices = (deterministic_joint("0", "0"), deterministic_joint("1", "1"))
    discrete = InterventionFamily("discrete", vertices, "discrete")
    convex = InterventionFamily("convex", vertices, "convex")

    assert not intervention_families_equivalent(discrete, convex)
    assert not family_contains(discrete, shared_fair_bit_joint())
    assert family_contains(convex, shared_fair_bit_joint())
