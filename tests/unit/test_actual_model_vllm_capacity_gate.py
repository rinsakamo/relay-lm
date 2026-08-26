from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.actual_model_vllm_host as vllm_host
from relaylm.actual_model_vllm_capacity import load_vllm_runtime_capacity_evidence


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "screenings"
    / "cogp5-vllm-screening-v1.json"
)
CURRENT_PLAN_PATH = REPO_ROOT / vllm_host.CANONICAL_VLLM_SCREENING_PLAN_PATH
PROOF_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "attestations"
    / "gemma-4-12b-it-qat-w4a16-vllm-reasoning-v1.json"
)
HISTORICAL_CAPACITY_EVIDENCE_ID = (
    "amcap-2e39f7fd7bf8d32b2bc2be4263d5a3ce08f079319e76e59b104f236cce2464be"
)
CAPACITY_ROOT = REPO_ROOT / vllm_host.CANONICAL_VLLM_CAPACITY_EVIDENCE_ROOT


def _historical_capacity():
    path = CAPACITY_ROOT / f"{HISTORICAL_CAPACITY_EVIDENCE_ID}.json"
    return load_vllm_runtime_capacity_evidence(path), path


def test_historical_screening_plan_is_loadable_but_has_no_capacity_evidence() -> None:
    plan = vllm_host.load_vllm_screening_plan(PLAN_PATH)

    assert plan.screening_id == "cogp5-vllm-screening-v1"
    assert plan.effective_context_window == 1024
    assert plan.capacity_evidence_id is None


def test_historical_format_can_reference_citable_capacity_evidence(
    tmp_path: Path,
) -> None:
    raw = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    raw["capacity_evidence_id"] = "amcap-example-citable-evidence"
    path = tmp_path / "historical-screening.json"
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    plan = vllm_host.load_vllm_screening_plan(path)

    assert plan.capacity_evidence_id == "amcap-example-citable-evidence"
    assert tuple(plan.conditions) == ("A", "B", "C")


def test_current_plan_has_no_stale_capacity_binding() -> None:
    plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)

    assert plan.format_version == vllm_host.VLLM_SCREENING_PLAN_FORMAT_VERSION
    assert plan.capacity_evidence_id is None


def test_capacity_commit_requirement_never_waives_measurement_commit() -> None:
    plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    evidence, _ = _historical_capacity()

    assert vllm_host._capacity_evidence_commit_requirement(
        plan=plan,
        capacity_evidence=evidence,
        capacity_evidence_root=None,
    ) == evidence.relaylm_commit
    assert vllm_host._capacity_evidence_commit_requirement(
        plan=plan,
        capacity_evidence=evidence,
        capacity_evidence_root=CAPACITY_ROOT,
    ) == evidence.relaylm_commit


def test_current_prepare_passes_exact_external_measurement_commit_to_repo_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    evidence, _ = _historical_capacity()
    execution_plan = replace(plan, capacity_evidence_id=evidence.evidence_id)
    observed: dict[str, object] = {}

    class ExpectedStop(Exception):
        pass

    def capture_repo_gate(**kwargs):
        observed.update(kwargs)
        raise ExpectedStop

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", capture_repo_gate)

    with pytest.raises(ExpectedStop):
        vllm_host.prepare_vllm_screening_condition(
            plan=execution_plan,
            condition_id="reference_baseline",
            proof_path=PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root="/tmp/unused",
            relaylm_commit="f" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
            capacity_evidence_root=CAPACITY_ROOT,
        )

    assert observed["expected_commit"] == "f" * 40
    assert observed["capacity_evidence_commit"] == evidence.relaylm_commit


def test_current_plan_without_fresh_capacity_fails_before_repo_or_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    touched = False

    def forbidden(*args, **kwargs):
        nonlocal touched
        touched = True
        raise AssertionError("capacity gate must fail before external preparation work")

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", forbidden)
    monkeypatch.setattr(vllm_host, "verify_actual_model_repository_snapshot", forbidden)
    monkeypatch.setattr(vllm_host, "acquire_vllm_reasoning_capability", forbidden)

    with pytest.raises(vllm_host.ActualModelVLLMHostError, match="capacity.*evidence"):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id="reference_baseline",
            proof_path=PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root="/tmp/unused",
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
        )

    assert touched is False


def test_referenced_capacity_evidence_must_exist_before_repo_or_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    plan = replace(plan, capacity_evidence_id="amcap-missing-evidence")
    touched = False

    def forbidden(*args, **kwargs):
        nonlocal touched
        touched = True
        raise AssertionError("missing capacity artifact must fail before external work")

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", forbidden)
    monkeypatch.setattr(vllm_host, "verify_actual_model_repository_snapshot", forbidden)
    monkeypatch.setattr(vllm_host, "acquire_vllm_reasoning_capability", forbidden)

    with pytest.raises(vllm_host.ActualModelVLLMHostError, match="capacity.*evidence"):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id="reference_baseline",
            proof_path=PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root="/tmp/unused",
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
            capacity_evidence_root=tmp_path / "capacity",
        )

    assert touched is False
