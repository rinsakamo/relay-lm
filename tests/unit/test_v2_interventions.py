from __future__ import annotations

import pytest

from relaylm.v2_interventions import (
    InterventionError,
    InterventionSpec,
    MeasurementTrace,
    Operation,
    OperationPolicy,
    ProjectionPolicy,
    ResourceLedger,
    ResourceLimitError,
    ResourceVector,
    RevisionPolicy,
    assert_clean_intervention,
    canonical_digest,
    commit_supported_revision,
    compare_arms,
    project_scope,
    run_operation_plan,
    snapshot_arm,
)
from relaylm.v2_semantics import (
    ObservationInput,
    Proposal,
    SemanticTransactionStore,
    TransactionRequest,
    apply,
    literal,
    semantic_id,
)


T0 = "2026-09-04T11:00:00+00:00"
T1 = "2026-09-04T11:01:00+00:00"


def transact(store, *, observations=(), proposals=()):
    return store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            observations=tuple(observations),
            proposals=tuple(proposals),
        )
    )


def observed(slot: str, payload: str, *, time: str = T0):
    return ObservationInput(
        slot=slot,
        time=time,
        source="synthetic-world",
        payload=payload,
    )


def clone(store: SemanticTransactionStore) -> SemanticTransactionStore:
    return SemanticTransactionStore.from_snapshot(store.canonical_snapshot())


def base_transfer_store():
    store = SemanticTransactionStore()
    local = apply("target_local", literal("local"))
    reusable = apply("source_structure", literal("shared-rule"))
    transact(store, proposals=(Proposal(local), Proposal(reusable)))
    return store, semantic_id(local), semantic_id(reusable)


def base_correction_store():
    store = SemanticTransactionStore()
    old = apply("world_rule", literal("A"))
    transact(store, proposals=(Proposal(old),))
    return store, old, semantic_id(old)


def transfer_spec() -> InterventionSpec:
    return InterventionSpec(
        "cross-task-project-eligibility",
        frozenset({"allow_cross_task", "projected_roots"}),
        frozenset({"allow_cross_task", "projected_roots"}),
    )


def test_d1_projection_eligibility_ablation_changes_only_declared_scope():
    base, local_id, reusable_id = base_transfer_store()
    blocked = clone(base)
    reusable = clone(base)

    blocked_policy = ProjectionPolicy(
        local_roots=(local_id,),
        cross_task_roots=(reusable_id,),
        allow_cross_task=False,
    )
    reusable_policy = ProjectionPolicy(
        local_roots=(local_id,),
        cross_task_roots=(reusable_id,),
        allow_cross_task=True,
    )
    blocked_projection = project_scope(blocked, blocked_policy)
    reusable_projection = project_scope(reusable, reusable_policy)

    left = snapshot_arm(
        blocked,
        projection_policy=blocked_policy,
        projection_result=blocked_projection,
        policy_id="transfer-projection",
    )
    right = snapshot_arm(
        reusable,
        projection_policy=reusable_policy,
        projection_result=reusable_projection,
        policy_id="transfer-projection",
    )
    diff = assert_clean_intervention(left, right, spec=transfer_spec())

    assert diff.all_differences == ("allow_cross_task", "projected_roots")
    assert blocked.canonical_snapshot() == reusable.canonical_snapshot()
    assert tuple(sorted(blocked.provenance)) == tuple(sorted(reusable.provenance))
    assert left.projection_local_roots == right.projection_local_roots
    assert left.cross_task_candidates == right.cross_task_candidates
    assert reusable_id in blocked.active_generation().active_roots
    assert reusable_id not in blocked_projection.projected_roots
    assert reusable_id in reusable_projection.projected_roots


def test_d1_candidate_set_change_is_detected_as_hidden_intervention():
    base, local_id, reusable_id = base_transfer_store()
    extra = apply("source_structure", literal("different-rule"))
    transact(base, proposals=(Proposal(extra),))
    extra_id = semantic_id(extra)
    left_store = clone(base)
    right_store = clone(base)

    left_policy = ProjectionPolicy(
        local_roots=(local_id,),
        cross_task_roots=(reusable_id,),
        allow_cross_task=False,
    )
    right_policy = ProjectionPolicy(
        local_roots=(local_id,),
        cross_task_roots=(extra_id,),
        allow_cross_task=True,
    )
    left = snapshot_arm(
        left_store,
        projection_policy=left_policy,
        projection_result=project_scope(left_store, left_policy),
    )
    right = snapshot_arm(
        right_store,
        projection_policy=right_policy,
        projection_result=project_scope(right_store, right_policy),
    )

    diff = compare_arms(left, right, spec=transfer_spec())
    assert "cross_task_candidates" in diff.unexpected_differences
    with pytest.raises(InterventionError, match="invalid arm differences"):
        assert_clean_intervention(left, right, spec=transfer_spec())


