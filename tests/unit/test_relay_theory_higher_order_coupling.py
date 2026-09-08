from fractions import Fraction

import pytest

from tools.relay_theory_higher_order_coupling import (
    MultiWorldModel,
    all_pairs_are_independent_fair,
    behavior_equivalent,
    behavior_partition,
    downstream_copy_model,
    even_parity_model,
    fair_single_law,
    marginal,
    odd_parity_model,
    pairwise_signature,
    parity_probability,
    partition_is_representative_independent,
    rename_worlds,
    run_higher_order_coupling_comparison,
    singleton_signature,
    uniform_pair_law,
    validate_multi_world_model,
    world_renaming_equivalent,
)


def test_higher_order_comparison_passes_with_strict_booleans() -> None:
    results = run_higher_order_coupling_comparison()

    assert [result.name for result in results] == [
        "ALL_SINGLETON_MARGINALS_MATCH",
        "ALL_PAIRWISE_JOINTS_MATCH",
        "EVERY_PAIR_IS_INDEPENDENT_FAIR",
        "TRIPLE_PARITY_DISTINGUISHES_FULL_JOINT",
        "EQUIVALENCE_IS_ARITY_RELATIVE",
        "WORLD_LABEL_RENAMING_IS_GAUGE_UNDER_EXPLICIT_TRANSPORT",
        "LOWER_ARITY_SIGNATURES_ARE_DERIVED_FROM_FULL_JOINT",
        "DOWNSTREAM_COPY_PRESERVES_ARITY_RELATIVE_DISTINCTION",
        "PAIRWISE_AND_TRIPLE_QUOTIENTS_ARE_REPRESENTATIVE_INDEPENDENT",
    ]
    assert all(type(result.passed) is bool for result in results)
    assert all(result.passed for result in results)


def test_declared_joint_requires_exact_unique_normalized_binary_support() -> None:
    quarter = Fraction(1, 4)

    with pytest.raises(TypeError, match="fractions.Fraction"):
        validate_multi_world_model(
            MultiWorldModel(
                "float",
                ("Y0", "Y1", "Y2"),
                ((("0", "0", "0"), 1.0),),  # type: ignore[arg-type]
            )
        )

    with pytest.raises(ValueError, match="joint outcomes must be unique"):
        validate_multi_world_model(
            MultiWorldModel(
                "duplicate",
                ("Y0", "Y1", "Y2"),
                (
                    (("0", "0", "0"), Fraction(1, 2)),
                    (("0", "0", "0"), Fraction(1, 2)),
                ),
            )
        )

    with pytest.raises(ValueError, match="sum exactly to 1"):
        validate_multi_world_model(
            MultiWorldModel(
                "bad-total",
                ("Y0", "Y1", "Y2"),
                (
                    (("0", "0", "0"), quarter),
                    (("1", "1", "1"), quarter),
                ),
            )
        )

    with pytest.raises(ValueError, match="bounded outcomes must be binary"):
        validate_multi_world_model(
            MultiWorldModel(
                "non-binary",
                ("Y0", "Y1", "Y2"),
                ((("0", "0", "2"), Fraction(1)),),
            )
        )

    with pytest.raises(ValueError, match="world labels must be unique"):
        validate_multi_world_model(
            MultiWorldModel(
                "duplicate-world",
                ("Y0", "Y0", "Y2"),
                ((("0", "0", "0"), Fraction(1)),),
            )
        )


def test_all_singleton_marginals_are_exactly_fair_and_equal() -> None:
    even = even_parity_model()
    odd = odd_parity_model()

    assert singleton_signature(even) == singleton_signature(odd)
    assert all(law == fair_single_law() for _, law in singleton_signature(even))


def test_all_pairwise_joints_are_exactly_uniform_and_equal() -> None:
    even = even_parity_model()
    odd = odd_parity_model()

    assert pairwise_signature(even) == pairwise_signature(odd)
    assert all(law == uniform_pair_law() for _, law in pairwise_signature(even))
    assert all_pairs_are_independent_fair(even)
    assert all_pairs_are_independent_fair(odd)


def test_triple_parity_separates_models_after_all_pairwise_probes_match() -> None:
    even = even_parity_model()
    odd = odd_parity_model()

    assert behavior_equivalent(even, odd, "pairwise")
    assert parity_probability(even, 0) == Fraction(1)
    assert parity_probability(odd, 0) == Fraction(0)
    assert parity_probability(even, 1) == Fraction(0)
    assert parity_probability(odd, 1) == Fraction(1)
    assert not behavior_equivalent(even, odd, "triple")


def test_lower_arity_signatures_are_derived_from_the_same_full_joint() -> None:
    even = even_parity_model()
    odd = odd_parity_model()

    for world in even.worlds:
        assert marginal(even, (world,)) == marginal(odd, (world,))

    for pair in (("Y0", "Y1"), ("Y0", "Y2"), ("Y1", "Y2")):
        assert marginal(even, pair) == marginal(odd, pair)

    assert even.joint != odd.joint


def test_world_label_renaming_is_gauge_only_under_explicit_transport() -> None:
    even = even_parity_model()
    mapping = {"Y0": "A", "Y1": "B", "Y2": "C"}
    renamed = rename_worlds(even, mapping, name="renamed")

    assert world_renaming_equivalent(even, renamed, mapping)
    assert not world_renaming_equivalent(
        even,
        renamed,
        {"Y0": "B", "Y1": "A", "Y2": "C"},
    )


def test_downstream_copy_preserves_pairwise_merge_and_triple_split() -> None:
    even_z = downstream_copy_model(even_parity_model(), name="even-z")
    odd_z = downstream_copy_model(odd_parity_model(), name="odd-z")

    assert behavior_equivalent(even_z, odd_z, "pairwise")
    assert not behavior_equivalent(even_z, odd_z, "triple")
    assert parity_probability(even_z, 0) == Fraction(1)
    assert parity_probability(odd_z, 0) == Fraction(0)


def test_pairwise_and_triple_partitions_are_representative_independent() -> None:
    even = even_parity_model()
    even_clone = MultiWorldModel("even-clone", even.worlds, even.joint)
    odd = odd_parity_model()
    models = (even, even_clone, odd)

    pairwise = behavior_partition(models, "pairwise")
    triple = behavior_partition(models, "triple")

    assert pairwise["even"] == pairwise["even-clone"] == pairwise["odd"]
    assert triple["even"] == triple["even-clone"]
    assert triple["even"] != triple["odd"]
    assert partition_is_representative_independent(models, pairwise, "pairwise")
    assert partition_is_representative_independent(models, triple, "triple")


def test_invalid_frame_marginal_and_rename_requests_fail_closed() -> None:
    even = even_parity_model()

    with pytest.raises(ValueError, match="unknown frame"):
        behavior_equivalent(even, odd_parity_model(), "quadruple")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="must be non-empty"):
        marginal(even, ())

    with pytest.raises(ValueError, match="must be unique"):
        marginal(even, ("Y0", "Y0"))

    with pytest.raises(ValueError, match="unknown marginal worlds"):
        marginal(even, ("Y3",))

    with pytest.raises(ValueError, match="cover every world exactly once"):
        rename_worlds(even, {"Y0": "A"}, name="partial")
