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

from relaylm.actual_model_evaluation import ActualModelEvidence
from relaylm.actual_model_fast_screening import screening_condition_key_for_role
from relaylm.actual_model_pass2_protocol_diagnostics import (
    Pass2ProtocolDiagnosticRecorder,
    bind_pass2_protocol_diagnostic_artifact,
    instrument_pass2_protocol_diagnostics,
    write_pass2_protocol_diagnostic_artifact,
)
from relaylm.actual_model_vllm import (
    ActualModelVLLMBindingError,
    run_bound_vllm_actual_model_scenario_definition,
    write_vllm_actual_model_execution_result,
)
from relaylm.actual_model_vllm_budget import (
    VLLMCognitiveBudgetDeclarationError,
    load_vllm_two_pass_cognitive_budget_declaration,
    prepare_vllm_screening_condition_with_budget_declaration,
)
from relaylm.actual_model_vllm_capacity import VLLM_MODEL_RUNNER_IDS
from relaylm.actual_model_vllm_host import (
    CANONICAL_VLLM_REASONING_PROOF_PATH,
    CANONICAL_VLLM_SCREENING_PLAN_PATH,
    ActualModelVLLMHostError,
    load_vllm_screening_plan,
)


class Pass2ProtocolDiagnosticRunnerError(ValueError):
    """The bounded Stage R Pass 2 protocol diagnostic cannot run truthfully."""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one existing current Stage R reference scenario with evidence-only "
            "Pass 2 provider/parser failure diagnostics."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--snapshot-root", required=True)
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--model-runner", required=True, choices=VLLM_MODEL_RUNNER_IDS)
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--capacity-evidence-id", required=True)
    parser.add_argument("--capacity-evidence-root", required=True)
    parser.add_argument("--replicate-id", default="protocol-diagnostic-0")
    parser.add_argument("--provider-api-key-env")
    parser.add_argument("--cognitive-budget")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    try:
        relaylm_commit = _current_repo_head(repo_root)
        api_key = _resolve_api_key(args.provider_api_key_env)
        plan = load_vllm_screening_plan(
            repo_root / CANONICAL_VLLM_SCREENING_PLAN_PATH
        )
        condition_key = screening_condition_key_for_role(
            plan,
            "reference_baseline",
        )
        plan = replace(plan, capacity_evidence_id=args.capacity_evidence_id)
        cognitive_budget = (
            load_vllm_two_pass_cognitive_budget_declaration(args.cognitive_budget)
            if args.cognitive_budget is not None
            else None
        )
        prepared = prepare_vllm_screening_condition_with_budget_declaration(
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
        if args.scenario_id not in prepared.scenario_ids:
            raise Pass2ProtocolDiagnosticRunnerError(
                "scenario-id must name an existing scenario in the current Stage R plan"
            )
        result_mapping = asyncio.run(
            _run_prepared_protocol_diagnostic(
                prepared=prepared,
                scenario_id=args.scenario_id,
                workspace_root=args.workspace_root,
                artifact_root=args.artifact_root,
            )
        )
    except (
        ActualModelVLLMBindingError,
        ActualModelVLLMHostError,
        Pass2ProtocolDiagnosticRunnerError,
        VLLMCognitiveBudgetDeclarationError,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "format_version": 1,
                "operation": "pass2_protocol_diagnostic",
                "condition": "reference_baseline",
                "relaylm_commit": relaylm_commit,
                "target_id": prepared.target.target_id,
                "scenario_id": args.scenario_id,
                "replicate_id": prepared.manifest.replicate_id,
                **result_mapping,
            },
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
    )
    return 0


async def _run_prepared_protocol_diagnostic(
    *,
    prepared,
    scenario_id: str,
    workspace_root: str | Path,
    artifact_root: str | Path,
) -> dict[str, object]:
    recorder = Pass2ProtocolDiagnosticRecorder()
    provider = instrument_pass2_protocol_diagnostics(
        prepared.provider,
        recorder=recorder,
    )
    try:
        result = await run_bound_vllm_actual_model_scenario_definition(
            binding=prepared.binding,
            scenario_set=prepared.scenario_set,
            scenario_id=scenario_id,
            fixture_root=prepared.fixture_root,
            workspace_root=(
                Path(workspace_root)
                / prepared.plan.screening_id
                / prepared.screening_condition_id
                / prepared.manifest.replicate_id
                / scenario_id
            ),
            provider=provider,
            cognitive_budget=prepared.cognitive_budget,
        )
        execution_path = write_vllm_actual_model_execution_result(
            result=result,
            artifact_root=artifact_root,
        )
        evidence = result.execution.evidence
        if not isinstance(evidence, ActualModelEvidence):
            raise Pass2ProtocolDiagnosticRunnerError(
                "Pass 2 protocol diagnostic requires ordinary actual-model evidence"
            )
        diagnostic_path: Path | None = None
        diagnostic_id: str | None = None
        if recorder.failures:
            artifact = bind_pass2_protocol_diagnostic_artifact(
                evidence=evidence,
                recorder=recorder,
                execution_id=result.execution_id,
            )
            diagnostic_path = write_pass2_protocol_diagnostic_artifact(
                artifact=artifact,
                artifact_root=artifact_root,
            )
            diagnostic_id = artifact.diagnostic_id
        return {
            "execution_id": result.execution_id,
            "run_id": result.run_id,
            "execution_artifact_path": str(execution_path),
            "protocol_failure_count": len(recorder.failures),
            "protocol_failure_turns": [
                failure.turn_index for failure in recorder.failures
            ],
            "protocol_diagnostic_id": diagnostic_id,
            "protocol_diagnostic_artifact_path": (
                str(diagnostic_path) if diagnostic_path is not None else None
            ),
        }
    finally:
        await prepared.provider.aclose()


def _current_repo_head(root: Path) -> str:
    if not root.is_dir():
        raise Pass2ProtocolDiagnosticRunnerError(
            "repo-root must be an existing directory"
        )
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(head) != 40 or any(char not in "0123456789abcdef" for char in head):
        raise Pass2ProtocolDiagnosticRunnerError(
            "repository HEAD must be an exact lowercase 40-character Git SHA"
        )
    return head


def _resolve_api_key(env_name: str | None) -> str | None:
    if env_name is None:
        return None
    if not isinstance(env_name, str) or not env_name.strip():
        raise Pass2ProtocolDiagnosticRunnerError(
            "provider API key environment name must be non-empty"
        )
    value = os.environ.get(env_name)
    if value is None or not value:
        raise Pass2ProtocolDiagnosticRunnerError(
            f"provider API key environment variable is unavailable: {env_name}"
        )
    return value


if __name__ == "__main__":
    raise SystemExit(main())
