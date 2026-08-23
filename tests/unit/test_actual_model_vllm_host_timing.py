from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import relaylm.actual_model_fast_screening_artifacts as timing_artifacts_module
import relaylm.actual_model_vllm_host as host


EXECUTION_ID = "amx-" + "a" * 64
RUN_ID = "amr-" + "b" * 64


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

    monkeypatch.setattr(host, "run_vllm_actual_model_scenario_definition", fake_run)
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
            screening_id="stage-r0-vllm-reference-v1",
            effective_context_window=1616,
        ),
        screening_condition_id="B",
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
    assert timing.screening_id == "stage-r0-vllm-reference-v1"
    assert timing.condition_id == "B"
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

    monkeypatch.setattr(host, "run_vllm_actual_model_scenario_definition", fake_run)
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
            screening_id="stage-r0-vllm-reference-v1",
            effective_context_window=1616,
        ),
        screening_condition_id="B",
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
    assert results[0].failed_provider_call_count == 1
    assert results[0].to_mapping()["failed_provider_call_count"] == 1
