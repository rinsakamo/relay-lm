from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_evaluation import ActualModelRunManifest
from relaylm.actual_model_lm_studio import (
    ActualModelLMStudioBindingError,
    LMStudioExecutionEnvironment,
    bind_lm_studio_execution_condition,
    run_lm_studio_actual_model_scenario_definition,
)
from relaylm.actual_model_targets import (
    ActualModelArtifactVerification,
    load_actual_model_target,
)
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import (
    describe_openai_compatible_provider,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-q4-k-m-v1.json"
)


class _Provider:
    def __init__(self) -> None:
        self.model = "google/gemma-4-12b"
        self.decoding_config = OpenAICompatibleDecodingConfig(
            temperature=0.2,
            top_p=0.95,
            seed=7,
        )
        self.decoding_capabilities = OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"temperature", "top_p", "seed"})
        )
        self.calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(response="ok")


def _environment() -> LMStudioExecutionEnvironment:
    return LMStudioExecutionEnvironment(
        version="0.3.30",
        build="example-build-123",
        deployment_identity="local-lm-studio-primary",
        request_model="google/gemma-4-12b",
    )


def _verification():
    target = load_actual_model_target(TARGET_PATH)
    return ActualModelArtifactVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_size_bytes=target.artifact_size_bytes,
        artifact_sha256=target.artifact_sha256,
    )


def _manifest(provider: _Provider) -> ActualModelRunManifest:
    target = load_actual_model_target(TARGET_PATH)
    environment = _environment()
    identity = describe_openai_compatible_provider(provider)
    return ActualModelRunManifest(
        relaylm_commit="0" * 40,
        character_fixture_id="actual-model-foundation-v1",
        character_fixture_revision="sha256:fixture",
        provider_identity=environment.manifest_provider_identity,
        adapter_identity=identity.adapter_identity,
        model_artifact=target.model_artifact_identity,
        tokenizer_identity=target.tokenizer_identity,
        effective_context_window=32768,
        decoding_configuration=tuple(
            sorted(identity.effective_decoding_configuration.items())
        ),
        structured_output_schema_version="relaylm-cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v2",
        condition_id="canonical-baseline",
        seed=7,
        provider_capabilities=identity.provider_capabilities,
    )


def test_lm_studio_environment_is_exact_and_secret_free_manifest_identity() -> None:
    environment = _environment()

    assert environment.environment_id.startswith("amlse-")
    assert environment.manifest_provider_identity.startswith(
        "actual-model-lm-studio-v1:"
    )
    assert '"implementation":"lm_studio"' in environment.manifest_provider_identity
    assert '"version":"0.3.30"' in environment.manifest_provider_identity
    assert '"build":"example-build-123"' in environment.manifest_provider_identity
    assert '"request_model":"google/gemma-4-12b"' in environment.manifest_provider_identity
    assert "api_key" not in environment.manifest_provider_identity
    assert "base_url" not in environment.manifest_provider_identity


def test_binding_matches_verified_target_provider_and_manifest() -> None:
    provider = _Provider()
    target = load_actual_model_target(TARGET_PATH)
    manifest = _manifest(provider)

    binding = bind_lm_studio_execution_condition(
        environment=_environment(),
        target=target,
        artifact_verification=_verification(),
        provider=provider,
        manifest=manifest,
        configured_context_window=32768,
    )

    assert binding.binding_id.startswith("amlsb-")
    assert binding.target_id == target.target_id
    assert binding.target_revision == target.revision
    assert binding.provider_identity.model == provider.model
    assert binding.configured_context_window == 32768
    assert binding.manifest == manifest


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("provider_identity", "not-the-runtime", "provider_identity"),
        ("adapter_identity", "wrong-adapter", "adapter_identity"),
        ("model_artifact", "wrong-model", "model_artifact"),
        ("tokenizer_identity", "wrong-tokenizer", "tokenizer_identity"),
        ("effective_context_window", 16384, "effective_context_window"),
        ("decoding_configuration", (("temperature", 0.2),), "decoding_configuration"),
        ("seed", 8, "seed"),
        ("provider_capabilities", ("state_candidates",), "provider_capabilities"),
    ),
)
def test_binding_rejects_manifest_metadata_that_provider_did_not_apply(
    field: str,
    value: object,
    message: str,
) -> None:
    provider = _Provider()
    target = load_actual_model_target(TARGET_PATH)
    manifest = replace(_manifest(provider), **{field: value})

    with pytest.raises(ActualModelLMStudioBindingError, match=message):
        bind_lm_studio_execution_condition(
            environment=_environment(),
            target=target,
            artifact_verification=_verification(),
            provider=provider,
            manifest=manifest,
            configured_context_window=32768,
        )


def test_binding_rejects_request_model_drift() -> None:
    provider = _Provider()
    target = load_actual_model_target(TARGET_PATH)
    environment = replace(_environment(), request_model="another/model")

    with pytest.raises(ActualModelLMStudioBindingError, match="request_model"):
        bind_lm_studio_execution_condition(
            environment=environment,
            target=target,
            artifact_verification=_verification(),
            provider=provider,
            manifest=_manifest(provider),
            configured_context_window=32768,
        )


def test_binding_rejects_unverified_target_revision() -> None:
    provider = _Provider()
    target = load_actual_model_target(TARGET_PATH)
    verification = replace(_verification(), target_revision="sha256:wrong")

    with pytest.raises(ActualModelLMStudioBindingError, match="target_revision"):
        bind_lm_studio_execution_condition(
            environment=_environment(),
            target=target,
            artifact_verification=verification,
            provider=provider,
            manifest=_manifest(provider),
            configured_context_window=32768,
        )


def test_canonical_wrapper_fails_before_generation_or_fixture_access_on_binding_drift() -> None:
    provider = _Provider()
    target = load_actual_model_target(TARGET_PATH)
    manifest = replace(_manifest(provider), seed=8)

    with pytest.raises(ActualModelLMStudioBindingError, match="seed"):
        asyncio.run(
            run_lm_studio_actual_model_scenario_definition(
                environment=_environment(),
                target=target,
                artifact_verification=_verification(),
                configured_context_window=32768,
                scenario_set=None,  # type: ignore[arg-type]
                scenario_id="not-reached",
                fixture_root="/does/not/exist",
                workspace_root="/must/not/be-created",
                provider=provider,
                manifest=manifest,
            )
        )

    assert provider.calls == 0
