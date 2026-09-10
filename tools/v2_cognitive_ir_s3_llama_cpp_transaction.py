from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from typing import Any, TextIO

from relaylm.v2_cognitive_ir_s3 import (
    S3_CLAIM,
    S3_INCOMPLETE_CLAIM,
    S3_PREREGISTRATION_SHA256,
    S3_REGIMES,
    S3_TOTAL_INPUT_TOKEN_REQUESTS,
    S3_TOTAL_SEMANTIC_CALLS,
    run_s3_shard,
    s3_call_plan,
    semantic_invariance_gate,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from tools.v2_cognitive_ir_s2_selected_llama_cpp import (
    probe_llama_cpp_selected_s2_binding,
)
from tools.v2_cognitive_ir_s2_selected_llama_cpp_transaction import (
    DEFAULT_ORIGIN,
    DEFAULT_PORT,
    SelectedS2TransactionError,
    _acquire_lifecycle_lock,
    _collect_gpu_identity,
    _collect_llama_identity,
    _controller_identity,
    _git_identity,
    _launch_command,
    _port_is_free,
    _probe_server,
    _release_lifecycle_lock,
    _require_clean_repo,
    _require_server_flags,
    _sha256_file,
    _start_server,
    _terminate_owned_process,
    _verify_reasoning_effort_none_semantics,
    _wait_until_ready,
    _write_json,
)
from tools.v2_cognitive_ir_s3_llama_cpp import (
    S3LlamaCppClient,
    S3_LLAMA_CPP_ENDPOINT,
    S3_LLAMA_CPP_MAX_OUTPUT_TOKENS,
    S3_LLAMA_CPP_REASONING_EFFORT,
    S3_LLAMA_CPP_TIMEOUT_SECONDS,
)


TRANSACTION_FORMAT_VERSION = 1
DEFAULT_SHARED_LOCK_PATH = Path(
    "/tmp/relaylm/locks/llama-server-127.0.0.1-1234.lock"
)
_LIGHT_PROBE_FIELDS = (
    "request_model",
    "build_info",
    "model_path",
    "model_ftype",
    "context",
    "slot_count",
    "slot_contexts",
)


class S3TransactionError(RuntimeError):
    """The frozen #2211 S3 physical campaign cannot proceed truthfully."""


class _BoundS3Client:
    """Perform a lightweight live-binding check before every semantic call.

    Full binary/GGUF SHA-256 attestation is deliberately performed at shard
    boundaries by the transaction harness. Rehashing a multi-gigabyte GGUF on
    every one of the 498 semantic calls would turn material attestation into the
    dominant experimental workload. The per-call probe instead checks the owned
    process plus /health, /v1/models, /props, /slots and material stat identity.
    """

    def __init__(
        self,
        *,
        inner: S3LlamaCppClient,
        live_binding_probe: Callable[[], None],
    ) -> None:
        self.inner = inner
        self._live_binding_probe = live_binding_probe
        self.live_binding_checks = 0

    @property
    def provider_attempts(self) -> int:
        return self.inner.provider_attempts

    @property
    def provider_completions(self) -> int:
        return self.inner.provider_completions

    @property
    def input_count_attempts(self) -> int:
        return self.inner.input_count_attempts

    @property
    def input_count_completions(self) -> int:
        return self.inner.input_count_completions

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        self._live_binding_probe()
        self.live_binding_checks += 1
        return self.inner.complete_named(
            question_id,
            messages,
            output_kind=output_kind,
        )


def _fresh_artifact_root(value: str | None) -> Path:
    if value:
        path = Path(value).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=False)
        return path
    return Path(
        tempfile.mkdtemp(prefix="relaylm-v2-2211-s3-llama-cpp-artifacts-")
    ).resolve()


def _new_s3_log_path(regime: str) -> Path:
    root = Path.home() / "logs"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    path = root / f"relaylm-v2-2211-s3-{regime}-{stamp}-{os.getpid()}.log"
    if path.exists():
        raise S3TransactionError(f"fresh S3 server log already exists: {path}")
    return path


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _material_stat(path: Path) -> dict[str, int]:
    try:
        stat = path.stat()
    except OSError as exc:
        raise S3TransactionError(f"cannot stat S3 material {path}: {exc}") from exc
    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "inode": stat.st_ino,
        "device": stat.st_dev,
    }


