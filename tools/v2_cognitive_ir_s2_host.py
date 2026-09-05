from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
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
    semantic_digest,
)
from relaylm.v2_transfer_actual_model import (
    ExperimentClient,
    ExperimentCompletion,
    StructureProposalError,
)
from relaylm.v2_transfer_experiment import TransferFamily


_FORMATION_ORDER = ("form-p2", "form-p3", "form-p4")
_PROBE_ORDER = tuple(f"probe-p{index}" for index in range(len(REPRESENTATION_KINDS)))
_EXECUTION_ORDER = _FORMATION_ORDER + _PROBE_ORDER
_REQUIRED_STABLE_IDENTITY_FIELDS = ("model", "backend", "runtime")
_DEFAULT_LIVE_BINDING_FIELDS = ("model",)
_CLAIM_STATUS = "NON_CITABLE_S2_SMOKE"
_RESULT_NAME = "s2-smoke-result.json"
_MANIFEST_NAME = "run-manifest.json"
_STATE_NAME = "run-state.json"
_EVIDENCE_NAME = "request-evidence.jsonl"
_SECRET_KEY_FRAGMENTS = ("api_key", "password", "secret", "authorization", "bearer")


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
    mechanical_classification: str
    typed_generic_semantic_equal: bool


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


def _sha256(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _reject_secret_keys(value: object, *, path: str = "identity") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).lower()
            if any(fragment in key for fragment in _SECRET_KEY_FRAGMENTS):
                raise S2HostError(f"{path} must not persist secret-bearing field {raw_key}")
            _reject_secret_keys(child, path=f"{path}.{raw_key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_keys(child, path=f"{path}[{index}]")


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


def _live_binding_fields(identity: Mapping[str, object]) -> tuple[str, ...]:
    raw = identity.get("live_binding_fields")
    if raw is None:
        fields = _DEFAULT_LIVE_BINDING_FIELDS
    else:
        if not isinstance(raw, list) or not raw:
            raise S2HostError("live_binding_fields must be a non-empty string array")
        if any(not isinstance(item, str) or not item.strip() for item in raw):
            raise S2HostError("live_binding_fields must contain only non-empty strings")
        fields = tuple(raw)
        if len(set(fields)) != len(fields):
            raise S2HostError("live_binding_fields must not contain duplicates")
    if "model" not in fields:
        raise S2HostError("live_binding_fields must include model")
    missing = [name for name in fields if name not in identity]
    if missing:
        raise S2HostError(
            "live binding fields are absent from stable identity: " + ", ".join(missing)
        )
    return fields


def _validate_static_contract(identity: Mapping[str, object]) -> tuple[str, ...]:
    if identity.get("execution_order") != list(_EXECUTION_ORDER):
        raise S2HostError(
            "execution order must be form-p2 -> form-p3 -> form-p4 -> probe-p0..p6"
        )
    retry_policy = _mapping(identity.get("retry_policy"), "retry policy")
    if retry_policy != {"automatic_retry": False, "semantic_retry": False}:
        raise S2HostError("retry policy must disable automatic retry and semantic retry")
    missing = [name for name in _REQUIRED_STABLE_IDENTITY_FIELDS if name not in identity]
    if missing:
        raise S2HostError(
            "stable experiment identity is missing fields: " + ", ".join(missing)
        )
    for name in _REQUIRED_STABLE_IDENTITY_FIELDS:
        value = identity[name]
        if value is None or (isinstance(value, str) and not value.strip()):
            raise S2HostError(f"stable experiment identity {name} must be non-empty")
    _reject_secret_keys(identity)
    return _live_binding_fields(identity)


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


def _prepare_artifact_root(root: Path) -> None:
    try:
        root.mkdir(parents=True, exist_ok=True)
        if any(root.iterdir()):
            raise S2HostError("fresh S2 artifact root must be empty")
    except OSError as exc:
        raise S2HostError(f"cannot prepare S2 artifact root: {exc}") from exc


def _write_json_atomically(path: Path, value: Mapping[str, object]) -> None:
    payload = _canonical_json(dict(value)) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise S2HostError(f"cannot persist S2 durable state: {exc}") from exc


def _write_json_exclusive(path: Path, value: Mapping[str, object]) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(dict(value)))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise S2HostError(f"cannot persist S2 artifact: {exc}") from exc


def _append_jsonl(path: Path, value: Mapping[str, object]) -> None:
    record = dict(value)
    envelope_keys = {"run_id", "identity_fingerprint", "question_id", "order"}
    if "evidence" not in record and "authority" in record:
        envelope = {key: record.pop(key) for key in list(record) if key in envelope_keys}
        envelope["evidence"] = record
        record = envelope
    try:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(record))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise S2HostError(f"cannot persist S2 request evidence: {exc}") from exc


