from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
import sys
from typing import Any

import pytest

from tools.external_qualification import DurableQuestion
from tools.external_qualification_readiness import ExternalQualificationReadinessError
from tools.v1_external_qualification_llama_cpp_campaign import (
    CAMPAIGN_TARGET,
    CampaignCarriageError,
    CampaignAxis,
    CampaignDescriptor,
    HindsightComparatorExecutor,
    HindsightHistoryPlan,
    HindsightSemanticRequestError,
    HindsightDeploymentSession,
    HindsightLifecycleSpec,
    ParticipantExecutionContext,
    ParticipantExecutionResult,
    ParticipantExecutors,
    run_campaign,
    _campaign_contract,
    _fingerprint,
    _hindsight_axis_bank_id,
    _hindsight_operational_fingerprint,
    _hindsight_owner_deployment_id,
)


def _release() -> dict[str, object]:
    return {
        "schema_version": 1,
        "package": "relaylm",
        "version": "1.0.0rc1",
        "release_kind": "rc",
        "tag": "v1.0.0rc1",
        "commit": "d" * 40,
        "artifacts": [
            {"filename": "relaylm-1.0.0rc1-py3-none-any.whl", "sha256": "1" * 64},
            {"filename": "relaylm-1.0.0rc1.tar.gz", "sha256": "2" * 64},
        ],
    }


def _participant_identity(
    implementation: str,
    *,
    revision: str,
    version: str,
    physical_model: str = "gemma-4-12b-q4",
) -> dict[str, object]:
    return {
        "implementation": implementation,
        "source_revision": revision,
        "version": version,
        "deployment": "local-process",
        "license": "MIT",
        "physical_model": {
            "artifact": physical_model,
            "tokenizer": "gemma-4",
            "quantization": "Q4_K_M",
        },
        "provider": "openai-compatible",
        "backend": "llama.cpp",
        "runtime": "llama-server",
        "context_capacity": 8192,
        "decoding": {"temperature": "0"},
        "reasoning": {"effort": "none"},
        "hardware": {"gpu": "synthetic-gpu", "cpu": "synthetic-cpu", "offload": "full"},
        "retry_policy": "no retry",
        "matched_condition_differences": [],
    }


def _manifest(adapter_id: str) -> dict[str, object]:
    release = _release()
    return {
        "format_version": 1,
        "purpose": "release_qualification",
        "harness": {"identity": "rinsakamo/relay-lm", "revision": "a" * 40},
        "adapter": {"identity": adapter_id, "revision": "b" * 40},
        "participants": [
            {
                "slot": "same_model_direct",
                "identity": _participant_identity(
                    "same-model-direct", revision="e" * 40, version="direct-v1"
                ),
                "omission_reason": None,
            },
            {
                "slot": "simple_baseline",
                "identity": None,
                "omission_reason": "not meaningful for this bounded axis",
            },
            {
                "slot": "serious_comparator",
                "identity": _participant_identity(
                    "hindsight", revision="c" * 40, version="v0.10.0"
                ),
                "omission_reason": None,
            },
            {
                "slot": "relaylm_exact_rc",
                "identity": _participant_identity(
                    "relaylm", revision=str(release["commit"]), version=str(release["version"])
                ),
                "omission_reason": None,
            },
        ],
        "relaylm_release": release,
        "judge": {"identity": "judge@frozen-revision", "policy": "same policy"},
        "replicate_id": "0",
    }


def _case(axis: str, benchmark: str, case_id: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "axis": axis,
        "benchmark": {
            "id": benchmark,
            "repository": f"https://example.test/{benchmark}.git",
            "revision": "f" * 40,
            "license": "MIT",
        },
        "dataset": {"revision": "dataset-revision", "license": "CC-BY-4.0"},
        "adapter_case_ref": f"cases/{case_id}",
    }


def _capacity() -> dict[str, object]:
    return {
        "kind": "synthetic-live-capacity",
        "gpu_identity": {
            "name": "synthetic-gpu",
            "driver_version": "synthetic-driver",
            "memory_total_mib": "12288",
            "memory_used_mib": "100",
        },
        "context": 8192,
        "slots": 1,
    }


def _live_mapping(capacity: Mapping[str, object] | None = None) -> dict[str, object]:
    capacity = capacity or _capacity()
    return {
        "backend": "llama.cpp",
        "runtime": "llama-server-test",
        "model_runner": "llama-server-test-runner",
        "effective_gpu_reservation": 1.0,
        "admitted_context": 8192,
        "capacity_evidence": capacity,
        "launch_evidence_reference": "live/runtime-attestation.json",
        "runtime_ownership_evidence_reference": "live/runtime-ownership.json",
    }


def _frozen_identity(axis: str, live: Mapping[str, object]) -> dict[str, object]:
    return {
        "repository": "rinsakamo/relay-lm",
        "candidate": "d" * 40,
        "prompt_core": "sha256:" + "1" * 64,
        "benchmark": axis,
        "dataset": "dataset-sha256:" + "2" * 64,
        "harness": "harness-sha256:" + "3" * 64,
        "adapter": "adapter-sha256:" + "4" * 64,
        "model": "gemma-4-12b-q4",
        "artifact": "artifact-sha256:" + "5" * 64,
        "tokenizer": "tokenizer-sha256:" + "6" * 64,
        "template": "template-v1",
        "backend": live["backend"],
        "runtime": live["runtime"],
        "decoding": {"temperature": 0},
        "reasoning": {"effort": "none"},
        "structured_output": "json-schema-v1",
        "context_capacity": live["admitted_context"],
        "capacity_evidence": live["capacity_evidence"],
        "hardware": {"gpu": "synthetic-gpu", "vram": 12288},
        "execution_order": "frozen-dataset-order-v1",
        "retry_policy": "no semantic retry",
        "authority": {
            "status": "CURRENT_AUTHORITY_CONFIRMED",
            "branch": "v1",
            "repository_head": "f" * 40,
            "repository_tree": "e" * 40,
        },
        "launch_admission": live,
    }


def _health() -> dict[str, object]:
    return {
        "implementation": "hindsight",
        "source_revision": "c" * 40,
        "version": "v0.10.0",
        "license": "MIT",
        "deployment": {
            "deployment_id": "hindsight-test-deployment",
            "dependency_fingerprint": "sha256:" + "7" * 64,
            "import_status": "passed",
            "llm_connection_verification": "skipped_zero_semantic_policy",
            "process_health_status": "passed",
            "capability_status": "passed",
        },
        "semantic_operations_called": [],
        "semantic_generation_count": 0,
        "benchmark_question_count": 0,
        "answer_model_generation_count": 0,
        "judge_call_count": 0,
    }


