from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

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
from relaylm.actual_model_vllm import (
    ActualModelVLLMBindingError,
    run_bound_vllm_actual_model_scenario_definition,
    run_vllm_actual_model_scenario_definition,
)
import relaylm.actual_model_vllm_host as vllm_host
from relaylm.actual_model_fast_screening import (
    ScreeningTimingRecorder,
    instrument_screening_provider,
)
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
CURRENT_SCREENING_ID = "stage-r0-vllm-reference-v2"
REFERENCE_BASELINE_ROLE = "reference_baseline"
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
                        "screening_id": CURRENT_SCREENING_ID,
                        "effective_context_window": 1024,
                    },
                )(),
                "screening_condition_id": REFERENCE_BASELINE_ROLE,
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


def test_timing_wrapper_remains_rejected_by_binding_gate() -> None:
    prepared, _ = _prepared()
    recorder = ScreeningTimingRecorder()
    wrapped = instrument_screening_provider(prepared.provider, recorder=recorder)

    with pytest.raises(TypeError, match="provider must be OpenAICompatibleProvider"):
        bind_vllm_execution_condition(
            target=prepared.target,
            snapshot_verification=prepared.snapshot_verification,
            snapshot_root=SNAPSHOT_ROOT,
            reasoning_capability=prepared.reasoning_capability,
            provider=wrapped,  # type: ignore[arg-type]
            manifest=prepared.manifest,
            configured_context_window=1024,
        )

    asyncio.run(prepared.provider.aclose())


def test_direct_vllm_execution_still_binds_original_provider(
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

    result = asyncio.run(
        run_vllm_actual_model_scenario_definition(
            target=prepared.target,
            snapshot_verification=prepared.snapshot_verification,
            snapshot_root=SNAPSHOT_ROOT,
            reasoning_capability=prepared.reasoning_capability,
            configured_context_window=1024,
            scenario_set=prepared.scenario_set,
            scenario_id="response-persona-correction-v1",
            fixture_root=prepared.fixture_root,
            workspace_root=tmp_path / "workspace",
            provider=prepared.provider,
            manifest=prepared.manifest,
        )
    )

    assert result.binding == binding
    asyncio.run(prepared.provider.aclose())


def test_prebound_execution_preserves_binding_and_records_both_passes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    prepared, binding = _prepared()
    recorder = ScreeningTimingRecorder()
    wrapped = instrument_screening_provider(prepared.provider, recorder=recorder)
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

    result = asyncio.run(
        run_bound_vllm_actual_model_scenario_definition(
            binding=binding,
            scenario_set=prepared.scenario_set,
            scenario_id="response-persona-correction-v1",
            fixture_root=prepared.fixture_root,
            workspace_root=tmp_path / "workspace",
            provider=wrapped,  # type: ignore[arg-type]
        )
    )

    assert result.binding is binding
    assert tuple(call.phase for call in recorder.calls) == (
        "pass1",
        "pass2",
        "pass1",
        "pass2",
        "pass1",
        "pass2",
    )
    asyncio.run(prepared.provider.aclose())


def test_invalid_prebound_binding_fails_without_rebinding_or_generation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    prepared, binding = _prepared()
    invalid = replace(binding, binding_id="amvb-" + "f" * 64)
    calls = []

    async def should_not_generate(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("invalid prebound evidence reached provider generation")

    monkeypatch.setattr(
        OpenAICompatibleTwoPassProvider,
        "generate_conversation",
        should_not_generate,
    )

    with pytest.raises(
        ActualModelVLLMBindingError,
        match="binding_id does not match vLLM binding evidence",
    ):
        asyncio.run(
            run_bound_vllm_actual_model_scenario_definition(
                binding=invalid,
                scenario_set=prepared.scenario_set,
                scenario_id="response-persona-correction-v1",
                fixture_root=prepared.fixture_root,
                workspace_root=tmp_path / "workspace",
                provider=prepared.provider,
            )
        )

    assert calls == []
    asyncio.run(prepared.provider.aclose())
