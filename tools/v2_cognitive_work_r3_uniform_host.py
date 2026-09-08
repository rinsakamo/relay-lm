from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from relaylm.v2_interventions import ResourceVector
from tools.v2_cognitive_work_r0 import ExecutionBinding
from tools import v2_cognitive_work_r2_host as historical_host
from tools import v2_cognitive_work_r2_structured_host as structured_host
from tools import v2_cognitive_work_structured_output_qualification as sopq
from tools import v2_cognitive_work_r3_uniform_preregistration as r3


FROZEN_R3_PREREGISTRATION_COMMIT = "75bba595e66fea695fe4caf50c4c20a71fa4083b"
FROZEN_R3_ROOT_SEED = (
    "sha256:ffb09eb916e990bfc4460641f66f877fea4bb4cd47464cc7673409c6ed663a00"
)
FROZEN_R3_PREREGISTRATION_DIGEST = (
    "sha256:a7f874b62ec6c386ce2274f09c50a1898383c5859f6f0fde8db88f034485eb1d"
)
CLAIM_STATUS = "R3_UNIFORM_PREREGISTERED_PHYSICAL_RESULT"

MANIFEST_NAME = "run-manifest.json"
STATE_NAME = "run-state.json"
REQUEST_EVIDENCE_NAME = "request-evidence.jsonl"
BANK_EVIDENCE_NAME = "r3-bank.jsonl"
RESULT_NAME = "r3-result.json"

CognitiveWorkR3UniformHostError = historical_host.CognitiveWorkR2HostError
RepositoryState = historical_host.RepositoryState


@dataclass(frozen=True, slots=True)
class R3UniformExecutionAuthorization:
    authorization_id: str
    execution_repository_commit: str
    preregistration_commit: str
    physical_execution_authorized: bool

    def __post_init__(self) -> None:
        if not self.authorization_id.strip():
            raise CognitiveWorkR3UniformHostError("R3 execution authorization id must be non-empty")
        if not self.execution_repository_commit.strip():
            raise CognitiveWorkR3UniformHostError(
                "R3 authorization repository commit must be non-empty"
            )
        if self.preregistration_commit != FROZEN_R3_PREREGISTRATION_COMMIT:
            raise CognitiveWorkR3UniformHostError(
                "R3 authorization must bind the frozen uniform preregistration"
            )


