from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Mapping

from relaylm.v2_interventions import ResourceVector
from relaylm.v2_transfer_actual_model import ExperimentClient, ExperimentCompletion
from tools.v2_cognitive_work_r0 import ExecutionBinding
from tools.v2_cognitive_work_r2_preregistration import (
    BOOTSTRAP_RESAMPLES,
    CONTEXT_LIMIT,
    CounterfactualOutcome,
    OperationResult,
    PlannedProviderCall,
    R2Preregistration,
    R2PreregistrationError,
    TaskOperationBank,
    a0_policy,
    a1_policy,
    a3_oracle,
    allocator_messages,
    answer_messages,
    build_preregistration,
    counterfactual_outcome,
    interpret_r2,
    paired_bootstrap_interval,
    parse_answer,
    parse_operation,
    physical_call_plan,
    revision_messages,
)


FROZEN_PREREGISTRATION_COMMIT = "f8540c959856938331d5db58ae3a2b9825ad5f9b"
FROZEN_ROOT_SEED = (
    "sha256:c7a2b3953b03d51228346ef57937c23b16329b6b659bc7201c00b853f2322e85"
)
CLAIM_STATUS = "R2_PREREGISTERED_PHYSICAL_RESULT"
MANIFEST_NAME = "run-manifest.json"
STATE_NAME = "run-state.json"
REQUEST_EVIDENCE_NAME = "request-evidence.jsonl"
BANK_EVIDENCE_NAME = "r2-bank.jsonl"
RESULT_NAME = "r2-result.json"


class CognitiveWorkR2HostError(RuntimeError):
    """The preregistered R2 host cannot preserve its execution contract."""


@dataclass(frozen=True, slots=True)
class RepositoryState:
    commit: str
    tree: str
    clean: bool


@dataclass(frozen=True, slots=True)
class R2ExecutionAuthorization:
    """A separately supplied execution gate; this package does not create one."""

    authorization_id: str
    execution_repository_commit: str
    preregistration_commit: str
    physical_execution_authorized: bool

    def __post_init__(self) -> None:
        if not self.authorization_id.strip():
            raise CognitiveWorkR2HostError("execution authorization id must be non-empty")
        if not self.execution_repository_commit.strip():
            raise CognitiveWorkR2HostError(
                "execution authorization repository commit must be non-empty"
            )
        if self.preregistration_commit != FROZEN_PREREGISTRATION_COMMIT:
            raise CognitiveWorkR2HostError(
                "execution authorization must bind the frozen R2 preregistration commit"
            )


@dataclass(frozen=True, slots=True)
class R2HostIdentity:
    repository_commit: str
    repository_tree: str
    execution: ExecutionBinding
    preregistration_commit: str = FROZEN_PREREGISTRATION_COMMIT
    automatic_retry: bool = False
    semantic_retry: bool = False

    def __post_init__(self) -> None:
        if not self.repository_commit.strip() or not self.repository_tree.strip():
            raise CognitiveWorkR2HostError("repository commit/tree must be non-empty")
        if self.preregistration_commit != FROZEN_PREREGISTRATION_COMMIT:
            raise CognitiveWorkR2HostError(
                "R2 host identity must preserve the frozen preregistration commit"
            )
        if self.execution.context_limit != CONTEXT_LIMIT:
            raise CognitiveWorkR2HostError(
                f"R2 execution binding must preserve context_limit={CONTEXT_LIMIT}"
            )
        if self.automatic_retry or self.semantic_retry:
            raise CognitiveWorkR2HostError(
                "R2 host must disable automatic and semantic retry"
            )
        preregistration = build_preregistration(self.preregistration_commit)
        if preregistration.root_seed != FROZEN_ROOT_SEED:
            raise CognitiveWorkR2HostError("frozen R2 root seed mismatch")
        if preregistration.budget.physical_provider_call_max != 136:
            raise CognitiveWorkR2HostError("frozen R2 plan must contain exactly 136 calls")

    @property
    def preregistration(self) -> R2Preregistration:
        return build_preregistration(self.preregistration_commit)

    @property
    def fingerprint(self) -> str:
        return _sha256(
            {
                "repository_commit": self.repository_commit,
                "repository_tree": self.repository_tree,
                "execution": asdict(self.execution),
                "preregistration_commit": self.preregistration_commit,
                "preregistration_digest": self.preregistration.digest,
                "automatic_retry": self.automatic_retry,
                "semantic_retry": self.semantic_retry,
            }
        )


