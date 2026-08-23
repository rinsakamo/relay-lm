from __future__ import annotations

import asyncio
import json
from pathlib import Path

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_evaluation import (
    ActualModelCognitionPassRequests,
    ActualModelRunManifest,
    ExplicitBudgetConfiguration,
    ExplicitContinuityRuntimeConfiguration,
)
from relaylm.actual_model_scenarios import load_actual_model_scenario_set
from relaylm.actual_model_targets import (
    ActualModelRepositorySnapshotVerification,
    load_actual_model_repository_snapshot_target,
)
from relaylm.actual_model_vllm import bind_vllm_execution_condition
import relaylm.actual_model_vllm_host as vllm_host
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionOutput,
    CognitionPassRequest,
    CognitionReasoningMode,
)
from relaylm.cognition_execution_evidence import (
    BUFFERED_EXECUTION_PATH,
    CognitionExecutionEvidenceIdentity,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import (
    describe_openai_compatible_provider,
)
from relaylm.providers.openai_compatible_two_pass import (
    OpenAICompatibleTwoPassProvider,
)
from relaylm.providers.vllm_backend import attest_vllm_backend
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningProbeEvidence,
    attest_vllm_reasoning_capabilities,
)


ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = (
    ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-vllm-v1.json"
)
SCENARIO_SET_PATH = (
    ROOT / "evaluation" / "actual_model" / "scenario_sets" / "foundation-v2.json"
)
FIXTURE_ROOT = ROOT / "evaluation" / "actual_model" / "characters" / "foundation-v1"
SNAPSHOT_ROOT = Path("/tmp/relaylm-unsloth-w4a16-model")
CONDITION_ID = "stage-r0-vllm-b-two-pass-off-off"


def _target():
    return load_actual_model_repository_snapshot_target(TARGET_PATH)


def _capability():
    target = _target()
    backend = attest_vllm_backend(
        request_model="gemma-4-12B-it-qat-w4a16",
        version_response={"version": "0.27.1"},
        models_response={
            "object": "list",
            "data": [
                {
                    "id": "gemma-4-12B-it-qat-w4a16",
                    "object": "model",
                    "root": str(SNAPSHOT_ROOT),
                    "max_model_len": 1024,
                }
            ],
        },
    )
    return attest_vllm_reasoning_capabilities(
        backend_attestation=backend,
        target=target,
        reasoning_parser="gemma4",
        template_thinking_control="enable_thinking",
        off_probe=VLLMReasoningProbeEvidence(
            wire_controls=VLLMReasoningWireControls(reasoning_effort="none"),
            http_status=200,
            accepted=True,
            effect_proven=True,
            repeatable=True,
        ),
        bounded_probe=VLLMReasoningProbeEvidence(
            wire_controls=VLLMReasoningWireControls(thinking_token_budget=16),
            http_status=200,
            accepted=True,
            effect_proven=True,
            repeatable=True,
            activation_applied=True,
            template_kwargs=(("enable_thinking", True),),
        ),
    )


def _provider(capability):
    return OpenAICompatibleTwoPassProvider(
        base_url="http://127.0.0.1:8000/v1",
        model="gemma-4-12B-it-qat-w4a16",
        decoding_config=OpenAICompatibleDecodingConfig(temperature=0, top_p=1),
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"temperature", "top_p"})
        ),
        vllm_reasoning_capability=capability,
    )


