from __future__ import annotations

from fractions import Fraction

import pytest

from tools.relay_theory_axiom_extraction import (
    AccessSpec,
    AlignmentInput,
    ExtractionResult,
    FiniteExperiment,
    LocalConstraint,
    TransformCommand,
    access_forgetting,
    access_specification_replaces_named_frame,
    alignment_is_explicit_transform_input,
    authority_reduces_to_transform_admissibility,
    axiom_extraction_verdicts,
    canonical_exact_law,
    construct_from_constraints,
    derived_behavioral_partition,
    derived_structures_0_1,
    exact_equality_boundary_survives,
    factorization_is_access_relative,
    gluing_is_partial_construction_with_certificate,
    historical_reconstruction_audit,
    information_reduces_to_access_specification,
    markov_structure_is_derived,
    minimal_interface_basis_0_1,
    necessity_matrix,
    quotient_is_derived_from_access_and_behavior,
    run_axiom_extraction,
    transformation_interface_unifies_choice_and_intervention,
)


def test_exact_law_contract_is_fail_closed() -> None:
    law = canonical_exact_law(
        {"L": Fraction(1, 2), "R": Fraction(1, 2)}
    )
    assert sum((mass for _, mass in law), Fraction(0)) == 1

    with pytest.raises(TypeError, match="Fraction"):
        canonical_exact_law({"L": 0.5, "R": 0.5})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="sum exactly"):
        canonical_exact_law({"L": Fraction(1, 3), "R": Fraction(1, 3)})


def test_public_transform_contract_has_no_opaque_payload() -> None:
    command = TransformCommand("choose", reads=("history",), writes=("choice",))
    assert command.reads == ("history",)
    assert command.writes == ("choice",)
    assert set(command.__dataclass_fields__) == {"name", "reads", "writes"}

    with pytest.raises(ValueError, match="command name"):
        TransformCommand("")
    with pytest.raises(ValueError, match="unique"):
        TransformCommand("bad", reads=("h", "h"))


def test_access_contract_is_declarative_and_name_is_gauge() -> None:
    left = AccessSpec(
        "left-frame",
        observations=("audit",),
        admissible_commands=("choose",),
        visible_information=("history",),
    )
    right = AccessSpec(
        "right-frame",
        observations=("audit",),
        admissible_commands=("choose",),
        visible_information=("history",),
    )
    assert access_specification_replaces_named_frame()
    assert left != right

    with pytest.raises(ValueError, match="access name"):
        AccessSpec("")
    with pytest.raises(ValueError, match="unique"):
        AccessSpec("bad", observations=("p", "p"))


def test_scheduler_and_intervention_share_one_public_transform_interface() -> None:
    assert transformation_interface_unifies_choice_and_intervention()


def test_authority_and_scheduler_information_reduce_to_access_contracts() -> None:
    assert authority_reduces_to_transform_admissibility()
    assert information_reduces_to_access_specification()


def test_hidden_factorization_is_gauge_until_access_exposes_resource_probe() -> None:
    assert factorization_is_access_relative()


def test_alignment_is_explicit_input_not_reconstructed_from_context_laws() -> None:
    assert alignment_is_explicit_transform_input()


def test_constraint_constructor_checks_alignment_exactly() -> None:
    half = Fraction(1, 2)
    constraints = (
        LocalConstraint(
            ("A",),
            canonical_exact_law({("0",): half, ("1",): half}),
        ),
        LocalConstraint(
            ("B",),
            canonical_exact_law({("0",): half, ("1",): half}),
        ),
    )
    correlated = AlignmentInput(
        ("A", "B"),
        canonical_exact_law(
            {("0", "0"): half, ("1", "1"): half}
        ),
    )
    assert construct_from_constraints(constraints, correlated) == correlated.joint

    invalid = AlignmentInput(
        ("A", "B"),
        canonical_exact_law(
            {("0", "0"): Fraction(1)}
        ),
    )
    with pytest.raises(ValueError, match="local constraint"):
        construct_from_constraints(constraints, invalid)


