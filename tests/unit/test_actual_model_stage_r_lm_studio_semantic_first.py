from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace

import relaylm.actual_model_stage_r_lm_studio_semantic_first as semantic_first
from relaylm.providers.lm_studio_reasoning import realize_lm_studio_reasoning_request
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest


def test_capsule_contains_no_native_provider_preflight() -> None:
    source = inspect.getsource(semantic_first)

    assert "/api/v1/models" not in source
    assert "urllib.request" not in source
    assert "native_provider_preflight\": False" in source


def test_declared_off_capability_uses_existing_production_reasoning_wire() -> None:
    capability = semantic_first._declared_reasoning_capability(
        request_model="google/gemma-4-12b",
        loaded_instance_id="google/gemma-4-12b",
        reasoning_options="off,on",
        reasoning_default="on",
    )

    application = realize_lm_studio_reasoning_request(
        request=OpenAICompatibleReasoningRequest(mode="off"),
        capability=capability,
    )

    assert application.to_mapping() == {
        "status": "applied",
        "requested": {"mode": "off"},
        "wire_fields": {"reasoning_effort": "none"},
    }


def test_fail_fast_sequence_stops_before_second_scenario() -> None:
    seen: list[str] = []

    async def execute(scenario_id: str):
        seen.append(scenario_id)
        return {"scenario_id": scenario_id}, "request_failure"

    executions, stop_reason = asyncio.run(
        semantic_first._run_fail_fast_sequence(
            scenario_ids=("scenario-1", "scenario-2", "scenario-3"),
            execute=execute,
        )
    )

    assert seen == ["scenario-1"]
    assert executions == [{"scenario_id": "scenario-1"}]
    assert stop_reason == "request_failure"


def test_fail_fast_sequence_continues_after_success() -> None:
    seen: list[str] = []

    async def execute(scenario_id: str):
        seen.append(scenario_id)
        return {"scenario_id": scenario_id}, None

    executions, stop_reason = asyncio.run(
        semantic_first._run_fail_fast_sequence(
            scenario_ids=("scenario-1", "scenario-2"),
            execute=execute,
        )
    )

    assert seen == ["scenario-1", "scenario-2"]
    assert executions == [
        {"scenario_id": "scenario-1"},
        {"scenario_id": "scenario-2"},
    ]
    assert stop_reason is None


def test_material_execution_failure_detects_request_failure(monkeypatch) -> None:
    class FakeEvidence:
        def __init__(self) -> None:
            self.request_failure = object()
            self.turns = ()

    monkeypatch.setattr(semantic_first, "ActualModelEvidence", FakeEvidence)
    result = SimpleNamespace(evidence=FakeEvidence())

    assert semantic_first._material_execution_failure(result) == "request_failure"


def test_material_execution_failure_detects_explicit_pass2_failure(monkeypatch) -> None:
    class FakeEvidence:
        def __init__(self) -> None:
            self.request_failure = None
            self.turns = (
                SimpleNamespace(
                    turn_index=2,
                    cognition_execution=SimpleNamespace(pass2_status="failed"),
                ),
            )

    monkeypatch.setattr(semantic_first, "ActualModelEvidence", FakeEvidence)
    result = SimpleNamespace(evidence=FakeEvidence())

    assert (
        semantic_first._material_execution_failure(result)
        == "pass2_failed_turn_2"
    )
