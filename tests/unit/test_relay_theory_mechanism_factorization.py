from fractions import Fraction

import pytest

from tools.relay_theory_mechanism_factorization import (
    ExposedCausalInterface,
    composed_xyz_interface,
    evaluate_exposed,
    exposed_hard_responses,
    exposed_interfaces_equivalent,
    exposed_soft_responses,
    factorization_partition,
    fused_fork_model,
    fused_xy_model,
    hidden_mediator_reveal_law,
    partition_is_representative_independent,
    resource_sensitive_signature,
    run_mechanism_factorization_comparison,
    single_target_hard_laws,
    split_fork_model,
    split_xy_model,
    validate_interface,
    xy_interface,
)


def test_mechanism_factorization_comparison_passes_with_strict_booleans() -> None:
    results = run_mechanism_factorization_comparison()

    assert [result.name for result in results] == [
        "PROJECTED_OBSERVATIONAL_LAW_IGNORES_HIDDEN_COPY_FACTORIZATION",
        "EXPOSED_HARD_SUBSTITUTIONS_IGNORE_HIDDEN_COPY_FACTORIZATION",
        "EXPOSED_SOFT_SUBSTITUTIONS_IGNORE_HIDDEN_COPY_FACTORIZATION",
        "HIDDEN_FACTORIZATION_IS_GAUGE_WITHIN_TESTED_EXPOSED_INTERFACE",
        "HIDDEN_MEDIATOR_NAME_IS_GAUGE",
        "EXPOSED_EQUIVALENCE_SURVIVES_COMMON_DOWNSTREAM_COMPOSITION",
        "INTERVENTION_DOMAIN_IS_PART_OF_THE_INTERFACE",
        "EXPOSING_HIDDEN_MEDIATOR_ADDS_OPERATIONAL_POWER",
        "RESOURCE_PROBE_REVEALS_HIDDEN_REALIZATION",
        "EXPOSED_FACTORIZATION_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
    ]
    assert all(type(result.passed) is bool for result in results)
    assert all(result.passed for result in results)


def test_fused_and_hidden_mediator_models_share_exposed_observational_law() -> None:
    fused = xy_interface(fused_xy_model(), name="fused")
    split = xy_interface(split_xy_model(), name="split")

    assert evaluate_exposed(fused) == evaluate_exposed(split)


def test_fused_and_hidden_mediator_models_share_all_declared_hard_responses() -> None:
    fused = xy_interface(fused_xy_model(), name="fused")
    split = xy_interface(split_xy_model(), name="split")

    assert exposed_hard_responses(fused) == exposed_hard_responses(split)


def test_fused_and_hidden_mediator_models_share_exact_soft_responses() -> None:
    fused = xy_interface(fused_xy_model(), name="fused")
    split = xy_interface(split_xy_model(), name="split")

    assert exposed_soft_responses(fused) == exposed_soft_responses(split)


def test_hidden_mediator_variable_name_is_gauge_under_exposed_interface() -> None:
    h_interface = xy_interface(split_xy_model(mediator="H"), name="with-h")
    m_interface = xy_interface(
        split_xy_model(name="split-m", mediator="M"),
        name="with-m",
    )

    assert exposed_interfaces_equivalent(h_interface, m_interface)


def test_exposed_equivalence_is_preserved_by_same_downstream_composition() -> None:
    fused = composed_xyz_interface(fused_xy_model(), name="fused-z")
    split = composed_xyz_interface(split_xy_model(), name="split-z")

    assert exposed_interfaces_equivalent(fused, split)


def test_intervention_domain_is_part_of_exact_interface_identity() -> None:
    model = fused_xy_model()
    full = ExposedCausalInterface("full", model, ("X", "Y"), ("X", "Y"))
    narrow = ExposedCausalInterface("narrow", model, ("X", "Y"), ("X",))

    assert evaluate_exposed(full) == evaluate_exposed(narrow)
    assert not exposed_interfaces_equivalent(full, narrow)


def test_exposing_hidden_fork_mediator_adds_single_operation_power() -> None:
    fused = ExposedCausalInterface(
        "fused-fork",
        fused_fork_model(),
        ("X", "Y", "Z"),
        ("X", "Y", "Z"),
    )
    split = split_fork_model()

    hidden_do = hidden_mediator_reveal_law(split, "H", "0")

    assert hidden_do not in single_target_hard_laws(fused)


def test_resource_probe_can_reveal_black_box_equivalent_realizations() -> None:
    fused = xy_interface(fused_xy_model(), name="fused")
    split = xy_interface(split_xy_model(), name="split")

    assert exposed_interfaces_equivalent(fused, split)
    assert resource_sensitive_signature(fused) != resource_sensitive_signature(split)


def test_factorization_quotient_is_representative_independent() -> None:
    fused = xy_interface(fused_xy_model(), name="fused")
    split_h = xy_interface(split_xy_model(), name="split-h")
    split_m = xy_interface(
        split_xy_model(name="split-m-model", mediator="M"),
        name="split-m",
    )
    narrow = ExposedCausalInterface(
        "narrow",
        fused.model,
        ("X", "Y"),
        ("X",),
    )
    interfaces = (fused, split_h, split_m, narrow)
    partition = factorization_partition(interfaces)

    assert partition["fused"] == partition["split-h"] == partition["split-m"]
    assert partition["fused"] != partition["narrow"]
    assert partition_is_representative_independent(interfaces, partition)


def test_interface_validation_rejects_hidden_replaceable_target_mismatch() -> None:
    interface = ExposedCausalInterface(
        "invalid",
        fused_xy_model(),
        ("X", "Y"),
        ("X", "H"),
    )

    with pytest.raises(ValueError, match="replaceable variables"):
        validate_interface(interface)


def test_interface_soft_probabilities_require_exact_fraction() -> None:
    interface = ExposedCausalInterface(
        "float-soft",
        fused_xy_model(),
        ("X", "Y"),
        ("X", "Y"),
        (Fraction(1, 4), 0.75),  # type: ignore[arg-type]
    )

    with pytest.raises(TypeError, match="fractions.Fraction"):
        validate_interface(interface)
