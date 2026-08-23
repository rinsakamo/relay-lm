from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.actual_model_lm_studio as lm_studio_subject
from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    ActualModelRunManifest,
    ActualModelScenario,
    stable_actual_model_run_id,
)
from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionPlan,
    ActualModelScenarioExecutionResult,
    _stable_execution_id,
    _stable_plan_id,
)
from relaylm.actual_model_lm_studio import (
    ActualModelLMStudioBindingError,
    ActualModelLMStudioExecutionResult,
    LMStudioExecutionEnvironment,
    bind_lm_studio_execution_condition,
    run_lm_studio_actual_model_scenario_definition,
    write_lm_studio_actual_model_execution_result,
)
from relaylm.actual_model_scenarios import ActualModelScenarioDefinition
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


def _manifest(
    provider: _Provider,
    *,
    replicate_id: str = "0",
) -> ActualModelRunManifest:
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
        replicate_id=replicate_id,
    )


def _execution_result(
    *,
    replicate_id: str = "0",
) -> ActualModelLMStudioExecutionResult:
    provider = _Provider()
    target = load_actual_model_target(TARGET_PATH)
    manifest = _manifest(provider, replicate_id=replicate_id)
    binding = bind_lm_studio_execution_condition(
        environment=_environment(),
        target=target,
        artifact_verification=_verification(),
        provider=provider,
        manifest=manifest,
        configured_context_window=32768,
    )
    scenario = ActualModelScenario(
        scenario_id="lm-studio-persistence-identity",
        family="response_persona_continuity",
        turns=("hello",),
        version="1",
    )
    definition = ActualModelScenarioDefinition(
        scenario=scenario,
        proposal_labels=(),
        required_provider_capabilities=(),
    )
    scenario_set_revision = "sha256:" + "b" * 64
    plan = ActualModelScenarioExecutionPlan(
        plan_id=_stable_plan_id(
            scenario_set_version=manifest.scenario_set_version,
            scenario_set_revision=scenario_set_revision,
            character_fixture_id=manifest.character_fixture_id,
            character_fixture_revision=manifest.character_fixture_revision,
            definition=definition,
            manifest=manifest,
        ),
        scenario_set_version=manifest.scenario_set_version,
        scenario_set_revision=scenario_set_revision,
        character_fixture_id=manifest.character_fixture_id,
        character_fixture_revision=manifest.character_fixture_revision,
        definition=definition,
        manifest=manifest,
    )
    evidence = ActualModelEvidence(
        run_id=stable_actual_model_run_id(manifest=manifest, scenario=scenario),
        manifest=manifest,
        scenario=scenario,
        turns=(),
    )
    execution = ActualModelScenarioExecutionResult(
        execution_id=_stable_execution_id(plan=plan, run_id=evidence.run_id),
        plan=plan,
        evidence=evidence,
    )
    return ActualModelLMStudioExecutionResult(
        execution_id=lm_studio_subject._stable_lm_studio_execution_id(
            binding_id=binding.binding_id,
            scenario_execution_id=execution.execution_id,
        ),
        binding=binding,
        execution=execution,
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
                workspace_root="/must/not-be-created",
                provider=provider,
                manifest=manifest,
            )
        )

    assert provider.calls == 0


@pytest.mark.parametrize(
    ("identity_layer", "forge", "message"),
    (
        (
            "binding",
            lambda result: replace(
                result,
                binding=replace(result.binding, binding_id="amlsb-" + "f" * 64),
            ),
            "binding_id does not match LM Studio binding evidence",
        ),
        (
            "scenario_execution",
            lambda result: replace(
                result,
                execution=replace(result.execution, execution_id="amx-" + "f" * 64),
            ),
            "scenario execution_id does not match execution evidence",
        ),
        (
            "lm_studio_execution",
            lambda result: replace(result, execution_id="amlsx-" + "f" * 64),
            "execution_id does not match LM Studio execution evidence",
        ),
    ),
)
def test_lm_studio_writer_rejects_forged_identity_chain_before_writing(
    tmp_path: Path,
    identity_layer: str,
    forge,
    message: str,
) -> None:
    forged = forge(_execution_result())
    artifact_root = tmp_path / identity_layer

    with pytest.raises(ActualModelLMStudioBindingError, match=message):
        write_lm_studio_actual_model_execution_result(
            result=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()


def test_lm_studio_writer_rejects_forged_nested_plan_with_recomputed_ids(
    tmp_path: Path,
) -> None:
    result = _execution_result()
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
        execution_id=lm_studio_subject._stable_lm_studio_execution_id(
            binding_id=result.binding.binding_id,
            scenario_execution_id=forged_execution.execution_id,
        ),
    )
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelLMStudioBindingError,
        match="scenario execution is not citable",
    ):
        write_lm_studio_actual_model_execution_result(
            result=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()


def test_lm_studio_writer_rejects_execution_from_another_valid_binding_manifest(
    tmp_path: Path,
) -> None:
    first = _execution_result(replicate_id="0")
    second = _execution_result(replicate_id="1")
    mixed = replace(
        first,
        execution=second.execution,
        execution_id=lm_studio_subject._stable_lm_studio_execution_id(
            binding_id=first.binding.binding_id,
            scenario_execution_id=second.execution.execution_id,
        ),
    )
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelLMStudioBindingError,
        match="binding manifest does not match scenario execution plan",
    ):
        write_lm_studio_actual_model_execution_result(
            result=mixed,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()
