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

from tools.external_qualification import (
    DurableQuestion,
    DurableQuestionRun,
    ExactResumeError,
    freeze_experiment_identity,
)
from tools.external_qualification_readiness import ExternalQualificationReadinessError
from tools.v1_external_qualification_llama_cpp_campaign import (
    CAMPAIGN_TARGET,
    CampaignCarriageError,
    CampaignAxis,
    CampaignDescriptor,
    CommonAnswerModelExecutor,
    CommonAnswerModelResult,
    COMMON_ANSWER_SYSTEM_PROMPT,
    HindsightComparatorExecutor,
    HindsightHistoryPlan,
    HindsightSemanticRequestError,
    HindsightDeploymentSession,
    HindsightLifecycleSpec,
    ExactRelayLMExecutor,
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


class _AnswerClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def post(self, url: str, *, json: Mapping[str, object]) -> _SemanticResponse:
        self.calls.append((url, dict(json)))
        return _SemanticResponse(
            200,
            {
                "choices": [{"message": {"content": "cannot confirm"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 3},
            },
        )

    def close(self) -> None:
        return None


class _ComparatorLifecycle:
    def __init__(self, profile: str) -> None:
        self.spec = type("Spec", (), {"database_profile": profile})()
        self.retain_calls: list[tuple[str, tuple[Mapping[str, object], ...]]] = []
        self.recall_calls: list[tuple[str, str]] = []
        self.reflect_calls: list[tuple[str, str, Mapping[str, object]]] = []
        self.wait_calls: list[tuple[str, set[str]]] = []

    def retain(
        self,
        *,
        bank_id: str,
        items: tuple[Mapping[str, object], ...],
    ) -> Mapping[str, object]:
        self.retain_calls.append((bank_id, tuple(dict(item) for item in items)))
        return {"retained": len(items)}

    def recall(
        self,
        prompt: str,
        *,
        bank_id: str,
        query_timestamp: str | None = None,
    ) -> Mapping[str, object]:
        self.recall_calls.append((bank_id, prompt))
        return {"results": []}

    def consolidation_pending_ids(self, *, bank_id: str) -> set[str]:
        return set()

    def wait_for_consolidation(
        self,
        *,
        bank_id: str,
        pre_existing_pending_ids: set[str],
    ) -> Mapping[str, object]:
        self.wait_calls.append((bank_id, set(pre_existing_pending_ids)))
        return {"poll_count": 1, "elapsed_ms": 0.0, "outstanding_count": 0}

    def reflect(
        self,
        prompt: str,
        *,
        context: Mapping[str, object],
        bank_id: str,
    ) -> Mapping[str, object]:
        self.reflect_calls.append((bank_id, prompt, dict(context)))
        return {"text": "synthetic reflection"}


class _PreloadJournal:
    """Small in-memory double for the ordinary routing test."""

    def __init__(self) -> None:
        self.completed: set[str] = set()
        self.started: set[str] = set()
        self.requests: dict[str, Mapping[str, object]] = {}

    def _key(
        self,
        *,
        bank_id: str,
        session_id: str,
        exchange_index: int,
    ) -> str:
        return json.dumps(
            [bank_id, session_id, exchange_index],
            sort_keys=True,
        )

    def hindsight_history_preload_completed(
        self,
        *,
        question_id: str,
        bank_id: str,
        session_id: str,
        exchange_index: int,
    ) -> bool:
        key = self._key(
            bank_id=bank_id,
            session_id=session_id,
            exchange_index=exchange_index,
        )
        if key in self.started:
            raise ExactResumeError("synthetic preload ambiguity")
        return key in self.completed

    def begin_hindsight_history_preload(
        self,
        *,
        question_id: str,
        bank_id: str,
        session_id: str,
        exchange_index: int,
        request: Mapping[str, object],
    ) -> bool:
        key = self._key(
            bank_id=bank_id,
            session_id=session_id,
            exchange_index=exchange_index,
        )
        if key in self.completed:
            return False
        if key in self.started:
            raise ExactResumeError("synthetic preload ambiguity")
        self.started.add(key)
        self.requests[key] = dict(request)
        return True

    def complete_hindsight_history_preload(
        self,
        *,
        question_id: str,
        bank_id: str,
        session_id: str,
        exchange_index: int,
        request: Mapping[str, object],
    ) -> None:
        key = self._key(
            bank_id=bank_id,
            session_id=session_id,
            exchange_index=exchange_index,
        )
        if key not in self.started:
            raise ExactResumeError("synthetic preload completion without start")
        assert self.requests[key] == dict(request)
        self.started.remove(key)
        self.completed.add(key)

    def hindsight_history_preload_counts(self) -> dict[str, int]:
        return {"completed": len(self.completed), "in_flight": len(self.started)}

class _CommonAnswerModel:
    def __init__(self) -> None:
        self.calls: list[list[Mapping[str, object]]] = []

    def answer(
        self,
        context: ParticipantExecutionContext,
        retrieved_memories: list[Mapping[str, object]],
    ) -> CommonAnswerModelResult:
        self.calls.append(list(retrieved_memories))
        return CommonAnswerModelResult(
            observation=_observation(),
            request_evidence={
                "boundary": "common_answer_model",
                "response_shape": ["choices", "usage"],
            },
        )


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
        "types": ["observation"],
        "prefer_observations": True,
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
    journal = _PreloadJournal()
    answer_model = _CommonAnswerModel()
    executor = HindsightComparatorExecutor(  # type: ignore[arg-type]
        lifecycle,
        answer_model,  # type: ignore[arg-type]
    )

    def context(question_id: str, prompt: str) -> ParticipantExecutionContext:
        return ParticipantExecutionContext(
            axis_id="axis-a",
            case={"benchmark": {"id": "memconflict"}},
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
            durable_run=journal,  # type: ignore[arg-type]
        )

    first = executor(context("question-0", "synthetic question 0"))
    second = executor(context("question-1", "synthetic question 1"))
    repeated = executor(context("question-1", "synthetic question 1"))

    first_request = lifecycle.retain_calls[0][1][0]
    assert json.loads(str(first_request["content"])) == [
        {
            "role": "user",
            "content": "User: synthetic first user",
            "timestamp": None,
        },
        {
            "role": "assistant",
            "content": "Assistant: synthetic first assistant",
            "timestamp": None,
        },
    ]
    assert first_request["document_id"] == (
        f"{_hindsight_axis_bank_id('repair-profile-a', 'axis-a')}_doc_session-0"
    )
    assert first_request["update_mode"] == "append"
    assert lifecycle.retain_calls[1][1][0]["document_id"] == (
        f"{_hindsight_axis_bank_id('repair-profile-a', 'axis-a')}_doc_session-1"
    )
    assert first.request_evidence[0]["operations"] == [
        "retain",
        "consolidation_wait",
        "recall",
    ]
    assert second.request_evidence[0]["operations"] == [
        "retain",
        "consolidation_wait",
        "recall",
    ]
    assert repeated.request_evidence[0]["operations"] == ["recall"]
    assert first.request_evidence[0]["recall_request"] == {
        "budget": "mid",
        "max_tokens": 4096,
        "types": ["observation"],
        "prefer_observations": True,
        "query_timestamp": None,
    }
    assert len(lifecycle.retain_calls) == 2
    assert len(lifecycle.recall_calls) == 3
    assert len(lifecycle.reflect_calls) == 0
    assert len(answer_model.calls) == 3
    assert _hindsight_axis_bank_id("repair-profile-a", "axis-a") == lifecycle.retain_calls[0][0]
    assert _hindsight_axis_bank_id("repair-profile-a", "axis-a") != _hindsight_axis_bank_id(
        "repair-profile-b", "axis-a"
    )


def test_hindsight_memconflict_exchange_append_metadata_matches_frozen_arm_c(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "memconflict-metadata-history.json"
    history_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "sessions": [
                    {
                        "session_id": "session-metadata",
                        "order": 0,
                        "items": [
                            {
                                "role": "user",
                                "content": "first turn",
                                "timestamp": "2025-01-02T03:04:05+00:00",
                            },
                            {
                                "role": "assistant",
                                "content": "second turn",
                                "timestamp": "2025-01-02T03:04:06+00:00",
                            },
                        ],
                    }
                ],
                "question_history": {"question-0": ["session-metadata"]},
            }
        ),
        encoding="utf-8",
    )
    session = HindsightHistoryPlan.from_path(history_path).sessions[0]

    request = session.to_retain_requests(
        bank_id="synthetic-bank",
        context_label="MemConflict",
    )[0]

    metadata = request["metadata"]
    assert isinstance(metadata, Mapping)
    assert set(metadata) == {
        "retained_at",
        "message_count",
        "turn_index",
        "session_date",
    }
    assert metadata["message_count"] == "2"
    assert metadata["turn_index"] == "0"
    assert metadata["session_date"] == "2025-01-02T03:04:05+00:00"
    assert isinstance(metadata["retained_at"], str)
    assert str(metadata["retained_at"]).endswith("+00:00")


def test_hindsight_longmemeval_does_not_inherit_memconflict_retain_metadata(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "longmemeval-metadata-history.json"
    history_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "sessions": [
                    {
                        "session_id": "session-long",
                        "order": 0,
                        "items": [
                            {
                                "role": "user",
                                "content": "historical update",
                                "timestamp": "2025-01-02T03:04:05+00:00",
                            }
                        ],
                    }
                ],
                "question_history": {"question-0": ["session-long"]},
            }
        ),
        encoding="utf-8",
    )
    session = HindsightHistoryPlan.from_path(history_path).sessions[0]

    request = session.to_retain_requests(
        bank_id="synthetic-bank",
        context_label="LongMemEval",
    )[0]

    assert "metadata" not in request