def _expected_binding(
    identity: Mapping[str, object],
    fields: tuple[str, ...],
) -> dict[str, object]:
    return _json_object_copy(
        {name: identity[name] for name in fields},
        "live physical binding",
    )


def _validate_live_binding(
    expected: Mapping[str, object],
    observed: Mapping[str, object],
) -> None:
    missing = [name for name in expected if name not in observed]
    if missing:
        raise S2HostError(
            "physical binding drift: live probe omitted " + ", ".join(missing)
        )
    for name, value in expected.items():
        if _canonical_json(observed[name]) != _canonical_json(value):
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


def _run_identity(
    identity: Mapping[str, object],
    family: TransferFamily,
    *,
    step_index: int,
    examples_visible: int,
) -> tuple[str, str]:
    fingerprint = _sha256(["relaylm2-cognitive-ir-s2-identity", identity])
    run_id = "s2-" + _sha256(
        [
            fingerprint,
            family.seed,
            family.regime,
            step_index,
            examples_visible,
            family.public_target_digest,
        ]
    ).split(":", 1)[1]
    return fingerprint, run_id


def _initial_manifest(
    *,
    identity: Mapping[str, object],
    identity_fingerprint: str,
    run_id: str,
    family: TransferFamily,
    step_index: int,
    examples_visible: int,
    live_binding_fields: tuple[str, ...],
) -> dict[str, object]:
    r0 = prepare_r0_representation_arms(family)
    return {
        "format_version": 1,
        "kind": "relaylm2_cognitive_ir_s2_smoke",
        "run_id": run_id,
        "identity": _json_object_copy(identity, "frozen S2 identity"),
        "identity_fingerprint": identity_fingerprint,
        "claim_status": _CLAIM_STATUS,
        "citable": False,
        "family": {
            "seed": family.seed,
            "regime": family.regime,
            "step_index": step_index,
            "examples_visible": examples_visible,
            "source_history_digest": r0["P0_RAW_HISTORY"].source_history_digest,
            "public_target_digest": family.public_target_digest,
        },
        "execution_order": list(_EXECUTION_ORDER),
        "live_binding_fields": list(live_binding_fields),
    }


