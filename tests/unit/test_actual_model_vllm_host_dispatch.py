from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import relaylm.actual_model_host as host_runner


_REPO_ROOT = Path(__file__).parents[2]


def test_shared_host_runner_dispatches_one_vllm_condition_without_backend_script(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    plan = SimpleNamespace(screening_id="cogp5-vllm-screening-v1")
    prepared = SimpleNamespace(
        plan=plan,
        screening_condition_id="A",
        manifest=SimpleNamespace(relaylm_commit="a" * 40, replicate_id="0"),
        target=SimpleNamespace(target_id="gemma-4-12b-it-qat-w4a16-vllm-v1"),
    )
    observed: dict[str, object] = {}

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
    monkeypatch.setattr(host_runner, "_prepare_vllm_screening_condition", fake_prepare)
    monkeypatch.setattr(host_runner, "_execute_vllm_host_run", fake_execute)
    monkeypatch.setattr(host_runner, "_current_repo_head", lambda _: "a" * 40)

    result = host_runner.main(
        [
            "--backend",
            "vllm",
            "--condition",
            "A",
            "--model-runner",
            "v2",
            "--repo-root",
            str(tmp_path),
            "--snapshot-root",
            "/tmp/relaylm-unsloth-w4a16-model",
            "--provider-base-url",
            "http://127.0.0.1:8000/v1",
            "--workspace-root",
            "/tmp/relaylm-vllm-work",
            "--artifact-root",
            "/tmp/relaylm-vllm-evidence",
        ]
    )

    assert result == 0
    assert observed["prepare"]["plan"] is plan
    assert observed["prepare"]["condition_id"] == "A"
    assert observed["prepare"]["model_runner"] == "v2"
    assert observed["prepare"]["base_url"] == "http://127.0.0.1:8000/v1"
    assert observed["execute"]["snapshot_root"] == "/tmp/relaylm-unsloth-w4a16-model"
    output = capsys.readouterr().out
    assert '"suite": "cogp5-vllm-screening-v1"' in output
    assert '"condition": "A"' in output
    assert '"operation": "screening"' in output


def test_current_stage_r_screening_rejects_non_reference_conditions(
    monkeypatch,
    capsys,
) -> None:
    prepared_conditions: list[str] = []

    def fake_prepare(**kwargs):
        prepared_conditions.append(kwargs["condition_id"])
        return SimpleNamespace(
            plan=kwargs["plan"],
            screening_condition_id=kwargs["condition_id"],
            manifest=SimpleNamespace(relaylm_commit="a" * 40, replicate_id="0"),
            target=SimpleNamespace(
                target_id="gemma-4-12b-it-qat-w4a16-google-vllm-v1"
            ),
        )

    async def fake_execute(**_kwargs):
        return ()

    monkeypatch.setattr(host_runner, "_prepare_vllm_screening_condition", fake_prepare)
    monkeypatch.setattr(host_runner, "_execute_vllm_host_run", fake_execute)
    monkeypatch.setattr(host_runner, "_current_repo_head", lambda _: "a" * 40)

    for condition in ("A", "C"):
        result = host_runner.main(
            [
                "--backend",
                "vllm",
                "--operation",
                "screening",
                "--condition",
                condition,
                "--model-runner",
                "v2",
                "--repo-root",
                str(_REPO_ROOT),
                "--snapshot-root",
                "/tmp/relaylm-google-w4a16-model",
                "--provider-base-url",
                "http://127.0.0.1:8000/v1",
                "--workspace-root",
                "/tmp/relaylm-vllm-work",
                "--artifact-root",
                "/tmp/relaylm-vllm-evidence",
            ]
        )
        assert result == 2
        assert condition in capsys.readouterr().err

    assert prepared_conditions == []


def test_shared_host_runner_dispatches_vllm_capacity_acquisition_separately(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    plan = SimpleNamespace(screening_id="cogp5-vllm-screening-v1")
    prepared = SimpleNamespace(
        plan=plan,
        screening_condition_id="A",
        manifest=SimpleNamespace(relaylm_commit="a" * 40, replicate_id="0"),
        target=SimpleNamespace(target_id="gemma-4-12b-it-qat-w4a16-vllm-v1"),
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

    def fake_prepare(**kwargs):
        observed["prepare"] = kwargs
        return prepared

    async def fake_execute(**kwargs):
        observed["execute"] = kwargs
        return artifact

    monkeypatch.setattr(host_runner, "load_vllm_screening_plan", lambda _: plan)
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
            "A",
            "--model-runner",
            "v2",
            "--repo-root",
            str(tmp_path),
            "--snapshot-root",
            "/tmp/relaylm-unsloth-w4a16-model",
            "--provider-base-url",
            "http://127.0.0.1:8000/v1",
            "--workspace-root",
            "/tmp/relaylm-vllm-work",
            "--artifact-root",
            "/tmp/relaylm-vllm-evidence",
        ]
    )

    assert result == 0
    assert observed["prepare"]["plan"] is plan
    assert observed["prepare"]["condition_id"] == "A"
    assert observed["prepare"]["model_runner"] == "v2"
    assert "capacity_evidence_root" not in observed["prepare"]
    assert "snapshot_root" not in observed["execute"]
    output = capsys.readouterr().out
    assert '"operation": "capacity"' in output
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