def test_hindsight_preload_identity_does_not_retry_when_only_retained_at_changes(
    tmp_path: Path,
) -> None:
    live = _live_mapping()
    identity = freeze_experiment_identity(
        identity=_frozen_identity("memconflict", live),
        live_attestation=live,
    )
    question = DurableQuestion.from_content(
        "question-0",
        "synthetic question",
        session_id="question-0",
    )
    durable = DurableQuestionRun.start(
        artifact_root=tmp_path / "durable-preload",
        identity=identity,
        questions=(question,),
    )
    durable.begin_question(question.question_id)
    base_request = {
        "content": '[{"role":"user","content":"User: hello","timestamp":null}]',
        "context": "MemConflict dialogue session session-0",
        "timestamp": None,
        "document_id": "synthetic-bank_doc_session-0",
        "update_mode": "append",
        "metadata": {
            "retained_at": "2026-09-19T00:00:00+00:00",
            "message_count": "1",
            "turn_index": "0",
            "session_date": "None",
        },
    }
    assert durable.begin_hindsight_history_preload(
        question_id=question.question_id,
        bank_id="synthetic-bank",
        session_id="session-0",
        exchange_index=0,
        request=base_request,
    )
    durable.complete_hindsight_history_preload(
        question_id=question.question_id,
        bank_id="synthetic-bank",
        session_id="session-0",
        exchange_index=0,
        request=base_request,
    )

    changed_clock_request = json.loads(json.dumps(base_request))
    changed_clock_request["metadata"]["retained_at"] = "2026-09-19T00:10:00+00:00"
    assert not durable.begin_hindsight_history_preload(
        question_id=question.question_id,
        bank_id="synthetic-bank",
        session_id="session-0",
        exchange_index=0,
        request=changed_clock_request,
    )

    records = [
        json.loads(line)
        for line in (tmp_path / "durable-preload" / "hindsight-history-preloads.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [record["event"] for record in records] == ["started", "completed"]
    assert records[0]["request"] == base_request
    assert records[1]["request"] == base_request


def test_hindsight_consolidation_wait_is_scoped_per_history_session(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "multi-session-history.json"
    history_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "sessions": [
                    {
                        "session_id": "session-0",
                        "order": 0,
                        "items": [
                            {"role": "user", "content": "first", "timestamp": None},
                            {"role": "assistant", "content": "reply", "timestamp": None},
                        ],
                    },
                    {
                        "session_id": "session-1",
                        "order": 1,
                        "items": [
                            {"role": "user", "content": "second", "timestamp": None},
                            {"role": "assistant", "content": "reply 2", "timestamp": None},
                        ],
                    },
                ],
                "question_history": {"question-0": ["session-0", "session-1"]},
            }
        ),
        encoding="utf-8",
    )
    plan = HindsightHistoryPlan.from_path(history_path)
    lifecycle = _ComparatorLifecycle("repair-profile-waits")
    executor = HindsightComparatorExecutor(  # type: ignore[arg-type]
        lifecycle,
        _CommonAnswerModel(),  # type: ignore[arg-type]
    )
    context = ParticipantExecutionContext(
        axis_id="axis-waits",
        case={"benchmark": {"id": "memconflict"}},
        manifest={},
        question=DurableQuestion.from_content(
            "question-0",
            "synthetic question",
            session_id="question-0",
        ),
        prompt="synthetic question",
        participant_slot="serious_comparator",
        participant_identity=_participant_identity(
            "hindsight", revision="c" * 40, version="v0.10.0"
        ),
        frozen_identity=None,  # type: ignore[arg-type]
        live_attestation=None,  # type: ignore[arg-type]
        history=plan,
        durable_run=_PreloadJournal(),  # type: ignore[arg-type]
    )

    executor(context)

    assert len(lifecycle.retain_calls) == 2
    assert len(lifecycle.wait_calls) == 2



