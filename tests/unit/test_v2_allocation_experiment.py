from __future__ import annotations

import pytest

from relaylm.v2_allocation_experiment import (
    REGIMES,
    adaptive_preprobe_policy,
    allocation_envelope,
    allocation_intervention_spec,
    allocation_operations,
    fixed_policy,
    generate_allocation_case,
    heuristic_policy,
    oracle_policy,
    prepare_r0_allocation_arms,
    prepare_r0_oracle_arm,
    run_paid_meta_probe,
)
from relaylm.v2_interventions import (
    InterventionError,
    MeasurementTrace,
    ProjectionPolicy,
    ResourceLedger,
    ResourceLimitError,
    ResourceVector,
    assert_clean_intervention,
    project_scope,
    run_operation_plan,
    snapshot_arm,
)
from relaylm.v2_semantics import ObservationInput, SemanticTransactionStore, TransactionRequest


def test_r0_public_task_is_regime_free_and_byte_identical_for_same_seed() -> None:
    cases = [generate_allocation_case(seed=17, regime=regime) for regime in REGIMES]
    packets = {case.task.model_packet() for case in cases}
    assert len(packets) == 1
    assert all(not hasattr(case.task, "regime") for case in cases)
    for regime, case in zip(REGIMES, cases, strict=True):
        assert regime.encode("utf-8") not in case.task.model_packet()

    replay = generate_allocation_case(seed=17, regime="saturated")
    assert replay.task == cases[0].task
    assert (
        generate_allocation_case(seed=18, regime="saturated").task.model_packet()
        != cases[0].task.model_packet()
    )


def test_r0_fixed_and_heuristic_are_regime_blind() -> None:
    cases = [generate_allocation_case(seed=41, regime=regime) for regime in REGIMES]
    assert {fixed_policy().plan for _case in cases} == {("think",)}
    assert len({heuristic_policy(case.task).plan for case in cases}) == 1


def test_r0_adaptive_preprobe_policy_cannot_select_hidden_ideal_operation() -> None:
    policies = {
        adaptive_preprobe_policy()
        for _case in (generate_allocation_case(seed=51, regime=regime) for regime in REGIMES)
    }
    assert len(policies) == 1
    policy = policies.pop()
    assert policy.plan == ("meta_probe",)
    assert policy.decision_cost == ResourceVector(latency_units=1)


def test_r0_unpaid_probe_cannot_return_hidden_result() -> None:
    case = generate_allocation_case(seed=31, regime="observation_beneficial")
    ledger = ResourceLedger(ResourceVector())
    trace = MeasurementTrace()
    with pytest.raises(ResourceLimitError):
        run_paid_meta_probe(
            case,
            store=SemanticTransactionStore(),
            operations=allocation_operations(),
            ledger=ledger,
            trace=trace,
        )
    assert ledger.total == ResourceVector()
    assert trace.snapshot() == ()


def test_r0_paid_meta_probe_reveals_evaluator_result_only_after_charge() -> None:
    case = generate_allocation_case(seed=31, regime="observation_beneficial")
    ledger = ResourceLedger(allocation_envelope())
    trace = MeasurementTrace()
    receipt = run_paid_meta_probe(
        case,
        store=SemanticTransactionStore(),
        operations=allocation_operations(),
        ledger=ledger,
        trace=trace,
    )
    assert receipt.case_id == case.case_id
    assert receipt.run.selected_operations == ("meta_probe",)
    assert receipt.run.resource_total.observation_units == 1
    assert receipt.run.resource_total.latency_units == 2
    assert receipt.run.measurement_events == (
        "policy:adaptive:decision",
        "policy:adaptive:operation:meta_probe",
    )
    assert receipt.selected_operation == "observe"


def test_r0_paid_probe_receipt_is_bound_to_one_case() -> None:
    paid_case = generate_allocation_case(seed=61, regime="retrieval_beneficial")
    other_case = generate_allocation_case(seed=61, regime="depth_beneficial")
    receipt = run_paid_meta_probe(
        paid_case,
        store=SemanticTransactionStore(),
        operations=allocation_operations(),
        ledger=ResourceLedger(allocation_envelope()),
        trace=MeasurementTrace(),
    )
    assert paid_case.task == other_case.task
    assert receipt.case_id == paid_case.case_id
    assert receipt.case_id != other_case.case_id
    assert receipt.selected_operation == "retrieve"


