from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from relaylm.v2_interventions import ResourceVector
from relaylm.v2_transfer_actual_model import ExperimentClient
from tools.v2_cognitive_work_r0 import ExecutionBinding
from tools import v2_cognitive_work_r2_host as historical_host
from tools.v2_cognitive_work_r2_replacement_preregistration import (
    ANSWER_PROTOCOL_VERSION,
    CONTEXT_LIMIT,
    CounterfactualOutcome,
    OperationResult,
    PlannedProviderCall,
    R2PreregistrationError,
    R2ReplacementPreregistration,
    TaskOperationBank,
    a0_policy,
    a1_policy,
    a3_oracle,
    allocator_messages,
    answer_messages,
    build_preregistration,
    counterfactual_outcome,
    parse_answer,
    parse_operation,
    physical_call_plan,
    revision_messages,
)


FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT = (
    "6a85ef75241baf65ebf1044ebbb3583e123063d7"
)
FROZEN_REPLACEMENT_ROOT_SEED = (
    "sha256:a4610e491d2ff5358d65a468d91163097608faf2dd223903300c24339207cdfd"
)
CLAIM_STATUS = "R2_REPLACEMENT_PREREGISTERED_PHYSICAL_RESULT"

MANIFEST_NAME = historical_host.MANIFEST_NAME
STATE_NAME = historical_host.STATE_NAME
REQUEST_EVIDENCE_NAME = historical_host.REQUEST_EVIDENCE_NAME
BANK_EVIDENCE_NAME = historical_host.BANK_EVIDENCE_NAME
RESULT_NAME = historical_host.RESULT_NAME

CognitiveWorkR2ReplacementHostError = historical_host.CognitiveWorkR2HostError
RepositoryState = historical_host.RepositoryState


@dataclass(frozen=True, slots=True)
class R2ReplacementExecutionAuthorization:
    """Separate execution gate for the replacement experiment identity only."""

    authorization_id: str
    execution_repository_commit: str
    preregistration_commit: str
    physical_execution_authorized: bool

    def __post_init__(self) -> None:
        if not self.authorization_id.strip():
            raise CognitiveWorkR2ReplacementHostError(
                "replacement execution authorization id must be non-empty"
            )
        if not self.execution_repository_commit.strip():
            raise CognitiveWorkR2ReplacementHostError(
                "replacement execution authorization repository commit must be non-empty"
            )
        if self.preregistration_commit != FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT:
            raise CognitiveWorkR2ReplacementHostError(
                "replacement execution authorization must bind the repaired preregistration"
            )


@dataclass(frozen=True, slots=True)
class R2ReplacementHostIdentity:
    repository_commit: str
    repository_tree: str
    execution: ExecutionBinding
    preregistration_commit: str = FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT
    automatic_retry: bool = False
    semantic_retry: bool = False

    def __post_init__(self) -> None:
        if not self.repository_commit.strip() or not self.repository_tree.strip():
            raise CognitiveWorkR2ReplacementHostError(
                "replacement repository commit/tree must be non-empty"
            )
        if self.preregistration_commit != FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT:
            raise CognitiveWorkR2ReplacementHostError(
                "replacement host identity must preserve the repaired preregistration commit"
            )
        if self.execution.context_limit != CONTEXT_LIMIT:
            raise CognitiveWorkR2ReplacementHostError(
                f"replacement execution binding must preserve context_limit={CONTEXT_LIMIT}"
            )
        if self.automatic_retry or self.semantic_retry:
            raise CognitiveWorkR2ReplacementHostError(
                "replacement R2 host must disable automatic and semantic retry"
            )
        preregistration = build_preregistration(self.preregistration_commit)
        if preregistration.root_seed != FROZEN_REPLACEMENT_ROOT_SEED:
            raise CognitiveWorkR2ReplacementHostError(
                "frozen replacement R2 root seed mismatch"
            )
        if preregistration.budget.physical_provider_call_max != 136:
            raise CognitiveWorkR2ReplacementHostError(
                "frozen replacement R2 plan must contain exactly 136 calls"
            )

    @property
    def preregistration(self) -> R2ReplacementPreregistration:
        return build_preregistration(self.preregistration_commit)

    @property
    def fingerprint(self) -> str:
        return historical_host._sha256(
            {
                "repository_commit": self.repository_commit,
                "repository_tree": self.repository_tree,
                "execution": asdict(self.execution),
                "preregistration_commit": self.preregistration_commit,
                "preregistration_digest": self.preregistration.digest,
                "preregistration_root_seed": self.preregistration.root_seed,
                "answer_protocol_version": ANSWER_PROTOCOL_VERSION,
                "automatic_retry": self.automatic_retry,
                "semantic_retry": self.semantic_retry,
            }
        )


