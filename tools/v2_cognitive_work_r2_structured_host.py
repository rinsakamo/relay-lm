from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from relaylm.v2_interventions import ResourceVector
from tools.v2_cognitive_work_r0 import ExecutionBinding
from tools import v2_cognitive_work_r2_host as historical_host
from tools import v2_cognitive_work_structured_output_qualification as sopq
from tools.v2_cognitive_work_r2_structured_preregistration import (
    ANSWER_PROTOCOL_VERSION,
    CONTEXT_LIMIT,
    CounterfactualOutcome,
    OperationResult,
    PlannedProviderCall,
    R2PreregistrationError,
    R2StructuredPreregistration,
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
    response_format_for_call,
    revision_messages,
)


FROZEN_STRUCTURED_PREREGISTRATION_COMMIT = (
    "bca9866cab344a9701a859d299af2b18924f6f2e"
)
FROZEN_STRUCTURED_ROOT_SEED = (
    "sha256:f59a601eedf78eb405691b59d86185c43226a749d9bf523bec20464a392bc495"
)
FROZEN_STRUCTURED_PREREGISTRATION_DIGEST = (
    "sha256:53271a481c2270eebe086a159fa7a8fb8905f7d087386bc0c580e504dcedc18b"
)
CLAIM_STATUS = "R2_STRUCTURED_PREREGISTERED_PHYSICAL_RESULT"

MANIFEST_NAME = historical_host.MANIFEST_NAME
STATE_NAME = historical_host.STATE_NAME
REQUEST_EVIDENCE_NAME = historical_host.REQUEST_EVIDENCE_NAME
BANK_EVIDENCE_NAME = historical_host.BANK_EVIDENCE_NAME
RESULT_NAME = historical_host.RESULT_NAME

CognitiveWorkR2StructuredHostError = historical_host.CognitiveWorkR2HostError
RepositoryState = historical_host.RepositoryState


@dataclass(frozen=True, slots=True)
class R2StructuredExecutionAuthorization:
    authorization_id: str
    execution_repository_commit: str
    preregistration_commit: str
    physical_execution_authorized: bool

    def __post_init__(self) -> None:
        if not self.authorization_id.strip():
            raise CognitiveWorkR2StructuredHostError(
                "structured R2 execution authorization id must be non-empty"
            )
        if not self.execution_repository_commit.strip():
            raise CognitiveWorkR2StructuredHostError(
                "structured R2 authorization repository commit must be non-empty"
            )
        if self.preregistration_commit != FROZEN_STRUCTURED_PREREGISTRATION_COMMIT:
            raise CognitiveWorkR2StructuredHostError(
                "structured R2 authorization must bind the frozen preregistration"
            )


@dataclass(frozen=True, slots=True)
class R2StructuredHostIdentity:
    repository_commit: str
    repository_tree: str
    execution: ExecutionBinding
    preregistration_commit: str = FROZEN_STRUCTURED_PREREGISTRATION_COMMIT
    automatic_retry: bool = False
    semantic_retry: bool = False

    def __post_init__(self) -> None:
        if not self.repository_commit.strip() or not self.repository_tree.strip():
            raise CognitiveWorkR2StructuredHostError(
                "structured R2 repository commit/tree must be non-empty"
            )
        if self.preregistration_commit != FROZEN_STRUCTURED_PREREGISTRATION_COMMIT:
            raise CognitiveWorkR2StructuredHostError(
                "structured host must preserve the frozen preregistration commit"
            )
        if self.execution.context_limit != CONTEXT_LIMIT:
            raise CognitiveWorkR2StructuredHostError(
                f"structured execution binding must preserve context_limit={CONTEXT_LIMIT}"
            )
        if self.automatic_retry or self.semantic_retry:
            raise CognitiveWorkR2StructuredHostError(
                "structured R2 host must disable automatic and semantic retry"
            )
        preregistration = build_preregistration(self.preregistration_commit)
        if preregistration.root_seed != FROZEN_STRUCTURED_ROOT_SEED:
            raise CognitiveWorkR2StructuredHostError(
                "frozen structured R2 root seed mismatch"
            )
        if preregistration.digest != FROZEN_STRUCTURED_PREREGISTRATION_DIGEST:
            raise CognitiveWorkR2StructuredHostError(
                "frozen structured R2 preregistration digest mismatch"
            )
        if preregistration.budget.physical_provider_call_max != 136:
            raise CognitiveWorkR2StructuredHostError(
                "frozen structured R2 plan must contain exactly 136 calls"
            )

    @property
    def preregistration(self) -> R2StructuredPreregistration:
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
                "qualified_transport": {
                    "qualification_version": sopq.QUALIFICATION_VERSION,
                    "answer_schema_digest": sopq.ANSWER_SCHEMA_DIGEST,
                    "operation_schema_digest": sopq.OPERATION_SCHEMA_DIGEST,
                    "answer_response_format_digest": sopq.ANSWER_RESPONSE_FORMAT_DIGEST,
                    "operation_response_format_digest": sopq.OPERATION_RESPONSE_FORMAT_DIGEST,
                },
                "automatic_retry": self.automatic_retry,
                "semantic_retry": self.semantic_retry,
            }
        )


