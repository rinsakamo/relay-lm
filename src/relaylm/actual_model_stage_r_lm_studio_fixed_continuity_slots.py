from __future__ import annotations

import argparse
import asyncio
import copy
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
from relaylm.actual_model_evaluation import ActualModelRunManifest
from relaylm.actual_model_execution import run_actual_model_scenario_definition
from relaylm.actual_model_execution_artifacts import write_actual_model_execution_result
from relaylm.actual_model_scenarios import ActualModelScenarioSet
from relaylm.actual_model_stage_r_lm_studio_semantic_first import (
    CANONICAL_FIXTURE_PATH,
    _CompletionObservingTwoPassProvider,
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
    CognitionStructuredOutputMode,
)
from relaylm.providers.lm_studio_reasoning import LMStudioReasoningCapabilityAttestation
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    WIRE_SCHEMA,
    _load_cognitive_wire_json,
    _parse_candidate_collections,
    _require_candidate_sources_in_cognitive_input,
    _resolve_cognition_pass_request,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import describe_openai_compatible_provider
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import (
    _completion_content_and_metadata,
    _extraction_request_body,
    _normalize_extraction_json_content,
    _resolve_extraction_structured_output_mode,
)
from relaylm.providers.vllm_reasoning_capability import VLLMReasoningCapabilityAttestation


FIXED_SLOT_DIAGNOSTIC_FORMAT_VERSION = 1
FIXED_SLOT_SCHEMA_NAME = "relaylm_fixed_continuity_slot_diagnostic"
_FIXED_SLOT_ORDER = ("referent", "unresolved", "active_task")


def _slot_schema(kind: str) -> dict[str, Any]:
    candidate = copy.deepcopy(
        WIRE_SCHEMA["properties"]["continuity_candidates"]["items"]
    )
    candidate["properties"]["kind"] = {"type": "string", "enum": [kind]}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["decision", "transitions"],
        "properties": {
            "decision": {"type": "string", "enum": ["none", "emit"]},
            "transitions": {
                "type": "array",
                "items": candidate,
            },
        },
    }


FIXED_SLOT_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["state_candidates", "continuity_decisions"],
    "properties": {
        "state_candidates": copy.deepcopy(
            WIRE_SCHEMA["properties"]["state_candidates"]
        ),
        "continuity_decisions": {
            "type": "object",
            "additionalProperties": False,
            "required": list(_FIXED_SLOT_ORDER),
            "properties": {
                kind: _slot_schema(kind) for kind in _FIXED_SLOT_ORDER
            },
        },
    },
}


_OLD_EMIT_LINE = "Emit `state_candidates`, then `continuity_candidates`."
_OLD_SHAPE = (
    "Exact top-level shape:\n"
    "`{\"state_candidates\":[],\"continuity_candidates\":[]}`\n\n"
    "Return exactly one JSON object with no extra keys."
)
_FIXED_SLOT_EMIT_LINE = (
    "Emit `state_candidates`, then `continuity_decisions` using the fixed per-kind "
    "diagnostic transport described below."
)
_FIXED_SLOT_TRANSPORT = """FIXED-SLOT DIAGNOSTIC TRANSPORT:
- All State and Continuity semantic rules above remain unchanged. This transport changes only how Continuity decisions are made mechanically explicit for diagnosis.
- Return `continuity_decisions` with exactly the three required keys `referent`, `unresolved`, and `active_task`; evaluate every slot exactly once.
- Each slot has exactly `decision` and `transitions`.
- Use `decision: \"none\"` with `transitions: []` when that kind has no justified transition after applying the existing Continuity rules.
- Use `decision: \"emit\"` with one or more ordinary Continuity wire transitions when that kind has justified `set` or `resolve` transitions.
- Every transition retains the ordinary Continuity wire fields and its `kind` must equal the containing slot kind.
- Do not emit a placeholder transition merely to fill a slot; `none` is the explicit no-candidate decision.

Exact diagnostic top-level shape:
`{"state_candidates":[],"continuity_decisions":{"referent":{"decision":"none","transitions":[]},"unresolved":{"decision":"none","transitions":[]},"active_task":{"decision":"none","transitions":[]}}}`

Return exactly one JSON object with no extra keys."""


