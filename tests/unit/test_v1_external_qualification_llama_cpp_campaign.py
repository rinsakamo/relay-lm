from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from tools.external_qualification import DurableQuestion
from tools.v1_external_qualification_llama_cpp_campaign import (
    CAMPAIGN_TARGET,
    CampaignCarriageError,
    CampaignDescriptor,
    ParticipantExecutionContext,
    ParticipantExecutionResult,
    ParticipantExecutors,
    run_campaign,
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
            "expected_build_info": "build-a" + "a" * 40,
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


def _controller_parts(
    descriptor: CampaignDescriptor,
    session: _Session,
    seen: list[ParticipantExecutionContext],
) -> dict[str, Any]:
    def factory(spec: Any, evidence_root: Path) -> _Session:
        return session

    def executor(context: ParticipantExecutionContext) -> ParticipantExecutionResult:
        seen.append(context)
        return ParticipantExecutionResult(
            slot=context.participant_slot,
            observation=_observation(),
        )

    probe = _Probe(_health())
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
    assert receipt["counters"] == {
        "semantic_generation_count": 0,
        "benchmark_question_count": 2,
        "answer_model_generation_count": 0,
        "judge_call_count": 0,
        "scientific_durable_run_completion_count": 2,
    }
    assert receipt["SCIENTIFIC_SPEND"] == "UNSPENT"
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
