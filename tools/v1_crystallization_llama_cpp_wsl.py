"""Carry the v1 off-turn Crystallization transaction into a WSL child.

This is an operator boundary only. The transaction module owns the current
llama-server lifecycle and the host module owns the off-turn evidence call.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.v1_stage_r_llama_cpp_wsl import (
    RuntimePaths,
    _child_environment,
    _normalized_forward_args,
    _prove_child_roots_are_fresh,
    _prove_runtime_home_writable,
)


INNER_TRANSACTION = "relaylm.actual_model_crystallization_llama_cpp_transaction"
RUNTIME_ROOT_PARENT = Path("/tmp")
GGUF_RELATIVE_PATH = Path("models/gguf/gemma-4-12B-it-Q4_K_M.gguf")


def main(
    argv: Sequence[str] | None = None,
    *,
    inner_transaction: str = INNER_TRANSACTION,
    inner_args: Sequence[str] = (),
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Invoke the current v1 off-turn Crystallization llama.cpp transaction "
            "once with fresh transaction roots."
        )
    )
    parser.add_argument("--replicate-id", default="0")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    operator_home = Path.home().resolve()
    repo_root = Path(__file__).resolve().parents[1]
    paths = _create_runtime_paths(operator_home)
    _prove_child_roots_are_fresh(paths)
    command = _inner_command(
        repo_root=repo_root,
        paths=paths,
        inner_transaction=inner_transaction,
        inner_args=inner_args,
        replicate_id=args.replicate_id,
    )
    environment = _child_environment(repo_root=repo_root, paths=paths)
    print(
        "v1_crystallization_llama_cpp_wsl: "
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
            prefix="relaylm-v1-crystallization-llama-cpp-",
            dir=RUNTIME_ROOT_PARENT,
        )
    ).resolve()
    runtime_home = runtime_root / "home"
    runtime_home.mkdir()
    _prove_runtime_home_writable(runtime_home)
    paths = RuntimePaths(
        runtime_root=runtime_root,
        runtime_home=runtime_home,
        workspace_root=runtime_root / "workspace",
        artifact_root=runtime_root / "artifacts",
        llama_cpp_root=(operator_home / "src" / "llama.cpp").resolve(),
        artifact_path=(operator_home / GGUF_RELATIVE_PATH).resolve(),
    )
    _prove_child_roots_are_fresh(paths)
    return paths


def _inner_command(
    *,
    repo_root: Path,
    paths: RuntimePaths,
    inner_transaction: str = INNER_TRANSACTION,
    inner_args: Sequence[str] = (),
    replicate_id: str = "0",
) -> list[str]:
    normalized_inner_args = _normalized_forward_args(inner_args, label="inner_args")
    return [
        sys.executable,
        "-m",
        inner_transaction,
        "--replicate-id",
        replicate_id,
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


if __name__ == "__main__":
    raise SystemExit(main())
