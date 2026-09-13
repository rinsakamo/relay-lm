from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from relaylm.actual_model_stage_r_llama_cpp_transaction import (
    DEFAULT_CONTEXT,
    DEFAULT_ORIGIN,
    DEFAULT_PORT,
    DEFAULT_SLOTS,
    LlamaCppTransactionError,
    _collect_gpu_identity,
    _collect_llama_identity,
    _fresh_root,
    _git_identity,
    _new_server_log_path,
    _port_is_free,
    _probe_server,
    _require_clean_repo,
    _start_server,
    _terminate_owned_process,
    _wait_until_ready,
    _write_json,
)


TRANSACTION_FORMAT_VERSION = 1
HOST_MODULE = "relaylm.actual_model_crystallization_llama_cpp"
HOST_SUMMARY_FILENAME = "crystallization-llama-cpp-summary.json"
TRANSACTION_SUMMARY_FILENAME = "crystallization-llama-cpp-transaction-summary.json"
WORKSPACE_PREFIX = "relaylm-crystallization-llama-cpp-workspace-"
ARTIFACT_PREFIX = "relaylm-crystallization-llama-cpp-artifacts-"
EXPECTED_ORIGIN = DEFAULT_ORIGIN
EXPECTED_PORT = DEFAULT_PORT


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Own one fresh llama-server lifetime around exactly one current "
            "off-turn crystallization host invocation."
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
    parser.add_argument("--origin", default=EXPECTED_ORIGIN)
    parser.add_argument("--port", type=int, default=EXPECTED_PORT)
    parser.add_argument("--workspace-root")
    parser.add_argument("--artifact-root")
    parser.add_argument("--summary-path")
    parser.add_argument("--replicate-id", default="0")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    llama_cpp_root = Path(args.llama_cpp_root).expanduser().resolve()
    artifact_path = Path(args.artifact_path).expanduser().resolve()
    workspace_root = _fresh_root(
        args.workspace_root,
        prefix=WORKSPACE_PREFIX,
    )
    artifact_root = _fresh_root(
        args.artifact_root,
        prefix=ARTIFACT_PREFIX,
    )
    summary_path = (
        Path(args.summary_path).expanduser().resolve()
        if args.summary_path
        else artifact_root / TRANSACTION_SUMMARY_FILENAME
    )
    host_summary_path = artifact_root / HOST_SUMMARY_FILENAME

    summary: dict[str, Any] = {
        "format_version": TRANSACTION_FORMAT_VERSION,
        "suite": "actual-model-crystallization-llama-cpp-transaction-v1",
        "disposition": None,
        "classification": None,
        "repo_root": str(repo_root),
        "workspace_root": str(workspace_root),
        "artifact_root": str(artifact_root),
        "server_launch_count": 0,
        "host_invocation_count": 0,
        "provider_request_count": 0,
        "crystallization_generation_count": 0,
        "input_counter_request_count": 0,
        "semantic_retry_count": 0,
        "replay_count": 0,
        "fallback_count": 0,
        "fastcal_count": 0,
        "stage_r_generation_count": 0,
        "lm_studio_contact_count": 0,
        "repository_mutation_count": 0,
    }
    process: subprocess.Popen[str] | None = None
    log_path: Path | None = None
    exit_code = 2

    try:
        _require_clean_repo(repo_root)
        head, tree = _git_identity(repo_root)
        summary["relaylm"] = {"head": head, "tree": tree}

        origin = _require_current_origin(args.origin, args.port)
        api_base = f"{origin}/v1"
        summary["origin"] = origin
        summary["provider_base_url"] = api_base

        if not _port_is_free("127.0.0.1", args.port):
            summary["disposition"] = "MECHANICAL_PRECONDITION_BLOCKED"
            summary["phase"] = "port_ownership_gate"
            exit_code = 3
            return exit_code

        server_binary = llama_cpp_root / "build" / "bin" / "llama-server"
        revision, version, build = _collect_llama_identity(
            llama_cpp_root=llama_cpp_root,
            server_binary=server_binary,
        )
        if not artifact_path.is_file():
            raise LlamaCppTransactionError(
                f"canonical GGUF is not a file: {artifact_path}"
            )
        gpu_identity = _collect_gpu_identity()
        log_path = _new_server_log_path(artifact_root=artifact_root)
        process, launch_command = _start_server(
            server_binary=server_binary,
            artifact_path=artifact_path,
            port=args.port,
            log_path=log_path,
        )
        summary["server_launch_count"] = 1
        summary["server"] = {
            "pid": process.pid,
            "binary": str(server_binary),
            "llama_cpp_root": str(llama_cpp_root),
            "revision": revision,
            "version": version,
            "build_number": build,
            "launch_command": shlex.join(launch_command),
            "log_path": str(log_path),
            "gpu_identity": gpu_identity,
        }

        _wait_until_ready(process=process, origin=origin)
        probe = _probe_server(origin=origin, api_base=api_base)
        request_model = probe["request_model"]
        summary["pre_host_probe"] = probe
        if not log_path.is_file():
            raise LlamaCppTransactionError(
                "transaction-owned llama-server did not create its log file"
            )

        summary["host_invocation_count"] = 1
        host_result = _invoke_crystallization_host(
            repo_root=repo_root,
            api_base=api_base,
            request_model=request_model,
            artifact_path=artifact_path,
            revision=revision,
            version=version,
            build=build,
            gpu_identity=gpu_identity,
            launch_command=launch_command,
            log_path=log_path,
            workspace_root=workspace_root,
            artifact_root=artifact_root,
            replicate_id=args.replicate_id,
            host_summary_path=host_summary_path,
        )
        summary["host"] = host_result
        host_summary = host_result["summary"]
        summary["classification"] = host_summary.get("classification")
        for key in (
            "provider_request_count",
            "crystallization_generation_count",
            "input_counter_request_count",
        ):
            value = host_summary.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                summary[key] = value
        summary["disposition"] = (
            "HOST_COMPLETED" if host_result["exit_code"] == 0 else "HARNESS_INVALID"
        )
        summary["phase"] = "host_complete"
        exit_code = int(host_result["exit_code"])
        return exit_code
    except LlamaCppTransactionError as exc:
        summary["disposition"] = (
            "MECHANICAL_PRECONDITION_BLOCKED"
            if summary["host_invocation_count"] == 0
            else "HARNESS_INVALID"
        )
        summary["phase"] = summary.get("phase") or "mechanical_pre_host"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 3 if summary["host_invocation_count"] == 0 else 2
        return exit_code
    except Exception as exc:  # pragma: no cover - final fail-closed boundary
        summary["disposition"] = "HARNESS_INVALID"
        summary["phase"] = "unexpected_exception"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 2
        return exit_code
    finally:
        if process is not None:
            summary["server"]["exit_code"] = _terminate_owned_process(process)
            summary["server"]["terminated"] = process.poll() is not None
        if log_path is not None and log_path.is_file():
            from relaylm.actual_model_stage_r_llama_cpp_transaction import _sha256_file

            summary["server"]["log_sha256"] = f"sha256:{_sha256_file(log_path)}"
        summary["transaction_exit_code"] = exit_code
        _write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


