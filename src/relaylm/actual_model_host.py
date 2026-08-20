from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from relaylm.actual_model_host_runner import main as _lm_studio_main
from relaylm.actual_model_vllm import ActualModelVLLMBindingError
from relaylm.actual_model_vllm_host import (
    CANONICAL_VLLM_REASONING_PROOF_PATH,
    CANONICAL_VLLM_SCREENING_PLAN_PATH,
    ActualModelVLLMHostError,
    execute_vllm_host_run as _execute_vllm_host_run,
    load_vllm_screening_plan,
    prepare_vllm_screening_condition as _prepare_vllm_screening_condition,
)


class ActualModelHostFacadeError(ValueError):
    """The shared host facade cannot dispatch a citable execution."""


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch one host execution without duplicating backend-specific runners."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    selector = argparse.ArgumentParser(add_help=False)
    selector.add_argument(
        "--backend",
        required=True,
        choices=("lm_studio", "vllm"),
    )
    selected, remaining = selector.parse_known_args(arguments)

    if selected.backend == "lm_studio":
        return _lm_studio_main(remaining)
    return _main_vllm(remaining)


def _main_vllm(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one canonical serial COGP5 condition against the frozen vLLM "
            "Gemma 4 target through the existing #1386 scenario harness."
        )
    )
    parser.add_argument("--condition", required=True, choices=("A", "B", "C"))
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--snapshot-root", required=True)
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--replicate-id", default="0")
    parser.add_argument("--provider-api-key-env")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    try:
        relaylm_commit = _current_repo_head(repo_root)
        api_key = _resolve_api_key(args.provider_api_key_env)
        plan = load_vllm_screening_plan(
            repo_root / CANONICAL_VLLM_SCREENING_PLAN_PATH
        )
        prepared = _prepare_vllm_screening_condition(
            plan=plan,
            condition_id=args.condition,
            proof_path=repo_root / CANONICAL_VLLM_REASONING_PROOF_PATH,
            repo_root=repo_root,
            snapshot_root=args.snapshot_root,
            relaylm_commit=relaylm_commit,
            base_url=args.provider_base_url,
            api_key=api_key,
            replicate_id=args.replicate_id,
        )
        results = asyncio.run(
            _execute_vllm_host_run(
                prepared=prepared,
                snapshot_root=args.snapshot_root,
                workspace_root=args.workspace_root,
                artifact_root=args.artifact_root,
            )
        )
    except (
        ActualModelHostFacadeError,
        ActualModelVLLMHostError,
        ActualModelVLLMBindingError,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "format_version": 1,
                "suite": prepared.plan.screening_id,
                "backend": "vllm",
                "condition": prepared.screening_condition_id,
                "relaylm_commit": prepared.manifest.relaylm_commit,
                "target_id": prepared.target.target_id,
                "replicate_id": prepared.manifest.replicate_id,
                "results": [item.to_mapping() for item in results],
                "score": None,
            },
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
    )
    return 0


def _current_repo_head(root: Path) -> str:
    if not root.is_dir():
        raise ActualModelHostFacadeError("repo_root must be an existing directory")
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ActualModelHostFacadeError(
            f"cannot resolve host repository HEAD: {exc}"
        ) from exc
    if len(head) != 40 or any(char not in "0123456789abcdef" for char in head):
        raise ActualModelHostFacadeError(
            "host repository HEAD must be an exact lowercase 40-character Git SHA"
        )
    return head


def _resolve_api_key(env_name: str | None) -> str | None:
    if env_name is None:
        return None
    if not isinstance(env_name, str) or not env_name.strip():
        raise ActualModelHostFacadeError(
            "provider API key environment name must be non-empty"
        )
    value = os.environ.get(env_name)
    if value is None or not value:
        raise ActualModelHostFacadeError(
            f"provider API key environment variable is unavailable: {env_name}"
        )
    return value


if __name__ == "__main__":
    raise SystemExit(main())
