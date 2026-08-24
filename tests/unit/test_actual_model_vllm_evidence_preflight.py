from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import relaylm.actual_model_host as host_runner
import relaylm.actual_model_vllm_host as vllm_host
from relaylm.actual_model_fast_screening import REFERENCE_BASELINE_ROLE


REPO_ROOT = Path(__file__).resolve().parents[2]
CURRENT_PLAN_PATH = REPO_ROOT / vllm_host.CANONICAL_VLLM_SCREENING_PLAN_PATH
GOOGLE_PROOF_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "attestations"
    / "gemma-4-12b-it-qat-w4a16-google-vllm-reasoning-v1.json"
)


def test_clean_exact_repo_rejects_capacity_provenance_from_different_commit(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "relaylm-test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "RelayLM Test"],
        check=True,
    )
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "fixture"],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="capacity evidence RelayLM commit",
    ):
        vllm_host._verify_clean_exact_repo(
            root=repo,
            expected_commit=head,
            capacity_evidence_commit="b" * 40,
        )


def test_clean_exact_repo_allows_capacity_acquisition_without_prior_capacity_provenance(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "relaylm-test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "RelayLM Test"],
        check=True,
    )
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "fixture"],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    vllm_host._verify_clean_exact_repo(
        root=repo,
        expected_commit=head,
    )


def test_screening_preparation_carries_capacity_commit_into_exact_repo_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    assert plan.capacity_evidence_id is not None
    capacity = vllm_host.load_vllm_runtime_capacity_evidence(
        vllm_host.capacity_evidence_path(
            artifact_root=REPO_ROOT / vllm_host.CANONICAL_VLLM_CAPACITY_EVIDENCE_ROOT,
            evidence_id=plan.capacity_evidence_id,
        )
    )
    observed: dict[str, object] = {}

    def stop_after_repo_gate(**kwargs):
        observed.update(kwargs)
        raise vllm_host.ActualModelVLLMHostError("stop after exact repo gate")

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", stop_after_repo_gate)

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="stop after exact repo gate",
    ):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root="/tmp/unused",
            relaylm_commit="a" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
        )

    assert observed["expected_commit"] == "a" * 40
    assert observed["capacity_evidence_commit"] == capacity.relaylm_commit


def test_screening_facade_can_bind_fresh_external_capacity_without_rewriting_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical_plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    canonical_capacity_id = canonical_plan.capacity_evidence_id
    fresh_capacity_id = "amcap-" + "f" * 64
    capacity_root = tmp_path / "fresh-capacity"
    observed: dict[str, object] = {}

    def fake_prepare(**kwargs):
        observed["prepare"] = kwargs
        plan = kwargs["plan"]
        return SimpleNamespace(
            plan=plan,
            screening_condition_id=REFERENCE_BASELINE_ROLE,
            manifest=SimpleNamespace(relaylm_commit="a" * 40, replicate_id="0"),
            target=SimpleNamespace(
                target_id="gemma-4-12b-it-qat-w4a16-google-vllm-v1"
            ),
        )

    async def fake_execute(**kwargs):
        observed["execute"] = kwargs
        return (
            SimpleNamespace(
                to_mapping=lambda: {
                    "scenario_id": "response-persona-correction-v1",
                    "execution_id": "amvx-1",
                    "run_id": "amr-1",
                    "artifact_path": "/tmp/amvx-1.vllm.json",
                    "boundary_verdict_id": "ambv-1",
                    "boundary_outcome": "pass",
                    "boundary_artifact_path": "/tmp/ambv-1.json",
                }
            ),
        )

    monkeypatch.setattr(host_runner, "load_vllm_screening_plan", lambda _: canonical_plan)
    monkeypatch.setattr(host_runner, "_prepare_vllm_screening_condition", fake_prepare)
    monkeypatch.setattr(host_runner, "_execute_vllm_host_run", fake_execute)
    monkeypatch.setattr(host_runner, "_current_repo_head", lambda _: "a" * 40)

    result = host_runner.main(
        [
            "--backend",
            "vllm",
            "--operation",
            "screening",
            "--condition",
            REFERENCE_BASELINE_ROLE,
            "--model-runner",
            "v2",
            "--repo-root",
            str(tmp_path),
            "--snapshot-root",
            "/tmp/relaylm-google-gemma4",
            "--provider-base-url",
            "http://127.0.0.1:8000/v1",
            "--workspace-root",
            "/tmp/relaylm-vllm-work",
            "--artifact-root",
            "/tmp/relaylm-vllm-evidence",
            "--capacity-evidence-id",
            fresh_capacity_id,
            "--capacity-evidence-root",
            str(capacity_root),
        ]
    )

    assert result == 0
    prepared = observed["prepare"]
    assert prepared["condition_id"] == REFERENCE_BASELINE_ROLE
    assert prepared["plan"].capacity_evidence_id == fresh_capacity_id
    assert prepared["capacity_evidence_root"] == str(capacity_root)
    assert canonical_plan.capacity_evidence_id == canonical_capacity_id
