from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Protocol

import httpx

from relaylm.v2_cognitive_ir_calibration import (
    CALIBRATION_CLAIM_STATUS,
    CALIBRATION_DIFFICULTIES,
    CALIBRATION_PROBES,
    CALIBRATION_SEEDS,
    CalibrationError,
    OpenAICompatibleStructuredCalibrationClient,
    run_calibration_matrix,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError


_RESULT_NAME = "calibration-result.json"
_MANIFEST_NAME = "run-manifest.json"
_STATE_NAME = "run-state.json"
_EVIDENCE_NAME = "request-evidence.jsonl"
_SECRET_KEY_FRAGMENTS = ("api_key", "password", "secret", "authorization", "bearer")
_RETRY_POLICY = {"automatic_retry": False, "semantic_retry": False}


class CalibrationHostError(ValueError):
    """The bounded #2211 physical calibration host contract is not satisfied."""


class CalibrationTransportClient(Protocol):
    provider_attempts: int
    provider_completions: int

    @property
    def transport_identity(self) -> Mapping[str, object]: ...

    def complete_structured(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> ExperimentCompletion: ...


@dataclass(frozen=True, slots=True)
class CalibrationRepositoryState:
    commit: str
    tree: str
    clean: bool


@dataclass(frozen=True, slots=True)
class CalibrationHostResult:
    run_id: str
    identity_fingerprint: str
    status: str
    claim_status: str
    citable: bool
    provider_attempts: int
    provider_completions: int
    selected_difficulty: str | None
    total_input_tokens: int
    total_output_tokens: int


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
        raise CalibrationHostError("calibration identity must be canonical JSON") from exc


def _json_object(value: Mapping[str, object], *, label: str) -> dict[str, object]:
    copied = json.loads(_canonical_json(dict(value)))
    if not isinstance(copied, dict):
        raise CalibrationHostError(f"{label} must be an object")
    return copied


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CalibrationHostError(f"{label} must be an object")
    return value


def _sha256(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _reject_secret_keys(value: object, *, path: str = "identity") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).lower()
            if any(fragment in key for fragment in _SECRET_KEY_FRAGMENTS):
                raise CalibrationHostError(f"{path} must not persist secret-bearing field {raw_key}")
            _reject_secret_keys(child, path=f"{path}.{raw_key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_keys(child, path=f"{path}[{index}]")


def _git_output(repository_root: str | Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CalibrationHostError(
            f"repository git attestation failed: {' '.join(args)}"
        ) from exc
    return completed.stdout.strip()


def probe_calibration_git_repository(
    repository_root: str | Path,
) -> CalibrationRepositoryState:
    commit = _git_output(repository_root, "rev-parse", "--verify", "HEAD")
    tree = _git_output(repository_root, "rev-parse", "HEAD^{tree}")
    status = _git_output(
        repository_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
    )
    return CalibrationRepositoryState(commit=commit, tree=tree, clean=not bool(status))


def _validate_repository(
    identity: Mapping[str, object],
    observed: CalibrationRepositoryState,
) -> None:
    expected = _mapping(identity.get("repository"), label="repository identity")
    if set(expected) != {"commit", "tree", "clean_required"}:
        raise CalibrationHostError(
            "repository identity must contain exactly commit/tree/clean_required"
        )
    if expected.get("clean_required") is not True:
        raise CalibrationHostError("repository identity must require a clean checkout")
    if not observed.clean:
        raise CalibrationHostError("repository checkout is dirty")
    if observed.commit != expected.get("commit"):
        raise CalibrationHostError("repository commit does not match frozen identity")
    if observed.tree != expected.get("tree"):
        raise CalibrationHostError("repository tree does not match frozen identity")


def _prepare_artifact_root(
    artifact_root: str | Path,
    repository_root: str | Path,
) -> Path:
    root = Path(artifact_root).resolve()
    repository = Path(repository_root).resolve()
    try:
        root.relative_to(repository)
    except ValueError:
        pass
    else:
        raise CalibrationHostError("artifact root must resolve outside repository checkout")
    try:
        root.mkdir(parents=True, exist_ok=True)
        if any(root.iterdir()):
            raise CalibrationHostError("fresh calibration artifact root must be empty")
    except OSError as exc:
        raise CalibrationHostError(f"cannot prepare calibration artifact root: {exc}") from exc
    return root


def _write_json_atomically(path: Path, value: Mapping[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = _canonical_json(dict(value)) + "\n"
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
        raise CalibrationHostError(f"cannot persist calibration state: {exc}") from exc


def _write_json_exclusive(path: Path, value: Mapping[str, object]) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(dict(value)))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CalibrationHostError(f"cannot persist calibration artifact: {exc}") from exc


def _append_jsonl(path: Path, value: Mapping[str, object]) -> None:
    try:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(dict(value)))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CalibrationHostError(f"cannot persist calibration request evidence: {exc}") from exc


def calibration_call_plan() -> tuple[str, ...]:
    return tuple(
        f"{difficulty}|{seed}|{probe}"
        for difficulty in CALIBRATION_DIFFICULTIES
        for seed in CALIBRATION_SEEDS
        for probe in CALIBRATION_PROBES
    )


def _validate_static_identity(
    identity: Mapping[str, object],
    client: CalibrationTransportClient,
) -> tuple[str, ...]:
    _reject_secret_keys(identity)

    required = {
        "repository",
        "model",
        "model_instance_id",
        "context_length",
        "runtime",
        "transport",
        "retry_policy",
        "live_binding_fields",
        "call_plan",
    }
    missing = sorted(required - set(identity))
    if missing:
        raise CalibrationHostError(
            "calibration identity is missing fields: " + ", ".join(missing)
        )

    if identity.get("retry_policy") != _RETRY_POLICY:
        raise CalibrationHostError("retry policy must disable automatic and semantic retry")
    if identity.get("call_plan") != list(calibration_call_plan()):
        raise CalibrationHostError("calibration call plan does not match frozen 72-call order")

    fields = identity.get("live_binding_fields")
    if not isinstance(fields, list) or not fields:
        raise CalibrationHostError("live_binding_fields must be a non-empty string array")
    if any(not isinstance(item, str) or not item.strip() for item in fields):
        raise CalibrationHostError("live_binding_fields must contain only non-empty strings")
    if len(set(fields)) != len(fields):
        raise CalibrationHostError("live_binding_fields must not contain duplicates")
    for required_field in ("model", "model_instance_id", "context_length", "runtime"):
        if required_field not in fields:
            raise CalibrationHostError(
                f"live_binding_fields must include {required_field}"
            )
        if required_field not in identity:
            raise CalibrationHostError(
                f"live binding field {required_field} is absent from identity"
            )

    declared_transport = _mapping(identity.get("transport"), label="transport identity")
    observed_transport = client.transport_identity
    if _canonical_json(dict(declared_transport)) != _canonical_json(dict(observed_transport)):
        raise CalibrationHostError("client transport identity does not match frozen identity")

    if declared_transport.get("api") != "openai-chat-completions-json-schema-v1":
        raise CalibrationHostError("calibration transport must use OpenAI-compatible Chat Completions")
    if declared_transport.get("structured_output") is not True:
        raise CalibrationHostError("calibration transport must require structured output")

    return tuple(fields)


def _expected_binding(
    identity: Mapping[str, object],
    fields: tuple[str, ...],
) -> dict[str, object]:
    return _json_object(
        {field: identity[field] for field in fields},
        label="expected live binding",
    )


def _validate_live_binding(
    expected: Mapping[str, object],
    observed: Mapping[str, object],
) -> None:
    for key, value in expected.items():
        if key not in observed:
            raise CalibrationHostError(f"physical binding probe omitted {key}")
        if _canonical_json(observed[key]) != _canonical_json(value):
            raise CalibrationHostError(f"physical binding drift: {key} changed")


def _identity_fingerprint(identity: Mapping[str, object]) -> str:
    return _sha256(["relaylm2-cognitive-ir-calibration-host-v1", identity])


def _run_id(identity_fingerprint: str) -> str:
    return "cal-" + _sha256(
        [identity_fingerprint, list(CALIBRATION_SEEDS), list(CALIBRATION_DIFFICULTIES)]
    ).split(":", 1)[1]


def probe_lmstudio_native_calibration_binding(
    *,
    base_url: str,
    model: str,
    api_key: str | None = None,
    timeout_seconds: float = 10.0,
    http_client: httpx.Client | None = None,
) -> dict[str, object]:
    """Observe one unique loaded LM Studio instance without generating model output."""

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=timeout_seconds)
    try:
        try:
            response = client.get(f"{base_url.rstrip('/')}/api/v1/models", headers=headers)
        except httpx.HTTPError as exc:
            raise CalibrationHostError(f"LM Studio native model probe failed: {exc}") from exc
        if not response.is_success:
            raise CalibrationHostError(
                f"LM Studio native model probe failed with status {response.status_code}"
            )
        try:
            envelope = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise CalibrationHostError("LM Studio native model probe is not valid JSON") from exc
    finally:
        if owns_client:
            client.close()

    root = _mapping(envelope, label="LM Studio models response")
    models = root.get("models")
    if not isinstance(models, list):
        raise CalibrationHostError("LM Studio models response must contain models array")
    matches = [
        item for item in models
        if isinstance(item, Mapping) and item.get("key") == model
    ]
    if len(matches) != 1:
        raise CalibrationHostError("LM Studio model key must resolve to exactly one model")
    model_entry = matches[0]
    loaded = model_entry.get("loaded_instances")
    if not isinstance(loaded, list) or len(loaded) != 1:
        raise CalibrationHostError("LM Studio model must have exactly one loaded instance")
    instance = _mapping(loaded[0], label="LM Studio loaded instance")
    instance_id = instance.get("id")
    if not isinstance(instance_id, str) or not instance_id.strip():
        raise CalibrationHostError("LM Studio loaded instance id must be non-empty")
    config = _mapping(instance.get("config"), label="LM Studio loaded instance config")
    context_length = config.get("context_length")
    if isinstance(context_length, bool) or not isinstance(context_length, int) or context_length <= 0:
        raise CalibrationHostError("LM Studio loaded context_length must be positive")

    capabilities = model_entry.get("capabilities")
    reasoning: object = None
    if isinstance(capabilities, Mapping):
        reasoning = capabilities.get("reasoning")

    return {
        "model": model,
        "model_instance_id": instance_id,
        "context_length": context_length,
        "runtime": {
            "architecture": model_entry.get("architecture"),
            "format": model_entry.get("format"),
            "quantization": model_entry.get("quantization"),
            "selected_variant": model_entry.get("selected_variant"),
            "reasoning_capability": reasoning,
        },
    }


class _BoundCalibrationClient:
    def __init__(
        self,
        *,
        client: CalibrationTransportClient,
        live_binding_probe: Callable[[], Mapping[str, object]],
        expected_binding: Mapping[str, object],
        evidence_path: Path,
        run_id: str,
        identity_fingerprint: str,
    ) -> None:
        self._client = client
        self._live_binding_probe = live_binding_probe
        self._expected_binding = expected_binding
        self._evidence_path = evidence_path
        self._run_id = run_id
        self._identity_fingerprint = identity_fingerprint
        self._plan = calibration_call_plan()
        self._index = 0

    @property
    def provider_attempts(self) -> int:
        return self._client.provider_attempts

    @property
    def provider_completions(self) -> int:
        return self._client.provider_completions

    @property
    def transport_identity(self) -> Mapping[str, object]:
        return self._client.transport_identity

    def complete_structured(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> ExperimentCompletion:
        if self._index >= len(self._plan):
            raise CalibrationHostError("calibration attempted an undeclared extra provider call")
        observed = self._live_binding_probe()
        if not isinstance(observed, Mapping):
            raise CalibrationHostError("live binding probe must return an object")
        _validate_live_binding(self._expected_binding, observed)

        question_id = self._plan[self._index]
        completion = self._client.complete_structured(
            messages,
            schema_name=schema_name,
            schema=schema,
        )
        _append_jsonl(
            self._evidence_path,
            {
                "run_id": self._run_id,
                "identity_fingerprint": self._identity_fingerprint,
                "order": self._index,
                "question_id": question_id,
                "response_id": completion.response_id,
                "input_tokens": completion.input_tokens,
                "output_tokens": completion.output_tokens,
                "content": completion.content,
                "classification": "instrumentation_only",
            },
        )
        self._index += 1
        return completion


def _initial_manifest(
    *,
    identity: Mapping[str, object],
    identity_fingerprint: str,
    run_id: str,
) -> dict[str, object]:
    return {
        "format_version": 1,
        "kind": "relaylm2_cognitive_ir_pre_s2_calibration",
        "run_id": run_id,
        "identity": _json_object(identity, label="frozen calibration identity"),
        "identity_fingerprint": identity_fingerprint,
        "claim_status": CALIBRATION_CLAIM_STATUS,
        "citable": False,
        "seeds": list(CALIBRATION_SEEDS),
        "difficulties": list(CALIBRATION_DIFFICULTIES),
        "probes": list(CALIBRATION_PROBES),
        "expected_provider_calls": len(calibration_call_plan()),
    }


def _state_mapping(
    *,
    run_id: str,
    identity_fingerprint: str,
    status: str,
    attempts: int,
    completions: int,
    failure: str | None = None,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "identity_fingerprint": identity_fingerprint,
        "status": status,
        "claim_status": CALIBRATION_CLAIM_STATUS,
        "citable": False,
        "provider_attempts": attempts,
        "provider_completions": completions,
        "next_call": completions,
        "failure": failure,
    }


def run_calibration_host(
    *,
    artifact_root: str | Path,
    identity: Mapping[str, object],
    repository_root: str | Path,
    live_binding_probe: Callable[[], Mapping[str, object]],
    client: CalibrationTransportClient,
) -> CalibrationHostResult:
    """Execute one fail-closed 72-call #2211 calibration transaction."""

    root = _prepare_artifact_root(artifact_root, repository_root)
    observed_repository = probe_calibration_git_repository(repository_root)
    _validate_repository(identity, observed_repository)
    live_fields = _validate_static_identity(identity, client)
    expected_binding = _expected_binding(identity, live_fields)

    preflight_binding = live_binding_probe()
    if not isinstance(preflight_binding, Mapping):
        raise CalibrationHostError("live binding probe must return an object")
    _validate_live_binding(expected_binding, preflight_binding)

    identity_fingerprint = _identity_fingerprint(identity)
    run_id = _run_id(identity_fingerprint)
    manifest_path = root / _MANIFEST_NAME
    state_path = root / _STATE_NAME
    evidence_path = root / _EVIDENCE_NAME
    result_path = root / _RESULT_NAME

    _write_json_exclusive(
        manifest_path,
        _initial_manifest(
            identity=identity,
            identity_fingerprint=identity_fingerprint,
            run_id=run_id,
        ),
    )
    _write_json_atomically(
        state_path,
        _state_mapping(
            run_id=run_id,
            identity_fingerprint=identity_fingerprint,
            status="RUNNING",
            attempts=client.provider_attempts,
            completions=client.provider_completions,
        ),
    )

    bound_client = _BoundCalibrationClient(
        client=client,
        live_binding_probe=live_binding_probe,
        expected_binding=expected_binding,
        evidence_path=evidence_path,
        run_id=run_id,
        identity_fingerprint=identity_fingerprint,
    )

    try:
        matrix = run_calibration_matrix(bound_client)
    except (CalibrationError, StructureProposalError, CalibrationHostError) as exc:
        _write_json_atomically(
            state_path,
            _state_mapping(
                run_id=run_id,
                identity_fingerprint=identity_fingerprint,
                status="INCOMPLETE",
                attempts=client.provider_attempts,
                completions=client.provider_completions,
                failure=f"{type(exc).__name__}: {exc}",
            ),
        )
        raise

    if client.provider_attempts != len(calibration_call_plan()):
        raise CalibrationHostError("completed calibration has wrong provider attempt count")
    if client.provider_completions != len(calibration_call_plan()):
        raise CalibrationHostError("completed calibration has wrong provider completion count")

    result = matrix.to_mapping()
    result.update(
        {
            "run_id": run_id,
            "identity_fingerprint": identity_fingerprint,
            "status": "COMPLETED",
            "provider_attempts": client.provider_attempts,
            "provider_completions": client.provider_completions,
        }
    )
    _write_json_exclusive(result_path, result)
    _write_json_atomically(
        state_path,
        _state_mapping(
            run_id=run_id,
            identity_fingerprint=identity_fingerprint,
            status="COMPLETED",
            attempts=client.provider_attempts,
            completions=client.provider_completions,
        ),
    )
    return CalibrationHostResult(
        run_id=run_id,
        identity_fingerprint=identity_fingerprint,
        status="COMPLETED",
        claim_status=matrix.claim_status,
        citable=matrix.citable,
        provider_attempts=client.provider_attempts,
        provider_completions=client.provider_completions,
        selected_difficulty=matrix.selected_difficulty,
        total_input_tokens=matrix.total_input_tokens,
        total_output_tokens=matrix.total_output_tokens,
    )


def build_default_lmstudio_calibration_client(
    *,
    base_url: str,
    model: str,
    api_key: str | None = None,
) -> OpenAICompatibleStructuredCalibrationClient:
    return OpenAICompatibleStructuredCalibrationClient(
        base_url=f"{base_url.rstrip('/')}/v1",
        model=model,
        api_key=api_key,
        timeout_seconds=300.0,
        max_tokens=128,
        temperature=0.0,
        seed=None,
    )