@dataclass(frozen=True, slots=True)
class R3UniformHostIdentity:
    repository_commit: str
    repository_tree: str
    execution: ExecutionBinding
    preregistration_commit: str = FROZEN_R3_PREREGISTRATION_COMMIT
    automatic_retry: bool = False
    semantic_retry: bool = False

    def __post_init__(self) -> None:
        if not self.repository_commit.strip() or not self.repository_tree.strip():
            raise CognitiveWorkR3UniformHostError("R3 repository commit/tree must be non-empty")
        if self.preregistration_commit != FROZEN_R3_PREREGISTRATION_COMMIT:
            raise CognitiveWorkR3UniformHostError(
                "R3 host must preserve the frozen preregistration commit"
            )
        if self.execution.context_limit != r3.CONTEXT_LIMIT:
            raise CognitiveWorkR3UniformHostError(
                f"R3 execution binding must preserve context_limit={r3.CONTEXT_LIMIT}"
            )
        if self.automatic_retry or self.semantic_retry:
            raise CognitiveWorkR3UniformHostError(
                "R3 host must disable automatic and semantic retry"
            )
        preregistration = r3.build_preregistration(self.preregistration_commit)
        if preregistration.root_seed != FROZEN_R3_ROOT_SEED:
            raise CognitiveWorkR3UniformHostError("frozen R3 root seed mismatch")
        if preregistration.digest != FROZEN_R3_PREREGISTRATION_DIGEST:
            raise CognitiveWorkR3UniformHostError("frozen R3 preregistration digest mismatch")
        if preregistration.budget.physical_provider_call_max != 64:
            raise CognitiveWorkR3UniformHostError("frozen R3 plan must contain exactly 64 calls")

    @property
    def preregistration(self) -> r3.R3UniformPreregistration:
        return r3.build_preregistration(self.preregistration_commit)

    @property
    def fingerprint(self) -> str:
        preregistration = self.preregistration
        return historical_host._sha256(
            {
                "repository_commit": self.repository_commit,
                "repository_tree": self.repository_tree,
                "execution": asdict(self.execution),
                "preregistration_commit": self.preregistration_commit,
                "preregistration_digest": preregistration.digest,
                "preregistration_root_seed": preregistration.root_seed,
                "preregistration_version": r3.PREREGISTRATION_VERSION,
                "uniform_regime": r3.UNIFORM_REGIME,
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
class R3UniformHostResult:
    run_id: str
    identity_fingerprint: str
    status: str
    claim_status: str
    citable: bool
    provider_attempts: int
    provider_completions: int
    plan_cursor: int
    physical_cost: ResourceVector
    arm_resource_totals: Mapping[str, ResourceVector]
    category: str
    outcomes: Mapping[str, tuple[r3.CounterfactualOutcome, ...]]


def probe_repository(repository_root: str | Path) -> RepositoryState:
    return historical_host.probe_repository(repository_root)


def _validate_repository(identity: R3UniformHostIdentity, observed: RepositoryState) -> None:
    if not observed.clean:
        raise CognitiveWorkR3UniformHostError("repository checkout is dirty")
    if observed.commit != identity.repository_commit:
        raise CognitiveWorkR3UniformHostError("repository commit does not match frozen R3 identity")
    if observed.tree != identity.repository_tree:
        raise CognitiveWorkR3UniformHostError("repository tree does not match frozen R3 identity")


def _validate_authorization(
    identity: R3UniformHostIdentity,
    authorization: R3UniformExecutionAuthorization,
) -> None:
    if not authorization.physical_execution_authorized:
        raise CognitiveWorkR3UniformHostError("R3 physical execution is not authorized")
    if authorization.execution_repository_commit != identity.repository_commit:
        raise CognitiveWorkR3UniformHostError(
            "R3 authorization does not bind the execution repository commit"
        )
    if authorization.preregistration_commit != identity.preregistration_commit:
        raise CognitiveWorkR3UniformHostError(
            "R3 authorization does not bind the frozen preregistration"
        )


def _sum_resources(values: tuple[ResourceVector, ...]) -> ResourceVector:
    total = ResourceVector()
    for value in values:
        total = total + value
    return total


def _arm_totals(
    outcomes: Mapping[str, tuple[r3.CounterfactualOutcome, ...]],
) -> dict[str, ResourceVector]:
    return {
        arm: _sum_resources(tuple(item.cost for item in items))
        for arm, items in outcomes.items()
    }


def _resource_mapping(value: ResourceVector) -> dict[str, int]:
    return asdict(value)


def _task_suite_digest(preregistration: r3.R3UniformPreregistration) -> str:
    return historical_host._sha256(
        [
            {
                "task_id": task.task_id,
                "public_prompt": task.public_prompt,
                "expected_answer": task.expected_answer,
                "retrieval_available": task.retrieval_available,
                "observation_available": task.observation_available,
                "retrieval_packet": task.retrieval_packet,
                "observation_packet": task.observation_packet,
                "hidden_regime": task.hidden_regime,
            }
            for task in preregistration.tasks
        ]
    )


def _plan_digest(plan: tuple[r3.PlannedProviderCall, ...]) -> str:
    return historical_host._sha256([asdict(item) for item in plan])


def _transport_mapping(call: r3.PlannedProviderCall) -> dict[str, object]:
    schema_kind = r3.schema_kind_for_call(call)
    return {
        "schema_kind": schema_kind,
        "schema_digest": (
            sopq.OPERATION_SCHEMA_DIGEST if schema_kind == "operation" else sopq.ANSWER_SCHEMA_DIGEST
        ),
        "response_format_digest": (
            sopq.OPERATION_RESPONSE_FORMAT_DIGEST
            if schema_kind == "operation"
            else sopq.ANSWER_RESPONSE_FORMAT_DIGEST
        ),
        "response_format": r3.response_format_for_call(call),
    }


class _R3BoundPlanClient:
    def __init__(
        self,
        *,
        client: sopq.StructuredOutputClient,
        root: Path,
        identity: R3UniformHostIdentity,
        live_binding_probe: Callable[[], ExecutionBinding],
        run_id: str,
        plan: tuple[r3.PlannedProviderCall, ...],
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
        expected: r3.PlannedProviderCall,
        messages: tuple[dict[str, str], ...],
    ) -> sopq.StructuredOutputCompletion:
        if self._cursor >= len(self._plan):
            self.fail(kind="undeclared_provider_call", detail="plan already exhausted")
            raise CognitiveWorkR3UniformHostError("undeclared provider call after frozen R3 plan")
        actual = self._plan[self._cursor]
        if actual != expected:
            self.fail(
                kind="call_plan_mismatch",
                detail=f"expected {asdict(actual)!r}, requested {asdict(expected)!r}",
            )
            raise CognitiveWorkR3UniformHostError("provider call does not match frozen R3 plan")

        try:
            observed_binding = self._live_binding_probe()
        except Exception as exc:
            self.fail(kind="binding_probe_failure", detail=str(exc))
            raise CognitiveWorkR3UniformHostError("live physical binding probe failed") from exc
        if observed_binding != self._identity.execution:
            self.fail(kind="binding_drift", detail="fresh binding differs from frozen R3 identity")
            raise CognitiveWorkR3UniformHostError("physical binding drift before provider attempt")

        transport = _transport_mapping(actual)
        question_id = (
            f"{self._run_id}:{self._cursor:03d}:{actual.task_id}:"
            f"{actual.role}:{actual.operation or '-'}"
        )
        if question_id in self._question_ids:
            self.fail(kind="duplicate_call_identity", detail=question_id)
            raise CognitiveWorkR3UniformHostError("duplicate provider call identity")
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
            raise CognitiveWorkR3UniformHostError("provider failure during frozen R3 call") from exc

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
            raise CognitiveWorkR3UniformHostError("R3 physical call plan is incomplete")
        if self._attempts != len(self._plan) or self._completions != len(self._plan):
            self.fail(kind="counter_mismatch", detail="provider counters do not equal R3 plan size")
            raise CognitiveWorkR3UniformHostError("R3 provider counters are incomplete")


def _validate_treatment_resources(
    preregistration: r3.R3UniformPreregistration,
    totals: Mapping[str, ResourceVector],
) -> int:
    violations = 0
    for arm in ("A0", "A1", "A2"):
        total = totals[arm]
        if total.calls > preregistration.budget.treatment_call_ceiling_per_arm:
            violations += 1
        if total.retrieval_units > preregistration.budget.retrieval_unit_ceiling_per_arm:
            violations += 1
        if total.observation_units > preregistration.budget.observation_unit_ceiling_per_arm:
            violations += 1
    return violations


def _result_mapping(
    *,
    run_id: str,
    identity: R3UniformHostIdentity,
    preregistration: r3.R3UniformPreregistration,
    bound: _R3BoundPlanClient,
    physical_cost: ResourceVector,
    outcomes: Mapping[str, tuple[r3.CounterfactualOutcome, ...]],
    arm_totals: Mapping[str, ResourceVector],
    hard_violations: int,
    interpretation: r3.R3UniformInterpretation,
) -> dict[str, object]:
    correctness = {
        arm: [item.correct for item in items]
        for arm, items in outcomes.items()
    }
    a2_a1_bootstrap = r3.paired_bootstrap_interval(
        correctness["A2"],
        correctness["A1"],
        seed=preregistration.root_seed + ":R3:A2-A1",
    )
    return {
        "run_id": run_id,
        "status": "COMPLETED",
        "claim_status": CLAIM_STATUS,
        "citable": True,
        "identity_fingerprint": identity.fingerprint,
        "provider_attempts": bound.attempts,
        "provider_completions": bound.completions,
        "plan_cursor": bound.cursor,
        "preregistration": {
            "commit": preregistration.merged_pr_commit_sha,
            "root_seed": preregistration.root_seed,
            "digest": preregistration.digest,
            "version": r3.PREREGISTRATION_VERSION,
            "uniform_regime": r3.UNIFORM_REGIME,
            "suite_digest": _task_suite_digest(preregistration),
            "call_plan_digest": _plan_digest(r3.physical_call_plan(preregistration.tasks)),
        },
        "structured_transport": {
            "qualification_version": sopq.QUALIFICATION_VERSION,
            "answer_schema_digest": sopq.ANSWER_SCHEMA_DIGEST,
            "operation_schema_digest": sopq.OPERATION_SCHEMA_DIGEST,
            "answer_response_format_digest": sopq.ANSWER_RESPONSE_FORMAT_DIGEST,
            "operation_response_format_digest": sopq.OPERATION_RESPONSE_FORMAT_DIGEST,
        },
        "physical_resource": _resource_mapping(physical_cost),
        "arm_resources": {
            arm: _resource_mapping(total) for arm, total in arm_totals.items()
        },
        "correctness": {
            arm: {
                "count": sum(values),
                "vector": values,
            }
            for arm, values in correctness.items()
        },
        "interpretation": {
            "category": interpretation.category,
            "counts": dict(interpretation.counts),
            "oracle_headroom_over_fixed": interpretation.oracle_headroom_over_fixed,
            "heuristic_oracle_gap": interpretation.heuristic_oracle_gap,
            "adaptive_minus_heuristic": interpretation.adaptive_minus_heuristic,
            "a2_vs_a1_pvalue": interpretation.a2_vs_a1_pvalue,
            "a2_vs_a1_bootstrap_95": list(a2_a1_bootstrap),
        },
        "hard_resource_violations": hard_violations,
        "protocol_invalid_count": 0,
        "production_scheduler_authority": "NONE",
        "architecture_consequence": "NONE",
    }


def run_r3_uniform_host_campaign(
    *,
    artifact_root: str | Path,
    repository_root: str | Path,
    identity: R3UniformHostIdentity,
    authorization: R3UniformExecutionAuthorization,
    live_binding_probe: Callable[[], ExecutionBinding],
    client: sopq.StructuredOutputClient,
    run_id: str,
) -> R3UniformHostResult:
    if not run_id.strip():
        raise CognitiveWorkR3UniformHostError("R3 run id must be non-empty")
    _validate_repository(identity, probe_repository(repository_root))
    _validate_authorization(identity, authorization)
    preregistration = identity.preregistration
    plan = r3.physical_call_plan(preregistration.tasks)
    if len(plan) != 64:
        raise CognitiveWorkR3UniformHostError("R3 frozen plan is not exactly 64 calls")

    try:
        preflight_binding = live_binding_probe()
    except Exception as exc:
        raise CognitiveWorkR3UniformHostError("R3 preflight binding probe failed") from exc
    if preflight_binding != identity.execution:
        raise CognitiveWorkR3UniformHostError("R3 preflight physical binding mismatch")

    root = historical_host._validate_artifact_root(
        artifact_root=artifact_root,
        repository_root=repository_root,
    )
    manifest = {
        "run_id": run_id,
        "claim_status": CLAIM_STATUS,
        "execution_authorization": asdict(authorization),
        "execution_repository": {
            "commit": identity.repository_commit,
            "tree": identity.repository_tree,
            "clean": True,
        },
        "execution_binding": asdict(identity.execution),
        "identity_fingerprint": identity.fingerprint,
        "preregistration": {
            "commit": preregistration.merged_pr_commit_sha,
            "root_seed": preregistration.root_seed,
            "digest": preregistration.digest,
            "version": r3.PREREGISTRATION_VERSION,
            "uniform_regime": r3.UNIFORM_REGIME,
            "task_ids": [task.task_id for task in preregistration.tasks],
            "suite_digest": _task_suite_digest(preregistration),
            "call_plan_digest": _plan_digest(plan),
            "call_plan_size": len(plan),
        },
        "budget": asdict(preregistration.budget),
        "structured_transport": {
            "qualification_version": sopq.QUALIFICATION_VERSION,
            "answer_schema_digest": sopq.ANSWER_SCHEMA_DIGEST,
            "operation_schema_digest": sopq.OPERATION_SCHEMA_DIGEST,
            "answer_response_format_digest": sopq.ANSWER_RESPONSE_FORMAT_DIGEST,
            "operation_response_format_digest": sopq.OPERATION_RESPONSE_FORMAT_DIGEST,
            "answer_calls": 48,
            "operation_calls": 16,
        },
        "retry_policy": {"automatic_retry": False, "semantic_retry": False},
        "production_scheduler_authority": "NONE",
        "architecture_consequence": "NONE",
    }
    historical_host._write_json_exclusive(root / MANIFEST_NAME, manifest)
    historical_host._write_json_atomic(
        root / STATE_NAME,
        {
            "run_id": run_id,
            "status": "READY",
            "provider_attempts": 0,
            "provider_completions": 0,
            "plan_cursor": 0,
            "plan_size": len(plan),
        },
    )

    bound = _R3BoundPlanClient(
        client=client,
        root=root,
        identity=identity,
        live_binding_probe=live_binding_probe,
        run_id=run_id,
        plan=plan,
    )
    physical_cost = ResourceVector()
    outcomes_mutable: dict[str, list[r3.CounterfactualOutcome]] = {
        "A0": [],
        "A1": [],
        "A2": [],
        "A3": [],
    }

    try:
        for task in preregistration.tasks:
            base_completion = bound.complete(
                r3.PlannedProviderCall(task.task_id, "BASE", None),
                r3.answer_messages(task),
            )
            base_answer = r3.parse_answer(base_completion.content)
            base_cost = historical_host._completion_cost(base_completion)  # type: ignore[arg-type]
            physical_cost = physical_cost + base_cost

            allocator_completion = bound.complete(
                r3.PlannedProviderCall(task.task_id, "A2_ALLOCATE", None),
                r3.allocator_messages(task, base_answer=base_answer),
            )
            a2_operation = r3.parse_operation(allocator_completion.content, task=task)
            allocator_cost = historical_host._completion_cost(allocator_completion)  # type: ignore[arg-type]
            physical_cost = physical_cost + allocator_cost

            operation_results: list[r3.OperationResult] = []
            for operation in task.legal_operations():
                if operation == "ZERO":
                    continue
                completion = bound.complete(
                    r3.PlannedProviderCall(task.task_id, "BANK", operation),
                    r3.revision_messages(
                        task,
                        base_answer=base_answer,
                        operation=operation,
                    ),
                )
                answer = r3.parse_answer(completion.content)
                cost = historical_host._completion_cost(  # type: ignore[arg-type]
                    completion,
                    operation=operation,
                )
                physical_cost = physical_cost + cost
                operation_results.append(
                    r3.OperationResult(
                        operation=operation,
                        answer=answer,
                        correct=answer == task.expected_answer,
                        extra_cost=cost,
                    )
                )

            bank = r3.TaskOperationBank(
                task_id=task.task_id,
                base_answer=base_answer,
                base_correct=base_answer == task.expected_answer,
                base_cost=base_cost,
                operation_results=tuple(operation_results),
            )
            oracle = r3.a3_oracle(task, bank)
            task_outcomes = {
                "A0": r3.counterfactual_outcome(
                    task,
                    bank,
                    arm_id="A0",
                    operation=r3.a0_policy(task),
                ),
                "A1": r3.counterfactual_outcome(
                    task,
                    bank,
                    arm_id="A1",
                    operation=r3.a1_policy(task),
                ),
                "A2": r3.counterfactual_outcome(
                    task,
                    bank,
                    arm_id="A2",
                    operation=a2_operation,
                    allocator_cost=allocator_cost,
                ),
                "A3": r3.counterfactual_outcome(
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
                    "base_cost": _resource_mapping(bank.base_cost),
                    "operation_results": [
                        {
                            "operation": item.operation,
                            "answer": item.answer,
                            "correct": item.correct,
                            "extra_cost": _resource_mapping(item.extra_cost),
                        }
                        for item in bank.operation_results
                    ],
                    "a0_operation": r3.a0_policy(task),
                    "a1_operation": r3.a1_policy(task),
                    "a2_operation": a2_operation,
                    "a3_operation": oracle.operation,
                },
            )

        bound.require_complete()
    except r3.R3PreregistrationError as exc:
        bound.fail(kind="protocol_invalid", detail=str(exc))
        raise CognitiveWorkR3UniformHostError(
            "R3 structured model output violated the frozen strict protocol"
        ) from exc

    outcomes = {arm: tuple(items) for arm, items in outcomes_mutable.items()}
    if any(len(items) != r3.TASK_COUNT for items in outcomes.values()):
        bound.fail(kind="outcome_count_mismatch", detail="R3 arm outcome count is incomplete")
        raise CognitiveWorkR3UniformHostError("R3 arm outcome count is incomplete")

    arm_totals = _arm_totals(outcomes)
    hard_violations = _validate_treatment_resources(preregistration, arm_totals)
    correctness = {
        arm: tuple(item.correct for item in items)
        for arm, items in outcomes.items()
    }
    interpretation = r3.interpret_r3_uniform(
        correctness,
        resource_accounting_complete=True,
        hard_constraint_violations=hard_violations,
        protocol_invalid_count=0,
    )
    result_mapping = _result_mapping(
        run_id=run_id,
        identity=identity,
        preregistration=preregistration,
        bound=bound,
        physical_cost=physical_cost,
        outcomes=outcomes,
        arm_totals=arm_totals,
        hard_violations=hard_violations,
        interpretation=interpretation,
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

    return R3UniformHostResult(
        run_id=run_id,
        identity_fingerprint=identity.fingerprint,
        status="COMPLETED",
        claim_status=CLAIM_STATUS,
        citable=True,
        provider_attempts=bound.attempts,
        provider_completions=bound.completions,
        plan_cursor=bound.cursor,
        physical_cost=physical_cost,
        arm_resource_totals=arm_totals,
        category=interpretation.category,
        outcomes=outcomes,
    )
