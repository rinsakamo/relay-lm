from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import relaylm.actual_model_host as host_runner


CURRENT_SCREENING_ID = "stage-r0-vllm-reference-v2"
REFERENCE_BASELINE_ROLE = "reference_baseline"


def test_shared_host_runner_dispatches_current_vllm_reference_by_semantic_role(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    plan = SimpleNamespace(screening_id=CURRENT_SCREENING_ID)
    prepared = SimpleNamespace(
        plan=plan,
        screening_condition_id=REFERENCE_BASELINE_ROLE,
        manifest=SimpleNamespace(relaylm_commit="a" * 40, replicate_id="0"),
        target=SimpleNamespace(target_id="gemma-4-12b-it-qat-w4a16-google-vllm-v1"),
    )
    observed: dict[str, object] = {}

    def fake_resolve(plan_arg, role):
        observed["role"] = role
        assert plan_arg is plan
        assert role == REFERENCE_BASELINE_ROLE
        return role

    def fake_prepare(**kwargs):
        observed["prepare"] = kwargs
        return prepared

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

    monkeypatch.setattr(host_runner, "load_vllm_screening_plan", lambda _: plan)
    monkeypatch.setattr(host_runner, "screening_condition_key_for_role", fake_resolve)
    monkeypatch.setattr(host_runner, "_prepare_vllm_screening_condition", fake_prepare)
    monkeypatch.setattr(host_runner, "_execute_vllm_host_run", fake_execute)
    monkeypatch.setattr(host_runner, "_current_repo_head", lambda _: "a" * 40)

    result = host_runner.main(
        [
            "--backend",
            "vllm",
            "--condition",
            REFERENCE_BASELINE_ROLE,
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
    assert observed["role"] == REFERENCE_BASELINE_ROLE
    assert observed["prepare"]["plan"] is plan
    assert observed["prepare"]["condition_id"] == REFERENCE_BASELINE_ROLE
    assert observed["prepare"]["model_runner"] == "v2"
    assert observed["prepare"]["base_url"] == "http://127.0.0.1:8000/v1"
    assert observed["execute"]["snapshot_root"] == (
        "/tmp/relaylm-google-gemma4-official-attest.CKxAGh"
    )
    output = capsys.readouterr().out
    assert f'"suite": "{CURRENT_SCREENING_ID}"' in output
    assert f'"condition": "{REFERENCE_BASELINE_ROLE}"' in output
    assert '"operation": "screening"' in output


def test_shared_host_runner_dispatches_vllm_capacity_by_semantic_role(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    plan = SimpleNamespace(screening_id=CURRENT_SCREENING_ID)
    prepared = SimpleNamespace(
        plan=plan,
        screening_condition_id=REFERENCE_BASELINE_ROLE,
        manifest=SimpleNamespace(relaylm_commit="a" * 40, replicate_id="0"),
        target=SimpleNamespace(target_id="gemma-4-12b-it-qat-w4a16-google-vllm-v1"),
        reasoning_capability=SimpleNamespace(
            backend_attestation=SimpleNamespace(max_model_len=1536)
        ),
    )
    artifact = SimpleNamespace(
        to_mapping=lambda: {
            "evidence_id": "amcap-1",
            "artifact_path": "/tmp/amcap-1.json",
            "footprint_count": 6,
            "maximum_observed_input_tokens": 1200,
            "complete": True,
        }
    )
    observed: dict[str, object] = {}

    def fake_resolve(plan_arg, role):
        observed["role"] = role
        assert plan_arg is plan
        assert role == REFERENCE_BASELINE_ROLE
        return role

    def fake_prepare(**kwargs):
        observed["prepare"] = kwargs
        return prepared

    async def fake_execute(**kwargs):
        observed["execute"] = kwargs
        return artifact

    monkeypatch.setattr(host_runner, "load_vllm_screening_plan", lambda _: plan)
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
            REFERENCE_BASELINE_ROLE,
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
    assert observed["role"] == REFERENCE_BASELINE_ROLE
    assert observed["prepare"]["plan"] is plan
    assert observed["prepare"]["condition_id"] == REFERENCE_BASELINE_ROLE
    assert observed["prepare"]["model_runner"] == "v2"
    assert "capacity_evidence_root" not in observed["prepare"]
    assert "snapshot_root" not in observed["execute"]
    output = capsys.readouterr().out
    assert '"operation": "capacity"' in output
    assert f'"condition": "{REFERENCE_BASELINE_ROLE}"' in output
    assert '"observed_max_model_len": 1536' in output
    assert '"evidence_id": "amcap-1"' in output
    assert '"score"' not in output


def test_shared_host_runner_delegates_lm_studio_without_reinterpreting_legacy_args(
    monkeypatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_lm_studio_main(argv):
        observed["argv"] = argv
        return 7

    monkeypatch.setattr(host_runner, "_lm_studio_main", fake_lm_studio_main)

    result = host_runner.main(
        [
            "--backend",
            "lm_studio",
            "--condition",
            "/tmp/condition.json",
            "--repo-root",
            "/repo",
            "--model-artifact",
            "/model.gguf",
            "--workspace-root",
            "/work",
            "--artifact-root",
            "/evidence",
        ]
    )

    assert result == 7
    assert observed["argv"] == [
        "--condition",
        "/tmp/condition.json",
        "--repo-root",
        "/repo",
        "--model-artifact",
        "/model.gguf",
        "--workspace-root",
        "/work",
        "--artifact-root",
        "/evidence",
    ]
