from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess

from relaylm.v2_transfer_actual_model import (
    ExperimentClient,
    ExperimentCompletion,
    StructureProposalError,
    prepare_r1_arms,
    run_source_learning,
    run_target_probe,
)
from relaylm.v2_transfer_experiment import TransferFamily
from tools.external_qualification import (
    DurableQuestion,
    DurableQuestionRun,
    ExternalQualificationError,
    FrozenExperimentIdentity,
    freeze_experiment_identity,
)


_EXECUTION_ORDER = ("source-learning", "t0", "t1", "t2")
_MATERIAL_BINDING_FIELDS = (
    "model",
    "artifact",
    "tokenizer",
    "template",
    "backend",
    "runtime",
    "decoding",
    "reasoning",
    "structured_output",
    "context_capacity",
    "hardware",
    "launch_admission",
)
_CLAIM_STATUS = "NON_CITABLE_R1_SMOKE"


class R1HostError(ValueError):
    """The bounded R1 physical-host contract is not satisfied."""


@dataclass(frozen=True, slots=True)
class RepositoryState:
    commit: str
    tree: str
    clean: bool

    def __post_init__(self) -> None:
        for name in ("commit", "tree"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise R1HostError(f"repository {name} must be non-empty")
        if not isinstance(self.clean, bool):
            raise R1HostError("repository clean must be a boolean")


@dataclass(frozen=True, slots=True)
class R1HostResult:
    run_id: str
    identity_fingerprint: str
    status: str
    claim_status: str
    citable: bool
    source_structure_id: str
    arm_correctness: tuple[bool, bool, bool]


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
        raise R1HostError("R1 host identity/binding must be canonical JSON") from exc


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise R1HostError(f"{label} must be an object")
    return value


def _git_output(repository_root: str | Path, *args: str) -> str:
    root = Path(repository_root)
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise R1HostError(f"repository git attestation failed: {' '.join(args)}") from exc
    return completed.stdout.strip()


def probe_git_repository(repository_root: str | Path) -> RepositoryState:
    """Observe current commit/tree/cleanliness directly from the supplied checkout."""

    commit = _git_output(repository_root, "rev-parse", "--verify", "HEAD")
    tree = _git_output(repository_root, "rev-parse", "HEAD^{tree}")
    status = _git_output(
        repository_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
    )
    return RepositoryState(commit=commit, tree=tree, clean=not bool(status))


def _validate_static_contract(identity: Mapping[str, object]) -> None:
    execution_order = identity.get("execution_order")
    if execution_order != list(_EXECUTION_ORDER):
        raise R1HostError(
            "execution order must be source-learning -> t0 -> t1 -> t2"
        )
    retry_policy = _mapping(identity.get("retry_policy"), "retry policy")
    if retry_policy != {"automatic_retry": False, "semantic_retry": False}:
        raise R1HostError(
            "retry policy must disable automatic retry and semantic retry"
        )


def _validate_repository(
    identity: Mapping[str, object],
    observed: RepositoryState,
) -> None:
    expected = _mapping(identity.get("repository"), "repository identity")
    if set(expected) != {"commit", "tree", "clean_required"}:
        raise R1HostError(
            "repository identity must contain exactly commit/tree/clean_required"
        )
    if expected.get("clean_required") is not True:
        raise R1HostError("repository identity must require a clean checkout")
    if not observed.clean:
        raise R1HostError("repository checkout is dirty")
    if observed.commit != expected.get("commit"):
        raise R1HostError("repository commit does not match frozen identity")
    if observed.tree != expected.get("tree"):
        raise R1HostError("repository tree does not match frozen identity")


def _expected_binding(identity: Mapping[str, object]) -> dict[str, object]:
    missing = [name for name in _MATERIAL_BINDING_FIELDS if name not in identity]
    if missing:
        raise R1HostError(
            "physical binding is missing frozen fields: " + ", ".join(missing)
        )
    return {name: identity[name] for name in _MATERIAL_BINDING_FIELDS}


def _validate_live_binding(
    expected: Mapping[str, object],
    observed: Mapping[str, object],
) -> None:
    if set(observed) != set(_MATERIAL_BINDING_FIELDS):
        raise R1HostError("physical binding drift: live binding field set changed")
    for name in _MATERIAL_BINDING_FIELDS:
        if _canonical_json(observed[name]) != _canonical_json(expected[name]):
            raise R1HostError(f"physical binding drift: {name} changed")


def _questions(
    family: TransferFamily,
    *,
    step_index: int,
    examples_visible: int,
) -> tuple[DurableQuestion, ...]:
    source_content = {
        "phase": "source-learning",
        "modulus": family.modulus,
        "examples": [
            {
                "input": list(example.input_values),
                "output": list(example.output_values),
            }
            for example in family.source_examples
        ],
    }
    target_common = {
        "public_target_digest": family.public_target_digest,
        "evidence_schedule_digest": family.evidence_schedule_digest,
        "step_index": step_index,
        "examples_visible": examples_visible,
    }
    return (
        DurableQuestion.from_content("source-learning", source_content, session_id="r1"),
        DurableQuestion.from_content(
            "t0",
            {"phase": "target", "arm": "t0", **target_common},
            session_id="r1",
        ),
        DurableQuestion.from_content(
            "t1",
            {"phase": "target", "arm": "t1", **target_common},
            session_id="r1",
        ),
        DurableQuestion.from_content(
            "t2",
            {"phase": "target", "arm": "t2", **target_common},
            session_id="r1",
        ),
    )


class _BoundExperimentClient:
    def __init__(
        self,
        *,
        client: ExperimentClient,
        durable_run: DurableQuestionRun,
        live_binding_probe: Callable[[], Mapping[str, object]],
        expected_binding: Mapping[str, object],
    ) -> None:
        self._client = client
        self._durable_run = durable_run
        self._live_binding_probe = live_binding_probe
        self._expected_binding = dict(expected_binding)
        self._question_id: str | None = None

    def bind_question(self, question_id: str) -> None:
        self._question_id = question_id

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        if self._question_id is None:
            raise R1HostError("model call attempted without a durable R1 question")
        try:
            observed = self._live_binding_probe()
            if not isinstance(observed, Mapping):
                raise R1HostError("physical binding drift: live probe did not return an object")
            _validate_live_binding(self._expected_binding, observed)
        except R1HostError as exc:
            self._durable_run.append_request_evidence(
                question_id=self._question_id,
                evidence={
                    "kind": "physical_binding_drift",
                    "authority": "instrumentation_only",
                    "error": str(exc),
                },
            )
            self._durable_run.mark_stopped()
            raise

        try:
            completion = self._client.complete(messages)
        except StructureProposalError as exc:
            self._durable_run.append_request_evidence(
                question_id=self._question_id,
                evidence={
                    "kind": "provider_failure",
                    "authority": "instrumentation_only",
                    "error": str(exc),
                },
            )
            self._durable_run.mark_stopped()
            raise R1HostError(f"provider failure: {exc}") from exc

        self._durable_run.append_request_evidence(
            question_id=self._question_id,
            evidence={
                "kind": "model_exchange",
                "authority": "instrumentation_only",
                "messages": messages,
                "response": {
                    "content": completion.content,
                    "input_tokens": completion.input_tokens,
                    "output_tokens": completion.output_tokens,
                    "response_id": completion.response_id,
                },
            },
        )
        return completion


def _stop_after_semantic_failure(
    durable_run: DurableQuestionRun,
    *,
    question_id: str,
    phase: str,
    exc: StructureProposalError,
) -> R1HostError:
    durable_run.append_request_evidence(
        question_id=question_id,
        evidence={
            "kind": "model_protocol_failure",
            "authority": "instrumentation_only",
            "phase": phase,
            "error": str(exc),
        },
    )
    durable_run.mark_stopped()
    return R1HostError(f"{phase} model protocol failure: {exc}")


def run_r1_host_smoke(
    *,
    artifact_root: str | Path,
    identity: Mapping[str, object],
    repository_root: str | Path,
    live_binding_probe: Callable[[], Mapping[str, object]],
    client: ExperimentClient,
    family: TransferFamily,
    step_index: int,
    examples_visible: int,
) -> R1HostResult:
    """Execute one fresh, non-citable R1 smoke under a frozen physical identity.

    The runner owns repository observation directly through Git.  Physical
    model/runtime facts still come from a live host probe because there is no
    provider-independent way to discover those facts.  Any drift or provider/
    protocol failure stops the run; there is deliberately no automatic or
    semantic retry path.
    """

    if not isinstance(identity, Mapping):
        raise R1HostError("frozen experiment identity must be an object")
    _validate_static_contract(identity)

    observed_repository = probe_git_repository(repository_root)
    _validate_repository(identity, observed_repository)

    expected_binding = _expected_binding(identity)
    initial_live_binding = live_binding_probe()
    if not isinstance(initial_live_binding, Mapping):
        raise R1HostError("physical binding drift: live probe did not return an object")
    _validate_live_binding(expected_binding, initial_live_binding)

    try:
        frozen_identity: FrozenExperimentIdentity = freeze_experiment_identity(
            identity=identity,
            live_attestation=_mapping(
                initial_live_binding["launch_admission"],
                "live launch admission",
            ),
        )
    except ExternalQualificationError as exc:
        raise R1HostError(f"physical frozen identity is invalid: {exc}") from exc

    questions = _questions(
        family,
        step_index=step_index,
        examples_visible=examples_visible,
    )
    try:
        durable_run = DurableQuestionRun.start(
            artifact_root=artifact_root,
            identity=frozen_identity,
            questions=questions,
            run_mode="fresh_run",
        )
    except ExternalQualificationError as exc:
        raise R1HostError(f"artifact root or durable identity rejected: {exc}") from exc

    bound_client = _BoundExperimentClient(
        client=client,
        durable_run=durable_run,
        live_binding_probe=live_binding_probe,
        expected_binding=expected_binding,
    )

    durable_run.begin_question("source-learning")
    bound_client.bind_question("source-learning")
    try:
        learned = run_source_learning(bound_client, family)
    except R1HostError:
        raise
    except StructureProposalError as exc:
        raise _stop_after_semantic_failure(
            durable_run,
            question_id="source-learning",
            phase="source-learning",
            exc=exc,
        ) from exc

    durable_run.commit_question(
        question_id="source-learning",
        result={
            "status": "source_structure_committed",
            "claim_status": _CLAIM_STATUS,
            "citable": False,
            "structure_id": learned.structure_id,
            "hypothesis": learned.hypothesis.to_mapping(),
            "source_evidence_ids": list(learned.source_evidence_ids),
            "resource_cost": {
                "calls": learned.resource_cost.calls,
                "input_tokens": learned.resource_cost.input_tokens,
                "output_tokens": learned.resource_cost.output_tokens,
            },
        },
    )

    try:
        arms = prepare_r1_arms(family, learned)
    except StructureProposalError as exc:
        durable_run.mark_stopped()
        raise R1HostError(f"R1 arm preparation failed: {exc}") from exc

    correctness: list[bool] = []
    for question_id, arm in (("t0", arms.t0), ("t1", arms.t1), ("t2", arms.t2)):
        durable_run.begin_question(question_id)
        bound_client.bind_question(question_id)
        try:
            probe = run_target_probe(
                bound_client,
                arm,
                family,
                step_index=step_index,
                examples_visible=examples_visible,
            )
        except R1HostError:
            raise
        except StructureProposalError as exc:
            raise _stop_after_semantic_failure(
                durable_run,
                question_id=question_id,
                phase=question_id,
                exc=exc,
            ) from exc

        correctness.append(probe.verification.correct)
        durable_run.commit_question(
            question_id=question_id,
            result={
                "status": "target_probe_completed",
                "claim_status": _CLAIM_STATUS,
                "citable": False,
                "correct": probe.verification.correct,
                "verification_error": probe.verification.error,
                "task_digest": probe.prompt.task_digest,
                "resource_cost": {
                    "calls": probe.resource_cost.calls,
                    "input_tokens": probe.resource_cost.input_tokens,
                    "output_tokens": probe.resource_cost.output_tokens,
                },
            },
        )

    durable_run.mark_completed()
    return R1HostResult(
        run_id=durable_run.run_id,
        identity_fingerprint=frozen_identity.fingerprint,
        status="COMPLETED",
        claim_status=_CLAIM_STATUS,
        citable=False,
        source_structure_id=learned.structure_id,
        arm_correctness=tuple(correctness),
    )