@dataclass(frozen=True, slots=True)
class R2ReplacementHostResult:
    run_id: str
    identity_fingerprint: str
    status: str
    claim_status: str
    citable: bool
    provider_attempts: int
    provider_completions: int
    physical_cost: ResourceVector
    arm_resource_totals: Mapping[str, ResourceVector]
    category: str
    outcomes: Mapping[str, tuple[CounterfactualOutcome, ...]]


def probe_repository(repository_root: str | Path) -> RepositoryState:
    return historical_host.probe_repository(repository_root)


def _validate_repository(
    identity: R2ReplacementHostIdentity,
    observed: RepositoryState,
) -> None:
    if not observed.clean:
        raise CognitiveWorkR2ReplacementHostError("repository checkout is dirty")
    if observed.commit != identity.repository_commit:
        raise CognitiveWorkR2ReplacementHostError(
            "repository commit does not match frozen replacement identity"
        )
    if observed.tree != identity.repository_tree:
        raise CognitiveWorkR2ReplacementHostError(
            "repository tree does not match frozen replacement identity"
        )


def _validate_authorization(
    identity: R2ReplacementHostIdentity,
    authorization: R2ReplacementExecutionAuthorization,
) -> None:
    if not authorization.physical_execution_authorized:
        raise CognitiveWorkR2ReplacementHostError(
            "replacement R2 physical execution is not authorized"
        )
    if authorization.execution_repository_commit != identity.repository_commit:
        raise CognitiveWorkR2ReplacementHostError(
            "replacement execution authorization does not bind the current execution commit"
        )
    if authorization.preregistration_commit != identity.preregistration_commit:
        raise CognitiveWorkR2ReplacementHostError(
            "replacement execution authorization does not bind the repaired preregistration"
        )


def _replacement_result_mapping(
    *,
    run_id: str,
    identity: R2ReplacementHostIdentity,
    preregistration: R2ReplacementPreregistration,
    attempts: int,
    completions: int,
    physical_cost: ResourceVector,
    outcomes: Mapping[str, tuple[CounterfactualOutcome, ...]],
    arm_totals: Mapping[str, ResourceVector],
) -> dict[str, object]:
    result = historical_host._result_mapping(
        run_id=run_id,
        identity=identity,  # type: ignore[arg-type]
        preregistration=preregistration,  # type: ignore[arg-type]
        attempts=attempts,
        completions=completions,
        physical_cost=physical_cost,
        outcomes=outcomes,
        arm_totals=arm_totals,
    )
    result["claim_status"] = CLAIM_STATUS
    result["answer_protocol_version"] = ANSWER_PROTOCOL_VERSION
    result["historical_original_preregistration_commit"] = (
        historical_host.FROZEN_PREREGISTRATION_COMMIT
    )
    return result


