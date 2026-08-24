from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import relaylm.actual_model_host as host_runner


_ROOT = Path(__file__).parents[2]
_REMOVED_FIXED_PLAN = Path(
    "evaluation/actual_model/screenings/stage-r0-vllm-functional-acceptance-v1.json"
)
_REFERENCE_BASELINE = "reference_baseline"


@dataclass(frozen=True)
class _Plan:
    screening_id: str
    effective_context_window: int
    capacity_evidence_id: str | None = None


def test_functional_acceptance_has_no_fixed_repository_context_window() -> None:
    assert not (_ROOT / _REMOVED_FIXED_PLAN).exists()


def test_shared_host_binds_screening_window_to_live_capacity_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plan = _Plan(
        screening_id="stage-r0-vllm-reference-v2",
        effective_context_window=1616,
        capacity_evidence_id="tracked-capacity",
    )
    observed: dict[str, object] = {}

    def fake_load(path):
        observed["plan_path"] = Path(path)
        return plan

    def fake_resolve(plan_arg, role):
        assert plan_arg is plan
        assert role == _REFERENCE_BASELINE
        return role

    def fake_load_capacity(path):
        observed["capacity_path"] = Path(path)
        return SimpleNamespace(observed_max_model_len=6144)

    def fake_prepare(**kwargs):
        observed["prepare"] = kwargs
        resolved_plan = kwargs["plan"]
        return SimpleNamespace(
            plan=resolved_plan,
            screening_condition_id=_REFERENCE_BASELINE,
            manifest=SimpleNamespace(
                relaylm_commit="a" * 40,
                replicate_id="0",
                effective_context_window=resolved_plan.effective_context_window,
            ),
            target=SimpleNamespace(
                target_id="gemma-4-12b-it-qat-w4a16-google-vllm-v1"
            ),
        )

    async def fake_execute(**kwargs):
        observed["execute"] = kwargs
        return ()

    monkeypatch.setattr(host_runner, "load_vllm_screening_plan", fake_load)
    monkeypatch.setattr(host_runner, "screening_condition_key_for_role", fake_resolve)
    monkeypatch.setattr(
        host_runner,
        "load_vllm_runtime_capacity_evidence",
        fake_load_capacity,
    )
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
            _REFERENCE_BASELINE,
            "--context-window-from-capacity-evidence",
            "--capacity-evidence-id",
            "amcap-live",
            "--capacity-evidence-root",
            "/tmp/relaylm-vllm-evidence",
            "--model-runner",
            "v2",
            "--repo-root",
            str(tmp_path),
            "--snapshot-root",
            "/tmp/relaylm-google-gemma4-official-attest.CKxAGh",
            "--provider-base-url",
            "http://127.0.0.1:8000/v1",
            "--workspace-root",
            "/tmp/relaylm-vllm-work",
            "--artifact-root",
            "/tmp/relaylm-vllm-evidence",
        ]
    )

    assert result == 0
    prepare = observed["prepare"]
    assert isinstance(prepare, dict)
    prepared_plan = prepare["plan"]
    assert isinstance(prepared_plan, _Plan)
    assert prepared_plan.effective_context_window == 6144
    assert prepared_plan.capacity_evidence_id == "amcap-live"
