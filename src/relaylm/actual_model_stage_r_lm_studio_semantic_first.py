from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_boundary import (
    evaluate_actual_model_deterministic_boundary,
    write_actual_model_deterministic_boundary_verdict,
)
from relaylm.actual_model_evaluation import ActualModelEvidence, ActualModelRunManifest
from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionResult,
    run_actual_model_scenario_definition,
)
from relaylm.actual_model_execution_artifacts import write_actual_model_execution_result
from relaylm.actual_model_scenarios import ActualModelScenarioSet
from relaylm.actual_model_stage_r_semantics import (
    CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH,
    StageRSemanticAuthority,
    load_current_stage_r_scenario_set,
    load_stage_r_semantic_authority,
)
from relaylm.cognition_execution import CognitionReasoningMode
from relaylm.providers.lm_studio_reasoning import LMStudioReasoningCapabilityAttestation
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import describe_openai_compatible_provider
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningCapabilities,
)
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider


CANONICAL_FIXTURE_PATH = Path("evaluation/actual_model/characters/foundation-v1")
SEMANTIC_FIRST_STAGE_R_FORMAT_VERSION = 1


class SemanticFirstStageRError(ValueError):
    """The declared semantic-first Stage R condition is not internally valid."""


ScenarioExecutor = Callable[
    [str],
    Awaitable[tuple[dict[str, object], str | None]],
]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run current LM Studio Stage R semantics without a content-free provider "
            "preflight. Stable non-secret binding facts are declared by the transaction; "
            "the first provider request is real semantic work."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--request-model", required=True)
    parser.add_argument("--loaded-instance-id", required=True)
    parser.add_argument("--model-artifact", required=True)
    parser.add_argument(
        "--tokenizer-identity",
        default="lmstudio-declared:tokenizer-unreported",
    )
    parser.add_argument("--quantization", required=True)
    parser.add_argument("--context-window", required=True, type=int)
    parser.add_argument(
        "--reasoning-options",
        default="off,on",
        help="Comma-separated stable declared LM Studio reasoning options.",
    )
    parser.add_argument("--reasoning-default", default="on")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--provider-api-key-env")
    parser.add_argument("--replicate-id", default="0")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    provider_base_url = _require_openai_api_base(args.provider_base_url)
    workspace_root = Path(args.workspace_root).resolve()
    artifact_root = Path(args.artifact_root).resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)

    authority = load_stage_r_semantic_authority(
        repo_root / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH
    )
    scenario_set = load_current_stage_r_scenario_set(
        repo_root=repo_root,
        authority=authority,
    )
    reasoning_capability = _declared_reasoning_capability(
        request_model=args.request_model,
        loaded_instance_id=args.loaded_instance_id,
        reasoning_options=args.reasoning_options,
        reasoning_default=args.reasoning_default,
    )
    if "off" not in reasoning_capability.allowed_options:
        raise SemanticFirstStageRError(
            "semantic-first Stage R requires declared LM Studio reasoning option off"
        )
    if args.context_window <= 0:
        raise SemanticFirstStageRError("context-window must be positive")
    for name in (
        "request_model",
        "loaded_instance_id",
        "model_artifact",
        "tokenizer_identity",
        "quantization",
    ):
        value = getattr(args, name)
        if not isinstance(value, str) or not value.strip():
            raise SemanticFirstStageRError(f"{name.replace('_', '-')} must not be empty")

    binding = {
        "format_version": SEMANTIC_FIRST_STAGE_R_FORMAT_VERSION,
        "binding_source": "declared_stable_non_secret",
        "native_provider_preflight": False,
        "provider_base_url": provider_base_url,
        "request_model": args.request_model,
        "loaded_instance_id": args.loaded_instance_id,
        "model_artifact": args.model_artifact,
        "tokenizer_identity": args.tokenizer_identity,
        "quantization": args.quantization,
        "context_window": args.context_window,
        "reasoning": {
            "allowed_options": list(reasoning_capability.allowed_options),
            "default": reasoning_capability.default,
            "requested": "off",
            "wire": {"reasoning_effort": "none"},
        },
    }
    _write_json_create_once(
        artifact_root / "lm-studio-semantic-first-binding.json",
        binding,
    )

    summary = asyncio.run(
        _run_stage_r(
            repo_root=repo_root,
            provider_base_url=provider_base_url,
            request_model=args.request_model,
            loaded_instance_id=args.loaded_instance_id,
            model_artifact=args.model_artifact,
            tokenizer_identity=args.tokenizer_identity,
            context_window=args.context_window,
            workspace_root=workspace_root,
            artifact_root=artifact_root,
            replicate_id=args.replicate_id,
            api_key_env=args.provider_api_key_env,
            authority=authority,
            scenario_set=scenario_set,
            reasoning_capability=reasoning_capability,
            binding=binding,
        )
    )
    _write_json_create_once(
        artifact_root / "stage-r-lm-studio-semantic-first-summary.json",
        summary,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


async def _run_stage_r(
    *,
    repo_root: Path,
    provider_base_url: str,
    request_model: str,
    loaded_instance_id: str,
    model_artifact: str,
    tokenizer_identity: str,
    context_window: int,
    workspace_root: Path,
    artifact_root: Path,
    replicate_id: str,
    api_key_env: str | None,
    authority: StageRSemanticAuthority,
    scenario_set: ActualModelScenarioSet,
    reasoning_capability: LMStudioReasoningCapabilityAttestation,
    binding: dict[str, object],
) -> dict[str, object]:
    api_key = os.environ.get(api_key_env) if api_key_env else None
    if api_key_env and not api_key:
        raise SemanticFirstStageRError(
            f"provider API key environment variable is empty: {api_key_env}"
        )
    provider = OpenAICompatibleTwoPassProvider(
        base_url=provider_base_url,
        model=request_model,
        api_key=api_key,
        decoding_config=OpenAICompatibleDecodingConfig(
            temperature=authority.temperature,
            top_p=authority.top_p,
            seed=authority.seed,
        ),
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"temperature", "top_p"})
        ),
        lm_studio_reasoning_capability=reasoning_capability,
    )
    identity = describe_openai_compatible_provider(provider)
    fixture_root = repo_root / CANONICAL_FIXTURE_PATH
    manifest = ActualModelRunManifest(
        relaylm_commit=_git_head(repo_root),
        character_fixture_id=scenario_set.character_fixture_id,
        character_fixture_revision=character_fixture_revision(fixture_root),
        provider_identity=(
            "lm_studio_declared_semantic_first:"
            f"{request_model}:{loaded_instance_id}:reasoning_effort=none"
        ),
        adapter_identity=identity.adapter_identity,
        model_artifact=model_artifact,
        tokenizer_identity=tokenizer_identity,
        effective_context_window=context_window,
        decoding_configuration=tuple(
            sorted(identity.effective_decoding_configuration.items())
        ),
        structured_output_schema_version="relaylm-cognitive-output-v1",
        scenario_set_version=scenario_set.scenario_set_version,
        condition_id="stage-r-lm-studio-semantic-first-v1",
        continuity_runtime=authority.continuity_runtime,
        execution_path=authority.execution_path,
        seed=authority.seed,
        provider_capabilities=identity.provider_capabilities,
        replicate_id=replicate_id,
        cognition_execution=authority.cognition_execution,
        cognition_pass_requests=authority.pass_requests(
            reasoning_mode=CognitionReasoningMode.OFF
        ),
    )

    async def execute_scenario(
        scenario_id: str,
    ) -> tuple[dict[str, object], str | None]:
        result = await run_actual_model_scenario_definition(
            scenario_set=scenario_set,
            scenario_id=scenario_id,
            fixture_root=fixture_root,
            workspace_root=workspace_root / scenario_id,
            provider=provider,
            manifest=manifest,
        )
        execution_path = write_actual_model_execution_result(
            result=result,
            artifact_root=artifact_root,
        )
        verdict = evaluate_actual_model_deterministic_boundary(result=result)
        boundary_path = write_actual_model_deterministic_boundary_verdict(
            verdict=verdict,
            artifact_root=artifact_root,
        )
        stop_reason = _material_execution_failure(result)
        return (
            {
                "scenario_id": scenario_id,
                "execution_id": result.execution_id,
                "run_id": result.run_id,
                "execution_artifact": str(execution_path),
                "boundary_verdict": verdict.outcome,
                "boundary_artifact": str(boundary_path),
                "material_execution_failure": stop_reason,
            },
            stop_reason,
        )

    try:
        executions, stop_reason = await _run_fail_fast_sequence(
            scenario_ids=authority.scenario_ids,
            execute=execute_scenario,
        )
    finally:
        await provider.aclose()

    return {
        "format_version": SEMANTIC_FIRST_STAGE_R_FORMAT_VERSION,
        "semantic_authority_id": authority.authority_id,
        "scenario_set_revision": authority.scenario_set_revision,
        "binding": binding,
        "reasoning_preference": authority.reasoning_preference,
        "reasoning_realization": "declared_off_plus_actual_completion_evidence_required",
        "reasoning_wire_control": "reasoning_effort=none",
        "stop_reason": stop_reason,
        "executions": executions,
    }


