from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence


INNER_TRANSACTION_MODULE = "tools.v2_cognitive_ir_s3_r2_llama_cpp_transaction"
DEFAULT_SHARED_LOCK_PATH = Path("/tmp/relaylm/locks/llama-server-127.0.0.1-1234.lock")
DEFAULT_LLAMA_CPP_RELATIVE = Path("src") / "llama.cpp"
DEFAULT_GGUF_RELATIVE = Path("models") / "gguf" / "gemma-4-12B-it-Q4_K_M.gguf"
WALL_TIME_SCHEMA = "relaylm2-cognitive-ir-s3-wsl-wall-time-v1"


class S3WslLauncherError(RuntimeError):
    """The S3 WSL launcher cannot establish its writable exact-checkout envelope."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inner_command(
    *,
    repo_root: Path,
    llama_cpp_root: Path,
    artifact_path: Path,
    lock_path: Path,
    artifact_root: Path,
    summary_path: Path,
) -> list[str]:
    return [
        sys.executable,
        "-m",
        INNER_TRANSACTION_MODULE,
        "--repo-root",
        str(repo_root),
        "--llama-cpp-root",
        str(llama_cpp_root),
        "--artifact-path",
        str(artifact_path),
        "--lock-path",
        str(lock_path),
        "--artifact-root",
        str(artifact_root),
        "--summary-path",
        str(summary_path),
    ]


def _write_wall_time_sidecar(
    *,
    path: Path,
    wall_seconds: float,
    return_code: int,
    transaction_summary_path: Path,
) -> None:
    if wall_seconds < 0:
        raise S3WslLauncherError("monotonic wall time must be non-negative")
    transaction_summary_sha256 = (
        _sha256_file(transaction_summary_path)
        if transaction_summary_path.is_file()
        else None
    )
    payload = {
        "schema": WALL_TIME_SCHEMA,
        "measurement": "time.monotonic_ns",
        "scope": "one-command-wrapper-child-transaction",
        "wall_seconds": wall_seconds,
        "child_return_code": return_code,
        "transaction_summary_path": str(transaction_summary_path),
        "transaction_summary_sha256": transaction_summary_sha256,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create one writable WSL envelope and invoke the frozen #2211 S3-R2 "
            "four-shard transaction exactly once."
        )
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--operator-home")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    operator_home = (
        Path(args.operator_home).expanduser().resolve()
        if args.operator_home
        else Path.home().resolve()
    )
    llama_cpp_root = operator_home / DEFAULT_LLAMA_CPP_RELATIVE
    artifact_path = operator_home / DEFAULT_GGUF_RELATIVE

    runtime_root = Path(tempfile.mkdtemp(prefix="relaylm-v2-2211-s3-wsl-runtime-")).resolve()
    runtime_home = runtime_root / "home"
    runtime_home.mkdir(parents=True, exist_ok=False)
    artifact_root = runtime_root / "artifacts"
    transaction_summary_path = artifact_root / "s3-llama-cpp-transaction-summary.json"
    wall_time_path = artifact_root / "s3-wsl-wall-time.json"
    try:
        DEFAULT_SHARED_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise S3WslLauncherError(
            f"cannot prepare shared S3 lifecycle-lock directory: {DEFAULT_SHARED_LOCK_PATH.parent}: {exc}"
        ) from exc

    child_env = os.environ.copy()
    child_env["HOME"] = str(runtime_home)
    exact_src = str((repo_root / "src").resolve())
    inherited = child_env.get("PYTHONPATH")
    child_env["PYTHONPATH"] = (
        exact_src if not inherited else os.pathsep.join((exact_src, inherited))
    )
    command = _inner_command(
        repo_root=repo_root,
        llama_cpp_root=llama_cpp_root,
        artifact_path=artifact_path,
        lock_path=DEFAULT_SHARED_LOCK_PATH,
        artifact_root=artifact_root,
        summary_path=transaction_summary_path,
    )
    started_ns = time.monotonic_ns()
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            env=child_env,
            check=False,
        )
    except OSError as exc:
        raise S3WslLauncherError(
            f"failed to invoke frozen S3 transaction once: {exc}"
        ) from exc
    finished_ns = time.monotonic_ns()
    wall_seconds = (finished_ns - started_ns) / 1_000_000_000
    _write_wall_time_sidecar(
        path=wall_time_path,
        wall_seconds=wall_seconds,
        return_code=int(completed.returncode),
        transaction_summary_path=transaction_summary_path,
    )
    print(
        json.dumps(
            {
                "s3_wsl_wall_time_path": str(wall_time_path),
                "s3_wsl_wall_time_sha256": _sha256_file(wall_time_path),
                "wall_seconds": wall_seconds,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
