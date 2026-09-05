from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from relaylm.v2_transfer_experiment import generate_transfer_family
from tools.v2_cognitive_ir_s2_host import (
    S2HostError,
    S2RepositoryState,
    probe_s2_git_repository,
    run_s2_host_smoke,
)


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_repo(root: Path) -> tuple[Path, S2RepositoryState]:
    root.mkdir(parents=True)
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True, text=True)
    _git(root, "config", "user.email", "s2-host@example.invalid")
    _git(root, "config", "user.name", "S2 Host Test")
    (root / "tracked.txt").write_text("relaylm2-cognitive-ir-s2-host\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "fixture")
    state = S2RepositoryState(
        commit=_git(root, "rev-parse", "HEAD"),
        tree=_git(root, "rev-parse", "HEAD^{tree}"),
        clean=True,
    )
    return root, state


def _launch_admission() -> dict[str, object]:
    return {
        "backend": "vllm",
        "runtime": "vllm-test",
        "model_runner": "vllm-v1",
        "effective_gpu_reservation": 0.9,
        "admitted_context": 8192,
        "capacity_evidence": {"kind": "bounded-test", "tokens": 8192},
        "launch_evidence_reference": "local://launch-evidence",
        "runtime_ownership_evidence_reference": "local://runtime-owner",
    }


def _identity(repository: S2RepositoryState) -> dict[str, object]:
    launch = _launch_admission()
    return {
        "repository": {
            "commit": repository.commit,
            "tree": repository.tree,
            "clean_required": True,
        },
        "candidate": "relaylm2-cognitive-ir-s2-smoke",
        "prompt_core": "relaylm2-cognitive-ir-s2",
        "benchmark": "cognitive-ir-s2-smoke",
        "dataset": "deterministic-transfer-family",
        "harness": "relaylm2-cognitive-ir-s2-host-v1",
        "adapter": "openai-compatible-chat-completions",
        "model": {"id": "test-model", "revision": "sha256:model"},
        "artifact": {"revision": "sha256:artifact"},
        "tokenizer": {"revision": "sha256:tokenizer"},
        "template": {"revision": "sha256:template"},
        "backend": "vllm",
        "runtime": "vllm-test",
        "decoding": {"temperature": 0, "top_p": 1},
        "reasoning": {"mode": "off"},
        "structured_output": {"mode": "none"},
        "context_capacity": 8192,
        "capacity_evidence": {"kind": "bounded-test", "tokens": 8192},
        "hardware": {"gpu": "fake-gpu", "vram_bytes": 12_000_000_000},
        "execution_order": [
            "form-p2",
            "form-p3",
            "form-p4",
            "probe-p0",
            "probe-p1",
            "probe-p2",
            "probe-p3",
            "probe-p4",
            "probe-p5",
            "probe-p6",
        ],
        "retry_policy": {"automatic_retry": False, "semantic_retry": False},
        "authority": {
            "status": "CURRENT_AUTHORITY_CONFIRMED",
            "commit": repository.commit,
        },
        "launch_admission": launch,
    }


def _live_binding(repository: S2RepositoryState) -> dict[str, object]:
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


def _responses(seed: int = 2211) -> tuple[object, list[str]]:
    family = generate_transfer_family(seed=seed, regime="shared")
    learned = json.dumps(
        {
            "permutation": list(family.source_rule.permutation),
            "offsets": list(family.source_rule.offsets),
            "modulus": family.modulus,
        },
        separators=(",", ":"),
    )
    target = json.dumps(list(family.expected_output(0)), separators=(",", ":"))
    return family, [
        '{"summary":"faithful concise recap of the observed episodes"}',
        '{"gist":"compact reusable semantic gist from the observed episodes"}',
        learned,
        target,
        target,
        target,
        target,
        target,
        target,
        target,
    ]


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
            input_tokens=17,
            output_tokens=6,
            response_id=f"fake-{len(self.calls)}",
        )


