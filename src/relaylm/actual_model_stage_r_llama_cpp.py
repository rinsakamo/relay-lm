from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

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
from relaylm.actual_model_llama_cpp import (
    LlamaCppRuntimeAttestationError,
    LlamaCppRuntimeIdentity,
    attest_llama_cpp_runtime,
)
from relaylm.actual_model_llama_cpp_thinking import (
    LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS,
    LlamaCppThinkingChatInputCounter,
)
from relaylm.actual_model_quality import evaluate_labeled_proposals
from relaylm.actual_model_scenarios import ActualModelScenarioSet
from relaylm.actual_model_stage_r_semantics import (
    CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH,
    StageRSemanticAuthority,
    load_current_stage_r_scenario_set,
    load_stage_r_semantic_authority,
)
from relaylm.actual_model_targets import (
    ActualModelArtifactTarget,
    ActualModelArtifactVerification,
    load_actual_model_target,
    verify_actual_model_artifact,
)
from relaylm.cognition_execution import CognitionReasoningMode
from relaylm.providers.llama_cpp_openai import LlamaCppOpenAICompatibleTwoPassProvider
from relaylm.providers.llama_cpp_reasoning import LlamaCppReasoningCapabilityAttestation
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import describe_openai_compatible_provider


CANONICAL_FIXTURE_PATH = Path("evaluation/actual_model/characters/foundation-v1")
DEFAULT_TARGET_PATH = Path(
    "evaluation/actual_model/targets/"
    "gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json"
)
QUALIFICATION_FORMAT_VERSION = 1
NON_GENERATIVE_PREFLIGHT_TIMEOUT_SECONDS = 20.0
CAPABILITY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status"],
    "properties": {"status": {"const": "ok"}},
}
_LLAMA_CPP_DECODING_CAPABILITIES = OpenAICompatibleDecodingCapabilities(
    supported_controls=frozenset({"temperature", "top_p", "max_output_tokens"})
)


class LlamaCppStageRQualificationError(ValueError):
    """The current llama-server physical condition is invalid for Stage R."""


