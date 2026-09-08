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
from tools.v2_transfer_r1_structured_client import SOURCE_SCHEMA_NAME, TARGET_SCHEMA_NAME
from tools.v2_transfer_r1_host import RepositoryState
from tools.v2_transfer_r2_host import (
    CALL_PLAN_DIGEST,
    CANDIDATE_ID,
    CLAIM_STATUS,
    HARNESS_ID,
    HOST_FAILURE_NAME,
    PREREGISTRATION_COMMIT,
    PREREGISTRATION_DIGEST,
    RESULT_NAME,
    TRANSPORT_IDENTITY_DIGEST,
    R2TransferHostError,
    benchmark_identity,
    execution_order,
    run_r2_transfer_host_campaign,
)
from tools.v2_transfer_r2_prereg import (
    FAMILY_COUNT,
    PROVIDER_CALL_COUNT,
    R2PlanStructuredClient,
    generate_families,
    transport_identity,
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
    _git(root, "config", "user.email", "r2-host@example.invalid")
    _git(root, "config", "user.name", "R2 Host Test")
    (root / "tracked.txt").write_text("relaylm2-r2-host\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "fixture")
    return root, RepositoryState(
        commit=_git(root, "rev-parse", "HEAD"),
        tree=_git(root, "rev-parse", "HEAD^{tree}"),
        clean=True,
    )


def _launch_admission() -> dict[str, object]:
    return {
        "backend": "fake-backend",
        "runtime": "fake-runtime",
        "model_runner": "fake-runner",
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
        "candidate": CANDIDATE_ID,
        "prompt_core": "relaylm2-transfer-r2",
        "benchmark": benchmark_identity(),
        "dataset": {
            "kind": "deterministic-transfer-families",
            "preregistration_commit": PREREGISTRATION_COMMIT,
        },
        "harness": HARNESS_ID,
        "adapter": "relaylm2-transfer-r2-structured-plan-v1",
        "model": {"id": "test-model", "revision": "sha256:model"},
        "artifact": {"revision": "sha256:artifact"},
        "tokenizer": {"revision": "sha256:tokenizer"},
        "template": {"revision": "sha256:template"},
        "backend": "fake-backend",
        "runtime": "fake-runtime",
        "decoding": {
            "temperature": "omitted",
            "top_p": "omitted",
            "seed": "omitted",
            "max_tokens": "omitted",
        },
        "reasoning": {"mode": "provider-default", "request_override": "omitted"},
        "structured_output": transport_identity(PREREGISTRATION_COMMIT),
        "context_capacity": 8192,
        "capacity_evidence": {"kind": "bounded-test", "tokens": 8192},
        "hardware": {"gpu": "fake-gpu", "vram_bytes": 12_000_000_000},
        "execution_order": execution_order(),
        "retry_policy": {"automatic_retry": False, "semantic_retry": False},
        "authority": {
            "status": "CURRENT_AUTHORITY_CONFIRMED",
            "commit": repository.commit,
        },
        "launch_admission": _launch_admission(),
    }


def _binding(identity: Mapping[str, object]) -> dict[str, object]:
    names = (
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
    return deepcopy({name: identity[name] for name in names})


def _responses() -> list[str]:
    responses: list[str] = []
    for family in generate_families(PREREGISTRATION_COMMIT):
        responses.append(
            json.dumps(
                {
                    "permutation": list(family.source_rule.permutation),
                    "offsets": list(family.source_rule.offsets),
                    "modulus": family.source_rule.modulus,
                },
                separators=(",", ":"),
            )
        )
        target = json.dumps(list(family.expected_output(0)), separators=(",", ":"))
        responses.extend([target] * 12)
    assert len(responses) == PROVIDER_CALL_COUNT
    return responses


class FakeStructuredClient:
    def __init__(
        self,
        responses: list[str],
        *,
        fail_at: int | None = None,
        invalid_at: int | None = None,
    ) -> None:
        self.responses = list(responses)
        self.fail_at = fail_at
        self.invalid_at = invalid_at
        self.calls: list[tuple[tuple[dict[str, str], ...], Mapping[str, object]]] = []

    def complete(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        response_format: Mapping[str, object],
    ) -> StructuredOutputCompletion:
        index = len(self.calls)
        self.calls.append((messages, deepcopy(dict(response_format))))
        if self.fail_at == index:
            raise StructuredOutputQualificationError("synthetic provider failure")
        if index >= len(self.responses):
            raise AssertionError("unexpected fake provider call")
        content = "[]" if self.invalid_at == index else self.responses[index]
        return StructuredOutputCompletion(
            content=content,
            input_tokens=10 + index % 3,
            output_tokens=4,
            response_id=f"fake-{index}",
            finish_reason="stop",
        )


def _plan_client(fake: FakeStructuredClient) -> R2PlanStructuredClient:
    return R2PlanStructuredClient(
        preregistration_commit=PREREGISTRATION_COMMIT,
        structured_client=fake,
    )


def _read_state(root: Path) -> dict[str, object]:
    return json.loads((root / "run-state.json").read_text(encoding="utf-8"))


def test_r2_host_frozen_identity_is_exact() -> None:
    benchmark = benchmark_identity()
    assert benchmark["preregistration_commit"] == PREREGISTRATION_COMMIT
    assert benchmark["preregistration_digest"] == PREREGISTRATION_DIGEST
    assert benchmark["call_plan_digest"] == CALL_PLAN_DIGEST
    assert benchmark["provider_calls"] == PROVIDER_CALL_COUNT == 208
    assert benchmark["families"] == FAMILY_COUNT == 16
    assert len(execution_order()) == PROVIDER_CALL_COUNT
    assert transport_identity(PREREGISTRATION_COMMIT)["provider_call_count"] == 208
    assert TRANSPORT_IDENTITY_DIGEST.startswith("sha256:")


def test_r2_host_fake_complete_campaign_is_exact_208_with_209_binding_probes(
    tmp_path: Path,
) -> None:
    repository_root, state = _git_repo(tmp_path / "repo")
    identity = _identity(state)
    expected_binding = _binding(identity)
    probe_count = 0

    def live_probe() -> Mapping[str, object]:
        nonlocal probe_count
        probe_count += 1
        return deepcopy(expected_binding)

    fake = FakeStructuredClient(_responses())
    client = _plan_client(fake)
    root = tmp_path / "run"
    result = run_r2_transfer_host_campaign(
        artifact_root=root,
        identity=identity,
        repository_root=repository_root,
        live_binding_probe=live_probe,
        client=client,
        run_id="fake-r2-complete",
    )

    assert result.status == "COMPLETED"
    assert result.claim_status == CLAIM_STATUS
    assert result.citable is True
    assert result.provider_calls == PROVIDER_CALL_COUNT
    assert result.family_count == FAMILY_COUNT
    assert result.category == "TRANSFER_EFFECT_UNCAPTURED_OR_UNSTABLE"
    assert len(fake.calls) == PROVIDER_CALL_COUNT
    assert client.call_count == PROVIDER_CALL_COUNT
    assert client.next_plan_entry is None
    assert probe_count == PROVIDER_CALL_COUNT + 1 == 209

    schema_names = [
        call[1]["json_schema"]["name"]  # type: ignore[index]
        for call in fake.calls
    ]
    assert schema_names.count(SOURCE_SCHEMA_NAME) == 16
    assert schema_names.count(TARGET_SCHEMA_NAME) == 192

    result_payload = json.loads((root / RESULT_NAME).read_text(encoding="utf-8"))
    assert result_payload["status"] == "COMPLETED"
    assert result_payload["provider_calls"] == 208
    assert len(result_payload["family_outcomes"]) == 16
    assert result_payload["analysis"]["source_correct_rate"] == 1.0
    assert result_payload["analysis"]["ceiling_saturated_families"] == 16
    assert result_payload["resource_totals"]["physical"]["calls"] == 208
    assert _read_state(root)["status"] == "COMPLETED"
    assert not (root / HOST_FAILURE_NAME).exists()


def test_r2_host_provider_failure_spends_one_slot_then_stops_without_result(
    tmp_path: Path,
) -> None:
    repository_root, state = _git_repo(tmp_path / "repo")
    identity = _identity(state)
    expected_binding = _binding(identity)
    fake = FakeStructuredClient(_responses(), fail_at=17)
    client = _plan_client(fake)
    root = tmp_path / "run"

    with pytest.raises(R2TransferHostError, match="provider client failure"):
        run_r2_transfer_host_campaign(
            artifact_root=root,
            identity=identity,
            repository_root=repository_root,
            live_binding_probe=lambda: deepcopy(expected_binding),
            client=client,
        )

    assert len(fake.calls) == 18
    assert client.call_count == 18
    assert not (root / RESULT_NAME).exists()
    assert (root / HOST_FAILURE_NAME).exists()
    assert _read_state(root)["status"] == "INCOMPLETE"


def test_r2_host_target_protocol_drift_is_not_rewritten_as_scientific_false(
    tmp_path: Path,
) -> None:
    repository_root, state = _git_repo(tmp_path / "repo")
    identity = _identity(state)
    expected_binding = _binding(identity)
    fake = FakeStructuredClient(_responses(), invalid_at=5)
    client = _plan_client(fake)
    root = tmp_path / "run"

    with pytest.raises(R2TransferHostError, match="structured answer contract"):
        run_r2_transfer_host_campaign(
            artifact_root=root,
            identity=identity,
            repository_root=repository_root,
            live_binding_probe=lambda: deepcopy(expected_binding),
            client=client,
        )

    assert len(fake.calls) == 6
    assert client.call_count == 6
    assert not (root / RESULT_NAME).exists()
    failure = json.loads((root / HOST_FAILURE_NAME).read_text(encoding="utf-8"))
    assert failure["kind"] == "model_protocol_failure"
    assert _read_state(root)["status"] == "INCOMPLETE"


def test_r2_host_binding_drift_stops_before_affected_provider_attempt(
    tmp_path: Path,
) -> None:
    repository_root, state = _git_repo(tmp_path / "repo")
    identity = _identity(state)
    stable = _binding(identity)
    probes = 0

    def live_probe() -> Mapping[str, object]:
        nonlocal probes
        probes += 1
        observed = deepcopy(stable)
        if probes == 12:  # preflight=1; probe 12 precedes planned provider call 10.
            observed["runtime"] = "drifted-runtime"
        return observed

    fake = FakeStructuredClient(_responses())
    client = _plan_client(fake)
    root = tmp_path / "run"

    with pytest.raises(R2TransferHostError, match="physical binding drift"):
        run_r2_transfer_host_campaign(
            artifact_root=root,
            identity=identity,
            repository_root=repository_root,
            live_binding_probe=live_probe,
            client=client,
        )

    assert probes == 12
    assert len(fake.calls) == 10
    assert client.call_count == 10
    assert not (root / RESULT_NAME).exists()
    assert _read_state(root)["status"] == "INCOMPLETE"


def test_r2_host_rejects_dirty_wrong_repo_and_occupied_artifact_before_provider_calls(
    tmp_path: Path,
) -> None:
    repository_root, state = _git_repo(tmp_path / "repo")
    identity = _identity(state)
    expected_binding = _binding(identity)

    (repository_root / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    fake = FakeStructuredClient(_responses())
    with pytest.raises(R2TransferHostError, match="repository checkout is dirty"):
        run_r2_transfer_host_campaign(
            artifact_root=tmp_path / "dirty-run",
            identity=identity,
            repository_root=repository_root,
            live_binding_probe=lambda: deepcopy(expected_binding),
            client=_plan_client(fake),
        )
    assert fake.calls == []

    repository_root2, state2 = _git_repo(tmp_path / "repo2")
    wrong_identity = _identity(state2)
    wrong_identity["repository"] = {
        "commit": "c" * 40,
        "tree": state2.tree,
        "clean_required": True,
    }
    fake2 = FakeStructuredClient(_responses())
    with pytest.raises(R2TransferHostError, match="repository commit"):
        run_r2_transfer_host_campaign(
            artifact_root=tmp_path / "wrong-run",
            identity=wrong_identity,
            repository_root=repository_root2,
            live_binding_probe=lambda: _binding(_identity(state2)),
            client=_plan_client(fake2),
        )
    assert fake2.calls == []

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "stale.json").write_text("{}", encoding="utf-8")
    identity2 = _identity(state2)
    stable2 = _binding(identity2)
    fake3 = FakeStructuredClient(_responses())
    with pytest.raises(R2TransferHostError, match="artifact root"):
        run_r2_transfer_host_campaign(
            artifact_root=occupied,
            identity=identity2,
            repository_root=repository_root2,
            live_binding_probe=lambda: deepcopy(stable2),
            client=_plan_client(fake3),
        )
    assert fake3.calls == []


def test_r2_host_rejects_mutated_scientific_identity_before_provider_calls(
    tmp_path: Path,
) -> None:
    repository_root, state = _git_repo(tmp_path / "repo")
    cases: list[tuple[str, object]] = [
        ("benchmark", {**benchmark_identity(), "provider_calls": 207}),
        ("structured_output", {**transport_identity(PREREGISTRATION_COMMIT), "provider_call_count": 207}),
        ("execution_order", execution_order()[:-1]),
        ("retry_policy", {"automatic_retry": True, "semantic_retry": False}),
    ]
    for index, (field, value) in enumerate(cases):
        identity = _identity(state)
        identity[field] = value
        fake = FakeStructuredClient(_responses())
        with pytest.raises(R2TransferHostError):
            run_r2_transfer_host_campaign(
                artifact_root=tmp_path / f"invalid-{index}",
                identity=identity,
                repository_root=repository_root,
                live_binding_probe=lambda identity=identity: _binding(identity),
                client=_plan_client(fake),
            )
        assert fake.calls == []


def test_r2_host_deep_freezes_identity_before_live_probe_mutates_caller(
    tmp_path: Path,
) -> None:
    repository_root, state = _git_repo(tmp_path / "repo")
    identity = _identity(state)
    stable = _binding(identity)
    mutated = False

    def live_probe() -> Mapping[str, object]:
        nonlocal mutated
        if not mutated:
            identity["model"] = {"id": "mutated-after-freeze", "revision": "bad"}
            mutated = True
        return deepcopy(stable)

    fake = FakeStructuredClient(_responses())
    result = run_r2_transfer_host_campaign(
        artifact_root=tmp_path / "run",
        identity=identity,
        repository_root=repository_root,
        live_binding_probe=live_probe,
        client=_plan_client(fake),
    )
    assert mutated is True
    assert result.status == "COMPLETED"
    assert len(fake.calls) == 208
