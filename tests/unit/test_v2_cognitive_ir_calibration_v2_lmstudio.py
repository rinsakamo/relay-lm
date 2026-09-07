from __future__ import annotations

from pathlib import Path

import pytest

from tools import v2_cognitive_ir_calibration_v2_lmstudio as entry
from tools.v2_cognitive_ir_calibration_host import CalibrationRepositoryState
from tools.v2_cognitive_ir_calibration_v2_host import (
    CalibrationV2HostError,
    CalibrationV2HostResult,
)


class FakeClient:
    def __init__(self, *, model: str) -> None:
        self.provider_attempts = 0
        self.provider_completions = 0
        self.model = model
        self.closed = False

    @property
    def transport_identity(self) -> dict[str, object]:
        return {
            "api": "openai-chat-completions-json-schema-v1",
            "model": self.model,
            "timeout_seconds": 300.0,
            "max_tokens": 128,
            "temperature": 0.0,
            "seed": None,
            "structured_output": True,
            "reasoning_mode": "off",
            "reasoning_verification": "usage.completion_tokens_details.reasoning_tokens==0",
        }

    def close(self) -> None:
        self.closed = True


def _binding(model: str = "google/gemma-4-12b") -> dict[str, object]:
    return {
        "model": model,
        "model_instance_id": "instance-1",
        "context_length": 8192,
        "runtime": {
            "architecture": "gemma4",
            "format": "gguf",
            "quantization": {"name": "Q4_K_M"},
            "selected_variant": f"{model}@q4_k_m",
            "reasoning_capability": {"allowed_options": ["off", "on"], "default": "on"},
        },
    }


def test_lmstudio_entrypoint_constructs_one_consistent_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = FakeClient(model="google/gemma-4-12b")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        entry,
        "probe_calibration_git_repository",
        lambda root: CalibrationRepositoryState(commit="commit", tree="tree", clean=True),
    )
    monkeypatch.setattr(
        entry,
        "build_reasoning_off_lmstudio_calibration_v2_client",
        lambda **kwargs: client,
    )
    monkeypatch.setattr(
        entry,
        "probe_lmstudio_native_calibration_binding",
        lambda **kwargs: _binding(),
    )

    def fake_run(**kwargs):
        captured.update(kwargs)
        return CalibrationV2HostResult(
            run_id="calv2-test",
            identity_fingerprint="sha256:test",
            status="COMPLETED",
            claim_status="NON_CITABLE_S2_CALIBRATION_V2",
            citable=False,
            provider_attempts=72,
            provider_completions=72,
            selected_regime=None,
            total_input_tokens=1,
            total_output_tokens=1,
        )

    monkeypatch.setattr(entry, "run_calibration_v2_host", fake_run)

    result = entry.run_lmstudio_calibration_v2_transaction(
        base_url="http://lmstudio:1234",
        model="google/gemma-4-12b",
        repository_root=tmp_path / "repo",
        artifact_root=tmp_path / "artifact",
    )

    identity = captured["identity"]
    assert identity["model"] == identity["transport"]["model"] == "google/gemma-4-12b"
    assert identity["repository"] == {
        "commit": "commit",
        "tree": "tree",
        "clean_required": True,
    }
    assert len(identity["call_plan"]) == 72
    assert result.status == "COMPLETED"
    assert client.closed is True


def test_lmstudio_entrypoint_rejects_native_transport_model_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = FakeClient(model="google/gemma-4-12b")
    monkeypatch.setattr(
        entry,
        "probe_calibration_git_repository",
        lambda root: CalibrationRepositoryState(commit="commit", tree="tree", clean=True),
    )
    monkeypatch.setattr(
        entry,
        "build_reasoning_off_lmstudio_calibration_v2_client",
        lambda **kwargs: client,
    )
    monkeypatch.setattr(
        entry,
        "probe_lmstudio_native_calibration_binding",
        lambda **kwargs: _binding("other/model"),
    )

    with pytest.raises(CalibrationV2HostError, match="does not match"):
        entry.run_lmstudio_calibration_v2_transaction(
            base_url="http://lmstudio:1234",
            model="google/gemma-4-12b",
            repository_root=tmp_path / "repo",
            artifact_root=tmp_path / "artifact",
        )
    assert client.closed is True
