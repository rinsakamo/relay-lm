from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path

import httpx
import pytest

from relaylm.v2_cognitive_ir_calibration import (
    CALIBRATION_CLAIM_STATUS,
    CALIBRATION_DIFFICULTIES,
    CALIBRATION_PROBES,
    CALIBRATION_SEEDS,
    generate_calibration_case,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools import v2_cognitive_ir_calibration_host as host


def _rule_mapping(case) -> dict[str, object]:
    return {
        "permutation": list(case.rule.permutation),
        "offsets": list(case.rule.offsets),
        "modulus": case.rule.modulus,
    }


class QueueClient:
    def __init__(self, *, fail_first: bool = False) -> None:
        self.provider_attempts = 0
        self.provider_completions = 0
        self.fail_first = fail_first

    @property
    def transport_identity(self) -> dict[str, object]:
        return {
            "api": "openai-chat-completions-json-schema-v1",
            "model": "google/gemma-4-12b",
            "timeout_seconds": 300.0,
            "max_tokens": 128,
            "temperature": 0.0,
            "seed": None,
            "structured_output": True,
        }

    def complete_structured(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> ExperimentCompletion:
        del schema_name, schema
        self.provider_attempts += 1
        if self.fail_first and self.provider_attempts == 1:
            raise StructureProposalError("synthetic provider failure")
        user = json.loads(messages[1]["content"])
        if "rule" in user and "query" in user:
            rule = user["rule"]
            query = user["query"]
            answer = [
                (query[rule["permutation"][index]] + rule["offsets"][index]) % rule["modulus"]
                for index in range(4)
            ]
            content = json.dumps({"answer": answer}, separators=(",", ":"))
        elif "examples" in user and "query" not in user:
            call_index = self.provider_completions
            cell_index = call_index // 3
            difficulty_index = cell_index // len(CALIBRATION_SEEDS)
            seed_index = cell_index % len(CALIBRATION_SEEDS)
            case = generate_calibration_case(
                seed=CALIBRATION_SEEDS[seed_index],
                difficulty=CALIBRATION_DIFFICULTIES[difficulty_index],
            )
            content = json.dumps(_rule_mapping(case), separators=(",", ":"))
        else:
            call_index = self.provider_completions
            cell_index = call_index // 3
            difficulty_index = cell_index // len(CALIBRATION_SEEDS)
            seed_index = cell_index % len(CALIBRATION_SEEDS)
            case = generate_calibration_case(
                seed=CALIBRATION_SEEDS[seed_index],
                difficulty=CALIBRATION_DIFFICULTIES[difficulty_index],
            )
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
        "repository": {
            "commit": "commit",
            "tree": "tree",
            "clean_required": True,
        },
        **binding,
        "transport": dict(client.transport_identity),
        "retry_policy": {"automatic_retry": False, "semantic_retry": False},
        "live_binding_fields": ["model", "model_instance_id", "context_length", "runtime"],
        "call_plan": list(host.calibration_call_plan()),
    }


def _patch_repo(monkeypatch) -> None:
    monkeypatch.setattr(
        host,
        "probe_calibration_git_repository",
        lambda root: host.CalibrationRepositoryState(commit="commit", tree="tree", clean=True),
    )


def test_calibration_host_completes_exact_frozen_matrix(tmp_path: Path, monkeypatch):
    _patch_repo(monkeypatch)
    client = QueueClient()
    artifact = tmp_path / "artifact"
    repository = tmp_path / "repo"
    repository.mkdir()

    result = host.run_calibration_host(
        artifact_root=artifact,
        identity=_identity(client),
        repository_root=repository,
        live_binding_probe=_binding,
        client=client,
    )

    assert result.status == "COMPLETED"
    assert result.claim_status == CALIBRATION_CLAIM_STATUS
    assert result.citable is False
    assert result.provider_attempts == result.provider_completions == 72
    assert result.selected_difficulty is None

    durable = json.loads((artifact / "calibration-result.json").read_text())
    assert durable["provider_attempts"] == durable["provider_completions"] == 72
    assert durable["selected_difficulty"] is None
    assert len(durable["cells"]) == len(CALIBRATION_DIFFICULTIES) * len(CALIBRATION_SEEDS)
    evidence = (artifact / "request-evidence.jsonl").read_text().splitlines()
    assert len(evidence) == 72
    assert json.loads(evidence[0])["question_id"] == host.calibration_call_plan()[0]


def test_calibration_host_binding_drift_fails_before_first_provider_attempt(
    tmp_path: Path,
    monkeypatch,
):
    _patch_repo(monkeypatch)
    client = QueueClient()
    artifact = tmp_path / "artifact"
    repository = tmp_path / "repo"
    repository.mkdir()
    calls = 0

    def probe():
        nonlocal calls
        calls += 1
        value = _binding()
        if calls >= 2:
            value["context_length"] = 4096
        return value

    with pytest.raises(host.CalibrationHostError, match="context_length changed"):
        host.run_calibration_host(
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


def test_calibration_host_counts_failed_first_provider_attempt(
    tmp_path: Path,
    monkeypatch,
):
    _patch_repo(monkeypatch)
    client = QueueClient(fail_first=True)
    artifact = tmp_path / "artifact"
    repository = tmp_path / "repo"
    repository.mkdir()

    with pytest.raises(StructureProposalError, match="synthetic provider failure"):
        host.run_calibration_host(
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


def test_native_probe_returns_unique_loaded_model_binding():
    response = {
        "models": [
            {
                "type": "llm",
                "key": "google/gemma-4-12b",
                "architecture": "gemma4",
                "format": "gguf",
                "quantization": {"name": "Q4_K_M", "bits_per_weight": 4},
                "selected_variant": "google/gemma-4-12b@q4_k_m",
                "capabilities": {
                    "reasoning": {"allowed_options": ["off", "on"], "default": "on"}
                },
                "loaded_instances": [
                    {
                        "id": "google/gemma-4-12b",
                        "config": {"context_length": 8192},
                    }
                ],
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/models"
        return httpx.Response(200, json=response)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        binding = host.probe_lmstudio_native_calibration_binding(
            base_url="http://lmstudio:1234",
            model="google/gemma-4-12b",
            http_client=client,
        )

    assert binding["model_instance_id"] == "google/gemma-4-12b"
    assert binding["context_length"] == 8192
    assert binding["runtime"]["reasoning_capability"]["default"] == "on"


def test_call_plan_is_frozen_72_calls():
    assert len(host.calibration_call_plan()) == (
        len(CALIBRATION_DIFFICULTIES)
        * len(CALIBRATION_SEEDS)
        * len(CALIBRATION_PROBES)
    ) == 72
