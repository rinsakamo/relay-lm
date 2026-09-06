from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from relaylm.v2_interventions import Operation, ResourceVector
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_work_r0 import (
    CognitiveWorkCampaign,
    ExecutionBinding,
    freeze_cognitive_start,
)
from tools.v2_cognitive_work_r1_host import (
    CognitiveWorkR1HostError,
    R1HostIdentity,
    SmokeSuite,
    SmokeTask,
    run_r1_host_smoke,
)
from tools.v2_event_semantic_kernel import EventSemanticKernel


class FakeClient:
    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[dict[str, str], ...]] = []

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("unexpected provider call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return ExperimentCompletion(
            content=response,
            input_tokens=10,
            output_tokens=3,
            response_id=f"resp-{len(self.calls)}",
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


def _suite() -> SmokeSuite:
    return SmokeSuite(
        tasks=(
            SmokeTask(
                task_id="easy",
                public_prompt="Return the result of 1+1 as a bare semantic answer.",
                expected_answer="2",
            ),
            SmokeTask(
                task_id="retrieval",
                public_prompt="Return the current project codename.",
                expected_answer="NEW-CODE",
                retrieval_packet="The current project codename is NEW-CODE.",
            ),
        )
    )


def _campaign(
    binding: ExecutionBinding | None = None,
    *,
    suite: SmokeSuite | None = None,
    envelope: ResourceVector | None = None,
    operations: tuple[Operation, ...] | None = None,
) -> CognitiveWorkCampaign:
    binding = binding or _binding()
    suite = suite or _suite()
    kernel = EventSemanticKernel()
    kernel.ingest("R1 smoke admitted", logical_ingress_id="r1-smoke")
    return CognitiveWorkCampaign(
        start=freeze_cognitive_start(kernel, lineage_id="r1-lineage"),
        execution=binding,
        task_digest=suite.digest,
        ordinary_information_ids=("public-task", "retrieval-availability"),
        operations=operations
        or (
            Operation("THINK", ResourceVector(calls=1)),
            Operation("RETRIEVE", ResourceVector(calls=1, retrieval_units=1)),
        ),
        envelope=envelope
        or ResourceVector(
            calls=10,
            input_tokens=500,
            output_tokens=200,
            retrieval_units=4,
        ),
    )


def _identity(
    repo: Path,
    binding: ExecutionBinding | None = None,
    *,
    suite: SmokeSuite | None = None,
    envelope: ResourceVector | None = None,
    operations: tuple[Operation, ...] | None = None,
) -> R1HostIdentity:
    return R1HostIdentity(
        repository_commit=_git(repo, "rev-parse", "HEAD"),
        repository_tree=_git(repo, "rev-parse", "HEAD^{tree}"),
        campaign=_campaign(
            binding,
            suite=suite,
            envelope=envelope,
            operations=operations,
        ),
    )


def _success_responses() -> list[str]:
    return [
        '{"answer":"2"}',
        '{"answer":"2"}',
        '{"operation":"ZERO"}',
        '{"answer":"OLD-CODE"}',
        '{"answer":"OLD-CODE"}',
        '{"answer":"NEW-CODE"}',
        '{"operation":"RETRIEVE"}',
        '{"answer":"NEW-CODE"}',
    ]


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _probe(binding: ExecutionBinding, calls: list[int]):
    def inner() -> ExecutionBinding:
        calls.append(1)
        return binding

    return inner


def test_r1_successful_two_task_smoke_is_non_citable_and_mechanically_discriminating(
    tmp_path: Path,
):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifacts"
    binding = _binding()
    suite = _suite()
    probe_calls: list[int] = []
    client = FakeClient(_success_responses())

    result = run_r1_host_smoke(
        artifact_root=artifact,
        identity=_identity(repo, binding, suite=suite),
        repository_root=repo,
        live_binding_probe=_probe(binding, probe_calls),
        client=client,
        suite=suite,
    )

    assert result.status == "COMPLETED"
    assert result.claim_status == "NON_CITABLE_R1_SMOKE"
    assert result.citable is False
    assert result.provider_calls == 8
    assert result.provider_attempts == 8
    assert result.provider_completions == 8
    assert len(client.calls) == 8
    assert len(probe_calls) == 9  # one preflight + one before every provider call
    assert result.classification == "MECHANICALLY_DISCRIMINATING"

    outcomes = {(item.task_id, item.arm_id): item for item in result.outcomes}
    assert outcomes[("easy", "A0")].operation == "THINK"
    assert outcomes[("easy", "A1")].operation == "ZERO"
    assert outcomes[("easy", "A2")].operation == "ZERO"
    assert outcomes[("retrieval", "A0")].correct is False
    assert outcomes[("retrieval", "A1")].operation == "RETRIEVE"
    assert outcomes[("retrieval", "A1")].correct is True
    assert outcomes[("retrieval", "A2")].operation == "RETRIEVE"
    assert outcomes[("retrieval", "A2")].correct is True

    # Shared base work is charged counterfactually to every arm. A2 additionally
    # pays its allocator call and any selected operation.
    assert outcomes[("easy", "A1")].cost.calls == 1
    assert outcomes[("easy", "A2")].cost.calls == 2
    assert outcomes[("retrieval", "A1")].cost.calls == 2
    assert outcomes[("retrieval", "A1")].cost.retrieval_units == 1
    assert outcomes[("retrieval", "A2")].cost.calls == 3
    assert outcomes[("retrieval", "A2")].cost.retrieval_units == 1

    manifest = _read_json(artifact / "run-manifest.json")
    state = _read_json(artifact / "run-state.json")
    durable = _read_json(artifact / "r1-smoke-result.json")
    assert manifest["citable"] is False
    assert manifest["identity"]["campaign"]["fingerprint"] == _identity(
        repo, binding, suite=suite
    ).campaign_fingerprint
    assert state["status"] == "COMPLETED"
    assert state["provider_attempts"] == 8
    assert state["provider_completions"] == 8
    assert durable["classification"] == "MECHANICALLY_DISCRIMINATING"
    assert durable["physical_base_completion_shared_across_arms"] is True
    assert durable["base_cost_charged_counterfactually_to_each_arm"] is True
    assert durable["arm_resource_totals"]["A2"]["calls"] == 5
    assert (artifact / "request-evidence.jsonl").exists()


def test_r1_evaluator_answer_and_retrieval_packet_do_not_leak_before_retrieve(
    tmp_path: Path,
):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifacts"
    binding = _binding()
    client = FakeClient(_success_responses())
    suite = SmokeSuite(
        tasks=(
            SmokeTask("easy", "Public easy prompt", "PRIVATE-EXPECTED"),
            SmokeTask(
                "retrieval",
                "Public retrieval prompt",
                "PRIVATE-NEW",
                retrieval_packet="SECRET-RETRIEVAL-PACKET",
            ),
        )
    )

    run_r1_host_smoke(
        artifact_root=artifact,
        identity=_identity(repo, binding, suite=suite),
        repository_root=repo,
        live_binding_probe=lambda: binding,
        client=client,
        suite=suite,
    )

    serialized = [json.dumps(call, ensure_ascii=False) for call in client.calls]
    assert all("PRIVATE-EXPECTED" not in item for item in serialized)
    assert all("PRIVATE-NEW" not in item for item in serialized)
    packet_calls = [
        index
        for index, item in enumerate(serialized)
        if "SECRET-RETRIEVAL-PACKET" in item
    ]
    assert packet_calls == [5, 7]
    assert "SECRET-RETRIEVAL-PACKET" not in serialized[6]  # A2 allocator call


def test_r1_provider_failure_records_attempt_even_without_completion(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifacts"
    binding = _binding()
    client = FakeClient([StructureProposalError("boom")])
    suite = _suite()

    with pytest.raises(CognitiveWorkR1HostError, match="provider failure"):
        run_r1_host_smoke(
            artifact_root=artifact,
            identity=_identity(repo, binding, suite=suite),
            repository_root=repo,
            live_binding_probe=lambda: binding,
            client=client,
            suite=suite,
        )

    state = _read_json(artifact / "run-state.json")
    assert len(client.calls) == 1
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 1
    assert state["provider_completions"] == 0


def test_r1_suite_must_match_exact_r0_campaign_before_artifacts_or_calls(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    admitted_suite = _suite()
    other_suite = SmokeSuite(
        (
            SmokeTask("easy", "changed prompt", "2"),
            SmokeTask("retrieval", "Return code", "NEW-CODE", "NEW-CODE"),
        )
    )
    identity = _identity(repo, suite=admitted_suite)
    client = FakeClient(_success_responses())
    artifact = tmp_path / "artifacts"
    with pytest.raises(CognitiveWorkR1HostError, match="exact R0 campaign task digest"):
        run_r1_host_smoke(
            artifact_root=artifact,
            identity=identity,
            repository_root=repo,
            live_binding_probe=lambda: identity.execution,
            client=client,
            suite=other_suite,
        )
    assert client.calls == []
    assert not artifact.exists()


def test_r1_identity_requires_nonprivileged_think_and_retrieve_surface(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    with pytest.raises(CognitiveWorkR1HostError, match="missing required R1 operations"):
        _identity(
            repo,
            operations=(Operation("THINK", ResourceVector(calls=1)),),
        )
    with pytest.raises(CognitiveWorkR1HostError, match="must not be privileged"):
        _identity(
            repo,
            operations=(
                Operation("THINK", ResourceVector(calls=1)),
                Operation(
                    "RETRIEVE",
                    ResourceVector(calls=1, retrieval_units=1),
                    privileged=True,
                ),
            ),
        )


def test_r1_measured_arm_work_must_fit_frozen_campaign_envelope(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifacts"
    binding = _binding()
    suite = _suite()
    identity = _identity(
        repo,
        binding,
        suite=suite,
        envelope=ResourceVector(
            calls=4,
            input_tokens=500,
            output_tokens=200,
            retrieval_units=4,
        ),
    )
    client = FakeClient(_success_responses())
    with pytest.raises(CognitiveWorkR1HostError, match="A2 measured work exceeds"):
        run_r1_host_smoke(
            artifact_root=artifact,
            identity=identity,
            repository_root=repo,
            live_binding_probe=lambda: binding,
            client=client,
            suite=suite,
        )
    assert len(client.calls) == 8
    state = _read_json(artifact / "run-state.json")
    assert state["status"] == "INCOMPLETE"
    assert state["failure"]["kind"] == "resource_envelope_exceeded"


def test_r1_preflight_binding_drift_fails_before_provider_call(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifacts"
    expected = _binding()
    suite = _suite()
    client = FakeClient(_success_responses())

    with pytest.raises(CognitiveWorkR1HostError, match="preflight"):
        run_r1_host_smoke(
            artifact_root=artifact,
            identity=_identity(repo, expected, suite=suite),
            repository_root=repo,
            live_binding_probe=lambda: _binding(runtime_identity="different-runtime"),
            client=client,
            suite=suite,
        )
    assert client.calls == []
    state = _read_json(artifact / "run-state.json")
    assert state["status"] == "INCOMPLETE"


def test_r1_midrun_binding_drift_stops_without_retry(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifacts"
    expected = _binding()
    suite = _suite()
    observations = [expected, expected, _binding(runtime_identity="drifted")]
    client = FakeClient(_success_responses())

    def probe() -> ExecutionBinding:
        return observations.pop(0)

    with pytest.raises(CognitiveWorkR1HostError, match="physical binding drift"):
        run_r1_host_smoke(
            artifact_root=artifact,
            identity=_identity(repo, expected, suite=suite),
            repository_root=repo,
            live_binding_probe=probe,
            client=client,
            suite=suite,
        )
    assert len(client.calls) == 1
    state = _read_json(artifact / "run-state.json")
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 1
    assert state["provider_completions"] == 1


@pytest.mark.parametrize(
    "allocator_output,error",
    [
        ('{"operation":"ZERO","operation":"THINK"}', "strict JSON"),
        ('{"operation":"MAGIC"}', "undeclared operation"),
    ],
)
def test_r1_invalid_allocator_protocol_is_terminal(
    tmp_path: Path,
    allocator_output: str,
    error: str,
):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifacts"
    binding = _binding()
    suite = _suite()
    client = FakeClient(
        [
            '{"answer":"2"}',
            '{"answer":"2"}',
            allocator_output,
        ]
    )
    with pytest.raises(CognitiveWorkR1HostError, match=error):
        run_r1_host_smoke(
            artifact_root=artifact,
            identity=_identity(repo, binding, suite=suite),
            repository_root=repo,
            live_binding_probe=lambda: binding,
            client=client,
            suite=suite,
        )
    assert _read_json(artifact / "run-state.json")["status"] == "INCOMPLETE"


def test_r1_allocator_cannot_retrieve_when_packet_absent(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifacts"
    binding = _binding()
    suite = _suite()
    client = FakeClient(
        [
            '{"answer":"2"}',
            '{"answer":"2"}',
            '{"operation":"RETRIEVE"}',
        ]
    )
    with pytest.raises(CognitiveWorkR1HostError, match="no retrieval packet"):
        run_r1_host_smoke(
            artifact_root=artifact,
            identity=_identity(repo, binding, suite=suite),
            repository_root=repo,
            live_binding_probe=lambda: binding,
            client=client,
            suite=suite,
        )
    assert _read_json(artifact / "run-state.json")["status"] == "INCOMPLETE"


def test_r1_dirty_repository_rejected_before_artifacts_or_model_calls(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    identity = _identity(repo)
    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    artifact = tmp_path / "artifacts"
    client = FakeClient(_success_responses())
    with pytest.raises(CognitiveWorkR1HostError, match="dirty"):
        run_r1_host_smoke(
            artifact_root=artifact,
            identity=identity,
            repository_root=repo,
            live_binding_probe=lambda: identity.execution,
            client=client,
            suite=_suite(),
        )
    assert client.calls == []
    assert not artifact.exists()


def test_r1_wrong_repository_identity_rejected_before_provider_call(tmp_path: Path):
    repo, _, tree = _repo(tmp_path)
    binding = _binding()
    identity = R1HostIdentity(
        repository_commit="0" * 40,
        repository_tree=tree,
        campaign=_campaign(binding),
    )
    client = FakeClient(_success_responses())
    with pytest.raises(CognitiveWorkR1HostError, match="commit does not match"):
        run_r1_host_smoke(
            artifact_root=tmp_path / "artifacts",
            identity=identity,
            repository_root=repo,
            live_binding_probe=lambda: identity.execution,
            client=client,
            suite=_suite(),
        )
    assert client.calls == []


def test_r1_artifact_root_must_be_outside_repo_and_empty(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    identity = _identity(repo)
    client = FakeClient(_success_responses())
    with pytest.raises(CognitiveWorkR1HostError, match="outside"):
        run_r1_host_smoke(
            artifact_root=repo / "artifacts",
            identity=identity,
            repository_root=repo,
            live_binding_probe=lambda: identity.execution,
            client=client,
            suite=_suite(),
        )

    artifact = tmp_path / "nonempty"
    artifact.mkdir()
    (artifact / "old.txt").write_text("old", encoding="utf-8")
    with pytest.raises(CognitiveWorkR1HostError, match="must be empty"):
        run_r1_host_smoke(
            artifact_root=artifact,
            identity=identity,
            repository_root=repo,
            live_binding_probe=lambda: identity.execution,
            client=client,
            suite=_suite(),
        )


def test_r1_suite_requires_retrieval_and_zero_work_mechanical_coverage():
    with pytest.raises(CognitiveWorkR1HostError, match="at least two"):
        SmokeSuite((SmokeTask("one", "p", "a"),))
    with pytest.raises(CognitiveWorkR1HostError, match="retrieval available"):
        SmokeSuite((SmokeTask("a", "p", "a"), SmokeTask("b", "p", "b")))
    with pytest.raises(CognitiveWorkR1HostError, match="zero-work"):
        SmokeSuite(
            (
                SmokeTask("a", "p", "a", "r1"),
                SmokeTask("b", "p", "b", "r2"),
            )
        )


def test_r1_identity_rejects_any_retry_policy():
    campaign = _campaign()
    with pytest.raises(CognitiveWorkR1HostError, match="disable"):
        R1HostIdentity("c", "t", campaign, automatic_retry=True)
    with pytest.raises(CognitiveWorkR1HostError, match="disable"):
        R1HostIdentity("c", "t", campaign, semantic_retry=True)
