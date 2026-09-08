from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from relaylm.v2_interventions import ResourceVector
from tools.v2_cognitive_work_r0 import ExecutionBinding
from tools import v2_cognitive_work_r2_host as historical_host
from tools import v2_cognitive_work_structured_output_qualification as sopq
from tools import v2_cognitive_work_r4_shift_preregistration as r4


FROZEN_R4_PREREGISTRATION_COMMIT = "af00c6686e6412c0bcfcb09567a609e978f81fe5"
FROZEN_R4_ROOT_SEED = (
    "sha256:234f8cf3232d686b2881d1162e6afa814f30bdcf7007453111c5d7b181e6af2c"
)
FROZEN_R4_PREREGISTRATION_DIGEST = (
    "sha256:6a0cf44f2cfb003eb065d6a5c53977ee144ed9fa695ae0298062c20f9e6655be"
)
CLAIM_STATUS = "R4_SHIFT_PREREGISTERED_PHYSICAL_RESULT"

MANIFEST_NAME = "run-manifest.json"
STATE_NAME = "run-state.json"
REQUEST_EVIDENCE_NAME = "request-evidence.jsonl"
BANK_EVIDENCE_NAME = "r4-bank.jsonl"
RESULT_NAME = "r4-result.json"

CognitiveWorkR4ShiftHostError = historical_host.CognitiveWorkR2HostError
RepositoryState = historical_host.RepositoryState


@dataclass(frozen=True, slots=True)
class R4ShiftExecutionAuthorization:
    authorization_id: str
    execution_repository_commit: str
    preregistration_commit: str
    physical_execution_authorized: bool

    def __post_init__(self) -> None:
        if not self.authorization_id.strip():
            raise CognitiveWorkR4ShiftHostError("R4 execution authorization id must be non-empty")
        if not self.execution_repository_commit.strip():
            raise CognitiveWorkR4ShiftHostError(
                "R4 authorization repository commit must be non-empty"
            )
        if self.preregistration_commit != FROZEN_R4_PREREGISTRATION_COMMIT:
            raise CognitiveWorkR4ShiftHostError(
                "R4 authorization must bind the frozen shift preregistration"
            )


@dataclass(frozen=True, slots=True)
class R4ShiftHostIdentity:
    repository_commit: str
    repository_tree: str
    execution: ExecutionBinding
    preregistration_commit: str = FROZEN_R4_PREREGISTRATION_COMMIT
    automatic_retry: bool = False
    semantic_retry: bool = False

    def __post_init__(self) -> None:
        if not self.repository_commit.strip() or not self.repository_tree.strip():
            raise CognitiveWorkR4ShiftHostError("R4 repository commit/tree must be non-empty")
        if self.preregistration_commit != FROZEN_R4_PREREGISTRATION_COMMIT:
            raise CognitiveWorkR4ShiftHostError(
                "R4 host must preserve the frozen preregistration commit"
            )
        if self.execution.context_limit != r4.CONTEXT_LIMIT:
            raise CognitiveWorkR4ShiftHostError(
                f"R4 execution binding must preserve context_limit={r4.CONTEXT_LIMIT}"
            )
        if self.automatic_retry or self.semantic_retry:
            raise CognitiveWorkR4ShiftHostError(
                "R4 host must disable automatic and semantic retry"
            )
        preregistration = r4.build_preregistration(self.preregistration_commit)
        if preregistration.root_seed != FROZEN_R4_ROOT_SEED:
            raise CognitiveWorkR4ShiftHostError("frozen R4 root seed mismatch")
        if preregistration.digest != FROZEN_R4_PREREGISTRATION_DIGEST:
            raise CognitiveWorkR4ShiftHostError("frozen R4 preregistration digest mismatch")
        if preregistration.budget.physical_provider_call_max != 100:
            raise CognitiveWorkR4ShiftHostError("frozen R4 plan must contain exactly 100 calls")

    @property
    def preregistration(self) -> r4.R4ShiftPreregistration:
        return r4.build_preregistration(self.preregistration_commit)

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
                "preregistration_version": r4.PREREGISTRATION_VERSION,
                "shift": "availability-cue-value-decorrelation",
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
class R4ShiftHostResult:
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
    outcomes: Mapping[str, tuple[r4.CounterfactualOutcome, ...]]


