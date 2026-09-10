"""Evaluation-only #2385 Continuity label diagnostic on current llama.cpp.

The physical admission and Stage R execution path remain the current llama.cpp
carriage.  Only Pass 2's diagnostic transport is changed: the model-facing
``unresolved`` coordinate is shown as ``open_question`` and is translated back
before the existing canonical parser, deterministic boundary, and scorer.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_boundary import (
    evaluate_actual_model_deterministic_boundary,
    write_actual_model_deterministic_boundary_verdict,
)
from relaylm.actual_model_continuity_diagnostic import (
    CANONICAL_UNRESOLVED_KIND,
    LABEL_INVARIANCE_DIAGNOSTIC_FORMAT_VERSION,
    SHADOW_OPEN_QUESTION_KIND,
    apply_fixed_slot_transport,
    apply_label_alias_to_request_body,
    parse_label_alias_wire,
)
from relaylm.actual_model_evaluation import ActualModelEvidence, ActualModelRunManifest
from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionResult,
    run_actual_model_scenario_definition,
)
from relaylm.actual_model_execution_artifacts import write_actual_model_execution_result
from relaylm.actual_model_llama_cpp import LlamaCppRuntimeIdentity
from relaylm.actual_model_llama_cpp_thinking import (
    LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS,
    LlamaCppThinkingChatInputCounter,
)
from relaylm.actual_model_quality import evaluate_labeled_proposals
from relaylm.actual_model_scenarios import ActualModelScenarioSet
from relaylm.actual_model_stage_r_llama_cpp import (
    CANONICAL_FIXTURE_PATH,
    DEFAULT_TARGET_PATH,
    QUALIFICATION_FORMAT_VERSION,
    LlamaCppStageRQualificationError,
    _CompletionObservingLlamaProvider,
    _LLAMA_CPP_DECODING_CAPABILITIES,
    _completion_evidence_is_thinking_off,
    _failure_summary,
    _frozen_core_fingerprint,
    _git_identity,
    _prepare_physical_condition,
    _require_clean_repo,
    _require_local_llama_api_base,
    _runtime_mapping,
    _write_json_create_once,
)
from relaylm.actual_model_stage_r_semantics import (
    CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH,
    StageRSemanticAuthority,
    load_current_stage_r_scenario_set,
    load_stage_r_semantic_authority,
)
from relaylm.actual_model_targets import (
    ActualModelArtifactTarget,
    ActualModelArtifactVerification,
)
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.providers.llama_cpp_reasoning import LlamaCppReasoningCapabilityAttestation
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    _load_cognitive_wire_json,
    _require_candidate_sources_in_cognitive_input,
)
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig
from relaylm.providers.openai_compatible_identity import describe_openai_compatible_provider
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import (
    _completion_content_and_metadata,
    _extraction_request_body,
    _normalize_extraction_json_content,
    _resolve_extraction_structured_output_mode,
)


DIAGNOSTIC_NAME = "continuity_semantic_label_invariance"
DIAGNOSTIC_CONDITION_ID = "stage-r-llama-cpp-continuity-label-invariance-v1"
DIAGNOSTIC_SCHEMA_VERSION = "relaylm-continuity-label-invariance-diagnostic-v1"


def _label_alias_extraction_request_body(
    *,
    provider: "ContinuityLabelInvarianceLlamaProvider",
    extraction_input: CognitionExtractionInput,
    pass_request: CognitionPassRequest | None,
    reasoning_request: OpenAICompatibleReasoningRequest | None = None,
) -> dict[str, Any]:
    """Build the exact llama.cpp Pass 2 body before counting and posting it."""

    decoding_config, effective_reasoning = provider._resolve_llama_cpp_pass_request(
        pass_request=pass_request,
        reasoning_request=reasoning_request,
    )
    structured_output_mode = _resolve_extraction_structured_output_mode(
        pass_request=pass_request,
        provider=provider,
    )
    if structured_output_mode is not CognitionStructuredOutputMode.NATIVE:
        raise ProviderProtocolError(
            "llama.cpp label-invariance diagnostic requires native Pass 2 structured output"
        )
    body = _extraction_request_body(
        model=provider.model,
        extraction_input=extraction_input,
        decoding=decoding_config.to_mapping(),
        structured_output_mode=structured_output_mode,
    )
    body.update(provider._llama_cpp_reasoning_fields(effective_reasoning))
    return apply_label_alias_to_request_body(apply_fixed_slot_transport(body))


class ContinuityLabelInvarianceLlamaProvider(_CompletionObservingLlamaProvider):
    """Current llama.cpp provider with an evaluation-only shadow Pass 2 label."""

    def __init__(
        self,
        *args: Any,
        label_observation_root: Path,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._label_observation_root = label_observation_root
        self.label_decision_artifacts: list[Path] = []

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
    ) -> CognitionExtractionOutput:
        body = _label_alias_extraction_request_body(
            provider=self,
            extraction_input=extraction_input,
            pass_request=pass_request,
            reasoning_request=reasoning_request,
        )
        envelope = await self._post_two_pass(body=body, boundary="extraction")
        content, completion = _completion_content_and_metadata(envelope)
        wire = _load_cognitive_wire_json(
            _normalize_extraction_json_content(content),
            invalid_message="label-invariance extraction content is not valid JSON",
        )
        output, shadow_decisions = parse_label_alias_wire(
            wire=wire,
            completion=completion,
        )
        _require_candidate_sources_in_cognitive_input(
            output,
            extraction_input.cognitive_input,
        )
        sequence_index = len(self.label_decision_artifacts) + 1
        observation_path = self._label_observation_root / (
            f"{sequence_index:04d}-extraction.json"
        )
        _write_json_create_once(
            observation_path,
            {
                "format_version": LABEL_INVARIANCE_DIAGNOSTIC_FORMAT_VERSION,
                "diagnostic": DIAGNOSTIC_NAME,
                "sequence_index": sequence_index,
                "originating_event_id": extraction_input.originating_event_id,
                "shadow_alias": {
                    CANONICAL_UNRESOLVED_KIND: SHADOW_OPEN_QUESTION_KIND,
                },
                "continuity_decisions": shadow_decisions,
                "canonical_translation_boundary": (
                    "before_existing_parser_and_deterministic_authority"
                ),
            },
        )
        self.label_decision_artifacts.append(observation_path)
        return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run current llama.cpp Stage R with the evaluation-only Continuity "
            "semantic-label invariance transport."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--request-model", required=True)
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--target-path")
    parser.add_argument("--llama-upstream-revision", required=True)
    parser.add_argument("--llama-version", required=True)
    parser.add_argument("--expected-build-number", required=True, type=int)
    parser.add_argument("--expected-context-window", required=True, type=int)
    parser.add_argument("--expected-slots", required=True, type=int)
    parser.add_argument("--context-shift-disabled", action="store_true")
    parser.add_argument("--gpu-identity")
    parser.add_argument("--gpu-offload-args")
    parser.add_argument("--launch-args")
    parser.add_argument("--server-log-path", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--provider-api-key-env")
    parser.add_argument("--replicate-id", default="0")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    workspace_root = Path(args.workspace_root).resolve()
    artifact_root = Path(args.artifact_root).resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)
    _require_clean_repo(repo_root)
    head, tree = _git_identity(repo_root)
    core_fingerprint = _frozen_core_fingerprint(repo_root)
    base_url = _require_local_llama_api_base(args.provider_base_url)
    api_key = os.environ.get(args.provider_api_key_env) if args.provider_api_key_env else None
    if args.provider_api_key_env and not api_key:
        raise LlamaCppStageRQualificationError(
            f"provider API key environment variable is empty: {args.provider_api_key_env}"
        )

    summary_path = artifact_root / "stage-r-llama-cpp-summary.json"
    try:
        preflight = _prepare_physical_condition(
            repo_root=repo_root,
            base_url=base_url,
            request_model=args.request_model,
            artifact_path=Path(args.artifact_path).resolve(),
            target_path=(
                Path(args.target_path)
                if args.target_path
                else DEFAULT_TARGET_PATH
            ),
            upstream_revision=args.llama_upstream_revision,
            llama_version=args.llama_version,
            expected_build_number=args.expected_build_number,
            expected_context_window=args.expected_context_window,
            expected_slots=args.expected_slots,
            context_shift_disabled=args.context_shift_disabled,
            api_key=api_key,
            artifact_root=artifact_root,
            gpu_identity=args.gpu_identity,
            gpu_offload_args=args.gpu_offload_args,
            launch_args=args.launch_args,
            server_log_path=Path(args.server_log_path).resolve(),
        )
    except Exception as exc:
        summary = _failure_summary(
            classification="INFRA_INVALID",
            phase="physical_preflight",
            head=head,
            tree=tree,
            core_fingerprint=core_fingerprint,
            base_url=base_url,
            exc=exc,
            semantic_execution_started=False,
        )
        summary["diagnostic"] = DIAGNOSTIC_NAME
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    diagnostic_binding = {
        "format_version": LABEL_INVARIANCE_DIAGNOSTIC_FORMAT_VERSION,
        "diagnostic": DIAGNOSTIC_NAME,
        "shadow_alias": {
            CANONICAL_UNRESOLVED_KIND: SHADOW_OPEN_QUESTION_KIND,
        },
        "canonical_translation_boundary": (
            "before_existing_parser_and_deterministic_authority"
        ),
        "physical_binding_artifact": str(
            artifact_root / "llama-cpp-physical-binding.json"
        ),
        "reasoning": {
            "requested": "off",
            "wire": {"reasoning_effort": "none"},
        },
    }
    _write_json_create_once(
        artifact_root / "llama-cpp-continuity-label-invariance-binding.json",
        diagnostic_binding,
    )

    authority = load_stage_r_semantic_authority(
        repo_root / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH
    )
    scenario_set = load_current_stage_r_scenario_set(
        repo_root=repo_root,
        authority=authority,
    )
    try:
        semantic = asyncio.run(
            _run_stage_r(
                repo_root=repo_root,
                base_url=base_url,
                request_model=args.request_model,
                workspace_root=workspace_root,
                artifact_root=artifact_root,
                replicate_id=args.replicate_id,
                api_key=api_key,
                authority=authority,
                scenario_set=scenario_set,
                target=preflight["target"],
                verification=preflight["verification"],
                runtime=preflight["runtime"],
                counter=preflight["counter"],
            )
        )
    except Exception as exc:
        summary = _failure_summary(
            classification="INFRA_INVALID",
            phase="semantic_transport",
            head=head,
            tree=tree,
            core_fingerprint=core_fingerprint,
            base_url=base_url,
            exc=exc,
            semantic_execution_started=True,
        )
        summary["diagnostic"] = DIAGNOSTIC_NAME
        summary["preflight"] = preflight["evidence"]
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    summary = {
        "format_version": QUALIFICATION_FORMAT_VERSION,
        "diagnostic": DIAGNOSTIC_NAME,
        "classification": semantic["classification"],
        "phase": "complete",
        "relaylm": {
            "head": head,
            "tree": tree,
            "core_semantic_fingerprint": core_fingerprint,
        },
        "provider_base_url": base_url,
        "preflight": preflight["evidence"],
        "semantic": semantic,
        "provider_request_count": 2 + semantic["provider_request_count"],
        "semantic_retry_count": 0,
        "fallback_count": 0,
        "product_quality_review": "not_run_by_host",
    }
    _write_json_create_once(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if semantic["classification"] == "PASS" else 1


async def _run_stage_r(
    *,
    repo_root: Path,
    base_url: str,
    request_model: str,
    workspace_root: Path,
    artifact_root: Path,
    replicate_id: str,
    api_key: str | None,
    authority: StageRSemanticAuthority,
    scenario_set: ActualModelScenarioSet,
    target: ActualModelArtifactTarget,
    verification: ActualModelArtifactVerification,
    runtime: LlamaCppRuntimeIdentity,
    counter: LlamaCppThinkingChatInputCounter,
) -> dict[str, object]:
    client = httpx.AsyncClient(
        timeout=LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS,
        trust_env=False,
    )
    provider = ContinuityLabelInvarianceLlamaProvider(
        base_url=base_url,
        model=request_model,
        api_key=api_key,
        decoding_config=OpenAICompatibleDecodingConfig(
            temperature=authority.temperature,
            top_p=authority.top_p,
            seed=authority.seed,
        ),
        decoding_capabilities=_LLAMA_CPP_DECODING_CAPABILITIES,
        llama_cpp_reasoning_capability=LlamaCppReasoningCapabilityAttestation(
            request_model=request_model,
            enable_thinking_supported=True,
        ),
        http_client=client,
        input_counter=counter,
        observation_root=artifact_root / "llama-cpp-request-observations",
        label_observation_root=(
            artifact_root / "llama-cpp-continuity-label-decision-observations"
        ),
    )
    identity = describe_openai_compatible_provider(provider)
    fixture_root = repo_root / CANONICAL_FIXTURE_PATH
    manifest = ActualModelRunManifest(
        relaylm_commit=_git_identity(repo_root)[0],
        character_fixture_id=scenario_set.character_fixture_id,
        character_fixture_revision=character_fixture_revision(fixture_root),
        provider_identity=(
            "llama_cpp_continuity_label_invariance:"
            f"{runtime.upstream_revision}:{request_model}:reasoning_effort=none"
        ),
        adapter_identity=identity.adapter_identity,
        model_artifact=target.model_artifact_identity,
        tokenizer_identity=target.tokenizer_identity,
        effective_context_window=runtime.context_limit,
        decoding_configuration=tuple(
            sorted(identity.effective_decoding_configuration.items())
        ),
        structured_output_schema_version=DIAGNOSTIC_SCHEMA_VERSION,
        scenario_set_version=scenario_set.scenario_set_version,
        condition_id=DIAGNOSTIC_CONDITION_ID,
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

    executions: list[dict[str, object]] = []
    classification = "PASS"
    try:
        for scenario_id in authority.scenario_ids:
            label_start = len(provider.label_decision_artifacts)
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
            request_failure = _request_failure(result)
            metrics = None
            metric_fail = False
            if isinstance(result.evidence, ActualModelEvidence):
                scored = evaluate_labeled_proposals(
                    evidence=result.evidence,
                    labels=result.plan.definition.proposal_labels,
                    scoring=result.plan.definition.effective_proposal_scoring,
                )
                metrics = scored.to_mapping()
                metric_fail = any(
                    channel.scored
                    and (
                        channel.false_positive_count > 0
                        or channel.false_negative_count > 0
                    )
                    for channel in (scored.state, scored.continuity)
                )
            executions.append(
                {
                    "scenario_id": scenario_id,
                    "execution_id": result.execution_id,
                    "run_id": result.run_id,
                    "execution_artifact": str(execution_path),
                    "boundary_verdict": verdict.outcome,
                    "boundary_artifact": str(boundary_path),
                    "proposal_metrics": metrics,
                    "request_failure": request_failure,
                    "label_decision_artifacts": [
                        str(path)
                        for path in provider.label_decision_artifacts[label_start:]
                    ],
                }
            )
            if request_failure is not None:
                classification = "INFRA_INVALID"
                break
            if verdict.outcome != "pass" or metric_fail:
                classification = "SEMANTIC_FAIL"
    finally:
        await provider.aclose()
        await client.aclose()

    reasoning_evidence_valid = _completion_evidence_is_thinking_off(
        provider.completion_artifacts
    )
    if not reasoning_evidence_valid:
        classification = "INFRA_INVALID"
    return {
        "diagnostic": DIAGNOSTIC_NAME,
        "classification": classification,
        "semantic_authority_id": authority.authority_id,
        "scenario_set_revision": authority.scenario_set_revision,
        "artifact_verification": verification.to_mapping(),
        "runtime": _runtime_mapping(runtime),
        "shadow_alias": {
            CANONICAL_UNRESOLVED_KIND: SHADOW_OPEN_QUESTION_KIND,
        },
        "canonical_translation_boundary": (
            "before_existing_parser_and_deterministic_authority"
        ),
        "reasoning": {
            "requested": "off",
            "wire": {"reasoning_effort": "none"},
            "completion_evidence_valid": reasoning_evidence_valid,
        },
        "provider_request_count": len(provider.completion_artifacts),
        "completion_observation_artifacts": [
            str(path) for path in provider.completion_artifacts
        ],
        "input_count_artifacts": [
            str(path) for path in provider.input_count_artifacts
        ],
        "label_decision_observation_count": len(provider.label_decision_artifacts),
        "label_decision_observation_artifacts": [
            str(path) for path in provider.label_decision_artifacts
        ],
        "executions": executions,
    }


def _request_failure(result: ActualModelScenarioExecutionResult) -> str | None:
    evidence = result.evidence
    if isinstance(evidence, ActualModelEvidence) and evidence.request_failure is not None:
        return "request_failure"
    return None


if __name__ == "__main__":
    raise SystemExit(main())
