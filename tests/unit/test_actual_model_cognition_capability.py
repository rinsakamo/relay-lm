from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.actual_model_cognition_capability import (
    ActualModelCognitionCapabilityArtifactError,
    build_unsupported_cognition_condition_evidence,
    write_unsupported_cognition_condition_evidence,
)
from relaylm.actual_model_targets import load_actual_model_target
from relaylm.cognition_execution import (
    CognitionPassRequest,
    CognitionReasoningMode,
)
from relaylm.providers.openai_compatible_cognition import (
    OpenAICompatibleCognitionCapabilityFacts,
)
from relaylm.providers.openai_compatible_identity import (
    OPENAI_COMPATIBLE_ADAPTER_IDENTITY,
    OPENAI_COMPATIBLE_STRUCTURED_OUTPUT_SCHEMA_NAME,
    OpenAICompatibleProviderCapabilities,
    OpenAICompatibleProviderIdentity,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json"
)


def _provider_identity() -> OpenAICompatibleProviderIdentity:
    capabilities = OpenAICompatibleProviderCapabilities(
        structured_semantic_channels=(
            "response",
            "state_candidates",
            "continuity_candidates",
        ),
        supported_decoding_controls=("seed", "temperature", "top_p"),
        buffered=True,
        streaming=True,
        seed_control_supported=True,
    )
    return OpenAICompatibleProviderIdentity(
        adapter_identity=OPENAI_COMPATIBLE_ADAPTER_IDENTITY,
        model="google/gemma-4-12b",
        structured_output_schema_name=OPENAI_COMPATIBLE_STRUCTURED_OUTPUT_SCHEMA_NAME,
        decoding_configuration=(("seed", 7), ("temperature", 0.2), ("top_p", 0.95)),
        capabilities=capabilities,
    )


def _unsupported_facts() -> OpenAICompatibleCognitionCapabilityFacts:
    return OpenAICompatibleCognitionCapabilityFacts(
        structured_output=True,
        streaming=True,
        reasoning_modes=(),
        bounded_reasoning_budget=False,
        per_pass_decoding_controls=("temperature", "top_p"),
    )


def _supported_bounded_facts() -> OpenAICompatibleCognitionCapabilityFacts:
    return OpenAICompatibleCognitionCapabilityFacts(
        structured_output=True,
        streaming=True,
        reasoning_modes=("bounded",),
        bounded_reasoning_budget=True,
        per_pass_decoding_controls=("temperature", "top_p"),
    )


def _request() -> CognitionPassRequest:
    return CognitionPassRequest(reasoning_mode=CognitionReasoningMode.BOUNDED)


def _build():
    return build_unsupported_cognition_condition_evidence(
        relaylm_commit="1" * 40,
        condition_id="cogp5-c-bounded-pass2",
        target=load_actual_model_target(TARGET_PATH),
        provider_identity=_provider_identity(),
        provider_cognition_facts=_unsupported_facts(),
        pass_name="pass2",
        request=_request(),
    )


def test_c_condition_is_explicit_unsupported_without_generation() -> None:
    evidence = _build()
    mapping = evidence.to_mapping()

    assert mapping["condition_status"] == "unsupported"
    assert mapping["generation_executed"] is False
    assert mapping["pass"] == "pass2"
    assert mapping["request"] == {
        "reasoning_mode": "bounded",
        "reasoning_budget": None,
        "temperature": None,
        "top_p": None,
        "max_output_tokens": None,
    }
    assert mapping["resolution"]["reasoning_mode"] == {
        "status": "unsupported",
        "value": "bounded",
    }
    assert mapping["resolution"]["reasoning_budget"] == {
        "status": "omitted",
        "value": None,
    }
    assert mapping["unsupported_fields"] == ["reasoning_mode"]
    assert mapping["model_quality"] is None
    assert mapping["score"] is None
    assert "response" not in mapping
    assert "raw_model" not in mapping
    assert "run_id" not in mapping


def test_evidence_binds_target_provider_facts_and_cogp_normalization() -> None:
    evidence = _build()
    mapping = evidence.to_mapping()

    target = load_actual_model_target(TARGET_PATH)
    assert mapping["relaylm_commit"] == "1" * 40
    assert mapping["target"] == {
        "target_id": target.target_id,
        "target_revision": target.revision,
        "model_artifact": target.model_artifact_identity,
    }
    assert mapping["provider_identity"] == _provider_identity().to_mapping()
    assert mapping["provider_cognition_facts"] == _unsupported_facts().to_mapping()
    assert mapping["normalized_cognition_capabilities"] == {
        "structured_output": True,
        "streaming": True,
        "reasoning_modes": [],
        "bounded_reasoning_budget": False,
        "decoding_controls": ["temperature", "top_p"],
    }


def test_evidence_id_is_content_addressed_and_deterministic() -> None:
    first = _build()
    second = _build()

    assert first.evidence_id == second.evidence_id
    assert first.evidence_id.startswith("cogp-capability-")
    assert len(first.evidence_id.removeprefix("cogp-capability-")) == 64


def test_unsupported_builder_refuses_fully_supported_request() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        build_unsupported_cognition_condition_evidence(
            relaylm_commit="1" * 40,
            condition_id="not-unsupported",
            target=load_actual_model_target(TARGET_PATH),
            provider_identity=_provider_identity(),
            provider_cognition_facts=_supported_bounded_facts(),
            pass_name="pass2",
            request=_request(),
        )


def test_unsupported_builder_rejects_invalid_commit_and_pass() -> None:
    with pytest.raises(ValueError, match="relaylm_commit"):
        build_unsupported_cognition_condition_evidence(
            relaylm_commit="not-a-commit",
            condition_id="cogp5-c",
            target=load_actual_model_target(TARGET_PATH),
            provider_identity=_provider_identity(),
            provider_cognition_facts=_unsupported_facts(),
            pass_name="pass2",
            request=_request(),
        )
    with pytest.raises(ValueError, match="pass_name"):
        build_unsupported_cognition_condition_evidence(
            relaylm_commit="1" * 40,
            condition_id="cogp5-c",
            target=load_actual_model_target(TARGET_PATH),
            provider_identity=_provider_identity(),
            provider_cognition_facts=_unsupported_facts(),
            pass_name="",
            request=_request(),
        )


def test_writer_is_idempotent_and_rejects_conflicting_existing_bytes(tmp_path: Path) -> None:
    evidence = _build()
    path = write_unsupported_cognition_condition_evidence(
        evidence=evidence,
        artifact_root=tmp_path,
    )
    assert write_unsupported_cognition_condition_evidence(
        evidence=evidence,
        artifact_root=tmp_path,
    ) == path
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == evidence.to_mapping()

    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ActualModelCognitionCapabilityArtifactError, match="conflict"):
        write_unsupported_cognition_condition_evidence(
            evidence=evidence,
            artifact_root=tmp_path,
        )