def _fixed_slot_prompt(production_prompt: str) -> str:
    if production_prompt.count(_OLD_EMIT_LINE) != 1:
        raise ProviderProtocolError(
            "fixed-slot diagnostic cannot identify production candidate emit instruction"
        )
    if production_prompt.count(_OLD_SHAPE) != 1:
        raise ProviderProtocolError(
            "fixed-slot diagnostic cannot identify production extraction top-level shape"
        )
    return production_prompt.replace(
        _OLD_EMIT_LINE,
        _FIXED_SLOT_EMIT_LINE,
        1,
    ).replace(
        _OLD_SHAPE,
        _FIXED_SLOT_TRANSPORT,
        1,
    )


def _fixed_slot_request_body(
    *,
    provider: _CompletionObservingTwoPassProvider,
    extraction_input: CognitionExtractionInput,
    pass_request: CognitionPassRequest | None,
    reasoning_request: OpenAICompatibleReasoningRequest | None,
    vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None,
    lm_studio_reasoning_capability: LMStudioReasoningCapabilityAttestation | None,
) -> dict[str, Any]:
    effective_vllm = vllm_reasoning_capability or provider.vllm_reasoning_capability
    effective_lm_studio = (
        lm_studio_reasoning_capability or provider.lm_studio_reasoning_capability
    )
    decoding_config, effective_reasoning = _resolve_cognition_pass_request(
        pass_request=pass_request,
        reasoning_request=reasoning_request,
        decoding_config=provider.decoding_config,
        decoding_capabilities=provider.decoding_capabilities,
        vllm_reasoning_capability=effective_vllm,
        lm_studio_reasoning_capability=effective_lm_studio,
    )
    structured_output_mode = _resolve_extraction_structured_output_mode(
        pass_request=pass_request,
        provider=provider,
    )
    if structured_output_mode is not CognitionStructuredOutputMode.NATIVE:
        raise ProviderProtocolError(
            "fixed-slot diagnostic requires native Pass 2 structured output"
        )
    body = _extraction_request_body(
        model=provider.model,
        extraction_input=extraction_input,
        decoding=decoding_config.to_mapping(),
        reasoning_request=effective_reasoning,
        vllm_reasoning_capability=effective_vllm,
        lm_studio_reasoning_capability=effective_lm_studio,
        structured_output_mode=structured_output_mode,
    )
    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        raise ProviderProtocolError(
            "fixed-slot diagnostic expected production two-message extraction request"
        )
    user_message = messages[1]
    if not isinstance(user_message, dict) or not isinstance(
        user_message.get("content"), str
    ):
        raise ProviderProtocolError(
            "fixed-slot diagnostic expected production extraction user prompt"
        )
    user_message["content"] = _fixed_slot_prompt(user_message["content"])
    body["response_format"] = {
        "type": "json_schema",
        "json_schema": {
            "name": FIXED_SLOT_SCHEMA_NAME,
            "strict": True,
            "schema": FIXED_SLOT_EXTRACTION_SCHEMA,
        },
    }
    return body


def _parse_fixed_slot_wire(
    *,
    wire: object,
    completion: object,
) -> tuple[CognitionExtractionOutput, dict[str, object]]:
    if not isinstance(wire, dict) or set(wire) != {
        "state_candidates",
        "continuity_decisions",
    }:
        raise ProviderProtocolError(
            "fixed-slot extraction must contain exactly state_candidates and "
            "continuity_decisions"
        )
    decisions = wire["continuity_decisions"]
    if not isinstance(decisions, dict) or set(decisions) != set(_FIXED_SLOT_ORDER):
        raise ProviderProtocolError(
            "fixed-slot continuity_decisions must contain exactly referent, "
            "unresolved, and active_task"
        )

    flattened: list[object] = []
    normalized_decisions: dict[str, object] = {}
    for kind in _FIXED_SLOT_ORDER:
        slot = decisions[kind]
        if not isinstance(slot, dict) or set(slot) != {"decision", "transitions"}:
            raise ProviderProtocolError(
                f"fixed-slot {kind} decision must contain exactly decision and transitions"
            )
        decision = slot["decision"]
        transitions = slot["transitions"]
        if decision not in {"none", "emit"} or not isinstance(transitions, list):
            raise ProviderProtocolError(
                f"fixed-slot {kind} decision/transitions have invalid types"
            )
        if decision == "none" and transitions:
            raise ProviderProtocolError(
                f"fixed-slot {kind} none decision must have empty transitions"
            )
        if decision == "emit" and not transitions:
            raise ProviderProtocolError(
                f"fixed-slot {kind} emit decision must have non-empty transitions"
            )
        for transition in transitions:
            if not isinstance(transition, dict) or transition.get("kind") != kind:
                raise ProviderProtocolError(
                    f"fixed-slot {kind} transition kind must match its containing slot"
                )
        flattened.extend(transitions)
        normalized_decisions[kind] = {
            "decision": decision,
            "transitions": transitions,
        }

    state_candidates, continuity_candidates = _parse_candidate_collections(
        raw_candidates=wire["state_candidates"],
        raw_continuity_candidates=flattened,
    )
    output = CognitionExtractionOutput(
        state_candidates=state_candidates,
        continuity_candidates=continuity_candidates,
        completion=completion,
    )
    return output, normalized_decisions