def test_d2_revision_arms_receive_identical_correction_evidence():
    base, _old_expr, old_id = base_correction_store()
    sticky = clone(base)
    revisable = clone(base)

    sticky_observation = transact(
        sticky,
        observations=(observed("correction", "rule is now B"),),
    )
    revisable_observation = transact(
        revisable,
        observations=(observed("correction", "rule is now B"),),
    )
    sticky_evidence = sticky_observation.observation_records[0]
    revisable_evidence = revisable_observation.observation_records[0]

    assert sticky_evidence == revisable_evidence
    assert sticky.canonical_snapshot() == revisable.canonical_snapshot()

    new_expr = apply("world_rule", literal("B"))
    sticky_outcome = commit_supported_revision(
        sticky,
        old_root=old_id,
        new_expr=new_expr,
        observed_support_id=sticky_evidence,
        policy=RevisionPolicy(allow_revision=False),
    )
    revisable_outcome = commit_supported_revision(
        revisable,
        old_root=old_id,
        new_expr=new_expr,
        observed_support_id=revisable_evidence,
        policy=RevisionPolicy(allow_revision=True),
    )

    assert not sticky_outcome.committed
    assert sticky_outcome.reason == "revision_disabled"
    assert revisable_outcome.committed
    assert old_id in sticky.active_generation().active_roots
    assert old_id not in revisable.active_generation().active_roots
    assert semantic_id(new_expr) in revisable.active_generation().active_roots


def test_d3_allocator_policy_substitution_uses_one_operation_surface_and_ledger():
    store = SemanticTransactionStore()
    baseline_snapshot = store.canonical_snapshot()
    operations = (
        Operation("think", ResourceVector(calls=1, latency_units=2)),
        Operation(
            "meta_observe",
            ResourceVector(latency_units=1, observation_units=1),
        ),
    )
    envelope = ResourceVector(
        calls=2,
        latency_units=7,
        observation_units=2,
    )

    fixed_ledger = ResourceLedger(envelope)
    fixed_trace = MeasurementTrace()
    fixed_run = run_operation_plan(
        store,
        operations=operations,
        policy=OperationPolicy("fixed", ("think",)),
        ledger=fixed_ledger,
        trace=fixed_trace,
    )

    adaptive_ledger = ResourceLedger(envelope)
    adaptive_trace = MeasurementTrace()
    adaptive_run = run_operation_plan(
        store,
        operations=operations,
        policy=OperationPolicy(
            "adaptive",
            ("meta_observe", "think"),
            decision_cost=ResourceVector(latency_units=1),
        ),
        ledger=adaptive_ledger,
        trace=adaptive_trace,
    )

    assert store.canonical_snapshot() == baseline_snapshot
    assert fixed_run.selected_operations == ("think",)
    assert adaptive_run.selected_operations == ("meta_observe", "think")
    assert adaptive_run.resource_total.observation_units == 1
    assert adaptive_run.resource_total.latency_units > fixed_run.resource_total.latency_units
    assert adaptive_ledger.entries[0].label == "policy:adaptive:decision"

    empty_projection_policy = ProjectionPolicy()
    empty_projection = project_scope(store, empty_projection_policy)
    left = snapshot_arm(
        store,
        projection_policy=empty_projection_policy,
        projection_result=empty_projection,
        policy_id=fixed_run.policy_id,
        resource_total=fixed_run.resource_total,
        measurement_events=fixed_run.measurement_events,
    )
    right = snapshot_arm(
        store,
        projection_policy=empty_projection_policy,
        projection_result=empty_projection,
        policy_id=adaptive_run.policy_id,
        resource_total=adaptive_run.resource_total,
        measurement_events=adaptive_run.measurement_events,
    )
    diff = assert_clean_intervention(
        left,
        right,
        spec=InterventionSpec(
            "allocator-policy-substitution",
            frozenset({"policy_id", "resource_total", "measurement_events"}),
            frozenset({"policy_id", "resource_total", "measurement_events"}),
        ),
    )
    assert diff.clean


