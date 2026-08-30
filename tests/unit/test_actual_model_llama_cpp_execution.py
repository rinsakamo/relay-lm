from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.actual_model_llama_cpp_execution as llama_subject
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
from relaylm.actual_model_llama_cpp import LlamaCppRuntimeIdentity
from relaylm.actual_model_llama_cpp_execution import (
    ActualModelLlamaCppBindingError,
    ActualModelLlamaCppExecutionResult,
    bind_llama_cpp_execution_condition,
    llama_cpp_manifest_provider_identity,
    run_llama_cpp_actual_model_scenario_definition,
    write_llama_cpp_actual_model_execution_result,
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
from relaylm.providers.openai_compatible_identity import describe_openai_compatible_provider


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-q4-k-m-v1.json"
)
UPSTREAM_REVISION = "c841aeeb8bb2fe417038dadfa9b007cf1a9ef950"
BUILD_INFO = "b999-c841aeeb8bb2fe417038dadfa9b007cf1a9ef950"
MODEL_ALIAS = "gemma-local"
MODEL_PATH = "/models/gemma-4-12B-it-Q4_K_M.gguf"


class _Provider:
    def __init__(self, *, model: str = MODEL_ALIAS) -> None:
        self.model = model
        self.decoding_config = OpenAICompatibleDecodingConfig(
            temperature=0.0,
            top_p=1.0,
            seed=7,
        )
        self.decoding_capabilities = OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"temperature", "top_p", "seed"})
        )
        self.calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(response="ok")


def _target():
    return load_actual_model_target(TARGET_PATH)


def _runtime_identity(**overrides) -> LlamaCppRuntimeIdentity:
    target = _target()
    values = {
        "upstream_revision": UPSTREAM_REVISION,
        "build_info": BUILD_INFO,
        "model_alias": MODEL_ALIAS,
        "model_path": MODEL_PATH,
        "model_ftype": target.quantization,
        "artifact_sha256": target.artifact_sha256,
        "chat_template_sha256": "ab" * 32,
        "context_limit": 4096,
        "total_slots": 1,
        "context_shift_enabled": False,
    }
    values.update(overrides)
    return LlamaCppRuntimeIdentity(**values)


def _verification() -> ActualModelArtifactVerification:
    target = _target()
    return ActualModelArtifactVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_size_bytes=target.artifact_size_bytes,
        artifact_sha256=target.artifact_sha256,
    )


def _manifest(
    provider: _Provider,
    runtime_identity: LlamaCppRuntimeIdentity | None = None,
    *,
    replicate_id: str = "0",
) -> ActualModelRunManifest:
    target = _target()
    runtime = runtime_identity or _runtime_identity()
    identity = describe_openai_compatible_provider(provider)
    return ActualModelRunManifest(
        relaylm_commit="0" * 40,
        character_fixture_id="actual-model-foundation-v1",
        character_fixture_revision="sha256:fixture",
        provider_identity=llama_cpp_manifest_provider_identity(runtime),
        adapter_identity=identity.adapter_identity,
        model_artifact=target.model_artifact_identity,
        tokenizer_identity=target.tokenizer_identity,
        effective_context_window=runtime.context_limit,
        decoding_configuration=tuple(
            sorted(identity.effective_decoding_configuration.items())
        ),
        structured_output_schema_version="relaylm-cognitive-output-v1",
        scenario_set_version="actual-model-foundation-v2",
        condition_id="llama-cpp-reference-baseline",
        seed=7,
        provider_capabilities=identity.provider_capabilities,
        replicate_id=replicate_id,
    )


