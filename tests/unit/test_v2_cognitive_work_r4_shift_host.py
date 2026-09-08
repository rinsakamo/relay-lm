from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Mapping

import pytest

from tools.v2_cognitive_work_r0 import ExecutionBinding
from tools import v2_cognitive_work_r4_shift_preregistration as r4
from tools import v2_cognitive_work_structured_output_qualification as sopq
from tools.v2_cognitive_work_r4_shift_host import (
    BANK_EVIDENCE_NAME,
    FROZEN_R4_PREREGISTRATION_COMMIT,
    FROZEN_R4_PREREGISTRATION_DIGEST,
    FROZEN_R4_ROOT_SEED,
    MANIFEST_NAME,
    REQUEST_EVIDENCE_NAME,
    RESULT_NAME,
    STATE_NAME,
    CognitiveWorkR4ShiftHostError,
    R4ShiftExecutionAuthorization,
    R4ShiftHostIdentity,
    run_r4_shift_host_campaign,
)


class ScriptedStructuredFakeClient:
    def __init__(self, responses: list[str], *, fail_at: int | None = None) -> None:
        self.responses = list(responses)
        self.fail_at = fail_at
        self.calls: list[
            tuple[tuple[dict[str, str], ...], Mapping[str, object]]
        ] = []

    def complete(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        response_format: Mapping[str, object],
    ) -> sopq.StructuredOutputCompletion:
        index = len(self.calls)
        self.calls.append((messages, response_format))
        if self.fail_at is not None and index == self.fail_at:
            raise sopq.StructuredOutputQualificationError("synthetic provider failure")
        if index >= len(self.responses):
            raise AssertionError("unexpected 101st R4 provider call")
        return sopq.StructuredOutputCompletion(
            content=self.responses[index],
            input_tokens=10 + index % 3,
            output_tokens=2,
            response_id=f"fake-r4-shift-{index:03d}",
            finish_reason="stop",
        )


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "RelayLM Test")
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(root, "add", "seed.txt")
    _git(root, "commit", "-m", "seed")
    return root, _git(root, "rev-parse", "HEAD"), _git(root, "rev-parse", "HEAD^{tree}")


def _binding(**overrides: object) -> ExecutionBinding:
    values: dict[str, object] = {
        "model_identity": "model@artifact",
        "runtime_identity": "runtime@build",
        "hardware_identity": "gpu@class",
        "tokenizer_identity": "tokenizer@revision",
        "template_identity": "template@digest",
        "context_limit": 8192,
        "decoding_identity": "stream=false;response_format=json_schema",
        "reasoning_identity": "reasoning=default-on;override=omitted",
    }
    values.update(overrides)
    return ExecutionBinding(**values)  # type: ignore[arg-type]


def _identity(repo: Path, binding: ExecutionBinding | None = None) -> R4ShiftHostIdentity:
    return R4ShiftHostIdentity(
        repository_commit=_git(repo, "rev-parse", "HEAD"),
        repository_tree=_git(repo, "rev-parse", "HEAD^{tree}"),
        execution=binding or _binding(),
    )


def _authorization(
    identity: R4ShiftHostIdentity,
    *,
    authorized: bool = True,
) -> R4ShiftExecutionAuthorization:
    return R4ShiftExecutionAuthorization(
        authorization_id="r4-shift-deterministic-test-only",
        execution_repository_commit=identity.repository_commit,
        preregistration_commit=FROZEN_R4_PREREGISTRATION_COMMIT,
        physical_execution_authorized=authorized,
    )


def _adaptive_operation(task: r4.R4ShiftTask) -> str:
    return {
        "EASY_SATURATED": "ZERO",
        "DEPTH_BENEFICIAL": "THINK",
        "RETRIEVAL_BENEFICIAL": "RETRIEVE",
        "OBSERVATION_BENEFICIAL": "OBSERVE",
        "UNCERTAINTY_TRAP": "ZERO",
    }[task.hidden_regime]


def _script() -> tuple[list[str], tuple[r4.PlannedProviderCall, ...]]:
    preregistration = r4.build_preregistration(FROZEN_R4_PREREGISTRATION_COMMIT)
    tasks = {task.task_id: task for task in preregistration.tasks}
    plan = r4.physical_call_plan(preregistration.tasks)
    responses: list[str] = []
    for item in plan:
        task = tasks[item.task_id]
        if item.role == "BASE":
            answer = (
                task.expected_answer
                if task.hidden_regime in {"EASY_SATURATED", "UNCERTAINTY_TRAP"}
                else "WRONG"
            )
            responses.append(json.dumps({"answer": answer}))
        elif item.role == "A2_ALLOCATE":
            responses.append(json.dumps({"operation": _adaptive_operation(task)}))
        else:
            assert item.operation is not None
            correct_operation = {
                "EASY_SATURATED": "ZERO",
                "DEPTH_BENEFICIAL": "THINK",
                "RETRIEVAL_BENEFICIAL": "RETRIEVE",
                "OBSERVATION_BENEFICIAL": "OBSERVE",
                "UNCERTAINTY_TRAP": "ZERO",
            }[task.hidden_regime]
            answer = task.expected_answer if item.operation == correct_operation else "WRONG"
            responses.append(json.dumps({"answer": answer}))
    assert len(responses) == 100
    return responses, plan


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        assert isinstance(value, dict)
        result.append(value)
    return result


