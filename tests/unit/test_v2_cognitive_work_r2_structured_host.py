from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Mapping

import pytest

from tools.v2_cognitive_work_r0 import ExecutionBinding
from tools import v2_cognitive_work_structured_output_qualification as sopq
from tools.v2_cognitive_work_r2_structured_host import (
    ANSWER_PROTOCOL_VERSION,
    BANK_EVIDENCE_NAME,
    FROZEN_STRUCTURED_PREREGISTRATION_COMMIT,
    FROZEN_STRUCTURED_PREREGISTRATION_DIGEST,
    FROZEN_STRUCTURED_ROOT_SEED,
    MANIFEST_NAME,
    REQUEST_EVIDENCE_NAME,
    RESULT_NAME,
    STATE_NAME,
    CognitiveWorkR2StructuredHostError,
    R2StructuredExecutionAuthorization,
    R2StructuredHostIdentity,
    run_r2_structured_host_campaign,
)
from tools.v2_cognitive_work_r2_structured_preregistration import (
    PlannedProviderCall,
    R2Task,
    build_preregistration,
    physical_call_plan,
    response_format_for_call,
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
            raise AssertionError("unexpected 137th structured provider call")
        return sopq.StructuredOutputCompletion(
            content=self.responses[index],
            input_tokens=10 + index % 3,
            output_tokens=2,
            response_id=f"fake-r2-structured-{index:03d}",
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


def _identity(repo: Path, binding: ExecutionBinding | None = None) -> R2StructuredHostIdentity:
    return R2StructuredHostIdentity(
        repository_commit=_git(repo, "rev-parse", "HEAD"),
        repository_tree=_git(repo, "rev-parse", "HEAD^{tree}"),
        execution=binding or _binding(),
    )


def _authorization(
    identity: R2StructuredHostIdentity,
    *,
    authorized: bool = True,
) -> R2StructuredExecutionAuthorization:
    return R2StructuredExecutionAuthorization(
        authorization_id="structured-deterministic-test-only",
        execution_repository_commit=identity.repository_commit,
        preregistration_commit=FROZEN_STRUCTURED_PREREGISTRATION_COMMIT,
        physical_execution_authorized=authorized,
    )


def _base_answer(task: R2Task) -> str:
    if task.hidden_regime in {"EASY_SATURATED", "UNCERTAINTY_TRAP"}:
        return task.expected_answer
    return "UNKNOWN"


def _adaptive_operation(task: R2Task) -> str:
    if task.retrieval_available:
        return "RETRIEVE"
    if task.observation_available:
        return "OBSERVE"
    if task.hidden_regime == "DEPTH_BENEFICIAL":
        return "THINK"
    return "ZERO"


def _bank_answer(task: R2Task, operation: str) -> str:
    if operation in {"RETRIEVE", "OBSERVE"}:
        return task.expected_answer
    if task.hidden_regime in {"EASY_SATURATED", "DEPTH_BENEFICIAL"}:
        return task.expected_answer
    if task.hidden_regime == "UNCERTAINTY_TRAP":
        return "CERTAIN-GUESS"
    return "UNKNOWN"


def _script() -> tuple[list[str], tuple[PlannedProviderCall, ...]]:
    preregistration = build_preregistration(FROZEN_STRUCTURED_PREREGISTRATION_COMMIT)
    tasks = {task.task_id: task for task in preregistration.tasks}
    plan = physical_call_plan(preregistration.tasks)
    responses: list[str] = []
    for item in plan:
        task = tasks[item.task_id]
        if item.role == "BASE":
            responses.append(json.dumps({"answer": _base_answer(task)}))
        elif item.role == "A2_ALLOCATE":
            responses.append(json.dumps({"operation": _adaptive_operation(task)}))
        else:
            assert item.operation is not None
            responses.append(json.dumps({"answer": _bank_answer(task, item.operation)}))
    assert len(responses) == 136
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


def test_structured_host_hard_binds_merged_preregistration_and_transport():
    preregistration = build_preregistration(FROZEN_STRUCTURED_PREREGISTRATION_COMMIT)
    assert preregistration.root_seed == FROZEN_STRUCTURED_ROOT_SEED
    assert preregistration.digest == FROZEN_STRUCTURED_PREREGISTRATION_DIGEST
    assert preregistration.budget.physical_provider_call_max == 136
    assert ANSWER_PROTOCOL_VERSION == "qualified-json-schema-string-v3"
    assert sopq.QUALIFICATION_VERSION == "relaylm2-cognitive-work-sopq-v1"
    with pytest.raises(CognitiveWorkR2StructuredHostError, match="frozen preregistration"):
        R2StructuredExecutionAuthorization(
            authorization_id="wrong-version",
            execution_repository_commit="abc",
            preregistration_commit="0" * 40,
            physical_execution_authorized=True,
        )


def test_structured_complete_fake_campaign_uses_exact_schema_per_call(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, plan = _script()
    client = ScriptedStructuredFakeClient(responses)
    probe_calls: list[int] = []

    def probe() -> ExecutionBinding:
        probe_calls.append(1)
        return binding

    result = run_r2_structured_host_campaign(
        artifact_root=artifact,
        repository_root=repo,
        identity=identity,
        authorization=_authorization(identity),
        live_binding_probe=probe,
        client=client,
        run_id="r2-structured-fake-complete",
    )

    assert result.status == "COMPLETED"
    assert result.provider_attempts == 136
    assert result.provider_completions == 136
    assert result.physical_cost.calls == 136
    assert result.category == "ADAPTIVE_SIGNAL"
    assert len(client.calls) == 136
    assert len(probe_calls) == 137
    assert all(len(items) == 40 for items in result.outcomes.values())

    for index, item in enumerate(plan):
        _, response_format = client.calls[index]
        assert response_format == response_format_for_call(item)
    assert sum(
        response_format == sopq.response_format_for("answer")
        for _, response_format in client.calls
    ) == 96
    assert sum(
        response_format == sopq.response_format_for("operation")
        for _, response_format in client.calls
    ) == 40

    manifest = _read_json(artifact / MANIFEST_NAME)
    state = _read_json(artifact / STATE_NAME)
    durable = _read_json(artifact / RESULT_NAME)
    bank = _read_jsonl(artifact / BANK_EVIDENCE_NAME)
    evidence = _read_jsonl(artifact / REQUEST_EVIDENCE_NAME)

    assert manifest["preregistration"]["commit"] == FROZEN_STRUCTURED_PREREGISTRATION_COMMIT  # type: ignore[index]
    assert manifest["preregistration"]["root_seed"] == FROZEN_STRUCTURED_ROOT_SEED  # type: ignore[index]
    assert manifest["preregistration"]["digest"] == FROZEN_STRUCTURED_PREREGISTRATION_DIGEST  # type: ignore[index]
    assert manifest["structured_transport"]["answer_response_format_digest"] == sopq.ANSWER_RESPONSE_FORMAT_DIGEST  # type: ignore[index]
    assert state["status"] == "COMPLETED"
    assert state["plan_cursor"] == 136
    assert len(bank) == 40
    assert all(item["authority"] == "evaluator_only" for item in bank)
    assert len(evidence) == 272
    assert durable["claim_status"] == "R2_STRUCTURED_PREREGISTERED_PHYSICAL_RESULT"
    assert durable["interpretation"]["category"] == "ADAPTIVE_SIGNAL"  # type: ignore[index]

    completed = [item for item in evidence if item["status"] == "COMPLETED"]
    assert [(x["task_id"], x["role"], x["operation"]) for x in completed] == [
        (x.task_id, x.role, x.operation) for x in plan
    ]
    assert all("response_format" in item["transport"] for item in evidence)  # type: ignore[operator]


def test_structured_requests_preserve_evaluator_and_packet_quarantine(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    preregistration = build_preregistration(FROZEN_STRUCTURED_PREREGISTRATION_COMMIT)
    responses, plan = _script()
    client = ScriptedStructuredFakeClient(responses)

    run_r2_structured_host_campaign(
        artifact_root=artifact,
        repository_root=repo,
        identity=identity,
        authorization=_authorization(identity),
        live_binding_probe=lambda: binding,
        client=client,
        run_id="r2-structured-leak-check",
    )

    task_by_id = {task.task_id: task for task in preregistration.tasks}
    serialized = [json.dumps(messages, ensure_ascii=False) for messages, _ in client.calls]
    for index, item in enumerate(plan):
        task = task_by_id[item.task_id]
        if item.role == "A2_ALLOCATE":
            payload = json.loads(client.calls[index][0][1]["content"])
            assert "hidden_regime" not in payload
            assert "expected_answer" not in payload
            assert task.hidden_regime not in serialized[index]
            if task.retrieval_packet is not None:
                assert task.retrieval_packet not in serialized[index]
            if task.observation_packet is not None:
                assert task.observation_packet not in serialized[index]

    for task in preregistration.tasks:
        if task.retrieval_packet is not None:
            indexes = [i for i, value in enumerate(serialized) if task.retrieval_packet in value]
            expected = next(
                i for i, item in enumerate(plan)
                if item.task_id == task.task_id and item.role == "BANK" and item.operation == "RETRIEVE"
            )
            assert indexes == [expected]
        if task.observation_packet is not None:
            indexes = [i for i, value in enumerate(serialized) if task.observation_packet in value]
            expected = next(
                i for i, item in enumerate(plan)
                if item.task_id == task.task_id and item.role == "BANK" and item.operation == "OBSERVE"
            )
            assert indexes == [expected]


def test_structured_provider_failure_preserves_attempt_and_no_result(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    client = ScriptedStructuredFakeClient(responses, fail_at=4)

    with pytest.raises(CognitiveWorkR2StructuredHostError, match="provider failure"):
        run_r2_structured_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-structured-provider-failure",
        )

    state = _read_json(artifact / STATE_NAME)
    assert len(client.calls) == 5
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 5
    assert state["provider_completions"] == 4
    assert state["plan_cursor"] == 4
    assert state["failure"]["kind"] == "provider_failure"  # type: ignore[index]
    assert not (artifact / RESULT_NAME).exists()


def test_structured_wrapper_protocol_failure_stays_incomplete(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    responses[2] = '```json\n{"answer":"1"}\n```'
    client = ScriptedStructuredFakeClient(responses)

    with pytest.raises(CognitiveWorkR2StructuredHostError, match="strict protocol"):
        run_r2_structured_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-structured-wrapper-failure",
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


def test_structured_binding_drift_stops_before_affected_attempt(tmp_path: Path):
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

    with pytest.raises(CognitiveWorkR2StructuredHostError, match="binding drift"):
        run_r2_structured_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=probe,
            client=client,
            run_id="r2-structured-binding-drift",
        )

    state = _read_json(artifact / STATE_NAME)
    assert len(client.calls) == 1
    assert state["provider_attempts"] == 1
    assert state["provider_completions"] == 1
    assert state["plan_cursor"] == 1
    assert state["failure"]["kind"] == "binding_drift"  # type: ignore[index]
    assert not (artifact / RESULT_NAME).exists()


def test_structured_dirty_repo_and_artifact_collision_fail_before_provider(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    client = ScriptedStructuredFakeClient(responses)
    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(CognitiveWorkR2StructuredHostError, match="dirty"):
        run_r2_structured_host_campaign(
            artifact_root=tmp_path / "artifact-dirty",
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-structured-dirty",
        )
    assert client.calls == []

    (repo / "dirty.txt").unlink()
    artifact = tmp_path / "artifact-collision"
    artifact.mkdir()
    (artifact / "occupied.txt").write_text("occupied\n", encoding="utf-8")
    with pytest.raises(CognitiveWorkR2StructuredHostError):
        run_r2_structured_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-structured-collision",
        )
    assert client.calls == []


def test_structured_authorization_is_explicit_and_fail_closed(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    client = ScriptedStructuredFakeClient(responses)

    with pytest.raises(CognitiveWorkR2StructuredHostError, match="not authorized"):
        run_r2_structured_host_campaign(
            artifact_root=tmp_path / "artifact",
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity, authorized=False),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-structured-not-authorized",
        )
    assert client.calls == []
