from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Mapping, Protocol

from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import TransferFamily
from tools.v2_cognitive_ir_s2_host import (
    S2HostError,
    S2HostResult,
    run_s2_host_smoke,
)


class AttemptAwareExperimentClient(Protocol):
    provider_attempts: int
    provider_completions: int

    @property
    def transport_identity(self) -> Mapping[str, object]: ...

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion: ...


@dataclass(frozen=True, slots=True)
class S2HostV2Result:
    run_id: str
    identity_fingerprint: str
    status: str
    claim_status: str
    citable: bool
    provider_calls: int
    provider_attempts: int
    provider_completions: int
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
        raise S2HostError("S2 v2 transport identity must be canonical JSON") from exc


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise S2HostError(f"{label} must be an object")
    return value


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise S2HostError(f"cannot read S2 v2 artifact {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise S2HostError(f"S2 v2 artifact {path.name} must contain an object")
    return value


def _write_json_atomically(path: Path, value: Mapping[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.s2v2.tmp")
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
        raise S2HostError(f"cannot persist S2 v2 accounting: {exc}") from exc


def _validate_transport_contract(
    identity: Mapping[str, object],
    client: AttemptAwareExperimentClient,
) -> None:
    declared = _require_mapping(identity.get("transport"), label="S2 transport identity")
    observed = client.transport_identity
    if not isinstance(observed, Mapping):
        raise S2HostError("S2 client transport_identity must be an object")
    if _canonical_json(dict(declared)) != _canonical_json(dict(observed)):
        raise S2HostError("S2 client transport identity does not match frozen identity")

    timeout_seconds = declared.get("timeout_seconds")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise S2HostError("S2 transport timeout_seconds must be numeric")
    if timeout_seconds <= 0:
        raise S2HostError("S2 transport timeout_seconds must be positive")
    max_output_tokens = declared.get("max_output_tokens")
    if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int):
        raise S2HostError("S2 transport max_output_tokens must be an integer")
    if max_output_tokens <= 0:
        raise S2HostError("S2 transport max_output_tokens must be positive")
    if declared.get("reasoning") is None:
        raise S2HostError("S2 transport reasoning policy must be explicit")


def _persist_attempt_accounting(
    *,
    artifact_root: str | Path,
    attempts: int,
    completions: int,
) -> None:
    if attempts < 0 or completions < 0 or completions > attempts:
        raise S2HostError("S2 provider attempt/completion accounting is invalid")
    root = Path(artifact_root)
    state_path = root / "run-state.json"
    if state_path.exists():
        state = _load_json_object(state_path)
        legacy_calls = state.get("provider_calls")
        if isinstance(legacy_calls, bool) or not isinstance(legacy_calls, int):
            raise S2HostError("legacy S2 provider_calls must be an integer")
        if legacy_calls != completions:
            raise S2HostError(
                "legacy S2 provider_calls diverged from completed provider exchanges"
            )
        state["provider_attempts"] = attempts
        state["provider_completions"] = completions
        _write_json_atomically(state_path, state)

    result_path = root / "s2-smoke-result.json"
    if result_path.exists():
        result = _load_json_object(result_path)
        legacy_calls = result.get("provider_calls")
        if legacy_calls != completions:
            raise S2HostError(
                "completed S2 provider_calls diverged from provider completions"
            )
        result["provider_attempts"] = attempts
        result["provider_completions"] = completions
        accounting = result.get("cost_accounting")
        if not isinstance(accounting, dict):
            raise S2HostError("completed S2 cost_accounting must be an object")
        accounting["physical_provider_attempts"] = attempts
        accounting["physical_provider_completions"] = completions
        _write_json_atomically(result_path, result)


def _adapt_result(
    legacy: S2HostResult,
    *,
    attempts: int,
    completions: int,
) -> S2HostV2Result:
    if legacy.provider_calls != completions:
        raise S2HostError("S2 legacy result does not match provider completions")
    return S2HostV2Result(
        run_id=legacy.run_id,
        identity_fingerprint=legacy.identity_fingerprint,
        status=legacy.status,
        claim_status=legacy.claim_status,
        citable=legacy.citable,
        provider_calls=legacy.provider_calls,
        provider_attempts=attempts,
        provider_completions=completions,
        arm_correctness=legacy.arm_correctness,
        mechanical_classification=legacy.mechanical_classification,
        typed_generic_semantic_equal=legacy.typed_generic_semantic_equal,
    )


def run_s2_host_smoke_v2(
    *,
    artifact_root: str | Path,
    identity: Mapping[str, object],
    repository_root: str | Path,
    live_binding_probe,
    client: AttemptAwareExperimentClient,
    family: TransferFamily,
    step_index: int,
    examples_visible: int,
) -> S2HostV2Result:
    """Run #2211 S2 with explicit transport identity and truthful attempt accounting.

    The underlying S2 semantic protocol remains unchanged. This wrapper adds two
    execution-honesty requirements discovered by the first physical attempts:

    * the provider transport/reasoning/output bound is frozen in ``identity``;
    * a failed physical request is counted as work even when no completion arrives.

    Historical ``provider_calls`` keeps its legacy meaning of completed exchanges.
    New artifacts additionally expose ``provider_attempts`` and
    ``provider_completions`` so failed work cannot disappear from the ledger.
    """

    if not isinstance(identity, Mapping):
        raise S2HostError("frozen S2 v2 identity must be an object")
    _validate_transport_contract(identity, client)

    legacy: S2HostResult | None = None
    try:
        legacy = run_s2_host_smoke(
            artifact_root=artifact_root,
            identity=identity,
            repository_root=repository_root,
            live_binding_probe=live_binding_probe,
            client=client,
            family=family,
            step_index=step_index,
            examples_visible=examples_visible,
        )
    finally:
        _persist_attempt_accounting(
            artifact_root=artifact_root,
            attempts=client.provider_attempts,
            completions=client.provider_completions,
        )

    if legacy is None:
        raise AssertionError("S2 legacy host returned no result without raising")
    return _adapt_result(
        legacy,
        attempts=client.provider_attempts,
        completions=client.provider_completions,
    )
