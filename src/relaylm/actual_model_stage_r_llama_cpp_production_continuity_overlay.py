"""Four-generation llama.cpp host for the #2593 production-overlay discriminator."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_llama_cpp_thinking import LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS
from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    CONDITION_ID,
    DIAGNOSTIC_NAME,
    PRIMARY_SCENARIO_ID,
    PRIMARY_TURN_INDEX,
    SCHEMA_VERSION,
    RetainedFormationBinding,
    assert_production_schema_unchanged,
    build_overlay_extraction_request_body,
    load_retained_formation_binding,
)
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
from relaylm.continuity import ContinuityCandidate, ContinuityContext
from relaylm.providers.llama_cpp_reasoning import LlamaCppReasoningCapabilityAttestation
from relaylm.providers.openai_compatible import _require_candidate_sources_in_cognitive_input
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import _parse_extraction_completion
from relaylm.state import StateCandidate
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime
from relaylm.two_pass_turn import (
    CognitionExecutionRuntime,
    TwoPassExtractionStatus,
    run_user_turn_two_pass,
)


SUMMARY_FILENAME = "production-continuity-overlay-t2-summary.json"
HOST_FORMAT_VERSION = 1


class ProductionContinuityOverlayLlamaProvider(_CompletionObservingLlamaProvider):
    """Production-exact T1 extraction and one overlaid production T2 extraction."""

    def __init__(self, *args: Any, retained_binding: RetainedFormationBinding, overlay_artifact_root: Path, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._retained_binding = retained_binding
        self._overlay_artifact_root = overlay_artifact_root
        self.extraction_call_count = 0
        self.overlay_generation_count = 0
        self.overlay_request_artifacts: list[Path] = []
        self.overlay_raw_artifacts: list[Path] = []
        self.overlay_binding_artifacts: list[Path] = []
        self.t1_extraction_output: CognitionExtractionOutput | None = None
        self.t2_extraction_output: CognitionExtractionOutput | None = None

    async def generate_extraction(self, extraction_input: CognitionExtractionInput, *, pass_request: CognitionPassRequest | None = None, reasoning_request: OpenAICompatibleReasoningRequest | None = None) -> CognitionExtractionOutput:
        self.extraction_call_count += 1
        if self.extraction_call_count == 1:
            output = await super().generate_extraction(extraction_input, pass_request=pass_request, reasoning_request=reasoning_request)
            self.t1_extraction_output = output
            return output
        if self.extraction_call_count != 2:
            raise LlamaCppStageRQualificationError("production overlay diagnostic permits exactly two extraction calls")

        prepared = build_overlay_extraction_request_body(provider=self, extraction_input=extraction_input, pass_request=pass_request, binding=self._retained_binding, reasoning_request=reasoning_request)
        assert_production_schema_unchanged(prepared)
        self.overlay_generation_count += 1
        sequence = self.overlay_generation_count
        baseline_path = self._overlay_artifact_root / f"{sequence:04d}-t2-production-baseline-request.json"
        request_path = self._overlay_artifact_root / f"{sequence:04d}-t2-retained-overlay-request.json"
        _write_json_create_once(baseline_path, prepared.baseline_body)
        _write_json_create_once(request_path, prepared.body)
        self.overlay_request_artifacts.extend((baseline_path, request_path))

        binding_path = self._overlay_artifact_root / f"{sequence:04d}-t2-retained-overlay-binding.json"
        _write_json_create_once(binding_path, {
            "format_version": HOST_FORMAT_VERSION,
            "diagnostic": DIAGNOSTIC_NAME,
            "retained_artifact": self._retained_binding.artifact_path,
            "retained_artifact_sha256": self._retained_binding.sha256,
            "retained_source_event_id": prepared.retained_source_event_id,
            "run_local_source_event_id": prepared.run_local_source_event_id,
            "provenance_rebound": True,
            "scenario_set_revision": self._retained_binding.scenario_set_revision,
            "subject_span": prepared.model_overlay[0]["subject_span"],
            "unknown_evidence_span": prepared.model_overlay[0]["unknown_evidence_span"],
            "model_overlay": list(prepared.model_overlay),
            "continuity_expectation_supplied": False,
            "baseline_request_artifact": str(baseline_path),
            "baseline_request_sha256": _sha256_file(baseline_path),
            "overlay_request_artifact": str(request_path),
            "overlay_request_sha256": _sha256_file(request_path),
        })
        self.overlay_binding_artifacts.append(binding_path)

        envelope = await self._post_two_pass(body=prepared.body, boundary="extraction-overlay")
        raw_path = self._overlay_artifact_root / f"{sequence:04d}-t2-retained-overlay-raw.json"
        _write_json_create_once(raw_path, envelope)
        self.overlay_raw_artifacts.append(raw_path)
        output = _parse_extraction_completion(envelope)
        _require_candidate_sources_in_cognitive_input(output, extraction_input.cognitive_input)
        self.t2_extraction_output = output
        return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run fresh production T1 and T2 Pass 1, adding only the retained formation overlay to production T2 Pass 2.")
    parser.add_argument("--retained-formation-artifact", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--request-model", required=True)
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--target-path", default=str(DEFAULT_TARGET_PATH))
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
        raise LlamaCppStageRQualificationError(f"provider API key environment variable is empty: {args.provider_api_key_env}")
    summary_path = artifact_root / SUMMARY_FILENAME

    try:
        authority = load_stage_r_semantic_authority(repo_root / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH)
        scenario_set = load_current_stage_r_scenario_set(repo_root=repo_root, authority=authority)
        scenario = scenario_set.scenario(PRIMARY_SCENARIO_ID).scenario
        if len(scenario.turns) != 3:
            raise LlamaCppStageRQualificationError("continuity-lifecycle-v1 must contain exactly three turns")
        retained = load_retained_formation_binding(path=args.retained_formation_artifact, scenario_set_revision=authority.scenario_set_revision, authoritative_t2_content=scenario.turns[PRIMARY_TURN_INDEX - 1])
    except Exception as exc:
        summary = _failure_summary(classification="INFRA_INVALID", phase="retained_formation_binding", head=head, tree=tree, core_fingerprint=core_fingerprint, base_url=base_url, exc=exc, semantic_execution_started=False)
        summary.update(_zero_counts())
        summary["diagnostic"] = DIAGNOSTIC_NAME
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    try:
        preflight = _prepare_physical_condition(repo_root=repo_root, base_url=base_url, request_model=args.request_model, artifact_path=Path(args.artifact_path).resolve(), target_path=Path(args.target_path), upstream_revision=args.llama_upstream_revision, llama_version=args.llama_version, expected_build_number=args.expected_build_number, expected_context_window=args.expected_context_window, expected_slots=args.expected_slots, context_shift_disabled=args.context_shift_disabled, api_key=api_key, artifact_root=artifact_root, gpu_identity=args.gpu_identity, gpu_offload_args=args.gpu_offload_args, launch_args=args.launch_args, server_log_path=Path(args.server_log_path).resolve())
    except Exception as exc:
        summary = _failure_summary(classification="INFRA_INVALID", phase="physical_preflight", head=head, tree=tree, core_fingerprint=core_fingerprint, base_url=base_url, exc=exc, semantic_execution_started=False)
        summary.update(_zero_counts())
        summary.update({"diagnostic": DIAGNOSTIC_NAME, "retained_formation": _retained_mapping(retained)})
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    try:
        semantic = asyncio.run(_run_overlay_transaction(repo_root=repo_root, base_url=base_url, request_model=args.request_model, workspace_root=workspace_root, artifact_root=artifact_root, api_key=api_key, authority=authority, scenario=scenario, retained=retained, counter=preflight["counter"]))
    except Exception as exc:
        summary = _failure_summary(classification="INFRA_INVALID", phase="semantic_transport_or_protocol", head=head, tree=tree, core_fingerprint=core_fingerprint, base_url=base_url, exc=exc, semantic_execution_started=True)
        summary.update(_zero_counts())
        summary.update({"diagnostic": DIAGNOSTIC_NAME, "preflight": preflight["evidence"], "retained_formation": _retained_mapping(retained)})
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    classification = semantic["classification"]
    summary = {
        "format_version": QUALIFICATION_FORMAT_VERSION,
        "diagnostic": DIAGNOSTIC_NAME,
        "condition_id": CONDITION_ID,
        "structured_output_schema_version": SCHEMA_VERSION,
        "classification": classification,
        "phase": "complete",
        "relaylm": {"head": head, "tree": tree, "core_semantic_fingerprint": core_fingerprint},
        "provider_base_url": base_url,
        "preflight": preflight["evidence"],
        "retained_formation": _retained_mapping(retained),
        "semantic": semantic,
        "provider_request_count": 2 + semantic["semantic_generation_count"],
        "semantic_generation_count": semantic["semantic_generation_count"],
        "t1_pass1_generation_count": semantic["t1_pass1_generation_count"],
        "t1_pass2_generation_count": semantic["t1_pass2_generation_count"],
        "t2_pass1_generation_count": semantic["t2_pass1_generation_count"],
        "t2_overlay_pass2_generation_count": semantic["t2_overlay_pass2_generation_count"],
        "formation_generation_count": 0,
        "t3_generation_count": 0,
        "semantic_verdict": "not_run",
        "semantic_retry_count": 0,
        "replay_count": 0,
        "reseed_count": 0,
        "fallback_count": 0,
        "fastcal_count": 0,
        "lm_studio_contact_count": 0,
        "repository_mutation_count": 0,
        "product_quality_review": "not_run_by_host",
    }
    _write_json_create_once(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if classification == "PROTOCOL_VALID_SEMANTIC_REVIEW_REQUIRED" else 2


async def _run_overlay_transaction(*, repo_root: Path, base_url: str, request_model: str, workspace_root: Path, artifact_root: Path, api_key: str | None, authority: StageRSemanticAuthority, scenario: Any, retained: RetainedFormationBinding, counter: Any) -> dict[str, Any]:
    client = httpx.AsyncClient(timeout=LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS, trust_env=False)
    provider = ProductionContinuityOverlayLlamaProvider(base_url=base_url, model=request_model, api_key=api_key, decoding_config=OpenAICompatibleDecodingConfig(temperature=authority.temperature, top_p=authority.top_p, seed=authority.seed), decoding_capabilities=_LLAMA_CPP_DECODING_CAPABILITIES, llama_cpp_reasoning_capability=LlamaCppReasoningCapabilityAttestation(request_model=request_model, enable_thinking_supported=True), http_client=client, input_counter=counter, observation_root=artifact_root / "llama-cpp-request-observations", retained_binding=retained, overlay_artifact_root=artifact_root / "production-continuity-overlay")
    fixture_root = repo_root / CANONICAL_FIXTURE_PATH
    character_root = workspace_root / "character"
    try:
        _copy_fixture(fixture_root=fixture_root, destination=character_root)
        character = CharacterDirectory(character_root)
        continuity_runtime = ContinuityRuntime(context=ContinuityContext(max_items=authority.continuity_runtime.max_items), lifetime_revisions=authority.continuity_runtime.lifetime_revisions)
        execution_runtime = CognitionExecutionRuntime()
        requests = authority.pass_requests(reasoning_mode=CognitionReasoningMode.OFF)
        assert requests.pass1 is not None and requests.pass2 is not None
        t1 = await run_user_turn_two_pass(character=character, provider=provider, content=scenario.turns[0], execution_runtime=execution_runtime, continuity_runtime=continuity_runtime, pass1_request=requests.pass1, pass2_request=requests.pass2)
        t1_extraction = await t1.extraction
        if t1_extraction.status is not TwoPassExtractionStatus.COMMITTED:
            return _transaction_result(classification="PRODUCTION_PARITY_NOT_REALIZED_NO_INFERENCE", provider=provider, t1=t1, t1_extraction=t1_extraction, t2=None, t2_extraction=None, continuity_runtime=continuity_runtime)
        t2 = await run_user_turn_two_pass(character=character, provider=provider, content=scenario.turns[1], execution_runtime=execution_runtime, continuity_runtime=continuity_runtime, pass1_request=requests.pass1, pass2_request=requests.pass2)
        t2_extraction = await t2.extraction
        classification = "PROTOCOL_VALID_SEMANTIC_REVIEW_REQUIRED"
        if t2_extraction.status is not TwoPassExtractionStatus.COMMITTED or provider.extraction_call_count != 2 or provider.overlay_generation_count != 1 or len(provider.completion_artifacts) != 4 or not _completion_evidence_is_thinking_off(provider.completion_artifacts):
            classification = "PROTOCOL_OR_PROVENANCE_INVALID_NO_INFERENCE"
        return _transaction_result(classification=classification, provider=provider, t1=t1, t1_extraction=t1_extraction, t2=t2, t2_extraction=t2_extraction, continuity_runtime=continuity_runtime)
    finally:
        await provider.aclose()
        await client.aclose()


def _transaction_result(*, classification: str, provider: ProductionContinuityOverlayLlamaProvider, t1: Any, t1_extraction: Any, t2: Any | None, t2_extraction: Any | None, continuity_runtime: ContinuityRuntime) -> dict[str, Any]:
    completion_count = len(provider.completion_artifacts)
    return {
        "classification": classification,
        "semantic_generation_count": completion_count,
        "t1_pass1_generation_count": 1 if completion_count >= 1 else 0,
        "t1_pass2_generation_count": 1 if completion_count >= 2 else 0,
        "t2_pass1_generation_count": 1 if completion_count >= 3 else 0,
        "t2_overlay_pass2_generation_count": provider.overlay_generation_count,
        "formation_generation_count": 0,
        "t3_generation_count": 0,
        "reasoning": {"requested": "off", "wire": {"reasoning_effort": "none"}, "completion_evidence_valid": _completion_evidence_is_thinking_off(provider.completion_artifacts) if provider.completion_artifacts else False},
        "t1": {"user_event_id": t1.user_event.id, "response": t1.response, "extraction_status": t1_extraction.status.value, "state_candidates": _state_candidates(provider.t1_extraction_output), "continuity_candidates": _continuity_candidates(provider.t1_extraction_output)},
        "t2": None if t2 is None else {"user_event_id": t2.user_event.id, "response": t2.response, "extraction_status": t2_extraction.status.value, "state_candidates": _state_candidates(provider.t2_extraction_output), "continuity_candidates": _continuity_candidates(provider.t2_extraction_output)},
        "resulting_continuity": {"revision": continuity_runtime.context.revision, "items": [{"kind": item.kind, "key": item.key, "value": item.value, "sources": list(item.sources), "epistemic_role": item.epistemic_role, "accepted_revision": item.accepted_revision, "expires_revision": item.expires_revision} for item in continuity_runtime.context.items]},
        "completion_observation_artifacts": [str(path) for path in provider.completion_artifacts],
        "input_count_artifacts": [str(path) for path in provider.input_count_artifacts],
        "overlay_request_artifacts": [str(path) for path in provider.overlay_request_artifacts],
        "overlay_binding_artifacts": [str(path) for path in provider.overlay_binding_artifacts],
        "overlay_raw_artifacts": [str(path) for path in provider.overlay_raw_artifacts],
        "semantic_retry_count": 0,
        "replay_count": 0,
        "reseed_count": 0,
        "fallback_count": 0,
    }


def _copy_fixture(*, fixture_root: Path, destination: Path) -> None:
    expected = character_fixture_revision(fixture_root)
    if destination.exists():
        raise LlamaCppStageRQualificationError("production overlay workspace character root must not already exist")
    shutil.copytree(fixture_root, destination, copy_function=shutil.copy2)
    observed = character_fixture_revision(destination)
    if observed != expected:
        shutil.rmtree(destination, ignore_errors=True)
        raise LlamaCppStageRQualificationError("character fixture changed while preparing production overlay workspace")


def _retained_mapping(binding: RetainedFormationBinding) -> dict[str, Any]:
    return {"artifact_path": binding.artifact_path, "sha256": binding.sha256, "scenario_set_revision": binding.scenario_set_revision, "item_count": len(binding.items), "items": [{"subject_span": item.subject_span, "unknown_evidence_span": item.unknown_evidence_span, "source_event_id": item.source_event_id} for item in binding.items], "continuity_expectation_supplied": False}


def _state_candidates(output: CognitionExtractionOutput | None) -> list[dict[str, Any]]:
    return [] if output is None else [_state_candidate_mapping(item) for item in output.state_candidates]


def _state_candidate_mapping(item: StateCandidate) -> dict[str, Any]:
    return {"state_class": item.state_class, "key": item.key, "op": item.op, "value": item.value if item.has_value else None, "sources": list(item.sources)}


def _continuity_candidates(output: CognitionExtractionOutput | None) -> list[dict[str, Any]]:
    return [] if output is None else [_continuity_candidate_mapping(item) for item in output.continuity_candidates]


def _continuity_candidate_mapping(item: ContinuityCandidate) -> dict[str, Any]:
    return {"kind": item.kind, "key": item.key, "op": item.op, "value": item.value if item.has_value else None, "sources": list(item.sources), "epistemic_role": item.epistemic_role}


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _zero_counts() -> dict[str, int]:
    return {"semantic_generation_count": 0, "t1_pass1_generation_count": 0, "t1_pass2_generation_count": 0, "t2_pass1_generation_count": 0, "t2_overlay_pass2_generation_count": 0, "formation_generation_count": 0, "t3_generation_count": 0, "semantic_retry_count": 0, "replay_count": 0, "reseed_count": 0, "fallback_count": 0, "fastcal_count": 0, "lm_studio_contact_count": 0, "repository_mutation_count": 0}


if __name__ == "__main__":
    raise SystemExit(main())
