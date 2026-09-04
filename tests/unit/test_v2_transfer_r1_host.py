from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from relaylm.v2_transfer_experiment import generate_transfer_family
from tools.v2_transfer_r1_host import (
    R1HostError,
    RepositoryState,
    run_r1_host_smoke,
)


_COMMIT = "a" * 40
_TREE = "b" * 40


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


def _identity() -> dict[str, object]:
    launch = _launch_admission()
    return {
        "repository": {"commit": _COMMIT, "tree": _TREE, "clean_required": True},
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
        "authority": {"status": "CURRENT_AUTHORITY_CONFIRMED", "commit": _COMMIT},
        "launch_admission": launch,
    }


def _live_binding() -> dict[str, object]:
    identity = _identity()
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


def _repo_state(*, clean: bool = True, commit: str = _COMMIT, tree: str = _TREE) -> RepositoryState:
    return RepositoryState(commit=commit, tree=tree, clean=clean)


def test_r1_host_rejects_dirty_or_wrong_repository_before_artifacts_or_model_calls(tmp_path: Path):
    family, responses = _responses()
    for observed in (
        _repo_state(clean=False),
        _repo_state(commit="c" * 40),
        _repo_state(tree="d" * 40),
    ):
        root = tmp_path / observed.commit[:4] / observed.tree[:4] / str(observed.clean)
        client = FakeClient(responses.copy())
        with pytest.raises(R1HostError, match="repository"):
            run_r1_host_smoke(
                artifact_root=root,
                identity=_identity(),
                repository_probe=lambda observed=observed: observed,
                live_binding_probe=_live_binding,
                client=client,
                family=family,
                step_index=0,
                examples_visible=0,
            )
        assert not (root / "run-manifest.json").exists()
        assert client.calls == []


def test_r1_host_requires_fresh_empty_artifact_root(tmp_path: Path):
    family, responses = _responses()
    root = tmp_path / "occupied"
    root.mkdir()
    (root / "stale.json").write_text("{}", encoding="utf-8")

    with pytest.raises(R1HostError, match="artifact root"):
        run_r1_host_smoke(
            artifact_root=root,
            identity=_identity(),
            repository_probe=_repo_state,
            live_binding_probe=_live_binding,
            client=FakeClient(responses),
            family=family,
            step_index=0,
            examples_visible=0,
        )


def test_r1_host_writes_frozen_manifest_before_first_model_call_and_uses_one_client(tmp_path: Path):
    family, responses = _responses()
    root = tmp_path / "run"
    client = FakeClient(responses, manifest_path=root / "run-manifest.json")

    result = run_r1_host_smoke(
        artifact_root=root,
        identity=_identity(),
        repository_probe=_repo_state,
        live_binding_probe=_live_binding,
        client=client,
        family=family,
        step_index=0,
        examples_visible=0,
    )

    assert len(client.calls) == 4
    manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
    assert manifest["identity"]["repository"] == {
        "commit": _COMMIT,
        "tree": _TREE,
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
    stable = _live_binding()
    drifted = _live_binding()
    drifted["model"] = {"id": "different-model", "revision": "sha256:other"}
    observations = [stable, stable, drifted]

    def probe() -> dict[str, object]:
        return observations.pop(0) if observations else drifted

    client = FakeClient(responses)
    root = tmp_path / "drift"
    with pytest.raises(R1HostError, match="physical binding drift"):
        run_r1_host_smoke(
            artifact_root=root,
            identity=_identity(),
            repository_probe=_repo_state,
            live_binding_probe=probe,
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    # Initial preflight + source-call check succeed; T0 is blocked before its request.
    assert len(client.calls) == 1
    state = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
    assert state["status"] == "INCOMPLETE"


def test_r1_host_provider_failure_is_terminal_and_never_retried_with_changed_settings(tmp_path: Path):
    family, responses = _responses()
    responses[1] = "__FAIL__"
    client = FakeClient(responses)
    root = tmp_path / "failure"

    with pytest.raises(R1HostError, match="provider"):
        run_r1_host_smoke(
            artifact_root=root,
            identity=_identity(),
            repository_probe=_repo_state,
            live_binding_probe=_live_binding,
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    assert len(client.calls) == 2
    state = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
    assert state["status"] == "INCOMPLETE"
    evidence = (root / "request-evidence.jsonl").read_text(encoding="utf-8")
    assert "provider_failure" in evidence


def test_r1_host_records_non_authoritative_raw_outputs_without_promoting_a_transfer_claim(tmp_path: Path):
    family, responses = _responses(seed=2162)
    root = tmp_path / "evidence"
    result = run_r1_host_smoke(
        artifact_root=root,
        identity=_identity(),
        repository_probe=_repo_state,
        live_binding_probe=_live_binding,
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
    for key, value in (
        ("retry_policy", {"automatic_retry": True, "semantic_retry": False}),
        ("execution_order", ["source-learning", "t1", "t0", "t2"]),
    ):
        identity = _identity()
        identity[key] = value
        with pytest.raises(R1HostError, match=key.replace("_", " ")):
            run_r1_host_smoke(
                artifact_root=tmp_path / key,
                identity=identity,
                repository_probe=_repo_state,
                live_binding_probe=_live_binding,
                client=FakeClient(responses.copy()),
                family=family,
                step_index=0,
                examples_visible=0,
            )