def test_s2_host_git_probe_reads_commit_tree_and_cleanliness(tmp_path: Path):
    repository_root, expected = _git_repo(tmp_path / "repo")
    assert probe_s2_git_repository(repository_root) == expected

    (repository_root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    observed = probe_s2_git_repository(repository_root)
    assert observed.commit == expected.commit
    assert observed.tree == expected.tree
    assert observed.clean is False


def test_s2_host_rejects_dirty_or_wrong_repository_before_artifacts_and_calls(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    (repository_root / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    root = tmp_path / "artifact"
    client = FakeClient(responses)

    with pytest.raises(S2HostError, match="repository"):
        run_s2_host_smoke(
            artifact_root=root,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=lambda: _live_binding(state),
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )
    assert client.calls == []
    assert not (root / "run-manifest.json").exists()

    repository_root, state = _git_repo(tmp_path / "wrong-repo")
    identity = _identity(state)
    identity["repository"] = {**identity["repository"], "commit": "c" * 40}
    root = tmp_path / "wrong-artifact"
    client = FakeClient(responses.copy())
    with pytest.raises(S2HostError, match="repository"):
        run_s2_host_smoke(
            artifact_root=root,
            identity=identity,
            repository_root=repository_root,
            live_binding_probe=lambda: _live_binding(state),
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )
    assert client.calls == []
    assert not (root / "run-manifest.json").exists()


def test_s2_host_requires_repo_external_fresh_artifact_root(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")

    inside = repository_root / "artifact"
    with pytest.raises(S2HostError, match="outside"):
        run_s2_host_smoke(
            artifact_root=inside,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=lambda: _live_binding(state),
            client=FakeClient(responses.copy()),
            family=family,
            step_index=0,
            examples_visible=0,
        )

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "stale.json").write_text("{}", encoding="utf-8")
    with pytest.raises(S2HostError, match="artifact root"):
        run_s2_host_smoke(
            artifact_root=occupied,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=lambda: _live_binding(state),
            client=FakeClient(responses.copy()),
            family=family,
            step_index=0,
            examples_visible=0,
        )


def test_s2_host_writes_frozen_manifest_before_first_call_and_completes_exact_ten_calls(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    root = tmp_path / "run"
    client = FakeClient(responses, manifest_path=root / "run-manifest.json")

    result = run_s2_host_smoke(
        artifact_root=root,
        identity=_identity(state),
        repository_root=repository_root,
        live_binding_probe=lambda: _live_binding(state),
        client=client,
        family=family,
        step_index=0,
        examples_visible=0,
    )

    assert len(client.calls) == 10
    assert result.provider_calls == 10
    assert result.status == "COMPLETED"
    assert result.claim_status == "NON_CITABLE_S2_SMOKE"
    assert result.citable is False
    assert result.arm_correctness == (True, True, True, True, True, True, True)

    manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
    assert manifest["identity"]["repository"] == {
        "commit": state.commit,
        "tree": state.tree,
        "clean_required": True,
    }
    assert manifest["identity"]["execution_order"] == _identity(state)["execution_order"]
    summary = json.loads((root / "s2-smoke-result.json").read_text(encoding="utf-8"))
    assert summary["claim_status"] == "NON_CITABLE_S2_SMOKE"
    assert summary["citable"] is False
    assert summary["provider_calls"] == 10
    assert [arm["kind"] for arm in summary["arms"]] == [
        "P0_RAW_HISTORY",
        "P1_RETRIEVAL_ONLY",
        "P2_ORDINARY_SUMMARY",
        "P3_SEMANTIC_CACHE",
        "P4_MEMORY_PLUS_STRUCTURE",
        "P5_STRUCTURE_ONLY_RECONSTRUCTABLE",
        "P6_GENERIC_EQUAL_INFORMATION",
    ]


def test_s2_host_rechecks_full_binding_before_every_call_and_stops_on_drift(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    stable = _live_binding(state)
    drifted = _live_binding(state)
    drifted["model"] = {"id": "other-model", "revision": "sha256:other"}
    probe_calls = 0

    def probe() -> dict[str, object]:
        nonlocal probe_calls
        probe_calls += 1
        if probe_calls < 5:
            return stable
        return drifted

    client = FakeClient(responses)
    root = tmp_path / "drift"
    with pytest.raises(S2HostError, match="physical binding drift"):
        run_s2_host_smoke(
            artifact_root=root,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=probe,
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    # preflight + one live check per successful call; drift happens before call 4.
    assert len(client.calls) == 3
    state_payload = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
    assert state_payload["status"] == "INCOMPLETE"
    evidence = (root / "request-evidence.jsonl").read_text(encoding="utf-8")
    assert "physical_binding_drift" in evidence


def test_s2_host_provider_failure_is_terminal_and_not_retried(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    responses[4] = "__FAIL__"
    client = FakeClient(responses)
    root = tmp_path / "provider-failure"

    with pytest.raises(S2HostError, match="provider"):
        run_s2_host_smoke(
            artifact_root=root,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=lambda: _live_binding(state),
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    assert len(client.calls) == 5
    state_payload = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
    assert state_payload["status"] == "INCOMPLETE"
    evidence = (root / "request-evidence.jsonl").read_text(encoding="utf-8")
    assert "provider_failure" in evidence


def test_s2_host_semantic_parse_failure_is_terminal_after_raw_exchange_is_preserved(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    responses[2] = '{"permutation":[0,1,2],"offsets":[0,0,0,0],"modulus":10}'
    client = FakeClient(responses)
    root = tmp_path / "protocol-failure"

    with pytest.raises(S2HostError, match="model protocol failure"):
        run_s2_host_smoke(
            artifact_root=root,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=lambda: _live_binding(state),
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    assert len(client.calls) == 3
    state_payload = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
    assert state_payload["status"] == "INCOMPLETE"
    evidence = (root / "request-evidence.jsonl").read_text(encoding="utf-8")
    assert "model_exchange" in evidence
    assert "model_protocol_failure" in evidence
    assert not (root / "s2-smoke-result.json").exists()


def test_s2_host_all_raw_exchange_evidence_is_instrumentation_only(tmp_path: Path):
    family, responses = _responses(seed=2311)
    repository_root, state = _git_repo(tmp_path / "repo")
    root = tmp_path / "evidence"

    result = run_s2_host_smoke(
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
    assert len(records) == 10
    assert all(record["evidence"]["authority"] == "instrumentation_only" for record in records)
    assert result.citable is False


def test_s2_host_rejects_retry_or_order_contract_before_model_calls(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")

    for label, mutate in (
        ("retry", lambda identity: identity["retry_policy"].update({"automatic_retry": True})),
        ("order", lambda identity: identity.update({"execution_order": list(reversed(identity["execution_order"]))})),
    ):
        identity = _identity(state)
        mutate(identity)
        client = FakeClient(responses.copy())
        root = tmp_path / label
        with pytest.raises(S2HostError):
            run_s2_host_smoke(
                artifact_root=root,
                identity=identity,
                repository_root=repository_root,
                live_binding_probe=lambda: _live_binding(state),
                client=client,
                family=family,
                step_index=0,
                examples_visible=0,
            )
        assert client.calls == []
        assert not (root / "run-manifest.json").exists()
