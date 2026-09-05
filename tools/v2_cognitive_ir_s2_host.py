from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess

from relaylm.v2_cognitive_ir_actual_model import (
    S2ExperimentError,
    S2SmokeResult,
    run_s2_smoke,
)
from relaylm.v2_cognitive_ir_experiment import (
    REPRESENTATION_KINDS,
    prepare_r0_representation_arms,
)
from relaylm.v2_transfer_actual_model import (
    ExperimentClient,
    ExperimentCompletion,
    StructureProposalError,
)
from relaylm.v2_transfer_experiment import TransferFamily
from tools.external_qualification import (
    DurableQuestion,
    DurableQuestionRun,
    ExternalQualificationError,
    FrozenExperimentIdentity,
    freeze_experiment_identity,
)


_FORMATION_ORDER = ("form-p2", "form-p3", "form-p4")
_PROBE_ORDER = tuple(f"probe-p{index}" for index in range(len(REPRESENTATION_KINDS)))
_EXECUTION_ORDER = _FORMATION_ORDER + _PROBE_ORDER
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
_CLAIM_STATUS = "NON_CITABLE_S2_SMOKE"
_RESULT_NAME = "s2-smoke-result.json"


class S2HostError(ValueError):
    """The bounded #2211 S2 physical-host contract is not satisfied."""


