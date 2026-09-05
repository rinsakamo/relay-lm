from __future__ import annotations

import pytest

from relaylm.v2_allocation_experiment import (
    REGIMES,
    adaptive_policy,
    allocation_intervention_spec,
    allocation_operations,
    fixed_policy,
    generate_allocation_task,
    heuristic_policy,
    oracle_policy,
    prepare_r0_allocation_arms,
    prepare_r0_oracle_arm,
)
from relaylm.v2_interventions import (
    InterventionError,
    MeasurementTrace,
    ProjectionPolicy,
    ResourceLedger,
    ResourceVector,
    assert_clean_intervention,
    project_scope,
    run_operation_plan,
    snapshot_arm,
)
from relaylm.v2_semantics import ObservationInput, SemanticTransactionStore, TransactionRequest


def test_r0_task_generation_is_deterministic_and_regime_is_not_public() -> None:
    for regime in REGIMES:
        first = generate_allocation_task(seed=17, regime=regime)
        replay = generate_allocation_task(seed=17, regime=regime)
        assert first == replay
        assert first.model_packet() == replay.model_packet()
        assert regime.encode("utf-8") not in first.model_packet()

    public_packets = {
        generate_allocation_task(seed=17, regime=regime).model_packet()
        for regime in REGIMES
    }
    assert len(public_packets) == 1
    assert (
        generate_allocation_task(seed=18, regime="saturated").model_packet()
        != generate_allocation_task(seed=17, regime="saturated").model_packet()
    )


def test_r0_regimes_define_distinct_evaluator_side_work_values() -> None:
    assert generate_allocation_task(seed=1, regime="saturated").ideal_operation == "stop"
    assert (
        generate_allocation_task(seed=1, regime="depth_beneficial").ideal_operation
        == "think"
    )
    assert (
        generate_allocation_task(seed=1, regime="retrieval_beneficial").ideal_operation
        == "retrieve"
    )
    assert (
        generate_allocation_task(seed=1, regime="observation_beneficial").ideal_operation
        == "observe"
    )
    assert generate_allocation_task(seed=1, regime="trap").ideal_operation == "stop"


def test_r0_fixed_heuristic_adaptive_share_task_operations_budget_and_cognition() -> None:
    task = generate_allocation_task(seed=23, regime="retrieval_beneficial")
    arms = prepare_r0_allocation_arms(task)

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


def test_r0_adaptive_meta_information_is_charged_before_selected_work() -> None:
    task = generate_allocation_task(seed=31, regime="observation_beneficial")
    policy = adaptive_policy(task)
    assert policy.plan == ("meta_probe", "observe")
    assert policy.decision_cost == ResourceVector(latency_units=1)

    arms = prepare_r0_allocation_arms(task)
    assert arms.adaptive.run.selected_operations == ("meta_probe", "observe")
    assert arms.adaptive.run.resource_total.observation_units == 2
    assert arms.adaptive.run.resource_total.latency_units >= 5
    assert arms.adaptive.run.measurement_events[0] == "policy:adaptive:decision"
    assert "policy:adaptive:operation:meta_probe" in arms.adaptive.run.measurement_events


def test_r0_heuristic_uses_only_public_surface_signals() -> None:
    same_seed = [generate_allocation_task(seed=41, regime=regime) for regime in REGIMES]
    plans = {heuristic_policy(task).plan for task in same_seed}
    assert len(plans) == 1

    task = same_seed[0]
    if task.visible_uncertainty == 2:
        expected = ("retrieve",)
    elif task.visible_complexity == 2:
        expected = ("think",)
    else:
        expected = ("stop",)
    assert heuristic_policy(task).plan == expected


def test_r0_oracle_is_privileged_and_not_a_deployable_policy() -> None:
    task = generate_allocation_task(seed=7, regime="depth_beneficial")
    policy = oracle_policy(task)
    assert policy.privileged
    assert policy.plan == ("think",)

    with pytest.raises(InterventionError, match="privileged policy"):
        run_operation_plan(
            SemanticTransactionStore(),
            operations=allocation_operations(),
            policy=policy,
            ledger=ResourceLedger(ResourceVector(calls=2, input_tokens=24, output_tokens=24, latency_units=8, observation_units=2, retrieval_units=2)),
            trace=MeasurementTrace(),
        )

    oracle = prepare_r0_oracle_arm(task)
    assert oracle.arm_id == "A3"
    assert oracle.run.policy_id == "oracle"
    assert oracle.run.selected_operations == ("think",)


def test_r0_policy_instrumentation_does_not_mutate_canonical_cognition() -> None:
    store = SemanticTransactionStore()
    before = store.canonical_snapshot()
    task = generate_allocation_task(seed=53, regime="depth_beneficial")
    run_operation_plan(
        store,
        operations=allocation_operations(),
        policy=adaptive_policy(task),
        ledger=ResourceLedger(ResourceVector(calls=2, input_tokens=24, output_tokens=24, latency_units=8, observation_units=2, retrieval_units=2)),
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
                    time="2026-09-05T00:00:00+00:00",
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


def test_r0_fixed_policy_is_regime_blind() -> None:
    assert fixed_policy().plan == ("think",)
    assert {
        fixed_policy().plan
        for _task in (generate_allocation_task(seed=5, regime=r) for r in REGIMES)
    } == {("think",)}
