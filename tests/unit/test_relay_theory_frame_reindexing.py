from __future__ import annotations

import pytest

from tools.relay_theory_frame_reindexing import (
    FrameResult,
    OperationalFrame,
    ProbeSystem,
    anti_smuggling_fail_closed,
    authority_change_is_not_probe_forgetting,
    behavioral_partition,
    counterfactual_requires_alignment_layer,
    frame_change_verdicts,
    frame_reindexing_core_survives,
    gluing_requires_realizability_certificate,
    heterogeneous_outer_changes_survive,
    intervention_requires_transformation_layer,
    noncomparable_probe_frames_survive,
    probe_forgetting_is_functorial,
    probe_refinement_fixture,
    probe_refinement_is_monotone,
    pure_forgetting,
    pure_forgetting_preserves_markov_slice,
    quotient_forgetting_map,
    run_frame_reindexing,
    scheduler_class_is_not_probe_forgetting,
    scheduler_information_changes_policy_space,
)


def test_frame_contract_rejects_invalid_declarations() -> None:
    with pytest.raises(ValueError, match="frame name"):
        OperationalFrame("")
    with pytest.raises(ValueError, match="probes entries must be unique"):
        OperationalFrame("bad", probes=("p", "p"))
    with pytest.raises(ValueError, match="alignment arity"):
        OperationalFrame("bad", alignment_arity=0)


def test_probe_system_contract_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="states must"):
        ProbeSystem(states=("s", "s"), values={"s": {"p": "x"}})
    with pytest.raises(ValueError, match="cover every"):
        ProbeSystem(states=("s0", "s1"), values={"s0": {"p": "x"}})


def test_richer_probe_frame_refines_exact_behavioral_quotient() -> None:
    system, coarse, rich, _ = probe_refinement_fixture()
    coarse_partition = behavioral_partition(system, coarse)
    rich_partition = behavioral_partition(system, rich)
    assert probe_refinement_is_monotone()
    assert len(set(coarse_partition.values())) == 2
    assert len(set(rich_partition.values())) == 3
    assert pure_forgetting(coarse, rich)


def test_quotient_forgetting_is_representative_independent() -> None:
    system, coarse, rich, _ = probe_refinement_fixture()
    mapping = quotient_forgetting_map(system, rich, coarse)
    rich_partition = behavioral_partition(system, rich)
    coarse_partition = behavioral_partition(system, coarse)
    for state in system.states:
        assert mapping[rich_partition[state]] == coarse_partition[state]


def test_chained_probe_forgetting_is_functorial_in_bounded_fixture() -> None:
    assert probe_forgetting_is_functorial()


def test_frames_need_not_form_a_total_richness_order() -> None:
    assert noncomparable_probe_frames_survive()


def test_scheduler_information_is_not_ordinary_probe_forgetting() -> None:
    assert scheduler_information_changes_policy_space()


def test_scheduler_class_change_alters_behavioral_equivalence() -> None:
    assert scheduler_class_is_not_probe_forgetting()


def test_write_authority_changes_attainable_interventions() -> None:
    assert authority_change_is_not_probe_forgetting()


def test_intervention_is_mechanism_transformation_not_plain_reindexing() -> None:
    assert intervention_requires_transformation_layer()


def test_counterfactual_extension_needs_alignment_data() -> None:
    assert counterfactual_requires_alignment_layer()


def test_local_stochastic_families_need_realizability_certificate() -> None:
    assert gluing_requires_realizability_certificate()


def test_genuine_forgetting_preserves_bounded_markov_operations() -> None:
    assert pure_forgetting_preserves_markov_slice()


def test_capability_changes_fail_closed_as_pure_reindexing() -> None:
    assert anti_smuggling_fail_closed()


def test_reconstruction_decomposes_frame_change_instead_of_unifying_by_fiat() -> None:
    assert frame_reindexing_core_survives()
    assert heterogeneous_outer_changes_survive()
    assert frame_change_verdicts() == (
        "FRAME_REFINEMENT_IS_FUNCTORIAL",
        "FRAME_INDEXED_MARKOV_SLICES_SURVIVE",
        "INTERVENTION_REQUIRES_TRANSFORMATION_LAYER",
        "COUNTERFACTUAL_EXTENSION_REQUIRES_ALIGNMENT_LAYER",
        "GLUING_REQUIRES_REALIZABILITY_CERTIFICATE",
    )


def test_result_contract_is_strict_bool() -> None:
    results = run_frame_reindexing()
    assert results
    assert all(type(result.passed) is bool for result in results)
    assert all(result.passed for result in results)
    assert results[-1].detail == ",".join(frame_change_verdicts())
    with pytest.raises(TypeError, match="strict bool"):
        FrameResult("bad", 1)  # type: ignore[arg-type]