def _prepared():
    target = _target()
    capability = _capability()
    provider = _provider(capability)
    scenario_set = load_actual_model_scenario_set(SCENARIO_SET_PATH)
    execution_identity = CognitionExecutionEvidenceIdentity.two_pass(
        execution_path=BUFFERED_EXECUTION_PATH
    )
    pass_request = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.OFF,
        temperature=0,
        top_p=1,
    )
    pass_requests = ActualModelCognitionPassRequests.two_pass(
        pass1=pass_request,
        pass2=pass_request,
    )
    identity = describe_openai_compatible_provider(provider)
    manifest = ActualModelRunManifest(
        relaylm_commit="4" * 40,
        character_fixture_id=scenario_set.character_fixture_id,
        character_fixture_revision=character_fixture_revision(FIXTURE_ROOT),
        provider_identity=vllm_host.vllm_manifest_provider_identity(capability),
        adapter_identity=identity.adapter_identity,
        model_artifact=target.model_artifact_identity,
        tokenizer_identity=target.tokenizer_identity,
        effective_context_window=1024,
        decoding_configuration=tuple(
            sorted(identity.effective_decoding_configuration.items())
        ),
        structured_output_schema_version="relaylm-cognitive-output-v1",
        scenario_set_version=scenario_set.scenario_set_version,
        condition_id=CONDITION_ID,
        budgets=ExplicitBudgetConfiguration(),
        continuity_runtime=ExplicitContinuityRuntimeConfiguration(
            max_items=4,
            lifetime_revisions=3,
        ),
        execution_path=BUFFERED_EXECUTION_PATH,
        provider_capabilities=identity.provider_capabilities,
        cognition_execution=execution_identity,
        cognition_pass_requests=pass_requests,
        replicate_id="timing-wrapper-regression",
    )
    snapshot_verification = ActualModelRepositorySnapshotVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        verified_file_count=len(target.files),
    )
    binding = bind_vllm_execution_condition(
        target=target,
        snapshot_verification=snapshot_verification,
        snapshot_root=SNAPSHOT_ROOT,
        reasoning_capability=capability,
        provider=provider,
        manifest=manifest,
        configured_context_window=1024,
    )
    return (
        type(
            "Prepared",
            (),
            {
                "plan": type(
                    "Plan",
                    (),
                    {
                        "screening_id": "stage-r0-vllm-reference-v1",
                        "effective_context_window": 1024,
                    },
                )(),
                "screening_condition_id": CONDITION_ID,
                "condition": type(
                    "Condition",
                    (),
                    {"cognition_execution": execution_identity},
                )(),
                "manifest": manifest,
                "scenario_set": scenario_set,
                "fixture_root": FIXTURE_ROOT,
                "target": target,
                "snapshot_verification": snapshot_verification,
                "reasoning_capability": capability,
                "provider": provider,
                "cognitive_budget": None,
                "binding": binding,
                "scenario_ids": ("response-persona-correction-v1",),
            },
        )(),
        binding,
    )


async def _stub_conversation(
    self,
    cognitive_input,
    *,
    pass_request=None,
    reasoning_request=None,
    vllm_reasoning_capability=None,
):
    del self, cognitive_input, pass_request, reasoning_request, vllm_reasoning_capability
    return CognitionConversationOutput(response="stub response")


async def _stub_extraction(
    self,
    extraction_input,
    *,
    pass_request=None,
    reasoning_request=None,
    vllm_reasoning_capability=None,
):
    del self, extraction_input, pass_request, reasoning_request, vllm_reasoning_capability
    return CognitionExtractionOutput()


def test_host_timing_wrapper_uses_precomputed_vllm_binding(
    tmp_path: Path,
    monkeypatch,
) -> None:
    prepared, binding = _prepared()
    monkeypatch.setattr(
        OpenAICompatibleTwoPassProvider,
        "generate_conversation",
        _stub_conversation,
    )
    monkeypatch.setattr(
        OpenAICompatibleTwoPassProvider,
        "generate_extraction",
        _stub_extraction,
    )

    results = asyncio.run(
        vllm_host.execute_vllm_host_run(
            prepared=prepared,
            snapshot_root=SNAPSHOT_ROOT,
            workspace_root=tmp_path / "workspace",
            artifact_root=tmp_path / "evidence",
        )
    )

    assert len(results) == 1
    execution = json.loads(Path(results[0].artifact_path).read_text(encoding="utf-8"))
    assert execution["binding"]["binding_id"] == binding.binding_id
    timing = json.loads(
        Path(results[0].timing_artifact_path).read_text(encoding="utf-8")
    )
    assert all(turn["response_outcome"] == "completed" for turn in timing["turns"])
    assert all(turn["extraction_outcome"] == "completed" for turn in timing["turns"])
