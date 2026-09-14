from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.relay_physical_run as physical_runner
import tools.v1_external_qualification_llama_cpp_gate as gate


def _normalized_freeze() -> dict[str, object]:
    return {
        "status": "EXECUTION_FROZEN",
        "fingerprint": "sha256:" + "1" * 64,
        "physical_carriage": {
            "target": "v1:external-qualification",
            "backend": "llama.cpp",
            "resource_key": "llama-cpp:local-gpu",
            "registered": True,
        },
        "relaylm_release": {
            "commit": "a" * 40,
            "version": "1.0.0rc1",
        },
        "comparator_participant_identity": {
            "implementation": "hindsight",
            "source_revision": "b" * 40,
        },
    }


def test_gate_accepts_only_exact_registered_carriage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = _normalized_freeze()
    monkeypatch.setattr(gate, "validate_launch_readiness", lambda raw: frozen)

    result = gate.validate_physical_execution_freeze({"synthetic": True})
    assert result is frozen

    drift = _normalized_freeze()
    drift["physical_carriage"]["target"] = "v1:stage-r"
    monkeypatch.setattr(gate, "validate_launch_readiness", lambda raw: drift)
    with pytest.raises(
        gate.ExternalQualificationPhysicalGateError,
        match="registered v1 external-qualification",
    ):
        gate.validate_physical_execution_freeze({"synthetic": True})


def test_gate_rejects_pre_rc_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pre_rc = _normalized_freeze()
    pre_rc["status"] = "READY_EXCEPT_EXACT_RC"
    monkeypatch.setattr(gate, "validate_launch_readiness", lambda raw: pre_rc)

    with pytest.raises(
        gate.ExternalQualificationPhysicalGateError,
        match="EXECUTION_FROZEN",
    ):
        gate.validate_physical_execution_freeze({"synthetic": True})


def test_cli_emits_zero_generation_admission_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("{}\n", encoding="utf-8")
    frozen = _normalized_freeze()
    monkeypatch.setattr(gate, "validate_launch_readiness", lambda raw: frozen)

    assert gate.main(["--plan", str(plan)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "EXECUTION_FROZEN"
    assert receipt["target"] == "v1:external-qualification"
    assert receipt["relaylm_release_commit"] == "a" * 40
    assert receipt["semantic_generation_count"] == 0
    assert receipt["benchmark_question_count"] == 0
    assert receipt["judge_call_count"] == 0
    assert receipt["llama_server_launch_count"] == 0


def test_repository_registers_gate_through_shared_runner() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    targets = physical_runner._load_targets(repo_root)
    target = targets["v1:external-qualification"]

    assert target.branch == "v1"
    assert target.module == "tools.v1_external_qualification_llama_cpp_gate"
    assert target.required_distributions == ()