@dataclass(frozen=True, slots=True)
class R2StructuredHostResult:
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
    identity: R2StructuredHostIdentity,
    observed: RepositoryState,
) -> None:
    if not observed.clean:
        raise CognitiveWorkR2StructuredHostError("repository checkout is dirty")
    if observed.commit != identity.repository_commit:
        raise CognitiveWorkR2StructuredHostError(
            "repository commit does not match frozen structured identity"
        )
    if observed.tree != identity.repository_tree:
        raise CognitiveWorkR2StructuredHostError(
            "repository tree does not match frozen structured identity"
        )


def _validate_authorization(
    identity: R2StructuredHostIdentity,
    authorization: R2StructuredExecutionAuthorization,
) -> None:
    if not authorization.physical_execution_authorized:
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 physical execution is not authorized"
        )
    if authorization.execution_repository_commit != identity.repository_commit:
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 authorization does not bind the execution commit"
        )
    if authorization.preregistration_commit != identity.preregistration_commit:
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 authorization does not bind the preregistration"
        )


def _transport_mapping(call: PlannedProviderCall) -> dict[str, object]:
    response_format = response_format_for_call(call)
    schema_kind = "operation" if call.role == "A2_ALLOCATE" else "answer"
    response_format_digest = (
        sopq.OPERATION_RESPONSE_FORMAT_DIGEST
        if schema_kind == "operation"
        else sopq.ANSWER_RESPONSE_FORMAT_DIGEST
    )
    schema_digest = (
        sopq.OPERATION_SCHEMA_DIGEST
        if schema_kind == "operation"
        else sopq.ANSWER_SCHEMA_DIGEST
    )
    return {
        "schema_kind": schema_kind,
        "schema_digest": schema_digest,
        "response_format_digest": response_format_digest,
        "response_format": response_format,
    }


