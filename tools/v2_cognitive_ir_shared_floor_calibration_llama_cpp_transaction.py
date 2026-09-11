from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from typing import Any, TextIO

from relaylm.v2_cognitive_ir_shared_floor_calibration import (
    CALIBRATION_INCOMPLETE,
    SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE,
    SHARED_FLOOR_CITABLE,
    SHARED_FLOOR_CLAIM,
    SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY,
    SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
    SHARED_FLOOR_MAX_SEMANTIC_CALLS,
)
from tools.v2_cognitive_ir_s2_selected_llama_cpp import (
    probe_llama_cpp_selected_s2_binding,
)
from tools.v2_cognitive_ir_s2_selected_llama_cpp_transaction import (
    DEFAULT_ORIGIN,
    DEFAULT_PORT,
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
from tools.v2_cognitive_ir_s3_llama_cpp import S3_LLAMA_CPP_ENDPOINT
from tools.v2_cognitive_ir_s3_llama_cpp_transaction import (
    _canonical,
    _lightweight_binding_check,
    _material_stat,
)
from tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp import (
    run_llama_cpp_shared_floor_calibration,
)


TRANSACTION_FORMAT_VERSION = 1
DEFAULT_SHARED_LOCK_PATH = Path(
    "/tmp/relaylm/locks/llama-server-127.0.0.1-1234.lock"
)


class SharedFloorCalibrationTransactionError(RuntimeError):
    """The frozen #2600 physical calibration cannot proceed truthfully."""


def _fresh_artifact_root(value: str | None) -> Path:
    if value:
        path = Path(value).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=False)
        return path
    return Path(
        tempfile.mkdtemp(prefix="relaylm-v2-2211-shared-floor-calibration-")
    ).resolve()