class _CompletionObservingLlamaProvider(LlamaCppOpenAICompatibleTwoPassProvider):
    """Count the exact generated body and persist content-free completion facts."""

    def __init__(
        self,
        *args: Any,
        input_counter: LlamaCppThinkingChatInputCounter,
        observation_root: Path,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._input_counter = input_counter
        self._observation_root = observation_root
        self.completion_artifacts: list[Path] = []
        self.input_count_artifacts: list[Path] = []

    async def _post_two_pass(
        self,
        *,
        body: dict[str, Any],
        boundary: str,
    ) -> Any:
        count = self._input_counter.count_input(body)
        sequence = len(self.input_count_artifacts) + 1
        count_path = self._observation_root / f"{sequence:04d}-{boundary}-input-count.json"
        _write_json_create_once(
            count_path,
            {
                "format_version": 1,
                "sequence_index": sequence,
                "boundary": boundary,
                "counter_identity": self._input_counter.evidence_identity.to_mapping(),
                "total_input_tokens": count.total_input_tokens,
                "required_input_framing_tokens": count.required_input_framing_tokens,
                "cognitive_input_tokens": count.cognitive_input_tokens,
                "mode": count.mode.value,
            },
        )
        self.input_count_artifacts.append(count_path)

        envelope = await super()._post_two_pass(body=body, boundary=boundary)
        completion_path = self._observation_root / f"{sequence:04d}-{boundary}-completion.json"
        _write_json_create_once(
            completion_path,
            _completion_observation(
                envelope=envelope,
                boundary=boundary,
                sequence_index=sequence,
            ),
        )
        self.completion_artifacts.append(completion_path)
        return envelope


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run current provider-neutral Stage R semantics on one freshly attested "
            "external llama.cpp/llama-server condition."
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

    summary_path = artifact_root / "stage-r-llama-cpp-summary.json"
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
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

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
        summary["preflight"] = preflight["evidence"]
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    summary = {
        "format_version": QUALIFICATION_FORMAT_VERSION,
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


def _prepare_physical_condition(
    *,
    repo_root: Path,
    base_url: str,
    request_model: str,
    artifact_path: Path,
    target_path: Path,
    upstream_revision: str,
    llama_version: str,
    expected_build_number: int,
    expected_context_window: int,
    expected_slots: int,
    context_shift_disabled: bool,
    api_key: str | None,
    artifact_root: Path,
    gpu_identity: str | None,
    gpu_offload_args: str | None,
    launch_args: str | None,
    server_log_path: Path,
) -> dict[str, Any]:
    if not isinstance(llama_version, str) or not llama_version.strip():
        raise LlamaCppStageRQualificationError("llama-version must not be empty")
    if not context_shift_disabled:
        raise LlamaCppStageRQualificationError(
            "qualification requires fresh proof that llama.cpp context shift is disabled"
        )
    if expected_build_number <= 0 or expected_context_window <= 0:
        raise LlamaCppStageRQualificationError(
            "expected build and context values must be positive"
        )
    if expected_slots != 1:
        raise LlamaCppStageRQualificationError(
            "current shared llama.cpp qualification requires exactly one live slot"
        )
    if not server_log_path.is_file():
        raise LlamaCppStageRQualificationError(
            "current shared llama.cpp qualification requires the live per-launch server log"
        )

    target_file = target_path if target_path.is_absolute() else repo_root / target_path
    target = load_actual_model_target(target_file)
    verification = verify_actual_model_artifact(
        target=target,
        artifact_path=artifact_path,
    )

    origin = _origin_from_api_base(base_url)
    headers = _headers(api_key)
    with httpx.Client(
        timeout=NON_GENERATIVE_PREFLIGHT_TIMEOUT_SECONDS,
        trust_env=False,
        headers=headers,
    ) as client:
        health = _get_json(client, f"{origin}/health", "health")
        if not isinstance(health, dict) or health.get("status") != "ok":
            raise LlamaCppStageRQualificationError("llama-server /health is not ok")
        model_ids = _model_ids(_get_json(client, f"{base_url}/models", "models"))
        if request_model not in model_ids:
            raise LlamaCppStageRQualificationError(
                "requested model is not present in llama-server /v1/models"
            )
        props = _get_json(client, f"{origin}/props", "props")
        slots = _get_json(client, f"{origin}/slots", "slots")

    if not isinstance(props, dict):
        raise LlamaCppStageRQualificationError("llama-server /props must be an object")
    if not isinstance(slots, list):
        raise LlamaCppStageRQualificationError("llama-server /slots must be an array")
    build_info = props.get("build_info")
    if not isinstance(build_info, str) or str(expected_build_number) not in build_info:
        raise LlamaCppStageRQualificationError(
            "llama-server build_info does not contain the expected build number"
        )
    runtime = attest_llama_cpp_runtime(
        props=props,
        slots=slots,
        upstream_revision=upstream_revision,
        expected_build_info=build_info,
        expected_model_alias=request_model,
        expected_model_path=str(artifact_path),
        artifact_sha256=verification.artifact_sha256,
        context_shift_enabled=False,
    )
    if runtime.context_limit != expected_context_window:
        raise LlamaCppStageRQualificationError(
            "attested llama.cpp context limit does not match expected context window"
        )
    if runtime.total_slots != expected_slots:
        raise LlamaCppStageRQualificationError(
            "attested llama.cpp slot count does not match expected slots"
        )

    counter = LlamaCppThinkingChatInputCounter(
        base_url=base_url,
        runtime_identity=runtime,
        api_key=api_key,
    )
    capability = _run_capability_smoke(
        base_url=base_url,
        request_model=request_model,
        api_key=api_key,
        counter=counter,
    )
    schema_sha = hashlib.sha256(
        json.dumps(CAPABILITY_SCHEMA, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    evidence = {
        "endpoint": base_url,
        "target": target.to_mapping(),
        "artifact": {
            "canonical_local_path": str(artifact_path),
            "verification": verification.to_mapping(),
        },
        "runtime": {
            **_runtime_mapping(runtime),
            "version": llama_version,
            "build_number": expected_build_number,
        },
        "launch": {
            "context_shift_disabled": True,
            "gpu_identity": gpu_identity,
            "gpu_offload_args": gpu_offload_args,
            "launch_args": launch_args,
            "server_log_path": str(server_log_path),
            "single_slot_required": True,
        },
        "counter_identity": counter.evidence_identity.to_mapping(),
        "thinking": {
            "mode": "off",
            "wire": {"reasoning_effort": "none"},
        },
        "request_timeout_seconds": LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS,
        "json_schema_capability_sha256": f"sha256:{schema_sha}",
        "capability_smoke": capability,
        "non_generative_preflight_request_count": 4,
        "generative_capability_request_count": 2,
    }
    _write_json_create_once(artifact_root / "llama-cpp-physical-binding.json", evidence)
    return {
        "target": target,
        "verification": verification,
        "runtime": runtime,
        "counter": counter,
        "evidence": evidence,
    }


def _run_capability_smoke(
    *,
    base_url: str,
    request_model: str,
    api_key: str | None,
    counter: LlamaCppThinkingChatInputCounter,
) -> dict[str, object]:
    common: dict[str, Any] = {
        "model": request_model,
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 48,
        "stream": False,
        "reasoning_effort": "none",
    }
    plain = {
        **common,
        "messages": [{"role": "user", "content": "Reply with only the word OK."}],
    }
    schema = {
        **common,
        "messages": [
            {"role": "user", "content": "Return a JSON object whose status is ok."}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "relaylm_llama_cpp_capability_smoke",
                "strict": True,
                "schema": CAPABILITY_SCHEMA,
            },
        },
    }
    plain_count = counter.count_input(plain)
    schema_count = counter.count_input(schema)
    with httpx.Client(
        timeout=LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS,
        trust_env=False,
        headers=_headers(api_key),
    ) as client:
        plain_envelope = _post_json(
            client,
            f"{base_url}/chat/completions",
            plain,
            "thinking-off capability smoke",
        )
        schema_envelope = _post_json(
            client,
            f"{base_url}/chat/completions",
            schema,
            "JSON-Schema capability smoke",
        )

    plain_message = _single_message(plain_envelope)
    schema_message = _single_message(schema_envelope)
    if not isinstance(plain_message.get("content"), str) or not plain_message["content"].strip():
        raise LlamaCppStageRQualificationError(
            "thinking-off capability smoke returned no usable content"
        )
    _require_no_reasoning(plain_envelope, plain_message)
    _require_no_reasoning(schema_envelope, schema_message)
    content = schema_message.get("content")
    if not isinstance(content, str):
        raise LlamaCppStageRQualificationError(
            "JSON-Schema capability smoke returned non-string content"
        )
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LlamaCppStageRQualificationError(
            "JSON-Schema capability smoke returned invalid JSON"
        ) from exc
    if parsed != {"status": "ok"}:
        raise LlamaCppStageRQualificationError(
            "JSON-Schema capability smoke violated the requested schema"
        )
    return {
        "thinking_off": {
            "http_success": True,
            "input_tokens": plain_count.total_input_tokens,
            "system_fingerprint": _system_fingerprint(plain_envelope),
        },
        "json_schema": {
            "http_success": True,
            "input_tokens": schema_count.total_input_tokens,
            "system_fingerprint": _system_fingerprint(schema_envelope),
        },
    }


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
    provider = _CompletionObservingLlamaProvider(
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
    )
    identity = describe_openai_compatible_provider(provider)
    fixture_root = repo_root / CANONICAL_FIXTURE_PATH
    manifest = ActualModelRunManifest(
        relaylm_commit=_git_identity(repo_root)[0],
        character_fixture_id=scenario_set.character_fixture_id,
        character_fixture_revision=character_fixture_revision(fixture_root),
        provider_identity=(
            "llama_cpp:"
            f"{runtime.upstream_revision}:{request_model}:reasoning_effort=none"
        ),
        adapter_identity=identity.adapter_identity,
        model_artifact=target.model_artifact_identity,
        tokenizer_identity=target.tokenizer_identity,
        effective_context_window=runtime.context_limit,
        decoding_configuration=tuple(
            sorted(identity.effective_decoding_configuration.items())
        ),
        structured_output_schema_version="relaylm-cognitive-output-v1",
        scenario_set_version=scenario_set.scenario_set_version,
        condition_id="stage-r-llama-cpp-reference-v1",
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
        "classification": classification,
        "semantic_authority_id": authority.authority_id,
        "scenario_set_revision": authority.scenario_set_revision,
        "artifact_verification": verification.to_mapping(),
        "runtime": _runtime_mapping(runtime),
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
        "executions": executions,
    }


def _request_failure(result: ActualModelScenarioExecutionResult) -> str | None:
    evidence = result.evidence
    if isinstance(evidence, ActualModelEvidence) and evidence.request_failure is not None:
        return "request_failure"
    return None


def _completion_evidence_is_thinking_off(paths: Sequence[Path]) -> bool:
    if not paths:
        return False
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        reasoning = document.get("reasoning")
        if not isinstance(reasoning, dict):
            return False
        if reasoning.get("reasoning") == "nonempty":
            return False
        if reasoning.get("reasoning_content") == "nonempty":
            return False
        tokens = reasoning.get("reasoning_tokens")
        if isinstance(tokens, int) and tokens > 0:
            return False
    return True


def _completion_observation(
    *,
    envelope: Any,
    boundary: str,
    sequence_index: int,
) -> dict[str, object]:
    message = _single_message(envelope)
    choice = envelope["choices"][0]
    usage = envelope.get("usage") if isinstance(envelope, dict) else None
    details = usage.get("completion_tokens_details") if isinstance(usage, dict) else None
    reasoning_tokens = None
    if isinstance(details, dict):
        raw = details.get("reasoning_tokens")
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
            reasoning_tokens = raw
    return {
        "format_version": 1,
        "sequence_index": sequence_index,
        "boundary": boundary,
        "finish_reason": choice.get("finish_reason") if isinstance(choice, dict) else None,
        "system_fingerprint": _system_fingerprint(envelope),
        "reasoning": {
            "reasoning": _field_status(message, "reasoning"),
            "reasoning_content": _field_status(message, "reasoning_content"),
            "reasoning_tokens": reasoning_tokens,
        },
    }


def _require_no_reasoning(envelope: Any, message: dict[str, Any]) -> None:
    for key in ("reasoning", "reasoning_content"):
        if _field_status(message, key) == "nonempty":
            raise LlamaCppStageRQualificationError(
                "explicit llama.cpp thinking OFF produced non-empty reasoning output"
            )
    usage = envelope.get("usage") if isinstance(envelope, dict) else None
    details = usage.get("completion_tokens_details") if isinstance(usage, dict) else None
    if isinstance(details, dict):
        tokens = details.get("reasoning_tokens")
        if isinstance(tokens, int) and not isinstance(tokens, bool) and tokens > 0:
            raise LlamaCppStageRQualificationError(
                "explicit llama.cpp thinking OFF reported reasoning tokens"
            )


def _field_status(message: dict[str, Any], key: str) -> str:
    if key not in message:
        return "absent"
    value = message[key]
    if value is None:
        return "empty"
    if isinstance(value, str):
        return "empty" if not value.strip() else "nonempty"
    if isinstance(value, (list, tuple, dict, set, frozenset, bytes, bytearray)):
        return "empty" if len(value) == 0 else "nonempty"
    return "nonempty"


def _single_message(envelope: Any) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise LlamaCppStageRQualificationError("provider response must be an object")
    choices = envelope.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise LlamaCppStageRQualificationError(
            "provider response must contain exactly one choice"
        )
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise LlamaCppStageRQualificationError("provider choice must contain a message")
    return message


def _system_fingerprint(envelope: Any) -> str | None:
    if not isinstance(envelope, dict):
        return None
    value = envelope.get("system_fingerprint")
    return value if isinstance(value, str) and value.strip() else None


def _model_ids(document: Any) -> tuple[str, ...]:
    if not isinstance(document, dict):
        raise LlamaCppStageRQualificationError("/v1/models response must be an object")
    data = document.get("data")
    if not isinstance(data, list):
        raise LlamaCppStageRQualificationError("/v1/models data must be an array")
    ids = tuple(
        item["id"]
        for item in data
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item["id"].strip()
    )
    if not ids:
        raise LlamaCppStageRQualificationError("/v1/models exposes no model IDs")
    return ids


def _get_json(client: httpx.Client, url: str, label: str) -> Any:
    try:
        response = client.get(url)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LlamaCppStageRQualificationError(
            f"llama-server {label} request failed: {exc}"
        ) from exc


def _post_json(
    client: httpx.Client,
    url: str,
    body: dict[str, Any],
    label: str,
) -> Any:
    try:
        response = client.post(url, json=body)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LlamaCppStageRQualificationError(
            f"llama-server {label} request failed: {exc}"
        ) from exc


def _headers(api_key: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _origin_from_api_base(base_url: str) -> str:
    parsed = urlsplit(base_url)
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")


def _require_local_llama_api_base(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise LlamaCppStageRQualificationError("provider-base-url must not be empty")
    value = base_url.rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port != 1234
        or parsed.path != "/v1"
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise LlamaCppStageRQualificationError(
            "current llama.cpp qualification endpoint must be http://127.0.0.1:1234/v1"
        )
    return value


def _runtime_mapping(runtime: LlamaCppRuntimeIdentity) -> dict[str, object]:
    return {
        "upstream_revision": runtime.upstream_revision,
        "build_info": runtime.build_info,
        "model_alias": runtime.model_alias,
        "model_path": runtime.model_path,
        "model_ftype": runtime.model_ftype,
        "artifact_sha256": runtime.artifact_sha256,
        "chat_template_sha256": runtime.chat_template_sha256,
        "context_limit": runtime.context_limit,
        "total_slots": runtime.total_slots,
        "context_shift_enabled": runtime.context_shift_enabled,
    }


def _git_identity(repo_root: Path) -> tuple[str, str]:
    values: list[str] = []
    for rev in ("HEAD", "HEAD^{tree}"):
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", rev],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        value = completed.stdout.strip()
        if completed.returncode != 0 or len(value) != 40:
            raise LlamaCppStageRQualificationError(
                f"cannot determine exact RelayLM git identity for {rev}"
            )
        values.append(value)
    return values[0], values[1]


def _require_clean_repo(repo_root: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise LlamaCppStageRQualificationError("cannot inspect RelayLM checkout state")
    if completed.stdout.strip():
        raise LlamaCppStageRQualificationError(
            "llama.cpp qualification requires a clean exact RelayLM checkout"
        )


def _frozen_core_fingerprint(repo_root: Path) -> str:
    path = repo_root / "evaluation/actual_model/qualifications/core-semantic-v1.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    value = document.get("expected_fingerprint") if isinstance(document, dict) else None
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise LlamaCppStageRQualificationError(
            "cannot read frozen Core semantic fingerprint"
        )
    return value


def _failure_summary(
    *,
    classification: str,
    phase: str,
    head: str,
    tree: str,
    core_fingerprint: str,
    base_url: str,
    exc: Exception,
    semantic_execution_started: bool,
) -> dict[str, object]:
    return {
        "format_version": QUALIFICATION_FORMAT_VERSION,
        "classification": classification,
        "phase": phase,
        "relaylm": {
            "head": head,
            "tree": tree,
            "core_semantic_fingerprint": core_fingerprint,
        },
        "provider_base_url": base_url,
        "failure": _bounded_failure(exc),
        "semantic_execution_started": semantic_execution_started,
        "semantic_retry_count": 0,
        "fallback_count": 0,
    }


def _bounded_failure(exc: Exception) -> dict[str, str | None]:
    message = (
        str(exc)
        if isinstance(
            exc,
            (LlamaCppStageRQualificationError, LlamaCppRuntimeAttestationError),
        )
        else None
    )
    if message is not None:
        message = " ".join(message.split())[:512]
    return {"exception_type": type(exc).__name__, "message": message}


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
            raise LlamaCppStageRQualificationError(
                f"artifact already exists with different content: {path}"
            )


if __name__ == "__main__":
    raise SystemExit(main())
