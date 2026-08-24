from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from relaylm.actual_model_fast_screening import (
    SCREENING_CONDITION_ROLES,
    screening_condition_key_for_role,
)
from relaylm.actual_model_fast_screening_artifacts import (
    FastScreeningTimingArtifact,
    FastScreeningTurnTiming,
)
from relaylm.actual_model_host_runner import main as _lm_studio_main
from relaylm.actual_model_vllm import ActualModelVLLMBindingError
from relaylm.actual_model_vllm_budget import (
    VLLMCognitiveBudgetDeclarationError,
    load_vllm_two_pass_cognitive_budget_declaration,
    prepare_vllm_screening_condition_with_budget_declaration as _prepare_vllm_screening_condition,
)
from relaylm.actual_model_vllm_capacity import VLLM_MODEL_RUNNER_IDS
from relaylm.actual_model_vllm_capacity_acquisition import (
    VLLMCapacityAcquisitionError,
    VLLMCapacityAcquisitionFailure,
    execute_vllm_capacity_acquisition as _execute_vllm_capacity_acquisition,
    prepare_vllm_capacity_acquisition as _prepare_vllm_capacity_acquisition,
)
from relaylm.actual_model_vllm_host import (
    CANONICAL_VLLM_REASONING_PROOF_PATH,
    CANONICAL_VLLM_SCREENING_PLAN_PATH,
    ActualModelVLLMHostError,
    execute_vllm_host_run as _execute_vllm_host_run,
    load_vllm_screening_plan,
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
            "Run one current Stage R vLLM role either as capacity acquisition "
            "or as capacity-gated product screening."
        )
    )
    parser.add_argument(
        "--operation",
        choices=("screening", "capacity"),
        default="screening",
    )
    parser.add_argument(
        "--condition",
        required=True,
        choices=SCREENING_CONDITION_ROLES,
        help="Current Stage R semantic role; historical A/B/C coordinates are internal.",
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--snapshot-root", required=True)
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--model-runner", required=True, choices=VLLM_MODEL_RUNNER_IDS)
    parser.add_argument("--replicate-id", default="0")
    parser.add_argument("--provider-api-key-env")
    parser.add_argument("--cognitive-budget")
    parser.add_argument("--capacity-evidence-id")
    parser.add_argument("--capacity-evidence-root")
    parser.add_argument(
        "--screening-plan",
        help=(
            "Repository-relative vLLM screening plan path. "
            "Defaults to the canonical current Stage R reference plan."
        ),
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    condition_role = args.condition
    try:
        relaylm_commit = _current_repo_head(repo_root)
        api_key = _resolve_api_key(args.provider_api_key_env)
        plan_path = _resolve_vllm_screening_plan_path(
            repo_root=repo_root,
            value=args.screening_plan,
        )
        plan = load_vllm_screening_plan(plan_path)
        condition_key = screening_condition_key_for_role(plan, condition_role)
        capacity_override = (
            args.capacity_evidence_id is not None
            or args.capacity_evidence_root is not None
        )
        if args.operation == "capacity":
            if args.cognitive_budget is not None:
                raise ActualModelHostFacadeError(
                    "--cognitive-budget is valid only for screening"
                )
            if capacity_override:
                raise ActualModelHostFacadeError(
                    "capacity evidence override is valid only for screening"
                )
            prepared = _prepare_vllm_capacity_acquisition(
                plan=plan,
                condition_id=condition_key,
                proof_path=repo_root / CANONICAL_VLLM_REASONING_PROOF_PATH,
                repo_root=repo_root,
                snapshot_root=args.snapshot_root,
                relaylm_commit=relaylm_commit,
                base_url=args.provider_base_url,
                api_key=api_key,
                model_runner=args.model_runner,
                replicate_id=args.replicate_id,
            )
            try:
                artifact = asyncio.run(
                    _execute_vllm_capacity_acquisition(
                        prepared=prepared,
                        workspace_root=args.workspace_root,
                        artifact_root=args.artifact_root,
                    )
                )
            except VLLMCapacityAcquisitionFailure as exc:
                _print_capacity_failure(
                    prepared=prepared,
                    failure=exc,
                    condition_role=condition_role,
                )
                return 2
            print(
                json.dumps(
                    {
                        "format_version": 1,
                        "suite": prepared.plan.screening_id,
                        "backend": "vllm",
                        "operation": "capacity",
                        "condition": condition_role,
                        "relaylm_commit": prepared.manifest.relaylm_commit,
                        "target_id": prepared.target.target_id,
                        "replicate_id": prepared.manifest.replicate_id,
                        "observed_max_model_len": (
                            prepared.reasoning_capability.backend_attestation.max_model_len
                        ),
                        "capacity_evidence": artifact.to_mapping(),
                    },
                    ensure_ascii=False,
                    allow_nan=False,
                    indent=2,
                )
            )
            return 0

        if (args.capacity_evidence_id is None) != (
            args.capacity_evidence_root is None
        ):
            raise ActualModelHostFacadeError(
                "--capacity-evidence-id and --capacity-evidence-root must be supplied together"
            )
        if args.capacity_evidence_id is not None:
            plan = replace(plan, capacity_evidence_id=args.capacity_evidence_id)

        cognitive_budget = (
            load_vllm_two_pass_cognitive_budget_declaration(args.cognitive_budget)
            if args.cognitive_budget is not None
            else None
        )
        prepared = _prepare_vllm_screening_condition(
            plan=plan,
            condition_id=condition_key,
            proof_path=repo_root / CANONICAL_VLLM_REASONING_PROOF_PATH,
            repo_root=repo_root,
            snapshot_root=args.snapshot_root,
            relaylm_commit=relaylm_commit,
            base_url=args.provider_base_url,
            api_key=api_key,
            model_runner=args.model_runner,
            replicate_id=args.replicate_id,
            capacity_evidence_root=args.capacity_evidence_root,
            cognitive_budget=cognitive_budget,
        )
        results = asyncio.run(
            _execute_vllm_host_run(
                prepared=prepared,
                snapshot_root=args.snapshot_root,
                workspace_root=args.workspace_root,
                artifact_root=args.artifact_root,
            )
        )
        result_mappings = [_screening_result_mapping(item) for item in results]
    except (
        ActualModelHostFacadeError,
        ActualModelVLLMHostError,
        ActualModelVLLMBindingError,
        VLLMCognitiveBudgetDeclarationError,
        VLLMCapacityAcquisitionError,
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
                "operation": "screening",
                "condition": condition_role,
                "relaylm_commit": prepared.manifest.relaylm_commit,
                "target_id": prepared.target.target_id,
                "replicate_id": prepared.manifest.replicate_id,
                "results": result_mappings,
                "score": None,
            },
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
    )
    return 0


def _screening_result_mapping(result) -> dict[str, object]:
    mapping = dict(result.to_mapping())
    timing_path_value = mapping.get("timing_artifact_path")
    if timing_path_value is None:
        return mapping
    if not isinstance(timing_path_value, str) or not timing_path_value.strip():
        raise ActualModelHostFacadeError(
            "screening result timing_artifact_path must be a non-empty string"
        )

    timing = _load_screening_timing_summary_evidence(Path(timing_path_value))
    expected_timing_id = mapping.get("timing_id")
    if timing.timing_id != expected_timing_id:
        raise ActualModelHostFacadeError(
            "screening timing_id does not match the screening result"
        )
    expected_run_id = mapping.get("run_id")
    if timing.run_id != expected_run_id:
        raise ActualModelHostFacadeError(
            "screening timing run_id does not match the screening result"
        )
    expected_scenario_id = mapping.get("scenario_id")
    if timing.scenario_id != expected_scenario_id:
        raise ActualModelHostFacadeError(
            "screening timing scenario_id does not match the screening result"
        )

    failed_provider_call_count = sum(
        outcome == "failed"
        for turn in timing.turns
        for outcome in (turn.response_outcome, turn.extraction_outcome)
    )
    mapping["failed_provider_call_count"] = failed_provider_call_count
    return mapping


def _load_screening_timing_summary_evidence(
    path: Path,
) -> FastScreeningTimingArtifact:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActualModelHostFacadeError(
            f"cannot read screening timing summary evidence: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise ActualModelHostFacadeError(
            "screening timing summary evidence must be a JSON object"
        )
    turns_raw = raw.get("turns")
    if not isinstance(turns_raw, list):
        raise ActualModelHostFacadeError(
            "screening timing summary evidence must contain turns"
        )

    turns: list[FastScreeningTurnTiming] = []
    try:
        for turn_index, turn_raw in enumerate(turns_raw, start=1):
            if not isinstance(turn_raw, dict):
                raise TypeError(f"turn {turn_index} must be a JSON object")
            turns.append(
                FastScreeningTurnTiming(
                    turn_index=turn_raw["turn_index"],
                    response_provider_ms=turn_raw["response_provider_ms"],
                    response_outcome=turn_raw["response_outcome"],
                    first_visible_provider_ms=turn_raw["first_visible_provider_ms"],
                    extraction_provider_ms=turn_raw["extraction_provider_ms"],
                    extraction_outcome=turn_raw["extraction_outcome"],
                )
            )
        artifact = FastScreeningTimingArtifact(
            format_version=raw["format_version"],
            screening_id=raw["screening_id"],
            condition_id=raw["condition_id"],
            replicate_id=raw["replicate_id"],
            scenario_id=raw["scenario_id"],
            execution_id=raw["execution_id"],
            run_id=raw["run_id"],
            execution_mode=raw["execution_mode"],
            scenario_elapsed_ms=raw["scenario_elapsed_ms"],
            turns=tuple(turns),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ActualModelHostFacadeError(
            f"invalid screening timing summary evidence: {exc}"
        ) from exc

    if raw != artifact.to_mapping():
        raise ActualModelHostFacadeError(
            "screening timing summary evidence does not match its canonical timing identity"
        )
    return artifact


def _print_capacity_failure(
    *,
    prepared,
    failure: VLLMCapacityAcquisitionFailure,
    condition_role: str,
) -> None:
    mapping: dict[str, object] = {
        "format_version": 1,
        "suite": prepared.plan.screening_id,
        "backend": "vllm",
        "operation": "capacity",
        "condition": condition_role,
        "relaylm_commit": prepared.manifest.relaylm_commit,
        "target_id": prepared.target.target_id,
        "replicate_id": prepared.manifest.replicate_id,
        "observed_max_model_len": (
            prepared.reasoning_capability.backend_attestation.max_model_len
        ),
        "complete": False,
        "error": str(failure),
        "capacity_evidence": (
            failure.artifact.to_mapping() if failure.artifact is not None else None
        ),
    }
    print(
        json.dumps(
            mapping,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        ),
        file=sys.stderr,
    )


def _resolve_vllm_screening_plan_path(
    *,
    repo_root: Path,
    value: str | None,
) -> Path:
    if value is None:
        return repo_root / CANONICAL_VLLM_SCREENING_PLAN_PATH
    if not isinstance(value, str) or not value.strip():
        raise ActualModelHostFacadeError(
            "screening plan path must be a non-empty repository-relative path"
        )
    candidate = Path(value)
    if candidate.is_absolute():
        raise ActualModelHostFacadeError(
            "screening plan path must be repository-relative"
        )
    resolved = (repo_root / candidate).resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ActualModelHostFacadeError(
            "screening plan path must remain inside repo_root"
        ) from exc
    return resolved


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