def _execution_result(*, replicate_id: str = "0") -> ActualModelLlamaCppExecutionResult:
    provider = _Provider()
    target = _target()
    runtime = _runtime_identity()
    manifest = _manifest(provider, runtime, replicate_id=replicate_id)
    binding = bind_llama_cpp_execution_condition(
        runtime_identity=runtime,
        target=target,
        artifact_verification=_verification(),
        provider=provider,
        manifest=manifest,
    )
    scenario = ActualModelScenario(
        scenario_id="llama-cpp-persistence-identity",
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
    return ActualModelLlamaCppExecutionResult(
        execution_id=llama_subject._stable_llama_cpp_execution_id(
            binding_id=binding.binding_id,
            scenario_execution_id=execution.execution_id,
        ),
        binding=binding,
        execution=execution,
    )


def test_manifest_provider_identity_is_exact_llama_cpp_runtime_identity() -> None:
    identity = llama_cpp_manifest_provider_identity(_runtime_identity())

    assert identity.startswith("actual-model-llama-cpp-v1:")
    assert '"implementation":"llama_cpp"' in identity
    assert f'"upstream_revision":"{UPSTREAM_REVISION}"' in identity
    assert f'"build_info":"{BUILD_INFO}"' in identity
    assert f'"model_alias":"{MODEL_ALIAS}"' in identity
    assert '"context_limit":4096' in identity
    assert '"context_shift_enabled":false' in identity
    assert '"chat_template_sha256":"' in identity


def test_binding_matches_runtime_target_provider_and_manifest() -> None:
    provider = _Provider()
    target = _target()
    runtime = _runtime_identity()
    manifest = _manifest(provider, runtime)

    binding = bind_llama_cpp_execution_condition(
        runtime_identity=runtime,
        target=target,
        artifact_verification=_verification(),
        provider=provider,
        manifest=manifest,
    )

    assert binding.binding_id.startswith("amlcb-")
    assert binding.runtime_identity == runtime
    assert binding.target_id == target.target_id
    assert binding.target_revision == target.revision
    assert binding.provider_identity.model == MODEL_ALIAS
    assert binding.manifest == manifest
    assert binding.runtime_identity.chat_template_sha256 == "ab" * 32


def test_binding_rejects_runtime_artifact_mismatch() -> None:
    provider = _Provider()
    runtime = _runtime_identity(artifact_sha256="cd" * 32)

    with pytest.raises(ActualModelLlamaCppBindingError, match="artifact_sha256"):
        bind_llama_cpp_execution_condition(
            runtime_identity=runtime,
            target=_target(),
            artifact_verification=_verification(),
            provider=provider,
            manifest=_manifest(provider, runtime),
        )


def test_binding_rejects_provider_model_alias_mismatch() -> None:
    provider = _Provider(model="another-model")
    runtime = _runtime_identity()

    with pytest.raises(ActualModelLlamaCppBindingError, match="model alias"):
        bind_llama_cpp_execution_condition(
            runtime_identity=runtime,
            target=_target(),
            artifact_verification=_verification(),
            provider=provider,
            manifest=_manifest(provider, runtime),
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("provider_identity", "not-llama-cpp", "provider_identity"),
        ("adapter_identity", "wrong-adapter", "adapter_identity"),
        ("model_artifact", "wrong-model", "model_artifact"),
        ("tokenizer_identity", "wrong-tokenizer", "tokenizer_identity"),
        ("effective_context_window", 2048, "effective_context_window"),
        ("decoding_configuration", (("temperature", 0.0),), "decoding_configuration"),
        ("seed", 8, "seed"),
        ("provider_capabilities", ("state_candidates",), "provider_capabilities"),
    ),
)
def test_binding_rejects_manifest_metadata_that_condition_did_not_apply(
    field: str,
    value: object,
    message: str,
) -> None:
    provider = _Provider()
    runtime = _runtime_identity()
    manifest = replace(_manifest(provider, runtime), **{field: value})

    with pytest.raises(ActualModelLlamaCppBindingError, match=message):
        bind_llama_cpp_execution_condition(
            runtime_identity=runtime,
            target=_target(),
            artifact_verification=_verification(),
            provider=provider,
            manifest=manifest,
        )


def test_wrapper_fails_before_generation_on_binding_drift() -> None:
    provider = _Provider()
    runtime = _runtime_identity()
    manifest = replace(_manifest(provider, runtime), seed=8)

    with pytest.raises(ActualModelLlamaCppBindingError, match="seed"):
        asyncio.run(
            run_llama_cpp_actual_model_scenario_definition(
                runtime_identity=runtime,
                target=_target(),
                artifact_verification=_verification(),
                scenario_set=None,  # type: ignore[arg-type]
                scenario_id="not-reached",
                fixture_root="/does/not/exist",
                workspace_root="/must/not-be-created",
                provider=provider,
                manifest=manifest,
            )
        )

    assert provider.calls == 0


def test_writer_rejects_forged_binding_identity_before_writing(tmp_path: Path) -> None:
    result = _execution_result()
    forged = replace(
        result,
        binding=replace(result.binding, binding_id="amlcb-" + "f" * 64),
    )
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelLlamaCppBindingError,
        match="binding_id does not match llama.cpp binding evidence",
    ):
        write_llama_cpp_actual_model_execution_result(
            result=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()


def test_writer_rejects_forged_nested_plan_before_writing(tmp_path: Path) -> None:
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
        execution_id=llama_subject._stable_llama_cpp_execution_id(
            binding_id=result.binding.binding_id,
            scenario_execution_id=forged_execution.execution_id,
        ),
    )
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(
        ActualModelLlamaCppBindingError,
        match="scenario execution is not citable",
    ):
        write_llama_cpp_actual_model_execution_result(
            result=forged,
            artifact_root=artifact_root,
        )

    assert not artifact_root.exists()