def _require_current_origin(origin: str, port: int) -> str:
    if port != EXPECTED_PORT or origin.rstrip("/") != EXPECTED_ORIGIN:
        raise LlamaCppTransactionError(
            f"off-turn crystallization transaction origin must be {EXPECTED_ORIGIN}"
        )
    return EXPECTED_ORIGIN


def _invoke_crystallization_host(
    *,
    repo_root: Path,
    api_base: str,
    request_model: str,
    artifact_path: Path,
    revision: str,
    version: str,
    build: int,
    gpu_identity: str,
    launch_command: list[str],
    log_path: Path,
    workspace_root: Path,
    artifact_root: Path,
    replicate_id: str,
    host_summary_path: Path,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        HOST_MODULE,
        "--repo-root",
        str(repo_root),
        "--provider-base-url",
        api_base,
        "--request-model",
        request_model,
        "--artifact-path",
        str(artifact_path),
        "--target-path",
        "evaluation/actual_model/targets/gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json",
        "--llama-upstream-revision",
        revision,
        "--llama-version",
        version,
        "--expected-build-number",
        str(build),
        "--expected-context-window",
        str(DEFAULT_CONTEXT),
        "--expected-slots",
        str(DEFAULT_SLOTS),
        "--context-shift-disabled",
        "--gpu-identity",
        gpu_identity,
        "--gpu-offload-args=-ngl 999",
        "--launch-args",
        shlex.join(launch_command),
        "--server-log-path",
        str(log_path),
        "--workspace-root",
        str(workspace_root),
        "--artifact-root",
        str(artifact_root),
        "--replicate-id",
        replicate_id,
    ]
    environment = os.environ.copy()
    source_root = str(repo_root / "src")
    inherited_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_root
        if not inherited_pythonpath
        else source_root + os.pathsep + inherited_pythonpath
    )
    completed = subprocess.run(
        command,
        cwd=repo_root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    stdout_path = artifact_root / "crystallization-llama-cpp-host-stdout.txt"
    stderr_path = artifact_root / "crystallization-llama-cpp-host-stderr.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    if host_summary_path.parent.resolve() != artifact_root.resolve():
        raise LlamaCppTransactionError(
            "crystallization host summary must remain directly inside artifact root"
        )
    if not host_summary_path.is_file():
        raise LlamaCppTransactionError(
            "crystallization host returned without its declared summary artifact"
        )
    try:
        host_summary = json.loads(host_summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LlamaCppTransactionError(
            f"could not read crystallization host summary: {exc}"
        ) from exc
    if not isinstance(host_summary, dict):
        raise LlamaCppTransactionError("crystallization host summary is not an object")
    return {
        "exit_code": completed.returncode,
        "command": shlex.join(command),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "summary_path": str(host_summary_path),
        "summary": host_summary,
    }


if __name__ == "__main__":
    raise SystemExit(main())