def run_r2_replacement_host_campaign(
    *,
    artifact_root: str | Path,
    repository_root: str | Path,
    identity: R2ReplacementHostIdentity,
    authorization: R2ReplacementExecutionAuthorization,
    live_binding_probe: Callable[[], ExecutionBinding],
    client: ExperimentClient,
    run_id: str,
) -> R2ReplacementHostResult:
    """Execute exactly one separately authorized replacement R2 transaction."""

    if not run_id.strip():
        raise CognitiveWorkR2ReplacementHostError(
            "replacement R2 run_id must be non-empty"
        )
    _validate_authorization(identity, authorization)
    observed_repository = probe_repository(repository_root)
    _validate_repository(identity, observed_repository)

    preregistration = identity.preregistration
    if (
        preregistration.merged_pr_commit_sha
        != FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT
    ):
        raise CognitiveWorkR2ReplacementHostError(
            "replacement R2 preregistration commit drift"
        )
    if preregistration.root_seed != FROZEN_REPLACEMENT_ROOT_SEED:
        raise CognitiveWorkR2ReplacementHostError(
            "replacement R2 preregistration root seed drift"
        )
    plan = physical_call_plan(preregistration.tasks)
    if len(plan) != preregistration.budget.physical_provider_call_max or len(plan) != 136:
        raise CognitiveWorkR2ReplacementHostError(
            "replacement R2 physical plan no longer has exactly 136 calls"
        )

    root = historical_host._validate_artifact_root(
        artifact_root=artifact_root,
        repository_root=repository_root,
    )
    manifest = {
        "run_id": run_id,
        "claim_status": CLAIM_STATUS,
        "answer_protocol_version": ANSWER_PROTOCOL_VERSION,
        "execution_authorization": asdict(authorization),
        "execution_repository": {
            "commit": identity.repository_commit,
            "tree": identity.repository_tree,
            "clean_required": True,
        },
        "execution_binding": asdict(identity.execution),
        "identity_fingerprint": identity.fingerprint,
        "preregistration": {
            "commit": preregistration.merged_pr_commit_sha,
            "root_seed": preregistration.root_seed,
            "digest": preregistration.digest,
            "suite_digest": historical_host._task_suite_digest(preregistration),  # type: ignore[arg-type]
            "task_ids": [task.task_id for task in preregistration.tasks],
            "call_plan_digest": historical_host._plan_digest(plan),
            "call_plan_size": len(plan),
        },
        "historical_original_preregistration_commit": (
            historical_host.FROZEN_PREREGISTRATION_COMMIT
        ),
        "budget": asdict(preregistration.budget),
        "retry_policy": {
            "automatic_retry": False,
            "semantic_retry": False,
            "fallback_provider": False,
            "partial_task_replay": False,
        },
        "model_facing_evaluator_fields": False,
        "architecture_consequence": "NONE",
        "production_scheduler_authority": "NONE",
    }
    historical_host._write_json_exclusive(root / MANIFEST_NAME, manifest)
    historical_host._write_json_exclusive(
        root / STATE_NAME,
        {
            "run_id": run_id,
            "status": "RUNNING",
            "provider_attempts": 0,
            "provider_completions": 0,
            "plan_cursor": 0,
            "plan_size": len(plan),
        },
    )

    try:
        preflight = live_binding_probe()
    except Exception as exc:
        historical_host._write_json_atomic(
            root / STATE_NAME,
            {
                "run_id": run_id,
                "status": "INCOMPLETE",
                "provider_attempts": 0,
                "provider_completions": 0,
                "plan_cursor": 0,
                "plan_size": len(plan),
                "failure": {"kind": "preflight_probe_failure", "detail": str(exc)},
            },
        )
        raise CognitiveWorkR2ReplacementHostError(
            "replacement R2 preflight binding probe failed"
        ) from exc
    if preflight != identity.execution:
        historical_host._write_json_atomic(
            root / STATE_NAME,
            {
                "run_id": run_id,
                "status": "INCOMPLETE",
                "provider_attempts": 0,
                "provider_completions": 0,
                "plan_cursor": 0,
                "plan_size": len(plan),
                "failure": {
                    "kind": "preflight_binding_drift",
                    "detail": "preflight binding differs from frozen replacement identity",
                },
            },
        )
        raise CognitiveWorkR2ReplacementHostError(
            "replacement R2 preflight physical binding drift"
        )

    bound = historical_host._BoundPlanClient(
        client=client,
        root=root,
        identity=identity,  # type: ignore[arg-type]
        live_binding_probe=live_binding_probe,
        run_id=run_id,
        plan=plan,
    )
    physical_cost = ResourceVector()
    outcomes_mutable: dict[str, list[CounterfactualOutcome]] = {
        "A0": [],
        "A1": [],
        "A2": [],
        "A3": [],
    }

    try:
        for task in preregistration.tasks:
            base_completion = bound.complete(
                PlannedProviderCall(task.task_id, "BASE", None),
                answer_messages(task),
            )
            base_answer = parse_answer(base_completion.content)
            base_cost = historical_host._completion_cost(base_completion)
            physical_cost = physical_cost + base_cost

            allocator_completion = bound.complete(
                PlannedProviderCall(task.task_id, "A2_ALLOCATE", None),
                allocator_messages(task, base_answer=base_answer),
            )
            a2_operation = parse_operation(allocator_completion.content, task=task)
            allocator_cost = historical_host._completion_cost(allocator_completion)
            physical_cost = physical_cost + allocator_cost

            operation_results: list[OperationResult] = []
            for operation in task.legal_operations():
                if operation == "ZERO":
                    continue
                completion = bound.complete(
                    PlannedProviderCall(task.task_id, "BANK", operation),
                    revision_messages(
                        task,
                        base_answer=base_answer,
                        operation=operation,
                    ),
                )
                answer = parse_answer(completion.content)
                cost = historical_host._completion_cost(
                    completion,
                    operation=operation,
                )
                physical_cost = physical_cost + cost
                operation_results.append(
                    OperationResult(
                        operation=operation,
                        answer=answer,
                        correct=answer == task.expected_answer,
                        extra_cost=cost,
                    )
                )

            bank = TaskOperationBank(
                task_id=task.task_id,
                base_answer=base_answer,
                base_correct=base_answer == task.expected_answer,
                base_cost=base_cost,
                operation_results=tuple(operation_results),
            )
            oracle = a3_oracle(task, bank)
            task_outcomes = {
                "A0": counterfactual_outcome(
                    task,
                    bank,
                    arm_id="A0",
                    operation=a0_policy(task),
                ),
                "A1": counterfactual_outcome(
                    task,
                    bank,
                    arm_id="A1",
                    operation=a1_policy(task),
                ),
                "A2": counterfactual_outcome(
                    task,
                    bank,
                    arm_id="A2",
                    operation=a2_operation,
                    allocator_cost=allocator_cost,
                ),
                "A3": counterfactual_outcome(
                    task,
                    bank,
                    arm_id="A3",
                    operation=oracle.operation,
                ),
            }
            for arm, outcome in task_outcomes.items():
                outcomes_mutable[arm].append(outcome)

            historical_host._append_jsonl(
                root / BANK_EVIDENCE_NAME,
                {
                    "task_id": task.task_id,
                    "hidden_regime": task.hidden_regime,
                    "expected_answer": task.expected_answer,
                    "base_answer": bank.base_answer,
                    "base_correct": bank.base_correct,
                    "base_cost": historical_host._resource_mapping(bank.base_cost),
                    "a2_operation": a2_operation,
                    "a2_allocator_cost": historical_host._resource_mapping(allocator_cost),
                    "operation_results": [
                        {
                            "operation": item.operation,
                            "answer": item.answer,
                            "correct": item.correct,
                            "extra_cost": historical_host._resource_mapping(item.extra_cost),
                        }
                        for item in bank.operation_results
                    ],
                    "a3_operation": oracle.operation,
                    "a3_correct": oracle.correct,
                    "a3_oracle_no_headroom": oracle.oracle_no_headroom,
                    "outcomes": {
                        arm: {
                            "operation": outcome.operation,
                            "answer": outcome.answer,
                            "correct": outcome.correct,
                            "cost": historical_host._resource_mapping(outcome.cost),
                        }
                        for arm, outcome in task_outcomes.items()
                    },
                },
            )

        bound.require_complete()
        outcomes = {arm: tuple(items) for arm, items in outcomes_mutable.items()}
        if any(len(items) != 40 for items in outcomes.values()):
            bound.fail(
                kind="outcome_count_mismatch",
                detail="each replacement arm requires 40 outcomes",
            )
            raise CognitiveWorkR2ReplacementHostError(
                "replacement R2 arm outcome count is incomplete"
            )
        arm_totals = historical_host._arm_totals(outcomes)
        hard_violations = historical_host._validate_treatment_resources(
            preregistration,  # type: ignore[arg-type]
            arm_totals,
        )
        if hard_violations:
            bound.fail(
                kind="resource_envelope_exceeded",
                detail=(
                    f"{hard_violations} replacement structural treatment resource violations"
                ),
            )
            raise CognitiveWorkR2ReplacementHostError(
                "replacement R2 treatment work exceeds frozen structural limits"
            )

        result_mapping = _replacement_result_mapping(
            run_id=run_id,
            identity=identity,
            preregistration=preregistration,
            attempts=bound.attempts,
            completions=bound.completions,
            physical_cost=physical_cost,
            outcomes=outcomes,
            arm_totals=arm_totals,
        )
        historical_host._write_json_exclusive(root / RESULT_NAME, result_mapping)
        historical_host._write_json_atomic(
            root / STATE_NAME,
            {
                "run_id": run_id,
                "status": "COMPLETED",
                "provider_attempts": bound.attempts,
                "provider_completions": bound.completions,
                "plan_cursor": bound.cursor,
                "plan_size": len(plan),
            },
        )
        return R2ReplacementHostResult(
            run_id=run_id,
            identity_fingerprint=identity.fingerprint,
            status="COMPLETED",
            claim_status=CLAIM_STATUS,
            citable=True,
            provider_attempts=bound.attempts,
            provider_completions=bound.completions,
            physical_cost=physical_cost,
            arm_resource_totals=arm_totals,
            category=str(result_mapping["interpretation"]["category"]),  # type: ignore[index]
            outcomes=outcomes,
        )
    except CognitiveWorkR2ReplacementHostError:
        raise
    except R2PreregistrationError as exc:
        bound.fail(kind="protocol_invalid", detail=str(exc))
        raise CognitiveWorkR2ReplacementHostError(
            "replacement R2 strict protocol validation failed"
        ) from exc
    except Exception as exc:
        bound.fail(kind="host_failure", detail=str(exc))
        raise CognitiveWorkR2ReplacementHostError(
            "replacement R2 host failed closed"
        ) from exc
