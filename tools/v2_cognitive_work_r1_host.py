from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess

from relaylm.v2_interventions import ResourceVector
from relaylm.v2_transfer_actual_model import (
    ExperimentClient,
    ExperimentCompletion,
    StructureProposalError,
)
from tools.v2_cognitive_work_r0 import CognitiveWorkCampaign, ExecutionBinding


_ALLOWED_OPERATIONS = ("ZERO", "THINK", "RETRIEVE")
_REQUIRED_CAMPAIGN_OPERATIONS = frozenset({"THINK", "RETRIEVE"})
_CLAIM_STATUS = "NON_CITABLE_R1_SMOKE"
_MANIFEST_NAME = "run-manifest.json"
_STATE_NAME = "run-state.json"
_EVIDENCE_NAME = "request-evidence.jsonl"
_RESULT_NAME = "r1-smoke-result.json"


class CognitiveWorkR1HostError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RepositoryState:
    commit: str
    tree: str
    clean: bool


@dataclass(frozen=True, slots=True)
class R1HostIdentity:
    repository_commit: str
    repository_tree: str
    campaign: CognitiveWorkCampaign
    automatic_retry: bool = False
    semantic_retry: bool = False

    def __post_init__(self) -> None:
        for name in ("repository_commit", "repository_tree"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise CognitiveWorkR1HostError(f"{name} must be non-empty")
        if self.automatic_retry or self.semantic_retry:
            raise CognitiveWorkR1HostError(
                "R1 smoke must disable automatic and semantic retry"
            )
        registry = {operation.name: operation for operation in self.campaign.operations}
        missing = _REQUIRED_CAMPAIGN_OPERATIONS - set(registry)
        if missing:
            raise CognitiveWorkR1HostError(
                "R0 campaign is missing required R1 operations: "
                + ", ".join(sorted(missing))
            )
        privileged = [
            name for name in _REQUIRED_CAMPAIGN_OPERATIONS if registry[name].privileged
        ]
        if privileged:
            raise CognitiveWorkR1HostError(
                "R1 deployable operations must not be privileged: "
                + ", ".join(sorted(privileged))
            )

    @property
    def campaign_fingerprint(self) -> str:
        return self.campaign.fingerprint

    @property
    def execution(self) -> ExecutionBinding:
        return self.campaign.execution

    def to_mapping(self) -> dict[str, object]:
        return {
            "repository": {
                "commit": self.repository_commit,
                "tree": self.repository_tree,
                "clean_required": True,
            },
            "campaign": {
                "fingerprint": self.campaign.fingerprint,
                "start": asdict(self.campaign.start),
                "execution": asdict(self.campaign.execution),
                "task_digest": self.campaign.task_digest,
                "ordinary_information_ids": list(
                    self.campaign.ordinary_information_ids
                ),
                "operations": [
                    {
                        "name": operation.name,
                        "cost": asdict(operation.cost),
                        "privileged": operation.privileged,
                    }
                    for operation in self.campaign.operations
                ],
                "envelope": asdict(self.campaign.envelope),
            },
            "retry_policy": {
                "automatic_retry": self.automatic_retry,
                "semantic_retry": self.semantic_retry,
            },
        }


@dataclass(frozen=True, slots=True)
class SmokeTask:
    task_id: str
    public_prompt: str
    expected_answer: str
    retrieval_packet: str | None = None

    def __post_init__(self) -> None:
        for name in ("task_id", "public_prompt", "expected_answer"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise CognitiveWorkR1HostError(f"task {name} must be non-empty")
        if self.retrieval_packet is not None and not self.retrieval_packet.strip():
            raise CognitiveWorkR1HostError(
                "retrieval_packet must be null or a non-empty string"
            )

    def public_mapping(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "prompt": self.public_prompt,
            "retrieval_available": self.retrieval_packet is not None,
        }


@dataclass(frozen=True, slots=True)
class SmokeSuite:
    tasks: tuple[SmokeTask, ...]

    def __post_init__(self) -> None:
        if len(self.tasks) < 2:
            raise CognitiveWorkR1HostError("R1 smoke requires at least two tasks")
        ids = tuple(task.task_id for task in self.tasks)
        if len(set(ids)) != len(ids):
            raise CognitiveWorkR1HostError("R1 smoke task ids must be unique")
        if not any(task.retrieval_packet is not None for task in self.tasks):
            raise CognitiveWorkR1HostError(
                "R1 smoke needs at least one task with retrieval available"
            )
        if not any(task.retrieval_packet is None for task in self.tasks):
            raise CognitiveWorkR1HostError(
                "R1 smoke needs at least one task where zero-work is available"
            )

    @property
    def digest(self) -> str:
        payload = [
            {
                "task_id": task.task_id,
                "public_prompt": task.public_prompt,
                "expected_answer": task.expected_answer,
                "retrieval_packet": task.retrieval_packet,
            }
            for task in self.tasks
        ]
        return _sha256(["relaylm2-cognitive-work-r1-suite", payload])


@dataclass(frozen=True, slots=True)
class ArmOutcome:
    task_id: str
    arm_id: str
    operation: str
    answer: str
    correct: bool
    cost: ResourceVector


@dataclass(frozen=True, slots=True)
class R1HostResult:
    run_id: str
    identity_fingerprint: str
    status: str
    claim_status: str
    citable: bool
    provider_calls: int
    provider_attempts: int
    provider_completions: int
    classification: str
    outcomes: tuple[ArmOutcome, ...]


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
        raise CognitiveWorkR1HostError("R1 identity/artifact must be canonical JSON") from exc


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
        raise CognitiveWorkR1HostError(
            f"repository git attestation failed: {' '.join(args)}"
        ) from exc
    return completed.stdout.strip()


def probe_repository(repository_root: str | Path) -> RepositoryState:
    commit = _git_output(repository_root, "rev-parse", "--verify", "HEAD")
    tree = _git_output(repository_root, "rev-parse", "HEAD^{tree}")
    status = _git_output(
        repository_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
    )
    return RepositoryState(commit=commit, tree=tree, clean=not bool(status))


def _validate_repository(identity: R1HostIdentity, observed: RepositoryState) -> None:
    if not observed.clean:
        raise CognitiveWorkR1HostError("repository checkout is dirty")
    if observed.commit != identity.repository_commit:
        raise CognitiveWorkR1HostError("repository commit does not match frozen identity")
    if observed.tree != identity.repository_tree:
        raise CognitiveWorkR1HostError("repository tree does not match frozen identity")


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
        raise CognitiveWorkR1HostError(
            "artifact root must resolve outside the repository checkout"
        )
    try:
        root.mkdir(parents=True, exist_ok=True)
        if any(root.iterdir()):
            raise CognitiveWorkR1HostError("fresh R1 artifact root must be empty")
    except OSError as exc:
        raise CognitiveWorkR1HostError(f"cannot prepare R1 artifact root: {exc}") from exc
    return root


def _write_json_exclusive(path: Path, value: dict[str, object]) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(value))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CognitiveWorkR1HostError(f"cannot persist R1 artifact: {exc}") from exc


def _write_json_atomic(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(value))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise CognitiveWorkR1HostError(f"cannot persist R1 state: {exc}") from exc


def _append_jsonl(path: Path, value: dict[str, object]) -> None:
    try:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(value))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CognitiveWorkR1HostError(f"cannot persist R1 evidence: {exc}") from exc