class _StructuredBoundPlanClient:
    def __init__(
        self,
        *,
        client: sopq.StructuredOutputClient,
        root: Path,
        identity: R2StructuredHostIdentity,
        live_binding_probe: Callable[[], ExecutionBinding],
        run_id: str,
        plan: tuple[PlannedProviderCall, ...],
    ) -> None:
        self._client = client
        self._root = root
        self._identity = identity
        self._live_binding_probe = live_binding_probe
        self._run_id = run_id
        self._plan = plan
        self._cursor = 0
        self._attempts = 0
        self._completions = 0
        self._question_ids: set[str] = set()

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def completions(self) -> int:
        return self._completions

    @property
    def cursor(self) -> int:
        return self._cursor

    def _state(
        self,
        *,
        status: str,
        failure: Mapping[str, object] | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "run_id": self._run_id,
            "status": status,
            "provider_attempts": self._attempts,
            "provider_completions": self._completions,
            "plan_cursor": self._cursor,
            "plan_size": len(self._plan),
        }
        if failure is not None:
            payload["failure"] = dict(failure)
        historical_host._write_json_atomic(self._root / STATE_NAME, payload)

    def fail(self, *, kind: str, detail: str) -> None:
        self._state(status="INCOMPLETE", failure={"kind": kind, "detail": detail})

    def complete(
        self,
        expected: PlannedProviderCall,
        messages: tuple[dict[str, str], ...],
    ) -> sopq.StructuredOutputCompletion:
        if self._cursor >= len(self._plan):
            self.fail(kind="undeclared_provider_call", detail="plan already exhausted")
            raise CognitiveWorkR2StructuredHostError(
                "undeclared provider call after frozen structured plan"
            )
        actual = self._plan[self._cursor]
        if actual != expected:
            self.fail(
                kind="call_plan_mismatch",
                detail=f"expected {asdict(actual)!r}, requested {asdict(expected)!r}",
            )
            raise CognitiveWorkR2StructuredHostError(
                "provider call does not match frozen structured R2 plan"
            )

        try:
            observed_binding = self._live_binding_probe()
        except Exception as exc:
            self.fail(kind="binding_probe_failure", detail=str(exc))
            raise CognitiveWorkR2StructuredHostError(
                "live physical binding probe failed"
            ) from exc
        if observed_binding != self._identity.execution:
            self.fail(
                kind="binding_drift",
                detail="fresh binding differs from frozen structured execution identity",
            )
            raise CognitiveWorkR2StructuredHostError(
                "physical binding drift before provider attempt"
            )

        transport = _transport_mapping(actual)
        question_id = (
            f"{self._run_id}:{self._cursor:03d}:{actual.task_id}:"
            f"{actual.role}:{actual.operation or '-'}"
        )
        if question_id in self._question_ids:
            self.fail(kind="duplicate_call_identity", detail=question_id)
            raise CognitiveWorkR2StructuredHostError("duplicate provider call identity")
        self._question_ids.add(question_id)
        self._attempts += 1
        historical_host._append_jsonl(
            self._root / REQUEST_EVIDENCE_NAME,
            {
                "question_id": question_id,
                "order": self._cursor,
                "task_id": actual.task_id,
                "role": actual.role,
                "operation": actual.operation,
                "status": "ATTEMPT_REGISTERED",
                "messages": list(messages),
                "transport": transport,
                "binding": asdict(observed_binding),
                "provider_attempts": self._attempts,
                "provider_completions": self._completions,
            },
        )
        self._state(status="RUNNING")

        try:
            completion = self._client.complete(
                messages,
                response_format=transport["response_format"],
            )
        except Exception as exc:
            historical_host._append_jsonl(
                self._root / REQUEST_EVIDENCE_NAME,
                {
                    "question_id": question_id,
                    "order": self._cursor,
                    "task_id": actual.task_id,
                    "role": actual.role,
                    "operation": actual.operation,
                    "status": "PROVIDER_FAILURE",
                    "transport": transport,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "provider_attempts": self._attempts,
                    "provider_completions": self._completions,
                },
            )
            self.fail(kind="provider_failure", detail=str(exc))
            raise CognitiveWorkR2StructuredHostError(
                "provider failure during frozen structured R2 call"
            ) from exc

        self._completions += 1
        historical_host._append_jsonl(
            self._root / REQUEST_EVIDENCE_NAME,
            {
                "question_id": question_id,
                "order": self._cursor,
                "task_id": actual.task_id,
                "role": actual.role,
                "operation": actual.operation,
                "status": "COMPLETED",
                "transport": transport,
                "response_content": completion.content,
                "response_id": completion.response_id,
                "finish_reason": completion.finish_reason,
                "input_tokens": completion.input_tokens,
                "output_tokens": completion.output_tokens,
                "provider_attempts": self._attempts,
                "provider_completions": self._completions,
            },
        )
        self._cursor += 1
        self._state(status="RUNNING")
        return completion

    def require_complete(self) -> None:
        if self._cursor != len(self._plan):
            self.fail(
                kind="incomplete_call_plan",
                detail=f"completed {self._cursor} of {len(self._plan)} declared calls",
            )
            raise CognitiveWorkR2StructuredHostError(
                "structured R2 physical call plan is incomplete"
            )
        if self._attempts != len(self._plan) or self._completions != len(self._plan):
            self.fail(
                kind="counter_mismatch",
                detail="provider counters do not equal the frozen plan size",
            )
            raise CognitiveWorkR2StructuredHostError(
                "structured R2 provider counters are incomplete"
            )


