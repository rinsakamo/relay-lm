from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

import httpx

from tools.v2_cognitive_ir_s2_host import S2HostError
from tools.v2_cognitive_ir_s2_selected_llama_cpp import (
    S2_SELECTED_LLAMA_CPP_CONTEXT_LENGTH,
    S2_SELECTED_LLAMA_CPP_ENDPOINT,
    run_llama_cpp_selected_s2_transaction,
)


TRANSACTION_FORMAT_VERSION = 1
DEFAULT_ORIGIN = "http://127.0.0.1:1234"
DEFAULT_PORT = 1234
DEFAULT_SLOTS = 1
READY_TIMEOUT_SECONDS = 1800.0
READY_POLL_SECONDS = 0.5
LOCK_TIMEOUT_SECONDS = 7200.0


class SelectedS2TransactionError(RuntimeError):
    """The one-command selected-S2 transaction cannot proceed truthfully."""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Own one fresh llama-server lifetime around at most one RelayLM 2.0 "
            "#2211 selected-S2 host invocation."
        )
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--llama-cpp-root", default=str(Path.home() / "src" / "llama.cpp")
    )
    parser.add_argument(
        "--artifact-path",
        default=str(
            Path.home() / "models" / "gguf" / "gemma-4-12B-it-Q4_K_M.gguf"
        ),
    )
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--artifact-root")
    parser.add_argument("--summary-path")
    parser.add_argument("--lock-path")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    llama_cpp_root = Path(args.llama_cpp_root).expanduser().resolve()
    artifact_path = Path(args.artifact_path).expanduser().resolve()
    artifact_root = _fresh_root(
        args.artifact_root, prefix="relaylm-v2-2211-s2-llama-cpp-artifacts-"
    )
    summary_path = (
        Path(args.summary_path).expanduser().resolve()
        if args.summary_path
        else artifact_root / "s2-selected-llama-cpp-transaction-summary.json"
    )
    lock_path = (
        Path(args.lock_path).expanduser().resolve()
        if args.lock_path
        else Path.home()
        / ".cache"
        / "relaylm"
        / "llama-server-127.0.0.1-1234.lock"
    )

    summary: dict[str, Any] = {
        "format_version": TRANSACTION_FORMAT_VERSION,
        "claim": "NON_CITABLE_S2_SMOKE",
        "citable": False,
        "architecture_consequence": "NONE",
        "s3_executed": False,
        "disposition": None,
        "classification": None,
        "repo_root": str(repo_root),
        "artifact_root": str(artifact_root),
        "server_launch_count": 0,
        "host_invocation_count": 0,
        "semantic_retry_count": 0,
        "replay_count": 0,
        "fallback_count": 0,
        "lm_studio_contact_count": 0,
        "repository_mutation_count": 0,
        "provider_attempts": 0,
        "provider_completions": 0,
    }
    process: subprocess.Popen[str] | None = None
    log_path: Path | None = None
    lock_handle: TextIO | None = None
    exit_code = 2

    try:
        _require_clean_repo(repo_root)
        head, tree = _git_identity(repo_root)
        summary["relaylm"] = {"head": head, "tree": tree, "clean": True}

        origin = _require_loopback_origin(args.origin, args.port)
        api_base = f"{origin}/v1"
        if api_base != S2_SELECTED_LLAMA_CPP_ENDPOINT:
            raise SelectedS2TransactionError(
                f"selected-S2 API base must be {S2_SELECTED_LLAMA_CPP_ENDPOINT}"
            )
        summary["origin"] = origin
        summary["provider_base_url"] = api_base

        lock_handle = _acquire_lifecycle_lock(lock_path)
        summary["lock"] = {"path": str(lock_path), "acquired": True}

        if not _port_is_free("127.0.0.1", args.port):
            summary["disposition"] = "EXECUTION_BLOCKED"
            summary["classification"] = "EXECUTION_BLOCKED"
            summary["phase"] = "preexisting_listener"
            summary["listener_snapshot"] = _listener_snapshot(args.port)
            exit_code = 3
            return exit_code

        server_binary = llama_cpp_root / "build" / "bin" / "llama-server"
        revision, version = _collect_llama_identity(
            llama_cpp_root=llama_cpp_root, server_binary=server_binary
        )
        _require_server_flags(server_binary)
        _verify_reasoning_effort_none_semantics(
            llama_cpp_root=llama_cpp_root, revision=revision
        )
        if not artifact_path.is_file():
            raise SelectedS2TransactionError(
                f"canonical GGUF is not a file: {artifact_path}"
            )

        binary_sha256 = _sha256_file(server_binary)
        artifact_sha256 = _sha256_file(artifact_path)
        gpu_identity = _collect_gpu_identity()
        log_path = _new_server_log_path()
        launch_command = _launch_command(
            server_binary=server_binary,
            artifact_path=artifact_path,
            port=args.port,
            log_path=log_path,
        )
        process = _start_server(launch_command)
        summary["server_launch_count"] = 1
        summary["server"] = {
            "pid": process.pid,
            "binary": str(server_binary),
            "binary_sha256": binary_sha256,
            "llama_cpp_root": str(llama_cpp_root),
            "revision": revision,
            "version": version,
            "launch_command": shlex.join(launch_command),
            "log_path": str(log_path),
            "gpu_identity": gpu_identity,
        }

        _wait_until_ready(process=process, origin=origin)
        probe = _probe_server(
            origin=origin, api_base=api_base, artifact_path=artifact_path
        )
        summary["pre_host_probe"] = probe
        request_model = str(probe["request_model"])
        controller_identity = _controller_identity(
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
        summary["controller_identity"] = controller_identity

        summary["host_invocation_count"] = 1
        try:
            result = run_llama_cpp_selected_s2_transaction(
                base_url=api_base,
                model=request_model,
                repository_root=repo_root,
                artifact_root=artifact_root,
                controller_identity=controller_identity,
            )
        except Exception as exc:
            summary["disposition"] = "HOST_INCOMPLETE"
            summary["classification"] = "INCOMPLETE"
            summary["phase"] = "host_entered"
            summary["error"] = f"{type(exc).__name__}: {exc}"
            _recover_host_artifacts(artifact_root, summary)
            exit_code = 2
            return exit_code

        summary["host"] = asdict(result)
        summary["provider_attempts"] = result.provider_attempts
        summary["provider_completions"] = result.provider_completions
        summary["classification"] = result.mechanical_classification
        summary["disposition"] = "HOST_COMPLETED"
        summary["phase"] = "host_complete"
        _recover_host_artifacts(artifact_root, summary)
        exit_code = 0
        return exit_code
    except (SelectedS2TransactionError, S2HostError) as exc:
        if summary["host_invocation_count"] == 0:
            summary["disposition"] = "EXECUTION_BLOCKED"
            summary["classification"] = "EXECUTION_BLOCKED"
            summary["phase"] = summary.get("phase") or "mechanical_pre_host"
            exit_code = 3
        else:
            summary["disposition"] = "HOST_INCOMPLETE"
            summary["classification"] = "INCOMPLETE"
            summary["phase"] = "host_entered"
            exit_code = 2
            _recover_host_artifacts(artifact_root, summary)
        summary["error"] = f"{type(exc).__name__}: {exc}"
        return exit_code
    except KeyboardInterrupt:
        if summary["host_invocation_count"] == 0:
            summary["disposition"] = "EXECUTION_BLOCKED"
            summary["classification"] = "EXECUTION_BLOCKED"
            summary["phase"] = "interrupted_pre_host"
        else:
            summary["disposition"] = "HOST_INCOMPLETE"
            summary["classification"] = "INCOMPLETE"
            summary["phase"] = "interrupted_after_host_entry"
            _recover_host_artifacts(artifact_root, summary)
        summary["error"] = "KeyboardInterrupt"
        exit_code = 130
        return exit_code
    except Exception as exc:  # pragma: no cover - final fail-closed boundary
        if summary["host_invocation_count"] == 0:
            summary["disposition"] = "EXECUTION_BLOCKED"
            summary["classification"] = "EXECUTION_BLOCKED"
            summary["phase"] = "unexpected_pre_host"
            exit_code = 3
        else:
            summary["disposition"] = "HOST_INCOMPLETE"
            summary["classification"] = "INCOMPLETE"
            summary["phase"] = "unexpected_after_host_entry"
            exit_code = 2
            _recover_host_artifacts(artifact_root, summary)
        summary["error"] = f"{type(exc).__name__}: {exc}"
        return exit_code
    finally:
        if process is not None:
            summary.setdefault("server", {})["cleanup"] = _terminate_owned_process(
                process
            )
        if log_path is not None and log_path.is_file():
            summary.setdefault("server", {})["log_sha256"] = _sha256_file(log_path)
            summary["server"]["log_bytes"] = log_path.stat().st_size
        _recover_host_artifacts(artifact_root, summary)
        summary["transaction_exit_code"] = exit_code
        _write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        if lock_handle is not None:
            _release_lifecycle_lock(lock_handle)


def _fresh_root(value: str | None, *, prefix: str) -> Path:
    if value:
        path = Path(value).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=False)
        return path
    return Path(tempfile.mkdtemp(prefix=prefix)).resolve()


