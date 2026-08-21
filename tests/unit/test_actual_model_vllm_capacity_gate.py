from __future__ import annotations

import json
from pathlib import Path

import pytest

import relaylm.actual_model_vllm_host as vllm_host


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "screenings"
    / "cogp5-vllm-screening-v1.json"
)
PROOF_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "attestations"
    / "gemma-4-12b-it-qat-w4a16-vllm-reasoning-v1.json"
)


def test_historical_screening_plan_is_loadable_but_has_no_capacity_evidence() -> None:
    plan = vllm_host.load_vllm_screening_plan(PLAN_PATH)

    assert plan.screening_id == "cogp5-vllm-screening-v1"
    assert plan.effective_context_window == 1024
    assert plan.capacity_evidence_id is None


def test_future_screening_plan_can_reference_citable_capacity_evidence(
    tmp_path: Path,
) -> None:
    raw = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    raw["capacity_evidence_id"] = "amcap-example-citable-evidence"
    future_path = tmp_path / "future-screening.json"
    future_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    plan = vllm_host.load_vllm_screening_plan(future_path)

    assert plan.capacity_evidence_id == "amcap-example-citable-evidence"
    assert plan.effective_context_window == 1024
    assert tuple(plan.conditions) == ("A", "B", "C")


def test_historical_plan_fails_closed_before_snapshot_or_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = vllm_host.load_vllm_screening_plan(PLAN_PATH)
    touched = False

    def forbidden(*args, **kwargs):
        nonlocal touched
        touched = True
        raise AssertionError("capacity gate must fail before external preparation work")

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", forbidden)
    monkeypatch.setattr(vllm_host, "verify_actual_model_repository_snapshot", forbidden)
    monkeypatch.setattr(vllm_host, "acquire_vllm_reasoning_capability", forbidden)

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="capacity.*evidence",
    ):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id="A",
            proof_path=PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root="/tmp/unused",
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
        )

    assert touched is False


def test_referenced_capacity_evidence_must_exist_before_repo_or_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    raw["capacity_evidence_id"] = "amcap-missing-evidence"
    future_path = tmp_path / "future-screening.json"
    future_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    plan = vllm_host.load_vllm_screening_plan(future_path)
    touched = False

    def forbidden(*args, **kwargs):
        nonlocal touched
        touched = True
        raise AssertionError("missing capacity artifact must fail before external work")

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", forbidden)
    monkeypatch.setattr(vllm_host, "verify_actual_model_repository_snapshot", forbidden)
    monkeypatch.setattr(vllm_host, "acquire_vllm_reasoning_capability", forbidden)

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="capacity.*evidence",
    ):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id="A",
            proof_path=PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root="/tmp/unused",
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            capacity_evidence_root=tmp_path / "capacity",
        )

    assert touched is False
