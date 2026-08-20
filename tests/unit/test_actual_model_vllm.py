from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_evaluation import (
    ActualModelCognitionPassRequests,
    ActualModelRunManifest,
    ExplicitBudgetConfiguration,
)
from relaylm.actual_model_targets import (
    ActualModelRepositorySnapshotVerification,
    load_actual_model_repository_snapshot_target,
)
from relaylm.actual_model_vllm import (
    ActualModelVLLMBindingError,
    bind_vllm_execution_condition,
    vllm_manifest_provider_identity,
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


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-vllm-v1.json"
)
SNAPSHOT_ROOT = Path("/tmp/relaylm-unsloth-w4a16-model")


def _target():
    return load_actual_model_repository_snapshot_target(TARGET_PATH)


def _capability(*, model_root: str = str(SNAPSHOT_ROOT), max_model_len: int = 1024):
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
                    "root": model_root,
                    "max_model_len": max_model_len,
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


def _provider(capability=None) -> OpenAICompatibleProvider:
    capability = capability or _capability()
    return OpenAICompatibleProvider(
        base_url="http://127.0.0.1:8000/v1",
        model="gemma-4-12B-it-qat-w4a16",
        decoding_config=OpenAICompatibleDecodingConfig(temperature=0, top_p=1),
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"temperature", "top_p"})
        ),
        vllm_reasoning_capability=capability,
    )


def _verification(*, verified_file_count: int | None = None):
    target = _target()
    return ActualModelRepositorySnapshotVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        verified_file_count=(
            len(target.files) if verified_file_count is None else verified_file_count
        ),
    )


def _manifest(provider: OpenAICompatibleProvider, *, request: CognitionPassRequest):
    target = _target()
    capability = provider.vllm_reasoning_capability
    assert capability is not None
    identity = describe_openai_compatible_provider(provider)
    return ActualModelRunManifest(
        relaylm_commit="4" * 40,
        character_fixture_id="actual-eval",
        character_fixture_revision="sha256:fixture-v1",
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
        condition_id="cogp5-vllm-screening",
        budgets=ExplicitBudgetConfiguration(),
        execution_path=BUFFERED_EXECUTION_PATH,
        provider_capabilities=identity.provider_capabilities,
        cognition_execution=CognitionExecutionEvidenceIdentity.single_pass(
            execution_path=BUFFERED_EXECUTION_PATH
        ),
        cognition_pass_requests=ActualModelCognitionPassRequests.single_pass(request),
    )


def test_vllm_binding_binds_snapshot_live_runtime_capability_provider_and_manifest() -> None:
    target = _target()
    capability = _capability()
    provider = _provider(capability)
    manifest = _manifest(
        provider,
        request=CognitionPassRequest(
            reasoning_mode=CognitionReasoningMode.OFF,
            temperature=0,
            top_p=1,
        ),
    )

    binding = bind_vllm_execution_condition(
        target=target,
        snapshot_verification=_verification(),
        snapshot_root=SNAPSHOT_ROOT,
        reasoning_capability=capability,
        provider=provider,
        manifest=manifest,
        configured_context_window=1024,
    )

    assert binding.target_id == target.target_id
    assert binding.target_revision == target.revision
    assert binding.snapshot_verification.verified_file_count == len(target.files)
    assert binding.reasoning_capability == capability
    assert binding.provider_identity.model == "gemma-4-12B-it-qat-w4a16"
    assert binding.manifest == manifest
    mapping = binding.to_mapping()
    assert mapping["runtime"]["backend"] == "vllm"
    assert mapping["runtime"]["version"] == "0.27.1"
    assert mapping["runtime"]["reasoning_parser"] == "gemma4"
    assert mapping["runtime"]["template_thinking_control"] == "enable_thinking"


def test_vllm_binding_rejects_snapshot_verification_drift() -> None:
    capability = _capability()
    provider = _provider(capability)
    manifest = _manifest(
        provider,
        request=CognitionPassRequest(reasoning_mode=CognitionReasoningMode.OFF),
    )

    with pytest.raises(ActualModelVLLMBindingError, match="verified file count"):
        bind_vllm_execution_condition(
            target=_target(),
            snapshot_verification=_verification(verified_file_count=1),
            snapshot_root=SNAPSHOT_ROOT,
            reasoning_capability=capability,
            provider=provider,
            manifest=manifest,
            configured_context_window=1024,
        )


def test_vllm_binding_rejects_live_model_root_or_context_drift() -> None:
    root_drift = _capability(model_root="/tmp/different-model")
    root_provider = _provider(root_drift)
    root_manifest = _manifest(
        root_provider,
        request=CognitionPassRequest(reasoning_mode=CognitionReasoningMode.OFF),
    )
    with pytest.raises(ActualModelVLLMBindingError, match="model_root"):
        bind_vllm_execution_condition(
            target=_target(),
            snapshot_verification=_verification(),
            snapshot_root=SNAPSHOT_ROOT,
            reasoning_capability=root_drift,
            provider=root_provider,
            manifest=root_manifest,
            configured_context_window=1024,
        )

    context_drift = _capability(max_model_len=2048)
    context_provider = _provider(context_drift)
    context_manifest = _manifest(
        context_provider,
        request=CognitionPassRequest(reasoning_mode=CognitionReasoningMode.OFF),
    )
    with pytest.raises(ActualModelVLLMBindingError, match="max_model_len"):
        bind_vllm_execution_condition(
            target=_target(),
            snapshot_verification=_verification(),
            snapshot_root=SNAPSHOT_ROOT,
            reasoning_capability=context_drift,
            provider=context_provider,
            manifest=context_manifest,
            configured_context_window=1024,
        )


def test_vllm_binding_rejects_provider_capability_or_manifest_identity_drift() -> None:
    capability = _capability()
    provider_without_capability = OpenAICompatibleProvider(
        base_url="http://127.0.0.1:8000/v1",
        model="gemma-4-12B-it-qat-w4a16",
        decoding_config=OpenAICompatibleDecodingConfig(temperature=0, top_p=1),
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"temperature", "top_p"})
        ),
    )
    manifest = _manifest(
        _provider(capability),
        request=CognitionPassRequest(reasoning_mode=CognitionReasoningMode.OFF),
    )
    with pytest.raises(ActualModelVLLMBindingError, match="reasoning capability"):
        bind_vllm_execution_condition(
            target=_target(),
            snapshot_verification=_verification(),
            snapshot_root=SNAPSHOT_ROOT,
            reasoning_capability=capability,
            provider=provider_without_capability,
            manifest=manifest,
            configured_context_window=1024,
        )

    provider = _provider(capability)
    drifted_manifest = replace(
        manifest,
        provider_identity="wrong-provider-identity",
    )
    with pytest.raises(ActualModelVLLMBindingError, match="provider_identity"):
        bind_vllm_execution_condition(
            target=_target(),
            snapshot_verification=_verification(),
            snapshot_root=SNAPSHOT_ROOT,
            reasoning_capability=capability,
            provider=provider,
            manifest=drifted_manifest,
            configured_context_window=1024,
        )
