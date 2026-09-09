from fractions import Fraction

import pytest

from tools.relay_theory_markov_reconstruction import (
    UNIT_VALUE,
    ExactKernel,
    category_laws_hold,
    copy_comonoid_laws_hold,
    deterministic_composition_law_holds,
    deterministic_maps_preserve_copy,
    discard_naturality_holds,
    exact_kernel,
    independent_fair_pair,
    local_global_gluing_boundary_survives,
    outer_relay_boundaries_survive,
    quotient_representative_independence_survives,
    reconstruction_verdict,
    resolved_choice_boundary_survives,
    run_markov_reconstruction,
    shared_fair_pair,
    shared_randomness_uses_copy_not_plain_tensor,
    stochastic_copy_naturality_fails,
    tensor_laws_hold,
    causal_intervention_boundary_survives,
    counterfactual_boundary_survives,
)


def test_exact_kernel_contract_rejects_nonexact_invalid_or_duplicate_data() -> None:
    with pytest.raises(TypeError, match="fractions.Fraction"):
        ExactKernel(("x",), ("y",), ((1.0,),))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="non-negative"):
        ExactKernel(("x",), ("y0", "y1"), ((Fraction(-1), Fraction(2)),))

    with pytest.raises(ValueError, match="sum exactly to 1"):
        ExactKernel(("x",), ("y0", "y1"), ((Fraction(1, 3), Fraction(1, 3)),))

    with pytest.raises(ValueError, match="source values must be unique"):
        ExactKernel(("x", "x"), ("y",), ((Fraction(1),), (Fraction(1),)))

    with pytest.raises(ValueError, match="target values must be unique"):
        ExactKernel(("x",), ("y", "y"), ((Fraction(1, 2), Fraction(1, 2)),))

    with pytest.raises(TypeError, match="fractions.Fraction"):
        exact_kernel(("x",), ("y",), {"x": {"y": 1}})  # type: ignore[dict-item]


def test_identity_and_associativity_reconstruct_exact_category_laws() -> None:
    assert category_laws_hold()


def test_deterministic_functions_embed_as_dirac_kernels() -> None:
    assert deterministic_composition_law_holds()
    assert deterministic_maps_preserve_copy()


def test_discard_and_copy_reconstruct_bounded_commutative_comonoid() -> None:
    assert discard_naturality_holds()
    assert copy_comonoid_laws_hold(("red", "blue", "green"))


def test_genuinely_stochastic_map_does_not_preserve_copy() -> None:
    shared = shared_fair_pair()
    independent = independent_fair_pair()

    assert stochastic_copy_naturality_fails()
    assert shared.row(UNIT_VALUE) == (
        (("0", "0"), Fraction(1, 2)),
        (("1", "1"), Fraction(1, 2)),
    )
    assert independent.row(UNIT_VALUE) == (
        (("0", "0"), Fraction(1, 4)),
        (("0", "1"), Fraction(1, 4)),
        (("1", "0"), Fraction(1, 4)),
        (("1", "1"), Fraction(1, 4)),
    )
    assert shared != independent


def test_independent_tensor_is_normalized_functorial_and_explicitly_symmetric() -> None:
    assert tensor_laws_hold()


def test_shared_randomness_is_expressed_by_copy_wiring_not_plain_tensor() -> None:
    assert shared_randomness_uses_copy_not_plain_tensor()


def test_fixed_scheduler_resolution_recovers_one_arrow_but_family_retains_capability() -> None:
    assert resolved_choice_boundary_survives()


def test_fixed_causal_realization_recovers_arrow_but_observational_arrow_loses_substitution() -> None:
    assert causal_intervention_boundary_survives()


def test_single_world_arrow_family_does_not_recover_same_unit_counterfactual_coupling() -> None:
    assert counterfactual_boundary_survives()


def test_local_stochastic_laws_do_not_manufacture_a_global_joint() -> None:
    assert local_global_gluing_boundary_survives()


def test_exact_behavioral_quotient_survives_representative_change_under_reconstructed_ops() -> None:
    assert quotient_representative_independence_survives()


def test_outer_relay_boundaries_survive_the_markov_reconstruction() -> None:
    assert outer_relay_boundaries_survive()


def test_reconstruction_summary_is_strict_and_complete() -> None:
    results = run_markov_reconstruction()

    assert [result.name for result in results] == [
        "CATEGORY_IDENTITY_AND_ASSOCIATIVITY_SURVIVE",
        "DETERMINISTIC_DIRAC_SUBCATEGORY_SURVIVES",
        "COPY_DISCARD_COMONOID_STRUCTURE_SURVIVES",
        "INDEPENDENT_TENSOR_AND_INTERCHANGE_SURVIVE",
        "STOCHASTIC_COPY_NONNATURALITY_SURVIVES",
        "SHARED_RANDOMNESS_IS_WIRING_NOT_PLAIN_TENSOR",
        "RESOLVED_CHOICE_RECOVERS_ONE_ARROW_UNRESOLVED_CHOICE_DOES_NOT",
        "INTERVENTION_ALGEBRA_REMAINS_OUTSIDE_OBSERVATIONAL_ARROW",
        "COUNTERFACTUAL_COUPLING_REMAINS_OUTSIDE_SINGLE_WORLD_ARROWS",
        "LOCAL_STOCHASTIC_PIECES_DO_NOT_GLUE_BY_FIAT",
        "EXACT_BEHAVIORAL_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
        "FINSTOCH_MARKOV_SINGLE_WORLD_SLICE_IS_RECONSTRUCTED",
        "MARKOV_CATEGORY_IS_DERIVED_SLICE_ONLY",
    ]
    assert all(type(result.passed) is bool for result in results)
    assert all(result.passed for result in results)


def test_final_verdict_is_derived_slice_not_whole_relay() -> None:
    assert reconstruction_verdict() == "MARKOV_CATEGORY_IS_DERIVED_SLICE_ONLY"