def test_gluing_is_partial_construction_with_realizability_certificate() -> None:
    assert gluing_is_partial_construction_with_certificate()


def test_behavioral_quotient_and_pure_forgetting_are_derived() -> None:
    assert quotient_is_derived_from_access_and_behavior()

    coarse = AccessSpec("coarse", observations=("p",))
    middle = AccessSpec("middle", observations=("p", "q"))
    rich = AccessSpec("rich", observations=("p", "q", "r"))
    assert access_forgetting(coarse, middle)
    assert access_forgetting(middle, rich)
    assert access_forgetting(coarse, rich)
    assert not access_forgetting(rich, coarse)


def test_partition_is_computed_from_public_signature_not_stored_state() -> None:
    half = canonical_exact_law(
        {"L": Fraction(1, 2), "R": Fraction(1, 2)}
    )
    first = FiniteExperiment("first", half)
    clone = FiniteExperiment("clone", half)
    changed = FiniteExperiment(
        "changed",
        canonical_exact_law(
            {"L": Fraction(3, 4), "R": Fraction(1, 4)}
        ),
    )
    partition = derived_behavioral_partition(
        (first, clone, changed),
        AccessSpec("observable"),
    )
    assert partition["first"] == partition["clone"]
    assert partition["first"] != partition["changed"]


def test_markov_slice_and_exact_identity_boundary_remain_derived() -> None:
    assert markov_structure_is_derived()
    assert exact_equality_boundary_survives()


def test_first_cycle_reconstructs_without_issue_specific_semantic_dispatch() -> None:
    audit = historical_reconstruction_audit()
    assert audit
    assert all(audit.values())

    matrix = necessity_matrix()
    assert matrix
    assert all(matrix.values())


def test_candidate_basis_is_smaller_than_first_cycle_vocabulary() -> None:
    assert minimal_interface_basis_0_1() == (
        "ACCESS_SPECIFICATION",
        "EXACT_RESOLVED_BEHAVIOR",
        "EXPERIMENT_TRANSFORMATION",
        "EXPLICIT_ALIGNMENT_INPUT",
        "REALIZABILITY_DOMAIN_CERTIFICATE",
        "EXACT_EQUALITY_BOUNDARY",
    )
    assert derived_structures_0_1() == (
        "BEHAVIORAL_QUOTIENT",
        "PURE_FORGETTING_REINDEXING",
        "FINSTOCH_MARKOV_SLICE",
    )


def test_bounded_axiom_extraction_earns_expected_verdicts() -> None:
    assert axiom_extraction_verdicts() == (
        "TRANSFORMATION_INTERFACE_UNIFIES_CHOICE_AND_INTERVENTION",
        "AUTHORITY_REDUCES_TO_TRANSFORM_ADMISSIBILITY",
        "INFORMATION_REDUCES_TO_ACCESS_SPECIFICATION",
        "ALIGNMENT_IS_EXPLICIT_TRANSFORM_INPUT",
        "GLUING_IS_PARTIAL_CONSTRUCTION_WITH_CERTIFICATE",
        "FRAME_REDUCES_TO_ACCESS_SPECIFICATION",
        "QUOTIENT_IS_DERIVED",
        "MARKOV_STRUCTURE_IS_DERIVED",
        "EXACT_EQUALITY_BOUNDARY_SURVIVES",
        "MINIMAL_INTERFACE_BASIS_0_1",
    )


def test_result_contract_is_strict_bool() -> None:
    results = run_axiom_extraction()
    assert results
    assert all(type(result.passed) is bool for result in results)
    assert all(result.passed for result in results)
    assert results[-1].name == "MINIMAL_INTERFACE_BASIS_0_1"

    with pytest.raises(TypeError, match="strict bool"):
        ExtractionResult("bad", 1)  # type: ignore[arg-type]
