from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_work_r0 import ExecutionBinding
from tools import v2_cognitive_work_r2_host as historical_host
from tools.v2_cognitive_work_r2_replacement_host import (
    ANSWER_PROTOCOL_VERSION,
    BANK_EVIDENCE_NAME,
    FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT,
    FROZEN_REPLACEMENT_ROOT_SEED,
    MANIFEST_NAME,
    REQUEST_EVIDENCE_NAME,
    RESULT_NAME,
    STATE_NAME,
    CognitiveWorkR2ReplacementHostError,
    R2ReplacementExecutionAuthorization,
    R2ReplacementHostIdentity,
    run_r2_replacement_host_campaign,
)
from tools.v2_cognitive_work_r2_replacement_preregistration import (
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
            raise AssertionError("unexpected 137th replacement provider call")
        return ExperimentCompletion(
            content=self.responses[index],
            input_tokens=10 + index % 3,
            output_tokens=2,
            response_id=f"fake-r2-replacement-{index:03d}",
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


def _identity(
    repo: Path,
    binding: ExecutionBinding | None = None,
) -> R2ReplacementHostIdentity:
    return R2ReplacementHostIdentity(
        repository_commit=_git(repo, "rev-parse", "HEAD"),
        repository_tree=_git(repo, "rev-parse", "HEAD^{tree}"),
        execution=binding or _binding(),
    )


def _authorization(
    identity: R2ReplacementHostIdentity,
    *,
    authorized: bool = True,
) -> R2ReplacementExecutionAuthorization:
    return R2ReplacementExecutionAuthorization(
        authorization_id="replacement-deterministic-test-only",
        execution_repository_commit=identity.repository_commit,
        preregistration_commit=FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT,
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


def _answer_json(answer: str) -> str:
    if answer.lstrip("-").isdigit():
        return json.dumps({"answer": int(answer)})
    return json.dumps({"answer": answer})


def _script() -> tuple[list[str], tuple[PlannedProviderCall, ...]]:
    preregistration = build_preregistration(
        FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT
    )
    tasks = {task.task_id: task for task in preregistration.tasks}
    plan = physical_call_plan(preregistration.tasks)
    responses: list[str] = []
    for item in plan:
        task = tasks[item.task_id]
        if item.role == "BASE":
            responses.append(_answer_json(_base_answer(task)))
        elif item.role == "A2_ALLOCATE":
            responses.append(json.dumps({"operation": _adaptive_operation(task)}))
        else:
            assert item.operation is not None
            responses.append(_answer_json(_bank_answer(task, item.operation)))
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


def test_replacement_host_binds_only_repaired_preregistration_identity():
    preregistration = build_preregistration(
        FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT
    )
    assert preregistration.root_seed == FROZEN_REPLACEMENT_ROOT_SEED
    assert preregistration.budget.physical_provider_call_max == 136
    assert ANSWER_PROTOCOL_VERSION == "canonical-string-or-integer-v2"

    assert (
        historical_host.FROZEN_PREREGISTRATION_COMMIT
        == "f8540c959856938331d5db58ae3a2b9825ad5f9b"
    )
    assert historical_host.FROZEN_PREREGISTRATION_COMMIT != (
        FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT
    )
    assert historical_host.FROZEN_ROOT_SEED != FROZEN_REPLACEMENT_ROOT_SEED

    with pytest.raises(
        CognitiveWorkR2ReplacementHostError,
        match="repaired preregistration",
    ):
        R2ReplacementExecutionAuthorization(
            authorization_id="wrong-version",
            execution_repository_commit="abc",
            preregistration_commit=historical_host.FROZEN_PREREGISTRATION_COMMIT,
            physical_execution_authorized=True,
        )


def test_replacement_complete_fake_campaign_accepts_integer_answers_and_shared_bank(
    tmp_path: Path,
):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, plan = _script()
    assert any('"answer": ' in item for item in responses)
    client = ScriptedFakeClient(responses)
    probe_calls: list[int] = []

    def probe() -> ExecutionBinding:
        probe_calls.append(1)
        return binding

    result = run_r2_replacement_host_campaign(
        artifact_root=artifact,
        repository_root=repo,
        identity=identity,
        authorization=_authorization(identity),
        live_binding_probe=probe,
        client=client,
        run_id="r2-replacement-fake-complete",
    )

    assert result.status == "COMPLETED"
    assert result.provider_attempts == 136
    assert result.provider_completions == 136
    assert result.physical_cost.calls == 136
    assert result.category == "ADAPTIVE_SIGNAL"
    assert len(client.calls) == 136
    assert len(probe_calls) == 137
    assert all(len(items) == 40 for items in result.outcomes.values())

    manifest = _read_json(artifact / MANIFEST_NAME)
    state = _read_json(artifact / STATE_NAME)
    durable = _read_json(artifact / RESULT_NAME)
    bank = _read_jsonl(artifact / BANK_EVIDENCE_NAME)
    request_evidence = _read_jsonl(artifact / REQUEST_EVIDENCE_NAME)

    assert manifest["claim_status"] == "R2_REPLACEMENT_PREREGISTERED_PHYSICAL_RESULT"
    assert manifest["answer_protocol_version"] == ANSWER_PROTOCOL_VERSION
    assert manifest["preregistration"]["commit"] == (  # type: ignore[index]
        FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT
    )
    assert manifest["preregistration"]["root_seed"] == (  # type: ignore[index]
        FROZEN_REPLACEMENT_ROOT_SEED
    )
    assert manifest["historical_original_preregistration_commit"] == (
        historical_host.FROZEN_PREREGISTRATION_COMMIT
    )
    assert state["status"] == "COMPLETED"
    assert state["provider_attempts"] == 136
    assert state["provider_completions"] == 136
    assert len(bank) == 40
    assert len(request_evidence) == 272
    assert durable["answer_protocol_version"] == ANSWER_PROTOCOL_VERSION
    assert durable["claim_status"] == "R2_REPLACEMENT_PREREGISTERED_PHYSICAL_RESULT"
    assert durable["interpretation"]["category"] == "ADAPTIVE_SIGNAL"  # type: ignore[index]

    completed = [item for item in request_evidence if item["status"] == "COMPLETED"]
    assert [
        (item["task_id"], item["role"], item["operation"]) for item in completed
    ] == [(item.task_id, item.role, item.operation) for item in plan]


def test_replacement_allocator_messages_preserve_evaluator_and_packet_quarantine(
    tmp_path: Path,
):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    preregistration = build_preregistration(
        FROZEN_REPLACEMENT_PREREGISTRATION_COMMIT
    )
    responses, plan = _script()
    client = ScriptedFakeClient(responses)

    run_r2_replacement_host_campaign(
        artifact_root=artifact,
        repository_root=repo,
        identity=identity,
        authorization=_authorization(identity),
        live_binding_probe=lambda: binding,
        client=client,
        run_id="r2-replacement-leak-check",
    )

    task_by_id = {task.task_id: task for task in preregistration.tasks}
    serialized_calls = [json.dumps(call, ensure_ascii=False) for call in client.calls]
    for index, item in enumerate(plan):
        task = task_by_id[item.task_id]
        if item.role == "A2_ALLOCATE":
            payload = json.loads(client.calls[index][1]["content"])
            assert "hidden_regime" not in payload
            assert "expected_answer" not in payload
            assert task.hidden_regime not in serialized_calls[index]
            if task.retrieval_packet is not None:
                assert task.retrieval_packet not in serialized_calls[index]
            if task.observation_packet is not None:
                assert task.observation_packet not in serialized_calls[index]

    for task in preregistration.tasks:
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


def test_replacement_provider_failure_preserves_attempt_and_stops_without_retry(
    tmp_path: Path,
):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    client = ScriptedFakeClient(responses, fail_at=4)

    with pytest.raises(CognitiveWorkR2ReplacementHostError, match="provider failure"):
        run_r2_replacement_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-replacement-provider-failure",
        )

    state = _read_json(artifact / STATE_NAME)
    assert len(client.calls) == 5
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 5
    assert state["provider_completions"] == 4
    assert state["failure"]["kind"] == "provider_failure"  # type: ignore[index]
    assert not (artifact / RESULT_NAME).exists()


def test_replacement_parser_failure_after_completion_remains_incomplete(
    tmp_path: Path,
):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    responses, _ = _script()
    responses[2] = '{"answer":1.0}'
    client = ScriptedFakeClient(responses)

    with pytest.raises(CognitiveWorkR2ReplacementHostError, match="strict protocol"):
        run_r2_replacement_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="r2-replacement-parser-failure",
        )

    state = _read_json(artifact / STATE_NAME)
    assert len(client.calls) == 3
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 3
    assert state["provider_completions"] == 3
    assert state["failure"]["kind"] == "protocol_invalid"  # type: ignore[index]
    assert not (artifact / RESULT_NAME).exists()
    assert not (artifact / BANK_EVIDENCE_NAME).exists()


def test_replacement_live_binding_drift_stops_before_next_provider_attempt(
    tmp_path: Path,
):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    drifted = _binding(runtime_identity="runtime@drifted")
    identity = _identity(repo, binding)
    responses, _ = _script()
    client = ScriptedFakeClient(responses)
    probes = 0

    def probe() -> ExecutionBinding:
        nonlocal probes
        probes += 1
        return binding if probes <= 3 else drifted

    with pytest.raises(CognitiveWorkR2ReplacementHostError, match="binding drift"):
        run_r2_replacement_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=probe,
            client=client,
            run_id="r2-replacement-binding-drift",
        )

    state = _read_json(artifact / STATE_NAME)
    assert len(client.calls) == 2
    assert state["provider_attempts"] == 2
    assert state["provider_completions"] == 2
    assert state["failure"]["kind"] == "binding_drift"  # type: ignore[index]
    assert not (artifact / RESULT_NAME).exists()


