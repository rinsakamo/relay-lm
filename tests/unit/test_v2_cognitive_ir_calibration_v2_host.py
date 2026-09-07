from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path

import pytest

from relaylm.v2_cognitive_ir_calibration_v2 import (
    CALIBRATION_V2_CLAIM_STATUS,
    CALIBRATION_V2_PROBES,
    CALIBRATION_V2_REGIMES,
    CALIBRATION_V2_SEEDS,
    generate_calibration_v2_case,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools import v2_cognitive_ir_calibration_v2_host as host


def _rule_mapping(case) -> dict[str, object]:
    return {
        "permutation": list(case.rule.permutation),
        "offsets": list(case.rule.offsets),
        "modulus": case.rule.modulus,
    }


class QueueClient:
    def __init__(self, *, fail_first: bool = False, verified_reasoning_off: bool = True) -> None:
        self.provider_attempts = 0
        self.provider_completions = 0
        self.fail_first = fail_first
        self.verified_reasoning_off = verified_reasoning_off

    @property
    def transport_identity(self) -> dict[str, object]:
        value: dict[str, object] = {
            "api": "openai-chat-completions-json-schema-v1",
            "model": "google/gemma-4-12b",
            "timeout_seconds": 300.0,
            "max_tokens": 128,
            "temperature": 0.0,
            "seed": None,
            "structured_output": True,
        }
        if self.verified_reasoning_off:
            value.update(
                {
                    "reasoning_mode": "off",
                    "reasoning_verification": (
                        "usage.completion_tokens_details.reasoning_tokens==0"
                    ),
                }
            )
        return value

    def complete_structured(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> ExperimentCompletion:
        del messages, schema_name, schema
        call_index = self.provider_completions
        cell_index = call_index // len(CALIBRATION_V2_PROBES)
        regime_index = cell_index // len(CALIBRATION_V2_SEEDS)
        seed_index = cell_index % len(CALIBRATION_V2_SEEDS)
        probe_index = call_index % len(CALIBRATION_V2_PROBES)
        case = generate_calibration_v2_case(
            seed=CALIBRATION_V2_SEEDS[seed_index],
            regime=CALIBRATION_V2_REGIMES[regime_index],
        )

        self.provider_attempts += 1
        if self.fail_first and self.provider_attempts == 1:
            raise StructureProposalError("synthetic provider failure")
        if probe_index == 0:
            content = json.dumps({"answer": list(case.expected_output)}, separators=(",", ":"))
        elif probe_index == 1:
            content = json.dumps(_rule_mapping(case), separators=(",", ":"))
        else:
            payload = _rule_mapping(case)
            payload["answer"] = list(case.expected_output)
            content = json.dumps(payload, separators=(",", ":"))
        self.provider_completions += 1
        return ExperimentCompletion(
            content=content,
            input_tokens=10,
            output_tokens=5,
            response_id=f"resp-{self.provider_completions}",
        )


def _binding() -> dict[str, object]:
    return {
        "model": "google/gemma-4-12b",
        "model_instance_id": "google/gemma-4-12b",
        "context_length": 8192,
        "runtime": {
            "architecture": "gemma4",
            "format": "gguf",
            "quantization": {"name": "Q4_K_M", "bits_per_weight": 4},
            "selected_variant": "google/gemma-4-12b@q4_k_m",
            "reasoning_capability": {"allowed_options": ["off", "on"], "default": "on"},
        },
    }


def _identity(client: QueueClient) -> dict[str, object]:
    binding = _binding()
    return {
        "repository": {"commit": "commit", "tree": "tree", "clean_required": True},
        **binding,
        "transport": dict(client.transport_identity),
        "retry_policy": {"automatic_retry": False, "semantic_retry": False},
        "live_binding_fields": ["model", "model_instance_id", "context_length", "runtime"],
        "call_plan": list(host.calibration_v2_call_plan()),
    }


def _patch_repo(monkeypatch) -> None:
    monkeypatch.setattr(
        host,
        "probe_calibration_git_repository",
        lambda root: host.CalibrationRepositoryState(commit="commit", tree="tree", clean=True),
    )


def test_calibration_v2_host_completes_exact_frozen_matrix(tmp_path: Path, monkeypatch) -> None:
    _patch_repo(monkeypatch)
    client = QueueClient()
    artifact = tmp_path / "artifact"
    repository = tmp_path / "repo"
    repository.mkdir()

    result = host.run_calibration_v2_host(
        artifact_root=artifact,
        identity=_identity(client),
        repository_root=repository,
        live_binding_probe=_binding,
        client=client,
    )

    assert result.status == "COMPLETED"
    assert result.claim_status == CALIBRATION_V2_CLAIM_STATUS
    assert result.citable is False
    assert result.provider_attempts == result.provider_completions == 72
    assert result.selected_regime is None

    durable = json.loads((artifact / "calibration-v2-result.json").read_text())
    assert durable["provider_attempts"] == durable["provider_completions"] == 72
    assert durable["selected_regime"] is None
    assert len(durable["cells"]) == 24
    evidence = (artifact / "request-evidence.jsonl").read_text().splitlines()
    assert len(evidence) == 72
    assert json.loads(evidence[0])["question_id"] == host.calibration_v2_call_plan()[0]
    manifest = json.loads((artifact / "run-manifest.json").read_text())
    assert manifest["expected_provider_calls"] == 72
    assert manifest["claim_status"] == CALIBRATION_V2_CLAIM_STATUS


def test_calibration_v2_host_binding_drift_fails_before_first_provider_attempt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_repo(monkeypatch)
    client = QueueClient()
    artifact = tmp_path / "artifact"
    repository = tmp_path / "repo"
    repository.mkdir()
    calls = 0

    def probe() -> dict[str, object]:
        nonlocal calls
        calls += 1
        value = _binding()
        if calls >= 2:
            value["context_length"] = 4096
        return value

    with pytest.raises(host.CalibrationV2HostError, match="context_length changed"):
        host.run_calibration_v2_host(
            artifact_root=artifact,
            identity=_identity(client),
            repository_root=repository,
            live_binding_probe=probe,
            client=client,
        )

    state = json.loads((artifact / "run-state.json").read_text())
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 0
    assert state["provider_completions"] == 0


def test_calibration_v2_host_counts_failed_first_provider_attempt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_repo(monkeypatch)
    client = QueueClient(fail_first=True)
    artifact = tmp_path / "artifact"
    repository = tmp_path / "repo"
    repository.mkdir()

    with pytest.raises(StructureProposalError, match="synthetic provider failure"):
        host.run_calibration_v2_host(
            artifact_root=artifact,
            identity=_identity(client),
            repository_root=repository,
            live_binding_probe=_binding,
            client=client,
        )

    state = json.loads((artifact / "run-state.json").read_text())
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 1
    assert state["provider_completions"] == 0
    assert state["next_call"] == 0


def test_calibration_v2_host_rejects_unverified_reasoning_transport(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_repo(monkeypatch)
    client = QueueClient(verified_reasoning_off=False)
    repository = tmp_path / "repo"
    repository.mkdir()

    with pytest.raises(host.CalibrationV2HostError, match="reasoning mode off"):
        host.run_calibration_v2_host(
            artifact_root=tmp_path / "artifact",
            identity=_identity(client),
            repository_root=repository,
            live_binding_probe=_binding,
            client=client,
        )
    assert client.provider_attempts == 0


def test_calibration_v2_call_plan_is_frozen_72_calls() -> None:
    plan = host.calibration_v2_call_plan()
    assert len(plan) == 72
    assert len(set(plan)) == 72