def _lightweight_binding_check(
    *,
    process: subprocess.Popen[str],
    expected_probe: Mapping[str, object],
    server_binary: Path,
    expected_binary_stat: Mapping[str, int],
    artifact_path: Path,
    expected_artifact_stat: Mapping[str, int],
) -> None:
    if process.poll() is not None:
        raise S3TransactionError(
            "transaction-owned llama-server exited before S3 semantic call"
        )
    observed = _probe_server(
        origin=DEFAULT_ORIGIN,
        api_base=S3_LLAMA_CPP_ENDPOINT,
        artifact_path=artifact_path,
    )
    for field in _LIGHT_PROBE_FIELDS:
        if _canonical(observed.get(field)) != _canonical(expected_probe.get(field)):
            raise S3TransactionError(f"S3 live binding drift before provider call: {field}")
    if _material_stat(server_binary) != dict(expected_binary_stat):
        raise S3TransactionError("llama-server material stat changed during S3 shard")
    if _material_stat(artifact_path) != dict(expected_artifact_stat):
        raise S3TransactionError("GGUF material stat changed during S3 shard")


def _runtime_material(
    *,
    revision: str,
    version: str,
    binary_sha256: str,
    artifact_sha256: str,
    gpu_identity: Mapping[str, str],
    probe: Mapping[str, object],
    attested: Mapping[str, object],
) -> dict[str, object]:
    return {
        "llama_cpp_revision": revision,
        "llama_cpp_version": version,
        "binary_sha256": binary_sha256,
        "artifact_sha256": artifact_sha256,
        "gpu": dict(gpu_identity),
        "request_model": probe["request_model"],
        "build_info": probe["build_info"],
        "model_path": probe["model_path"],
        "model_ftype": probe.get("model_ftype"),
        "context": probe["context"],
        "slot_count": probe["slot_count"],
        "slot_contexts": probe["slot_contexts"],
        "runtime_attestation": dict(attested),
        "reasoning_effort": S3_LLAMA_CPP_REASONING_EFFORT,
        "temperature": 0.0,
        "seed": None,
        "max_output_tokens": S3_LLAMA_CPP_MAX_OUTPUT_TOKENS,
        "timeout_seconds": S3_LLAMA_CPP_TIMEOUT_SECONDS,
    }


def _fingerprint(
    repo: Mapping[str, object], runtime: Mapping[str, object]
) -> tuple[str, str]:
    payload = [
        "relaylm2-cognitive-ir-s3-identity-v1",
        S3_PREREGISTRATION_SHA256,
        dict(repo),
        dict(runtime),
    ]
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}", f"s3-{digest}"


