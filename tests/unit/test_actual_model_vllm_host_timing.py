from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import relaylm.actual_model_fast_screening_artifacts as timing_artifacts_module
import relaylm.actual_model_host as host_facade
import relaylm.actual_model_vllm_host as host
from relaylm.actual_model_fast_screening import ScreeningCallTiming


EXECUTION_ID = "amx-" + "a" * 64
RUN_ID = "amr-" + "b" * 64
CURRENT_SCREENING_ID = "stage-r0-vllm-reference-v2"
REFERENCE_BASELINE_ROLE = "reference_baseline"


class _Provider:
    async def generate_conversation(self, cognitive_input, *, pass_request=None):
        return SimpleNamespace(response="visible")

    async def generate_extraction(self, extraction_input, *, pass_request=None):
        return SimpleNamespace()

    async def aclose(self):
        return None


class _FailingExtractionProvider:
    async def generate_conversation(self, cognitive_input, *, pass_request=None):
        return SimpleNamespace(response="visible")

    async def generate_extraction(self, extraction_input, *, pass_request=None):
        raise RuntimeError("pass2 failed")

    async def aclose(self):
        return None


def _timing_artifact(
    *,
    run_id: str = RUN_ID,
    scenario_id: str = "scenario-v1",
    extraction_outcome: str = "completed",
):
    return timing_artifacts_module.bind_fast_screening_timing_artifact(
        screening_id=CURRENT_SCREENING_ID,
        condition_id=REFERENCE_BASELINE_ROLE,
        replicate_id="r0",
        scenario_id=scenario_id,
        execution_id=EXECUTION_ID,
        run_id=run_id,
        execution_mode="two_pass",
        turn_count=1,
        scenario_elapsed_ms=20.0,
        calls=(
            ScreeningCallTiming(
                phase="pass1",
                duration_ms=8.0,
                first_visible_ms=None,
                outcome="completed",
            ),
            ScreeningCallTiming(
                phase="pass2",
                duration_ms=5.0,
                first_visible_ms=None,
                outcome=extraction_outcome,
            ),
        ),
    )


def _host_result(*, timing_id: str, timing_path: Path) -> host.VLLMHostRunArtifact:
    return host.VLLMHostRunArtifact(
        scenario_id="scenario-v1",
        execution_id="amvx-" + "d" * 64,
        run_id=RUN_ID,
        artifact_path="/evidence/execution.vllm.json",
        boundary_verdict_id="ambv-" + "c" * 64,
        boundary_outcome="pass",
        boundary_artifact_path="/evidence/boundary.json",
        timing_id=timing_id,
        timing_artifact_path=str(timing_path),
    )


def test_vllm_host_carries_two_pass_timing_as_separate_sidecar(
    tmp_path: Path,
    monkeypatch,
) -> None:
    timing_artifacts = []

    async def fake_run(**kwargs):
        provider = kwargs["provider"]
        await provider.generate_conversation(None)
        await provider.generate_extraction(None)
        await provider.generate_conversation(None)
        await provider.generate_extraction(None)
        return SimpleNamespace(
            execution_id="amvx-" + "d" * 64,
            run_id=RUN_ID,
            execution=SimpleNamespace(execution_id=EXECUTION_ID),
        )

    monkeypatch.setattr(host, "run_bound_vllm_actual_model_scenario_definition", fake_run)
    monkeypatch.setattr(
        host,
        "write_vllm_actual_model_execution_result",
        lambda **kwargs: tmp_path / "execution.vllm.json",
    )
    monkeypatch.setattr(
        host,
        "evaluate_actual_model_deterministic_boundary",
        lambda **kwargs: SimpleNamespace(verdict_id="ambv-" + "c" * 64, outcome="pass"),
    )
    monkeypatch.setattr(
        host,
        "write_actual_model_deterministic_boundary_verdict",
        lambda **kwargs: tmp_path / "boundary.json",
    )
    monkeypatch.setattr(
        timing_artifacts_module,
        "write_fast_screening_timing_artifact",
        lambda *, artifact, artifact_root: timing_artifacts.append(artifact)
        or tmp_path / "screening_timing" / f"{artifact.run_id}.json",
    )

    prepared = SimpleNamespace(
        scenario_ids=("scenario-v1",),
        plan=SimpleNamespace(
            screening_id=CURRENT_SCREENING_ID,
            effective_context_window=1616,
        ),
        screening_condition_id=REFERENCE_BASELINE_ROLE,
        condition=SimpleNamespace(
            cognition_execution=SimpleNamespace(mode="two_pass"),
        ),
        manifest=SimpleNamespace(replicate_id="r0"),
        scenario_set=SimpleNamespace(
            scenario=lambda _: SimpleNamespace(
                scenario=SimpleNamespace(turns=("one", "two")),
            ),
        ),
        fixture_root=tmp_path / "fixture",
        target=SimpleNamespace(),
        snapshot_verification=SimpleNamespace(),
        reasoning_capability=SimpleNamespace(),
        provider=_Provider(),
        cognitive_budget=None,
        binding=SimpleNamespace(),
    )

    results = asyncio.run(
        host.execute_vllm_host_run(
            prepared=prepared,
            snapshot_root="/snapshot",
            workspace_root=tmp_path / "work",
            artifact_root=tmp_path / "evidence",
        )
    )

    assert len(results) == 1
    assert len(timing_artifacts) == 1
    timing = timing_artifacts[0]
    assert timing.screening_id == CURRENT_SCREENING_ID
    assert timing.condition_id == REFERENCE_BASELINE_ROLE
    assert timing.replicate_id == "r0"
    assert timing.scenario_id == "scenario-v1"
    assert timing.execution_mode == "two_pass"
    assert len(timing.turns) == 2
    assert all(turn.extraction_provider_ms is not None for turn in timing.turns)
    assert results[0].timing_artifact_path.endswith(f"{RUN_ID}.json")