def test_common_answer_boundary_uses_frozen_prompt_and_one_generation() -> None:
    spec = type(
        "Spec",
        (),
        {"port": 8199, "expected_model_alias": "frozen-answer-model"},
    )()
    answer_model = CommonAnswerModelExecutor(spec)  # type: ignore[arg-type]
    client = _AnswerClient()
    answer_model.client = client  # type: ignore[assignment]
    context = ParticipantExecutionContext(
        axis_id="axis-a",
        case={"benchmark": {"id": "memconflict"}},
        manifest={},
        question=DurableQuestion.from_content(
            "question-0",
            "What changed?",
            session_id="session-0",
        ),
        prompt="What changed?",
        participant_slot="serious_comparator",
        participant_identity=_participant_identity(
            "hindsight", revision="c" * 40, version="v0.10.0"
        ),
        frozen_identity=None,  # type: ignore[arg-type]
        live_attestation=None,  # type: ignore[arg-type]
    )

    result = answer_model.answer(
        context,
        [{"memory": "the value changed", "created_at": "2025-01-02T12:00:00+00:00"}],
    )
    payload = client.calls[0][1]
    assert payload["model"] == "frozen-answer-model"
    assert payload["temperature"] == 0
    assert "top_p" not in payload
    assert payload["stream"] is False
    assert payload["messages"][0] == {
        "role": "system",
        "content": COMMON_ANSWER_SYSTEM_PROMPT,
    }
    assert payload["messages"][1] == {
        "role": "user",
        "content": (
            "Retrieved Memory Context:\nRetrieved memories:\n"
            "1. [2025-01-02T12:00:00+00:00] the value changed\n\n"
            "Question:\nWhat changed?\n\nAnswer:"
        ),
    }
    assert result.observation["tokens"]["model_call_count"] == 1
    assert result.request_evidence["boundary"] == "common_answer_model"


