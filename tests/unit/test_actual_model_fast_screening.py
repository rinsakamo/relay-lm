from __future__ import annotations

import asyncio
from pathlib import Path

from relaylm.actual_model_fast_screening import (
    ScreeningTimingRecorder,
    instrument_screening_provider,
    reasoning_escalation_condition_ids,
    topology_screening_condition_ids,
)
from relaylm.actual_model_vllm_host import load_vllm_screening_plan
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "evaluation/actual_model/screenings/cogp5-vllm-screening-v1.json"


def test_fast_screening_runs_topology_before_reasoning_escalation() -> None:
    plan = load_vllm_screening_plan(PLAN)

    assert topology_screening_condition_ids(plan) == ("A", "B")
    assert reasoning_escalation_condition_ids(
        plan,
        structured_semantic_quality_sufficient=True,
    ) == ()
    assert reasoning_escalation_condition_ids(
        plan,
        structured_semantic_quality_sufficient=False,
    ) == ("C",)


class _FakeClock:
    def __init__(self) -> None:
        self.value = 0

    def __call__(self) -> int:
        self.value += 1_000_000
        return self.value


class _Provider:
    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        return CognitiveOutput(response="single")

    async def generate_conversation(self, _: CognitiveInput) -> CognitionConversationOutput:
        return CognitionConversationOutput(response="pass1")

    async def generate_extraction(
        self,
        _: CognitionExtractionInput,
    ) -> CognitionExtractionOutput:
        return CognitionExtractionOutput()


class _StreamingProvider(_Provider):
    async def stream_generate(self, cognitive_input, emit_response_delta):
        await emit_response_delta("a")
        await emit_response_delta("b")
        return CognitiveOutput(response="ab")

    async def stream_generate_conversation(self, cognitive_input, emit_response_delta):
        await emit_response_delta("x")
        await emit_response_delta("y")
        return CognitionConversationOutput(response="xy")


def test_timing_recorder_separates_visible_response_and_pass2_work() -> None:
    recorder = ScreeningTimingRecorder(clock_ns=_FakeClock())
    provider = instrument_screening_provider(_StreamingProvider(), recorder=recorder)

    async def exercise() -> None:
        async def sink(_: str) -> None:
            return None

        # Input values are not inspected by the fake provider; the timing wrapper
        # must remain transport-only and not reinterpret RelayLM semantics.
        await provider.stream_generate(None, sink)  # type: ignore[arg-type]
        await provider.stream_generate_conversation(None, sink)  # type: ignore[arg-type]
        await provider.generate_extraction(None)  # type: ignore[arg-type]

    asyncio.run(exercise())

    calls = recorder.calls
    assert tuple(call.phase for call in calls) == ("single_pass", "pass1", "pass2")
    assert calls[0].first_visible_ms is not None
    assert calls[1].first_visible_ms is not None
    assert calls[2].first_visible_ms is None
    assert all(call.duration_ms > 0 for call in calls)


def test_buffered_response_has_completion_timing_without_fake_ttft() -> None:
    recorder = ScreeningTimingRecorder(clock_ns=_FakeClock())
    provider = instrument_screening_provider(_Provider(), recorder=recorder)

    asyncio.run(provider.generate(None))  # type: ignore[arg-type]

    call = recorder.calls[0]
    assert call.phase == "single_pass"
    assert call.duration_ms > 0
    assert call.first_visible_ms is None
