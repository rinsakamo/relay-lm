from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from collections.abc import Sequence


INNER_TRANSACTION_MODULE = "tools.v2_cognitive_ir_s3_llama_cpp_transaction"
DEFAULT_SHARED_LOCK_PATH = Path("/tmp/relaylm/locks/llama-server-127.0.0.1-1234.lock")
DEFAULT_LLAMA_CPP_RELATIVE = Path("src") / "llama.cpp"
DEFAULT_GGUF_RELATIVE = Path("models") / "gguf" / "gemma-4-12B-it-Q4_K_M.gguf"


class S3WslLauncherError(RuntimeError):
    """The S3 WSL launcher cannot establish its writable exact-checkout envelope."""


def _inner_command(
    *,
    repo_root: Path,
    llama_cpp_root: Path,
    artifact_path: Path,
    lock_path: Path,
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
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create one writable WSL envelope and invoke the frozen #2211 S3 "
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
    child_env["PYTHONPATH"] = exact_src if not inherited else os.pathsep.join((exact_src, inherited))
    command = _inner_command(
        repo_root=repo_root,
        llama_cpp_root=llama_cpp_root,
        artifact_path=artifact_path,
        lock_path=DEFAULT_SHARED_LOCK_PATH,
    )
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            env=child_env,
            check=False,
        )
    except OSError as exc:
        raise S3WslLauncherError(f"failed to invoke frozen S3 transaction once: {exc}") from exc
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