def _descriptor_mapping(tmp_path: Path, *, run_mode: str = "fresh_run") -> dict[str, object]:
    live = _live_mapping()
    axes: list[dict[str, object]] = []
    release_cases: list[dict[str, object]] = []
    for axis_id, axis_family, benchmark, adapter in (
        ("axis-a", "conflict_temporal_validity", "benchmark-a", "adapter-a"),
        ("axis-b", "update_belief_revision", "benchmark-b", "adapter-b"),
    ):
        case = _case(axis_family, benchmark, f"{axis_id}-case")
        manifest = _manifest(adapter)
        question = DurableQuestion.from_content(
            f"{axis_id}-question",
            f"synthetic question for {axis_id}",
            session_id=axis_id,
        )
        release_cases.append({"axis_id": axis_id, "case": case, "manifest": manifest})
        axes.append(
            {
                "axis_id": axis_id,
                "case": case,
                "manifest": manifest,
                "identity": _frozen_identity(axis_id, live),
                "questions": [
                    {
                        "question_id": question.question_id,
                        "prompt": f"synthetic question for {axis_id}",
                        "content_fingerprint": question.content_fingerprint,
                        "session_id": axis_id,
                    }
                ],
                "run_mode": run_mode,
            }
        )
    return {
        "format_version": 1,
        "target": CAMPAIGN_TARGET,
        "execution_freeze": {
            "format_version": 1,
            "phase": "execution_freeze",
            "axes": [
                {
                    "axis_id": "axis-a",
                    "axis_family": "conflict_temporal_validity",
                    "benchmark_id": "benchmark-a",
                    "adapter_id": "adapter-a",
                },
                {
                    "axis_id": "axis-b",
                    "axis_family": "update_belief_revision",
                    "benchmark_id": "benchmark-b",
                    "adapter_id": "adapter-b",
                },
            ],
            "comparator": {
                "implementation": "hindsight",
                "repository": "https://github.com/vectorize-io/hindsight",
                "source_revision": "c" * 40,
                "version": "v0.10.0",
                "license": "MIT",
            },
            "physical_carriage": {
                "target": CAMPAIGN_TARGET,
                "backend": "llama.cpp",
                "resource_key": "llama-cpp:local-gpu",
                "registered": True,
            },
            "release_cases": release_cases,
            "retry_policy": "no_semantic_retry_or_fallback",
            "resume_policy": "exact_infrastructure_resume_only",
        },
        "artifact_root": str(tmp_path / "campaign-artifacts"),
        "llama_cpp": {
            "llama_cpp_root": str(tmp_path / "llama.cpp"),
            "artifact_path": str(tmp_path / "relaylm-1.0.0rc1.whl"),
            "upstream_revision": "a" * 40,
            "expected_build_info": "b10874-" + "a" * 9,
            "expected_model_alias": "gemma-test",
            "artifact_sha256": "b" * 64,
            "runtime": live["runtime"],
            "model_runner": live["model_runner"],
            "context": 8192,
            "slots": 1,
            "port": 18091,
            "gpu_layers": 99,
            "effective_gpu_reservation": 1.0,
            "capacity_evidence": live["capacity_evidence"],
        },
        "hindsight_health": _health(),
        "axes": axes,
    }


def _observation() -> dict[str, object]:
    return {
        "quality": {"accuracy": 0.0},
        "tokens": {"model_input_tokens": 0, "model_output_tokens": 0, "model_call_count": 0},
        "latency": {"ttft_ms": 0.0, "query_latency_ms": 0.0, "end_to_end_ms": 0.0},
        "resources": {
            "peak_gpu_memory_bytes": 0,
            "peak_cpu_memory_bytes": 0,
            "persistent_storage_bytes": 0,
            "notes": ["typed deterministic unit fixture"],
        },
        "known_limitations": ["no provider invocation"],
        "failure": None,
    }


class _Probe:
    def __init__(self, value: Mapping[str, object]) -> None:
        self.value = value
        self.calls = 0

    def attest_zero_semantic_health(self) -> Mapping[str, object]:
        self.calls += 1
        return self.value


class _Session:
    launch_count = 1

    def __init__(self, value: Mapping[str, object]) -> None:
        self.value = value
        self.attest_calls = 0
        self.cleanup_calls = 0

    def attest(self) -> Mapping[str, object]:
        self.attest_calls += 1
        return self.value

    def cleanup(self) -> Mapping[str, object]:
        self.cleanup_calls += 1
        return {
            "all_owned_processes_terminated": True,
            "external_processes_touched": 0,
            "errors": [],
        }


class _CleanupFailSession(_Session):
    def cleanup(self) -> Mapping[str, object]:
        self.cleanup_calls += 1
        raise RuntimeError("synthetic cleanup failure")


class _LifecycleResponse:
    def __init__(self, status_code: int, payload: Mapping[str, object]) -> None:
        self.status_code = status_code
        self._payload = dict(payload)

    def json(self) -> Mapping[str, object]:
        return dict(self._payload)


class _LifecycleClient:
    def __init__(self, health_responses: list[_LifecycleResponse]) -> None:
        self.health_responses = health_responses
        self.get_paths: list[str] = []
        self.post_paths: list[str] = []

    def post(self, url: str, **_: object) -> _LifecycleResponse:
        self.post_paths.append(url)
        return _LifecycleResponse(204, {})

    def get(self, url: str) -> _LifecycleResponse:
        self.get_paths.append(url)
        if url.endswith("/health"):
            return self.health_responses.pop(0)
        return _LifecycleResponse(200, {"api_version": "0.10.0"})

    def close(self) -> None:
        return None


