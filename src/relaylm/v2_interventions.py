from __future__ import annotations

from dataclasses import dataclass, field, fields
import hashlib
from typing import Iterable

from relaylm.v2_semantics import (
    Expr,
    Proposal,
    SemanticTransactionStore,
    TransactionRequest,
)


class InterventionError(RuntimeError):
    pass


class ResourceLimitError(InterventionError):
    pass


@dataclass(frozen=True, slots=True)
class ProjectionPolicy:
    local_roots: tuple[str, ...] = ()
    cross_task_roots: tuple[str, ...] = ()
    allow_cross_task: bool = False
    evidence_packet_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(set(self.local_roots)) != len(self.local_roots):
            raise ValueError("local projection roots must be unique")
        if len(set(self.cross_task_roots)) != len(self.cross_task_roots):
            raise ValueError("cross-task projection roots must be unique")
        overlap = set(self.local_roots) & set(self.cross_task_roots)
        if overlap:
            raise ValueError(f"local/cross-task roots overlap: {sorted(overlap)}")

    @property
    def eligible_roots(self) -> tuple[str, ...]:
        roots = set(self.local_roots)
        if self.allow_cross_task:
            roots.update(self.cross_task_roots)
        return tuple(sorted(roots))


@dataclass(frozen=True, slots=True)
class ProjectionResult:
    projected_roots: tuple[str, ...]
    evidence_packet_ids: tuple[str, ...]
    canonical_digest: str


@dataclass(frozen=True, slots=True)
class RevisionPolicy:
    allow_revision: bool


@dataclass(frozen=True, slots=True)
class CommitOutcome:
    committed: bool
    reason: str
    generation_id: str
    semantic_id: str | None = None


@dataclass(frozen=True, slots=True)
class ResourceVector:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_units: int = 0
    observation_units: int = 0
    retrieval_units: int = 0
    memory_units: int = 0

    def __post_init__(self) -> None:
        if any(getattr(self, item.name) < 0 for item in fields(self)):
            raise ValueError("resource quantities must be non-negative")

    def __add__(self, other: ResourceVector) -> ResourceVector:
        return ResourceVector(
            **{
                item.name: getattr(self, item.name) + getattr(other, item.name)
                for item in fields(self)
            }
        )

    def fits_within(self, envelope: ResourceVector) -> bool:
        return all(
            getattr(self, item.name) <= getattr(envelope, item.name)
            for item in fields(self)
        )

    def as_tuple(self) -> tuple[int, ...]:
        return tuple(getattr(self, item.name) for item in fields(self))

    def is_zero(self) -> bool:
        return all(value == 0 for value in self.as_tuple())


@dataclass(frozen=True, slots=True)
class ResourceSpend:
    label: str
    cost: ResourceVector


@dataclass(slots=True)
class ResourceLedger:
    envelope: ResourceVector
    _total: ResourceVector = field(default_factory=ResourceVector)
    _entries: list[ResourceSpend] = field(default_factory=list)

    @property
    def total(self) -> ResourceVector:
        return self._total

    @property
    def entries(self) -> tuple[ResourceSpend, ...]:
        return tuple(self._entries)

    def spend(self, label: str, cost: ResourceVector) -> None:
        if not label:
            raise ValueError("resource-spend label must not be empty")
        candidate = self._total + cost
        if not candidate.fits_within(self.envelope):
            raise ResourceLimitError(f"resource envelope exceeded by {label}")
        self._entries.append(ResourceSpend(label, cost))
        self._total = candidate


@dataclass(frozen=True, slots=True)
class Operation:
    name: str
    cost: ResourceVector
    privileged: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("operation name must not be empty")


@dataclass(frozen=True, slots=True)
class OperationPolicy:
    policy_id: str
    plan: tuple[str, ...]
    decision_cost: ResourceVector = ResourceVector()
    privileged: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("policy id must not be empty")


@dataclass(slots=True)
class MeasurementTrace:
    _events: list[str] = field(default_factory=list)

    def record(self, event: str) -> None:
        if not event:
            raise ValueError("measurement event must not be empty")
        self._events.append(event)

    def snapshot(self) -> tuple[str, ...]:
        return tuple(self._events)


@dataclass(frozen=True, slots=True)
class PolicyRun:
    policy_id: str
    selected_operations: tuple[str, ...]
    resource_total: ResourceVector
    measurement_events: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArmSnapshot:
    canonical_digest: str
    active_roots: tuple[str, ...]
    provenance_ids: tuple[str, ...]
    projection_local_roots: tuple[str, ...]
    cross_task_candidates: tuple[str, ...]
    allow_cross_task: bool
    projected_roots: tuple[str, ...]
    evidence_packet_ids: tuple[str, ...]
    policy_id: str
    resource_total: ResourceVector
    commit_decisions: tuple[str, ...]
    measurement_events: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InterventionSpec:
    name: str
    allowed_differences: frozenset[str]
    required_differences: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("intervention name must not be empty")
        undeclared_required = self.required_differences - self.allowed_differences
        if undeclared_required:
            raise ValueError(
                "required differences must also be allowed: "
                f"{sorted(undeclared_required)}"
            )


@dataclass(frozen=True, slots=True)
class ArmDiff:
    all_differences: tuple[str, ...]
    unexpected_differences: tuple[str, ...]
    missing_required_differences: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.unexpected_differences and not self.missing_required_differences


def canonical_digest(store: SemanticTransactionStore) -> str:
    return hashlib.sha256(store.canonical_snapshot()).hexdigest()


