from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_work_r0 import ExecutionBinding
from tools.v2_cognitive_work_r2_host import (
    BANK_EVIDENCE_NAME,
    FROZEN_PREREGISTRATION_COMMIT,
    FROZEN_ROOT_SEED,
    MANIFEST_NAME,
    REQUEST_EVIDENCE_NAME,
    RESULT_NAME,
    STATE_NAME,
    CognitiveWorkR2HostError,
    R2ExecutionAuthorization,
    R2HostIdentity,
    run_r2_host_campaign,
)
from tools.v2_cognitive_work_r2_preregistration import (
    PlannedProviderCall,
    R2Task,
    build_preregistration,
    physical_call_plan,
)


class ScriptedFakeClient:
    def __init__(
        self,
        responses: list[str],
        *,
        fail_at: int | None = None,
    ) -> None:
        self.responses = list(responses)
        self.fail_at = fail_at
        self.calls: list[tuple[dict[str, str], ...]] = []

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        index = len(self.calls)
        self.calls.append(messages)
        if self.fail_at is not None and index == self.fail_at:
            raise StructureProposalError("synthetic provider failure")
        if index >= len(self.responses):
            raise AssertionError("unexpected 137th provider call")
        return ExperimentCompletion(
            content=self.responses[index],
            input_tokens=10 + index % 3,
            output_tokens=2,
            response_id=f"fake-r2-{index:03d}",
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
        "decoding_identity": "temperature=0;top_p=1",
        "reasoning_identity": "reasoning=off",
    }
    values.update(overrides)
    return ExecutionBinding(**values)  # type: ignore[arg-type]


def _identity(repo: Path, binding: ExecutionBinding | None = None) -> R2HostIdentity:
    return R2HostIdentity(
        repository_commit=_git(repo, "rev-parse", "HEAD"),
        repository_tree=_git(repo, "rev-parse", "HEAD^{tree}"),
        execution=binding or _binding(),
    )


