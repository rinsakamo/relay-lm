from __future__ import annotations

from dataclasses import dataclass
import hashlib

from relaylm.v2_interventions import (
    Operation,
    ResourceLedger,
    ResourceLimitError,
    ResourceVector,
)
from tools.v2_event_semantic_kernel import EventSemanticKernel


class CognitiveWorkAdmissionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CognitiveStart:
    lineage_id: str
    head_id: str
    canonical_digest: str
    occurrence_ids: tuple[str, ...]
    boundary_digest: str


@dataclass(frozen=True, slots=True)
class ExecutionBinding:
    model_identity: str
    runtime_identity: str
    hardware_identity: str
    tokenizer_identity: str
    template_identity: str
    context_limit: int
    decoding_identity: str
    reasoning_identity: str

    def __post_init__(self) -> None:
        text_fields = (
            self.model_identity,
            self.runtime_identity,
            self.hardware_identity,
            self.tokenizer_identity,
            self.template_identity,
            self.decoding_identity,
            self.reasoning_identity,
        )
        if any(not value for value in text_fields):
            raise ValueError("execution binding identities must not be empty")
        if self.context_limit <= 0:
            raise ValueError("context_limit must be positive")


@dataclass(frozen=True, slots=True)
class CognitiveWorkCampaign:
    start: CognitiveStart
    execution: ExecutionBinding
    task_digest: str
    ordinary_information_ids: tuple[str, ...]
    operations: tuple[Operation, ...]
    envelope: ResourceVector

    def __post_init__(self) -> None:
        if not self.task_digest:
            raise ValueError("task_digest must not be empty")
        operation_names = tuple(operation.name for operation in self.operations)
        if len(set(operation_names)) != len(operation_names):
            raise ValueError("operation names must be unique")
        if len(set(self.ordinary_information_ids)) != len(self.ordinary_information_ids):
            raise ValueError("ordinary information ids must be unique")

    @property
    def fingerprint(self) -> str:
        payload = (
            self.start,
            self.execution,
            self.task_digest,
            self.ordinary_information_ids,
            tuple(
                (operation.name, operation.cost.as_tuple(), operation.privileged)
                for operation in self.operations
            ),
            self.envelope.as_tuple(),
        )
        return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AllocationArm:
    arm_id: str
    policy_class: str
    plan: tuple[str, ...]
    decision_cost: ResourceVector = ResourceVector()
    initial_information_ids: tuple[str, ...] = ()
    privileged: bool = False

    def __post_init__(self) -> None:
        if not self.arm_id:
            raise ValueError("arm_id must not be empty")
        if self.policy_class not in {"fixed", "heuristic", "adaptive", "oracle"}:
            raise ValueError(f"unknown policy_class: {self.policy_class}")
        if len(set(self.initial_information_ids)) != len(self.initial_information_ids):
            raise ValueError("initial information ids must be unique")


@dataclass(frozen=True, slots=True)
class ArmAdmission:
    campaign_fingerprint: str
    start: CognitiveStart
    operation_names: tuple[str, ...]
    envelope: ResourceVector
    ordinary_information_ids: tuple[str, ...]
    arm_id: str
    policy_class: str
    plan: tuple[str, ...]
    decision_cost: ResourceVector
    resource_total: ResourceVector
    privileged: bool


@dataclass(frozen=True, slots=True)
class MatchedDeployableAdmission:
    campaign_fingerprint: str
    arm_ids: tuple[str, ...]