class FixedContinuitySlotDiagnosticProvider(_CompletionObservingTwoPassProvider):
    """Evaluation-only fixed-slot Pass 2 transport over production semantics."""

    def __init__(
        self,
        *args: Any,
        slot_observation_root: Path,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._slot_observation_root = slot_observation_root
        self.slot_observation_artifacts: list[Path] = []

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
        vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
        lm_studio_reasoning_capability: LMStudioReasoningCapabilityAttestation | None = None,
    ) -> CognitionExtractionOutput:
        body = _fixed_slot_request_body(
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
            invalid_message="fixed-slot extraction content is not valid JSON",
        )
        output, decisions = _parse_fixed_slot_wire(
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
                "format_version": FIXED_SLOT_DIAGNOSTIC_FORMAT_VERSION,
                "sequence_index": sequence_index,
                "originating_event_id": extraction_input.originating_event_id,
                "continuity_decisions": decisions,
            },
        )
        self.slot_observation_artifacts.append(observation_path)
        return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run current LM Studio Stage R with an evaluation-only fixed per-kind "
            "Continuity decision transport."
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
            "fixed-slot diagnostic requires declared LM Studio reasoning option off"
        )
    if args.context_window <= 0:
        raise ValueError("context-window must be positive")

    binding = {
        "format_version": FIXED_SLOT_DIAGNOSTIC_FORMAT_VERSION,
        "diagnostic": "fixed_per_kind_continuity_decisions",
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
        artifact_root / "lm-studio-fixed-continuity-slots-binding.json",
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
        artifact_root / "stage-r-lm-studio-fixed-continuity-slots-summary.json",
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
    provider = FixedContinuitySlotDiagnosticProvider(
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
            artifact_root / "lm-studio-fixed-slot-completion-observations"
        ),
        slot_observation_root=(
            artifact_root / "lm-studio-fixed-slot-decision-observations"
        ),
    )
    identity = describe_openai_compatible_provider(provider)
    fixture_root = repo_root / CANONICAL_FIXTURE_PATH
    manifest = ActualModelRunManifest(
        relaylm_commit=_git_head(repo_root),
        character_fixture_id=scenario_set.character_fixture_id,
        character_fixture_revision=character_fixture_revision(fixture_root),
        provider_identity=(
            "lm_studio_declared_fixed_continuity_slots:"
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
            "relaylm-fixed-continuity-slot-diagnostic-v1"
        ),
        scenario_set_version=scenario_set.scenario_set_version,
        condition_id="stage-r-lm-studio-fixed-continuity-slots-v1",
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
                "fixed_slot_decision_artifacts": [
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
        "format_version": FIXED_SLOT_DIAGNOSTIC_FORMAT_VERSION,
        "diagnostic": "fixed_per_kind_continuity_decisions",
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
        "fixed_slot_decision_observation_count": len(
            provider.slot_observation_artifacts
        ),
        "fixed_slot_decision_observation_artifacts": [
            str(path) for path in provider.slot_observation_artifacts
        ],
        "stop_reason": stop_reason,
        "executions": executions,
    }


if __name__ == "__main__":
    raise SystemExit(main())
