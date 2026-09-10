"""One-command physical carriage for the #2516 T2 formation probe.

The repository transaction adds this owner but never invokes it.  A future
physical owner may invoke the WSL wrapper once; this host performs one T2
diagnostic generation and never enters the Stage R two-pass scenario runner.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx

from relaylm.actual_model_epistemic_formation_diagnostic import (
    DIAGNOSTIC_CONDITION_ID,
    DIAGNOSTIC_FORMAT_VERSION,
    DIAGNOSTIC_NAME,
    DIAGNOSTIC_SCHEMA_NAME,
    DIAGNOSTIC_SCHEMA_VERSION,
    EPISTEMIC_FORMATION_REVIEW_SCHEMA,
    PRIMARY_SCENARIO_ID,
    build_epistemic_formation_request_body,
    build_t2_epistemic_formation_input,
    completion_metadata_mapping,
    parse_epistemic_formation_completion,
    raw_observation_mapping,
)
from relaylm.actual_model_llama_cpp_thinking import (
    LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS,
)
from relaylm.actual_model_stage_r_llama_cpp import (
    CANONICAL_FIXTURE_PATH,
    DEFAULT_TARGET_PATH,
    QUALIFICATION_FORMAT_VERSION,
    _LLAMA_CPP_DECODING_CAPABILITIES,
    _CompletionObservingLlamaProvider,
    _failure_summary,
    _frozen_core_fingerprint,
    _prepare_physical_condition,
    _require_clean_repo,
    _require_local_llama_api_base,
    _write_json_create_once,
    _git_identity,
    LlamaCppStageRQualificationError,
)
from relaylm.actual_model_stage_r_semantics import (
    CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH,
    load_current_stage_r_scenario_set,
    load_stage_r_semantic_authority,
)
from relaylm.cognition_execution import (
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.providers.llama_cpp_reasoning import LlamaCppReasoningCapabilityAttestation
from relaylm.providers.openai_compatible_two_pass import _completion_content_and_metadata
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig
from relaylm.storage.filesystem import CharacterDirectory


class EpistemicFormationLlamaProvider(_CompletionObservingLlamaProvider):
    """Current llama.cpp carriage with a separate raw T2 observation capsule."""

    def __init__(
        self,
        *args: Any,
        raw_observation_root: Path,
        request_body_root: Path,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._raw_observation_root = raw_observation_root
        self._request_body_root = request_body_root
        self.raw_observation_artifacts: list[Path] = []
        self.request_body_artifacts: list[Path] = []
        self.mechanical_outputs: list[object] = []

    async def generate_epistemic_formation(
        self,
        cognitive_input: Any,
        *,
        pass_request: CognitionPassRequest,
    ) -> Any:
        body = build_epistemic_formation_request_body(
            provider=self,
            cognitive_input=cognitive_input,
            pass_request=pass_request,
        )
        sequence_index = len(self.request_body_artifacts) + 1
        request_body_path = self._request_body_root / (
            f"{sequence_index:04d}-t2-epistemic-formation-request.json"
        )
        _write_json_create_once(request_body_path, body)
        self.request_body_artifacts.append(request_body_path)

        envelope = await self._post_two_pass(
            body=body,
            boundary="epistemic-formation-t2",
        )
        try:
            content, completion = _completion_content_and_metadata(envelope)
        except Exception:
            raw_path = self._raw_observation_root / (
                f"{sequence_index:04d}-t2-epistemic-formation-raw.json"
            )
            _write_json_create_once(
                raw_path,
                {
                    "format_version": DIAGNOSTIC_FORMAT_VERSION,
                    "diagnostic": DIAGNOSTIC_NAME,
                    "request_body_artifact": str(request_body_path),
                    "input_event_id": cognitive_input.input.id,
                    "raw_envelope": envelope,
                    "semantic_review": "not_run",
                },
            )
            self.raw_observation_artifacts.append(raw_path)
            raise

        raw_path = self._raw_observation_root / (
            f"{sequence_index:04d}-t2-epistemic-formation-raw.json"
        )
        _write_json_create_once(
            raw_path,
            raw_observation_mapping(
                cognitive_input=cognitive_input,
                content=content,
                completion=completion,
                request_body_artifact=str(request_body_path),
            ),
        )
        self.raw_observation_artifacts.append(raw_path)
        output = parse_epistemic_formation_completion(
            envelope=envelope,
            cognitive_input=cognitive_input,
        )
        self.mechanical_outputs.append(output)
        return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the evaluation-only T2 epistemic formation probe on one current "
            "llama.cpp condition."
        )
    )
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
        raise LlamaCppStageRQualificationError(
            f"provider API key environment variable is empty: {args.provider_api_key_env}"
        )

    summary_path = artifact_root / "epistemic-formation-t2-summary.json"
    try:
        authority = load_stage_r_semantic_authority(
            repo_root / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH
        )
        scenario_set = load_current_stage_r_scenario_set(
            repo_root=repo_root,
            authority=authority,
        )
        preflight = _prepare_physical_condition(
            repo_root=repo_root,
            base_url=base_url,
            request_model=args.request_model,
            artifact_path=Path(args.artifact_path).resolve(),
            target_path=Path(args.target_path),
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
        summary.update(
            {
                "diagnostic": DIAGNOSTIC_NAME,
                "diagnostic_generation_count": 0,
                "t3_generation_count": 0,
            }
        )
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    schema_sha = hashlib.sha256(
        json.dumps(
            EPISTEMIC_FORMATION_REVIEW_SCHEMA,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    binding_path = artifact_root / "llama-cpp-epistemic-formation-binding.json"
    _write_json_create_once(
        binding_path,
        {
            "format_version": DIAGNOSTIC_FORMAT_VERSION,
            "diagnostic": DIAGNOSTIC_NAME,
            "condition_id": DIAGNOSTIC_CONDITION_ID,
            "scenario_authority": str(
                repo_root / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH
            ),
            "scenario_set_revision": authority.scenario_set_revision,
            "scenario_id": PRIMARY_SCENARIO_ID,
            "primary_turn_index": 2,
            "t3_generation_count": 0,
            "continuity_ir_supplied": False,
            "native_schema_name": DIAGNOSTIC_SCHEMA_NAME,
            "review_schema_sha256": f"sha256:{schema_sha}",
            "reasoning": {
                "requested": "off",
                "wire": {"reasoning_effort": "none"},
            },
            "physical_binding_artifact": str(
                artifact_root / "llama-cpp-physical-binding.json"
            ),
        },
    )

    try:
        semantic = asyncio.run(
            _run_t2_diagnostic(
                repo_root=repo_root,
                base_url=base_url,
                request_model=args.request_model,
                workspace_root=workspace_root,
                artifact_root=artifact_root,
                replicate_id=args.replicate_id,
                api_key=api_key,
                authority=authority,
                scenario_set=scenario_set,
                counter=preflight["counter"],
            )
        )
    except Exception as exc:
        summary = _failure_summary(
            classification="INFRA_INVALID",
            phase="diagnostic_transport_or_protocol",
            head=head,
            tree=tree,
            core_fingerprint=core_fingerprint,
            base_url=base_url,
            exc=exc,
            semantic_execution_started=True,
        )
        summary.update(
            {
                "diagnostic": DIAGNOSTIC_NAME,
                "preflight": preflight["evidence"],
                "diagnostic_generation_count": 1,
                "t3_generation_count": 0,
            }
        )
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    summary = {
        "format_version": QUALIFICATION_FORMAT_VERSION,
        "diagnostic": DIAGNOSTIC_NAME,
        "classification": "PROTOCOL_VALID_SEMANTIC_REVIEW_REQUIRED",
        "phase": "complete",
        "relaylm": {
            "head": head,
            "tree": tree,
            "core_semantic_fingerprint": core_fingerprint,
        },
        "provider_base_url": base_url,
        "preflight": preflight["evidence"],
        "binding_artifact": str(binding_path),
        "semantic": semantic,
        "provider_request_count": 2 + semantic["diagnostic_generation_count"],
        "diagnostic_generation_count": semantic["diagnostic_generation_count"],
        "semantic_verdict": "not_run",
        "semantic_retry_count": 0,
        "fallback_count": 0,
        "t3_generation_count": 0,
        "product_quality_review": "not_run_by_host",
    }
    _write_json_create_once(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


async def _run_t2_diagnostic(
    *,
    repo_root: Path,
    base_url: str,
    request_model: str,
    workspace_root: Path,
    artifact_root: Path,
    replicate_id: str,
    api_key: str | None,
    authority: Any,
    scenario_set: Any,
    counter: Any,
) -> dict[str, object]:
    scenario = scenario_set.scenario(PRIMARY_SCENARIO_ID).scenario
    fixture = CharacterDirectory(repo_root / CANONICAL_FIXTURE_PATH)
    cognitive_input = build_t2_epistemic_formation_input(
        identity=fixture.load_identity(),
        state=fixture.load_state(),
        scenario=scenario,
        scenario_set_revision=authority.scenario_set_revision,
    )
    pass_request = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.OFF,
        temperature=authority.temperature,
        top_p=authority.top_p,
        structured_output_mode=CognitionStructuredOutputMode.NATIVE,
    )
    client = httpx.AsyncClient(
        timeout=LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS,
        trust_env=False,
    )
    provider = EpistemicFormationLlamaProvider(
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
        raw_observation_root=artifact_root / "epistemic-formation-raw-observations",
        request_body_root=artifact_root / "epistemic-formation-request-bodies",
    )
    try:
        output = await provider.generate_epistemic_formation(
            cognitive_input,
            pass_request=pass_request,
        )
        mechanical_path = artifact_root / "epistemic-formation-mechanical-observation.json"
        _write_json_create_once(
            mechanical_path,
            {
                "format_version": DIAGNOSTIC_FORMAT_VERSION,
                "diagnostic": DIAGNOSTIC_NAME,
                "mechanical_validation": "pass",
                "input_event_id": cognitive_input.input.id,
                "items": [
                    {
                        "subject_span": item.subject_span,
                        "unknown_evidence_span": item.unknown_evidence_span,
                        "source_event_id": item.source_event_id,
                    }
                    for item in output.items
                ],
                "raw_observation_artifacts": [
                    str(path) for path in provider.raw_observation_artifacts
                ],
                "semantic_review": {
                    "status": "not_run",
                    "generation_count": 0,
                    "contract": DIAGNOSTIC_SCHEMA_VERSION,
                },
            },
        )
        return {
            "scenario_id": PRIMARY_SCENARIO_ID,
            "primary_turn_index": 2,
            "input_event_id": cognitive_input.input.id,
            "diagnostic_generation_count": 1,
            "t3_generation_count": 0,
            "continuity_ir_supplied": False,
            "mechanical_validation": "pass",
            "semantic_verdict": "not_run",
            "mechanical_observation_artifact": str(mechanical_path),
            "raw_observation_artifacts": [
                str(path) for path in provider.raw_observation_artifacts
            ],
            "request_body_artifacts": [
                str(path) for path in provider.request_body_artifacts
            ],
            "completion_observation_artifacts": [
                str(path) for path in provider.completion_artifacts
            ],
            "input_count_artifacts": [str(path) for path in provider.input_count_artifacts],
            "reasoning": {
                "requested": "off",
                "wire": {"reasoning_effort": "none"},
                "completion": completion_metadata_mapping(output.completion),
            },
            "replicate_id": replicate_id,
            "workspace_root": str(workspace_root),
        }
    finally:
        await provider.aclose()
        await client.aclose()


if __name__ == "__main__":
    raise SystemExit(main())
