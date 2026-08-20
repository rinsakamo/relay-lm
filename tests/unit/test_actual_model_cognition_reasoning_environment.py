from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import relaylm.actual_model_host_runner as host_runner
from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ActualModelScenario,
    ExplicitBudgetConfiguration,
    stable_actual_model_run_id,
)
from relaylm.actual_model_host_runner import (
    ActualModelHostRunnerError,
    load_actual_model_host_condition,
    prepare_actual_model_host_run,
)
from relaylm.actual_model_reasoning import (
    ActualModelReasoningEnvironmentIdentity,
    ActualModelReasoningRunManifest,
)
from relaylm.actual_model_targets import (
    ActualModelArtifactVerification,
    load_actual_model_target,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_ID = "gemma-4-12b-it-q4-k-m-lmstudio-community-v1"
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json"
)


def _identity(setting: str = "off") -> ActualModelReasoningEnvironmentIdentity:
    return ActualModelReasoningEnvironmentIdentity(
        required_setting=setting,
        effective_setting=setting,
        allowed_options=("on", "off"),
        live_default=setting,
        control_source="lmstudio_model_default",
        control_mode="attested_default_without_per_request_override",
        serving_attestation_identity="lm-studio-serving-proof:sha256:" + "a" * 64,
    )


def _manifest_kwargs() -> dict[str, object]:
    return {
        "relaylm_commit": "a" * 40,
        "character_fixture_id": "fixture",
        "character_fixture_revision": "sha256:fixture",
        "provider_identity": "provider",
        "adapter_identity": "adapter",
        "model_artifact": "model@sha256:111",
        "tokenizer_identity": "tokenizer",
        "effective_context_window": 8192,
        "decoding_configuration": (),
        "structured_output_schema_version": "schema-v1",
        "scenario_set_version": "scenario-set-v1",
        "condition_id": "condition",
        "budgets": ExplicitBudgetConfiguration(),
    }


def _scenario() -> ActualModelScenario:
    return ActualModelScenario(
        scenario_id="reasoning-environment-v1",
        family="state_candidate_quality",
        version="1",
        turns=("hello",),
    )


def _condition_mapping(*, version: int = 5, setting: str = "off") -> dict[str, object]:
    mapping: dict[str, object] = {
        "format_version": version,
        "target_id": TARGET_ID,
        "relaylm_commit": "9" * 40,
        "lm_studio": {
            "version": "0.3.30",
            "build": "example-build-123",
            "deployment_identity": "local-lm-studio-primary",
            "base_url": "http://127.0.0.1:1234/v1",
            "request_model": "google/gemma-4-12b",
            "api_key_env": None,
        },
        "effective_context_window": 32768,
        "decoding": {"temperature": 0.2, "top_p": 0.95, "seed": 7},
        "supported_decoding_controls": ["temperature", "top_p", "seed"],
        "execution_path": "buffered",
        "continuity_runtime": None,
        "budgets": {
            "memory_max_chunks": 2,
            "memory_max_chars": 1024,
            "event_max_events": 4,
            "event_max_chars": 2048,
        },
        "cognition_execution": {"mode": "two_pass"},
        "condition_id": "cogp5-two-pass",
        "replicate_id": "0",
        "scenario_ids": ["response-persona-correction-v1"],
    }
    if version == 5:
        mapping["reasoning"] = {"required_setting": setting}
    return mapping


def _write_condition(tmp_path: Path, mapping: dict[str, object]) -> Path:
    path = tmp_path / "condition.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")
    return path


def _verification() -> ActualModelArtifactVerification:
    target = load_actual_model_target(TARGET_PATH)
    return ActualModelArtifactVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_size_bytes=target.artifact_size_bytes,
        artifact_sha256=target.artifact_sha256,
    )


def test_reasoning_manifest_extends_identity_without_changing_historical_manifest_shape() -> None:
    historical = ActualModelRunManifest(**_manifest_kwargs())
    assert "reasoning_environment" not in historical.to_mapping()

    explicit = ActualModelReasoningRunManifest(
        **_manifest_kwargs(),
        reasoning_environment=_identity(),
    )
    assert explicit.to_mapping()["reasoning_environment"]["effective_setting"] == "off"
    assert stable_actual_model_run_id(
        manifest=historical,
        scenario=_scenario(),
    ) != stable_actual_model_run_id(manifest=explicit, scenario=_scenario())


def test_reasoning_environment_canonicalizes_allowed_options() -> None:
    identity = _identity()
    assert identity.allowed_options == ("off", "on")
    assert identity.control_mode == "attested_default_without_per_request_override"


