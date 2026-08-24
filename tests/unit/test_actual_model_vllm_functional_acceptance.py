from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import relaylm.actual_model_host as host_runner
from relaylm.actual_model_vllm_host import (
    CANONICAL_VLLM_SCREENING_PLAN_PATH,
    load_vllm_screening_plan,
)


_ROOT = Path(__file__).parents[2]
_FUNCTIONAL_PLAN = Path(
    "evaluation/actual_model/screenings/stage-r0-vllm-functional-acceptance-v1.json"
)
_REFERENCE_BASELINE = "reference_baseline"


def test_functional_acceptance_plan_preserves_reference_semantics_with_roomy_window() -> None:
    canonical = load_vllm_screening_plan(_ROOT / CANONICAL_VLLM_SCREENING_PLAN_PATH)
    functional = load_vllm_screening_plan(_ROOT / _FUNCTIONAL_PLAN)

    assert canonical.screening_id == "stage-r0-vllm-reference-v2"
    assert canonical.effective_context_window == 1616
    assert canonical.capacity_evidence_id is not None

    assert functional.screening_id == "stage-r0-vllm-functional-acceptance-v1"
    assert functional.effective_context_window == 4096
    assert functional.capacity_evidence_id is None
    assert functional.target_id == canonical.target_id
    assert functional.decoding_config == canonical.decoding_config
    assert functional.decoding_capabilities == canonical.decoding_capabilities
    assert functional.execution_path == canonical.execution_path
    assert functional.continuity_runtime == canonical.continuity_runtime
    assert functional.scenario_ids == canonical.scenario_ids
    assert tuple(functional.conditions) == tuple(canonical.conditions)
    assert {
        key: value.to_mapping() for key, value in functional.conditions.items()
    } == {
        key: value.to_mapping() for key, value in canonical.conditions.items()
    }


def test_shared_host_can_select_repository_owned_functional_acceptance_plan(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    plan = SimpleNamespace(screening_id="stage-r0-vllm-functional-acceptance-v1")
    prepared = SimpleNamespace(
        plan=plan,
        screening_condition_id=_REFERENCE_BASELINE,
        manifest=SimpleNamespace(relaylm_commit="a" * 40, replicate_id="0"),
        target=SimpleNamespace(target_id="gemma-4-12b-it-qat-w4a16-google-vllm-v1"),
        reasoning_capability=SimpleNamespace(
            backend_attestation=SimpleNamespace(max_model_len=4096)
        ),
    )
    artifact = SimpleNamespace(
        to_mapping=lambda: {
            "evidence_id": "amcap-functional",
            "artifact_path": "/tmp/amcap-functional.json",
            "footprint_count": 12,
            "maximum_observed_input_tokens": 1540,
            "complete": True,
        }
    )
    observed: dict[str, object] = {}

    def fake_load(path):
        observed["plan_path"] = Path(path)
        return plan

    def fake_resolve(plan_arg, role):
        assert plan_arg is plan
        assert role == _REFERENCE_BASELINE
        return role

    def fake_prepare(**kwargs):
        observed["prepare"] = kwargs
        return prepared

    async def fake_execute(**kwargs):
        observed["execute"] = kwargs
        return artifact

    monkeypatch.setattr(host_runner, "load_vllm_screening_plan", fake_load)
    monkeypatch.setattr(host_runner, "screening_condition_key_for_role", fake_resolve)
    monkeypatch.setattr(host_runner, "_prepare_vllm_capacity_acquisition", fake_prepare)
    monkeypatch.setattr(host_runner, "_execute_vllm_capacity_acquisition", fake_execute)
    monkeypatch.setattr(host_runner, "_current_repo_head", lambda _: "a" * 40)

    result = host_runner.main(
        [
            "--backend",
            "vllm",
            "--operation",
            "capacity",
            "--condition",
            _REFERENCE_BASELINE,
            "--screening-plan",
            str(_FUNCTIONAL_PLAN),
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
    assert observed["plan_path"] == tmp_path / _FUNCTIONAL_PLAN
    assert observed["prepare"]["plan"] is plan
    output = capsys.readouterr().out
    assert '"suite": "stage-r0-vllm-functional-acceptance-v1"' in output
    assert '"observed_max_model_len": 4096' in output