def probe_repository(repository_root: str | Path) -> RepositoryState:
    return historical_host.probe_repository(repository_root)


def _validate_repository(identity: R4ShiftHostIdentity, observed: RepositoryState) -> None:
    if not observed.clean:
        raise CognitiveWorkR4ShiftHostError("repository checkout is dirty")
    if observed.commit != identity.repository_commit:
        raise CognitiveWorkR4ShiftHostError("repository commit does not match frozen R4 identity")
    if observed.tree != identity.repository_tree:
        raise CognitiveWorkR4ShiftHostError("repository tree does not match frozen R4 identity")


def _validate_authorization(
    identity: R4ShiftHostIdentity,
    authorization: R4ShiftExecutionAuthorization,
) -> None:
    if not authorization.physical_execution_authorized:
        raise CognitiveWorkR4ShiftHostError("R4 physical execution is not authorized")
    if authorization.execution_repository_commit != identity.repository_commit:
        raise CognitiveWorkR4ShiftHostError(
            "R4 authorization does not bind the execution repository commit"
        )
    if authorization.preregistration_commit != identity.preregistration_commit:
        raise CognitiveWorkR4ShiftHostError(
            "R4 authorization does not bind the frozen preregistration"
        )


def _sum_resources(values: tuple[ResourceVector, ...]) -> ResourceVector:
    total = ResourceVector()
    for value in values:
        total = total + value
    return total


def _arm_totals(
    outcomes: Mapping[str, tuple[r4.CounterfactualOutcome, ...]],
) -> dict[str, ResourceVector]:
    return {
        arm: _sum_resources(tuple(item.cost for item in items))
        for arm, items in outcomes.items()
    }


def _resource_mapping(value: ResourceVector) -> dict[str, int]:
    return asdict(value)


def _task_suite_digest(preregistration: r4.R4ShiftPreregistration) -> str:
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


def _plan_digest(plan: tuple[r4.PlannedProviderCall, ...]) -> str:
    return historical_host._sha256([asdict(item) for item in plan])


def _transport_mapping(call: r4.PlannedProviderCall) -> dict[str, object]:
    schema_kind = r4.schema_kind_for_call(call)
    return {
        "schema_kind": schema_kind,
        "schema_digest": (
            sopq.OPERATION_SCHEMA_DIGEST
            if schema_kind == "operation"
            else sopq.ANSWER_SCHEMA_DIGEST
        ),
        "response_format_digest": (
            sopq.OPERATION_RESPONSE_FORMAT_DIGEST
            if schema_kind == "operation"
            else sopq.ANSWER_RESPONSE_FORMAT_DIGEST
        ),
        "response_format": r4.response_format_for_call(call),
    }


