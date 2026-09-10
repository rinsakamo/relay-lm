from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


TRANSACTION_FORMAT_VERSION = 1
DEFAULT_ORIGIN = "http://127.0.0.1:1234"
DEFAULT_API_BASE = f"{DEFAULT_ORIGIN}/v1"
DEFAULT_PORT = 1234
DEFAULT_CONTEXT = 8192
DEFAULT_SLOTS = 1
READY_TIMEOUT_SECONDS = 120.0
READY_POLL_SECONDS = 0.5
HOST_MODULE = "relaylm.actual_model_stage_r_llama_cpp"


class LlamaCppTransactionError(RuntimeError):
    """The one-command physical transaction could not proceed truthfully."""


def main(
    argv: Sequence[str] | None = None,
    *,
    host_module: str = HOST_MODULE,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Own one fresh llama-server lifetime around exactly one current "
            "RelayLM llama.cpp Stage R qualification host invocation."
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
        prefix="relaylm-stage-r-llama-cpp-workspace-",
    )
    artifact_root = _fresh_root(
        args.artifact_root,
        prefix="relaylm-stage-r-llama-cpp-artifacts-",
    )
    summary_path = (
        Path(args.summary_path).expanduser().resolve()
        if args.summary_path
        else artifact_root / "stage-r-llama-cpp-transaction-summary.json"
    )

    summary: dict[str, Any] = {
        "format_version": TRANSACTION_FORMAT_VERSION,
        "disposition": None,
        "classification": None,
        "repo_root": str(repo_root),
        "workspace_root": str(workspace_root),
        "artifact_root": str(artifact_root),
        "server_launch_count": 0,
        "host_invocation_count": 0,
        "semantic_retry_count": 0,
        "replay_count": 0,
        "fallback_count": 0,
        "fastcal_count": 0,
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

        origin = _require_loopback_origin(args.origin, args.port)
        api_base = f"{origin}/v1"
        summary["origin"] = origin
        summary["provider_base_url"] = api_base

        if not _port_is_free("127.0.0.1", args.port):
            summary["disposition"] = "MECHANICAL_PRECONDITION_BLOCKED"
            summary["phase"] = "port_ownership_gate"
            summary["listener_snapshot"] = _listener_snapshot(args.port)
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

        log_path = _new_server_log_path()
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
        host_result = _invoke_host(
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
            host_module=host_module,
        )
        summary["host"] = host_result
        host_summary = host_result["summary"]
        summary["classification"] = host_summary.get("classification")
        summary["disposition"] = "HOST_COMPLETED"
        summary["phase"] = "host_complete"
        exit_code = int(host_result["exit_code"])
        return exit_code
    except LlamaCppTransactionError as exc:
        if summary["host_invocation_count"] == 0:
            summary["disposition"] = "MECHANICAL_PRECONDITION_BLOCKED"
            summary["phase"] = summary.get("phase") or "mechanical_pre_host"
            exit_code = 3
        else:
            summary["disposition"] = "HARNESS_INVALID"
            summary["phase"] = "host_orchestration"
            exit_code = 2
        summary["error"] = f"{type(exc).__name__}: {exc}"
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
            summary["server"]["log_sha256"] = f"sha256:{_sha256_file(log_path)}"
        summary["transaction_exit_code"] = exit_code
        _write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


def _fresh_root(value: str | None, *, prefix: str) -> Path:
    if value:
        path = Path(value).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=False)
        return path
    return Path(tempfile.mkdtemp(prefix=prefix)).resolve()


def _require_clean_repo(repo_root: Path) -> None:
    if not (repo_root / ".git").exists():
        raise LlamaCppTransactionError(f"repo-root is not a git checkout: {repo_root}")
    status = _run_text(["git", "status", "--porcelain"], cwd=repo_root)
    if status.strip():
        raise LlamaCppTransactionError(
            "transaction requires a fresh clean RelayLM checkout"
        )


def _git_identity(repo_root: Path) -> tuple[str, str]:
    head = _run_text(["git", "rev-parse", "HEAD"], cwd=repo_root).strip()
    tree = _run_text(["git", "rev-parse", "HEAD^{tree}"], cwd=repo_root).strip()
    return head, tree


def _require_loopback_origin(origin: str, port: int) -> str:
    expected = f"http://127.0.0.1:{port}"
    if origin.rstrip("/") != expected:
        raise LlamaCppTransactionError(
            f"transaction origin must be exactly {expected}"
        )
    return expected


def _port_is_free(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _listener_snapshot(port: int) -> str | None:
    try:
        output = _run_text(["ss", "-ltnp"])
    except LlamaCppTransactionError:
        return None
    matches = [line for line in output.splitlines() if f":{port}" in line]
    return "\n".join(matches) or None


def _collect_llama_identity(
    *,
    llama_cpp_root: Path,
    server_binary: Path,
) -> tuple[str, str, int]:
    if not server_binary.is_file() or not os.access(server_binary, os.X_OK):
        raise LlamaCppTransactionError(
            f"llama-server is not executable: {server_binary}"
        )
    revision = _run_text(
        ["git", "rev-parse", "HEAD"],
        cwd=llama_cpp_root,
    ).strip()
    version = _run_text([str(server_binary), "--version"]).strip()
    match = re.search(r"\bbuild\s+(\d+)\b", version)
    if match is None:
        raise LlamaCppTransactionError(
            "could not parse llama-server build number from --version"
        )
    if not revision or not version:
        raise LlamaCppTransactionError("llama.cpp revision/version is empty")
    return revision, version, int(match.group(1))


def _collect_gpu_identity() -> str:
    output = _run_text(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total",
            "--format=csv,noheader",
        ]
    ).strip()
    if not output:
        raise LlamaCppTransactionError("nvidia-smi returned no GPU identity")
    return output