def _authorization(identity: R2HostIdentity, *, authorized: bool = True):
    return R2ExecutionAuthorization(
        authorization_id="deterministic-test-only",
        execution_repository_commit=identity.repository_commit,
        preregistration_commit=FROZEN_PREREGISTRATION_COMMIT,
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
    preregistration = build_preregistration(FROZEN_PREREGISTRATION_COMMIT)
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
            responses.append(
                json.dumps({"answer": _bank_answer(task, item.operation)})
            )
    assert len(responses) == 136
    return responses, plan


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        assert isinstance(value, dict)
        result.append(value)
    return result


def test_r2_host_consumes_exact_frozen_preregistration_and_136_call_plan():
    preregistration = build_preregistration(FROZEN_PREREGISTRATION_COMMIT)
    assert preregistration.root_seed == FROZEN_ROOT_SEED
    assert preregistration.budget.physical_provider_call_max == 136
    assert preregistration.budget.bank_provider_call_max == 96
    assert preregistration.budget.a2_allocator_call_max == 40
    assert preregistration.budget.aggregate_input_token_ceiling is None
    assert preregistration.budget.aggregate_output_token_ceiling is None
    plan = physical_call_plan(preregistration.tasks)
    assert len(plan) == 136
    assert sum(item.role == "BASE" for item in plan) == 40
    assert sum(item.role == "A2_ALLOCATE" for item in plan) == 40
    assert sum(item.role == "BANK" and item.operation == "THINK" for item in plan) == 40
    assert sum(item.role == "BANK" and item.operation == "RETRIEVE" for item in plan) == 8
    assert sum(item.role == "BANK" and item.operation == "OBSERVE" for item in plan) == 8


def test_r2_complete_fake_campaign_uses_exact_plan_and_shared_bank(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, plan = _script()
    client = ScriptedFakeClient(responses)
    probe_calls: list[int] = []

    def probe() -> ExecutionBinding:
        probe_calls.append(1)
        return binding

    result = run_r2_host_campaign(
        artifact_root=artifact,
        repository_root=repo,
        identity=identity,
        authorization=_authorization(identity),
        live_binding_probe=probe,
        client=client,
        run_id="r2-fake-complete",
    )

    assert result.status == "COMPLETED"
    assert result.citable is True
    assert result.provider_attempts == 136
    assert result.provider_completions == 136
    assert result.physical_cost.calls == 136
    assert result.physical_cost.retrieval_units == 8
    assert result.physical_cost.observation_units == 8
    assert result.category == "ADAPTIVE_SIGNAL"
    assert len(client.calls) == 136
    assert len(probe_calls) == 137  # preflight + one fresh probe per provider attempt
    assert client.responses[135]  # script had exactly 136 declared responses

    assert len(result.outcomes["A0"]) == 40
    assert len(result.outcomes["A1"]) == 40
    assert len(result.outcomes["A2"]) == 40
    assert len(result.outcomes["A3"]) == 40
    assert sum(item.correct for item in result.outcomes["A2"]) == 40
    assert sum(item.correct for item in result.outcomes["A1"]) == 32
    assert sum(item.correct for item in result.outcomes["A0"]) == 16
    assert sum(item.correct for item in result.outcomes["A3"]) == 40

    assert result.arm_resource_totals["A0"].calls == 80
    assert result.arm_resource_totals["A1"].calls == 56
    assert result.arm_resource_totals["A2"].calls == 104
    assert result.arm_resource_totals["A2"].retrieval_units == 8
    assert result.arm_resource_totals["A2"].observation_units == 8

    manifest = _read_json(artifact / MANIFEST_NAME)
    state = _read_json(artifact / STATE_NAME)
    durable = _read_json(artifact / RESULT_NAME)
    bank = _read_jsonl(artifact / BANK_EVIDENCE_NAME)
    request_evidence = _read_jsonl(artifact / REQUEST_EVIDENCE_NAME)

    assert manifest["preregistration"]["commit"] == FROZEN_PREREGISTRATION_COMMIT  # type: ignore[index]
    assert manifest["preregistration"]["root_seed"] == FROZEN_ROOT_SEED  # type: ignore[index]
    assert manifest["preregistration"]["call_plan_size"] == 136  # type: ignore[index]
    assert manifest["budget"]["aggregate_input_token_ceiling"] is None  # type: ignore[index]
    assert manifest["budget"]["aggregate_output_token_ceiling"] is None  # type: ignore[index]
    assert state["status"] == "COMPLETED"
    assert state["provider_attempts"] == 136
    assert state["provider_completions"] == 136
    assert len(bank) == 40
    assert len(request_evidence) == 272  # attempt + completion for every physical call
    assert durable["interpretation"]["category"] == "ADAPTIVE_SIGNAL"  # type: ignore[index]
    assert durable["hard_constraint_violations"] == 0
    assert durable["protocol_invalid_count"] == 0

    recomputed = {
        arm: [bool(item["outcomes"][arm]["correct"]) for item in bank]  # type: ignore[index]
        for arm in ("A0", "A1", "A2", "A3")
    }
    assert durable["correctness"] == recomputed

    # The durable request sequence itself is an exact replayable declaration of the plan.
    completed = [item for item in request_evidence if item["status"] == "COMPLETED"]
    assert [
        (item["task_id"], item["role"], item["operation"]) for item in completed
    ] == [(item.task_id, item.role, item.operation) for item in plan]


def test_r2_allocator_messages_never_receive_evaluator_or_bank_truth(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    preregistration = build_preregistration(FROZEN_PREREGISTRATION_COMMIT)
    responses, plan = _script()
    client = ScriptedFakeClient(responses)

    run_r2_host_campaign(
        artifact_root=artifact,
        repository_root=repo,
        identity=identity,
        authorization=_authorization(identity),
        live_binding_probe=lambda: binding,
        client=client,
        run_id="r2-leak-check",
    )

    task_by_id = {task.task_id: task for task in preregistration.tasks}
    for index, item in enumerate(plan):
        call = client.calls[index]
        serialized = json.dumps(call, ensure_ascii=False)
        task = task_by_id[item.task_id]
        if item.role == "A2_ALLOCATE":
            payload = json.loads(call[1]["content"])
            assert set(payload) == {
                "task_id",
                "prompt",
                "retrieval_available",
                "observation_available",
                "base_answer",
                "legal_operations",
            }
            assert task.hidden_regime not in serialized
            if task.retrieval_packet is not None:
                assert task.retrieval_packet not in serialized
            if task.observation_packet is not None:
                assert task.observation_packet not in serialized

    for task in preregistration.tasks:
        serialized_calls = [json.dumps(call, ensure_ascii=False) for call in client.calls]
        if task.retrieval_packet is not None:
            indexes = [
                index
                for index, value in enumerate(serialized_calls)
                if task.retrieval_packet in value
            ]
            expected_index = next(
                index
                for index, item in enumerate(plan)
                if item.task_id == task.task_id
                and item.role == "BANK"
                and item.operation == "RETRIEVE"
            )
            assert indexes == [expected_index]
        if task.observation_packet is not None:
            indexes = [
                index
                for index, value in enumerate(serialized_calls)
                if task.observation_packet in value
            ]
            expected_index = next(
                index
                for index, item in enumerate(plan)
                if item.task_id == task.task_id
                and item.role == "BANK"
                and item.operation == "OBSERVE"
            )
            assert indexes == [expected_index]


def test_r2_provider_failure_preserves_attempt_and_stops_without_retry(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    client = ScriptedFakeClient(responses, fail_at=4)

    with pytest.raises(CognitiveWorkR2HostError, match="provider failure"):
        run_r2_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-provider-failure",
        )

    state = _read_json(artifact / STATE_NAME)
    assert len(client.calls) == 5
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 5
    assert state["provider_completions"] == 4
    assert state["failure"]["kind"] == "provider_failure"  # type: ignore[index]
    assert not (artifact / RESULT_NAME).exists()


def test_r2_strict_parser_failure_is_incomplete_after_completed_response(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    responses[1] = '{"operation":"ZERO","extra":"forbidden"}'
    client = ScriptedFakeClient(responses)

    with pytest.raises(CognitiveWorkR2HostError, match="strict protocol"):
        run_r2_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-parser-failure",
        )

    state = _read_json(artifact / STATE_NAME)
    assert len(client.calls) == 2
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 2
    assert state["provider_completions"] == 2
    assert state["failure"]["kind"] == "protocol_invalid"  # type: ignore[index]
    assert not (artifact / RESULT_NAME).exists()


def test_r2_midrun_binding_drift_stops_before_next_provider_attempt(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    drifted = _binding(runtime_identity="runtime@drifted")
    identity = _identity(repo, binding)
    responses, _ = _script()
    client = ScriptedFakeClient(responses)
    probe_count = 0

    def probe() -> ExecutionBinding:
        nonlocal probe_count
        probe_count += 1
        if probe_count >= 3:  # preflight, first provider, then drift before second
            return drifted
        return binding

    with pytest.raises(CognitiveWorkR2HostError, match="binding drift"):
        run_r2_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=probe,
            client=client,
            run_id="r2-binding-drift",
        )

    state = _read_json(artifact / STATE_NAME)
    assert len(client.calls) == 1
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 1
    assert state["provider_completions"] == 1
    assert state["failure"]["kind"] == "binding_drift"  # type: ignore[index]
    assert not (artifact / RESULT_NAME).exists()


def test_r2_requires_separate_positive_execution_authorization_before_artifacts_or_calls(
    tmp_path: Path,
):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    client = ScriptedFakeClient(responses)

    with pytest.raises(CognitiveWorkR2HostError, match="not authorized"):
        run_r2_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity, authorized=False),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-not-authorized",
        )

    assert client.calls == []
    assert not artifact.exists()


def test_r2_repository_mismatch_and_artifact_collision_fail_before_provider(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()

    wrong_identity = R2HostIdentity(
        repository_commit="wrong-commit",
        repository_tree=identity.repository_tree,
        execution=binding,
    )
    client = ScriptedFakeClient(responses)
    with pytest.raises(CognitiveWorkR2HostError, match="repository commit"):
        run_r2_host_campaign(
            artifact_root=tmp_path / "repo-mismatch-artifact",
            repository_root=repo,
            identity=wrong_identity,
            authorization=R2ExecutionAuthorization(
                authorization_id="deterministic-test-only",
                execution_repository_commit="wrong-commit",
                preregistration_commit=FROZEN_PREREGISTRATION_COMMIT,
                physical_execution_authorized=True,
            ),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-repo-mismatch",
        )
    assert client.calls == []

    artifact = tmp_path / "collision"
    artifact.mkdir()
    (artifact / "existing.txt").write_text("occupied\n", encoding="utf-8")
    client = ScriptedFakeClient(responses)
    with pytest.raises(CognitiveWorkR2HostError, match="must be empty"):
        run_r2_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-artifact-collision",
        )
    assert client.calls == []