def test_d3_oracle_privilege_and_resource_limits_are_explicit():
    store = SemanticTransactionStore()
    operation = Operation(
        "oracle_hint",
        ResourceVector(observation_units=1),
        privileged=True,
    )
    policy = OperationPolicy("oracle", ("oracle_hint",), privileged=True)

    with pytest.raises(InterventionError, match="privileged policy"):
        run_operation_plan(
            store,
            operations=(operation,),
            policy=policy,
            ledger=ResourceLedger(ResourceVector(observation_units=1)),
            trace=MeasurementTrace(),
        )

    run = run_operation_plan(
        store,
        operations=(operation,),
        policy=policy,
        ledger=ResourceLedger(ResourceVector(observation_units=1)),
        trace=MeasurementTrace(),
        allow_privileged=True,
    )
    assert run.resource_total.observation_units == 1

    with pytest.raises(ResourceLimitError):
        run_operation_plan(
            store,
            operations=(Operation("think", ResourceVector(calls=2)),),
            policy=OperationPolicy("too-expensive", ("think",)),
            ledger=ResourceLedger(ResourceVector(calls=1)),
            trace=MeasurementTrace(),
        )


def test_d4_one_shot_evidence_does_not_silently_become_durable_semantics():
    store, old_expr, old_id = base_correction_store()
    correction = apply("world_rule", literal("B"))
    observation = transact(
        store,
        observations=(observed("correction", "rule is now B"),),
    )
    evidence_id = observation.observation_records[0]

    current_policy = ProjectionPolicy(
        local_roots=(old_id,),
        evidence_packet_ids=(evidence_id,),
    )
    current_scope = project_scope(store, current_policy)
    assert current_scope.evidence_packet_ids == (evidence_id,)
    assert store.query_status(old_expr) == "TRUE"
    assert store.query_status(correction) == "UNKNOWN"

    later_policy = ProjectionPolicy(local_roots=(old_id,))
    later_scope = project_scope(store, later_policy)
    assert later_scope.evidence_packet_ids == ()
    assert later_scope.projected_roots == (old_id,)
    assert store.query_status(correction) == "UNKNOWN"
    assert evidence_id in store.provenance


def test_d5_supported_correction_propagates_without_reinjecting_packet():
    store, _old_expr, old_id = base_correction_store()
    new_expr = apply("world_rule", literal("B"))
    observation = transact(
        store,
        observations=(observed("correction", "rule is now B"),),
    )
    evidence_id = observation.observation_records[0]
    historical_generation = store.current_generation

    outcome = commit_supported_revision(
        store,
        old_root=old_id,
        new_expr=new_expr,
        observed_support_id=evidence_id,
        policy=RevisionPolicy(allow_revision=True),
    )
    new_id = semantic_id(new_expr)
    assert outcome.committed
    assert new_id in store.active_generation().active_roots
    assert old_id not in store.active_generation().active_roots
    assert old_id in store.semantic_nodes
    assert old_id in store.generations[historical_generation].active_roots

    later_policy = ProjectionPolicy(local_roots=(new_id,))
    later_scope = project_scope(store, later_policy)
    assert later_scope.evidence_packet_ids == ()
    assert later_scope.projected_roots == (new_id,)

    producer_records = [
        record
        for record in store.provenance.values()
        if any(
            link.relation == "produces" and link.target == f"sem:{new_id}"
            for link in record.links
        )
    ]
    assert producer_records
    assert any(
        link.relation == "supports" and link.target == evidence_id
        for record in producer_records
        for link in record.links
    )


