from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from relaylm.v2_transfer_experiment import generate_transfer_family
from tools.v2_transfer_r1_host import (
    R1HostError,
    RepositoryState,
    probe_git_repository,
    run_r1_host_smoke,
)


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_repo(root: Path) -> tuple[Path, RepositoryState]:
    root.mkdir(parents=True)
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True, text=True)
    _git(root, "config", "user.email", "r1-host@example.invalid")
    _git(root, "config", "user.name", "R1 Host Test")
    (root / "tracked.txt").write_text("relaylm2-r1-host\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "fixture")
    state = RepositoryState(
        commit=_git(root, "rev-parse", "HEAD"),
        tree=_git(root, "rev-parse", "HEAD^{tree}"),
        clean=True,
    )
    return root, state


def _launch_admission() -> dict[str, object]:
    return {
        "backend": "vllm",
        "runtime": "vllm-0.26.1-test",
        "model_runner": "vllm-v1",
        "effective_gpu_reservation": 0.9,
        "admitted_context": 8192,
        "capacity_evidence": {"kind": "bounded-test", "tokens": 8192},
        "launch_evidence_reference": "local://launch-evidence",
        "runtime_ownership_evidence_reference": "local://runtime-owner",
    }


def _identity(repository: RepositoryState) -> dict[str, object]:
    launch = _launch_admission()
    return {
        "repository": {
            "commit": repository.commit,
            "tree": repository.tree,
            "clean_required": True,
        },
        "candidate": "relaylm2-transfer-r1-smoke",
        "prompt_core": "relaylm2-transfer-r1",
        "benchmark": "transfer-r1-smoke",
        "dataset": "deterministic-transfer-family",
        "harness": "relaylm2-transfer-r1-host-v1",
        "adapter": "openai-compatible-chat-completions",
        "model": {"id": "test-model", "revision": "sha256:model"},
        "artifact": {"revision": "sha256:artifact"},
        "tokenizer": {"revision": "sha256:tokenizer"},
        "template": {"revision": "sha256:template"},
        "backend": "vllm",
        "runtime": "vllm-0.26.1-test",
        "decoding": {"temperature": 0, "top_p": 1},
        "reasoning": {"mode": "off"},
        "structured_output": {"mode": "none"},
        "context_capacity": 8192,
        "capacity_evidence": {"kind": "bounded-test", "tokens": 8192},
        "hardware": {"gpu": "fake-gpu", "vram_bytes": 12_000_000_000},
        "execution_order": ["source-learning", "t0", "t1", "t2"],
        "retry_policy": {"automatic_retry": False, "semantic_retry": False},
        "authority": {
            "status": "CURRENT_AUTHORITY_CONFIRMED",
            "commit": repository.commit,
        },
        "launch_admission": launch,
    }


def _live_binding(repository: RepositoryState) -> dict[str, object]:
    identity = _identity(repository)
    return {
        key: identity[key]
        for key in (
            "model",
            "artifact",
            "tokenizer",
            "template",
            "backend",
            "runtime",
            "decoding",
            "reasoning",
            "structured_output",
            "context_capacity",
            "hardware",
            "launch_admission",
        )
    }


class FakeClient:
    def __init__(self, responses: list[str], *, manifest_path: Path | None = None) -> None:
        self.responses = list(responses)
        self.manifest_path = manifest_path
        self.calls: list[tuple[dict[str, str], ...]] = []

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        if self.manifest_path is not None:
            assert self.manifest_path.exists(), "manifest must predate the first model call"
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("unexpected model call")
        content = self.responses.pop(0)
        if content == "__FAIL__":
            raise StructureProposalError("synthetic provider failure")
        if content == "__CRASH__":
            raise RuntimeError("synthetic provider client crash")
        return ExperimentCompletion(
            content=content,
            input_tokens=11,
            output_tokens=5,
            response_id=f"fake-{len(self.calls)}",
        )


def _responses(seed: int = 2157) -> tuple[object, list[str]]:
    family = generate_transfer_family(seed=seed, regime="shared")
    source = json.dumps(
        {
            "permutation": list(family.source_rule.permutation),
            "offsets": list(family.source_rule.offsets),
            "modulus": family.source_rule.modulus,
        },
        separators=(",", ":"),
    )
    target = json.dumps(list(family.expected_output(0)), separators=(",", ":"))
    return family, [source, target, target, target]


def test_r1_git_probe_reads_commit_tree_and_worktree_cleanliness(tmp_path: Path):
    repository_root, expected = _git_repo(tmp_path / "repo")

    assert probe_git_repository(repository_root) == expected

    (repository_root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    dirty = probe_git_repository(repository_root)
    assert dirty.commit == expected.commit
    assert dirty.tree == expected.tree
    assert dirty.clean is False


def test_r1_host_rejects_dirty_or_wrong_repository_before_artifacts_or_model_calls(tmp_path: Path):
    family, responses = _responses()

    dirty_root, dirty_state = _git_repo(tmp_path / "dirty-repo")
    (dirty_root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    dirty_artifact = tmp_path / "dirty-artifact"
    dirty_client = FakeClient(responses.copy())
    with pytest.raises(R1HostError, match="repository"):
        run_r1_host_smoke(
            artifact_root=dirty_artifact,
            identity=_identity(dirty_state),
            repository_root=dirty_root,
            live_binding_probe=lambda: _live_binding(dirty_state),
            client=dirty_client,
            family=family,
            step_index=0,
            examples_visible=0,
        )
    assert not (dirty_artifact / "run-manifest.json").exists()
    assert dirty_client.calls == []

    for label, identity_mutation in (
        ("wrong-commit", {"commit": "c" * 40}),
        ("wrong-tree", {"tree": "d" * 40}),
    ):
        repository_root, state = _git_repo(tmp_path / f"{label}-repo")
        identity = _identity(state)
        identity["repository"] = {**identity["repository"], **identity_mutation}
        artifact = tmp_path / f"{label}-artifact"
        client = FakeClient(responses.copy())
        with pytest.raises(R1HostError, match="repository"):
            run_r1_host_smoke(
                artifact_root=artifact,
                identity=identity,
                repository_root=repository_root,
                live_binding_probe=lambda state=state: _live_binding(state),
                client=client,
                family=family,
                step_index=0,
                examples_visible=0,
            )
        assert not (artifact / "run-manifest.json").exists()
        assert client.calls == []


def test_r1_host_requires_fresh_empty_artifact_root(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    root = tmp_path / "occupied"
    root.mkdir()
    (root / "stale.json").write_text("{}", encoding="utf-8")

    with pytest.raises(R1HostError, match="artifact root"):
        run_r1_host_smoke(
            artifact_root=root,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=lambda: _live_binding(state),
            client=FakeClient(responses),
            family=family,
            step_index=0,
            examples_visible=0,
        )


def test_r1_host_writes_frozen_manifest_before_first_model_call_and_uses_one_client(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    root = tmp_path / "run"
    client = FakeClient(responses, manifest_path=root / "run-manifest.json")

    result = run_r1_host_smoke(
        artifact_root=root,
        identity=_identity(state),
        repository_root=repository_root,
        live_binding_probe=lambda: _live_binding(state),
        client=client,
        family=family,
        step_index=0,
        examples_visible=0,
    )

    assert len(client.calls) == 4
    manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
    assert manifest["identity"]["repository"] == {
        "commit": state.commit,
        "tree": state.tree,
        "clean_required": True,
    }
    assert manifest["identity"]["execution_order"] == ["source-learning", "t0", "t1", "t2"]
    assert manifest["identity"]["retry_policy"] == {
        "automatic_retry": False,
        "semantic_retry": False,
    }
    assert result.status == "COMPLETED"
    assert result.claim_status == "NON_CITABLE_R1_SMOKE"
    assert result.citable is False
    assert tuple(result.arm_correctness) == (True, True, True)


def test_r1_host_rechecks_full_physical_binding_before_every_model_call(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    stable = _live_binding(state)
    drifted = _live_binding(state)
    drifted["model"] = {"id": "different-model", "revision": "sha256:other"}
    observations = [stable, stable, drifted]

    def probe() -> dict[str, object]:
        return observations.pop(0) if observations else drifted

    client = FakeClient(responses)
    root = tmp_path / "drift"
    with pytest.raises(R1HostError, match="physical binding drift"):
        run_r1_host_smoke(
            artifact_root=root,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=probe,
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    assert len(client.calls) == 1
    state_payload = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
    assert state_payload["status"] == "INCOMPLETE"


def test_r1_host_live_binding_probe_crash_is_terminal_after_manifest_creation(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    stable = _live_binding(state)
    calls = 0

    def probe() -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return stable
        raise RuntimeError("synthetic physical probe crash")

    client = FakeClient(responses)
    root = tmp_path / "probe-crash"
    with pytest.raises(R1HostError, match="physical binding probe failure"):
        run_r1_host_smoke(
            artifact_root=root,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=probe,
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    assert client.calls == []
    state_payload = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
    assert state_payload["status"] == "INCOMPLETE"
    evidence = (root / "request-evidence.jsonl").read_text(encoding="utf-8")
    assert "physical_binding_probe_failure" in evidence


def test_r1_host_provider_failure_is_terminal_and_never_retried_with_changed_settings(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    responses[1] = "__FAIL__"
    client = FakeClient(responses)
    root = tmp_path / "failure"

    with pytest.raises(R1HostError, match="provider"):
        run_r1_host_smoke(
            artifact_root=root,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=lambda: _live_binding(state),
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    assert len(client.calls) == 2
    state_payload = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
    assert state_payload["status"] == "INCOMPLETE"
    evidence = (root / "request-evidence.jsonl").read_text(encoding="utf-8")
    assert "provider_failure" in evidence


def test_r1_host_unexpected_provider_client_crash_is_terminal(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    responses[1] = "__CRASH__"
    client = FakeClient(responses)
    root = tmp_path / "provider-crash"

    with pytest.raises(R1HostError, match="provider client failure"):
        run_r1_host_smoke(
            artifact_root=root,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=lambda: _live_binding(state),
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    assert len(client.calls) == 2
    state_payload = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
    assert state_payload["status"] == "INCOMPLETE"
    evidence = (root / "request-evidence.jsonl").read_text(encoding="utf-8")
    assert "provider_client_failure" in evidence


def test_r1_host_records_non_authoritative_raw_outputs_without_promoting_a_transfer_claim(tmp_path: Path):
    family, responses = _responses(seed=2162)
    repository_root, state = _git_repo(tmp_path / "repo")
    root = tmp_path / "evidence"
    result = run_r1_host_smoke(
        artifact_root=root,
        identity=_identity(state),
        repository_root=repository_root,
        live_binding_probe=lambda: _live_binding(state),
        client=FakeClient(responses),
        family=family,
        step_index=0,
        examples_visible=0,
    )

    records = [
        json.loads(line)
        for line in (root / "request-evidence.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert records
    assert all(record["evidence"]["authority"] == "instrumentation_only" for record in records)
    assert result.citable is False
    assert result.claim_status == "NON_CITABLE_R1_SMOKE"


def test_r1_host_rejects_retry_policy_or_execution_order_that_could_change_the_causal_contract(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    for key, value in (
        ("retry_policy", {"automatic_retry": True, "semantic_retry": False}),
        ("execution_order", ["source-learning", "t1", "t0", "t2"]),
    ):
        identity = _identity(state)
        identity[key] = value
        with pytest.raises(R1HostError, match=key.replace("_", " ")):
            run_r1_host_smoke(
                artifact_root=tmp_path / key,
                identity=identity,
                repository_root=repository_root,
                live_binding_probe=lambda: _live_binding(state),
                client=FakeClient(responses.copy()),
                family=family,
                step_index=0,
                examples_visible=0,
            )
