from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from relaylm.v2_interventions import (
    ArmSnapshot,
    InterventionSpec,
    MeasurementTrace,
    Operation,
    OperationPolicy,
    ProjectionPolicy,
    ResourceLedger,
    ResourceVector,
    PolicyRun,
    assert_clean_intervention,
    project_scope,
    run_operation_plan,
    snapshot_arm,
)
from relaylm.v2_semantics import SemanticTransactionStore


REGIMES = (
    "saturated",
    "depth_beneficial",
    "retrieval_beneficial",
    "observation_beneficial",
    "trap",
)


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _seed_bytes(seed: int, label: str) -> bytes:
    if type(seed) is not int:
        raise TypeError("seed must be an int")
    if not label:
        raise ValueError("seed label must not be empty")
    return hashlib.sha256(
        f"relaylm2-allocation-r0|{seed}|{label}".encode("utf-8")
    ).digest()


@dataclass(frozen=True, slots=True)
class AllocationTask:
    seed: int
    regime: str
    visible_complexity: int
    visible_uncertainty: int
    public_values: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.regime not in REGIMES:
            raise ValueError(f"unsupported allocation regime: {self.regime}")
        if not 0 <= self.visible_complexity <= 2:
            raise ValueError("visible complexity must be in [0, 2]")
        if not 0 <= self.visible_uncertainty <= 2:
            raise ValueError("visible uncertainty must be in [0, 2]")
        if len(self.public_values) != 4:
            raise ValueError("public task vector must have width four")

    def model_packet(self) -> bytes:
        return _json_bytes(
            {
                "instruction": (
                    "Solve the task using only the supplied task information. "
                    "The experiment may separately allocate additional cognitive work."
                ),
                "surface": {
                    "complexity": self.visible_complexity,
                    "uncertainty": self.visible_uncertainty,
                    "values": list(self.public_values),
                },
            }
        )

    @property
    def public_digest(self) -> str:
        return hashlib.sha256(self.model_packet()).hexdigest()

    @property
    def ideal_operation(self) -> str:
        return {
            "saturated": "stop",
            "depth_beneficial": "think",
            "retrieval_beneficial": "retrieve",
            "observation_beneficial": "observe",
            "trap": "stop",
        }[self.regime]


@dataclass(slots=True)
class AllocationR0Arm:
    arm_id: str
    task_digest: str
    operation_surface_digest: str
    envelope: ResourceVector
    run: PolicyRun
    snapshot: ArmSnapshot


@dataclass(slots=True)
class AllocationR0ArmSet:
    fixed: AllocationR0Arm
    heuristic: AllocationR0Arm
    adaptive: AllocationR0Arm


def generate_allocation_task(*, seed: int, regime: str) -> AllocationTask:
    if regime not in REGIMES:
        raise ValueError(f"unsupported allocation regime: {regime}")
    raw = _seed_bytes(seed, "public")
    return AllocationTask(
        seed=seed,
        regime=regime,
        visible_complexity=raw[0] % 3,
        visible_uncertainty=raw[1] % 3,
        public_values=tuple(raw[index] % 10 for index in range(2, 6)),
    )


def allocation_operations() -> tuple[Operation, ...]:
    return (
        Operation("stop", ResourceVector()),
        Operation(
            "think",
            ResourceVector(calls=1, input_tokens=8, output_tokens=8, latency_units=2),
        ),
        Operation(
            "retrieve",
            ResourceVector(
                calls=1,
                input_tokens=6,
                output_tokens=4,
                latency_units=2,
                retrieval_units=1,
            ),
        ),
        Operation(
            "observe",
            ResourceVector(
                calls=1,
                input_tokens=4,
                output_tokens=4,
                latency_units=3,
                observation_units=1,
            ),
        ),
        Operation(
            "meta_probe",
            ResourceVector(latency_units=1, observation_units=1),
        ),
    )


def allocation_envelope() -> ResourceVector:
    return ResourceVector(
        calls=2,
        input_tokens=24,
        output_tokens=24,
        latency_units=8,
        observation_units=2,
        retrieval_units=2,
    )


def operation_surface_digest(operations: tuple[Operation, ...]) -> str:
    return _digest(
        [
            {
                "name": operation.name,
                "privileged": operation.privileged,
                "cost": list(operation.cost.as_tuple()),
            }
            for operation in operations
        ]
    )


def fixed_policy() -> OperationPolicy:
    return OperationPolicy("fixed", ("think",))


def heuristic_policy(task: AllocationTask) -> OperationPolicy:
    if task.visible_uncertainty == 2:
        plan = ("retrieve",)
    elif task.visible_complexity == 2:
        plan = ("think",)
    else:
        plan = ("stop",)
    return OperationPolicy("cheap-heuristic", plan)