def _require_clean_repo(repo_root: Path) -> None:
    if not (repo_root / ".git").exists():
        raise SelectedS2TransactionError(f"repo-root is not a git checkout: {repo_root}")
    status = _run_text(["git", "status", "--porcelain"], cwd=repo_root)
    if status.strip():
        raise SelectedS2TransactionError("transaction requires a fresh clean v2 checkout")


def _git_identity(repo_root: Path) -> tuple[str, str]:
    return (
        _run_text(["git", "rev-parse", "HEAD"], cwd=repo_root).strip(),
        _run_text(["git", "rev-parse", "HEAD^{tree}"], cwd=repo_root).strip(),
    )


def _require_loopback_origin(origin: str, port: int) -> str:
    if origin.rstrip("/") != DEFAULT_ORIGIN or port != DEFAULT_PORT:
        raise SelectedS2TransactionError(
            f"transaction origin must be exactly {DEFAULT_ORIGIN}"
        )
    return DEFAULT_ORIGIN


def _acquire_lifecycle_lock(path: Path) -> TextIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    while True:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle
        except BlockingIOError:
            if time.monotonic() >= deadline:
                handle.close()
                raise SelectedS2TransactionError(
                    f"timed out waiting for llama-server lifecycle lock: {path}"
                )
            time.sleep(0.5)