def freeze_cognitive_start(
    kernel: EventSemanticKernel,
    *,
    lineage_id: str,
) -> CognitiveStart:
    if not lineage_id:
        raise ValueError("lineage_id must not be empty")
    head = kernel.heads[kernel.current_head]
    canonical_digest = hashlib.sha256(repr(head.cells).encode("utf-8")).hexdigest()
    occurrences = tuple(
        sorted(
            kernel.occurrences.values(),
            key=lambda occurrence: occurrence.receipt_index,
        )
    )
    occurrence_ids = tuple(occurrence.id for occurrence in occurrences)
    boundary_payload = tuple(
        (
            occurrence.id,
            occurrence.source,
            occurrence.content,
            occurrence.receipt_index,
            occurrence.world_rank,
            occurrence.logical_ingress_id,
            occurrence.redacted,
        )
        for occurrence in occurrences
    )
    boundary_digest = hashlib.sha256(
        repr(boundary_payload).encode("utf-8")
    ).hexdigest()
    return CognitiveStart(
        lineage_id=lineage_id,
        head_id=kernel.current_head,
        canonical_digest=canonical_digest,
        occurrence_ids=occurrence_ids,
        boundary_digest=boundary_digest,
    )


def admit_arm(
    campaign: CognitiveWorkCampaign,
    arm: AllocationArm,
) -> ArmAdmission:
    if arm.policy_class == "oracle" and not arm.privileged:
        raise CognitiveWorkAdmissionError("oracle arm must be privileged")
    if arm.privileged and arm.policy_class != "oracle":
        raise CognitiveWorkAdmissionError(
            "deployable policy classes cannot claim privileged information"
        )

    ordinary = set(campaign.ordinary_information_ids)
    initial = set(arm.initial_information_ids)
    if arm.privileged:
        if not ordinary.issubset(initial):
            raise CognitiveWorkAdmissionError(
                "oracle arm must retain all ordinary task information"
            )
    elif initial != ordinary:
        raise CognitiveWorkAdmissionError(
            "deployable arm initial information differs from campaign ordinary information"
        )

    registry = {operation.name: operation for operation in campaign.operations}
    ledger = ResourceLedger(campaign.envelope)

    try:
        if not arm.decision_cost.is_zero():
            ledger.spend(f"policy:{arm.arm_id}:decision", arm.decision_cost)
        for operation_name in arm.plan:
            operation = registry.get(operation_name)
            if operation is None:
                raise CognitiveWorkAdmissionError(
                    f"undeclared cognitive operation: {operation_name}"
                )
            if operation.privileged and not arm.privileged:
                raise CognitiveWorkAdmissionError(
                    f"deployable arm selected privileged operation: {operation_name}"
                )
            ledger.spend(operation_name, operation.cost)
    except ResourceLimitError as exc:
        raise CognitiveWorkAdmissionError(
            f"resource envelope rejected arm {arm.arm_id}: {exc}"
        ) from exc

    return ArmAdmission(
        campaign_fingerprint=campaign.fingerprint,
        start=campaign.start,
        operation_names=tuple(sorted(registry)),
        envelope=campaign.envelope,
        ordinary_information_ids=campaign.ordinary_information_ids,
        arm_id=arm.arm_id,
        policy_class=arm.policy_class,
        plan=arm.plan,
        decision_cost=arm.decision_cost,
        resource_total=ledger.total,
        privileged=arm.privileged,
    )


def assert_matched_deployable_arms(
    *admissions: ArmAdmission,
) -> MatchedDeployableAdmission:
    if len(admissions) < 2:
        raise CognitiveWorkAdmissionError("at least two deployable arms are required")
    if any(admission.privileged for admission in admissions):
        raise CognitiveWorkAdmissionError(
            "oracle/privileged admission cannot enter deployable matched comparison"
        )

    first = admissions[0]
    fixed_surface = (
        first.campaign_fingerprint,
        first.start,
        first.operation_names,
        first.envelope,
        first.ordinary_information_ids,
    )
    for admission in admissions[1:]:
        candidate = (
            admission.campaign_fingerprint,
            admission.start,
            admission.operation_names,
            admission.envelope,
            admission.ordinary_information_ids,
        )
        if candidate != fixed_surface:
            raise CognitiveWorkAdmissionError(
                "deployable arms differ outside allocation policy/cost surfaces"
            )

    return MatchedDeployableAdmission(
        campaign_fingerprint=first.campaign_fingerprint,
        arm_ids=tuple(admission.arm_id for admission in admissions),
    )
