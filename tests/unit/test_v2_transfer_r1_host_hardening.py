from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import generate_transfer_family
from tools.v2_transfer_r1_host import R1HostError, RepositoryState, run_r1_host_smoke


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
    _git(root, "config", "user.email", "r1-hardening@example.invalid")
    _git(root, "config", "user.name", "R1 Host Hardening")
    (root / "tracked.txt").write_text("relaylm2-r1-host-hardening\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "fixture")
    return root, RepositoryState(
        commit=_git(root, "rev-parse", "HEAD"),
        tree=_git(root, "rev-parse", "HEAD^{tree}"),
        clean=True,
    )


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
            "repository_head": repository.commit,
        },
        "launch_admission": _launch_admission(),
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


class _FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[dict[str, str], ...]] = []

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        self.calls.append(messages)
        content = self.responses.pop(0)
        return ExperimentCompletion(
            content=content,
            input_tokens=11,
            output_tokens=5,
            response_id=f"fake-{len(self.calls)}",
        )


def test_r1_host_frozen_binding_cannot_follow_caller_identity_mutation(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    identity = _identity(state)
    stable = _live_binding(state)
    drifted = _live_binding(state)
    drifted["model"] = {"id": "different-model", "revision": "sha256:model"}
    probe_count = 0

    def probe() -> dict[str, object]:
        nonlocal probe_count
        probe_count += 1
        if probe_count == 1:
            return stable
        model = identity["model"]
        assert isinstance(model, dict)
        model["id"] = "different-model"
        return drifted

    client = _FakeClient(responses)
    root = tmp_path / "run"
    with pytest.raises(R1HostError, match="physical binding drift"):
        run_r1_host_smoke(
            artifact_root=root,
            identity=identity,
            repository_root=repository_root,
            live_binding_probe=probe,
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    assert client.calls == []
    manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
    assert manifest["identity"]["model"] == {
        "id": "test-model",
        "revision": "sha256:model",
    }
    state_payload = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
    assert state_payload["status"] == "INCOMPLETE"


def test_r1_host_rejects_artifact_root_inside_repository_before_creating_it(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    artifact_root = repository_root / "generated" / "r1"
    client = _FakeClient(responses)

    with pytest.raises(R1HostError, match="artifact root.*outside.*repository"):
        run_r1_host_smoke(
            artifact_root=artifact_root,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=lambda: _live_binding(state),
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    assert not artifact_root.exists()
    assert client.calls == []
    assert _git(repository_root, "status", "--porcelain=v1", "--untracked-files=normal") == ""