def _structured_result_mapping(
    *,
    run_id: str,
    identity: R2StructuredHostIdentity,
    preregistration: R2StructuredPreregistration,
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
    result["structured_transport"] = {
        "qualification_version": sopq.QUALIFICATION_VERSION,
        "answer_schema_digest": sopq.ANSWER_SCHEMA_DIGEST,
        "operation_schema_digest": sopq.OPERATION_SCHEMA_DIGEST,
        "answer_response_format_digest": sopq.ANSWER_RESPONSE_FORMAT_DIGEST,
        "operation_response_format_digest": sopq.OPERATION_RESPONSE_FORMAT_DIGEST,
    }
    return result


def run_r2_structured_host_campaign(
    *,
    artifact_root: str | Path,
    repository_root: str | Path,
    identity: R2StructuredHostIdentity,
    authorization: R2StructuredExecutionAuthorization,
    live_binding_probe: Callable[[], ExecutionBinding],
    client: sopq.StructuredOutputClient,
    run_id: str,
) -> R2StructuredHostResult:
    """Execute exactly one separately authorized structured-output R2 transaction."""

    if not run_id.strip():
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 run_id must be non-empty"
        )
    _validate_authorization(identity, authorization)
    observed_repository = probe_repository(repository_root)
    _validate_repository(identity, observed_repository)

    preregistration = identity.preregistration
    if preregistration.merged_pr_commit_sha != FROZEN_STRUCTURED_PREREGISTRATION_COMMIT:
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 preregistration commit drift"
        )
    if preregistration.root_seed != FROZEN_STRUCTURED_ROOT_SEED:
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 preregistration root seed drift"
        )
    if preregistration.digest != FROZEN_STRUCTURED_PREREGISTRATION_DIGEST:
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 preregistration digest drift"
        )
    plan = physical_call_plan(preregistration.tasks)
    if len(plan) != preregistration.budget.physical_provider_call_max or len(plan) != 136:
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 physical plan no longer has exactly 136 calls"
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
        "structured_transport": {
            "qualification_version": sopq.QUALIFICATION_VERSION,
            "answer_schema_digest": sopq.ANSWER_SCHEMA_DIGEST,
            "operation_schema_digest": sopq.OPERATION_SCHEMA_DIGEST,
            "answer_response_format_digest": sopq.ANSWER_RESPONSE_FORMAT_DIGEST,
            "operation_response_format_digest": sopq.OPERATION_RESPONSE_FORMAT_DIGEST,
        },
        "budget": asdict(preregistration.budget),
        "retry_policy": {
            "automatic_retry": False,
            "semantic_retry": False,
            "fallback_provider": False,
            "partial_task_replay": False,
            "parser_repair": False,
            "schema_fallback": False,
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
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 preflight binding probe failed"
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
                    "detail": "preflight binding differs from frozen structured identity",
                },
            },
        )
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 preflight physical binding drift"
        )

    bound = _StructuredBoundPlanClient(
        client=client,
        root=root,
        identity=identity,
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
            base_cost = historical_host._completion_cost(base_completion)  # type: ignore[arg-type]
            physical_cost = physical_cost + base_cost

            allocator_completion = bound.complete(
                PlannedProviderCall(task.task_id, "A2_ALLOCATE", None),
                allocator_messages(task, base_answer=base_answer),
            )
            a2_operation = parse_operation(allocator_completion.content, task=task)
            allocator_cost = historical_host._completion_cost(allocator_completion)  # type: ignore[arg-type]
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
                cost = historical_host._completion_cost(  # type: ignore[arg-type]
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
                    "authority": "evaluator_only",
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
                detail="each structured R2 arm requires 40 outcomes",
            )
            raise CognitiveWorkR2StructuredHostError(
                "structured R2 arm outcome count is incomplete"
            )
        arm_totals = historical_host._arm_totals(outcomes)
        hard_violations = historical_host._validate_treatment_resources(
            preregistration,  # type: ignore[arg-type]
            arm_totals,
        )
        if hard_violations:
            bound.fail(
                kind="resource_envelope_exceeded",
                detail=f"{hard_violations} structured treatment resource violations",
            )
            raise CognitiveWorkR2StructuredHostError(
                "structured R2 treatment work exceeds frozen structural limits"
            )

        result_mapping = _structured_result_mapping(
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
        return R2StructuredHostResult(
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
    except CognitiveWorkR2StructuredHostError:
        raise
    except R2PreregistrationError as exc:
        bound.fail(kind="protocol_invalid", detail=str(exc))
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 strict protocol validation failed"
        ) from exc
    except Exception as exc:
        bound.fail(kind="host_failure", detail=str(exc))
        raise CognitiveWorkR2StructuredHostError(
            "structured R2 host failed closed"
        ) from exc