def _state_payload(
    *,
    run_id: str,
    identity_fingerprint: str,
    status: str,
    provider_calls: int,
    next_call: int,
    failure: Mapping[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "format_version": 1,
        "run_id": run_id,
        "identity_fingerprint": identity_fingerprint,
        "status": status,
        "claim_status": _CLAIM_STATUS,
        "citable": False,
        "provider_calls": provider_calls,
        "next_call": next_call,
    }
    if failure is not None:
        payload["failure"] = _json_object_copy(failure, "S2 failure")
    return payload


def _record_failure(
    *,
    root: Path,
    run_id: str,
    identity_fingerprint: str,
    provider_calls: int,
    next_call: int,
    question_id: str,
    kind: str,
    error: str,
) -> None:
    failure = {"kind": kind, "question_id": question_id, "error": error}
    try:
        _append_jsonl(
            root / _EVIDENCE_NAME,
            {
                "run_id": run_id,
                "identity_fingerprint": identity_fingerprint,
                "question_id": question_id,
                "kind": kind,
                "authority": "instrumentation_only",
                "error": error,
            },
        )
    finally:
        _write_json_atomically(
            root / _STATE_NAME,
            _state_payload(
                run_id=run_id,
                identity_fingerprint=identity_fingerprint,
                status="INCOMPLETE",
                provider_calls=provider_calls,
                next_call=next_call,
                failure=failure,
            ),
        )


class _BoundS2Client:
    def __init__(
        self,
        *,
        client: ExperimentClient,
        root: Path,
        run_id: str,
        identity_fingerprint: str,
        live_binding_probe: Callable[[], Mapping[str, object]],
        expected_binding: Mapping[str, object],
    ) -> None:
        self._client = client
        self._root = root
        self._run_id = run_id
        self._identity_fingerprint = identity_fingerprint
        self._live_binding_probe = live_binding_probe
        self._expected_binding = _json_object_copy(expected_binding, "live physical binding")
        self._call_index = 0

    @property
    def call_count(self) -> int:
        return self._call_index

    def _fail(self, *, question_id: str, kind: str, error: str) -> None:
        _record_failure(
            root=self._root,
            run_id=self._run_id,
            identity_fingerprint=self._identity_fingerprint,
            provider_calls=self._call_index,
            next_call=self._call_index,
            question_id=question_id,
            kind=kind,
            error=error,
        )

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        if self._call_index >= len(_EXECUTION_ORDER):
            self._fail(
                question_id="undeclared-extra-call",
                kind="undeclared_extra_model_call",
                error="S2 protocol attempted more than ten provider calls",
            )
            raise S2HostError("S2 protocol attempted an undeclared extra model call")

        question_id = _EXECUTION_ORDER[self._call_index]
        try:
            observed = self._live_binding_probe()
            if not isinstance(observed, Mapping):
                raise S2HostError(
                    "physical binding drift: live probe did not return an object"
                )
            _validate_live_binding(self._expected_binding, observed)
        except S2HostError as exc:
            self._fail(question_id=question_id, kind="physical_binding_drift", error=str(exc))
            raise
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self._fail(
                question_id=question_id,
                kind="physical_binding_probe_failure",
                error=error,
            )
            raise S2HostError(f"physical binding probe failure: {error}") from exc

        try:
            completion = self._client.complete(messages)
        except StructureProposalError as exc:
            self._fail(question_id=question_id, kind="provider_failure", error=str(exc))
            raise S2HostError(f"provider failure: {exc}") from exc
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self._fail(question_id=question_id, kind="provider_client_failure", error=error)
            raise S2HostError(f"provider client failure: {error}") from exc

        _append_jsonl(
            self._root / _EVIDENCE_NAME,
            {
                "run_id": self._run_id,
                "identity_fingerprint": self._identity_fingerprint,
                "question_id": question_id,
                "order": self._call_index,
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
        _write_json_atomically(
            self._root / _STATE_NAME,
            _state_payload(
                run_id=self._run_id,
                identity_fingerprint=self._identity_fingerprint,
                status="RUNNING",
                provider_calls=self._call_index,
                next_call=self._call_index,
            ),
        )
        return completion

    def stop_after_protocol_failure(self, exc: Exception) -> None:
        index = max(0, self._call_index - 1)
        question_id = _EXECUTION_ORDER[index] if self._call_index else "pre-model-protocol"
        self._fail(
            question_id=question_id,
            kind="model_protocol_failure",
            error=f"{type(exc).__name__}: {exc}",
        )

    def finish_exchanges(self) -> None:
        if self._call_index != len(_EXECUTION_ORDER):
            self._fail(
                question_id="call-count",
                kind="model_call_count_mismatch",
                error=(
                    f"expected {len(_EXECUTION_ORDER)} provider calls, "
                    f"observed {self._call_index}"
                ),
            )
            raise S2HostError("S2 provider call count does not match frozen protocol")


def _representation_digest(serialized: str) -> str:
    return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _protocol_assessment(result: S2SmokeResult) -> dict[str, object]:
    verifications = [result.arms[kind].verification for kind in REPRESENTATION_KINDS]
    all_outputs_protocol_valid = all(item.error is None for item in verifications)
    correctness = [item.correct for item in verifications]
    if not all_outputs_protocol_valid:
        classification = "OUTPUT_PROTOCOL_DEFECT"
    elif all(correctness):
        classification = "CEILING"
    elif not any(correctness):
        classification = "FLOOR"
    else:
        classification = "MECHANICALLY_DISCRIMINATING"

    p4 = result.arms["P4_MEMORY_PLUS_STRUCTURE"].representation
    p5 = result.arms["P5_STRUCTURE_ONLY_RECONSTRUCTABLE"].representation
    p6 = result.arms["P6_GENERIC_EQUAL_INFORMATION"].representation
    p4_payload = _mapping(json.loads(p4.serialized), "P4 representation")
    p6_payload = _mapping(json.loads(p6.serialized), "P6 representation")
    p4_semantic_digest = semantic_digest(p4.kind, p4_payload)
    p6_semantic_digest = semantic_digest(p6.kind, p6_payload)
    semantic_equal = p4_semantic_digest == p6_semantic_digest
    if not semantic_equal:
        raise S2HostError("completed S2 smoke lost P4/P6 semantic identity")
    shared_formation = (
        p4.formation_completion is not None
        and p4.formation_completion is p5.formation_completion
        and p4.formation_completion is p6.formation_completion
    )
    if not shared_formation:
        raise S2HostError("P4/P5/P6 do not share the one declared formation completion")

    return {
        "classification": classification,
        "all_outputs_protocol_valid": all_outputs_protocol_valid,
        "typed_generic_semantic_equal": semantic_equal,
        "typed_generic_semantic_digest": p4_semantic_digest,
        "p4_p5_p6_shared_formation": shared_formation,
        "s3_preregistration_allowed": classification == "MECHANICALLY_DISCRIMINATING",
    }


def _result_payload(
    *,
    result: S2SmokeResult,
    family: TransferFamily,
    run_id: str,
    identity_fingerprint: str,
) -> dict[str, object]:
    assessment = _protocol_assessment(result)
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
        "protocol_assessment": assessment,
        "cost_accounting": {
            "physical_provider_calls": result.physical_provider_calls,
            "p5_p6_formation_cost_is_counterfactual_shared_p4_cost": True,
        },
        "arms": arms,
    }


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
    """Execute one fresh NON_CITABLE #2211 S2 smoke under minimum sufficient host binding."""

    if not isinstance(identity, Mapping):
        raise S2HostError("frozen experiment identity must be an object")
    identity_snapshot = _json_object_copy(identity, "frozen experiment identity")
    live_fields = _validate_static_contract(identity_snapshot)
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

    root = Path(artifact_root)
    _prepare_artifact_root(root)
    identity_fingerprint, run_id = _run_identity(
        identity_snapshot,
        family,
        step_index=step_index,
        examples_visible=examples_visible,
    )
    _write_json_exclusive(
        root / _MANIFEST_NAME,
        _initial_manifest(
            identity=identity_snapshot,
            identity_fingerprint=identity_fingerprint,
            run_id=run_id,
            family=family,
            step_index=step_index,
            examples_visible=examples_visible,
            live_binding_fields=live_fields,
        ),
    )
    _write_json_atomically(
        root / _STATE_NAME,
        _state_payload(
            run_id=run_id,
            identity_fingerprint=identity_fingerprint,
            status="RUNNING",
            provider_calls=0,
            next_call=0,
        ),
    )

    expected_binding = _expected_binding(identity_snapshot, live_fields)
    try:
        initial_live_binding = live_binding_probe()
        if not isinstance(initial_live_binding, Mapping):
            raise S2HostError(
                "physical binding drift: live probe did not return an object"
            )
        _validate_live_binding(expected_binding, initial_live_binding)
    except S2HostError as exc:
        _record_failure(
            root=root,
            run_id=run_id,
            identity_fingerprint=identity_fingerprint,
            provider_calls=0,
            next_call=0,
            question_id="preflight",
            kind="physical_binding_drift",
            error=str(exc),
        )
        raise
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        _record_failure(
            root=root,
            run_id=run_id,
            identity_fingerprint=identity_fingerprint,
            provider_calls=0,
            next_call=0,
            question_id="preflight",
            kind="physical_binding_probe_failure",
            error=error,
        )
        raise S2HostError(f"physical binding probe failure during preflight: {error}") from exc

    bound_client = _BoundS2Client(
        client=client,
        root=root,
        run_id=run_id,
        identity_fingerprint=identity_fingerprint,
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
        _record_failure(
            root=root,
            run_id=run_id,
            identity_fingerprint=identity_fingerprint,
            provider_calls=bound_client.call_count,
            next_call=bound_client.call_count,
            question_id="reported-call-count",
            kind="model_call_count_mismatch",
            error="S2 result reports an unexpected physical provider call count",
        )
        raise S2HostError("S2 result reports an unexpected physical provider call count")

    result_payload = _result_payload(
        result=smoke,
        family=family,
        run_id=run_id,
        identity_fingerprint=identity_fingerprint,
    )
    try:
        _write_json_exclusive(root / _RESULT_NAME, result_payload)
    except S2HostError as exc:
        _record_failure(
            root=root,
            run_id=run_id,
            identity_fingerprint=identity_fingerprint,
            provider_calls=bound_client.call_count,
            next_call=bound_client.call_count,
            question_id="result-persistence",
            kind="artifact_persistence_failure",
            error=str(exc),
        )
        raise

    _write_json_atomically(
        root / _STATE_NAME,
        _state_payload(
            run_id=run_id,
            identity_fingerprint=identity_fingerprint,
            status="COMPLETED",
            provider_calls=bound_client.call_count,
            next_call=bound_client.call_count,
        ),
    )
    assessment = _mapping(result_payload["protocol_assessment"], "protocol assessment")
    return S2HostResult(
        run_id=run_id,
        identity_fingerprint=identity_fingerprint,
        status="COMPLETED",
        claim_status=_CLAIM_STATUS,
        citable=False,
        provider_calls=smoke.physical_provider_calls,
        arm_correctness=tuple(
            smoke.arms[kind].verification.correct for kind in REPRESENTATION_KINDS
        ),
        mechanical_classification=str(assessment["classification"]),
        typed_generic_semantic_equal=bool(assessment["typed_generic_semantic_equal"]),
    )