def test_d6_measurement_and_resource_instrumentation_have_no_authority():
    store, local_id, reusable_id = base_transfer_store()
    before = store.canonical_snapshot()

    trace = MeasurementTrace()
    trace.record("threshold-crossed:synthetic")
    ledger = ResourceLedger(ResourceVector(calls=2, latency_units=4))
    ledger.spend("measurement-only", ResourceVector(latency_units=1))
    policy = ProjectionPolicy(
        local_roots=(local_id,),
        cross_task_roots=(reusable_id,),
        allow_cross_task=True,
    )
    projection = project_scope(store, policy)

    assert trace.snapshot() == ("threshold-crossed:synthetic",)
    assert ledger.total.latency_units == 1
    assert store.canonical_snapshot() == before
    assert "threshold-crossed:synthetic" not in store.canonical_snapshot().decode("utf-8")
    assert all(record.origin != "observed" for record in store.provenance.values())
    assert reusable_id in projection.projected_roots


def test_d7_arm_diff_rejects_hidden_evidence_contamination():
    base, local_id, reusable_id = base_transfer_store()
    clean_left = clone(base)
    clean_right = clone(base)

    left_policy = ProjectionPolicy(
        local_roots=(local_id,),
        cross_task_roots=(reusable_id,),
        allow_cross_task=False,
    )
    right_policy = ProjectionPolicy(
        local_roots=(local_id,),
        cross_task_roots=(reusable_id,),
        allow_cross_task=True,
    )
    left_projection = project_scope(clean_left, left_policy)
    right_projection = project_scope(clean_right, right_policy)
    clean_spec = transfer_spec()
    assert assert_clean_intervention(
        snapshot_arm(
            clean_left,
            projection_policy=left_policy,
            projection_result=left_projection,
            policy_id="transfer",
        ),
        snapshot_arm(
            clean_right,
            projection_policy=right_policy,
            projection_result=right_projection,
            policy_id="transfer",
        ),
        spec=clean_spec,
    ).clean

    contaminated = clone(base)
    contaminated_projection = project_scope(contaminated, right_policy)
    transact(
        contaminated,
        observations=(observed("hidden", "extra target hint", time=T1),),
    )
    contaminated_snapshot = snapshot_arm(
        contaminated,
        projection_policy=right_policy,
        projection_result=contaminated_projection,
        policy_id="transfer",
    )
    clean_snapshot = snapshot_arm(
        clean_left,
        projection_policy=left_policy,
        projection_result=left_projection,
        policy_id="transfer",
    )

    diff = compare_arms(clean_snapshot, contaminated_snapshot, spec=clean_spec)
    assert "canonical_digest" in diff.unexpected_differences
    assert "provenance_ids" in diff.unexpected_differences
    with pytest.raises(InterventionError, match="invalid arm differences"):
        assert_clean_intervention(
            clean_snapshot,
            contaminated_snapshot,
            spec=clean_spec,
        )


def test_arm_diff_rejects_a_noop_when_difference_is_required():
    base, local_id, reusable_id = base_transfer_store()
    left_store = clone(base)
    right_store = clone(base)
    policy = ProjectionPolicy(
        local_roots=(local_id,),
        cross_task_roots=(reusable_id,),
        allow_cross_task=False,
    )
    left = snapshot_arm(
        left_store,
        projection_policy=policy,
        projection_result=project_scope(left_store, policy),
    )
    right = snapshot_arm(
        right_store,
        projection_policy=policy,
        projection_result=project_scope(right_store, policy),
    )

    diff = compare_arms(left, right, spec=transfer_spec())
    assert diff.missing_required_differences == (
        "allow_cross_task",
        "projected_roots",
    )
    with pytest.raises(InterventionError, match="missing_required"):
        assert_clean_intervention(left, right, spec=transfer_spec())


def test_projection_rejects_endogenous_trace_as_evidence_packet():
    store = SemanticTransactionStore()
    result = transact(store, proposals=(Proposal(apply("hypothesis", literal("x"))),))
    root_id = result.decisions[0].semantic_id
    endogenous_record = next(
        record.id
        for record in store.provenance.values()
        if record.origin == "endogenous"
    )

    with pytest.raises(InterventionError, match="must be observed Evidence"):
        project_scope(
            store,
            ProjectionPolicy(
                local_roots=(root_id,),
                evidence_packet_ids=(endogenous_record,),
            ),
        )


def test_resource_vector_preserves_non_fungible_dimensions():
    token_rich_but_no_observation = ResourceVector(
        input_tokens=1000,
        observation_units=0,
    )
    observation_required = ResourceVector(observation_units=1)
    assert not observation_required.fits_within(token_rich_but_no_observation)
    assert canonical_digest(SemanticTransactionStore())