def _release_lifecycle_lock(handle: TextIO) -> None:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


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
    except SelectedS2TransactionError:
        return None
    return "\n".join(line for line in output.splitlines() if f":{port}" in line) or None


def _collect_llama_identity(
    *, llama_cpp_root: Path, server_binary: Path
) -> tuple[str, str]:
    if not server_binary.is_file() or not os.access(server_binary, os.X_OK):
        raise SelectedS2TransactionError(
            f"llama-server is not executable: {server_binary}"
        )
    revision = _run_text(["git", "rev-parse", "HEAD"], cwd=llama_cpp_root).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SelectedS2TransactionError(
            "llama.cpp HEAD must be an exact lowercase 40-hex commit"
        )
    version = _run_text([str(server_binary), "--version"]).strip()
    if not version:
        raise SelectedS2TransactionError("llama-server --version returned no identity")
    return revision, version


def _require_server_flags(server_binary: Path) -> None:
    help_text = _run_text([str(server_binary), "--help"])
    required = (
        "--model",
        "--host",
        "--port",
        "--n-gpu-layers",
        "--ctx-size",
        "--parallel",
        "--no-context-shift",
        "--log-verbosity",
        "--log-prefix",
        "--log-timestamps",
        "--log-file",
    )
    missing = [flag for flag in required if flag not in help_text]
    if missing:
        raise SelectedS2TransactionError(
            "llama-server lacks required launch flags: " + ", ".join(missing)
        )


def _verify_reasoning_effort_none_semantics(
    *, llama_cpp_root: Path, revision: str
) -> None:
    source = _run_text(
        ["git", "show", f"{revision}:tools/server/server-common.cpp"],
        cwd=llama_cpp_root,
    )
    match = re.search(r'reasoning_effort\s*==\s*"none"', source)
    if match is None:
        raise SelectedS2TransactionError(
            "exact llama.cpp revision lacks reasoning_effort=none handling"
        )
    window = source[match.start() : match.start() + 2000]
    if re.search(r"inputs\.enable_thinking\s*=\s*false", window) is None:
        raise SelectedS2TransactionError(
            "exact llama.cpp revision does not map reasoning_effort=none to "
            "enable_thinking=false"
        )


def _collect_gpu_identity() -> dict[str, str]:
    output = _run_text(
        [
            "nvidia-smi",
            "--query-gpu=name,uuid,driver_version,memory.total",
            "--format=csv,noheader,nounits",
        ]
    ).strip()
    rows = [row.strip() for row in output.splitlines() if row.strip()]
    if len(rows) != 1:
        raise SelectedS2TransactionError(
            "selected-S2 laboratory requires exactly one visible GPU row"
        )
    parts = [part.strip() for part in rows[0].split(",")]
    if len(parts) != 4 or any(not part for part in parts):
        raise SelectedS2TransactionError("nvidia-smi GPU identity shape is invalid")
    return {
        "name": parts[0],
        "uuid": parts[1],
        "driver": parts[2],
        "memory_mib": parts[3],
    }


