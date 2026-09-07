from __future__ import annotations

import asyncio
import inspect
import json
from types import SimpleNamespace

import httpx

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


def test_completion_observer_persists_reasoning_off_metadata(tmp_path) -> None:
    envelope = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": "visible response",
                    "reasoning": None,
                    "reasoning_content": "",
                },
            }
        ],
        "usage": {
            "prompt_tokens": 101,
            "completion_tokens": 7,
            "total_tokens": 108,
            "completion_tokens_details": {"reasoning_tokens": 0},
        },
    }

    async def exercise():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=envelope, request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = semantic_first._CompletionObservingTwoPassProvider(
                base_url="http://provider.test/v1",
                model="gemma",
                http_client=client,
                completion_observation_root=tmp_path,
            )
            returned = await provider._post_two_pass(
                body={"model": "gemma", "messages": []},
                boundary="conversation",
            )
            return returned, tuple(provider.completion_observation_artifacts)

    returned, artifacts = asyncio.run(exercise())

    assert returned == envelope
    assert len(artifacts) == 1
    observed = json.loads(artifacts[0].read_text(encoding="utf-8"))
    assert observed == {
        "boundary": "conversation",
        "finish_reason": "stop",
        "format_version": 1,
        "provider_http_success": True,
        "reasoning": {"status": "empty"},
        "reasoning_content": {"status": "empty"},
        "sequence_index": 1,
        "usage": {
            "completion_tokens": 7,
            "prompt_tokens": 101,
            "reasoning_tokens": 0,
            "reasoning_tokens_supplied": True,
            "total_tokens": 108,
        },
    }


def test_completion_observer_distinguishes_nonempty_reasoning_without_storing_it(
    tmp_path,
) -> None:
    envelope = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": "visible response",
                    "reasoning": "private hidden reasoning",
                    "reasoning_content": "other private reasoning",
                },
            }
        ],
        "usage": {
            "completion_tokens_details": {"reasoning_tokens": 5},
        },
    }

    async def exercise():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=envelope, request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = semantic_first._CompletionObservingTwoPassProvider(
                base_url="http://provider.test/v1",
                model="gemma",
                http_client=client,
                completion_observation_root=tmp_path,
            )
            await provider._post_two_pass(
                body={"model": "gemma", "messages": []},
                boundary="extraction",
            )
            return provider.completion_observation_artifacts[0]

    artifact = asyncio.run(exercise())
    raw = artifact.read_text(encoding="utf-8")
    observed = json.loads(raw)

    assert observed["usage"]["reasoning_tokens"] == 5
    assert observed["usage"]["reasoning_tokens_supplied"] is True
    assert observed["reasoning"] == {"status": "nonempty"}
    assert observed["reasoning_content"] == {"status": "nonempty"}
    assert "private hidden reasoning" not in raw
    assert "other private reasoning" not in raw


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