def test_hindsight_history_crash_after_retain_fails_closed_without_duplicate(
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
                                "content": "history before crash",
                                "timestamp": "2025-01-02T03:04:05+00:00",
                            },
                            {
                                "role": "assistant",
                                "content": "assistant history before crash",
                                "timestamp": "2025-01-02T03:04:06+00:00",
                            },
                        ],
                    }
                ],
                "question_history": {"question-0": ["session-0"]},
            }
        ),
        encoding="utf-8",
    )
    plan = HindsightHistoryPlan.from_path(history_path)
    live = _live_mapping()
    identity = freeze_experiment_identity(
        identity=_frozen_identity("memconflict", live),
        live_attestation=live,
    )
    question = DurableQuestion.from_content(
        "question-0",
        "synthetic question",
        session_id="question-0",
    )
    run_root = tmp_path / "durable-run"
    durable = DurableQuestionRun.start(
        artifact_root=run_root,
        identity=identity,
        questions=(question,),
    )
    durable.begin_question(question.question_id)

    class _CrashAfterRetain(_ComparatorLifecycle):
        def wait_for_consolidation(
            self,
            *,
            bank_id: str,
            pre_existing_pending_ids: set[str],
        ) -> Mapping[str, object]:
            raise RuntimeError("synthetic process stop after external retain")

    lifecycle = _CrashAfterRetain("repair-profile-crash")
    executor = HindsightComparatorExecutor(  # type: ignore[arg-type]
        lifecycle,
        _CommonAnswerModel(),  # type: ignore[arg-type]
    )
    context = ParticipantExecutionContext(
        axis_id="axis-crash",
        case={"benchmark": {"id": "memconflict"}},
        manifest={},
        question=question,
        prompt="synthetic question",
        participant_slot="serious_comparator",
        participant_identity=_participant_identity(
            "hindsight", revision="c" * 40, version="v0.10.0"
        ),
        frozen_identity=identity,
        live_attestation=None,  # type: ignore[arg-type]
        history=plan,
        durable_run=durable,
    )

    with pytest.raises(RuntimeError, match="synthetic process stop"):
        executor(context)
    durable.mark_process_exited()
    assert len(lifecycle.retain_calls) == 1

    with pytest.raises(
        ExactResumeError,
        match="Hindsight retain acknowledgement is ambiguous",
    ):
        DurableQuestionRun.resume(
            artifact_root=run_root,
            identity=identity,
            questions=(question,),
        )

    # The exact-resume attempt fails before a comparator is callable, so no
    # second provider retain can be issued.
    assert len(lifecycle.retain_calls) == 1


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


