from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import relaylm.actual_model_vllm_capacity_acquisition as capacity_acquisition
from relaylm.actual_model_vllm_host import load_vllm_screening_plan


REPO_ROOT = Path(__file__).resolve().parents[2]
V3_PLAN_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "screenings"
    / "stage-r0-vllm-reference-v3.json"
)
PROOF_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "attestations"
    / "gemma-4-12b-it-qat-w4a16-google-vllm-reasoning-v1.json"
)


def _live_fetch(snapshot_root: Path):
    def fetch(url: str, _: str | None) -> object:
        if url.endswith("/version"):
            return {"version": "0.26.1rc1.dev549+g70b84f0bc"}
        if url.endswith("/v1/models"):
            return {
                "object": "list",
                "data": [
                    {
                        "id": "gemma-4-12B-it-qat-w4a16",
                        "object": "model",
                        "root": str(snapshot_root),
                        "max_model_len": 4096,
                    }
                ],
            }
        raise AssertionError(f"unexpected URL: {url}")

    return fetch


def _prepare_v3(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    plan = load_vllm_screening_plan(V3_PLAN_PATH)
    target = capacity_acquisition.load_actual_model_repository_snapshot_target(
        REPO_ROOT / capacity_acquisition.CANONICAL_VLLM_TARGET_PATH
    )
    snapshot_root = tmp_path / "snapshot"
    snapshot_root.mkdir()

    monkeypatch.setattr(
        capacity_acquisition,
        "_verify_clean_exact_repo",
        lambda **_: None,
    )
    monkeypatch.setattr(
        capacity_acquisition,
        "verify_actual_model_repository_snapshot",
        lambda **_: capacity_acquisition.ActualModelRepositorySnapshotVerification(
            target_id=target.target_id,
            target_revision=target.revision,
            verified_file_count=len(target.files),
        ),
    )

    return capacity_acquisition.prepare_vllm_capacity_acquisition(
        plan=plan,
        condition_id="reference_baseline",
        proof_path=PROOF_PATH,
        repo_root=REPO_ROOT,
        snapshot_root=snapshot_root,
        relaylm_commit="a" * 40,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        model_runner="v2",
        fetch_json=_live_fetch(snapshot_root),
    )


def test_capacity_acquisition_binds_foundation_v3_from_execution_template(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_v3(tmp_path=tmp_path, monkeypatch=monkeypatch)
    try:
        assert prepared.plan.scenario_set_path == (
            "evaluation/actual_model/scenario_sets/foundation-v3.json"
        )
        assert prepared.scenario_set.revision == prepared.plan.scenario_set_revision
        assert prepared.scenario_set.scenario_set_version == "actual-model-foundation-v3"
        assert prepared.scenario_ids == (
            "response-transcript-fidelity-v1",
            "response-false-attribution-resistance-v1",
            "continuity-lifecycle-v1",
        )
        for scenario_id in prepared.scenario_ids:
            prepared.scenario_set.scenario(scenario_id)
    finally:
        asyncio.run(prepared.provider.aclose())
