from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
from typing import Mapping

import pytest

from tools.v2_cognitive_work_structured_output_qualification import (
    StructuredOutputCompletion,
    StructuredOutputQualificationError,
)
from tools.v2_transfer_q1_host import (
    CALIBRATION_CANDIDATE,
    CALIBRATION_CLAIM,
    CALIBRATION_HARNESS,
    CALIBRATION_RESULT_NAME,
    QUALIFICATION_CANDIDATE,
    QUALIFICATION_HARNESS,
    QUALIFICATION_RESULT_NAME,
    Q1HostError,
    calibration_benchmark_identity,
    calibration_execution_order,
    material_binding_fields,
    qualification_benchmark_identity,
    qualification_execution_order,
    run_q1_calibration_host,
    run_q1_qualification_host,
)
from tools.v2_transfer_q1_structured_client import Q1PlanStructuredClient
from tools.v2_transfer_q1_target_range import (
    CALIBRATION_SELECTED,
    CANDIDATES,
    calibration_call_plan,
    generate_family,
    qualification_call_plan,
    transport_identity,
)
from tools.v2_transfer_r1_host import RepositoryState
from tools.v2_transfer_qualification import PASS


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _repo(root: Path) -> tuple[Path, RepositoryState]:
    root.mkdir(parents=True)
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True, text=True)
    _git(root, "config", "user.email", "q1@example.invalid")
    _git(root, "config", "user.name", "Q1 Test")
    (root / "tracked.txt").write_text("q1\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "fixture")
    return root, RepositoryState(_git(root, "rev-parse", "HEAD"), _git(root, "rev-parse", "HEAD^{tree}"), True)


def _launch() -> dict[str, object]:
    return {
        "backend": "fake-backend", "runtime": "fake-runtime", "model_runner": "fake-runner",
        "effective_gpu_reservation": 0.9, "admitted_context": 8192,
        "capacity_evidence": {"kind": "bounded", "tokens": 8192},
        "launch_evidence_reference": "local://launch",
        "runtime_ownership_evidence_reference": "local://runtime",
    }


def _base(state: RepositoryState) -> dict[str, object]:
    return {
        "repository": {"commit": state.commit, "tree": state.tree, "clean_required": True},
        "candidate": "", "prompt_core": "q1-target", "benchmark": {},
        "dataset": {"kind": "deterministic-q1"}, "harness": "", "adapter": "q1-json-schema",
        "model": {"id": "test-model"}, "artifact": {"revision": "sha256:artifact"},
        "tokenizer": {"revision": "sha256:tokenizer"}, "template": {"revision": "sha256:template"},
        "backend": "fake-backend", "runtime": "fake-runtime",
        "decoding": {"temperature": "omitted", "top_p": "omitted", "seed": "omitted", "max_tokens": "omitted"},
        "reasoning": {"mode": "provider-default", "request_override": "omitted"},
        "structured_output": {}, "context_capacity": 8192,
        "capacity_evidence": {"kind": "bounded", "tokens": 8192},
        "hardware": {"gpu": "fake"}, "execution_order": [],
        "retry_policy": {"automatic_retry": False, "semantic_retry": False},
        "authority": {"status": "CURRENT_AUTHORITY_CONFIRMED", "commit": state.commit},
        "launch_admission": _launch(),
    }


def _cal_identity(state: RepositoryState) -> dict[str, object]:
    value = _base(state)
    plan = calibration_call_plan(state.commit)
    value.update(candidate=CALIBRATION_CANDIDATE, harness=CALIBRATION_HARNESS,
                 benchmark=calibration_benchmark_identity(state.commit),
                 structured_output=transport_identity(plan),
                 execution_order=calibration_execution_order(state.commit))
    return value


def _qual_identity(state: RepositoryState, calibration: Mapping[str, object]) -> dict[str, object]:
    candidate_id = calibration["selected_candidate_id"]
    assert isinstance(candidate_id, str)
    value = _base(state)
    plan = qualification_call_plan(state.commit, candidate_id)
    value.update(candidate=QUALIFICATION_CANDIDATE, harness=QUALIFICATION_HARNESS,
                 benchmark=qualification_benchmark_identity(state.commit, candidate_id, calibration),
                 structured_output=transport_identity(plan),
                 execution_order=qualification_execution_order(state.commit, candidate_id))
    return value


def _binding(identity: Mapping[str, object]) -> dict[str, object]:
    return deepcopy({name: identity[name] for name in material_binding_fields()})


def _wrong(entry) -> str:
    family = generate_family(entry.seed, entry.candidate_id)
    result = list(family.expected())
    result[0] = (result[0] + 1) % entry.modulus
    return json.dumps(result, separators=(",", ":"))


def _responses(plan, endpoint_counts: Mapping[str, int], level_counts: Mapping[int, int] | None = None) -> list[str]:
    output: list[str] = []
    for entry in plan:
        family = generate_family(entry.seed, entry.candidate_id)
        if level_counts is None:
            correct = entry.evidence_visible == 3 and entry.family_index < endpoint_counts[entry.candidate_id]
        else:
            correct = entry.family_index < level_counts[entry.evidence_visible]
        output.append(json.dumps(list(family.expected()), separators=(",", ":")) if correct else _wrong(entry))
    return output


class FakeStructured:
    def __init__(self, responses: list[str], fail_at: int | None = None, invalid_at: int | None = None) -> None:
        self.responses, self.fail_at, self.invalid_at = responses, fail_at, invalid_at
        self.calls: list[object] = []

    def complete(self, messages, *, response_format):
        index = len(self.calls)
        self.calls.append((messages, deepcopy(dict(response_format))))
        if self.fail_at == index:
            raise StructuredOutputQualificationError("synthetic provider failure")
        content = "[]" if self.invalid_at == index else self.responses[index]
        return StructuredOutputCompletion(content=content, input_tokens=10, output_tokens=3,
                                          response_id=f"fake-{index}", finish_reason="stop")


def _run_calibration(tmp_path: Path):
    repo, state = _repo(tmp_path / "repo")
    identity = _cal_identity(state)
    plan = calibration_call_plan(state.commit)
    counts = {
        CANDIDATES[0].candidate_id: 4,
        CANDIDATES[1].candidate_id: 2,
        CANDIDATES[2].candidate_id: 3,
        CANDIDATES[3].candidate_id: 0,
    }
    fake = FakeStructured(_responses(plan, counts))
    client = Q1PlanStructuredClient(call_plan=plan, structured_client=fake)
    probes = 0
    def probe():
        nonlocal probes
        probes += 1
        return _binding(identity)
    result = run_q1_calibration_host(artifact_root=tmp_path / "cal", identity=identity,
                                     repository_root=repo, live_binding_probe=probe,
                                     client=client, run_id="q1-cal-test")
    payload = json.loads((tmp_path / "cal" / CALIBRATION_RESULT_NAME).read_text())
    return repo, state, identity, fake, client, probes, result, payload


def test_calibration_is_complete_64_call_transaction_before_first_pass_selection(tmp_path: Path) -> None:
    _repo_root, _state, _identity, fake, client, probes, result, payload = _run_calibration(tmp_path)
    assert result.status == "COMPLETED" and result.citable is False
    assert result.claim_status == CALIBRATION_CLAIM
    assert result.verdict == CALIBRATION_SELECTED
    assert result.selected_candidate_id == CANDIDATES[1].candidate_id
    assert result.provider_calls == client.call_count == len(fake.calls) == 64
    assert probes == 65
    assert [x["endpoint_correct"] for x in payload["outcomes"]] == [4, 2, 3, 0]


def test_heldout_q1_is_separate_32_call_transaction_and_passes_only_through_classifier(tmp_path: Path) -> None:
    repo, state, _cal_identity_value, _fake, _client, _probes, _result, calibration = _run_calibration(tmp_path)
    candidate_id = calibration["selected_candidate_id"]
    identity = _qual_identity(state, calibration)
    plan = qualification_call_plan(state.commit, candidate_id)
    fake = FakeStructured(_responses(plan, {}, {0: 0, 1: 2, 2: 4, 3: 5}))
    client = Q1PlanStructuredClient(call_plan=plan, structured_client=fake)
    probes = 0
    def probe():
        nonlocal probes
        probes += 1
        return _binding(identity)
    result = run_q1_qualification_host(artifact_root=tmp_path / "qual", identity=identity,
                                       repository_root=repo, live_binding_probe=probe,
                                       client=client, calibration_result=calibration,
                                       run_id="q1-qual-test")
    payload = json.loads((tmp_path / "qual" / QUALIFICATION_RESULT_NAME).read_text())
    assert result.verdict == PASS and result.citable is True
    assert result.provider_calls == client.call_count == len(fake.calls) == 32
    assert probes == 33
    assert payload["q1_result"]["evidence_level_correct"] == [0, 2, 4, 5]
    assert payload["q1_result"]["structure_origin"] == "NONE"
    assert payload["q1_result"]["replaced_seed_count"] == 0


def test_protocol_failure_stops_without_repair_or_later_calls(tmp_path: Path) -> None:
    repo, state = _repo(tmp_path / "repo")
    identity = _cal_identity(state)
    plan = calibration_call_plan(state.commit)
    counts = {x.candidate_id: 0 for x in CANDIDATES}
    fake = FakeStructured(_responses(plan, counts), invalid_at=7)
    client = Q1PlanStructuredClient(call_plan=plan, structured_client=fake)
    with pytest.raises(Q1HostError, match="model protocol failure"):
        run_q1_calibration_host(artifact_root=tmp_path / "artifact", identity=identity,
                                repository_root=repo, live_binding_probe=lambda: _binding(identity),
                                client=client)
    assert len(fake.calls) == client.call_count == 8
    assert not (tmp_path / "artifact" / CALIBRATION_RESULT_NAME).exists()
    assert json.loads((tmp_path / "artifact" / "run-state.json").read_text())["status"] == "INCOMPLETE"


def test_provider_failure_consumes_failed_slot_and_never_retries(tmp_path: Path) -> None:
    repo, state = _repo(tmp_path / "repo")
    identity = _cal_identity(state)
    plan = calibration_call_plan(state.commit)
    fake = FakeStructured(_responses(plan, {x.candidate_id: 0 for x in CANDIDATES}), fail_at=5)
    client = Q1PlanStructuredClient(call_plan=plan, structured_client=fake)
    with pytest.raises(Q1HostError, match="provider client failure"):
        run_q1_calibration_host(artifact_root=tmp_path / "artifact", identity=identity,
                                repository_root=repo, live_binding_probe=lambda: _binding(identity),
                                client=client)
    assert len(fake.calls) == client.call_count == 6


def test_binding_drift_fails_before_affected_provider_call(tmp_path: Path) -> None:
    repo, state = _repo(tmp_path / "repo")
    identity = _cal_identity(state)
    plan = calibration_call_plan(state.commit)
    fake = FakeStructured(_responses(plan, {x.candidate_id: 0 for x in CANDIDATES}))
    client = Q1PlanStructuredClient(call_plan=plan, structured_client=fake)
    probes = 0
    def probe():
        nonlocal probes
        probes += 1
        value = _binding(identity)
        if probes == 9:
            value["runtime"] = "drifted"
        return value
    with pytest.raises(Q1HostError, match="physical binding probe failure"):
        run_q1_calibration_host(artifact_root=tmp_path / "artifact", identity=identity,
                                repository_root=repo, live_binding_probe=probe, client=client)
    assert len(fake.calls) == client.call_count == 7
