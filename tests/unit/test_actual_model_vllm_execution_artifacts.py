from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_evaluation import (
    ActualModelCognitionPassRequests,
    ActualModelRunManifest,
    ExplicitBudgetConfiguration,
    ExplicitContinuityRuntimeConfiguration,
)
from relaylm.actual_model_execution import _stable_execution_id
from relaylm.actual_model_scenarios import load_actual_model_scenario_set
from relaylm.actual_model_targets import (
    ActualModelRepositorySnapshotVerification,
    load_actual_model_repository_snapshot_target,
)
from relaylm.actual_model_vllm import (
    ActualModelVLLMBindingError,
    _stable_id,
    run_vllm_actual_model_scenario_definition,
    vllm_manifest_provider_identity,
    write_vllm_actual_model_execution_result,
)
from relaylm.cognition_execution import CognitionPassRequest, CognitionReasoningMode
from relaylm.cognition_execution_evidence import (
    BUFFERED_EXECUTION_PATH,
    CognitionExecutionEvidenceIdentity,
)
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import describe_openai_compatible_provider
from relaylm.providers.vllm_backend import attest_vllm_backend
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningProbeEvidence,
    attest_vllm_reasoning_capabilities,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TARGET_PATH = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-vllm-v1.json"
)
_SCENARIO_SET_PATH = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "scenario_sets"
    / "foundation-v2.json"
)
_FIXTURE_ROOT = (
    _REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "characters"
    / "foundation-v1"
)
_SNAPSHOT_ROOT = Path("/tmp/relaylm-unsloth-w4a16-model")


def _target():
    return load_actual_model_repository_snapshot_target(_TARGET_PATH)


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
                    "root": str(_SNAPSHOT_ROOT),
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


def _provider(capability) -> OpenAICompatibleProvider:
    response_content = json.dumps(
        {
            "utterance": "grounded response",
            "state_candidates": [],
            "continuity_candidates": [],
        },
        separators=(",", ":"),
    )

    def mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": response_content},
                        "finish_reason": "stop",
                    }
                ]
            },
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_transport))
    provider = OpenAICompatibleProvider(
        base_url="http://127.0.0.1:8000/v1",
        model="gemma-4-12B-it-qat-w4a16",
        decoding_config=OpenAICompatibleDecodingConfig(temperature=0, top_p=1),
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"temperature", "top_p"})
        ),
        vllm_reasoning_capability=capability,
        http_client=client,
    )
    # The test-created client belongs to this test-created provider.
    provider._owns_client = True
    return provider


def _verification() -> ActualModelRepositorySnapshotVerification:
    target = _target()
    return ActualModelRepositorySnapshotVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        verified_file_count=len(target.files),
    )


def _manifest(
    provider: OpenAICompatibleProvider,
    *,
    replicate_id: str = "0",
) -> ActualModelRunManifest:
    target = _target()
    capability = provider.vllm_reasoning_capability
    assert capability is not None
    identity = describe_openai_compatible_provider(provider)
    request = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.OFF,
        temperature=0,
        top_p=1,
    )
    return ActualModelRunManifest(
        relaylm_commit="4" * 40,
        character_fixture_id="actual-model-foundation-v1",
        character_fixture_revision=character_fixture_revision(_FIXTURE_ROOT),
        provider_identity=vllm_manifest_provider_identity(capability),
        adapter_identity=identity.adapter_identity,
        model_artifact=target.model_artifact_identity,
        tokenizer_identity=target.tokenizer_identity,
        effective_context_window=1024,
        decoding_configuration=tuple(
            sorted(identity.effective_decoding_configuration.items())
        ),
        structured_output_schema_version="relaylm-cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v2",
        condition_id="vllm-execution-id-integrity",
        budgets=ExplicitBudgetConfiguration(),
        continuity_runtime=ExplicitContinuityRuntimeConfiguration(
            max_items=4,
            lifetime_revisions=3,
        ),
        execution_path=BUFFERED_EXECUTION_PATH,
        provider_capabilities=identity.provider_capabilities,
        cognition_execution=CognitionExecutionEvidenceIdentity.single_pass(
            execution_path=BUFFERED_EXECUTION_PATH
        ),
        cognition_pass_requests=ActualModelCognitionPassRequests.single_pass(request),
        replicate_id=replicate_id,
    )