def _cost(completion: ExperimentCompletion) -> ResourceVector:
    return ResourceVector(
        calls=1,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
    )


def _answer_messages(task: SmokeTask) -> tuple[dict[str, str], ...]:
    public = task.public_mapping()
    return (
        {
            "role": "system",
            "content": (
                "Answer the task. Return strict JSON only as "
                '{"answer":"..."}. Do not add other keys or prose.'
            ),
        },
        {"role": "user", "content": _canonical_json(public)},
    )


def _revision_messages(
    task: SmokeTask,
    *,
    base_answer: str,
    retrieval_packet: str | None,
) -> tuple[dict[str, str], ...]:
    packet: dict[str, object] = {
        **task.public_mapping(),
        "previous_answer": base_answer,
    }
    if retrieval_packet is not None:
        packet["retrieved_information"] = retrieval_packet
        instruction = "Use the retrieved information when revising the answer."
    else:
        instruction = "Reconsider the previous answer carefully using the task information."
    return (
        {
            "role": "system",
            "content": (
                instruction
                + " Return strict JSON only as "
                + '{"answer":"..."}. Do not add other keys or prose.'
            ),
        },
        {"role": "user", "content": _canonical_json(packet)},
    )


def _allocator_messages(
    task: SmokeTask,
    *,
    base_answer: str,
) -> tuple[dict[str, str], ...]:
    packet = {
        **task.public_mapping(),
        "current_answer": base_answer,
        "available_operations": {
            "ZERO": "keep the current answer and spend no extra task work",
            "THINK": "buy one more model reasoning/revision call",
            "RETRIEVE": "read the available retrieval packet, then buy one revision call",
        },
    }
    return (
        {
            "role": "system",
            "content": (
                "Choose the single next cognitive operation with the best expected value "
                "for this task. RETRIEVE is legal only when retrieval_available is true. "
                "Return strict JSON only as "
                '{"operation":"ZERO|THINK|RETRIEVE"}. No prose.'
            ),
        },
        {"role": "user", "content": _canonical_json(packet)},
    )


