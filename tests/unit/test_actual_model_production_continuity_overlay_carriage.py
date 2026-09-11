from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import relaylm.actual_model_stage_r_llama_cpp_production_continuity_overlay as host
import relaylm.actual_model_stage_r_llama_cpp_production_continuity_overlay_transaction as selector
import relaylm.actual_model_stage_r_llama_cpp_transaction as transaction
import tools.v1_llama_cpp_controller_preflight as controller_preflight
import tools.v1_stage_r_llama_cpp_production_continuity_overlay_wsl as overlay_wrapper
import tools.v1_stage_r_llama_cpp_wsl as base_wrapper


def test_zero_counts_for_unconsumed_semantics() -> None:
    counts = host._zero_counts()
    assert counts["semantic_generation_count"] == 0
    assert counts["t1_pass1_generation_count"] == 0
    assert counts["t1_pass2_generation_count"] == 0
    assert counts["t2_pass1_generation_count"] == 0
    assert counts["t2_overlay_pass2_generation_count"] == 0
    assert counts["formation_generation_count"] == 0
    assert counts["t3_generation_count"] == 0
    assert counts["semantic_retry_count"] == 0
    assert counts["replay_count"] == 0
    assert counts["reseed_count"] == 0
    assert counts["fallback_count"] == 0
    assert counts["fastcal_count"] == 0
    assert counts["lm_studio_contact_count"] == 0
    assert counts["repository_mutation_count"] == 0


def test_selector_forwards_retained_artifact_to_named_host(tmp_path: Path, monkeypatch) -> None:
    retained = tmp_path / "retained.json"
    retained.write_text("{}", encoding="utf-8")
    observed: dict[str, object] = {}
    def fake_run_transaction(argv, *, host_module, host_summary_filename, host_args) -> int:
        observed.update(argv=list(argv), host_module=host_module, host_summary_filename=host_summary_filename, host_args=tuple(host_args))
        return 17
    monkeypatch.setattr(selector, "run_transaction", fake_run_transaction)
    rc = selector.main(["--retained-formation-artifact", str(retained), "--origin", "http://127.0.0.1:1234"])
    assert rc == 17
    assert observed["host_module"] == selector.HOST_MODULE
    assert observed["host_summary_filename"] == selector.HOST_SUMMARY_FILENAME
    assert observed["host_args"] == ("--retained-formation-artifact", str(retained.resolve()))
    assert observed["argv"] == ["--origin", "http://127.0.0.1:1234"]


def test_overlay_wrapper_forwards_only_explicit_retained_artifact(tmp_path: Path, monkeypatch) -> None:
    retained = tmp_path / "retained.json"
    observed: dict[str, object] = {}
    def fake_run_wsl_transaction(argv, *, inner_transaction, inner_args) -> int:
        observed.update(argv=list(argv), inner_transaction=inner_transaction, inner_args=tuple(inner_args))
        return 23
    monkeypatch.setattr(overlay_wrapper, "run_wsl_transaction", fake_run_wsl_transaction)
    rc = overlay_wrapper.main(["--retained-formation-artifact", str(retained)])
    assert rc == 23
    assert observed["argv"] == []
    assert observed["inner_transaction"] == overlay_wrapper.INNER_TRANSACTION
    assert observed["inner_args"] == ("--retained-formation-artifact", str(retained.resolve()))


def test_controller_preflight_can_emit_exact_overlay_wrapper_command() -> None:
    command = controller_preflight.one_shot_command("tools.v1_stage_r_llama_cpp_production_continuity_overlay_wsl", executable="/venv/bin/python", wrapper_args=("--retained-formation-artifact", "/tmp/retained.json"))
    assert command == ["/venv/bin/python", "-m", "tools.v1_stage_r_llama_cpp_production_continuity_overlay_wsl", "--retained-formation-artifact", "/tmp/retained.json"]


def test_generic_transaction_preserves_overlay_host_args(tmp_path: Path, monkeypatch) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    selected_summary = artifact_root / "selected-summary.json"
    selected_summary.write_text(json.dumps({"classification": "PASS"}), encoding="utf-8")
    observed: list[str] = []
    def fake_run(command, **kwargs):
        observed.extend(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
    monkeypatch.setattr(transaction.subprocess, "run", fake_run)
    result = transaction._invoke_host(repo_root=tmp_path, api_base="http://127.0.0.1:1234/v1", request_model="synthetic-model", artifact_path=tmp_path / "model.gguf", revision="r" * 40, version="synthetic", build=1, gpu_identity="synthetic-gpu", launch_command=["llama-server"], log_path=tmp_path / "server.log", workspace_root=tmp_path / "workspace", artifact_root=artifact_root, replicate_id="0", host_module="synthetic.host", host_summary_path=selected_summary, host_args=("--retained-formation-artifact", "/tmp/retained.json"))
    assert result["summary"]["classification"] == "PASS"
    assert observed[1:5] == ["-m", "synthetic.host", "--retained-formation-artifact", "/tmp/retained.json"]


def test_base_wrapper_ordinary_mode_remains_unchanged(tmp_path: Path, monkeypatch) -> None:
    operator_home = tmp_path / "operator-home"
    operator_home.mkdir()
    monkeypatch.setenv("HOME", str(operator_home))
    commands: list[list[str]] = []
    runtime_roots: list[Path] = []
    def fake_run(command, *, cwd, env, check):
        commands.append(list(command))
        runtime_roots.append(Path(env["HOME"]).parent)
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(base_wrapper.subprocess, "run", fake_run)
    try:
        assert base_wrapper.main([]) == 0
    finally:
        for root in runtime_roots:
            shutil.rmtree(root, ignore_errors=True)
    assert commands[0][1:3] == ["-m", base_wrapper.INNER_TRANSACTION]
    assert "--retained-formation-artifact" not in commands[0]


def test_overlay_provider_rejects_a_third_extraction_call_without_generation() -> None:
    provider = object.__new__(host.ProductionContinuityOverlayLlamaProvider)
    provider.extraction_call_count = 2
    with pytest.raises(Exception, match="exactly two extraction calls"):
        import asyncio
        from relaylm.cognitive import CognitiveInput
        from relaylm.cognition_execution import CognitionExtractionInput
        from relaylm.events import Event
        from relaylm.identity import Identity
        cognitive_input = CognitiveInput(identity=Identity("Synthetic."), state_classes={}, state=(), context=(), input=Event.create(type="message", actor="user", payload={"content": "x"}, event_id="evt", timestamp="2026-01-01T00:00:00+00:00"))
        asyncio.run(provider.generate_extraction(CognitionExtractionInput(cognitive_input=cognitive_input, assistant_response="y")))