class _R4BoundPlanClient:
    def __init__(
        self,
        *,
        client: sopq.StructuredOutputClient,
        root: Path,
        identity: R4ShiftHostIdentity,
        live_binding_probe: Callable[[], ExecutionBinding],
        run_id: str,
        plan: tuple[r4.PlannedProviderCall, ...],
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
        expected: r4.PlannedProviderCall,
        messages: tuple[dict[str, str], ...],
    ) -> sopq.StructuredOutputCompletion:
        if self._cursor >= len(self._plan):
            self.fail(kind="undeclared_provider_call", detail="plan already exhausted")
            raise CognitiveWorkR4ShiftHostError("undeclared provider call after frozen R4 plan")
        actual = self._plan[self._cursor]
        if actual != expected:
            self.fail(
                kind="call_plan_mismatch",
                detail=f"expected {asdict(actual)!r}, requested {asdict(expected)!r}",
            )
            raise CognitiveWorkR4ShiftHostError("provider call does not match frozen R4 plan")

        try:
            observed_binding = self._live_binding_probe()
        except Exception as exc:
            self.fail(kind="binding_probe_failure", detail=str(exc))
            raise CognitiveWorkR4ShiftHostError("live physical binding probe failed") from exc
        if observed_binding != self._identity.execution:
            self.fail(kind="binding_drift", detail="fresh binding differs from frozen R4 identity")
            raise CognitiveWorkR4ShiftHostError("physical binding drift before provider attempt")

        transport = _transport_mapping(actual)
        question_id = (
            f"{self._run_id}:{self._cursor:03d}:{actual.task_id}:"
            f"{actual.role}:{actual.operation or '-'}"
        )
        if question_id in self._question_ids:
            self.fail(kind="duplicate_call_identity", detail=question_id)
            raise CognitiveWorkR4ShiftHostError("duplicate provider call identity")
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
            raise CognitiveWorkR4ShiftHostError("provider failure during frozen R4 call") from exc

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
            raise CognitiveWorkR4ShiftHostError("R4 physical call plan is incomplete")
        if self._attempts != len(self._plan) or self._completions != len(self._plan):
            self.fail(kind="counter_mismatch", detail="provider counters do not equal R4 plan size")
            raise CognitiveWorkR4ShiftHostError("R4 provider counters are incomplete")


