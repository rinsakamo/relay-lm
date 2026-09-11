"""One-generation llama.cpp host for retained-formation Continuity projection.

The host never regenerates epistemic formation. It binds an externally retained
formation artifact to the current Stage R T2 Event, then performs exactly one
projection-only generation through the evaluation-only #2545 primitive.
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
    DIAGNOSTIC_NAME as FORMATION_DIAGNOSTIC_NAME,
    EpistemicFormationItem,
    build_t2_epistemic_formation_input,
    completion_metadata_mapping,
)
from relaylm.actual_model_llama_cpp_thinking import (
    LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS,
)
from relaylm.actual_model_semantic_continuity_projection_diagnostic import (
    PROJECTION_CONDITION_ID,
    PROJECTION_DIAGNOSTIC_NAME,
    PROJECTION_SCHEMA,
    PROJECTION_SCHEMA_NAME,
    build_semantic_continuity_projection_request_body,
    parse_semantic_continuity_projection_completion,
    serialize_semantic_continuity_projection_input,
)
from relaylm.actual_model_stage_r_llama_cpp import (
    CANONICAL_FIXTURE_PATH,
    DEFAULT_TARGET_PATH,
    QUALIFICATION_FORMAT_VERSION,
    _LLAMA_CPP_DECODING_CAPABILITIES,
    _CompletionObservingLlamaProvider,
    _failure_summary,
    _frozen_core_fingerprint,
    _git_identity,
    _prepare_physical_condition,
    _require_clean_repo,
    _require_local_llama_api_base,
    _write_json_create_once,
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
from relaylm.continuity import ContinuityCandidate
from relaylm.providers.llama_cpp_reasoning import LlamaCppReasoningCapabilityAttestation
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig
from relaylm.providers.openai_compatible_two_pass import (
    _completion_content_and_metadata,
)
from relaylm.storage.filesystem import CharacterDirectory


PRIMARY_SCENARIO_ID = "continuity-lifecycle-v1"
PRIMARY_TURN_INDEX = 2
SUMMARY_FILENAME = "semantic-continuity-projection-t2-summary.json"
HOST_FORMAT_VERSION = 1


class ProjectionLlamaProvider(_CompletionObservingLlamaProvider):
    """Current llama.cpp carriage with projection-specific evidence artifacts."""

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

    async def generate_projection(
        self,
        cognitive_input: Any,
        *,
        observations: Sequence[EpistemicFormationItem],
        pass_request: CognitionPassRequest,
    ) -> Any:
        body = build_semantic_continuity_projection_request_body(
            provider=self,
            cognitive_input=cognitive_input,
            observations=observations,
            pass_request=pass_request,
        )
        sequence_index = len(self.request_body_artifacts) + 1
        request_body_path = self._request_body_root / (
            f"{sequence_index:04d}-t2-semantic-continuity-projection-request.json"
        )
        _write_json_create_once(request_body_path, body)
        self.request_body_artifacts.append(request_body_path)

        envelope = await self._post_two_pass(
            body=body,
            boundary="semantic-continuity-projection-t2",
        )
        raw_path = self._raw_observation_root / (
            f"{sequence_index:04d}-t2-semantic-continuity-projection-raw.json"
        )
        try:
            content, completion = _completion_content_and_metadata(envelope)
        except Exception:
            _write_json_create_once(
                raw_path,
                {
                    "format_version": HOST_FORMAT_VERSION,
                    "diagnostic": PROJECTION_DIAGNOSTIC_NAME,
                    "request_body_artifact": str(request_body_path),
                    "input_event_id": cognitive_input.input.id,
                    "raw_envelope": envelope,
                    "semantic_review": "not_run",
                },
            )
            self.raw_observation_artifacts.append(raw_path)
            raise

        _write_json_create_once(
            raw_path,
            {
                "format_version": HOST_FORMAT_VERSION,
                "diagnostic": PROJECTION_DIAGNOSTIC_NAME,
                "request_body_artifact": str(request_body_path),
                "input_event_id": cognitive_input.input.id,
                "raw_content": content,
                "raw_envelope": envelope,
                "completion": completion_metadata_mapping(completion),
                "semantic_review": "not_run",
            },
        )
        self.raw_observation_artifacts.append(raw_path)
        return parse_semantic_continuity_projection_completion(
            envelope=envelope,
            cognitive_input=cognitive_input,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run exactly one retained-formation semantic-to-Continuity "
            "projection generation on the current llama.cpp condition."
        )
    )
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
    api_key = (
        os.environ.get(args.provider_api_key_env)
        if args.provider_api_key_env
        else None
    )
    if args.provider_api_key_env and not api_key:
        raise LlamaCppStageRQualificationError(
            "provider API key environment variable is empty: "
            f"{args.provider_api_key_env}"
        )

    summary_path = artifact_root / SUMMARY_FILENAME

    try:
        authority = load_stage_r_semantic_authority(
            repo_root / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH
        )
        scenario_set = load_current_stage_r_scenario_set(
            repo_root=repo_root,
            authority=authority,
        )
        scenario = scenario_set.scenario(PRIMARY_SCENARIO_ID).scenario
        fixture = CharacterDirectory(repo_root / CANONICAL_FIXTURE_PATH)
        cognitive_input = build_t2_epistemic_formation_input(
            identity=fixture.load_identity(),
            state=fixture.load_state(),
            scenario=scenario,
            scenario_set_revision=authority.scenario_set_revision,
        )
        retained = load_retained_formation_binding(
            path=Path(args.retained_formation_artifact),
            cognitive_input=cognitive_input,
        )
    except Exception as exc:
        summary = _failure_summary(
            classification="INFRA_INVALID",
            phase="retained_formation_binding",
            head=head,
            tree=tree,
            core_fingerprint=core_fingerprint,
            base_url=base_url,
            exc=exc,
            semantic_execution_started=False,
        )
        summary.update(_zero_semantic_counts())
        summary["diagnostic"] = PROJECTION_DIAGNOSTIC_NAME
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    try:
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
        summary.update(_zero_semantic_counts())
        summary["diagnostic"] = PROJECTION_DIAGNOSTIC_NAME
        summary["retained_formation"] = retained
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    schema_sha = hashlib.sha256(
        json.dumps(
            PROJECTION_SCHEMA,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    binding_path = (
        artifact_root / "llama-cpp-semantic-continuity-projection-binding.json"
    )
    _write_json_create_once(
        binding_path,
        {
            "format_version": HOST_FORMAT_VERSION,
            "diagnostic": PROJECTION_DIAGNOSTIC_NAME,
            "condition_id": PROJECTION_CONDITION_ID,
            "scenario_authority": str(
                repo_root / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH
            ),
            "scenario_set_revision": authority.scenario_set_revision,
            "scenario_id": PRIMARY_SCENARIO_ID,
            "primary_turn_index": PRIMARY_TURN_INDEX,
            "input_event_id": cognitive_input.input.id,
            "retained_formation": retained,
            "formation_generation_count": 0,
            "pass1_generation_count": 0,
            "state_generation_count": 0,
            "t3_generation_count": 0,
            "native_schema_name": PROJECTION_SCHEMA_NAME,
            "projection_schema_sha256": f"sha256:{schema_sha}",
            "reasoning": {
                "requested": "off",
                "wire": {"reasoning_effort": "none"},
            },
            "physical_binding_artifact": str(
                artifact_root / "llama-cpp-physical-binding.json"
            ),
        },
    )

    observations = tuple(
        EpistemicFormationItem(
            subject_span=item["subject_span"],
            unknown_evidence_span=item["unknown_evidence_span"],
            source_event_id=item["source_event_id"],
        )
        for item in retained["items"]
    )
    try:
        semantic = asyncio.run(
            _run_projection(
                base_url=base_url,
                request_model=args.request_model,
                workspace_root=workspace_root,
                artifact_root=artifact_root,
                replicate_id=args.replicate_id,
                api_key=api_key,
                authority=authority,
                cognitive_input=cognitive_input,
                observations=observations,
                counter=preflight["counter"],
            )
        )
    except Exception as exc:
        summary = _failure_summary(
            classification="INFRA_INVALID",
            phase="projection_transport_or_protocol",
            head=head,
            tree=tree,
            core_fingerprint=core_fingerprint,
            base_url=base_url,
            exc=exc,
            semantic_execution_started=True,
        )
        summary.update(_zero_semantic_counts())
        summary.update(
            {
                "diagnostic": PROJECTION_DIAGNOSTIC_NAME,
                "preflight": preflight["evidence"],
                "retained_formation": retained,
                "projection_generation_count": 1,
            }
        )
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    summary = {
        "format_version": QUALIFICATION_FORMAT_VERSION,
        "diagnostic": PROJECTION_DIAGNOSTIC_NAME,
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
        "retained_formation": retained,
        "semantic": semantic,
        "provider_request_count": 2 + semantic["projection_generation_count"],
        "projection_generation_count": semantic["projection_generation_count"],
        "formation_generation_count": 0,
        "pass1_generation_count": 0,
        "state_generation_count": 0,
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
    return 0


def load_retained_formation_binding(
    *,
    path: Path,
    cognitive_input: Any,
) -> dict[str, Any]:
    """Load only mechanically formed observations and bind them to current T2."""

    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise LlamaCppStageRQualificationError(
            f"retained formation artifact is not a file: {resolved}"
        )
    raw_bytes = resolved.read_bytes()
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LlamaCppStageRQualificationError(
            f"retained formation artifact is not valid UTF-8 JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise LlamaCppStageRQualificationError(
            "retained formation artifact must be a JSON object"
        )
    if payload.get("diagnostic") != FORMATION_DIAGNOSTIC_NAME:
        raise LlamaCppStageRQualificationError(
            "retained formation artifact diagnostic identity is invalid"
        )
    if payload.get("mechanical_validation") != "pass":
        raise LlamaCppStageRQualificationError(
            "retained formation artifact is not mechanically validated"
        )
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise LlamaCppStageRQualificationError(
            "retained formation artifact contains no formed observations"
        )

    expected_fields = {
        "subject_span",
        "unknown_evidence_span",
        "source_event_id",
    }
    observations: list[EpistemicFormationItem] = []
    item_mappings: list[dict[str, str]] = []
    for index, raw_item in enumerate(raw_items, start=1):
        if not isinstance(raw_item, dict) or set(raw_item) != expected_fields:
            raise LlamaCppStageRQualificationError(
                f"retained formation item {index} has invalid fields"
            )
        if not all(
            isinstance(raw_item[field], str) and raw_item[field]
            for field in expected_fields
        ):
            raise LlamaCppStageRQualificationError(
                f"retained formation item {index} fields must be non-empty strings"
            )
        item = EpistemicFormationItem(
            subject_span=raw_item["subject_span"],
            unknown_evidence_span=raw_item["unknown_evidence_span"],
            source_event_id=raw_item["source_event_id"],
        )
        observations.append(item)
        item_mappings.append(
            {
                "subject_span": item.subject_span,
                "unknown_evidence_span": item.unknown_evidence_span,
                "source_event_id": item.source_event_id,
            }
        )

    serialize_semantic_continuity_projection_input(
        cognitive_input=cognitive_input,
        observations=observations,
    )
    return {
        "path": str(resolved),
        "sha256": f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}",
        "diagnostic": FORMATION_DIAGNOSTIC_NAME,
        "mechanical_validation": "pass",
        "item_count": len(item_mappings),
        "items": item_mappings,
        "continuity_expectation_supplied": False,
    }


async def _run_projection(
    *,
    base_url: str,
    request_model: str,
    workspace_root: Path,
    artifact_root: Path,
    replicate_id: str,
    api_key: str | None,
    authority: Any,
    cognitive_input: Any,
    observations: Sequence[EpistemicFormationItem],
    counter: Any,
) -> dict[str, object]:
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
    provider = ProjectionLlamaProvider(
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
        raw_observation_root=artifact_root / "semantic-continuity-projection-raw",
        request_body_root=artifact_root / "semantic-continuity-projection-requests",
    )
    try:
        output = await provider.generate_projection(
            cognitive_input,
            observations=observations,
            pass_request=pass_request,
        )
        parsed = [
            _candidate_mapping(candidate)
            for candidate in output.continuity_candidates
        ]
        mechanical_path = (
            artifact_root / "semantic-continuity-projection-mechanical-observation.json"
        )
        _write_json_create_once(
            mechanical_path,
            {
                "format_version": HOST_FORMAT_VERSION,
                "diagnostic": PROJECTION_DIAGNOSTIC_NAME,
                "mechanical_validation": "pass",
                "input_event_id": cognitive_input.input.id,
                "continuity_candidates": parsed,
                "state_candidates": [],
                "semantic_review": {
                    "status": "not_run",
                    "generation_count": 0,
                },
            },
        )
        return {
            "scenario_id": PRIMARY_SCENARIO_ID,
            "primary_turn_index": PRIMARY_TURN_INDEX,
            "input_event_id": cognitive_input.input.id,
            "projection_generation_count": 1,
            "formation_generation_count": 0,
            "pass1_generation_count": 0,
            "state_generation_count": 0,
            "t3_generation_count": 0,
            "mechanical_validation": "pass",
            "semantic_verdict": "not_run",
            "continuity_candidates": parsed,
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
            "input_count_artifacts": [
                str(path) for path in provider.input_count_artifacts
            ],
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


def _candidate_mapping(candidate: ContinuityCandidate) -> dict[str, Any]:
    return {
        "kind": candidate.kind,
        "key": candidate.key,
        "op": candidate.op,
        "value": candidate.value if candidate.has_value else None,
        "sources": list(candidate.sources),
        "epistemic_role": candidate.epistemic_role,
    }


def _zero_semantic_counts() -> dict[str, int]:
    return {
        "projection_generation_count": 0,
        "formation_generation_count": 0,
        "pass1_generation_count": 0,
        "state_generation_count": 0,
        "t3_generation_count": 0,
        "semantic_retry_count": 0,
        "replay_count": 0,
        "reseed_count": 0,
        "fallback_count": 0,
        "fastcal_count": 0,
        "lm_studio_contact_count": 0,
        "repository_mutation_count": 0,
    }


if __name__ == "__main__":
    raise SystemExit(main())