def project_scope(
    store: SemanticTransactionStore,
    policy: ProjectionPolicy,
) -> ProjectionResult:
    before = store.canonical_snapshot()
    active = set(store.active_generation().active_roots)

    declared_roots = set(policy.local_roots) | set(policy.cross_task_roots)
    missing_roots = declared_roots - active
    if missing_roots:
        raise InterventionError(
            f"projection policy names inactive roots: {sorted(missing_roots)}"
        )

    for record_id in policy.evidence_packet_ids:
        record = store.provenance.get(record_id)
        if record is None:
            raise InterventionError(f"projection Evidence is missing: {record_id}")
        if record.origin != "observed":
            raise InterventionError(
                f"projection packet must be observed Evidence: {record_id}"
            )

    result = ProjectionResult(
        projected_roots=policy.eligible_roots,
        evidence_packet_ids=tuple(sorted(set(policy.evidence_packet_ids))),
        canonical_digest=hashlib.sha256(before).hexdigest(),
    )
    if store.canonical_snapshot() != before:
        raise InterventionError("projection mutated canonical cognition")
    return result


def commit_supported_revision(
    store: SemanticTransactionStore,
    *,
    old_root: str,
    new_expr: Expr,
    observed_support_id: str,
    policy: RevisionPolicy,
) -> CommitOutcome:
    support = store.provenance.get(observed_support_id)
    if support is None or support.origin != "observed":
        raise InterventionError("revision requires an observed support record")
    if old_root not in store.active_generation().active_roots:
        raise InterventionError("revision target must be an active semantic root")

    if not policy.allow_revision:
        return CommitOutcome(
            committed=False,
            reason="revision_disabled",
            generation_id=store.current_generation,
        )

    result = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            proposals=(
                Proposal(
                    expr=new_expr,
                    existing_provenance_support=(observed_support_id,),
                    revision_of=(old_root,),
                    deactivate_roots=(old_root,),
                ),
            ),
        )
    )
    decision = result.decisions[0]
    return CommitOutcome(
        committed=decision.status == "accepted",
        reason=decision.reason,
        generation_id=result.generation_id,
        semantic_id=decision.semantic_id,
    )


def run_operation_plan(
    store: SemanticTransactionStore,
    *,
    operations: Iterable[Operation],
    policy: OperationPolicy,
    ledger: ResourceLedger,
    trace: MeasurementTrace,
    allow_privileged: bool = False,
) -> PolicyRun:
    before = store.canonical_snapshot()
    registry: dict[str, Operation] = {}
    for operation in operations:
        if operation.name in registry:
            raise InterventionError(f"duplicate operation: {operation.name}")
        registry[operation.name] = operation

    selected: list[str] = []
    if policy.privileged and not allow_privileged:
        raise InterventionError("privileged policy is quarantined")

    if not policy.decision_cost.is_zero():
        ledger.spend(f"policy:{policy.policy_id}:decision", policy.decision_cost)
        trace.record(f"policy:{policy.policy_id}:decision")

    for operation_name in policy.plan:
        operation = registry.get(operation_name)
        if operation is None:
            raise InterventionError(f"unknown operation: {operation_name}")
        if operation.privileged and not allow_privileged:
            raise InterventionError(f"privileged operation is quarantined: {operation_name}")
        ledger.spend(operation_name, operation.cost)
        trace.record(f"policy:{policy.policy_id}:operation:{operation_name}")
        selected.append(operation_name)

    if store.canonical_snapshot() != before:
        raise InterventionError("operation policy mutated canonical cognition")

    return PolicyRun(
        policy_id=policy.policy_id,
        selected_operations=tuple(selected),
        resource_total=ledger.total,
        measurement_events=trace.snapshot(),
    )


def snapshot_arm(
    store: SemanticTransactionStore,
    *,
    projection_policy: ProjectionPolicy,
    projection_result: ProjectionResult,
    policy_id: str = "",
    resource_total: ResourceVector = ResourceVector(),
    commit_decisions: tuple[str, ...] = (),
    measurement_events: tuple[str, ...] = (),
) -> ArmSnapshot:
    return ArmSnapshot(
        canonical_digest=canonical_digest(store),
        active_roots=tuple(store.active_generation().active_roots),
        provenance_ids=tuple(sorted(store.provenance)),
        projection_local_roots=tuple(sorted(projection_policy.local_roots)),
        cross_task_candidates=tuple(sorted(projection_policy.cross_task_roots)),
        allow_cross_task=projection_policy.allow_cross_task,
        projected_roots=projection_result.projected_roots,
        evidence_packet_ids=projection_result.evidence_packet_ids,
        policy_id=policy_id,
        resource_total=resource_total,
        commit_decisions=commit_decisions,
        measurement_events=measurement_events,
    )


def compare_arms(
    left: ArmSnapshot,
    right: ArmSnapshot,
    *,
    spec: InterventionSpec,
) -> ArmDiff:
    surfaces = (
        "canonical_digest",
        "active_roots",
        "provenance_ids",
        "projection_local_roots",
        "cross_task_candidates",
        "allow_cross_task",
        "projected_roots",
        "evidence_packet_ids",
        "policy_id",
        "resource_total",
        "commit_decisions",
        "measurement_events",
    )
    differences = tuple(
        surface
        for surface in surfaces
        if getattr(left, surface) != getattr(right, surface)
    )
    unexpected = tuple(
        surface for surface in differences if surface not in spec.allowed_differences
    )
    missing_required = tuple(
        sorted(spec.required_differences - set(differences))
    )
    return ArmDiff(differences, unexpected, missing_required)


def assert_clean_intervention(
    left: ArmSnapshot,
    right: ArmSnapshot,
    *,
    spec: InterventionSpec,
) -> ArmDiff:
    diff = compare_arms(left, right, spec=spec)
    if not diff.clean:
        raise InterventionError(
            f"invalid arm differences for {spec.name}: "
            f"unexpected={diff.unexpected_differences}, "
            f"missing_required={diff.missing_required_differences}"
        )
    return diff
