from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import relaylm.actual_model_vllm_host as host


EXECUTION_ID = "amx-" + "a" * 64
RUN_ID = "amr-" + "b" * 64


class _Provider:
    async def generate_conversation(self, cognitive_input, *, pass_request=None):
        return SimpleNamespace(response="visible")

    async def aclose(self):
        return None


def test_vllm_host_persists_timing_when_pass2_never_reaches_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def fake_run(**kwargs):
        provider = kwargs["provider"]
        await provider.generate_conversation(None)
        await provider.generate_conversation(None)
        return SimpleNamespace(
            execution_id="amvx-" + "d" * 64,
            run_id=RUN_ID,
            execution=SimpleNamespace(execution_id=EXECUTION_ID),
        )

    monkeypatch.setattr(
        host,
        "run_bound_vllm_actual_model_scenario_definition",
        fake_run,
    )
    monkeypatch.setattr(
        host,
        "write_vllm_actual_model_execution_result",
        lambda **_: tmp_path / "execution.vllm.json",
    )
    monkeypatch.setattr(
        host,
        "evaluate_actual_model_deterministic_boundary",
        lambda **_: SimpleNamespace(verdict_id="ambv-" + "c" * 64, outcome="pass"),
    )
    monkeypatch.setattr(
        host,
        "write_actual_model_deterministic_boundary_verdict",
        lambda **_: tmp_path / "boundary.json",
    )

    prepared = SimpleNamespace(
        scenario_ids=("scenario-v1",),
        plan=SimpleNamespace(screening_id="stage-r0-vllm-reference-v2"),
        screening_condition_id="reference_baseline",
        condition=SimpleNamespace(
            cognition_execution=SimpleNamespace(mode="two_pass"),
        ),
        manifest=SimpleNamespace(replicate_id="near-floor"),
        scenario_set=SimpleNamespace(
            scenario=lambda _: SimpleNamespace(
                scenario=SimpleNamespace(turns=("one", "two")),
            ),
        ),
        fixture_root=tmp_path / "fixture",
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
    timing_path = Path(results[0].timing_artifact_path)
    raw = json.loads(timing_path.read_text(encoding="utf-8"))
    assert [turn["response_outcome"] for turn in raw["turns"]] == [
        "completed",
        "completed",
    ]
    assert [turn["extraction_provider_ms"] for turn in raw["turns"]] == [None, None]
    assert [turn["extraction_outcome"] for turn in raw["turns"]] == [None, None]