def test_vllm_host_summary_surfaces_absorbed_pass2_provider_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    timing_artifacts = []

    async def fake_run(**kwargs):
        provider = kwargs["provider"]
        await provider.generate_conversation(None)
        try:
            await provider.generate_extraction(None)
        except RuntimeError:
            pass
        return SimpleNamespace(
            execution_id="amvx-" + "d" * 64,
            run_id=RUN_ID,
            execution=SimpleNamespace(execution_id=EXECUTION_ID),
        )

    def capture_timing(*, artifact, artifact_root):
        timing_artifacts.append(artifact)
        path = tmp_path / "screening_timing" / f"{artifact.run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(artifact.to_json(), encoding="utf-8")
        return path

    monkeypatch.setattr(host, "run_bound_vllm_actual_model_scenario_definition", fake_run)
    monkeypatch.setattr(
        host,
        "write_vllm_actual_model_execution_result",
        lambda **kwargs: tmp_path / "execution.vllm.json",
    )
    monkeypatch.setattr(
        host,
        "evaluate_actual_model_deterministic_boundary",
        lambda **kwargs: SimpleNamespace(verdict_id="ambv-" + "c" * 64, outcome="pass"),
    )
    monkeypatch.setattr(
        host,
        "write_actual_model_deterministic_boundary_verdict",
        lambda **kwargs: tmp_path / "boundary.json",
    )
    monkeypatch.setattr(
        timing_artifacts_module,
        "write_fast_screening_timing_artifact",
        capture_timing,
    )

    prepared = SimpleNamespace(
        scenario_ids=("scenario-v1",),
        plan=SimpleNamespace(
            screening_id=CURRENT_SCREENING_ID,
            effective_context_window=1616,
        ),
        screening_condition_id=REFERENCE_BASELINE_ROLE,
        condition=SimpleNamespace(
            cognition_execution=SimpleNamespace(mode="two_pass"),
        ),
        manifest=SimpleNamespace(replicate_id="r0"),
        scenario_set=SimpleNamespace(
            scenario=lambda _: SimpleNamespace(
                scenario=SimpleNamespace(turns=("one",)),
            ),
        ),
        fixture_root=tmp_path / "fixture",
        target=SimpleNamespace(),
        snapshot_verification=SimpleNamespace(),
        reasoning_capability=SimpleNamespace(),
        provider=_FailingExtractionProvider(),
        cognitive_budget=None,
        binding=SimpleNamespace(),
    )

    results = asyncio.run(
        host.execute_vllm_host_run(
            prepared=prepared,
            snapshot_root="/snapshot",
            workspace_root=tmp_path / "work",
            artifact_root=tmp_path / "evidence",
        )
    )

    assert len(results) == 1
    assert len(timing_artifacts) == 1
    assert timing_artifacts[0].turns[0].extraction_outcome == "failed"
    assert results[0].boundary_outcome == "pass"
    summary = host_facade._screening_result_mapping(results[0])
    assert summary["failed_provider_call_count"] == 1


def test_vllm_host_summary_rejects_foreign_valid_timing_sidecar(
    tmp_path: Path,
) -> None:
    expected = _timing_artifact()
    foreign = _timing_artifact(
        run_id="amr-" + "c" * 64,
        scenario_id="other-scenario-v1",
        extraction_outcome="failed",
    )
    timing_path = tmp_path / "foreign-timing.json"
    timing_path.write_text(foreign.to_json(), encoding="utf-8")
    result = _host_result(timing_id=expected.timing_id, timing_path=timing_path)

    with pytest.raises(host_facade.ActualModelHostFacadeError, match="timing"):
        host_facade._screening_result_mapping(result)


def test_vllm_host_summary_rejects_timing_content_with_stale_timing_id(
    tmp_path: Path,
) -> None:
    timing = _timing_artifact()
    raw = timing.to_mapping()
    raw["turns"][0]["extraction_outcome"] = "failed"  # type: ignore[index]
    timing_path = tmp_path / "tampered-timing.json"
    timing_path.write_text(
        json.dumps(raw, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = _host_result(timing_id=timing.timing_id, timing_path=timing_path)

    with pytest.raises(host_facade.ActualModelHostFacadeError, match="timing"):
        host_facade._screening_result_mapping(result)