def _production_result(
    tmp_path: Path,
    *,
    replicate_id: str = "0",
):
    capability = _capability()
    provider = _provider(capability)
    manifest = _manifest(provider, replicate_id=replicate_id)
    return asyncio.run(
        run_vllm_actual_model_scenario_definition(
            target=_target(),
            snapshot_verification=_verification(),
            snapshot_root=_SNAPSHOT_ROOT,
            reasoning_capability=capability,
            configured_context_window=1024,
            scenario_set=load_actual_model_scenario_set(_SCENARIO_SET_PATH),
            scenario_id="response-persona-correction-v1",
            fixture_root=_FIXTURE_ROOT,
            workspace_root=tmp_path / "workspace",
            provider=provider,
            manifest=manifest,
        )
    )


def _outer_id(*, binding_id: str, scenario_execution_id: str) -> str:
    return _stable_id(
        prefix="amvx",
        payload={
            "binding_id": binding_id,
            "scenario_execution_id": scenario_execution_id,
        },
    )


def test_vllm_writer_rejects_forged_binding_id_with_recomputed_outer_id(
    tmp_path: Path,
) -> None:
    result = _production_result(tmp_path)
    forged_binding = replace(result.binding, binding_id="amvb-" + "f" * 64)
    forged = replace(
        result,
        binding=forged_binding,
        execution_id=_outer_id(
            binding_id=forged_binding.binding_id,
            scenario_execution_id=result.execution.execution_id,
        ),
    )
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelVLLMBindingError,
        match="binding_id does not match vLLM binding evidence",
    ):
        write_vllm_actual_model_execution_result(
            result=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()


def test_vllm_writer_rejects_forged_nested_execution_id_with_recomputed_outer_id(
    tmp_path: Path,
) -> None:
    result = _production_result(tmp_path)
    forged_execution = replace(
        result.execution,
        execution_id="amx-" + "f" * 64,
    )
    forged = replace(
        result,
        execution=forged_execution,
        execution_id=_outer_id(
            binding_id=result.binding.binding_id,
            scenario_execution_id=forged_execution.execution_id,
        ),
    )
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelVLLMBindingError,
        match="scenario execution_id does not match execution evidence",
    ):
        write_vllm_actual_model_execution_result(
            result=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()


def test_vllm_writer_rejects_forged_outer_execution_id(
    tmp_path: Path,
) -> None:
    result = _production_result(tmp_path)
    forged = replace(result, execution_id="amvx-" + "f" * 64)
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelVLLMBindingError,
        match="execution_id does not match vLLM execution evidence",
    ):
        write_vllm_actual_model_execution_result(
            result=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()


def test_vllm_writer_rejects_forged_nested_plan_with_recomputed_ids(
    tmp_path: Path,
) -> None:
    result = _production_result(tmp_path)
    forged_plan = replace(result.execution.plan, plan_id="amp-" + "f" * 64)
    forged_execution = replace(
        result.execution,
        plan=forged_plan,
        execution_id=_stable_execution_id(
            plan=forged_plan,
            run_id=result.execution.run_id,
        ),
    )
    forged = replace(
        result,
        execution=forged_execution,
        execution_id=_outer_id(
            binding_id=result.binding.binding_id,
            scenario_execution_id=forged_execution.execution_id,
        ),
    )
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelVLLMBindingError,
        match="scenario execution is not citable",
    ):
        write_vllm_actual_model_execution_result(
            result=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()


def test_vllm_writer_rejects_execution_from_another_valid_binding_manifest(
    tmp_path: Path,
) -> None:
    first = _production_result(tmp_path / "first", replicate_id="0")
    second = _production_result(tmp_path / "second", replicate_id="1")
    mixed = replace(
        first,
        execution=second.execution,
        execution_id=_outer_id(
            binding_id=first.binding.binding_id,
            scenario_execution_id=second.execution.execution_id,
        ),
    )
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelVLLMBindingError,
        match="binding manifest does not match scenario execution plan",
    ):
        write_vllm_actual_model_execution_result(
            result=mixed,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()