def _sum_work(shards: list[Mapping[str, object]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for shard in shards:
        work = shard.get("work")
        if not isinstance(work, Mapping):
            continue
        for key, value in work.items():
            if isinstance(value, int) and not isinstance(value, bool):
                totals[str(key)] = totals.get(str(key), 0) + value
    return totals


def _pooled_effect(shards: list[Mapping[str, object]], key: str) -> float:
    values = [float(shard[key]) for shard in shards]
    if len(values) != len(S3_REGIMES):
        raise S3TransactionError("cannot pool incomplete S3 shard effects")
    return sum(values) / len(values)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Execute the frozen #2211 S3 semantic-invariance campaign with exactly "
            "four ordered one-server shard lifetimes and no retry."
        )
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--llama-cpp-root",
        default=str(Path.home() / "src" / "llama.cpp"),
    )
    parser.add_argument(
        "--artifact-path",
        default=str(
            Path.home()
            / "models"
            / "gguf"
            / "gemma-4-12B-it-Q4_K_M.gguf"
        ),
    )
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--artifact-root")
    parser.add_argument("--summary-path")
    parser.add_argument("--lock-path", default=str(DEFAULT_SHARED_LOCK_PATH))
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    llama_cpp_root = Path(args.llama_cpp_root).expanduser().resolve()
    artifact_path = Path(args.artifact_path).expanduser().resolve()
    artifact_root = _fresh_artifact_root(args.artifact_root)
    summary_path = (
        Path(args.summary_path).expanduser().resolve()
        if args.summary_path
        else artifact_root / "s3-llama-cpp-transaction-summary.json"
    )
    lock_path = Path(args.lock_path).expanduser().resolve()

    summary: dict[str, Any] = {
        "format_version": TRANSACTION_FORMAT_VERSION,
        "preregistration_sha256": S3_PREREGISTRATION_SHA256,
        "claim": S3_INCOMPLETE_CLAIM,
        "citable": False,
        "architecture_consequence": "NONE",
        "disposition": None,
        "classification": None,
        "artifact_root": str(artifact_root),
        "shard_order": list(S3_REGIMES),
        "planned_semantic_calls": S3_TOTAL_SEMANTIC_CALLS,
        "planned_input_token_requests": S3_TOTAL_INPUT_TOKEN_REQUESTS,
        "server_launch_count": 0,
        "host_shard_count": 0,
        "full_material_attestation_count": 0,
        "lightweight_live_binding_check_count": 0,
        "provider_attempts": 0,
        "provider_completions": 0,
        "input_count_attempts": 0,
        "input_count_completions": 0,
        "retry_count": 0,
        "replay_count": 0,
        "reseed_count": 0,
        "fallback_count": 0,
        "lm_studio_contact_count": 0,
        "repository_mutation_count": 0,
        "s2_rerun_count": 0,
    }
    lock_handle: TextIO | None = None
    runtime_frozen: dict[str, object] | None = None
    shard_summaries: list[dict[str, object]] = []
    exit_code = 2

    try:
        _require_clean_repo(repo_root)
        head, tree = _git_identity(repo_root)
        repo_identity = {"commit": head, "tree": tree, "clean": True}
        summary["repository"] = repo_identity
        if args.origin.rstrip("/") != DEFAULT_ORIGIN or args.port != DEFAULT_PORT:
            raise S3TransactionError(
                f"S3 endpoint must be exactly {DEFAULT_ORIGIN}/v1"
            )
        if S3_LLAMA_CPP_ENDPOINT != f"{DEFAULT_ORIGIN}/v1":
            raise AssertionError("S3 transport endpoint drifted from physical transaction")
        if not artifact_path.is_file():
            raise S3TransactionError(f"canonical GGUF is not a file: {artifact_path}")

        lock_handle = _acquire_lifecycle_lock(lock_path)
        summary["lock"] = {"path": str(lock_path), "acquired": True}
        if not _port_is_free("127.0.0.1", args.port):
            raise S3TransactionError("127.0.0.1:1234 is occupied before S3 campaign")

        server_binary = llama_cpp_root / "build" / "bin" / "llama-server"
        revision, version = _collect_llama_identity(
            llama_cpp_root=llama_cpp_root,
            server_binary=server_binary,
        )
        _require_server_flags(server_binary)
        _verify_reasoning_effort_none_semantics(
            llama_cpp_root=llama_cpp_root,
            revision=revision,
        )
        binary_sha256 = _sha256_file(server_binary)
        artifact_sha256 = _sha256_file(artifact_path)
        binary_stat = _material_stat(server_binary)
        artifact_stat = _material_stat(artifact_path)
        gpu_identity = _collect_gpu_identity()

        for regime in S3_REGIMES:
            if not _port_is_free("127.0.0.1", args.port):
                raise S3TransactionError(
                    f"port 1234 became occupied before planned {regime} shard"
                )
            log_path = _new_s3_log_path(regime)
            launch_command = _launch_command(
                server_binary=server_binary,
                artifact_path=artifact_path,
                port=args.port,
                log_path=log_path,
            )
            process: subprocess.Popen[str] | None = None
            client: S3LlamaCppClient | None = None
            shard_summary: dict[str, object] = {
                "regime": regime,
                "status": "INCOMPLETE",
                "log_path": str(log_path),
                "planned_semantic_calls": len(s3_call_plan(regime)),
                "full_material_attestations": 0,
                "lightweight_live_binding_checks": 0,
            }
            try:
                process = _start_server(launch_command)
                summary["server_launch_count"] += 1
                shard_summary["server_pid"] = process.pid
                shard_summary["launch_command"] = shlex.join(launch_command)
                _wait_until_ready(process=process, origin=DEFAULT_ORIGIN)
                probe = _probe_server(
                    origin=DEFAULT_ORIGIN,
                    api_base=S3_LLAMA_CPP_ENDPOINT,
                    artifact_path=artifact_path,
                )
                controller = _controller_identity(
                    revision=revision,
                    build_info=str(probe["build_info"]),
                    server_binary=server_binary,
                    binary_sha256=binary_sha256,
                    artifact_path=artifact_path,
                    artifact_sha256=artifact_sha256,
                    launch_command=launch_command,
                    process=process,
                    log_path=log_path,
                    gpu_identity=gpu_identity,
                    probe=probe,
                )
                request_model = str(probe["request_model"])

                start_binding = probe_llama_cpp_selected_s2_binding(
                    base_url=S3_LLAMA_CPP_ENDPOINT,
                    model=request_model,
                    controller_identity=controller,
                )
                summary["full_material_attestation_count"] += 1
                shard_summary["full_material_attestations"] = 1
                attested = start_binding.get("runtime_attestation")
                if not isinstance(attested, Mapping):
                    raise S3TransactionError(
                        "S3 live runtime attestation is not an object"
                    )
                material = _runtime_material(
                    revision=revision,
                    version=version,
                    binary_sha256=binary_sha256,
                    artifact_sha256=artifact_sha256,
                    gpu_identity=gpu_identity,
                    probe=probe,
                    attested=attested,
                )
                if runtime_frozen is None:
                    runtime_frozen = material
                    fingerprint, run_id = _fingerprint(repo_identity, runtime_frozen)
                    summary["identity_fingerprint"] = fingerprint
                    summary["run_id"] = run_id
                    summary["runtime_material"] = runtime_frozen
                elif _canonical(material) != _canonical(runtime_frozen):
                    raise S3TransactionError(
                        "runtime/material drift across S3 shard lifetimes"
                    )

                client = S3LlamaCppClient(
                    base_url=S3_LLAMA_CPP_ENDPOINT,
                    model=request_model,
                    call_plan=s3_call_plan(regime),
                    timeout_seconds=S3_LLAMA_CPP_TIMEOUT_SECONDS,
                    max_output_tokens=S3_LLAMA_CPP_MAX_OUTPUT_TOKENS,
                    temperature=0.0,
                    seed=None,
                )

                def live_binding_probe() -> None:
                    if process is None:
                        raise AssertionError("S3 owned process is unavailable")
                    _lightweight_binding_check(
                        process=process,
                        expected_probe=probe,
                        server_binary=server_binary,
                        expected_binary_stat=binary_stat,
                        artifact_path=artifact_path,
                        expected_artifact_stat=artifact_stat,
                    )

                bound = _BoundS3Client(
                    inner=client,
                    live_binding_probe=live_binding_probe,
                )
                summary["host_shard_count"] += 1
                result = run_s3_shard(bound, regime)
                client.require_complete_plan()
                if bound.live_binding_checks != result.semantic_calls:
                    raise S3TransactionError(
                        "S3 lightweight live binding was not checked before every semantic call"
                    )
                shard_summary["lightweight_live_binding_checks"] = (
                    bound.live_binding_checks
                )
                summary["lightweight_live_binding_check_count"] += (
                    bound.live_binding_checks
                )

                end_binding = probe_llama_cpp_selected_s2_binding(
                    base_url=S3_LLAMA_CPP_ENDPOINT,
                    model=request_model,
                    controller_identity=controller,
                )
                summary["full_material_attestation_count"] += 1
                shard_summary["full_material_attestations"] = 2
                if _canonical(end_binding) != _canonical(start_binding):
                    raise S3TransactionError(
                        "full runtime/material binding drifted within S3 shard"
                    )
                if _material_stat(server_binary) != binary_stat:
                    raise S3TransactionError(
                        "llama-server material stat drifted across S3 shard"
                    )
                if _material_stat(artifact_path) != artifact_stat:
                    raise S3TransactionError("GGUF material stat drifted across S3 shard")

                shard_summary.update(asdict(result))
                shard_summary["status"] = "COMPLETED"
                shard_summary["provider_attempts"] = client.provider_attempts
                shard_summary["provider_completions"] = client.provider_completions
                shard_summary["input_count_attempts"] = client.input_count_attempts
                shard_summary["input_count_completions"] = (
                    client.input_count_completions
                )
            except Exception as exc:
                shard_summary["error"] = f"{type(exc).__name__}: {exc}"
                if client is not None:
                    shard_summary["provider_attempts"] = client.provider_attempts
                    shard_summary["provider_completions"] = (
                        client.provider_completions
                    )
                    shard_summary["input_count_attempts"] = (
                        client.input_count_attempts
                    )
                    shard_summary["input_count_completions"] = (
                        client.input_count_completions
                    )
                shard_summaries.append(shard_summary)
                summary["classification"] = "S3_INCOMPLETE"
                summary["disposition"] = f"STOPPED_AT_{regime.upper()}"
                exit_code = 2
                break
            finally:
                if client is not None:
                    client.close()
                if process is not None:
                    shard_summary["cleanup"] = _terminate_owned_process(process)
                if log_path.is_file():
                    shard_summary["log_sha256"] = _sha256_file(log_path)
                    shard_summary["log_bytes"] = log_path.stat().st_size
                if not _port_is_free("127.0.0.1", args.port):
                    shard_summary["listener_released"] = False
                    if shard_summary.get("status") == "COMPLETED":
                        shard_summary["status"] = "INCOMPLETE"
                        shard_summary["error"] = (
                            "transaction-owned listener remained after cleanup"
                        )
                else:
                    shard_summary["listener_released"] = True

            if shard_summary not in shard_summaries:
                shard_summaries.append(shard_summary)
            if shard_summary.get("status") != "COMPLETED":
                summary["classification"] = "S3_INCOMPLETE"
                summary["disposition"] = f"STOPPED_AT_{regime.upper()}"
                exit_code = 2
                break
            shard_path = artifact_root / f"s3-shard-{regime}.json"
            _write_json(shard_path, shard_summary)
            shard_summary["artifact_path"] = str(shard_path)
            shard_summary["artifact_sha256"] = _sha256_file(shard_path)
        else:
            surface = _pooled_effect(
                shard_summaries,
                "surface_perturbation_effect",
            )
            semantic = _pooled_effect(
                shard_summaries,
                "semantic_intervention_effect",
            )
            gate = semantic_invariance_gate(surface, semantic)
            summary["pooled_surface_perturbation_effect"] = surface
            summary["pooled_semantic_intervention_effect"] = semantic
            summary["semantic_invariance_gate"] = gate
            summary["work"] = _sum_work(shard_summaries)
            summary["provider_attempts"] = sum(
                int(item["provider_attempts"]) for item in shard_summaries
            )
            summary["provider_completions"] = sum(
                int(item["provider_completions"]) for item in shard_summaries
            )
            summary["input_count_attempts"] = sum(
                int(item["input_count_attempts"]) for item in shard_summaries
            )
            summary["input_count_completions"] = sum(
                int(item["input_count_completions"])
                for item in shard_summaries
            )
            if summary["provider_attempts"] != S3_TOTAL_SEMANTIC_CALLS:
                raise S3TransactionError(
                    "completed S3 campaign semantic call total drifted"
                )
            if summary["provider_completions"] != S3_TOTAL_SEMANTIC_CALLS:
                raise S3TransactionError(
                    "completed S3 campaign completion total drifted"
                )
            if summary["input_count_attempts"] != S3_TOTAL_INPUT_TOKEN_REQUESTS:
                raise S3TransactionError(
                    "completed S3 campaign input-token request total drifted"
                )
            if (
                summary["input_count_completions"]
                != S3_TOTAL_INPUT_TOKEN_REQUESTS
            ):
                raise S3TransactionError(
                    "completed S3 input-token completion total drifted"
                )
            if summary["lightweight_live_binding_check_count"] != S3_TOTAL_SEMANTIC_CALLS:
                raise S3TransactionError(
                    "completed S3 per-call lightweight binding count drifted"
                )
            if summary["full_material_attestation_count"] != 2 * len(S3_REGIMES):
                raise S3TransactionError(
                    "completed S3 shard-boundary full material attestation count drifted"
                )
            summary["claim"] = S3_CLAIM
            summary["citable"] = True
            summary["classification"] = "S3_COMPLETED"
            summary["disposition"] = "ALL_SHARDS_COMPLETED"
            summary["candidate_verdict"] = "UNDERDETERMINED"
            exit_code = 0

        if summary["provider_attempts"] == 0:
            summary["provider_attempts"] = sum(
                int(item.get("provider_attempts", 0))
                for item in shard_summaries
            )
            summary["provider_completions"] = sum(
                int(item.get("provider_completions", 0))
                for item in shard_summaries
            )
            summary["input_count_attempts"] = sum(
                int(item.get("input_count_attempts", 0))
                for item in shard_summaries
            )
            summary["input_count_completions"] = sum(
                int(item.get("input_count_completions", 0))
                for item in shard_summaries
            )
        return exit_code
    except (S3TransactionError, SelectedS2TransactionError) as exc:
        summary["classification"] = "S3_INCOMPLETE"
        summary["disposition"] = summary.get("disposition") or "EXECUTION_BLOCKED"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 3 if summary["host_shard_count"] == 0 else 2
        return exit_code
    except Exception as exc:  # pragma: no cover - final fail-closed boundary
        summary["classification"] = "S3_INCOMPLETE"
        summary["disposition"] = summary.get("disposition") or "UNEXPECTED_FAILURE"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 3 if summary["host_shard_count"] == 0 else 2
        return exit_code
    finally:
        summary["shards"] = shard_summaries
        summary["transaction_exit_code"] = exit_code
        _write_json(summary_path, summary)
        print(_canonical(summary))
        if lock_handle is not None:
            _release_lifecycle_lock(lock_handle)


if __name__ == "__main__":
    raise SystemExit(main())
