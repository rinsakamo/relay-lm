"""Carry the v1 llama.cpp Stage R transaction into a WSL/LocalCodex child.

This module is intentionally only an operator boundary. The existing
``relaylm.actual_model_stage_r_llama_cpp_transaction`` module remains the sole
owner of the physical server, provider, host, readiness, evidence, and
cleanup lifecycle.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


INNER_TRANSACTION = "relaylm.actual_model_stage_r_llama_cpp_transaction"
RUNTIME_ROOT_PARENT = Path("/tmp")
GGUF_RELATIVE_PATH = Path("models/gguf/gemma-4-12B-it-Q4_K_M.gguf")


@dataclass(frozen=True)
class RuntimePaths:
    """Paths created or passed by the wrapper for one child transaction."""

    runtime_root: Path
    runtime_home: Path
    workspace_root: Path
    artifact_root: Path
    llama_cpp_root: Path
    artifact_path: Path


def main(
    argv: Sequence[str] | None = None,
    *,
    inner_transaction: str = INNER_TRANSACTION,
    inner_args: Sequence[str] = (),
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Invoke the existing v1 llama.cpp Stage R transaction once with "
            "fresh transaction roots."
        )
    )
    parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    # Capture the operator identity before constructing the child environment.
    # The child HOME must not change where the real llama.cpp and GGUF are read.
    operator_home = Path.home().resolve()
    repo_root = Path(__file__).resolve().parents[1]
    paths = _create_runtime_paths(operator_home)
    _prove_child_roots_are_fresh(paths)
    command = _inner_command(
        repo_root=repo_root,
        paths=paths,
        inner_transaction=inner_transaction,
        inner_args=inner_args,
    )
    environment = _child_environment(repo_root=repo_root, paths=paths)

    print(
        "v1_stage_r_llama_cpp_wsl: "
        f"runtime_root={paths.runtime_root} "
        f"workspace_root={paths.workspace_root} "
        f"artifact_root={paths.artifact_root}",
        flush=True,
    )
    completed = subprocess.run(
        command,
        cwd=repo_root,
        env=environment,
        check=False,
    )
    return completed.returncode


def _create_runtime_paths(operator_home: Path) -> RuntimePaths:
    runtime_root = Path(
        tempfile.mkdtemp(
            prefix="relaylm-v1-stage-r-llama-cpp-",
            dir=RUNTIME_ROOT_PARENT,
        )
    ).resolve()
    runtime_home = runtime_root / "home"
    runtime_home.mkdir()
    _prove_runtime_home_writable(runtime_home)

    workspace_root = runtime_root / "workspace"
    artifact_root = runtime_root / "artifacts"
    paths = RuntimePaths(
        runtime_root=runtime_root,
        runtime_home=runtime_home,
        workspace_root=workspace_root,
        artifact_root=artifact_root,
        llama_cpp_root=(operator_home / "src" / "llama.cpp").resolve(),
        artifact_path=(operator_home / GGUF_RELATIVE_PATH).resolve(),
    )
    _prove_child_roots_are_fresh(paths)
    return paths


def _prove_runtime_home_writable(runtime_home: Path) -> None:
    if not runtime_home.is_dir() or not os.access(runtime_home, os.W_OK):
        raise RuntimeError(f"runtime HOME is not writable: {runtime_home}")
    probe = runtime_home / ".relaylm-wsl-wrapper-write-probe"
    try:
        probe.write_text("ok\n", encoding="utf-8")
    finally:
        probe.unlink(missing_ok=True)


def _prove_child_roots_are_fresh(paths: RuntimePaths) -> None:
    for name, path in (
        ("workspace-root", paths.workspace_root),
        ("artifact-root", paths.artifact_root),
    ):
        if path.exists():
            raise RuntimeError(
                f"{name} must be fresh and nonexistent before inner invocation: "
                f"{path}"
            )


def _inner_command(
    *,
    repo_root: Path,
    paths: RuntimePaths,
    inner_transaction: str = INNER_TRANSACTION,
    inner_args: Sequence[str] = (),
) -> list[str]:
    normalized_inner_args = _normalized_forward_args(inner_args, label="inner_args")
    return [
        sys.executable,
        "-m",
        inner_transaction,
        *normalized_inner_args,
        "--repo-root",
        str(repo_root),
        "--llama-cpp-root",
        str(paths.llama_cpp_root),
        "--artifact-path",
        str(paths.artifact_path),
        "--workspace-root",
        str(paths.workspace_root),
        "--artifact-root",
        str(paths.artifact_root),
    ]


def _normalized_forward_args(values: Sequence[str], *, label: str) -> list[str]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{label} must be a sequence of strings")
    normalized = list(values)
    if not all(isinstance(value, str) and "\x00" not in value for value in normalized):
        raise TypeError(f"{label} must contain strings without NUL bytes")
    return normalized


def _child_environment(*, repo_root: Path, paths: RuntimePaths) -> dict[str, str]:
    environment = os.environ.copy()
    environment["HOME"] = str(paths.runtime_home)
    src_root = str(repo_root / "src")
    inherited_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        src_root
        if not inherited_pythonpath
        else os.pathsep.join((src_root, inherited_pythonpath))
    )
    return environment


if __name__ == "__main__":
    raise SystemExit(main())