async def _run_fail_fast_sequence(
    *,
    scenario_ids: Sequence[str],
    execute: ScenarioExecutor,
) -> tuple[list[dict[str, object]], str | None]:
    executions: list[dict[str, object]] = []
    terminal_reason: str | None = None
    for scenario_id in scenario_ids:
        execution, stop_reason = await execute(scenario_id)
        executions.append(execution)
        if stop_reason is not None:
            terminal_reason = stop_reason
            break
    return executions, terminal_reason


def _material_execution_failure(
    result: ActualModelScenarioExecutionResult,
) -> str | None:
    evidence = result.evidence
    if not isinstance(evidence, ActualModelEvidence):
        return None
    if evidence.request_failure is not None:
        return "request_failure"
    for turn in evidence.turns:
        observation = turn.cognition_execution
        if observation is not None and observation.pass2_status == "failed":
            return f"pass2_failed_turn_{turn.turn_index}"
    return None


def _declared_reasoning_capability(
    *,
    request_model: str,
    loaded_instance_id: str,
    reasoning_options: str,
    reasoning_default: str,
) -> LMStudioReasoningCapabilityAttestation:
    options = tuple(
        sorted(
            item.strip()
            for item in reasoning_options.split(",")
            if item.strip()
        )
    )
    if not options:
        raise SemanticFirstStageRError("reasoning-options must not be empty")
    if reasoning_default not in options:
        raise SemanticFirstStageRError(
            "reasoning-default must be present in reasoning-options"
        )
    return LMStudioReasoningCapabilityAttestation(
        request_model=request_model,
        loaded_instance_id=loaded_instance_id,
        reasoning_exposed=True,
        allowed_options=options,
        default=reasoning_default,
        capabilities=OpenAICompatibleReasoningCapabilities(
            mode_control_supported=True,
            supported_mode_values=options,
            token_budget_supported=False,
        ),
    )


def _require_openai_api_base(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise SemanticFirstStageRError(
            "provider-base-url must be a non-empty HTTP(S) URL ending in /v1"
        )
    value = base_url.rstrip("/")
    if not value.startswith(("http://", "https://")) or not value.endswith("/v1"):
        raise SemanticFirstStageRError(
            "provider-base-url must be an HTTP(S) URL ending in /v1"
        )
    return value


def _git_head(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    head = completed.stdout.strip()
    if completed.returncode != 0 or len(head) != 40:
        raise SemanticFirstStageRError("cannot determine exact RelayLM checkout HEAD")
    return head


def _write_json_create_once(path: Path, value: object) -> None:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    ) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != payload:
            raise SemanticFirstStageRError(
                f"artifact already exists with different content: {path}"
            )


if __name__ == "__main__":
    raise SystemExit(main())