def _new_log_path() -> Path:
    root = Path.home() / "logs"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    path = (
        root
        / f"relaylm-v2-2211-shared-floor-calibration-{stamp}-{os.getpid()}.log"
    )
    if path.exists():
        raise SharedFloorCalibrationTransactionError(
            f"fresh shared-floor server log already exists: {path}"
        )
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Execute the frozen #2600 non-citable F_SHARED target-range "
            "calibration under one owned llama-server lifetime."
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
        else artifact_root / "shared-floor-calibration-transaction-summary.json"
    )
    lock_path = Path(args.lock_path).expanduser().resolve()

    summary: dict[str, Any] = {
        "format_version": TRANSACTION_FORMAT_VERSION,
        "claim": SHARED_FLOOR_CLAIM,
        "citable": SHARED_FLOOR_CITABLE,
        "architecture_consequence": SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE,
        "classification": CALIBRATION_INCOMPLETE,
        "disposition": None,
        "artifact_root": str(artifact_root),
        "planned_max_semantic_calls": SHARED_FLOOR_MAX_SEMANTIC_CALLS,
        "planned_max_input_token_requests": SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
        "planned_input_token_requests_per_difficulty": (
            SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY
        ),
        "server_launch_count": 0,
        "host_invocation_count": 0,
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
    }
    process: subprocess.Popen[str] | None = None
    lock_handle: TextIO | None = None
    log_path: Path | None = None
    exit_code = 2

    try:
        _require_clean_repo(repo_root)
        head, tree = _git_identity(repo_root)
        summary["repository"] = {
            "commit": head,
            "tree": tree,
            "clean": True,
        }
        if args.origin.rstrip("/") != DEFAULT_ORIGIN or args.port != DEFAULT_PORT:
            raise SharedFloorCalibrationTransactionError(
                f"calibration endpoint must be exactly {DEFAULT_ORIGIN}/v1"
            )
        if S3_LLAMA_CPP_ENDPOINT != f"{DEFAULT_ORIGIN}/v1":
            raise AssertionError(
                "shared-floor transport endpoint drifted from R4 transport"
            )
        if not artifact_path.is_file():
            raise SharedFloorCalibrationTransactionError(
                f"canonical GGUF is not a file: {artifact_path}"
            )

        lock_handle = _acquire_lifecycle_lock(lock_path)
        summary["lock"] = {"path": str(lock_path), "acquired": True}
        if not _port_is_free("127.0.0.1", args.port):
            raise SharedFloorCalibrationTransactionError(
                "127.0.0.1:1234 is occupied before calibration"
            )

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

        log_path = _new_log_path()
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
            "artifact_path": str(artifact_path),
            "artifact_sha256": artifact_sha256,
            "launch_command": shlex.join(launch_command),
            "log_path": str(log_path),
            "gpu_identity": gpu_identity,
        }

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
        summary["full_material_attestation_count"] = 1
        summary["controller_identity"] = controller
        summary["start_binding"] = start_binding

        def before_call() -> None:
            if process is None:
                raise AssertionError(
                    "shared-floor transaction-owned server is unavailable"
                )
            _lightweight_binding_check(
                process=process,
                expected_probe=probe,
                server_binary=server_binary,
                expected_binary_stat=binary_stat,
                artifact_path=artifact_path,
                expected_artifact_stat=artifact_stat,
            )

        summary["host_invocation_count"] = 1
        run = run_llama_cpp_shared_floor_calibration(
            base_url=S3_LLAMA_CPP_ENDPOINT,
            model=request_model,
            before_call=before_call,
        )
        summary["provider_attempts"] = run.provider_attempts
        summary["provider_completions"] = run.provider_completions
        summary["input_count_attempts"] = run.input_count_attempts
        summary["input_count_completions"] = run.input_count_completions
        summary["lightweight_live_binding_check_count"] = run.live_binding_checks
        summary["p2_hard_admissions"] = run.p2_hard_admissions
        summary["p2_records"] = list(run.p2_records)
        summary["result"] = asdict(run.result)

        if run.live_binding_checks != run.result.semantic_calls:
            raise SharedFloorCalibrationTransactionError(
                "live binding was not checked before every semantic call"
            )

        end_binding = probe_llama_cpp_selected_s2_binding(
            base_url=S3_LLAMA_CPP_ENDPOINT,
            model=request_model,
            controller_identity=controller,
        )
        summary["full_material_attestation_count"] = 2
        summary["end_binding"] = end_binding
        if _canonical(end_binding) != _canonical(start_binding):
            raise SharedFloorCalibrationTransactionError(
                "full runtime/material binding drifted during calibration"
            )
        if _material_stat(server_binary) != binary_stat:
            raise SharedFloorCalibrationTransactionError(
                "llama-server material stat drifted during calibration"
            )
        if _material_stat(artifact_path) != artifact_stat:
            raise SharedFloorCalibrationTransactionError(
                "GGUF material stat drifted during calibration"
            )

        summary["classification"] = run.result.classification
        summary["disposition"] = "CALIBRATION_COMPLETED"
        exit_code = 0

    except KeyboardInterrupt:
        summary["classification"] = CALIBRATION_INCOMPLETE
        summary["disposition"] = (
            "INTERRUPTED_AFTER_HOST_ENTRY"
            if summary["host_invocation_count"]
            else "INTERRUPTED_PRE_HOST"
        )
        summary["error"] = "KeyboardInterrupt"
        exit_code = 130
    except Exception as exc:
        summary["classification"] = CALIBRATION_INCOMPLETE
        summary["disposition"] = (
            "HOST_INCOMPLETE"
            if summary["host_invocation_count"]
            else "EXECUTION_BLOCKED"
        )
        summary["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 2 if summary["host_invocation_count"] else 3
    finally:
        if process is not None:
            summary.setdefault("server", {})["cleanup"] = _terminate_owned_process(
                process
            )
        if log_path is not None and log_path.is_file():
            summary.setdefault("server", {})["log_sha256"] = _sha256_file(log_path)
            summary["server"]["log_bytes"] = log_path.stat().st_size
        summary["listener_released"] = _port_is_free("127.0.0.1", args.port)
        if (
            summary["classification"] != CALIBRATION_INCOMPLETE
            and not summary["listener_released"]
        ):
            summary["classification"] = CALIBRATION_INCOMPLETE
            summary["disposition"] = "CLEANUP_INCOMPLETE"
            exit_code = 2
        summary["transaction_exit_code"] = exit_code
        _write_json(summary_path, summary)
        print(
            json.dumps(
                summary,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        if lock_handle is not None:
            _release_lifecycle_lock(lock_handle)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