def adaptive_policy(task: AllocationTask) -> OperationPolicy:
    # R0 gives the adaptive arm a synthetic meta-probe result only after it pays
    # for the declared meta_probe operation. This is mechanism admission, not
    # evidence that a physical allocator can infer the hidden regime cheaply.
    return OperationPolicy(
        "adaptive",
        ("meta_probe", task.ideal_operation),
        decision_cost=ResourceVector(latency_units=1),
    )


def oracle_policy(task: AllocationTask) -> OperationPolicy:
    return OperationPolicy(
        "oracle",
        (task.ideal_operation,),
        privileged=True,
    )


def allocation_intervention_spec() -> InterventionSpec:
    return InterventionSpec(
        "allocation-policy-substitution",
        frozenset({"policy_id", "resource_total", "measurement_events"}),
        frozenset({"policy_id"}),
    )


def _clone_store(store: SemanticTransactionStore) -> SemanticTransactionStore:
    return SemanticTransactionStore.from_snapshot(store.canonical_snapshot())


def _run_arm(
    *,
    arm_id: str,
    task: AllocationTask,
    base: SemanticTransactionStore,
    operations: tuple[Operation, ...],
    envelope: ResourceVector,
    policy: OperationPolicy,
    allow_privileged: bool = False,
) -> AllocationR0Arm:
    store = _clone_store(base)
    projection_policy = ProjectionPolicy()
    projection = project_scope(store, projection_policy)
    ledger = ResourceLedger(envelope)
    trace = MeasurementTrace()
    run = run_operation_plan(
        store,
        operations=operations,
        policy=policy,
        ledger=ledger,
        trace=trace,
        allow_privileged=allow_privileged,
    )
    return AllocationR0Arm(
        arm_id=arm_id,
        task_digest=task.public_digest,
        operation_surface_digest=operation_surface_digest(operations),
        envelope=envelope,
        run=run,
        snapshot=snapshot_arm(
            store,
            projection_policy=projection_policy,
            projection_result=projection,
            policy_id=run.policy_id,
            resource_total=run.resource_total,
            measurement_events=run.measurement_events,
        ),
    )


def prepare_r0_allocation_arms(task: AllocationTask) -> AllocationR0ArmSet:
    base = SemanticTransactionStore()
    operations = allocation_operations()
    envelope = allocation_envelope()
    arms = AllocationR0ArmSet(
        fixed=_run_arm(
            arm_id="A0",
            task=task,
            base=base,
            operations=operations,
            envelope=envelope,
            policy=fixed_policy(),
        ),
        heuristic=_run_arm(
            arm_id="A1",
            task=task,
            base=base,
            operations=operations,
            envelope=envelope,
            policy=heuristic_policy(task),
        ),
        adaptive=_run_arm(
            arm_id="A2",
            task=task,
            base=base,
            operations=operations,
            envelope=envelope,
            policy=adaptive_policy(task),
        ),
    )
    assert_matched_allocation_arms(arms)
    return arms


def prepare_r0_oracle_arm(task: AllocationTask) -> AllocationR0Arm:
    return _run_arm(
        arm_id="A3",
        task=task,
        base=SemanticTransactionStore(),
        operations=allocation_operations(),
        envelope=allocation_envelope(),
        policy=oracle_policy(task),
        allow_privileged=True,
    )


def assert_matched_allocation_arms(arms: AllocationR0ArmSet) -> None:
    candidates = (arms.fixed, arms.heuristic, arms.adaptive)
    task_digests = {arm.task_digest for arm in candidates}
    operation_digests = {arm.operation_surface_digest for arm in candidates}
    envelopes = {arm.envelope.as_tuple() for arm in candidates}
    canonical_digests = {arm.snapshot.canonical_digest for arm in candidates}
    provenance_ids = {arm.snapshot.provenance_ids for arm in candidates}
    if len(task_digests) != 1:
        raise RuntimeError("allocation arms do not share one public task")
    if len(operation_digests) != 1:
        raise RuntimeError("allocation arms do not share one operation surface")
    if len(envelopes) != 1:
        raise RuntimeError("allocation arms do not share one resource envelope")
    if len(canonical_digests) != 1 or len(provenance_ids) != 1:
        raise RuntimeError("allocation policy contaminated canonical cognition")

    spec = allocation_intervention_spec()
    assert_clean_intervention(arms.fixed.snapshot, arms.heuristic.snapshot, spec=spec)
    assert_clean_intervention(arms.fixed.snapshot, arms.adaptive.snapshot, spec=spec)