def test_v5_host_condition_requires_reasoning_environment_setting(tmp_path: Path) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    assert condition.format_version == 5
    assert condition.reasoning_required_setting == "off"
    assert condition.cognition_execution is not None
    assert condition.cognition_execution.mode == "two_pass"

    malformed = _condition_mapping()
    del malformed["reasoning"]
    with pytest.raises(ActualModelHostRunnerError, match="reasoning"):
        load_actual_model_host_condition(_write_condition(tmp_path, malformed))


def test_v5_preparation_attests_and_binds_reasoning_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(host_runner, "verify_actual_model_artifact", lambda **_: _verification())
    monkeypatch.setattr(
        host_runner,
        "_attest_lm_studio_reasoning_environment",
        lambda **_: _identity(),
    )

    prepared = prepare_actual_model_host_run(
        condition=condition,
        repo_root=REPO_ROOT,
        model_artifact_path=tmp_path / "model.gguf",
        serving_proof_path=tmp_path / "serving-proof.json",
    )
    try:
        assert isinstance(prepared.manifest, ActualModelReasoningRunManifest)
        assert prepared.manifest.reasoning_environment == _identity()
        assert prepared.manifest.to_mapping()["reasoning_environment"]["live_default"] == "off"
    finally:
        asyncio.run(prepared.provider.aclose())


def test_v5_preparation_rejects_missing_serving_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(host_runner, "verify_actual_model_artifact", lambda **_: _verification())

    with pytest.raises(ActualModelHostRunnerError, match="serving proof"):
        prepare_actual_model_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "model.gguf",
        )


def test_reasoning_attestation_uses_live_default_not_output_style(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    target = load_actual_model_target(TARGET_PATH)
    proof = SimpleNamespace(
        request_model=condition.request_model,
        model_key=condition.request_model,
        loaded_size_bytes=123456,
    )
    monkeypatch.setattr(host_runner, "build_lm_studio_counter_capabilities", lambda **_: {})
    monkeypatch.setattr(host_runner, "load_lm_studio_counter_proof", lambda _: proof)
    monkeypatch.setattr(
        host_runner,
        "_fetch_lm_studio_native_models",
        lambda **_: {
            "models": [
                {
                    "key": condition.request_model,
                    "type": "llm",
                    "size_bytes": 123456,
                    "quantization": {"name": target.quantization},
                    "loaded_instances": [{"id": condition.request_model}],
                    "capabilities": {
                        "reasoning": {
                            "allowed_options": ["on", "off"],
                            "default": "off",
                        }
                    },
                }
            ]
        },
    )
    proof_path = tmp_path / "proof.json"
    proof_path.write_text("{}", encoding="utf-8")

    identity = host_runner._attest_lm_studio_reasoning_environment(
        condition=condition,
        target=target,
        artifact_path=tmp_path / "model.gguf",
        proof_path=proof_path,
        api_key=None,
        node_path=None,
        sdk_root=None,
    )
    assert identity.effective_setting == "off"
    assert identity.live_default == "off"
    assert identity.serving_attestation_identity.startswith(
        "lm-studio-serving-proof:sha256:"
    )


def test_reasoning_attestation_rejects_live_default_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _condition_mapping(setting="off"))
    )
    target = load_actual_model_target(TARGET_PATH)
    proof = SimpleNamespace(
        request_model=condition.request_model,
        model_key=condition.request_model,
        loaded_size_bytes=123456,
    )
    monkeypatch.setattr(host_runner, "build_lm_studio_counter_capabilities", lambda **_: {})
    monkeypatch.setattr(host_runner, "load_lm_studio_counter_proof", lambda _: proof)
    monkeypatch.setattr(
        host_runner,
        "_fetch_lm_studio_native_models",
        lambda **_: {
            "models": [
                {
                    "key": condition.request_model,
                    "type": "llm",
                    "size_bytes": 123456,
                    "quantization": {"name": target.quantization},
                    "loaded_instances": [{"id": condition.request_model}],
                    "capabilities": {
                        "reasoning": {
                            "allowed_options": ["off", "on"],
                            "default": "on",
                        }
                    },
                }
            ]
        },
    )
    proof_path = tmp_path / "proof.json"
    proof_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ActualModelHostRunnerError, match="reasoning default"):
        host_runner._attest_lm_studio_reasoning_environment(
            condition=condition,
            target=target,
            artifact_path=tmp_path / "model.gguf",
            proof_path=proof_path,
            api_key=None,
            node_path=None,
            sdk_root=None,
        )
