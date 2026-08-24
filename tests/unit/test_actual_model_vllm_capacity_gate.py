from __future__ import annotations

import json
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


def _current_plan_and_capacity():
    plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    assert plan.capacity_evidence_id is not None
    evidence_path = (
        REPO_ROOT
        / vllm_host.CANONICAL_VLLM_CAPACITY_EVIDENCE_ROOT
        / f"{plan.capacity_evidence_id}.json"
    )
    return plan, load_vllm_runtime_capacity_evidence(evidence_path), evidence_path


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


def test_current_semantic_plan_allows_reviewed_tracked_capacity_commit_reuse() -> None:
    plan, evidence, _ = _current_plan_and_capacity()

    assert plan.format_version == vllm_host.VLLM_SCREENING_PLAN_FORMAT_VERSION
    assert evidence.relaylm_commit != ""
    assert (
        vllm_host._capacity_evidence_commit_requirement(
            plan=plan,
            capacity_evidence=evidence,
            capacity_evidence_root=None,
        )
        is None
    )


def test_external_capacity_override_keeps_exact_measurement_commit_requirement(
    tmp_path: Path,
) -> None:
    plan, evidence, _ = _current_plan_and_capacity()

    assert vllm_host._capacity_evidence_commit_requirement(
        plan=plan,
        capacity_evidence=evidence,
        capacity_evidence_root=tmp_path,
    ) == evidence.relaylm_commit


def test_current_prepare_passes_no_measurement_commit_for_tracked_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, _, _ = _current_plan_and_capacity()
    observed: dict[str, object] = {}

    class ExpectedStop(Exception):
        pass

    def capture_repo_gate(**kwargs):
        observed.update(kwargs)
        raise ExpectedStop

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", capture_repo_gate)

    with pytest.raises(ExpectedStop):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id="reference_baseline",
            proof_path=PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root="/tmp/unused",
            relaylm_commit="f" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
        )

    assert observed["expected_commit"] == "f" * 40
    assert observed["capacity_evidence_commit"] is None


def test_current_prepare_keeps_measurement_commit_for_external_capacity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, evidence, evidence_path = _current_plan_and_capacity()
    assert plan.capacity_evidence_id is not None
    external_root = tmp_path / "capacity"
    external_root.mkdir()
    (external_root / f"{plan.capacity_evidence_id}.json").write_bytes(
        evidence_path.read_bytes()
    )
    observed: dict[str, object] = {}

    class ExpectedStop(Exception):
        pass

    def capture_repo_gate(**kwargs):
        observed.update(kwargs)
        raise ExpectedStop

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", capture_repo_gate)

    with pytest.raises(ExpectedStop):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id="reference_baseline",
            proof_path=PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root="/tmp/unused",
            relaylm_commit="f" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
            capacity_evidence_root=external_root,
        )

    assert observed["capacity_evidence_commit"] == evidence.relaylm_commit


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
