from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import relaylm.actual_model_vllm as vllm
import relaylm.actual_model_vllm_host as vllm_host
from relaylm.actual_model_fast_screening import ScreeningTimingRecorder
from relaylm.cognitive import CognitiveOutput


SCENARIO_EXECUTION_ID = "amx-" + "a" * 64
RUN_ID = "amr-" + "b" * 64
BACKEND_EXECUTION_ID = "amvx-" + "c" * 64


class _Provider:
    def __init__(self) -> None:
        self.closed = False

    async def generate(self, _):
        return CognitiveOutput(response="ok")

    async def aclose(self) -> None:
        self.closed = True


def test_vllm_execution_times_only_after_original_provider_is_bound(monkeypatch) -> None:
    provider = _Provider()
    recorder = ScreeningTimingRecorder()
    observed: dict[str, object] = {}
    binding = SimpleNamespace(binding_id="amvb-" + "d" * 64)

    def fake_bind(**kwargs):
        observed["bound_provider"] = kwargs["provider"]
        return binding

    async def fake_run(**kwargs):
        observed["execution_provider"] = kwargs["provider"]
        await kwargs["provider"].generate(None)
        return SimpleNamespace(execution_id=SCENARIO_EXECUTION_ID, run_id=RUN_ID)

    monkeypatch.setattr(vllm, "bind_vllm_execution_condition", fake_bind)
    monkeypatch.setattr(vllm, "run_actual_model_scenario_definition", fake_run)

    result = asyncio.run(
        vllm.run_vllm_actual_model_scenario_definition(
            target=None,  # type: ignore[arg-type]
            snapshot_verification=None,  # type: ignore[arg-type]
            snapshot_root="/snapshot",
            reasoning_capability=None,  # type: ignore[arg-type]
            configured_context_window=1024,
            scenario_set=None,  # type: ignore[arg-type]
            scenario_id="scenario-v1",
            fixture_root="/fixture",
            workspace_root="/workspace",
            provider=provider,  # type: ignore[arg-type]
            manifest=None,  # type: ignore[arg-type]
            timing_recorder=recorder,
        )
    )

    assert observed["bound_provider"] is provider
    assert observed["execution_provider"] is not provider
    assert tuple(call.phase for call in recorder.calls) == ("single_pass",)
    assert result.execution is not None


def test_vllm_host_persists_timing_sidecar_with_existing_execution(monkeypatch, tmp_path: Path) -> None:
    provider = _Provider()
    observed: dict[str, object] = {}
    definition = SimpleNamespace(scenario=SimpleNamespace(turns=("hello",)))
    prepared = SimpleNamespace(
        scenario_ids=("scenario-v1",),
        target=object(),
        snapshot_verification=object(),
        reasoning_capability=object(),
        plan=SimpleNamespace(effective_context_window=1024, screening_id="screening-v1"),
        scenario_set=SimpleNamespace(scenario=lambda _: definition),
        fixture_root=tmp_path / "fixture",
        provider=provider,
        manifest=SimpleNamespace(replicate_id="r1"),
        screening_condition_id="A",
        condition=SimpleNamespace(cognition_execution=SimpleNamespace(mode="single_pass")),
    )

    async def fake_run(**kwargs):
        observed["timing_recorder"] = kwargs.get("timing_recorder")
        recorder = kwargs["timing_recorder"]
        started = recorder.clock_ns()
        completed = recorder.clock_ns()
        recorder.append(
            phase="single_pass",
            started_ns=started,
            completed_ns=completed,
            first_visible_ns=None,
            outcome="completed",
        )
        return SimpleNamespace(
            execution_id=BACKEND_EXECUTION_ID,
            run_id=RUN_ID,
            execution=SimpleNamespace(execution_id=SCENARIO_EXECUTION_ID),
        )

    verdict = SimpleNamespace(
        verdict_id="ambv-" + "e" * 64,
        outcome="pass",
    )
    monkeypatch.setattr(vllm_host, "run_vllm_actual_model_scenario_definition", fake_run)
    monkeypatch.setattr(
        vllm_host,
        "write_vllm_actual_model_execution_result",
        lambda **_: tmp_path / "execution.vllm.json",
    )
    monkeypatch.setattr(
        vllm_host,
        "evaluate_actual_model_deterministic_boundary",
        lambda **_: verdict,
    )
    monkeypatch.setattr(
        vllm_host,
        "write_actual_model_deterministic_boundary_verdict",
        lambda **_: tmp_path / "boundary.json",
    )

    artifacts = asyncio.run(
        vllm_host.execute_vllm_host_run(
            prepared=prepared,  # type: ignore[arg-type]
            snapshot_root="/snapshot",
            workspace_root=tmp_path / "workspace",
            artifact_root=tmp_path / "evidence",
        )
    )

    assert isinstance(observed["timing_recorder"], ScreeningTimingRecorder)
    assert provider.closed is True
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.timing_id.startswith("amt-")
    timing_path = Path(artifact.timing_artifact_path)
    assert timing_path.is_file()
    payload = json.loads(timing_path.read_text(encoding="utf-8"))
    assert payload["execution_id"] == SCENARIO_EXECUTION_ID
    assert payload["run_id"] == RUN_ID
    assert payload["execution_mode"] == "single_pass"
    assert payload["turns"][0]["response_provider_ms"] >= 0
    assert payload["turns"][0]["extraction_provider_ms"] is None