class _SemanticResponse:
    def __init__(
        self,
        status_code: int,
        payload: Mapping[str, object],
        *,
        headers: Mapping[str, str] | None = None,
        text: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = dict(headers or {})
        self._payload = dict(payload)
        self.text = text if text is not None else json.dumps(self._payload)

    def json(self) -> Mapping[str, object]:
        return dict(self._payload)


class _SemanticClient:
    def __init__(self, responses: list[_SemanticResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def post(self, url: str, *, json: Mapping[str, object]) -> _SemanticResponse:
        self.calls.append((url, dict(json)))
        return self.responses.pop(0)

    def close(self) -> None:
        return None


class _ComparatorLifecycle:
    def __init__(self, profile: str) -> None:
        self.spec = type("Spec", (), {"database_profile": profile})()
        self.retain_calls: list[tuple[str, tuple[Mapping[str, object], ...]]] = []
        self.recall_calls: list[tuple[str, str]] = []
        self.reflect_calls: list[tuple[str, str, Mapping[str, object]]] = []

    def retain(
        self,
        *,
        bank_id: str,
        items: tuple[Mapping[str, object], ...],
    ) -> Mapping[str, object]:
        self.retain_calls.append((bank_id, tuple(dict(item) for item in items)))
        return {"retained": len(items)}

    def recall(self, prompt: str, *, bank_id: str) -> Mapping[str, object]:
        self.recall_calls.append((bank_id, prompt))
        return {"results": []}

    def reflect(
        self,
        prompt: str,
        *,
        context: Mapping[str, object],
        bank_id: str,
    ) -> Mapping[str, object]:
        self.reflect_calls.append((bank_id, prompt, dict(context)))
        return {"text": "synthetic reflection"}


def _controller_parts(
    descriptor: CampaignDescriptor,
    session: _Session,
    seen: list[ParticipantExecutionContext],
    *,
    scientific: bool = False,
) -> dict[str, Any]:
    def factory(spec: Any, evidence_root: Path) -> _Session:
        return session

    def executor(context: ParticipantExecutionContext) -> ParticipantExecutionResult:
        seen.append(context)
        return ParticipantExecutionResult(
            slot=context.participant_slot,
            observation={
                **_observation(),
                "tokens": {
                    **_observation()["tokens"],
                    "model_call_count": 1 if scientific else 0,
                },
            },
            semantic_generation_count=1 if scientific else 0,
        )

    probe = _Probe(descriptor.hindsight_health.value)
    return {
        "live_launch_factory": factory,
        "hindsight_probe": probe,
        "participant_executors": ParticipantExecutors(
            same_model_direct=executor,
            serious_comparator=executor,
            relaylm_exact_rc=executor,
        ),
        "current_authority_reader": lambda: {
            "status": "CURRENT_AUTHORITY_CONFIRMED",
            "branch": "v1",
            "repository_head": "f" * 40,
            "repository_tree": "e" * 40,
        },
    }


def _refresh_campaign_contracts(raw: dict[str, object]) -> None:
    axes = raw["axes"]
    assert isinstance(axes, list)
    for axis in axes:
        assert isinstance(axis, dict)
        parsed_axis = CampaignAxis.from_mapping(axis)
        assert isinstance(parsed_axis.identity, dict)
        parsed_axis.identity["campaign_contract"] = _campaign_contract(parsed_axis)


def _set_comparator_deployment(raw: dict[str, object], deployment: str) -> None:
    axes = raw["axes"]
    assert isinstance(axes, list)
    for axis in axes:
        assert isinstance(axis, dict)
        manifest = axis["manifest"]
        assert isinstance(manifest, dict)
        participants = manifest["participants"]
        assert isinstance(participants, list)
        comparator = next(
            participant
            for participant in participants
            if isinstance(participant, dict) and participant.get("slot") == "serious_comparator"
        )
        identity = comparator["identity"]
        assert isinstance(identity, dict)
        identity["deployment"] = deployment


def _strict_descriptor_mapping(
    tmp_path: Path,
    *,
    run_mode: str = "fresh_run",
) -> dict[str, object]:
    raw = _descriptor_mapping(tmp_path, run_mode=run_mode)
    model_path = tmp_path / "gemma.gguf"
    model_path.write_bytes(b"frozen-model")
    model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    config_path = tmp_path / "relaylm-config.yaml"
    config_path.write_text("mode: exact-rc\n", encoding="utf-8")
    config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
    wheel_path = tmp_path / "relaylm-1.0.0rc1-py3-none-any.whl"
    wheel_path.write_bytes(b"accepted-rc-wheel")
    wheel_sha = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
    onnx_path = tmp_path / "model.onnx"
    onnx_path.write_bytes(b"frozen-onnx")
    tokenizer_path = tmp_path / "tokenizer"
    tokenizer_path.mkdir(exist_ok=True)
    (tokenizer_path / "tokenizer.json").write_text("{}\n", encoding="utf-8")
    (tokenizer_path / "config.json").write_text("{}\n", encoding="utf-8")
    tokenizer_entries = []
    for child in sorted(tokenizer_path.rglob("*")):
        if child.is_file():
            tokenizer_entries.append(
                {
                    "path": child.relative_to(tokenizer_path).as_posix(),
                    "sha256": hashlib.sha256(child.read_bytes()).hexdigest(),
                }
            )
    tokenizer_tree_sha = hashlib.sha256(
        json.dumps(tokenizer_entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    template_sha = "3" * 64
    physical_model = {
        "artifact": f"model:sha256={model_sha}",
        "tokenizer": "tokenizer:sha256=" + "4" * 64,
        "quantization": "Q4_K_M",
    }
    for axis in raw["axes"]:
        assert isinstance(axis, dict)
        manifest = axis["manifest"]
        assert isinstance(manifest, dict)
        for participant in manifest["participants"]:
            assert isinstance(participant, dict)
            if participant["identity"] is not None:
                assert isinstance(participant["identity"], dict)
                participant["identity"]["physical_model"] = dict(physical_model)
                participant["identity"]["runtime"] = raw["llama_cpp"]["runtime"]
                participant["identity"]["backend"] = "llama.cpp"
                participant["identity"]["context_capacity"] = 8192
        identity = axis["identity"]
        assert isinstance(identity, dict)
        identity["launch_admission"] = _strict_live_mapping(
            raw["llama_cpp"]["capacity_evidence"],
            model_path=model_path,
            model_sha=model_sha,
            template_sha=template_sha,
        )
        identity["capacity_evidence"] = raw["llama_cpp"]["capacity_evidence"]
        identity["artifact"] = f"model:sha256={model_sha}"
        identity["template"] = f"template:sha256={template_sha}"
        identity["runtime"] = raw["llama_cpp"]["runtime"]
        identity["backend"] = "llama.cpp"
        identity["context_capacity"] = 8192

    release_cases = raw["execution_freeze"]["release_cases"]
    for axis, frozen in zip(raw["axes"], release_cases, strict=True):
        assert isinstance(axis, dict) and isinstance(frozen, dict)
        question = axis["questions"][0]
        assert isinstance(question, dict)
        material_path = tmp_path / f"{axis['axis_id']}-benchmark.json"
        material_path.write_text(
            json.dumps({"axis_id": axis["axis_id"], "case": axis["case"]}, sort_keys=True),
            encoding="utf-8",
        )
        material = {
            "path": str(material_path),
            "sha256": hashlib.sha256(material_path.read_bytes()).hexdigest(),
            "case_fingerprint": _fingerprint(axis["case"]),
            "question_fingerprints": [question["content_fingerprint"]],
        }
        history_path = tmp_path / f"{axis['axis_id']}-history.json"
        history_session_id = f"{axis['axis_id']}-history-session-0"
        history_path.write_text(
            json.dumps(
                {
                    "format_version": 1,
                    "sessions": [
                        {
                            "session_id": history_session_id,
                            "order": 0,
                            "items": [
                                {
                                    "role": "user",
                                    "content": f"synthetic history for {axis['axis_id']}",
                                    "timestamp": None,
                                },
                                {
                                    "role": "assistant",
                                    "content": f"synthetic answer history for {axis['axis_id']}",
                                    "timestamp": None,
                                },
                            ],
                        }
                    ],
                    "question_history": {
                        question["question_id"]: [history_session_id],
                    },
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        history_material = {
            "path": str(history_path),
            "sha256": hashlib.sha256(history_path.read_bytes()).hexdigest(),
        }
        axis["classification"] = "comparison_condition_mismatch"
        axis["benchmark_material"] = material
        axis["history_material"] = history_material
        frozen["benchmark_material"] = material
        frozen["history_material"] = history_material

    raw["llama_cpp"]["artifact_path"] = str(model_path)
    raw["llama_cpp"]["artifact_sha256"] = model_sha
    raw["relaylm_exact_rc"] = {
        "wheel_path": str(wheel_path),
        "wheel_sha256": wheel_sha,
        "version": "1.0.0rc1",
        "source_revision": "d" * 40,
        "source_tree": "e" * 40,
        "distribution": "relaylm",
        "config_path": str(config_path),
        "config_sha256": config_sha,
        "port": 18092,
    }
    owner_id = "owner-2965-strict-test"
    deployment_id = _hindsight_owner_deployment_id(owner_id)
    raw["hindsight_lifecycle"] = {
        "mode": "owned_local",
        "base_url": "http://127.0.0.1:44367",
        "health_path": "/health",
        "deployment_id": deployment_id,
        "dependency_fingerprint": "sha256:" + "7" * 64,
        "cleanup_path": "/cleanup",
        "start_path": "/start",
        "runtime_python": sys.executable,
        "runtime_version": "v0.10.0",
        "source_revision": "c" * 40,
        "source_tree": "f" * 40,
        "database_profile": owner_id,
        "llm_model": "openai/gpt-oss-120b",
        "llm_base_url": "http://127.0.0.1:18091/v1",
        "embeddings_provider": "onnx",
        "reranker_provider": "rrf",
        "embeddings_onnx_model_path": str(onnx_path),
        "embeddings_onnx_model_sha256": hashlib.sha256(onnx_path.read_bytes()).hexdigest(),
        "embeddings_onnx_tokenizer_path": str(tokenizer_path),
        "embeddings_onnx_tokenizer_tree_sha256": tokenizer_tree_sha,
        "package_wheel_sha256": {
            "hindsight-all": "1" * 64,
            "hindsight-api-slim": "2" * 64,
            "hindsight-client": "3" * 64,
            "hindsight-embed": "4" * 64,
        },
        "port": 44367,
    }
    raw["owner_id"] = owner_id
    raw["spend_ledger_path"] = str(tmp_path / "scientific-spend.json")
    raw["hindsight_health"]["source_revision"] = "c" * 40
    raw["hindsight_health"]["deployment"]["deployment_id"] = deployment_id
    raw["hindsight_health"]["deployment"]["dependency_fingerprint"] = "sha256:" + "7" * 64
    for manifest in (axis["manifest"] for axis in raw["axes"]):
        assert isinstance(manifest, dict)
        manifest["relaylm_release"]["artifacts"][0]["sha256"] = wheel_sha
    raw["relaylm_exact_rc"]["wheel_sha256"] = wheel_sha
    lifecycle = HindsightLifecycleSpec.from_mapping(raw["hindsight_lifecycle"])
    _set_comparator_deployment(
        raw,
        _hindsight_operational_fingerprint(owner_id, lifecycle),
    )
    _refresh_campaign_contracts(raw)
    return raw


def _strict_live_mapping(
    capacity: Mapping[str, object],
    *,
    model_path: Path,
    model_sha: str,
    template_sha: str,
) -> dict[str, object]:
    return {
        **_live_mapping(capacity),
        "runtime_identity": {
            "upstream_revision": "a" * 40,
            "build_info": "b10874-aaaaaaaaa",
            "model_alias": "gemma-test",
            "model_path": str(model_path),
            "artifact_sha256": model_sha,
            "chat_template_sha256": template_sha,
            "context_limit": 8192,
            "total_slots": 1,
            "context_shift_enabled": False,
        },
        "gpu_identity": {
            "name": "synthetic-gpu",
            "driver_version": "synthetic-driver",
            "memory_total_mib": "12288",
        },
        "launch_observation": {
            "runtime_evidence_path": "live/runtime-attestation.json",
            "runtime_ownership_evidence_path": "live/runtime-ownership.json",
            "pid": 1234,
            "memory_used_mib": "100",
            "observed_at": "launch-1",
        },
    }


def test_zero_validation_is_complete_and_does_not_spend(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from tools.v1_external_qualification_llama_cpp_campaign import main

    plan_path = tmp_path / "campaign.json"
    plan_path.write_text(
        json.dumps(_descriptor_mapping(tmp_path), sort_keys=True),
        encoding="utf-8",
    )
    assert main(["--plan", str(plan_path)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "FULL_CAMPAIGN_CARRIAGE_READY"
    assert receipt["target"] == CAMPAIGN_TARGET
    assert receipt["semantic_generation_count"] == 0
    assert receipt["benchmark_question_count"] == 0
    assert receipt["answer_model_generation_count"] == 0
    assert receipt["judge_call_count"] == 0
    assert receipt["llama_server_launch_count"] == 0
    assert receipt["SCIENTIFIC_SPEND"] == "UNSPENT"


def test_descriptor_rejects_arbitrary_command_fields(tmp_path: Path) -> None:
    raw = _descriptor_mapping(tmp_path)
    raw["command"] = ["sh", "-c", "anything"]
    with pytest.raises(CampaignCarriageError, match="exact"):
        CampaignDescriptor.from_mapping(raw)


def test_registry_adds_campaign_without_rebinding_admission_target() -> None:
    registry = json.loads(
        (Path(__file__).parents[2] / ".ai/physical/llama_cpp_targets.json").read_text(
            encoding="utf-8"
        )
    )
    targets = registry["targets"]
    assert targets["v1:external-qualification"]["module"] == (
        "tools.v1_external_qualification_llama_cpp_gate"
    )
    assert targets[CAMPAIGN_TARGET]["module"] == (
        "tools.v1_external_qualification_llama_cpp_campaign"
    )
    assert targets[CAMPAIGN_TARGET]["branch"] == "v1"
    assert targets[CAMPAIGN_TARGET]["required_distributions"] == ["httpx"]


def test_typed_controller_freezes_live_identity_and_cleans_owned_session(tmp_path: Path) -> None:
    descriptor = CampaignDescriptor.from_mapping(_descriptor_mapping(tmp_path))
    live = _live_mapping()
    session = _Session(live)
    seen: list[ParticipantExecutionContext] = []
    parts = _controller_parts(descriptor, session, seen)

    receipt = run_campaign(descriptor, **parts)

    assert session.attest_calls == 1
    assert session.cleanup_calls == 1
    assert len(seen) == 6
    assert {context.participant_slot for context in seen} == {
        "same_model_direct",
        "serious_comparator",
        "relaylm_exact_rc",
    }
    assert all(context.prompt == context.question.content for context in seen)
    assert receipt["counters"] == {
        "semantic_generation_count": 0,
        "benchmark_question_count": 2,
        "answer_model_generation_count": 0,
        "judge_call_count": 0,
        "scientific_durable_run_completion_count": 2,
    }
    assert receipt["SCIENTIFIC_SPEND"] == "UNSPENT"
    observed = receipt["observed_execution"]
    assert observed["authority"] == "OBSERVED_EXECUTION"
    assert observed["live_launch_attestation"] == live
    assert observed["live_launch_attestation_fingerprint"]
    assert all(item["status"] == "completed" for item in receipt["axis_receipts"])


def test_live_identity_mismatch_fails_before_any_participant_and_still_cleans(tmp_path: Path) -> None:
    descriptor = CampaignDescriptor.from_mapping(_descriptor_mapping(tmp_path))
    changed = _live_mapping()
    changed["runtime"] = "different-live-runtime"
    session = _Session(changed)
    seen: list[ParticipantExecutionContext] = []
    parts = _controller_parts(descriptor, session, seen)

    with pytest.raises(CampaignCarriageError, match="runtime"):
        run_campaign(descriptor, **parts)

    assert seen == []
    assert session.attest_calls == 1
    assert session.cleanup_calls == 1


def test_participant_failure_leaves_durable_tail_for_exact_resume_and_cleans(tmp_path: Path) -> None:
    descriptor = CampaignDescriptor.from_mapping(_descriptor_mapping(tmp_path))
    session = _Session(_live_mapping())
    seen: list[ParticipantExecutionContext] = []
    parts = _controller_parts(descriptor, session, seen)

    def fail(_context: ParticipantExecutionContext) -> ParticipantExecutionResult:
        raise RuntimeError("synthetic participant stop")

    parts["participant_executors"] = ParticipantExecutors(
        same_model_direct=fail,
        serious_comparator=fail,
        relaylm_exact_rc=fail,
    )
    with pytest.raises(RuntimeError, match="synthetic participant stop"):
        run_campaign(descriptor, **parts)

    assert session.cleanup_calls == 1
    state = json.loads(
        (tmp_path / "campaign-artifacts" / "axis-a" / "run-state.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["status"] == "RUNNING"
    assert state["in_flight_questions"] == ["axis-a-question"]


def test_cleanup_failure_does_not_replace_active_participant_failure(
    tmp_path: Path,
) -> None:
    descriptor = CampaignDescriptor.from_mapping(_descriptor_mapping(tmp_path))
    session = _CleanupFailSession(_live_mapping())

    def fail(_context: ParticipantExecutionContext) -> ParticipantExecutionResult:
        raise RuntimeError("synthetic participant failure")

    parts = _controller_parts(descriptor, session, [])
    parts["participant_executors"] = ParticipantExecutors(
        same_model_direct=fail,
        serious_comparator=fail,
        relaylm_exact_rc=fail,
    )
    with pytest.raises(RuntimeError, match="synthetic participant failure") as failure:
        run_campaign(descriptor, **parts)
    assert session.cleanup_calls == 1
    assert any("llama cleanup failed" in note for note in failure.value.__notes__)


def test_hindsight_health_waits_for_owned_startup_without_semantic_calls(
    tmp_path: Path,
) -> None:
    descriptor = CampaignDescriptor.from_mapping(_strict_descriptor_mapping(tmp_path))
    assert descriptor.hindsight_lifecycle is not None
    lifecycle = HindsightDeploymentSession(
        replace(descriptor.hindsight_lifecycle, mode="owned_http"),
        descriptor.hindsight_health,
    )
    client = _LifecycleClient(
        [
            _LifecycleResponse(503, {"status": "starting"}),
            _LifecycleResponse(200, {"status": "healthy"}),
        ]
    )
    lifecycle.client = client  # type: ignore[assignment]

    lifecycle.start()
    observed = lifecycle.attest_zero_semantic_health()

    assert observed == descriptor.hindsight_health.value
    assert client.post_paths == ["http://127.0.0.1:44367/start"]
    assert client.get_paths == [
        "http://127.0.0.1:44367/health",
        "http://127.0.0.1:44367/health",
        "http://127.0.0.1:44367/version",
    ]
    assert lifecycle.health_count == 1
    assert lifecycle.semantic_operation_count == 0


def test_hindsight_v010_semantic_routes_and_failure_evidence_are_typed(
    tmp_path: Path,
) -> None:
    descriptor = CampaignDescriptor.from_mapping(_strict_descriptor_mapping(tmp_path))
    assert descriptor.hindsight_lifecycle is not None
    lifecycle = HindsightDeploymentSession(
        descriptor.hindsight_lifecycle,
        descriptor.hindsight_health,
    )
    client = _SemanticClient(
        [
            _SemanticResponse(200, {"retained": 2}),
            _SemanticResponse(200, {"results": []}),
            _SemanticResponse(200, {"text": "synthetic reflection"}),
        ]
    )
    lifecycle.client = client  # type: ignore[assignment]
    lifecycle.started = True

    lifecycle.retain(
        bank_id="synthetic-bank",
        items=(
            {
                "content": "synthetic history",
                "context": "user",
                "timestamp": None,
                "document_id": "synthetic-document",
            },
        ),
    )
    lifecycle.recall("synthetic question", bank_id="synthetic-bank")
    lifecycle.reflect(
        "synthetic question",
        context={"results": []},
        bank_id="synthetic-bank",
    )

    assert [url.removeprefix("http://127.0.0.1:44367") for url, _ in client.calls] == [
        "/v1/default/banks/synthetic-bank/memories",
        "/v1/default/banks/synthetic-bank/memories/recall",
        "/v1/default/banks/synthetic-bank/reflect",
    ]
    assert client.calls[0][1]["async"] is False
    assert client.calls[1][1] == {
        "query": "synthetic question",
        "max_tokens": 4096,
        "budget": "mid",
    }
    assert client.calls[2][1] == {
        "query": "synthetic question",
        "context": '{"results":[]}',
        "budget": "low",
    }
    assert all("/memories/reflect" not in url for url, _ in client.calls)
    assert lifecycle.semantic_operation_count == 3

    error_client = _SemanticClient(
        [
            _SemanticResponse(
                405,
                {"detail": "Method Not Allowed"},
                headers={"allow": "GET"},
                text='{"detail":"Method Not Allowed"}',
            )
        ]
    )
    lifecycle.client = error_client  # type: ignore[assignment]
    with pytest.raises(HindsightSemanticRequestError) as captured:
        lifecycle._semantic_post(
            operation="reflect",
            path="/v1/default/banks/synthetic-bank/memories/reflect",
            payload={"query": "synthetic question"},
        )
    assert captured.value.to_mapping() == {
        "operation": "reflect",
        "method": "POST",
        "path": "/v1/default/banks/synthetic-bank/memories/reflect",
        "status": 405,
        "allow": "GET",
        "body": '{"detail":"Method Not Allowed"}',
    }


def test_hindsight_history_is_ordered_exactly_once_and_profile_isolated(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "synthetic-history.json"
    history_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "sessions": [
                    {
                        "session_id": "session-0",
                        "order": 0,
                        "items": [
                            {
                                "role": "user",
                                "content": "synthetic first user",
                                "timestamp": None,
                            },
                            {
                                "role": "assistant",
                                "content": "synthetic first assistant",
                                "timestamp": None,
                            },
                        ],
                    },
                    {
                        "session_id": "session-1",
                        "order": 1,
                        "items": [
                            {
                                "role": "user",
                                "content": "synthetic second user",
                                "timestamp": None,
                            }
                        ],
                    },
                ],
                "question_history": {
                    "question-0": ["session-0"],
                    "question-1": ["session-0", "session-1"],
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    plan = HindsightHistoryPlan.from_path(history_path)
    lifecycle = _ComparatorLifecycle("repair-profile-a")
    executor = HindsightComparatorExecutor(lifecycle)  # type: ignore[arg-type]

    def context(question_id: str, prompt: str) -> ParticipantExecutionContext:
        return ParticipantExecutionContext(
            axis_id="axis-a",
            case={},
            manifest={},
            question=DurableQuestion.from_content(
                question_id,
                prompt,
                session_id=question_id,
            ),
            prompt=prompt,
            participant_slot="serious_comparator",
            participant_identity={},
            frozen_identity=None,  # type: ignore[arg-type]
            live_attestation=None,  # type: ignore[arg-type]
            history=plan,
        )

    first = executor(context("question-0", "synthetic question 0"))
    second = executor(context("question-1", "synthetic question 1"))
    repeated = executor(context("question-1", "synthetic question 1"))

    assert [item["content"] for item in lifecycle.retain_calls[0][1]] == [
        "synthetic first user",
        "synthetic first assistant",
    ]
    assert [item["content"] for item in lifecycle.retain_calls[1][1]] == [
        "synthetic second user",
    ]
    assert [item["document_id"] for item in lifecycle.retain_calls[0][1]] == [
        "relaylm-history-00000000",
        "relaylm-history-00000000",
    ]
    assert lifecycle.retain_calls[1][1][0]["document_id"] == "relaylm-history-00000001"
    assert first.request_evidence[0]["operations"] == ["retain", "recall", "reflect"]
    assert second.request_evidence[0]["operations"] == ["retain", "recall", "reflect"]
    assert repeated.request_evidence[0]["operations"] == ["recall", "reflect"]
    assert len(lifecycle.retain_calls) == 2
    assert len(lifecycle.recall_calls) == 3
    assert len(lifecycle.reflect_calls) == 3
    assert _hindsight_axis_bank_id("repair-profile-a", "axis-a") == lifecycle.retain_calls[0][0]
    assert _hindsight_axis_bank_id("repair-profile-a", "axis-a") != _hindsight_axis_bank_id(
        "repair-profile-b", "axis-a"
    )


def test_hindsight_history_rejects_reference_or_gold_fields(tmp_path: Path) -> None:
    path = tmp_path / "history-with-reference.json"
    path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "sessions": [],
                "question_history": {},
                "reference_answer": "must not enter Hindsight",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(CampaignCarriageError, match="keys must be exact"):
        HindsightHistoryPlan.from_path(path)


def test_strict_resume_rejects_old_descriptor_without_hindsight_history_boundary(
    tmp_path: Path,
) -> None:
    raw = _strict_descriptor_mapping(tmp_path, run_mode="exact_infrastructure_resume")
    axes = raw["axes"]
    release_cases = raw["execution_freeze"]["release_cases"]
    assert isinstance(axes, list)
    assert isinstance(release_cases, list)
    for axis, release_case in zip(axes, release_cases, strict=True):
        assert isinstance(axis, dict)
        assert isinstance(release_case, dict)
        axis.pop("history_material")
        release_case.pop("history_material")
    with pytest.raises(CampaignCarriageError, match="campaign axis keys must be exact"):
        CampaignDescriptor.from_mapping(raw)


def test_exact_resume_skips_completed_questions_and_does_not_reinvoke_hooks(tmp_path: Path) -> None:
    first_descriptor = CampaignDescriptor.from_mapping(_descriptor_mapping(tmp_path))
    first_session = _Session(_live_mapping())
    first_seen: list[ParticipantExecutionContext] = []
    run_campaign(first_descriptor, **_controller_parts(first_descriptor, first_session, first_seen))

    resumed_raw = _descriptor_mapping(tmp_path, run_mode="exact_infrastructure_resume")
    resumed_descriptor = CampaignDescriptor.from_mapping(resumed_raw)
    resumed_session = _Session(_live_mapping())
    resumed_seen: list[ParticipantExecutionContext] = []
    receipt = run_campaign(
        resumed_descriptor,
        **_controller_parts(resumed_descriptor, resumed_session, resumed_seen),
    )

    assert resumed_seen == []
    assert receipt["counters"]["benchmark_question_count"] == 0
    assert receipt["counters"]["semantic_generation_count"] == 0
    assert receipt["SCIENTIFIC_SPEND"] == "UNSPENT"
    assert resumed_session.cleanup_calls == 1


def test_strict_descriptor_binds_material_rc_hindsight_and_campaign_contract(
    tmp_path: Path,
) -> None:
    descriptor = CampaignDescriptor.from_mapping(_strict_descriptor_mapping(tmp_path))
    assert descriptor.relaylm_exact_rc is not None
    assert descriptor.hindsight_lifecycle is not None
    assert descriptor.artifact_root not in descriptor.spend_ledger_path.parents
    assert descriptor.hindsight_lifecycle.database_profile == descriptor.owner_id
    assert descriptor.hindsight_lifecycle.deployment_id == _hindsight_owner_deployment_id(
        descriptor.owner_id
    )
    expected_operational = _hindsight_operational_fingerprint(
        descriptor.owner_id,
        descriptor.hindsight_lifecycle,
    )
    assert all(axis.classification == "comparison_condition_mismatch" for axis in descriptor.axes)
    assert all(axis.benchmark_material is not None for axis in descriptor.axes)
    assert all(axis.history_material is not None for axis in descriptor.axes)
    assert all(axis.history_plan is not None for axis in descriptor.axes)
    assert all("campaign_contract" in axis.identity for axis in descriptor.axes)
    for axis in descriptor.axes:
        comparator = next(
            participant["identity"]
            for participant in axis.manifest["participants"]
            if participant["slot"] == "serious_comparator"
        )
        assert comparator["deployment"] == expected_operational


def test_strict_descriptor_rejects_stale_previous_owner_deployment_id(
    tmp_path: Path,
) -> None:
    raw = _strict_descriptor_mapping(tmp_path)
    stale_deployment = _hindsight_owner_deployment_id("owner-2961-rehearsal")
    raw["hindsight_lifecycle"]["deployment_id"] = stale_deployment
    raw["hindsight_health"]["deployment"]["deployment_id"] = stale_deployment
    with pytest.raises(CampaignCarriageError, match="deployment_id.*owner_id"):
        CampaignDescriptor.from_mapping(raw)


def test_strict_descriptor_rejects_stale_previous_owner_database_profile(
    tmp_path: Path,
) -> None:
    raw = _strict_descriptor_mapping(tmp_path)
    raw["hindsight_lifecycle"]["database_profile"] = "owner-2961-rehearsal"
    with pytest.raises(CampaignCarriageError, match="database profile.*owner_id"):
        CampaignDescriptor.from_mapping(raw)


def test_strict_descriptor_rejects_mutually_stale_health_and_lifecycle_for_new_owner(
    tmp_path: Path,
) -> None:
    raw = _strict_descriptor_mapping(tmp_path)
    stale_owner = "owner-2961-rehearsal"
    stale_deployment = _hindsight_owner_deployment_id(stale_owner)
    raw["hindsight_lifecycle"]["database_profile"] = stale_owner
    raw["hindsight_lifecycle"]["deployment_id"] = stale_deployment
    raw["hindsight_health"]["deployment"]["deployment_id"] = stale_deployment
    with pytest.raises(CampaignCarriageError, match="owner_id"):
        CampaignDescriptor.from_mapping(raw)


def test_strict_descriptor_rejects_rehearsal_identity_carry_over_after_owner_change(
    tmp_path: Path,
) -> None:
    raw = _strict_descriptor_mapping(tmp_path)
    raw["owner_id"] = "fresh-scientific-owner"
    with pytest.raises(CampaignCarriageError, match="owner_id"):
        CampaignDescriptor.from_mapping(raw)


def test_strict_descriptor_rejects_serious_comparator_operational_identity_drift(
    tmp_path: Path,
) -> None:
    raw = _strict_descriptor_mapping(tmp_path)
    _set_comparator_deployment(raw, "sha256:" + "0" * 64)
    with pytest.raises(CampaignCarriageError, match="serious comparator.*operational identity"):
        CampaignDescriptor.from_mapping(raw)


def test_strict_descriptor_rejects_frozen_contract_after_lifecycle_identity_changes(
    tmp_path: Path,
) -> None:
    raw = _strict_descriptor_mapping(tmp_path)
    raw["hindsight_lifecycle"]["llm_model"] = "openai/changed-answer-model"
    lifecycle = HindsightLifecycleSpec.from_mapping(raw["hindsight_lifecycle"])
    _set_comparator_deployment(
        raw,
        _hindsight_operational_fingerprint(str(raw["owner_id"]), lifecycle),
    )
    with pytest.raises(CampaignCarriageError, match="campaign contract drifted"):
        CampaignDescriptor.from_mapping(raw)


def test_hindsight_runtime_launch_arguments_derive_from_admitted_owner_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor = CampaignDescriptor.from_mapping(_strict_descriptor_mapping(tmp_path))
    assert descriptor.hindsight_lifecycle is not None
    seen: dict[str, object] = {}

    class _FakePopen:
        def __init__(self, command: list[str], **_: object) -> None:
            seen["command"] = list(command)
            self.pid = 4242
            self.returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.returncode = 0

        def kill(self) -> None:
            self.returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            self.returncode = 0
            return 0

    monkeypatch.setattr(subprocess, "Popen", _FakePopen)
    lifecycle = HindsightDeploymentSession(
        descriptor.hindsight_lifecycle,
        descriptor.hindsight_health,
        repo_root=tmp_path,
        evidence_root=tmp_path / "hindsight-evidence",
    )
    lifecycle.start()
    command = seen["command"]
    assert isinstance(command, list)

    def argument(name: str) -> str:
        index = command.index(name)
        value = command[index + 1]
        assert isinstance(value, str)
        return value

    assert argument("--database-profile") == descriptor.owner_id
    assert argument("--deployment-id") == _hindsight_owner_deployment_id(
        descriptor.owner_id
    )
    assert argument("--dependency-fingerprint") == descriptor.hindsight_lifecycle.dependency_fingerprint
    assert argument("--source-revision") == descriptor.hindsight_lifecycle.source_revision
    assert argument("--source-tree") == descriptor.hindsight_lifecycle.source_tree
    assert argument("--llm-model") == descriptor.hindsight_lifecycle.llm_model
    assert argument("--llm-base-url") == descriptor.hindsight_lifecycle.llm_base_url
    assert argument("--embeddings-provider") == descriptor.hindsight_lifecycle.embeddings_provider
    assert argument("--reranker-provider") == descriptor.hindsight_lifecycle.reranker_provider
    cleanup = lifecycle.cleanup()
    assert cleanup["semantic_operation_count"] == 0


def test_strict_descriptor_rejects_benchmark_material_replacement(
    tmp_path: Path,
) -> None:
    raw = _strict_descriptor_mapping(tmp_path)
    material = raw["axes"][0]["benchmark_material"]
    assert isinstance(material, dict)
    Path(material["path"]).write_text("changed\n", encoding="utf-8")
    with pytest.raises(ExternalQualificationReadinessError, match="content drifted"):
        CampaignDescriptor.from_mapping(raw)


def test_strict_descriptor_rejects_exact_rc_config_replacement(tmp_path: Path) -> None:
    raw = _strict_descriptor_mapping(tmp_path)
    exact_rc = raw["relaylm_exact_rc"]
    assert isinstance(exact_rc, dict)
    Path(exact_rc["config_path"]).write_text("changed\n", encoding="utf-8")
    with pytest.raises(CampaignCarriageError, match="config content drifted"):
        CampaignDescriptor.from_mapping(raw)


def test_strict_descriptor_rejects_exact_rc_wheel_replacement(tmp_path: Path) -> None:
    raw = _strict_descriptor_mapping(tmp_path)
    exact_rc = raw["relaylm_exact_rc"]
    assert isinstance(exact_rc, dict)
    Path(exact_rc["wheel_path"]).write_bytes(b"changed-wheel")
    with pytest.raises(CampaignCarriageError, match="wheel content drifted"):
        CampaignDescriptor.from_mapping(raw)


def test_strict_descriptor_rejects_manifest_wheel_identity_drift(tmp_path: Path) -> None:
    raw = _strict_descriptor_mapping(tmp_path)
    for axis in raw["axes"]:
        assert isinstance(axis, dict)
        manifest = axis["manifest"]
        assert isinstance(manifest, dict)
        manifest["relaylm_release"]["artifacts"][0]["sha256"] = "9" * 64
    _refresh_campaign_contracts(raw)
    with pytest.raises(CampaignCarriageError, match="wheel identity"):
        CampaignDescriptor.from_mapping(raw)


def test_strict_descriptor_rejects_frozen_candidate_drift_from_exact_rc(tmp_path: Path) -> None:
    raw = _strict_descriptor_mapping(tmp_path)
    for axis in raw["axes"]:
        assert isinstance(axis, dict)
        identity = axis["identity"]
        assert isinstance(identity, dict)
        identity["candidate"] = "9" * 40
    with pytest.raises(CampaignCarriageError, match="candidate.*RC"):
        CampaignDescriptor.from_mapping(raw)


def test_strict_pre_call_rehearsal_stays_unspent_and_invokes_no_participant(
    tmp_path: Path,
) -> None:
    descriptor = CampaignDescriptor.from_mapping(_strict_descriptor_mapping(tmp_path))
    live = descriptor.axes[0].identity["launch_admission"]
    session = _Session(live)
    seen: list[ParticipantExecutionContext] = []
    receipt = run_campaign(
        descriptor,
        **_controller_parts(descriptor, session, seen, scientific=True),
        pre_call_rehearsal=True,
    )
    assert seen == []
    assert receipt["status"] == "PRE_CALL_BARRIER_REACHED"
    assert receipt["pre_call_barrier_reached"] is True
    assert receipt["SCIENTIFIC_SPEND"] == "UNSPENT"
    assert receipt["counters"]["semantic_generation_count"] == 0
    assert receipt["counters"]["benchmark_question_count"] == 0
    observed = receipt["observed_execution"]
    assert observed["authority"] == "OBSERVED_EXECUTION"
    assert observed["live_launch_attestation"] == live
    assert session.cleanup_calls == 1
    ledger = json.loads(descriptor.spend_ledger_path.read_text(encoding="utf-8"))
    assert ledger["state"] == "UNSPENT"


def test_strict_resume_skips_participant_after_spend_consumption(tmp_path: Path) -> None:
    descriptor = CampaignDescriptor.from_mapping(_strict_descriptor_mapping(tmp_path))
    live = descriptor.axes[0].identity["launch_admission"]
    first_session = _Session(live)
    first_seen: list[ParticipantExecutionContext] = []
    failed = False

    def fail_once(context: ParticipantExecutionContext) -> ParticipantExecutionResult:
        nonlocal failed
        first_seen.append(context)
        if context.participant_slot == "serious_comparator" and not failed:
            failed = True
            raise RuntimeError("strict synthetic C failure")
        return ParticipantExecutionResult(
            slot=context.participant_slot,
            observation={
                **_observation(),
                "tokens": {**_observation()["tokens"], "model_call_count": 1},
            },
            semantic_generation_count=1,
        )

    first_parts = _controller_parts(descriptor, first_session, first_seen, scientific=True)
    first_parts["participant_executors"] = ParticipantExecutors(
        same_model_direct=fail_once,
        serious_comparator=fail_once,
        relaylm_exact_rc=fail_once,
    )
    with pytest.raises(RuntimeError, match="strict synthetic C failure"):
        run_campaign(descriptor, **first_parts)
    assert [context.participant_slot for context in first_seen] == [
        "same_model_direct",
        "serious_comparator",
    ]
    ledger = json.loads(descriptor.spend_ledger_path.read_text(encoding="utf-8"))
    assert ledger["state"] == "CONSUMED"

    resumed_raw = _strict_descriptor_mapping(tmp_path, run_mode="exact_infrastructure_resume")
    resumed_raw["axes"][1]["run_mode"] = "fresh_run"
    resumed = CampaignDescriptor.from_mapping(resumed_raw)
    resumed_session = _Session(resumed.axes[0].identity["launch_admission"])
    resumed_seen: list[ParticipantExecutionContext] = []
    receipt = run_campaign(
        resumed,
        **_controller_parts(resumed, resumed_session, resumed_seen, scientific=True),
    )
    assert [context.participant_slot for context in resumed_seen].count(
        "same_model_direct"
    ) == 1
    assert all(
        context.question.question_id != "axis-a-question"
        or context.participant_slot != "same_model_direct"
        for context in resumed_seen
    )
    assert receipt["SCIENTIFIC_SPEND"] == "CONSUMED"


def test_strict_resume_rejects_completed_question_aggregate_drift(
    tmp_path: Path,
) -> None:
    descriptor = CampaignDescriptor.from_mapping(_strict_descriptor_mapping(tmp_path))
    session = _Session(descriptor.axes[0].identity["launch_admission"])
    run_campaign(
        descriptor,
        **_controller_parts(
            descriptor,
            session,
            [],
            scientific=True,
        ),
    )

    observations_path = (
        tmp_path / "campaign-artifacts" / "axis-a" / "question-observations.jsonl"
    )
    records = [json.loads(line) for line in observations_path.read_text().splitlines()]
    for record in records:
        if record.get("event") == "completed":
            participants = record["result"]["participants"]
            participants[0]["observation"]["quality"]["accuracy"] = 0.25
            break
    observations_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )

    resumed = CampaignDescriptor.from_mapping(
        _strict_descriptor_mapping(tmp_path, run_mode="exact_infrastructure_resume")
    )
    with pytest.raises(CampaignCarriageError, match="aggregate disagrees"):
        run_campaign(
            resumed,
            **_controller_parts(
                resumed,
                _Session(resumed.axes[0].identity["launch_admission"]),
                [],
                scientific=True,
            ),
        )