def test_r0_fixed_heuristic_adaptive_share_task_operations_budget_and_cognition() -> None:
    case = generate_allocation_case(seed=23, regime="retrieval_beneficial")
    arms = prepare_r0_allocation_arms(case)

    assert arms.fixed.task_digest == arms.heuristic.task_digest == arms.adaptive.task_digest
    assert (
        arms.fixed.operation_surface_digest
        == arms.heuristic.operation_surface_digest
        == arms.adaptive.operation_surface_digest
    )
    assert arms.fixed.envelope == arms.heuristic.envelope == arms.adaptive.envelope
    assert (
        arms.fixed.snapshot.canonical_digest
        == arms.heuristic.snapshot.canonical_digest
        == arms.adaptive.snapshot.canonical_digest
    )
    assert (
        arms.fixed.snapshot.provenance_ids
        == arms.heuristic.snapshot.provenance_ids
        == arms.adaptive.snapshot.provenance_ids
        == ()
    )

    spec = allocation_intervention_spec()
    assert assert_clean_intervention(
        arms.fixed.snapshot,
        arms.heuristic.snapshot,
        spec=spec,
    ).clean
    assert assert_clean_intervention(
        arms.fixed.snapshot,
        arms.adaptive.snapshot,
        spec=spec,
    ).clean


def test_r0_adaptive_pays_probe_before_selected_work() -> None:
    case = generate_allocation_case(seed=31, regime="observation_beneficial")
    arms = prepare_r0_allocation_arms(case)
    assert arms.adaptive.run.selected_operations == ("meta_probe", "observe")
    assert arms.adaptive.run.resource_total.observation_units == 2
    assert arms.adaptive.run.resource_total.latency_units == 5
    assert arms.adaptive.run.measurement_events[:2] == (
        "policy:adaptive:decision",
        "policy:adaptive:operation:meta_probe",
    )
    assert arms.adaptive.run.measurement_events[2] == "policy:adaptive:operation:observe"


def test_r0_oracle_is_privileged_and_not_a_deployable_policy() -> None:
    case = generate_allocation_case(seed=7, regime="depth_beneficial")
    policy = oracle_policy(case)
    assert policy.privileged
    assert policy.plan == ("think",)

    with pytest.raises(InterventionError, match="privileged policy"):
        run_operation_plan(
            SemanticTransactionStore(),
            operations=allocation_operations(),
            policy=policy,
            ledger=ResourceLedger(allocation_envelope()),
            trace=MeasurementTrace(),
        )

    oracle = prepare_r0_oracle_arm(case)
    assert oracle.arm_id == "A3"
    assert oracle.run.policy_id == "oracle"
    assert oracle.run.selected_operations == ("think",)


def test_r0_policy_instrumentation_does_not_mutate_canonical_cognition() -> None:
    store = SemanticTransactionStore()
    before = store.canonical_snapshot()
    run_operation_plan(
        store,
        operations=allocation_operations(),
        policy=adaptive_preprobe_policy(),
        ledger=ResourceLedger(allocation_envelope()),
        trace=MeasurementTrace(),
    )
    assert store.canonical_snapshot() == before
    assert tuple(store.provenance) == ()


def test_r0_hidden_evidence_contamination_is_visible_to_arm_diff() -> None:
    store = SemanticTransactionStore()
    empty_policy = ProjectionPolicy()
    clean_projection = project_scope(store, empty_policy)
    clean = snapshot_arm(
        store,
        projection_policy=empty_policy,
        projection_result=clean_projection,
        policy_id="fixed",
    )

    contaminated = SemanticTransactionStore.from_snapshot(store.canonical_snapshot())
    contaminated.transact(
        TransactionRequest(
            base_generation=contaminated.current_generation,
            observations=(
                ObservationInput(
                    slot="hidden-allocation-hint",
                    time="2026-09-07T00:00:00+00:00",
                    source="synthetic-evaluator",
                    payload="extra hint",
                ),
            ),
        )
    )
    contaminated_policy = ProjectionPolicy()
    contaminated_projection = project_scope(contaminated, contaminated_policy)
    contaminated_snapshot = snapshot_arm(
        contaminated,
        projection_policy=contaminated_policy,
        projection_result=contaminated_projection,
        policy_id="adaptive",
    )

    with pytest.raises(InterventionError, match="invalid arm differences"):
        assert_clean_intervention(
            clean,
            contaminated_snapshot,
            spec=allocation_intervention_spec(),
        )