@dataclass(frozen=True, slots=True)
class R2HostResult:
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


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CognitiveWorkR2HostError("R2 host value is not canonical JSON") from exc


def _sha256(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _git_output(repository_root: str | Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CognitiveWorkR2HostError(
            f"repository git attestation failed: {' '.join(args)}"
        ) from exc
    return completed.stdout.strip()


def probe_repository(repository_root: str | Path) -> RepositoryState:
    return RepositoryState(
        commit=_git_output(repository_root, "rev-parse", "--verify", "HEAD"),
        tree=_git_output(repository_root, "rev-parse", "HEAD^{tree}"),
        clean=not bool(
            _git_output(
                repository_root,
                "status",
                "--porcelain=v1",
                "--untracked-files=normal",
            )
        ),
    )


def _validate_repository(identity: R2HostIdentity, observed: RepositoryState) -> None:
    if not observed.clean:
        raise CognitiveWorkR2HostError("repository checkout is dirty")
    if observed.commit != identity.repository_commit:
        raise CognitiveWorkR2HostError("repository commit does not match frozen identity")
    if observed.tree != identity.repository_tree:
        raise CognitiveWorkR2HostError("repository tree does not match frozen identity")


def _validate_authorization(
    identity: R2HostIdentity,
    authorization: R2ExecutionAuthorization,
) -> None:
    if not authorization.physical_execution_authorized:
        raise CognitiveWorkR2HostError("R2 physical execution is not authorized")
    if authorization.execution_repository_commit != identity.repository_commit:
        raise CognitiveWorkR2HostError(
            "execution authorization does not bind the current execution commit"
        )
    if authorization.preregistration_commit != identity.preregistration_commit:
        raise CognitiveWorkR2HostError(
            "execution authorization does not bind the frozen preregistration"
        )


def _validate_artifact_root(
    *,
    artifact_root: str | Path,
    repository_root: str | Path,
) -> Path:
    repository = Path(repository_root).resolve()
    root = Path(artifact_root).resolve()
    try:
        root.relative_to(repository)
    except ValueError:
        pass
    else:
        raise CognitiveWorkR2HostError(
            "artifact root must resolve outside the repository checkout"
        )
    try:
        root.mkdir(parents=True, exist_ok=True)
        if any(root.iterdir()):
            raise CognitiveWorkR2HostError("fresh R2 artifact root must be empty")
    except OSError as exc:
        raise CognitiveWorkR2HostError(f"cannot prepare R2 artifact root: {exc}") from exc
    return root


def _write_json_exclusive(path: Path, value: Mapping[str, object]) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(dict(value)))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CognitiveWorkR2HostError(f"cannot persist R2 artifact: {exc}") from exc


def _write_json_atomic(path: Path, value: Mapping[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(dict(value)))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise CognitiveWorkR2HostError(f"cannot persist R2 state: {exc}") from exc


def _append_jsonl(path: Path, value: Mapping[str, object]) -> None:
    try:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(dict(value)))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CognitiveWorkR2HostError(f"cannot persist R2 evidence: {exc}") from exc


def _resource_mapping(value: ResourceVector) -> dict[str, int]:
    return asdict(value)


def _completion_cost(
    completion: ExperimentCompletion,
    *,
    operation: str | None = None,
) -> ResourceVector:
    return ResourceVector(
        calls=1,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
        retrieval_units=1 if operation == "RETRIEVE" else 0,
        observation_units=1 if operation == "OBSERVE" else 0,
    )


def _task_suite_digest(preregistration: R2Preregistration) -> str:
    return _sha256(
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


def _plan_digest(plan: tuple[PlannedProviderCall, ...]) -> str:
    return _sha256([asdict(item) for item in plan])


def _same_binding(left: ExecutionBinding, right: ExecutionBinding) -> bool:
    return left == right


class _BoundPlanClient:
    def __init__(
        self,
        *,
        client: ExperimentClient,
        root: Path,
        identity: R2HostIdentity,
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
        _write_json_atomic(self._root / STATE_NAME, payload)

    def fail(self, *, kind: str, detail: str) -> None:
        self._state(status="INCOMPLETE", failure={"kind": kind, "detail": detail})

    def complete(
        self,
        expected: PlannedProviderCall,
        messages: tuple[dict[str, str], ...],
    ) -> ExperimentCompletion:
        if self._cursor >= len(self._plan):
            self.fail(kind="undeclared_provider_call", detail="plan already exhausted")
            raise CognitiveWorkR2HostError("undeclared provider call after frozen plan")
        actual = self._plan[self._cursor]
        if actual != expected:
            self.fail(
                kind="call_plan_mismatch",
                detail=f"expected {asdict(actual)!r}, requested {asdict(expected)!r}",
            )
            raise CognitiveWorkR2HostError("provider call does not match frozen R2 plan")

        try:
            observed_binding = self._live_binding_probe()
        except Exception as exc:
            self.fail(kind="binding_probe_failure", detail=str(exc))
            raise CognitiveWorkR2HostError("live physical binding probe failed") from exc
        if not _same_binding(observed_binding, self._identity.execution):
            self.fail(
                kind="binding_drift",
                detail="fresh binding differs from frozen execution identity",
            )
            raise CognitiveWorkR2HostError("physical binding drift before provider attempt")

        question_id = (
            f"{self._run_id}:{self._cursor:03d}:{actual.task_id}:"
            f"{actual.role}:{actual.operation or '-'}"
        )
        if question_id in self._question_ids:
            self.fail(kind="duplicate_call_identity", detail=question_id)
            raise CognitiveWorkR2HostError("duplicate provider call identity")
        self._question_ids.add(question_id)
        self._attempts += 1
        _append_jsonl(
            self._root / REQUEST_EVIDENCE_NAME,
            {
                "question_id": question_id,
                "order": self._cursor,
                "task_id": actual.task_id,
                "role": actual.role,
                "operation": actual.operation,
                "status": "ATTEMPT_REGISTERED",
                "messages": list(messages),
                "binding": asdict(observed_binding),
                "provider_attempts": self._attempts,
                "provider_completions": self._completions,
            },
        )
        self._state(status="RUNNING")

        try:
            completion = self._client.complete(messages)
        except Exception as exc:
            _append_jsonl(
                self._root / REQUEST_EVIDENCE_NAME,
                {
                    "question_id": question_id,
                    "order": self._cursor,
                    "task_id": actual.task_id,
                    "role": actual.role,
                    "operation": actual.operation,
                    "status": "PROVIDER_FAILURE",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "provider_attempts": self._attempts,
                    "provider_completions": self._completions,
                },
            )
            self.fail(kind="provider_failure", detail=str(exc))
            raise CognitiveWorkR2HostError("provider failure during frozen R2 call") from exc

        self._completions += 1
        _append_jsonl(
            self._root / REQUEST_EVIDENCE_NAME,
            {
                "question_id": question_id,
                "order": self._cursor,
                "task_id": actual.task_id,
                "role": actual.role,
                "operation": actual.operation,
                "status": "COMPLETED",
                "response_content": completion.content,
                "response_id": completion.response_id,
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
            raise CognitiveWorkR2HostError("R2 physical call plan is incomplete")
        if self._attempts != len(self._plan) or self._completions != len(self._plan):
            self.fail(
                kind="counter_mismatch",
                detail="provider counters do not equal the frozen plan size",
            )
            raise CognitiveWorkR2HostError("R2 provider counters are incomplete")


def _sum_resources(values: tuple[ResourceVector, ...]) -> ResourceVector:
    total = ResourceVector()
    for value in values:
        total = total + value
    return total


def _arm_totals(
    outcomes: Mapping[str, tuple[CounterfactualOutcome, ...]],
) -> dict[str, ResourceVector]:
    return {
        arm: _sum_resources(tuple(item.cost for item in arm_outcomes))
        for arm, arm_outcomes in outcomes.items()
    }


def _per_regime_counts(
    preregistration: R2Preregistration,
    outcomes: Mapping[str, tuple[CounterfactualOutcome, ...]],
) -> dict[str, dict[str, int]]:
    task_regimes = {task.task_id: task.hidden_regime for task in preregistration.tasks}
    result: dict[str, dict[str, int]] = {}
    for arm, arm_outcomes in outcomes.items():
        counts = {regime: 0 for regime in {task.hidden_regime for task in preregistration.tasks}}
        for item in arm_outcomes:
            if item.correct:
                counts[task_regimes[item.task_id]] += 1
        result[arm] = dict(sorted(counts.items()))
    return result


def _selection_confusion(
    a2: tuple[CounterfactualOutcome, ...],
    a3: tuple[CounterfactualOutcome, ...],
) -> dict[str, int]:
    result: dict[str, int] = {}
    for adaptive, oracle in zip(a2, a3, strict=True):
        key = f"{adaptive.operation}->{oracle.operation}"
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def _validate_treatment_resources(
    preregistration: R2Preregistration,
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
    identity: R2HostIdentity,
    preregistration: R2Preregistration,
    attempts: int,
    completions: int,
    physical_cost: ResourceVector,
    outcomes: Mapping[str, tuple[CounterfactualOutcome, ...]],
    arm_totals: Mapping[str, ResourceVector],
) -> dict[str, object]:
    correctness = {
        arm: tuple(item.correct for item in arm_outcomes)
        for arm, arm_outcomes in outcomes.items()
    }
    hard_violations = _validate_treatment_resources(preregistration, arm_totals)
    interpretation = interpret_r2(
        correctness,
        resource_accounting_complete=True,
        hard_constraint_violations=hard_violations,
        protocol_invalid_count=0,
    )
    a2_a0_bootstrap = paired_bootstrap_interval(
        correctness["A2"],
        correctness["A0"],
        seed=preregistration.root_seed + ":A2-A0",
    )
    a2_a1_bootstrap = paired_bootstrap_interval(
        correctness["A2"],
        correctness["A1"],
        seed=preregistration.root_seed + ":A2-A1",
    )
    task_by_id = {task.task_id: task for task in preregistration.tasks}
    wasted = sum(
        item.operation != "ZERO"
        and task_by_id[item.task_id].hidden_regime
        in {"EASY_SATURATED", "UNCERTAINTY_TRAP"}
        for item in outcomes["A2"]
    )
    missed = sum(
        item.operation == "ZERO"
        and task_by_id[item.task_id].hidden_regime
        in {"DEPTH_BENEFICIAL", "RETRIEVAL_BENEFICIAL", "OBSERVATION_BENEFICIAL"}
        for item in outcomes["A2"]
    )
    return {
        "run_id": run_id,
        "status": "COMPLETED",
        "claim_status": CLAIM_STATUS,
        "citable": True,
        "identity_fingerprint": identity.fingerprint,
        "preregistration_commit": preregistration.merged_pr_commit_sha,
        "preregistration_root_seed": preregistration.root_seed,
        "preregistration_digest": preregistration.digest,
        "provider_attempts": attempts,
        "provider_completions": completions,
        "physical_cost": _resource_mapping(physical_cost),
        "arm_resource_totals": {
            arm: _resource_mapping(total) for arm, total in arm_totals.items()
        },
        "correctness": {arm: list(values) for arm, values in correctness.items()},
        "per_regime_correct": _per_regime_counts(preregistration, outcomes),
        "interpretation": {
            "category": interpretation.category,
            "counts": dict(interpretation.counts),
            "a2_minus_a0": interpretation.a2_minus_a0,
            "a2_minus_a1": interpretation.a2_minus_a1,
            "oracle_headroom_over_fixed": interpretation.oracle_headroom_over_fixed,
            "a2_vs_a0_pvalue": interpretation.a2_vs_a0_pvalue,
            "a2_vs_a1_pvalue": interpretation.a2_vs_a1_pvalue,
        },
        "bootstrap": {
            "resamples": BOOTSTRAP_RESAMPLES,
            "a2_minus_a0_95": list(a2_a0_bootstrap),
            "a2_minus_a1_95": list(a2_a1_bootstrap),
        },
        "a2_selection_confusion_vs_a3": _selection_confusion(
            outcomes["A2"], outcomes["A3"]
        ),
        "a2_wasted_work_count": wasted,
        "a2_missed_useful_work_count": missed,
        "hard_constraint_violations": hard_violations,
        "protocol_invalid_count": 0,
        "architecture_consequence": "NONE",
        "production_scheduler_authority": "NONE",
    }


def run_r2_host_campaign(
    *,
    artifact_root: str | Path,
    repository_root: str | Path,
    identity: R2HostIdentity,
    authorization: R2ExecutionAuthorization,
    live_binding_probe: Callable[[], ExecutionBinding],
    client: ExperimentClient,
    run_id: str,
) -> R2HostResult:
    """Execute exactly one separately authorized preregistered R2 transaction."""

    if not run_id.strip():
        raise CognitiveWorkR2HostError("R2 run_id must be non-empty")
    _validate_authorization(identity, authorization)
    observed_repository = probe_repository(repository_root)
    _validate_repository(identity, observed_repository)

    preregistration = identity.preregistration
    if preregistration.merged_pr_commit_sha != FROZEN_PREREGISTRATION_COMMIT:
        raise CognitiveWorkR2HostError("R2 preregistration commit drift")
    if preregistration.root_seed != FROZEN_ROOT_SEED:
        raise CognitiveWorkR2HostError("R2 preregistration root seed drift")
    plan = physical_call_plan(preregistration.tasks)
    if len(plan) != preregistration.budget.physical_provider_call_max or len(plan) != 136:
        raise CognitiveWorkR2HostError("R2 physical plan no longer has exactly 136 calls")

    root = _validate_artifact_root(
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
            "clean_required": True,
        },
        "execution_binding": asdict(identity.execution),
        "identity_fingerprint": identity.fingerprint,
        "preregistration": {
            "commit": preregistration.merged_pr_commit_sha,
            "root_seed": preregistration.root_seed,
            "digest": preregistration.digest,
            "suite_digest": _task_suite_digest(preregistration),
            "task_ids": [task.task_id for task in preregistration.tasks],
            "call_plan_digest": _plan_digest(plan),
            "call_plan_size": len(plan),
        },
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
    _write_json_exclusive(root / MANIFEST_NAME, manifest)
    _write_json_exclusive(
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
        _write_json_atomic(
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
        raise CognitiveWorkR2HostError("R2 preflight binding probe failed") from exc
    if not _same_binding(preflight, identity.execution):
        _write_json_atomic(
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
                    "detail": "preflight binding differs from frozen identity",
                },
            },
        )
        raise CognitiveWorkR2HostError("R2 preflight physical binding drift")

    bound = _BoundPlanClient(
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
            base_cost = _completion_cost(base_completion)
            physical_cost = physical_cost + base_cost

            allocator_completion = bound.complete(
                PlannedProviderCall(task.task_id, "A2_ALLOCATE", None),
                allocator_messages(task, base_answer=base_answer),
            )
            a2_operation = parse_operation(allocator_completion.content, task=task)
            allocator_cost = _completion_cost(allocator_completion)
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
                cost = _completion_cost(completion, operation=operation)
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

            _append_jsonl(
                root / BANK_EVIDENCE_NAME,
                {
                    "task_id": task.task_id,
                    "hidden_regime": task.hidden_regime,
                    "expected_answer": task.expected_answer,
                    "base_answer": bank.base_answer,
                    "base_correct": bank.base_correct,
                    "base_cost": _resource_mapping(bank.base_cost),
                    "a2_operation": a2_operation,
                    "a2_allocator_cost": _resource_mapping(allocator_cost),
                    "operation_results": [
                        {
                            "operation": item.operation,
                            "answer": item.answer,
                            "correct": item.correct,
                            "extra_cost": _resource_mapping(item.extra_cost),
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
                            "cost": _resource_mapping(outcome.cost),
                        }
                        for arm, outcome in task_outcomes.items()
                    },
                },
            )

        bound.require_complete()
        outcomes = {
            arm: tuple(items) for arm, items in outcomes_mutable.items()
        }
        if any(len(items) != 40 for items in outcomes.values()):
            bound.fail(kind="outcome_count_mismatch", detail="each arm requires 40 outcomes")
            raise CognitiveWorkR2HostError("R2 arm outcome count is incomplete")
        arm_totals = _arm_totals(outcomes)
        hard_violations = _validate_treatment_resources(preregistration, arm_totals)
        if hard_violations:
            bound.fail(
                kind="resource_envelope_exceeded",
                detail=f"{hard_violations} structural treatment resource violations",
            )
            raise CognitiveWorkR2HostError("R2 treatment work exceeds frozen structural limits")

        result_mapping = _result_mapping(
            run_id=run_id,
            identity=identity,
            preregistration=preregistration,
            attempts=bound.attempts,
            completions=bound.completions,
            physical_cost=physical_cost,
            outcomes=outcomes,
            arm_totals=arm_totals,
        )
        _write_json_exclusive(root / RESULT_NAME, result_mapping)
        _write_json_atomic(
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
        return R2HostResult(
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
    except CognitiveWorkR2HostError:
        raise
    except R2PreregistrationError as exc:
        bound.fail(kind="protocol_invalid", detail=str(exc))
        raise CognitiveWorkR2HostError("R2 strict protocol validation failed") from exc
    except Exception as exc:
        bound.fail(kind="host_failure", detail=str(exc))
        raise CognitiveWorkR2HostError("R2 host failed closed") from exc
