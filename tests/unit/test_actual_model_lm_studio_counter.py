from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import relaylm.actual_model_lm_studio_counter as counter_module
from relaylm.actual_model_host_runner import (
    ActualModelHostCondition,
    HostLegacyBudgetCondition,
)
from relaylm.actual_model_lm_studio_counter import (
    LM_STUDIO_GEMMA4_COUNTER_CAPABILITY,
    LM_STUDIO_MODEL_BINDING_METHOD,
    LM_STUDIO_PROMPT_PARITY_METHOD,
    LMStudioCounterError,
    build_lm_studio_counter_capabilities,
    load_lm_studio_counter_proof,
)
from relaylm.actual_model_targets import load_actual_model_target
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json"
)


def _proof_mapping(path: Path) -> dict[str, object]:
    target = load_actual_model_target(TARGET_PATH)
    return {
        "format_version": 1,
        "attestation": "exact",
        "capability": LM_STUDIO_GEMMA4_COUNTER_CAPABILITY,
        "implementation": "lmstudio-js-loaded-model-counter",
        "version": "1",
        "relaylm_commit": "a" * 40,
        "target_id": target.target_id,
        "request_model": "google/gemma-4-12b",
        "lm_studio": {
            "version": "0.4.21.0",
            "build": "0.4.21+2",
            "deployment_identity": "local-proof-test",
        },
        "loaded_model": {
            "model_key": (
                "lmstudio-community/gemma-4-12B-it-GGUF/"
                "gemma-4-12B-it-Q4_K_M.gguf"
            ),
            "path": str(path),
            "quantization": target.quantization,
            "size_bytes": target.artifact_size_bytes,
            "sha256": target.artifact_sha256,
            "instance_reference_sha256": "b" * 64,
        },
        "sdk": {
            "package": "@lmstudio/sdk",
            "version": "1.5.0",
            "prompt_template_method": (
                "loaded-model.applyPromptTemplate->countTokens"
            ),
            "tokenizer_method": "loaded-model.countTokens",
        },
        "probe_matrix": [
            {
                "probe_id": probe_id,
                "request_sha256": f"{index:064x}",
                "sdk_prompt_tokens": 100 + index,
                "server_prompt_tokens": 100 + index,
                "equal": True,
            }
            for index, probe_id in enumerate(
                sorted(counter_module.LM_STUDIO_REQUIRED_PROBE_IDS),
                start=1,
            )
        ],
        "model_binding": {
            "method": LM_STUDIO_MODEL_BINDING_METHOD,
            "verdict": "same-loaded-instance",
        },
        "prompt_template_parity": {
            "method": LM_STUDIO_PROMPT_PARITY_METHOD,
            "verdict": "all-required-probes-equal",
        },
        "structured_output": {
            "comparison": "response_format-json-schema-vs-messages-only",
            "schema_token_delta": 0,
            "verdict": "no-token-bearing-prompt-delta",
        },
        "framing_accounting": {
            "method": "empty-user-message-baseline-v1",
            "verdict": "reproducible",
        },
    }


def _condition() -> ActualModelHostCondition:
    return ActualModelHostCondition(
        target_id="gemma-4-12b-it-q4-k-m-lmstudio-community-v1",
        relaylm_commit="a" * 40,
        lm_studio_version="0.4.21.0",
        lm_studio_build="0.4.21+2",
        deployment_identity="local-proof-test",
        base_url="http://127.0.0.1:1234/v1",
        request_model="google/gemma-4-12b",
        api_key_env=None,
        effective_context_window=8192,
        temperature=0.2,
        top_p=0.95,
        seed=7,
        supported_decoding_controls=("temperature", "top_p", "seed"),
        execution_path="buffered",
        continuity=None,
        budgets=HostLegacyBudgetCondition(
            memory_max_chunks=None,
            memory_max_chars=None,
            event_max_events=None,
            event_max_chars=None,
        ),
        condition_id="proof-test",
        replicate_id="0",
        scenario_ids=("response-persona-correction-v1",),
        cognitive_budget=None,
        format_version=2,
    )


def test_counter_proof_requires_all_evidence_probe_categories(tmp_path: Path) -> None:
    mapping = _proof_mapping(tmp_path / "gemma.gguf")
    probes = list(mapping["probe_matrix"])  # type: ignore[arg-type]
    assert isinstance(probes[-1], dict)
    probes[-1] = {**probes[-1], "probe_id": "unclassified-input"}
    mapping["probe_matrix"] = probes
    path = tmp_path / "counter-proof.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")

    with pytest.raises(LMStudioCounterError, match="missing required probes"):
        load_lm_studio_counter_proof(path)


def test_exact_capability_is_host_bound_and_secret_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_path = tmp_path / "gemma-4-12B-it-Q4_K_M.gguf"
    mapping = _proof_mapping(model_path)
    proof_path = tmp_path / "counter-proof.json"
    proof_path.write_text(json.dumps(mapping), encoding="utf-8")

    class FakeTransport:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        def attest(self) -> dict[str, object]:
            loaded = mapping["loaded_model"]
            assert isinstance(loaded, dict)
            return {
                "model_key": loaded["model_key"],
                "path": loaded["path"],
                "size_bytes": loaded["size_bytes"],
                "quantization": loaded["quantization"],
                "sdk_version": "1.5.0",
                "instance_reference_sha256": loaded["instance_reference_sha256"],
            }

        def count_input(self, model_input: object) -> object:
            raise AssertionError("counting is not part of this construction test")

    monkeypatch.setattr(counter_module, "_LMStudioSdkTransport", FakeTransport)
    target = load_actual_model_target(TARGET_PATH)
    condition = _condition()
    capabilities = build_lm_studio_counter_capabilities(
        condition=condition,
        target=target,
        artifact_path=model_path,
        proof_path=proof_path,
    )

    capability = capabilities[LM_STUDIO_GEMMA4_COUNTER_CAPABILITY]
    assert capability.exact_behavior_demonstrated is True
    assert capability.conservative_bound_demonstrated is False
    provider = SimpleNamespace(
        model="google/gemma-4-12b",
        decoding_config=OpenAICompatibleDecodingConfig(
            temperature=0.2,
            top_p=0.95,
            seed=7,
        ),
    )
    counter = capability.factory(condition, provider)
    identity = counter.evidence_identity
    assert identity is not None
    serialized = json.dumps(identity.to_mapping())
    assert "base_url" not in serialized
    lowered = serialized.casefold()
    for sensitive_key in ("api_key", "password", "passkey", "secret", "base_url"):
        assert f'"{sensitive_key}"' not in lowered


def test_missing_proof_fails_before_optional_sdk_resolution(tmp_path: Path) -> None:
    target = load_actual_model_target(TARGET_PATH)
    with pytest.raises(LMStudioCounterError, match="exact LM Studio counter proof"):
        build_lm_studio_counter_capabilities(
            condition=_condition(),
            target=target,
            artifact_path=tmp_path / "gemma.gguf",
            proof_path=None,
        )