def test_r4_host_hard_binds_merged_preregistration():
    preregistration = r4.build_preregistration(FROZEN_R4_PREREGISTRATION_COMMIT)
    assert preregistration.root_seed == FROZEN_R4_ROOT_SEED
    assert preregistration.digest == FROZEN_R4_PREREGISTRATION_DIGEST
    assert preregistration.budget.physical_provider_call_max == 100
    assert len(preregistration.tasks) == 20
    with pytest.raises(CognitiveWorkR4ShiftHostError, match="frozen shift preregistration"):
        R4ShiftExecutionAuthorization(
            authorization_id="wrong-prereg",
            execution_repository_commit="abc",
            preregistration_commit="0" * 40,
            physical_execution_authorized=True,
        )


def test_r4_complete_fake_campaign_is_exact_100_calls_and_qualified_transport(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, plan = _script()
    client = ScriptedStructuredFakeClient(responses)
    probes: list[int] = []

    def probe() -> ExecutionBinding:
        probes.append(1)
        return binding

    result = run_r4_shift_host_campaign(
        artifact_root=artifact,
        repository_root=repo,
        identity=identity,
        authorization=_authorization(identity),
        live_binding_probe=probe,
        client=client,
        run_id="r4-shift-fake-complete",
    )

    assert result.status == "COMPLETED"
    assert result.provider_attempts == 100
    assert result.provider_completions == 100
    assert result.plan_cursor == 100
    assert result.physical_cost.calls == 100
    assert result.category == "ADAPTIVE_TRANSFER_SIGNAL"
    assert len(client.calls) == 100
    assert len(probes) == 101
    assert all(len(items) == 20 for items in result.outcomes.values())

    for index, item in enumerate(plan):
        _, response_format = client.calls[index]
        assert response_format == r4.response_format_for_call(item)
    assert sum(
        response_format == sopq.response_format_for("answer")
        for _, response_format in client.calls
    ) == 80
    assert sum(
        response_format == sopq.response_format_for("operation")
        for _, response_format in client.calls
    ) == 20

    manifest = _read_json(artifact / MANIFEST_NAME)
    state = _read_json(artifact / STATE_NAME)
    durable = _read_json(artifact / RESULT_NAME)
    bank = _read_jsonl(artifact / BANK_EVIDENCE_NAME)
    evidence = _read_jsonl(artifact / REQUEST_EVIDENCE_NAME)

    assert manifest["preregistration"]["commit"] == FROZEN_R4_PREREGISTRATION_COMMIT  # type: ignore[index]
    assert manifest["preregistration"]["root_seed"] == FROZEN_R4_ROOT_SEED  # type: ignore[index]
    assert manifest["preregistration"]["digest"] == FROZEN_R4_PREREGISTRATION_DIGEST  # type: ignore[index]
    assert state["status"] == "COMPLETED"
    assert state["plan_cursor"] == 100
    assert len(bank) == 20
    assert all(item["authority"] == "evaluator_only" for item in bank)
    assert all(item["a1_operation"] == "RETRIEVE" for item in bank)
    assert len(evidence) == 200
    assert durable["claim_status"] == "R4_SHIFT_PREREGISTERED_PHYSICAL_RESULT"
    assert durable["interpretation"]["category"] == "ADAPTIVE_TRANSFER_SIGNAL"  # type: ignore[index]
    assert durable["operation_diagnostics"]["a1_selection_counts"] == {"RETRIEVE": 20}  # type: ignore[index]
    assert durable["correctness"]["A2"]["count"] == 20  # type: ignore[index]
    assert durable["correctness"]["A3"]["count"] == 20  # type: ignore[index]
    assert durable["correctness"]["A1"]["count"] == 4  # type: ignore[index]


def test_r4_requests_quarantine_hidden_labels_and_unpurchased_packets(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    preregistration = r4.build_preregistration(FROZEN_R4_PREREGISTRATION_COMMIT)
    responses, plan = _script()
    client = ScriptedStructuredFakeClient(responses)

    run_r4_shift_host_campaign(
        artifact_root=artifact,
        repository_root=repo,
        identity=identity,
        authorization=_authorization(identity),
        live_binding_probe=lambda: binding,
        client=client,
        run_id="r4-shift-leak-check",
    )

    tasks = {task.task_id: task for task in preregistration.tasks}
    serialized = [json.dumps(messages, ensure_ascii=False) for messages, _ in client.calls]
    for index, item in enumerate(plan):
        task = tasks[item.task_id]
        assert task.hidden_regime not in serialized[index]
        if item.role in {"BASE", "A2_ALLOCATE"}:
            assert task.retrieval_packet not in serialized[index]
            assert task.observation_packet not in serialized[index]
        if item.role == "BANK" and item.operation == "THINK":
            assert task.retrieval_packet not in serialized[index]
            assert task.observation_packet not in serialized[index]
        if item.role == "BANK" and item.operation == "RETRIEVE":
            assert task.retrieval_packet in serialized[index]
            assert task.observation_packet not in serialized[index]
        if item.role == "BANK" and item.operation == "OBSERVE":
            assert task.observation_packet in serialized[index]
            assert task.retrieval_packet not in serialized[index]


def test_r4_false_authorization_fails_before_artifact_and_provider(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    client = ScriptedStructuredFakeClient(responses)

    with pytest.raises(CognitiveWorkR4ShiftHostError, match="not authorized"):
        run_r4_shift_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity, authorized=False),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r4-shift-unauthorized",
        )
    assert not artifact.exists()
    assert client.calls == []


def test_r4_provider_failure_preserves_attempt_and_no_result(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    client = ScriptedStructuredFakeClient(responses, fail_at=5)

    with pytest.raises(CognitiveWorkR4ShiftHostError, match="provider failure"):
        run_r4_shift_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r4-shift-provider-failure",
        )

    state = _read_json(artifact / STATE_NAME)
    assert len(client.calls) == 6
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 6
    assert state["provider_completions"] == 5
    assert state["plan_cursor"] == 5
    assert state["failure"]["kind"] == "provider_failure"  # type: ignore[index]
    assert not (artifact / RESULT_NAME).exists()


def test_r4_wrapper_protocol_failure_stays_incomplete(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    responses[2] = '```json\n{"answer":"1"}\n```'
    client = ScriptedStructuredFakeClient(responses)

    with pytest.raises(CognitiveWorkR4ShiftHostError, match="strict protocol"):
        run_r4_shift_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r4-shift-wrapper-failure",
        )

    state = _read_json(artifact / STATE_NAME)
    assert len(client.calls) == 3
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 3
    assert state["provider_completions"] == 3
    assert state["plan_cursor"] == 3
    assert state["failure"]["kind"] == "protocol_invalid"  # type: ignore[index]
    assert not (artifact / RESULT_NAME).exists()
    assert not (artifact / BANK_EVIDENCE_NAME).exists()


def test_r4_binding_drift_stops_before_affected_attempt(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    drifted = _binding(runtime_identity="runtime@drifted")
    identity = _identity(repo, binding)
    responses, _ = _script()
    client = ScriptedStructuredFakeClient(responses)
    probes = 0

    def probe() -> ExecutionBinding:
        nonlocal probes
        probes += 1
        return drifted if probes == 3 else binding

    with pytest.raises(CognitiveWorkR4ShiftHostError, match="binding drift"):
        run_r4_shift_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=probe,
            client=client,
            run_id="r4-shift-binding-drift",
        )

    state = _read_json(artifact / STATE_NAME)
    assert len(client.calls) == 1
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 1
    assert state["provider_completions"] == 1
    assert state["plan_cursor"] == 1
    assert state["failure"]["kind"] == "binding_drift"  # type: ignore[index]
    assert not (artifact / RESULT_NAME).exists()


def test_r4_dirty_repo_and_artifact_collision_fail_closed(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()

    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    client = ScriptedStructuredFakeClient(responses)
    with pytest.raises(CognitiveWorkR4ShiftHostError, match="dirty"):
        run_r4_shift_host_campaign(
            artifact_root=tmp_path / "dirty-artifact",
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r4-shift-dirty",
        )
    assert client.calls == []

    _git(repo, "add", "dirty.txt")
    _git(repo, "commit", "-m", "clean-for-collision")
    identity = _identity(repo, binding)
    artifact = tmp_path / "collision-artifact"
    artifact.mkdir()
    (artifact / "occupied.txt").write_text("occupied\n", encoding="utf-8")
    client = ScriptedStructuredFakeClient(responses)
    with pytest.raises(CognitiveWorkR4ShiftHostError):
        run_r4_shift_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r4-shift-collision",
        )
    assert client.calls == []
    assert not (artifact / RESULT_NAME).exists()
