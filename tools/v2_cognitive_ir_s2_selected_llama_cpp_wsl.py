from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from collections.abc import Sequence


INNER_TRANSACTION_MODULE = (
    "tools.v2_cognitive_ir_s2_selected_llama_cpp_transaction"
)
DEFAULT_SHARED_LOCK_PATH = Path(
    "/tmp/relaylm/locks/llama-server-127.0.0.1-1234.lock"
)
DEFAULT_LLAMA_CPP_RELATIVE = Path("src") / "llama.cpp"
DEFAULT_GGUF_RELATIVE = (
    Path("models") / "gguf" / "gemma-4-12B-it-Q4_K_M.gguf"
)


class SelectedS2WslLauncherError(RuntimeError):
    """The WSL launcher cannot establish a writable mechanical envelope."""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a sandbox-writable WSL envelope and invoke the existing "
            "RelayLM 2.0 #2211 selected-S2 transaction exactly once."
        )
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--operator-home")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    source_root = (repo_root / "src").resolve()
    if not source_root.is_dir():
        raise SelectedS2WslLauncherError(
            f"exact checkout src package root is missing: {source_root}"
        )
    operator_home = (
        Path(args.operator_home).expanduser().resolve()
        if args.operator_home
        else Path.home().resolve()
    )
    llama_cpp_root = operator_home / DEFAULT_LLAMA_CPP_RELATIVE
    artifact_path = operator_home / DEFAULT_GGUF_RELATIVE

    runtime_root = Path(
        tempfile.mkdtemp(prefix="relaylm-v2-2211-s2-wsl-runtime-")
    ).resolve()
    runtime_home = runtime_root / "home"
    runtime_home.mkdir(parents=True, exist_ok=False)

    try:
        DEFAULT_SHARED_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SelectedS2WslLauncherError(
            "cannot prepare shared writable lifecycle-lock directory: "
            f"{DEFAULT_SHARED_LOCK_PATH.parent}: {exc}"
        ) from exc

    command = _inner_command(
        repo_root=repo_root,
        llama_cpp_root=llama_cpp_root,
        artifact_path=artifact_path,
        lock_path=DEFAULT_SHARED_LOCK_PATH,
    )
    child_env = os.environ.copy()
    child_env["HOME"] = str(runtime_home)
    child_env["PYTHONPATH"] = _exact_checkout_pythonpath(
        source_root=source_root,
        inherited=child_env.get("PYTHONPATH"),
    )

    try:
        completed = subprocess.run(
            command,
            env=child_env,
            cwd=repo_root,
            check=False,
        )
    except OSError as exc:
        raise SelectedS2WslLauncherError(
            f"failed to invoke selected-S2 transaction once: {exc}"
        ) from exc
    return int(completed.returncode)


def _exact_checkout_pythonpath(*, source_root: Path, inherited: str | None) -> str:
    source = str(source_root.resolve())
    if not inherited:
        return source
    return os.pathsep.join((source, inherited))


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


if __name__ == "__main__":
    raise SystemExit(main())