def test_replacement_false_authorization_fails_before_artifact_and_provider(
    tmp_path: Path,
):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    identity = _identity(repo)
    responses, _ = _script()
    client = ScriptedFakeClient(responses)

    with pytest.raises(CognitiveWorkR2ReplacementHostError, match="not authorized"):
        run_r2_replacement_host_campaign(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity, authorized=False),
            live_binding_probe=lambda: identity.execution,
            client=client,
            run_id="r2-replacement-not-authorized",
        )

    assert len(client.calls) == 0
    assert not artifact.exists()


def test_replacement_repository_mismatch_and_artifact_collision_fail_closed(
    tmp_path: Path,
):
    repo, _, _ = _repo(tmp_path)
    identity = _identity(repo)
    responses, _ = _script()

    dirty = repo / "dirty.txt"
    dirty.write_text("dirty\n", encoding="utf-8")
    client = ScriptedFakeClient(responses)
    with pytest.raises(CognitiveWorkR2ReplacementHostError, match="dirty"):
        run_r2_replacement_host_campaign(
            artifact_root=tmp_path / "dirty-artifact",
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: identity.execution,
            client=client,
            run_id="r2-replacement-dirty",
        )
    assert len(client.calls) == 0
    dirty.unlink()

    collision = tmp_path / "collision"
    collision.mkdir()
    (collision / "existing.txt").write_text("occupied\n", encoding="utf-8")
    client = ScriptedFakeClient(responses)
    with pytest.raises(CognitiveWorkR2ReplacementHostError, match="must be empty"):
        run_r2_replacement_host_campaign(
            artifact_root=collision,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: identity.execution,
            client=client,
            run_id="r2-replacement-collision",
        )
    assert len(client.calls) == 0