@dataclass(frozen=True, slots=True)
class S2RepositoryState:
    commit: str
    tree: str
    clean: bool

    def __post_init__(self) -> None:
        for name in ("commit", "tree"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise S2HostError(f"repository {name} must be non-empty")
        if not isinstance(self.clean, bool):
            raise S2HostError("repository clean must be a boolean")


@dataclass(frozen=True, slots=True)
class S2HostResult:
    run_id: str
    identity_fingerprint: str
    status: str
    claim_status: str
    citable: bool
    provider_calls: int
    arm_correctness: tuple[bool, ...]


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
        raise S2HostError("S2 host identity/binding must be canonical JSON") from exc


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise S2HostError(f"{label} must be an object")
    return value


def _json_object_copy(value: Mapping[str, object], label: str) -> dict[str, object]:
    copied = json.loads(_canonical_json(dict(value)))
    if not isinstance(copied, dict):
        raise S2HostError(f"{label} must be an object")
    return copied


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
        raise S2HostError(f"repository git attestation failed: {' '.join(args)}") from exc
    return completed.stdout.strip()


def probe_s2_git_repository(repository_root: str | Path) -> S2RepositoryState:
    commit = _git_output(repository_root, "rev-parse", "--verify", "HEAD")
    tree = _git_output(repository_root, "rev-parse", "HEAD^{tree}")
    status = _git_output(
        repository_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
    )
    return S2RepositoryState(commit=commit, tree=tree, clean=not bool(status))


def _validate_static_contract(identity: Mapping[str, object]) -> None:
    if identity.get("execution_order") != list(_EXECUTION_ORDER):
        raise S2HostError(
            "execution order must be form-p2 -> form-p3 -> form-p4 -> probe-p0..p6"
        )
    retry_policy = _mapping(identity.get("retry_policy"), "retry policy")
    if retry_policy != {"automatic_retry": False, "semantic_retry": False}:
        raise S2HostError("retry policy must disable automatic retry and semantic retry")


def _validate_repository(
    identity: Mapping[str, object],
    observed: S2RepositoryState,
) -> None:
    expected = _mapping(identity.get("repository"), "repository identity")
    if set(expected) != {"commit", "tree", "clean_required"}:
        raise S2HostError(
            "repository identity must contain exactly commit/tree/clean_required"
        )
    if expected.get("clean_required") is not True:
        raise S2HostError("repository identity must require a clean checkout")
    if not observed.clean:
        raise S2HostError("repository checkout is dirty")
    if observed.commit != expected.get("commit"):
        raise S2HostError("repository commit does not match frozen identity")
    if observed.tree != expected.get("tree"):
        raise S2HostError("repository tree does not match frozen identity")


def _validate_artifact_root_outside_repository(
    *,
    artifact_root: str | Path,
    repository_root: str | Path,
) -> None:
    repository = Path(repository_root).resolve()
    artifact = Path(artifact_root).resolve()
    try:
        artifact.relative_to(repository)
    except ValueError:
        return
    raise S2HostError("artifact root must resolve outside the repository checkout")


def _expected_binding(identity: Mapping[str, object]) -> dict[str, object]:
    missing = [name for name in _MATERIAL_BINDING_FIELDS if name not in identity]
    if missing:
        raise S2HostError(
            "physical binding is missing frozen fields: " + ", ".join(missing)
        )
    return _json_object_copy(
        {name: identity[name] for name in _MATERIAL_BINDING_FIELDS},
        "physical binding",
    )


def _validate_live_binding(
    expected: Mapping[str, object],
    observed: Mapping[str, object],
) -> None:
    if set(observed) != set(_MATERIAL_BINDING_FIELDS):
        raise S2HostError("physical binding drift: live binding field set changed")
    for name in _MATERIAL_BINDING_FIELDS:
        if _canonical_json(observed[name]) != _canonical_json(expected[name]):
            raise S2HostError(f"physical binding drift: {name} changed")


def _validate_probe_coordinates(
    family: TransferFamily,
    *,
    step_index: int,
    examples_visible: int,
) -> None:
    if isinstance(step_index, bool) or not isinstance(step_index, int):
        raise S2HostError("step_index must be an integer")
    if step_index < 0 or step_index >= len(family.target_steps):
        raise S2HostError("step_index is outside the target trajectory")
    examples = family.target_steps[step_index].examples
    if isinstance(examples_visible, bool) or not isinstance(examples_visible, int):
        raise S2HostError("examples_visible must be an integer")
    if examples_visible < 0 or examples_visible > len(examples):
        raise S2HostError("examples_visible is outside the declared evidence range")


def _questions(
    family: TransferFamily,
    *,
    step_index: int,
    examples_visible: int,
) -> tuple[DurableQuestion, ...]:
    r0 = prepare_r0_representation_arms(family)
    source_history_digest = r0["P0_RAW_HISTORY"].source_history_digest
    questions: list[DurableQuestion] = []
    for question_id, representation_kind in (
        ("form-p2", "P2_ORDINARY_SUMMARY"),
        ("form-p3", "P3_SEMANTIC_CACHE"),
        ("form-p4", "P4_MEMORY_PLUS_STRUCTURE"),
    ):
        questions.append(
            DurableQuestion.from_content(
                question_id,
                {
                    "phase": "formation",
                    "representation_kind": representation_kind,
                    "source_history_digest": source_history_digest,
                },
                session_id="s2",
            )
        )
    for index, representation_kind in enumerate(REPRESENTATION_KINDS):
        questions.append(
            DurableQuestion.from_content(
                f"probe-p{index}",
                {
                    "phase": "target_probe",
                    "representation_kind": representation_kind,
                    "public_target_digest": family.public_target_digest,
                    "step_index": step_index,
                    "examples_visible": examples_visible,
                },
                session_id="s2",
            )
        )
    return tuple(questions)


class _DurableS2Client:
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
        self._expected_binding = _json_object_copy(expected_binding, "physical binding")
        self._call_index = 0
        self._active_question: str | None = None

    @property
    def call_count(self) -> int:
        return self._call_index

    def _append_failure(self, *, kind: str, error: str) -> None:
        if self._active_question is not None:
            self._durable_run.append_request_evidence(
                question_id=self._active_question,
                evidence={
                    "kind": kind,
                    "authority": "instrumentation_only",
                    "error": error,
                },
            )
        self._durable_run.mark_stopped()

    def _commit_previous_if_protocol_advanced(self) -> None:
        if self._active_question is None:
            return
        try:
            self._durable_run.commit_question(
                question_id=self._active_question,
                result={
                    "status": "MODEL_EXCHANGE_ACCEPTED_BY_PROTOCOL",
                    "claim_status": _CLAIM_STATUS,
                    "citable": False,
                },
            )
        except ExternalQualificationError as exc:
            self._durable_run.mark_stopped()
            raise S2HostError(f"durable question commit failed: {exc}") from exc
        self._active_question = None

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        if self._call_index >= len(_EXECUTION_ORDER):
            self._append_failure(
                kind="undeclared_extra_model_call",
                error="S2 protocol attempted more than ten provider calls",
            )
            raise S2HostError("S2 protocol attempted an undeclared extra model call")

        self._commit_previous_if_protocol_advanced()
        question_id = _EXECUTION_ORDER[self._call_index]
        try:
            self._durable_run.begin_question(question_id)
        except ExternalQualificationError as exc:
            self._durable_run.mark_stopped()
            raise S2HostError(f"durable question begin failed: {exc}") from exc
        self._active_question = question_id

        try:
            observed = self._live_binding_probe()
            if not isinstance(observed, Mapping):
                raise S2HostError(
                    "physical binding drift: live probe did not return an object"
                )
            _validate_live_binding(self._expected_binding, observed)
        except S2HostError as exc:
            self._append_failure(kind="physical_binding_drift", error=str(exc))
            raise
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self._append_failure(kind="physical_binding_probe_failure", error=error)
            raise S2HostError(f"physical binding probe failure: {error}") from exc

        try:
            completion = self._client.complete(messages)
        except StructureProposalError as exc:
            self._append_failure(kind="provider_failure", error=str(exc))
            raise S2HostError(f"provider failure: {exc}") from exc
        except S2HostError:
            raise
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self._append_failure(kind="provider_client_failure", error=error)
            raise S2HostError(f"provider client failure: {error}") from exc

        self._durable_run.append_request_evidence(
            question_id=question_id,
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
        self._call_index += 1
        return completion

    def stop_after_protocol_failure(self, exc: Exception) -> None:
        error = f"{type(exc).__name__}: {exc}"
        self._append_failure(kind="model_protocol_failure", error=error)

    def finish_exchanges(self) -> None:
        if self._call_index != len(_EXECUTION_ORDER):
            self._append_failure(
                kind="model_call_count_mismatch",
                error=(
                    f"expected {len(_EXECUTION_ORDER)} provider calls, "
                    f"observed {self._call_index}"
                ),
            )
            raise S2HostError("S2 provider call count does not match frozen protocol")
        self._commit_previous_if_protocol_advanced()
        if self._durable_run.next_question() is not None:
            self._durable_run.mark_stopped()
            raise S2HostError("S2 durable question sequence did not fully complete")


def _representation_digest(serialized: str) -> str:
    return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _result_payload(
    *,
    result: S2SmokeResult,
    family: TransferFamily,
    run_id: str,
    identity_fingerprint: str,
) -> dict[str, object]:
    arms: list[dict[str, object]] = []
    for kind in REPRESENTATION_KINDS:
        arm = result.arms[kind]
        arms.append(
            {
                "kind": kind,
                "representation_digest": _representation_digest(
                    arm.representation.serialized
                ),
                "provenance_handles": list(arm.representation.provenance_handles),
                "reconstruction_handles": list(
                    arm.representation.reconstruction_handles
                ),
                "cost": {
                    "formation_calls": arm.formation_calls,
                    "formation_input_tokens": arm.formation_input_tokens,
                    "formation_output_tokens": arm.formation_output_tokens,
                    "projected_bytes": arm.projected_bytes,
                    "target_calls": arm.target_calls,
                    "target_input_tokens": arm.target_input_tokens,
                    "target_output_tokens": arm.target_output_tokens,
                    "total_calls": arm.total_calls,
                    "total_input_tokens": arm.total_input_tokens,
                    "total_output_tokens": arm.total_output_tokens,
                },
                "verification": {
                    "correct": arm.verification.correct,
                    "parsed_output": (
                        None
                        if arm.verification.parsed_output is None
                        else list(arm.verification.parsed_output)
                    ),
                    "error": arm.verification.error,
                },
                "target_task_digest": arm.target_task_digest,
            }
        )
    return {
        "run_id": run_id,
        "identity_fingerprint": identity_fingerprint,
        "status": "COMPLETED",
        "claim_status": _CLAIM_STATUS,
        "citable": False,
        "seed": family.seed,
        "regime": family.regime,
        "provider_calls": result.physical_provider_calls,
        "arms": arms,
    }


def _write_result_exclusive(root: Path, payload: Mapping[str, object]) -> None:
    path = root / _RESULT_NAME
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(_canonical_json(payload))
            handle.write("\n")
            handle.flush()
    except OSError as exc:
        raise S2HostError(f"cannot persist S2 smoke result: {exc}") from exc


def run_s2_host_smoke(
    *,
    artifact_root: str | Path,
    identity: Mapping[str, object],
    repository_root: str | Path,
    live_binding_probe: Callable[[], Mapping[str, object]],
    client: ExperimentClient,
    family: TransferFamily,
    step_index: int,
    examples_visible: int,
) -> S2HostResult:
    """Execute one fresh NON_CITABLE #2211 S2 smoke under frozen host authority."""

    if not isinstance(identity, Mapping):
        raise S2HostError("frozen experiment identity must be an object")
    identity_snapshot = _json_object_copy(identity, "frozen experiment identity")
    _validate_static_contract(identity_snapshot)
    _validate_probe_coordinates(
        family,
        step_index=step_index,
        examples_visible=examples_visible,
    )

    observed_repository = probe_s2_git_repository(repository_root)
    _validate_repository(identity_snapshot, observed_repository)
    _validate_artifact_root_outside_repository(
        artifact_root=artifact_root,
        repository_root=repository_root,
    )

    proposed_binding = _expected_binding(identity_snapshot)
    try:
        initial_live_binding = live_binding_probe()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        raise S2HostError(
            f"physical binding probe failure during preflight: {error}"
        ) from exc
    if not isinstance(initial_live_binding, Mapping):
        raise S2HostError(
            "physical binding drift: live probe did not return an object"
        )
    _validate_live_binding(proposed_binding, initial_live_binding)

    try:
        frozen_identity: FrozenExperimentIdentity = freeze_experiment_identity(
            identity=identity_snapshot,
            live_attestation=_mapping(
                initial_live_binding["launch_admission"],
                "live launch admission",
            ),
        )
    except ExternalQualificationError as exc:
        raise S2HostError(f"physical frozen identity is invalid: {exc}") from exc

    expected_binding = _expected_binding(frozen_identity.to_mapping())
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
        raise S2HostError(f"artifact root or durable identity rejected: {exc}") from exc

    bound_client = _DurableS2Client(
        client=client,
        durable_run=durable_run,
        live_binding_probe=live_binding_probe,
        expected_binding=expected_binding,
    )
    try:
        smoke = run_s2_smoke(
            bound_client,
            family,
            step_index=step_index,
            examples_visible=examples_visible,
        )
    except S2HostError:
        raise
    except S2ExperimentError as exc:
        bound_client.stop_after_protocol_failure(exc)
        raise S2HostError(f"S2 model protocol failure: {exc}") from exc
    except Exception as exc:
        bound_client.stop_after_protocol_failure(exc)
        raise S2HostError(
            f"S2 model protocol failure: {type(exc).__name__}: {exc}"
        ) from exc

    bound_client.finish_exchanges()
    if smoke.physical_provider_calls != len(_EXECUTION_ORDER):
        durable_run.mark_stopped()
        raise S2HostError("S2 result reports an unexpected physical provider call count")

    result_payload = _result_payload(
        result=smoke,
        family=family,
        run_id=durable_run.run_id,
        identity_fingerprint=frozen_identity.fingerprint,
    )
    try:
        _write_result_exclusive(Path(artifact_root), result_payload)
    except S2HostError:
        durable_run.mark_stopped()
        raise

    try:
        durable_run.mark_completed()
    except ExternalQualificationError as exc:
        durable_run.mark_stopped()
        raise S2HostError(f"S2 durable run completion failed: {exc}") from exc

    return S2HostResult(
        run_id=durable_run.run_id,
        identity_fingerprint=frozen_identity.fingerprint,
        status="COMPLETED",
        claim_status=_CLAIM_STATUS,
        citable=False,
        provider_calls=smoke.physical_provider_calls,
        arm_correctness=tuple(
            smoke.arms[kind].verification.correct for kind in REPRESENTATION_KINDS
        ),
    )