def test_history_plan_rejects_prefix_regression_in_campaign_question_order(
    tmp_path: Path,
) -> None:
    path = tmp_path / "regressing-history.json"
    path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "sessions": [
                    {
                        "session_id": "session-0",
                        "order": 0,
                        "items": [
                            {"role": "user", "content": "first", "timestamp": None}
                        ],
                    },
                    {
                        "session_id": "session-1",
                        "order": 1,
                        "items": [
                            {"role": "user", "content": "second", "timestamp": None}
                        ],
                    },
                ],
                "question_history": {
                    "Q_001": ["session-0", "session-1"],
                    "Q_002": ["session-0"],
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    plan = HindsightHistoryPlan.from_path(path)
    with pytest.raises(CampaignCarriageError, match="must not regress"):
        plan.validate_questions(["Q_001", "Q_002"])


class _ExactRCAdapter:
    def __init__(self) -> None:
        self.start_count = 0
        self.query_count = 0
        self.calls: list[dict[str, object]] = []

    def start(self) -> dict[str, object]:
        self.start_count += 1
        return {"status": "ready"}

    def query(self, **kwargs: object) -> dict[str, object]:
        self.query_count += 1
        self.calls.append(dict(kwargs))
        sessions = kwargs["sessions"]
        assert isinstance(sessions, list)
        return {
            "status": "ok",
            "model_call_count": 3,
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "external_evidence": {
                "answer": "synthetic exact RC answer",
                "adapter_mechanics": {"question_isolation": "fresh clone"},
            },
            "history_session_ids": [
                str(item["session_id"])
                for item in sessions
                if isinstance(item, Mapping)
            ],
            "new_history_session_count": 1,
            "new_history_pass2_calls": 1,
            "snapshot_fingerprint": "sha256:" + "3" * 64,
        }


def test_exact_rc_executor_uses_question_bounded_history_adapter(
    tmp_path: Path,
) -> None:
    path = tmp_path / "exact-rc-history.json"
    path.write_text(
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
                                "content": "history zero",
                                "timestamp": None,
                            }
                        ],
                    },
                    {
                        "session_id": "session-1",
                        "order": 1,
                        "items": [
                            {
                                "role": "assistant",
                                "content": "history one",
                                "timestamp": None,
                            }
                        ],
                    },
                ],
                "question_history": {
                    "Q_001": ["session-0"],
                    "Q_002": ["session-0", "session-1"],
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    plan = HindsightHistoryPlan.from_path(path)
    adapter = _ExactRCAdapter()
    executor = ExactRelayLMExecutor(adapter)

    def context(question_id: str, prompt: str) -> ParticipantExecutionContext:
        return ParticipantExecutionContext(
            axis_id="memconflict",
            case={"benchmark": {"id": "memconflict"}},
            manifest={},
            question=DurableQuestion.from_content(
                question_id,
                prompt,
                session_id=question_id,
            ),
            prompt=prompt,
            participant_slot="relaylm_exact_rc",
            participant_identity={},
            frozen_identity=None,  # type: ignore[arg-type]
            live_attestation=None,  # type: ignore[arg-type]
            history=plan,
            durable_run=None,
        )

    first = executor(context("Q_001", "question one"))
    second = executor(context("Q_002", "question two"))

    assert adapter.start_count == 1
    assert adapter.query_count == 2
    assert [
        [item["session_id"] for item in call["sessions"]]
        for call in adapter.calls
    ] == [["session-0"], ["session-0", "session-1"]]
    assert first.semantic_generation_count == 3
    assert first.observation["tokens"]["model_call_count"] == 3
    assert second.semantic_generation_count == 3
    evidence = first.request_evidence[0]
    assert evidence["boundary"] == "relaylm_exact_rc_history_adapter"
    assert evidence["history_session_ids"] == ["session-0"]
    assert evidence["adapter_query_evidence"]["answer"] == (
        "synthetic exact RC answer"
    )