def _new_server_log_path() -> Path:
    root = Path.home() / "logs"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    path = root / f"relaylm-v2-2211-s2-{stamp}-{os.getpid()}.log"
    if path.exists():
        raise SelectedS2TransactionError(f"fresh server log already exists: {path}")
    return path


def _launch_command(
    *, server_binary: Path, artifact_path: Path, port: int, log_path: Path
) -> list[str]:
    return [
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
        str(S2_SELECTED_LLAMA_CPP_CONTEXT_LENGTH),
        "-np",
        str(DEFAULT_SLOTS),
        "--no-context-shift",
        "-lv",
        "4",
        "--log-prefix",
        "--log-timestamps",
        "--log-file",
        str(log_path),
    ]


def _start_server(command: list[str]) -> subprocess.Popen[str]:
    try:
        return subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError as exc:
        raise SelectedS2TransactionError(
            f"failed to launch transaction-owned llama-server: {exc}"
        ) from exc


def _wait_until_ready(*, process: subprocess.Popen[str], origin: str) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SelectedS2TransactionError(
                "transaction-owned llama-server exited before readiness: "
                f"{process.returncode}"
            )
        try:
            health = _get_json(f"{origin}/health", timeout=20.0)
            if isinstance(health, Mapping) and health.get("status") == "ok":
                return
        except Exception as exc:
            last_error = exc
        time.sleep(READY_POLL_SECONDS)
    detail = f": {last_error}" if last_error else ""
    raise SelectedS2TransactionError(
        "transaction-owned llama-server did not become ready within "
        f"{READY_TIMEOUT_SECONDS:g}s{detail}"
    )


def _probe_server(
    *, origin: str, api_base: str, artifact_path: Path
) -> dict[str, Any]:
    health = _get_json(f"{origin}/health", timeout=30.0)
    models = _get_json(f"{api_base}/models", timeout=30.0)
    props = _get_json(f"{origin}/props", timeout=30.0)
    slots = _get_json(f"{origin}/slots", timeout=30.0)
    if not isinstance(health, Mapping) or health.get("status") != "ok":
        raise SelectedS2TransactionError("llama-server /health is not ready")
    model_ids = _model_ids(models)
    if len(model_ids) != 1:
        raise SelectedS2TransactionError(
            "transaction-owned server must expose exactly one model id"
        )
    if not isinstance(props, Mapping):
        raise SelectedS2TransactionError("llama-server /props must return an object")
    if not isinstance(slots, list) or len(slots) != DEFAULT_SLOTS:
        raise SelectedS2TransactionError(
            "transaction-owned server must expose exactly one slot"
        )
    settings = props.get("default_generation_settings")
    if (
        not isinstance(settings, Mapping)
        or settings.get("n_ctx") != S2_SELECTED_LLAMA_CPP_CONTEXT_LENGTH
    ):
        raise SelectedS2TransactionError("llama-server /props context is not 8192")
    if props.get("total_slots") != DEFAULT_SLOTS:
        raise SelectedS2TransactionError("llama-server /props total_slots is not 1")
    slot_contexts: list[int] = []
    for slot in slots:
        if (
            not isinstance(slot, Mapping)
            or slot.get("n_ctx") != S2_SELECTED_LLAMA_CPP_CONTEXT_LENGTH
        ):
            raise SelectedS2TransactionError("llama-server slot context is not 8192")
        slot_contexts.append(int(slot["n_ctx"]))
    request_model = model_ids[0]
    if props.get("model_alias") != request_model:
        raise SelectedS2TransactionError(
            "/v1/models id disagrees with /props.model_alias"
        )
    model_path = props.get("model_path")
    if (
        not isinstance(model_path, str)
        or Path(model_path).expanduser().resolve() != artifact_path
    ):
        raise SelectedS2TransactionError(
            "/props.model_path disagrees with canonical GGUF path"
        )
    build_info = props.get("build_info")
    if not isinstance(build_info, str) or not build_info.strip():
        raise SelectedS2TransactionError("/props.build_info is unavailable")
    return {
        "request_model": request_model,
        "build_info": build_info,
        "model_path": model_path,
        "model_ftype": props.get("model_ftype"),
        "context": S2_SELECTED_LLAMA_CPP_CONTEXT_LENGTH,
        "slot_count": DEFAULT_SLOTS,
        "slot_contexts": slot_contexts,
        "non_generative_request_count": 4,
    }


