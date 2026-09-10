from __future__ import annotations

import argparse
from collections.abc import Sequence
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


INNER_TRANSACTION_MODULE = "tools.v2_cognitive_ir_p2_termination_qual_transaction"
DEFAULT_SHARED_LOCK_PATH = Path("/tmp/relaylm/locks/llama-server-127.0.0.1-1234.lock")
DEFAULT_LLAMA_CPP_RELATIVE = Path("src") / "llama.cpp"
DEFAULT_GGUF_RELATIVE = Path("models") / "gguf" / "gemma-4-12B-it-Q4_K_M.gguf"
WALL_TIME_SCHEMA = "relaylm2-cognitive-ir-p2-termination-qual-wsl-wall-time-v1"


class P2TerminationQualWslLauncherError(RuntimeError):
    """The qualification launcher cannot establish its exact-checkout WSL envelope."""


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
        str(DEFAULT_SHARED_LOCK_PATH),
        "--artifact-root",
        str(artifact_root),
        "--summary-path",
        str(summary_path),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create one writable WSL envelope and invoke P2 termination qualification exactly once."
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
    source_root = (repo_root / "src").resolve()
    if not source_root.is_dir():
        raise P2TerminationQualWslLauncherError(f"exact checkout source root is missing: {source_root}")
    llama_cpp_root = operator_home / DEFAULT_LLAMA_CPP_RELATIVE
    artifact_path = operator_home / DEFAULT_GGUF_RELATIVE

    runtime_root = Path(
        tempfile.mkdtemp(prefix="relaylm-v2-2211-p2-termination-qual-wsl-runtime-")
    ).resolve()
    runtime_home = runtime_root / "home"
    runtime_home.mkdir(parents=True, exist_ok=False)
    artifact_root = runtime_root / "artifacts"
    summary_path = artifact_root / "p2-termination-qual-summary.json"
    wall_time_path = artifact_root / "p2-termination-qual-wsl-wall-time.json"
    try:
        DEFAULT_SHARED_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise P2TerminationQualWslLauncherError(
            f"cannot prepare lifecycle-lock directory: {DEFAULT_SHARED_LOCK_PATH.parent}: {exc}"
        ) from exc

    child_env = os.environ.copy()
    child_env["HOME"] = str(runtime_home)
    inherited = child_env.get("PYTHONPATH")
    child_env["PYTHONPATH"] = (
        str(source_root)
        if not inherited
        else os.pathsep.join((str(source_root), inherited))
    )
    command = _inner_command(
        repo_root=repo_root,
        llama_cpp_root=llama_cpp_root,
        artifact_path=artifact_path,
        artifact_root=artifact_root,
        summary_path=summary_path,
    )
    started_ns = time.monotonic_ns()
    try:
        completed = subprocess.run(command, cwd=repo_root, env=child_env, check=False)
    except OSError as exc:
        raise P2TerminationQualWslLauncherError(
            f"failed to invoke qualification transaction once: {exc}"
        ) from exc
    wall_seconds = (time.monotonic_ns() - started_ns) / 1_000_000_000
    summary_sha256 = _sha256_file(summary_path) if summary_path.is_file() else None
    payload = {
        "schema": WALL_TIME_SCHEMA,
        "measurement": "time.monotonic_ns",
        "scope": "one-command-wrapper-child-transaction",
        "wall_seconds": wall_seconds,
        "child_return_code": int(completed.returncode),
        "transaction_summary_path": str(summary_path),
        "transaction_summary_sha256": summary_sha256,
    }
    wall_time_path.parent.mkdir(parents=True, exist_ok=True)
    wall_time_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "p2_termination_qual_summary_path": str(summary_path),
                "p2_termination_qual_wsl_wall_time_path": str(wall_time_path),
                "p2_termination_qual_wsl_wall_time_sha256": _sha256_file(wall_time_path),
                "wall_seconds": wall_seconds,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
