from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_boundary import (
    evaluate_actual_model_deterministic_boundary,
    write_actual_model_deterministic_boundary_verdict,
)
from relaylm.actual_model_continuity_diagnostic import (
    CANONICAL_UNRESOLVED_KIND,
    LABEL_INVARIANCE_DIAGNOSTIC_FORMAT_VERSION,
    LABEL_INVARIANCE_EXTRACTION_SCHEMA,
    LABEL_INVARIANCE_SCHEMA_NAME,
    SHADOW_OPEN_QUESTION_KIND,
    alias_cognitive_input_json,
    alias_projected_continuity_context,
    apply_label_alias_to_request_body,
    label_alias_prompt,
    parse_label_alias_wire,
)
from relaylm.actual_model_evaluation import ActualModelRunManifest
from relaylm.actual_model_execution import run_actual_model_scenario_definition
from relaylm.actual_model_execution_artifacts import write_actual_model_execution_result
from relaylm.actual_model_scenarios import ActualModelScenarioSet
from relaylm.actual_model_stage_r_lm_studio_fixed_continuity_slots import (
    FixedContinuitySlotDiagnosticProvider,
    _fixed_slot_request_body,
)
from relaylm.actual_model_stage_r_lm_studio_semantic_first import (
    CANONICAL_FIXTURE_PATH,
    _declared_reasoning_capability,
    _git_head,
    _material_execution_failure,
    _require_openai_api_base,
    _run_fail_fast_sequence,
    _write_json_create_once,
)
from relaylm.actual_model_stage_r_semantics import (
    CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH,
    StageRSemanticAuthority,
    load_current_stage_r_scenario_set,
    load_stage_r_semantic_authority,
)
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
    CognitionReasoningMode,
)
from relaylm.providers.lm_studio_reasoning import LMStudioReasoningCapabilityAttestation
from relaylm.providers.openai_compatible import (
    _load_cognitive_wire_json,
    _require_candidate_sources_in_cognitive_input,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import (
    describe_openai_compatible_provider,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningRequest,
)
from relaylm.providers.openai_compatible_two_pass import (
    _completion_content_and_metadata,
    _normalize_extraction_json_content,
)
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityAttestation,
)


__all__ = [
    "LABEL_INVARIANCE_EXTRACTION_SCHEMA",
    "LABEL_INVARIANCE_SCHEMA_NAME",
    "SHADOW_OPEN_QUESTION_KIND",
]

# Preserve the old module's internal helper names for existing diagnostic tests
# while keeping the implementation in the provider-neutral module.
_alias_cognitive_input_json = alias_cognitive_input_json
_alias_projected_continuity_context = alias_projected_continuity_context
_label_alias_prompt = label_alias_prompt


def _label_alias_request_body(
    *,
    provider: FixedContinuitySlotDiagnosticProvider,
    extraction_input: CognitionExtractionInput,
    pass_request: CognitionPassRequest | None,
    reasoning_request: OpenAICompatibleReasoningRequest | None,
    vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None,
    lm_studio_reasoning_capability: LMStudioReasoningCapabilityAttestation | None,
) -> dict[str, Any]:
    body = _fixed_slot_request_body(
        provider=provider,
        extraction_input=extraction_input,
        pass_request=pass_request,
        reasoning_request=reasoning_request,
        vllm_reasoning_capability=vllm_reasoning_capability,
        lm_studio_reasoning_capability=lm_studio_reasoning_capability,
    )
    return apply_label_alias_to_request_body(body)


def _parse_label_alias_wire(
    *,
    wire: object,
    completion: object,
) -> tuple[CognitionExtractionOutput, dict[str, object]]:
    return parse_label_alias_wire(wire=wire, completion=completion)


