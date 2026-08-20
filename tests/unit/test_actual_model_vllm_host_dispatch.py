from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import relaylm.actual_model_host_runner as host_runner


def test_shared_host_runner_dispatches_one_vllm_condition_without_backend_script(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    prepared = SimpleNamespace(
        plan=SimpleNamespace(screening_id="cogp5-vllm-screening-v1"),
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

    monkeypatch.setattr(
        host_runner,
        "_prepare_vllm_screening_condition",
        fake_prepare,
        raising=False,
    )
    monkeypatch.setattr(
        host_runner,
        "_execute_vllm_host_run",
        fake_execute,
        raising=False,
    )
    monkeypatch.setattr(
        host_runner,
        "_current_repo_head",
        lambda _: "a" * 40,
        raising=False,
    )

    result = host_runner.main(
        [
            "--backend",
            "vllm",
            "--condition",
            "A",
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
    assert observed["prepare"]["condition_id"] == "A"
    assert observed["prepare"]["base_url"] == "http://127.0.0.1:8000/v1"
    assert observed["execute"]["snapshot_root"] == "/tmp/relaylm-unsloth-w4a16-model"
    output = capsys.readouterr().out
    assert '"suite": "cogp5-vllm-screening-v1"' in output
    assert '"condition": "A"' in output