def _validate_treatment_resources(
    preregistration: r4.R4ShiftPreregistration,
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


def _per_regime_correctness(
    preregistration: r4.R4ShiftPreregistration,
    outcomes: Mapping[str, tuple[r4.CounterfactualOutcome, ...]],
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for regime in r4.REGIMES:
        indexes = [
            index
            for index, task in enumerate(preregistration.tasks)
            if task.hidden_regime == regime
        ]
        result[regime] = {
            arm: sum(outcomes[arm][index].correct for index in indexes)
            for arm in ("A0", "A1", "A2", "A3")
        }
    return result


def _result_mapping(
    *,
    run_id: str,
    identity: R4ShiftHostIdentity,
    preregistration: r4.R4ShiftPreregistration,
    bound: _R4BoundPlanClient,
    physical_cost: ResourceVector,
    outcomes: Mapping[str, tuple[r4.CounterfactualOutcome, ...]],
    arm_totals: Mapping[str, ResourceVector],
    hard_violations: int,
    interpretation: r4.R4ShiftInterpretation,
    a2_operations: tuple[str, ...],
    a3_operations: tuple[str, ...],
) -> dict[str, object]:
    correctness = {
        arm: [item.correct for item in items]
        for arm, items in outcomes.items()
    }
    a2_a1_bootstrap = r4.paired_bootstrap_interval(
        correctness["A2"],
        correctness["A1"],
        seed=preregistration.root_seed + ":R4:A2-A1",
    )
    confusion = Counter(
        f"{a2}->{a3}" for a2, a3 in zip(a2_operations, a3_operations, strict=True)
    )
    a2_selection_counts = Counter(a2_operations)
    a3_selection_counts = Counter(a3_operations)
    wasted_work = sum(
        a2 != "ZERO" and a3 == "ZERO"
        for a2, a3 in zip(a2_operations, a3_operations, strict=True)
    )
    missed_useful_work = sum(
        a2 == "ZERO" and a3 != "ZERO"
        for a2, a3 in zip(a2_operations, a3_operations, strict=True)
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
            "version": r4.PREREGISTRATION_VERSION,
            "suite_digest": _task_suite_digest(preregistration),
            "call_plan_digest": _plan_digest(r4.physical_call_plan(preregistration.tasks)),
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
            arm: {"count": sum(values), "vector": values}
            for arm, values in correctness.items()
        },
        "per_regime_correctness": _per_regime_correctness(preregistration, outcomes),
        "interpretation": {
            "category": interpretation.category,
            "counts": dict(interpretation.counts),
            "oracle_headroom_over_fixed": interpretation.oracle_headroom_over_fixed,
            "shift_headroom_over_heuristic": interpretation.shift_headroom_over_heuristic,
            "adaptive_minus_heuristic": interpretation.adaptive_minus_heuristic,
            "adaptive_minus_fixed": interpretation.adaptive_minus_fixed,
            "a2_vs_a1_pvalue": interpretation.a2_vs_a1_pvalue,
            "a2_vs_a1_bootstrap_95": list(a2_a1_bootstrap),
        },
        "operation_diagnostics": {
            "a1_selection_counts": {"RETRIEVE": r4.TASK_COUNT},
            "a2_selection_counts": dict(sorted(a2_selection_counts.items())),
            "a3_selection_counts": dict(sorted(a3_selection_counts.items())),
            "a2_vs_a3_confusion": dict(sorted(confusion.items())),
            "a1_regret_vs_a3": interpretation.counts["A3"] - interpretation.counts["A1"],
            "a2_regret_vs_a3": interpretation.counts["A3"] - interpretation.counts["A2"],
            "wasted_work": wasted_work,
            "missed_useful_work": missed_useful_work,
        },
        "hard_resource_violations": hard_violations,
        "protocol_invalid_count": 0,
        "production_scheduler_authority": "NONE",
        "architecture_consequence": "NONE",
    }


def run_r4_shift_host_campaign(
    *,
    artifact_root: str | Path,
    repository_root: str | Path,
    identity: R4ShiftHostIdentity,
    authorization: R4ShiftExecutionAuthorization,
    live_binding_probe: Callable[[], ExecutionBinding],
    client: sopq.StructuredOutputClient,
    run_id: str,
) -> R4ShiftHostResult:
    if not run_id.strip():
        raise CognitiveWorkR4ShiftHostError("R4 run id must be non-empty")
    _validate_repository(identity, probe_repository(repository_root))
    _validate_authorization(identity, authorization)
    preregistration = identity.preregistration
    plan = r4.physical_call_plan(preregistration.tasks)
    if len(plan) != 100:
        raise CognitiveWorkR4ShiftHostError("R4 frozen plan is not exactly 100 calls")

    try:
        preflight_binding = live_binding_probe()
    except Exception as exc:
        raise CognitiveWorkR4ShiftHostError("R4 preflight binding probe failed") from exc
    if preflight_binding != identity.execution:
        raise CognitiveWorkR4ShiftHostError("R4 preflight physical binding mismatch")

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
            "version": r4.PREREGISTRATION_VERSION,
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
            "answer_calls": 80,
            "operation_calls": 20,
        },
        "retry_policy": {
            "automatic_retry": False,
            "semantic_retry": False,
            "fallback_provider": False,
            "partial_task_replay": False,
            "parser_repair": False,
            "schema_fallback": False,
        },
        "model_facing_evaluator_fields": False,
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

    bound = _R4BoundPlanClient(
        client=client,
        root=root,
        identity=identity,
        live_binding_probe=live_binding_probe,
        run_id=run_id,
        plan=plan,
    )
    physical_cost = ResourceVector()
    outcomes_mutable: dict[str, list[r4.CounterfactualOutcome]] = {
        "A0": [],
        "A1": [],
        "A2": [],
        "A3": [],
    }
    a2_operations: list[str] = []
    a3_operations: list[str] = []

    try:
        for task in preregistration.tasks:
            base_completion = bound.complete(
                r4.PlannedProviderCall(task.task_id, "BASE", None),
                r4.answer_messages(task),
            )
            base_answer = r4.parse_answer(base_completion.content)
            base_cost = historical_host._completion_cost(base_completion)  # type: ignore[arg-type]
            physical_cost = physical_cost + base_cost

            allocator_completion = bound.complete(
                r4.PlannedProviderCall(task.task_id, "A2_ALLOCATE", None),
                r4.allocator_messages(task, base_answer=base_answer),
            )
            a2_operation = r4.parse_operation(allocator_completion.content, task=task)
            allocator_cost = historical_host._completion_cost(allocator_completion)  # type: ignore[arg-type]
            physical_cost = physical_cost + allocator_cost

            operation_results: list[r4.OperationResult] = []
            for operation in task.legal_operations():
                if operation == "ZERO":
                    continue
                completion = bound.complete(
                    r4.PlannedProviderCall(task.task_id, "BANK", operation),
                    r4.revision_messages(
                        task,
                        base_answer=base_answer,
                        operation=operation,
                    ),
                )
                answer = r4.parse_answer(completion.content)
                cost = historical_host._completion_cost(  # type: ignore[arg-type]
                    completion,
                    operation=operation,
                )
                physical_cost = physical_cost + cost
                operation_results.append(
                    r4.OperationResult(
                        operation=operation,
                        answer=answer,
                        correct=answer == task.expected_answer,
                        extra_cost=cost,
                    )
                )

            bank = r4.TaskOperationBank(
                task_id=task.task_id,
                base_answer=base_answer,
                base_correct=base_answer == task.expected_answer,
                base_cost=base_cost,
                operation_results=tuple(operation_results),
            )
            oracle = r4.a3_oracle(task, bank)
            a2_operations.append(a2_operation)
            a3_operations.append(oracle.operation)
            task_outcomes = {
                "A0": r4.counterfactual_outcome(
                    task, bank, arm_id="A0", operation=r4.a0_policy(task)
                ),
                "A1": r4.counterfactual_outcome(
                    task, bank, arm_id="A1", operation=r4.a1_policy(task)
                ),
                "A2": r4.counterfactual_outcome(
                    task,
                    bank,
                    arm_id="A2",
                    operation=a2_operation,
                    allocator_cost=allocator_cost,
                ),
                "A3": r4.counterfactual_outcome(
                    task, bank, arm_id="A3", operation=oracle.operation
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
                    "a0_operation": r4.a0_policy(task),
                    "a1_operation": r4.a1_policy(task),
                    "a2_operation": a2_operation,
                    "a2_allocator_cost": _resource_mapping(allocator_cost),
                    "a3_operation": oracle.operation,
                    "a3_correct": oracle.correct,
                    "a3_oracle_no_headroom": oracle.oracle_no_headroom,
                    "outcomes": {
                        arm: {
                            "operation": outcome.operation,
                            "answer": outcome.answer,
                            "correct": outcome.correct,
                            "cost": _resource_mapping(outcome.cost),
                        }
                        for arm, outcome in task_outcomes.items()
                    },
                },
            )

        bound.require_complete()
    except r4.R4PreregistrationError as exc:
        bound.fail(kind="protocol_invalid", detail=str(exc))
        raise CognitiveWorkR4ShiftHostError(
            "R4 structured model output violated the frozen strict protocol"
        ) from exc

    outcomes = {arm: tuple(items) for arm, items in outcomes_mutable.items()}
    if any(len(items) != r4.TASK_COUNT for items in outcomes.values()):
        bound.fail(kind="outcome_count_mismatch", detail="R4 arm outcome count is incomplete")
        raise CognitiveWorkR4ShiftHostError("R4 arm outcome count is incomplete")
    if len(a2_operations) != r4.TASK_COUNT or len(a3_operations) != r4.TASK_COUNT:
        bound.fail(kind="operation_count_mismatch", detail="R4 operation diagnostics incomplete")
        raise CognitiveWorkR4ShiftHostError("R4 operation diagnostics are incomplete")

    arm_totals = _arm_totals(outcomes)
    hard_violations = _validate_treatment_resources(preregistration, arm_totals)
    correctness = {
        arm: tuple(item.correct for item in items)
        for arm, items in outcomes.items()
    }
    interpretation = r4.interpret_r4_shift(
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
        a2_operations=tuple(a2_operations),
        a3_operations=tuple(a3_operations),
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

    return R4ShiftHostResult(
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