class ContinuityLabelInvarianceDiagnosticProvider(
    FixedContinuitySlotDiagnosticProvider
):
    """Fixed-slot shadow provider with an aliased unresolved model-facing label."""

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
        vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
        lm_studio_reasoning_capability: (
            LMStudioReasoningCapabilityAttestation | None
        ) = None,
    ) -> CognitionExtractionOutput:
        body = _label_alias_request_body(
            provider=self,
            extraction_input=extraction_input,
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            vllm_reasoning_capability=vllm_reasoning_capability,
            lm_studio_reasoning_capability=lm_studio_reasoning_capability,
        )
        envelope = await self._post_two_pass(body=body, boundary="extraction")
        content, completion = _completion_content_and_metadata(envelope)
        wire = _load_cognitive_wire_json(
            _normalize_extraction_json_content(content),
            invalid_message="label-invariance extraction content is not valid JSON",
        )
        output, decisions = _parse_label_alias_wire(
            wire=wire,
            completion=completion,
        )
        _require_candidate_sources_in_cognitive_input(
            output,
            extraction_input.cognitive_input,
        )
        sequence_index = len(self.slot_observation_artifacts) + 1
        observation_path = self._slot_observation_root / (
            f"{sequence_index:04d}-extraction.json"
        )
        _write_json_create_once(
            observation_path,
            {
                "format_version": LABEL_INVARIANCE_DIAGNOSTIC_FORMAT_VERSION,
                "diagnostic": "continuity_semantic_label_invariance",
                "sequence_index": sequence_index,
                "originating_event_id": extraction_input.originating_event_id,
                "shadow_alias": {
                    CANONICAL_UNRESOLVED_KIND: SHADOW_OPEN_QUESTION_KIND,
                },
                "continuity_decisions": decisions,
            },
        )
        self.slot_observation_artifacts.append(observation_path)
        return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run current LM Studio Stage R with an evaluation-only Continuity "
            "semantic-label invariance transport."
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
    parser.add_argument("--reasoning-options", default="off,on")
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
        raise ValueError(
            "label-invariance diagnostic requires declared LM Studio "
            "reasoning option off"
        )
    if args.context_window <= 0:
        raise ValueError("context-window must be positive")

    binding = {
        "format_version": LABEL_INVARIANCE_DIAGNOSTIC_FORMAT_VERSION,
        "diagnostic": "continuity_semantic_label_invariance",
        "shadow_alias": {CANONICAL_UNRESOLVED_KIND: SHADOW_OPEN_QUESTION_KIND},
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
        artifact_root / "lm-studio-continuity-label-invariance-binding.json",
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
        artifact_root / "stage-r-lm-studio-continuity-label-invariance-summary.json",
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
        raise ValueError(
            f"provider API key environment variable is empty: {api_key_env}"
        )
    provider = ContinuityLabelInvarianceDiagnosticProvider(
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
        completion_observation_root=(
            artifact_root / "lm-studio-continuity-label-completion-observations"
        ),
        slot_observation_root=(
            artifact_root / "lm-studio-continuity-label-decision-observations"
        ),
    )
    identity = describe_openai_compatible_provider(provider)
    fixture_root = repo_root / CANONICAL_FIXTURE_PATH
    manifest = ActualModelRunManifest(
        relaylm_commit=_git_head(repo_root),
        character_fixture_id=scenario_set.character_fixture_id,
        character_fixture_revision=character_fixture_revision(fixture_root),
        provider_identity=(
            "lm_studio_declared_continuity_label_invariance:"
            f"{request_model}:{loaded_instance_id}:reasoning_effort=none"
        ),
        adapter_identity=identity.adapter_identity,
        model_artifact=model_artifact,
        tokenizer_identity=tokenizer_identity,
        effective_context_window=context_window,
        decoding_configuration=tuple(
            sorted(identity.effective_decoding_configuration.items())
        ),
        structured_output_schema_version=(
            "relaylm-continuity-label-invariance-diagnostic-v1"
        ),
        scenario_set_version=scenario_set.scenario_set_version,
        condition_id="stage-r-lm-studio-continuity-label-invariance-v1",
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
        completion_start = len(provider.completion_observation_artifacts)
        slot_start = len(provider.slot_observation_artifacts)
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
                "completion_observation_artifacts": [
                    str(path)
                    for path in provider.completion_observation_artifacts[
                        completion_start:
                    ]
                ],
                "label_decision_artifacts": [
                    str(path)
                    for path in provider.slot_observation_artifacts[slot_start:]
                ],
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
        "format_version": LABEL_INVARIANCE_DIAGNOSTIC_FORMAT_VERSION,
        "diagnostic": "continuity_semantic_label_invariance",
        "shadow_alias": {CANONICAL_UNRESOLVED_KIND: SHADOW_OPEN_QUESTION_KIND},
        "semantic_authority_id": authority.authority_id,
        "scenario_set_revision": authority.scenario_set_revision,
        "binding": binding,
        "reasoning_preference": authority.reasoning_preference,
        "reasoning_realization": (
            "declared_off_plus_actual_completion_evidence_required"
        ),
        "reasoning_wire_control": "reasoning_effort=none",
        "completion_observation_count": len(provider.completion_observation_artifacts),
        "completion_observation_artifacts": [
            str(path) for path in provider.completion_observation_artifacts
        ],
        "label_decision_observation_count": len(provider.slot_observation_artifacts),
        "label_decision_observation_artifacts": [
            str(path) for path in provider.slot_observation_artifacts
        ],
        "stop_reason": stop_reason,
        "executions": executions,
    }


if __name__ == "__main__":
    raise SystemExit(main())
