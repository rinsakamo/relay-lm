from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

import relaylm.actual_model_host_runner as host_runner
from relaylm.actual_model_host_runner import (
    ActualModelHostRunnerError,
    load_actual_model_host_condition,
    prepare_actual_model_host_run,
)
from relaylm.actual_model_targets import (
    ActualModelArtifactVerification,
    load_actual_model_target,
)
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_ID = "gemma-4-12b-it-q4-k-m-lmstudio-community-v1"
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json"
)


def _condition_mapping(*, mode: str) -> dict[str, object]:
    return {
        "format_version": 4,
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
        "decoding": {
            "temperature": 0.2,
            "top_p": 0.95,
            "seed": 7,
        },
        "supported_decoding_controls": ["temperature", "top_p", "seed"],
        "execution_path": "buffered",
        "continuity_runtime": None,
        "budgets": {
            "memory_max_chunks": 2,
            "memory_max_chars": 1024,
            "event_max_events": 4,
            "event_max_chars": 2048,
        },
        "cognition_execution": {"mode": mode},
        "condition_id": f"cogp5-{mode}",
        "replicate_id": "0",
        "scenario_ids": ["response-persona-correction-v1"],
    }


def _write_condition(tmp_path: Path, mapping: dict[str, object]) -> Path:
    path = tmp_path / "condition.json"
    path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    return path


def _verification() -> ActualModelArtifactVerification:
    target = load_actual_model_target(TARGET_PATH)
    return ActualModelArtifactVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_size_bytes=target.artifact_size_bytes,
        artifact_sha256=target.artifact_sha256,
    )


@pytest.mark.parametrize("mode", ["single_pass", "two_pass", "shadow_two_pass"])
def test_v4_host_condition_parses_explicit_cognition_execution_identity(
    tmp_path: Path,
    mode: str,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _condition_mapping(mode=mode))
    )

    assert condition.format_version == 4
    assert condition.cognition_execution is not None
    assert condition.cognition_execution.mode == mode
    assert condition.cognition_execution.execution_path == "buffered"
    assert condition.cognitive_budget is None


def test_v4_host_condition_rejects_unresolved_auto_topology(tmp_path: Path) -> None:
    with pytest.raises(ActualModelHostRunnerError, match="auto"):
        load_actual_model_host_condition(
            _write_condition(tmp_path, _condition_mapping(mode="auto"))
        )


@pytest.mark.parametrize("mode", ["two_pass", "shadow_two_pass"])
def test_v4_preparation_binds_topology_and_two_pass_capable_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _condition_mapping(mode=mode))
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )

    prepared = prepare_actual_model_host_run(
        condition=condition,
        repo_root=REPO_ROOT,
        model_artifact_path=tmp_path / "not-read-because-verifier-is-patched.gguf",
    )
    try:
        assert isinstance(prepared.provider, OpenAICompatibleTwoPassProvider)
        assert prepared.manifest.cognition_execution == condition.cognition_execution
        mapping = prepared.manifest.to_mapping()
        assert mapping["cognition_execution"]["mode"] == mode
        assert mapping["cognition_execution"]["execution_path"] == "buffered"
    finally:
        asyncio.run(prepared.provider.aclose())


def test_v4_single_pass_uses_canonical_provider_with_explicit_topology_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _condition_mapping(mode="single_pass"))
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )

    prepared = prepare_actual_model_host_run(
        condition=condition,
        repo_root=REPO_ROOT,
        model_artifact_path=tmp_path / "not-read-because-verifier-is-patched.gguf",
    )
    try:
        assert type(prepared.provider) is OpenAICompatibleProvider
        assert prepared.manifest.cognition_execution is not None
        assert prepared.manifest.cognition_execution.mode == "single_pass"
    finally:
        asyncio.run(prepared.provider.aclose())