def _model_ids(payload: object) -> list[str]:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("data"), list):
        raise SelectedS2TransactionError("llama-server /v1/models response is invalid")
    ids: list[str] = []
    for item in payload["data"]:
        if (
            isinstance(item, Mapping)
            and isinstance(item.get("id"), str)
            and item["id"].strip()
        ):
            ids.append(str(item["id"]))
    return ids


def _get_json(url: str, *, timeout: float) -> object:
    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SelectedS2TransactionError(f"GET {url} failed: {exc}") from exc


def _controller_identity(
    *,
    revision: str,
    build_info: str,
    server_binary: Path,
    binary_sha256: str,
    artifact_path: Path,
    artifact_sha256: str,
    launch_command: list[str],
    process: subprocess.Popen[str],
    log_path: Path,
    gpu_identity: Mapping[str, str],
    probe: Mapping[str, object],
) -> dict[str, object]:
    return {
        "upstream_revision": revision,
        "build_info": build_info,
        "binary_path": str(server_binary),
        "binary_sha256": binary_sha256,
        "model_path": str(artifact_path),
        "artifact_sha256": artifact_sha256,
        "context_shift_enabled": False,
        "launch": {
            "pid": process.pid,
            "argv": shlex.join(launch_command),
            "context": S2_SELECTED_LLAMA_CPP_CONTEXT_LENGTH,
            "slots": DEFAULT_SLOTS,
            "context_shift": False,
            "gpu_layers": 999,
            "log_path": str(log_path),
        },
        "hardware": dict(gpu_identity),
        "capacity_evidence": {
            "context": probe["context"],
            "slots": probe["slot_count"],
            "slot_contexts": probe["slot_contexts"],
        },
    }


def _terminate_owned_process(process: subprocess.Popen[str]) -> dict[str, object]:
    forced = False
    path = "already_exited"
    if process.poll() is None:
        path = "sigint"
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=30.0)
        except subprocess.TimeoutExpired:
            path = "sigterm"
            process.terminate()
            try:
                process.wait(timeout=15.0)
            except subprocess.TimeoutExpired:
                path = "sigkill"
                forced = True
                process.kill()
                process.wait(timeout=5.0)
    return {
        "terminated": process.poll() is not None,
        "exit_code": process.returncode,
        "signal_path": path,
        "forced": forced,
    }


def _recover_host_artifacts(root: Path, summary: dict[str, Any]) -> None:
    artifacts: dict[str, object] = {}
    for name in (
        "run-manifest.json",
        "run-state.json",
        "s2-smoke-result.json",
        "request-evidence.jsonl",
    ):
        path = root / name
        if not path.is_file():
            continue
        artifacts[name] = {
            "path": str(path),
            "sha256": _sha256_file(path),
            "bytes": path.stat().st_size,
        }
        if name not in {"run-manifest.json", "run-state.json", "s2-smoke-result.json"}:
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(value, Mapping):
            continue
        if name == "run-manifest.json":
            if value.get("run_id") is not None:
                summary["run_id"] = value.get("run_id")
            if value.get("identity_fingerprint") is not None:
                summary["identity_fingerprint"] = value.get("identity_fingerprint")
        elif name == "run-state.json":
            attempts = value.get("provider_attempts")
            completions = value.get("provider_completions")
            if isinstance(attempts, int) and not isinstance(attempts, bool):
                summary["provider_attempts"] = attempts
            if isinstance(completions, int) and not isinstance(completions, bool):
                summary["provider_completions"] = completions
        else:
            assessment = value.get("protocol_assessment")
            if isinstance(assessment, Mapping):
                summary["typed_generic_semantic_equal"] = assessment.get(
                    "typed_generic_semantic_equal"
                )
                summary["p4_p5_p6_shared_formation"] = assessment.get(
                    "p4_p5_p6_shared_formation"
                )
    if artifacts:
        summary["artifacts"] = artifacts


def _run_text(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, check=False
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise SelectedS2TransactionError(
            f"command failed ({completed.returncode}): "
            f"{shlex.join(command)}: {detail}"
        )
    return completed.stdout or completed.stderr


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