def _strict_json_object(text: str) -> dict[str, object]:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise CognitiveWorkR1HostError(f"duplicate JSON member: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=reject_duplicates)
    except (json.JSONDecodeError, CognitiveWorkR1HostError) as exc:
        raise CognitiveWorkR1HostError("model output is not strict JSON") from exc
    if not isinstance(value, dict):
        raise CognitiveWorkR1HostError("model output must be a JSON object")
    return value


def _parse_answer(completion: ExperimentCompletion) -> str:
    payload = _strict_json_object(completion.content)
    if set(payload) != {"answer"}:
        raise CognitiveWorkR1HostError("answer output must contain exactly answer")
    answer = payload["answer"]
    if not isinstance(answer, str) or not answer.strip():
        raise CognitiveWorkR1HostError("answer must be a non-empty string")
    return answer.strip()


def _parse_operation(
    completion: ExperimentCompletion,
    *,
    retrieval_available: bool,
) -> str:
    payload = _strict_json_object(completion.content)
    if set(payload) != {"operation"}:
        raise CognitiveWorkR1HostError(
            "allocator output must contain exactly operation"
        )
    operation = payload["operation"]
    if operation not in _ALLOWED_OPERATIONS:
        raise CognitiveWorkR1HostError("allocator selected an undeclared operation")
    if operation == "RETRIEVE" and not retrieval_available:
        raise CognitiveWorkR1HostError(
            "allocator selected RETRIEVE when no retrieval packet is available"
        )
    return str(operation)


def _correct(answer: str, expected: str) -> bool:
    return answer.strip() == expected.strip()


class _BoundClient:
    def __init__(
        self,
        *,
        client: ExperimentClient,
        root: Path,
        identity: R1HostIdentity,
        live_binding_probe: Callable[[], ExecutionBinding],
        run_id: str,
        identity_fingerprint: str,
        max_calls: int,
    ) -> None:
        self._client = client
        self._root = root
        self._identity = identity
        self._live_binding_probe = live_binding_probe
        self._run_id = run_id
        self._identity_fingerprint = identity_fingerprint
        self._max_calls = max_calls
        self._attempts = 0
        self._completions = 0
        self._question_ids: set[str] = set()

    @property
    def call_count(self) -> int:
        return self._completions

    @property
    def attempt_count(self) -> int:
        return self._attempts

    def _state(self, *, status: str, failure: dict[str, object] | None = None) -> None:
        payload: dict[str, object] = {
            "format_version": 1,
            "run_id": self._run_id,
            "identity_fingerprint": self._identity_fingerprint,
            "status": status,
            "claim_status": _CLAIM_STATUS,
            "citable": False,
            "provider_calls": self._completions,
            "provider_attempts": self._attempts,
            "provider_completions": self._completions,
        }
        if failure is not None:
            payload["failure"] = failure
        _write_json_atomic(self._root / _STATE_NAME, payload)

    def fail(self, *, question_id: str, kind: str, error: str) -> None:
        failure = {"question_id": question_id, "kind": kind, "error": error}
        _append_jsonl(
            self._root / _EVIDENCE_NAME,
            {
                "run_id": self._run_id,
                "identity_fingerprint": self._identity_fingerprint,
                "question_id": question_id,
                "kind": kind,
                "authority": "instrumentation_only",
                "error": error,
                "provider_attempts": self._attempts,
                "provider_completions": self._completions,
            },
        )
        self._state(status="INCOMPLETE", failure=failure)

    def complete(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
    ) -> ExperimentCompletion:
        if not question_id or question_id in self._question_ids:
            raise CognitiveWorkR1HostError("R1 question ids must be unique and non-empty")
        if self._attempts >= self._max_calls:
            self.fail(
                question_id=question_id,
                kind="undeclared_extra_model_call",
                error="R1 protocol exceeded its frozen maximum provider-call budget",
            )
            raise CognitiveWorkR1HostError("R1 protocol exceeded maximum provider calls")
        self._question_ids.add(question_id)
        try:
            observed = self._live_binding_probe()
            if observed != self._identity.execution:
                raise CognitiveWorkR1HostError("physical binding drift")
        except CognitiveWorkR1HostError as exc:
            self.fail(question_id=question_id, kind="physical_binding_drift", error=str(exc))
            raise
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self.fail(
                question_id=question_id,
                kind="physical_binding_probe_failure",
                error=error,
            )
            raise CognitiveWorkR1HostError(
                f"physical binding probe failure: {error}"
            ) from exc

        self._attempts += 1
        self._state(status="RUNNING")
        try:
            completion = self._client.complete(messages)
        except StructureProposalError as exc:
            self.fail(question_id=question_id, kind="provider_failure", error=str(exc))
            raise CognitiveWorkR1HostError(f"provider failure: {exc}") from exc
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self.fail(question_id=question_id, kind="provider_client_failure", error=error)
            raise CognitiveWorkR1HostError(f"provider client failure: {error}") from exc

        self._completions += 1
        _append_jsonl(
            self._root / _EVIDENCE_NAME,
            {
                "run_id": self._run_id,
                "identity_fingerprint": self._identity_fingerprint,
                "question_id": question_id,
                "order": self._attempts - 1,
                "kind": "model_exchange",
                "authority": "instrumentation_only",
                "messages": messages,
                "response": {
                    "content": completion.content,
                    "input_tokens": completion.input_tokens,
                    "output_tokens": completion.output_tokens,
                    "response_id": completion.response_id,
                },
                "provider_attempts": self._attempts,
                "provider_completions": self._completions,
            },
        )
        self._state(status="RUNNING")
        return completion


def _execute_revision(
    bound: _BoundClient,
    *,
    task: SmokeTask,
    arm_id: str,
    operation: str,
    base_answer: str,
) -> tuple[str, ResourceVector]:
    if operation == "ZERO":
        return base_answer, ResourceVector()
    if operation == "THINK":
        completion = bound.complete(
            f"{task.task_id}:{arm_id}:think",
            _revision_messages(task, base_answer=base_answer, retrieval_packet=None),
        )
        extra_cost = _cost(completion)
    elif operation == "RETRIEVE":
        if task.retrieval_packet is None:
            raise CognitiveWorkR1HostError("RETRIEVE requires an available packet")
        completion = bound.complete(
            f"{task.task_id}:{arm_id}:retrieve",
            _revision_messages(
                task,
                base_answer=base_answer,
                retrieval_packet=task.retrieval_packet,
            ),
        )
        extra_cost = _cost(completion) + ResourceVector(retrieval_units=1)
    else:
        raise CognitiveWorkR1HostError(f"unsupported operation: {operation}")
    try:
        answer = _parse_answer(completion)
    except CognitiveWorkR1HostError as exc:
        bound.fail(
            question_id=f"{task.task_id}:{arm_id}:{operation.lower()}:parse",
            kind="model_protocol_failure",
            error=str(exc),
        )
        raise
    return answer, extra_cost


def _outcome_mapping(outcome: ArmOutcome) -> dict[str, object]:
    return {
        "task_id": outcome.task_id,
        "arm_id": outcome.arm_id,
        "operation": outcome.operation,
        "answer": outcome.answer,
        "correct": outcome.correct,
        "cost": asdict(outcome.cost),
    }


def _classification(outcomes: tuple[ArmOutcome, ...]) -> str:
    correctness = tuple(outcome.correct for outcome in outcomes)
    if all(correctness):
        return "CEILING"
    if not any(correctness):
        return "FLOOR"
    return "MECHANICALLY_DISCRIMINATING"


def _arm_totals(outcomes: tuple[ArmOutcome, ...]) -> dict[str, ResourceVector]:
    totals = {"A0": ResourceVector(), "A1": ResourceVector(), "A2": ResourceVector()}
    for outcome in outcomes:
        totals[outcome.arm_id] = totals[outcome.arm_id] + outcome.cost
    return totals


def run_r1_host_smoke(
    *,
    artifact_root: str | Path,
    identity: R1HostIdentity,
    repository_root: str | Path,
    live_binding_probe: Callable[[], ExecutionBinding],
    client: ExperimentClient,
    suite: SmokeSuite,
) -> R1HostResult:
    """Run one fresh NON_CITABLE #2187 R1 smoke; never choose a scientific winner."""

    if identity.campaign.task_digest != suite.digest:
        raise CognitiveWorkR1HostError(
            "R1 suite does not match the exact R0 campaign task digest"
        )

    observed_repository = probe_repository(repository_root)
    _validate_repository(identity, observed_repository)
    root = _validate_artifact_root(
        artifact_root=artifact_root,
        repository_root=repository_root,
    )

    identity_mapping = identity.to_mapping()
    identity_fingerprint = _sha256(
        ["relaylm2-cognitive-work-r1-identity", identity_mapping, suite.digest]
    )
    run_id = "cw-r1-" + identity_fingerprint.split(":", 1)[1]
    max_calls = 4 * len(suite.tasks) + sum(
        task.retrieval_packet is not None for task in suite.tasks
    )

    _write_json_exclusive(
        root / _MANIFEST_NAME,
        {
            "format_version": 1,
            "kind": "relaylm2_cognitive_work_r1_smoke",
            "run_id": run_id,
            "identity_fingerprint": identity_fingerprint,
            "identity": identity_mapping,
            "suite_digest": suite.digest,
            "claim_status": _CLAIM_STATUS,
            "citable": False,
            "operations": list(_ALLOWED_OPERATIONS),
            "policy_surface": {
                "A0": "fixed THINK",
                "A1": "RETRIEVE when available, otherwise ZERO",
                "A2": "model-allocated ZERO/THINK/RETRIEVE with charged decision call",
            },
            "max_provider_calls": max_calls,
        },
    )
    _write_json_atomic(
        root / _STATE_NAME,
        {
            "format_version": 1,
            "run_id": run_id,
            "identity_fingerprint": identity_fingerprint,
            "status": "RUNNING",
            "claim_status": _CLAIM_STATUS,
            "citable": False,
            "provider_calls": 0,
            "provider_attempts": 0,
            "provider_completions": 0,
        },
    )

    try:
        initial_binding = live_binding_probe()
        if initial_binding != identity.execution:
            raise CognitiveWorkR1HostError("physical binding drift during preflight")
    except CognitiveWorkR1HostError as exc:
        failure = {
            "question_id": "preflight",
            "kind": "physical_binding_drift",
            "error": str(exc),
        }
        _append_jsonl(
            root / _EVIDENCE_NAME,
            {**failure, "authority": "instrumentation_only"},
        )
        _write_json_atomic(
            root / _STATE_NAME,
            {
                "format_version": 1,
                "run_id": run_id,
                "identity_fingerprint": identity_fingerprint,
                "status": "INCOMPLETE",
                "claim_status": _CLAIM_STATUS,
                "citable": False,
                "provider_calls": 0,
                "provider_attempts": 0,
                "provider_completions": 0,
                "failure": failure,
            },
        )
        raise

    bound = _BoundClient(
        client=client,
        root=root,
        identity=identity,
        live_binding_probe=live_binding_probe,
        run_id=run_id,
        identity_fingerprint=identity_fingerprint,
        max_calls=max_calls,
    )
    outcomes: list[ArmOutcome] = []

    for task in suite.tasks:
        base_completion = bound.complete(f"{task.task_id}:base", _answer_messages(task))
        try:
            base_answer = _parse_answer(base_completion)
        except CognitiveWorkR1HostError as exc:
            bound.fail(
                question_id=f"{task.task_id}:base:parse",
                kind="model_protocol_failure",
                error=str(exc),
            )
            raise
        base_cost = _cost(base_completion)

        a0_answer, a0_extra = _execute_revision(
            bound,
            task=task,
            arm_id="A0",
            operation="THINK",
            base_answer=base_answer,
        )
        outcomes.append(
            ArmOutcome(
                task_id=task.task_id,
                arm_id="A0",
                operation="THINK",
                answer=a0_answer,
                correct=_correct(a0_answer, task.expected_answer),
                cost=base_cost + a0_extra,
            )
        )

        a1_operation = "RETRIEVE" if task.retrieval_packet is not None else "ZERO"
        a1_answer, a1_extra = _execute_revision(
            bound,
            task=task,
            arm_id="A1",
            operation=a1_operation,
            base_answer=base_answer,
        )
        outcomes.append(
            ArmOutcome(
                task_id=task.task_id,
                arm_id="A1",
                operation=a1_operation,
                answer=a1_answer,
                correct=_correct(a1_answer, task.expected_answer),
                cost=base_cost + a1_extra,
            )
        )

        allocator_completion = bound.complete(
            f"{task.task_id}:A2:allocate",
            _allocator_messages(task, base_answer=base_answer),
        )
        try:
            a2_operation = _parse_operation(
                allocator_completion,
                retrieval_available=task.retrieval_packet is not None,
            )
        except CognitiveWorkR1HostError as exc:
            bound.fail(
                question_id=f"{task.task_id}:A2:allocate:parse",
                kind="model_protocol_failure",
                error=str(exc),
            )
            raise
        a2_answer, a2_extra = _execute_revision(
            bound,
            task=task,
            arm_id="A2",
            operation=a2_operation,
            base_answer=base_answer,
        )
        outcomes.append(
            ArmOutcome(
                task_id=task.task_id,
                arm_id="A2",
                operation=a2_operation,
                answer=a2_answer,
                correct=_correct(a2_answer, task.expected_answer),
                cost=base_cost + _cost(allocator_completion) + a2_extra,
            )
        )

    frozen_outcomes = tuple(outcomes)
    arm_totals = _arm_totals(frozen_outcomes)
    for arm_id, total in arm_totals.items():
        if not total.fits_within(identity.campaign.envelope):
            error = (
                f"{arm_id} measured work exceeds the frozen R0 campaign envelope: "
                f"total={total.as_tuple()} envelope={identity.campaign.envelope.as_tuple()}"
            )
            bound.fail(
                question_id=f"budget:{arm_id}",
                kind="resource_envelope_exceeded",
                error=error,
            )
            raise CognitiveWorkR1HostError(error)

    classification = _classification(frozen_outcomes)
    result_payload = {
        "format_version": 1,
        "run_id": run_id,
        "identity_fingerprint": identity_fingerprint,
        "status": "COMPLETED",
        "claim_status": _CLAIM_STATUS,
        "citable": False,
        "suite_digest": suite.digest,
        "provider_calls": bound.call_count,
        "provider_attempts": bound.attempt_count,
        "provider_completions": bound.call_count,
        "classification": classification,
        "physical_base_completion_shared_across_arms": True,
        "base_cost_charged_counterfactually_to_each_arm": True,
        "arm_resource_totals": {
            arm_id: asdict(total) for arm_id, total in arm_totals.items()
        },
        "outcomes": [_outcome_mapping(outcome) for outcome in frozen_outcomes],
    }
    _write_json_exclusive(root / _RESULT_NAME, result_payload)
    _write_json_atomic(
        root / _STATE_NAME,
        {
            "format_version": 1,
            "run_id": run_id,
            "identity_fingerprint": identity_fingerprint,
            "status": "COMPLETED",
            "claim_status": _CLAIM_STATUS,
            "citable": False,
            "provider_calls": bound.call_count,
            "provider_attempts": bound.attempt_count,
            "provider_completions": bound.call_count,
        },
    )
    return R1HostResult(
        run_id=run_id,
        identity_fingerprint=identity_fingerprint,
        status="COMPLETED",
        claim_status=_CLAIM_STATUS,
        citable=False,
        provider_calls=bound.call_count,
        provider_attempts=bound.attempt_count,
        provider_completions=bound.call_count,
        classification=classification,
        outcomes=frozen_outcomes,
    )