def _new_server_log_path() -> Path:
    root = Path.home() / "logs"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    return root / f"llama-server-{stamp}-{os.getpid()}.log"


def _start_server(
    *,
    server_binary: Path,
    artifact_path: Path,
    port: int,
    log_path: Path,
) -> tuple[subprocess.Popen[str], list[str]]:
    command = [
        str(server_binary),
        "-m",
        str(artifact_path),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-ngl",
        "999",
        "-c",
        str(DEFAULT_CONTEXT),
        "-np",
        str(DEFAULT_SLOTS),
        "--no-context-shift",
        "-lv",
        "4",
        "--log-timestamps",
        "--log-file",
        str(log_path),
    ]
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError as exc:
        raise LlamaCppTransactionError(
            f"failed to launch transaction-owned llama-server: {exc}"
        ) from exc
    return process, command


def _wait_until_ready(
    *,
    process: subprocess.Popen[str],
    origin: str,
) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise LlamaCppTransactionError(
                f"transaction-owned llama-server exited before readiness: {process.returncode}"
            )
        try:
            health = _get_json(f"{origin}/health", timeout=5.0)
            if isinstance(health, dict) and health.get("status") == "ok":
                return
        except Exception as exc:  # readiness polling is non-generative
            last_error = exc
        time.sleep(READY_POLL_SECONDS)
    detail = f": {last_error}" if last_error else ""
    raise LlamaCppTransactionError(
        f"transaction-owned llama-server did not become ready{detail}"
    )


def _probe_server(*, origin: str, api_base: str) -> dict[str, Any]:
    health = _get_json(f"{origin}/health", timeout=20.0)
    models = _get_json(f"{api_base}/models", timeout=20.0)
    props = _get_json(f"{origin}/props", timeout=20.0)
    slots = _get_json(f"{origin}/slots", timeout=20.0)
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise LlamaCppTransactionError("llama-server /health is not ready")
    request_models = _model_ids(models)
    if len(request_models) != 1:
        raise LlamaCppTransactionError(
            "transaction-owned single-model server must expose exactly one /v1/models id"
        )
    if not isinstance(props, dict):
        raise LlamaCppTransactionError("llama-server /props must return an object")
    if not isinstance(slots, list) or len(slots) != DEFAULT_SLOTS:
        raise LlamaCppTransactionError(
            "transaction-owned llama-server must expose exactly one /slots entry"
        )
    return {
        "request_model": request_models[0],
        "health": health,
        "props": props,
        "slot_count": len(slots),
        "non_generative_request_count": 4,
    }


def _model_ids(payload: Any) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise LlamaCppTransactionError("llama-server /v1/models response is invalid")
    result: list[str] = []
    for item in payload["data"]:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            result.append(item["id"])
    return result


def _get_json(url: str, *, timeout: float) -> Any:
    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LlamaCppTransactionError(f"GET {url} failed: {exc}") from exc


def _invoke_host(
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
    host_module: str = HOST_MODULE,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        host_module,
        "--repo-root",
        str(repo_root),
        "--provider-base-url",
        api_base,
        "--request-model",
        request_model,
        "--artifact-path",
        str(artifact_path),
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
        "--server-log-path",
        str(log_path),
        "--gpu-identity",
        gpu_identity,
        "--gpu-offload-args=-ngl 999",
        "--launch-args",
        shlex.join(launch_command),
        "--workspace-root",
        str(workspace_root),
        "--artifact-root",
        str(artifact_root),
        "--replicate-id",
        replicate_id,
    ]
    env = os.environ.copy()
    src_root = str(repo_root / "src")
    env["PYTHONPATH"] = (
        src_root
        if not env.get("PYTHONPATH")
        else src_root + os.pathsep + env["PYTHONPATH"]
    )
    completed = subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    stdout_path = artifact_root / "stage-r-llama-cpp-host-stdout.txt"
    stderr_path = artifact_root / "stage-r-llama-cpp-host-stderr.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")

    host_summary_path = artifact_root / "stage-r-llama-cpp-summary.json"
    if not host_summary_path.is_file():
        raise LlamaCppTransactionError(
            "citable Stage R host returned without its required summary artifact"
        )
    try:
        host_summary = json.loads(host_summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LlamaCppTransactionError(
            f"could not read citable Stage R host summary: {exc}"
        ) from exc
    if not isinstance(host_summary, dict):
        raise LlamaCppTransactionError("citable Stage R host summary is not an object")
    return {
        "exit_code": completed.returncode,
        "command": shlex.join(command),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "summary_path": str(host_summary_path),
        "summary": host_summary,
    }


def _terminate_owned_process(process: subprocess.Popen[str]) -> int | None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5.0)
    return process.returncode


def _run_text(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise LlamaCppTransactionError(
            f"command failed ({completed.returncode}): {shlex.join(command)}: {detail}"
        )
    return completed.stdout or completed.stderr


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
