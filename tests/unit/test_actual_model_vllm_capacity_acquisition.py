from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.actual_model_vllm_capacity_acquisition import (
    VLLMCapacityMeasurementProvider,
)
from relaylm.actual_model_vllm_host import load_vllm_screening_plan
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.cognitive import (
    CognitiveInput,
    ContextItem,
    EventEvidenceItem,
    RetrievedMemoryItem,
)
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionCompletionMetadata,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import STATE_CLASS_DEFINITIONS


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "screenings"
    / "cogp5-vllm-screening-v1.json"
)


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "hello"},
            event_id="evt-now",
            timestamp="2026-08-21T00:00:00+00:00",
        ),
    )


def _observed_cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(
            ContextItem(content="accepted continuity"),
            ContextItem(content="working user", sources=("evt-1",), actor="user"),
            ContextItem(
                content="working assistant",
                sources=("evt-2",),
                actor="assistant",
            ),
        ),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "hello"},
            event_id="evt-now",
            timestamp="2026-08-21T00:00:00+00:00",
        ),
        memory=(
            RetrievedMemoryItem(content="retrieved memory", location="memory.md"),
        ),
        event_evidence=(
            EventEvidenceItem(
                event_id="evt-evidence",
                event_type="message",
                actor="user",
                timestamp="2026-08-20T00:00:00+00:00",
                content="event evidence",
            ),
        ),
    )


class _SingleCounter:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    def count_serialized_input(self, cognitive_input, *, pass_request=None):
        assert cognitive_input is not None
        assert pass_request is not None
        self.order.append("count")
        return SerializedInputTokenCount(
            total_input_tokens=1500,
            required_input_framing_tokens=100,
            mode=TokenCountMode.EXACT,
        )


class _FailingSingleDelegate:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    async def generate(self, cognitive_input, *, pass_request=None):
        assert cognitive_input is not None
        assert pass_request is not None
        self.order.append("delegate")
        raise RuntimeError("provider failed after count")


class _TwoPassCounter:
    def __init__(self) -> None:
        self.extraction_responses: list[str] = []

    def count_conversation_input(self, cognitive_input, *, pass_request=None):
        assert cognitive_input is not None
        assert pass_request is not None
        return SerializedInputTokenCount(
            total_input_tokens=700,
            required_input_framing_tokens=80,
            mode=TokenCountMode.EXACT,
        )

    def count_extraction_input(self, extraction_input, *, pass_request=None):
        assert pass_request is not None
        self.extraction_responses.append(extraction_input.assistant_response)
        return SerializedInputTokenCount(
            total_input_tokens=900,
            required_input_framing_tokens=90,
            mode=TokenCountMode.EXACT,
        )


class _TwoPassDelegate:
    def __init__(self) -> None:
        self.responses = iter(("actual-pass1-turn1", "actual-pass1-turn2"))

    async def generate_conversation(self, cognitive_input, *, pass_request=None):
        assert cognitive_input is not None
        assert pass_request is not None
        return CognitionConversationOutput(response=next(self.responses))

    async def generate_extraction(self, extraction_input, *, pass_request=None):
        assert extraction_input is not None
        assert pass_request is not None
        return CognitionExtractionOutput()


class _ObservedTwoPassDelegate:
    async def generate_conversation(self, cognitive_input, *, pass_request=None):
        return CognitionConversationOutput(
            response="actual-pass1",
            completion=CognitionCompletionMetadata(
                finish_reason="stop",
                prompt_tokens=101,
                completion_tokens=23,
                total_tokens=124,
                reasoning_tokens=0,
            ),
        )

    async def generate_extraction(self, extraction_input, *, pass_request=None):
        return CognitionExtractionOutput(
            completion=CognitionCompletionMetadata(
                finish_reason="stop",
                prompt_tokens=201,
                completion_tokens=31,
                total_tokens=232,
                reasoning_tokens=0,
            )
        )


class _MissingUsageTwoPassDelegate:
    async def generate_conversation(self, cognitive_input, *, pass_request=None):
        return CognitionConversationOutput(
            response="actual-pass1",
            completion=CognitionCompletionMetadata(finish_reason="stop"),
        )

    async def generate_extraction(self, extraction_input, *, pass_request=None):
        return CognitionExtractionOutput(
            completion=CognitionCompletionMetadata(finish_reason="stop")
        )


def test_measurement_records_single_pass_before_delegate_failure() -> None:
    plan = load_vllm_screening_plan(PLAN_PATH)
    condition = plan.conditions["A"]
    request = condition.pass_requests.single_request
    assert request is not None
    order: list[str] = []
    provider = VLLMCapacityMeasurementProvider(
        delegate=_FailingSingleDelegate(order),
        condition=condition,
        scenario_id="response-persona-correction-v1",
        single_pass_counter=_SingleCounter(order),
    )

    async def run() -> None:
        with pytest.raises(RuntimeError, match="after count"):
            await provider.generate(_cognitive_input(), pass_request=request)

    asyncio.run(run())

    assert order == ["count", "delegate"]
    assert len(provider.observations) == 1
    observed = provider.observations[0]
    assert observed.condition_id == condition.condition_id
    assert observed.topology == "single_pass"
    assert observed.pass_id == "single_pass"
    assert observed.scenario_id == "response-persona-correction-v1"
    assert observed.turn_index == 1
    assert observed.total_input_tokens == 1500
    assert observed.required_input_framing_tokens == 100
    assert observed.count_mode is TokenCountMode.EXACT
    assert observed.selected_layer_occupancy.to_mapping() == {
        "canonical_state": {"item_count": 0},
        "working_context": {"item_count": 0, "character_occupancy": 0},
        "retrieved_memory": {"item_count": 0, "character_occupancy": 0},
        "event_evidence": {"item_count": 0, "character_occupancy": 0},
    }
    assert observed.completion_observation is None


def test_measurement_two_pass_uses_actual_pass1_response_and_turn_order() -> None:
    plan = load_vllm_screening_plan(PLAN_PATH)
    condition = plan.conditions["C"]
    pass1 = condition.pass_requests.pass1
    pass2 = condition.pass_requests.pass2
    assert pass1 is not None
    assert pass2 is not None
    counter = _TwoPassCounter()
    provider = VLLMCapacityMeasurementProvider(
        delegate=_TwoPassDelegate(),
        condition=condition,
        scenario_id="continuity-lifecycle-v1",
        two_pass_counter=counter,
    )
    cognitive_input = _cognitive_input()

    async def run() -> None:
        first = await provider.generate_conversation(
            cognitive_input,
            pass_request=pass1,
        )
        await provider.generate_extraction(
            CognitionExtractionInput(
                cognitive_input=cognitive_input,
                assistant_response=first.response,
            ),
            pass_request=pass2,
        )
        second = await provider.generate_conversation(
            cognitive_input,
            pass_request=pass1,
        )
        await provider.generate_extraction(
            CognitionExtractionInput(
                cognitive_input=cognitive_input,
                assistant_response=second.response,
            ),
            pass_request=pass2,
        )

    asyncio.run(run())

    assert counter.extraction_responses == [
        "actual-pass1-turn1",
        "actual-pass1-turn2",
    ]
    assert [item.pass_id for item in provider.observations] == [
        "pass1",
        "pass2",
        "pass1",
        "pass2",
    ]
    assert [item.turn_index for item in provider.observations] == [1, 1, 2, 2]
    assert [item.total_input_tokens for item in provider.observations] == [
        700,
        900,
        700,
        900,
    ]


def test_measurement_persists_provider_completion_and_selected_layer_occupancy() -> None:
    plan = load_vllm_screening_plan(PLAN_PATH)
    condition = plan.conditions["C"]
    pass1 = condition.pass_requests.pass1
    pass2 = condition.pass_requests.pass2
    assert pass1 is not None
    assert pass2 is not None
    provider = VLLMCapacityMeasurementProvider(
        delegate=_ObservedTwoPassDelegate(),
        condition=condition,
        scenario_id="continuity-lifecycle-v1",
        two_pass_counter=_TwoPassCounter(),
    )
    cognitive_input = _observed_cognitive_input()

    async def run() -> None:
        first = await provider.generate_conversation(
            cognitive_input,
            pass_request=pass1,
        )
        await provider.generate_extraction(
            CognitionExtractionInput(
                cognitive_input=cognitive_input,
                assistant_response=first.response,
            ),
            pass_request=pass2,
        )

    asyncio.run(run())

    pass1_observation, pass2_observation = provider.observations
    assert pass1_observation.completion_observation == CognitionCompletionMetadata(
        finish_reason="stop",
        prompt_tokens=101,
        completion_tokens=23,
        total_tokens=124,
        reasoning_tokens=0,
    )
    assert pass2_observation.completion_observation == CognitionCompletionMetadata(
        finish_reason="stop",
        prompt_tokens=201,
        completion_tokens=31,
        total_tokens=232,
        reasoning_tokens=0,
    )
    assert pass1_observation.selected_layer_occupancy.to_mapping() == {
        "canonical_state": {"item_count": 0},
        "working_context": {"item_count": 2, "character_occupancy": 29},
        "retrieved_memory": {"item_count": 1, "character_occupancy": 16},
        "event_evidence": {"item_count": 1, "character_occupancy": 14},
    }
    assert pass2_observation.selected_layer_occupancy == (
        pass1_observation.selected_layer_occupancy
    )


def test_measurement_does_not_invent_missing_provider_usage() -> None:
    plan = load_vllm_screening_plan(PLAN_PATH)
    condition = plan.conditions["C"]
    pass1 = condition.pass_requests.pass1
    pass2 = condition.pass_requests.pass2
    assert pass1 is not None
    assert pass2 is not None
    provider = VLLMCapacityMeasurementProvider(
        delegate=_MissingUsageTwoPassDelegate(),
        condition=condition,
        scenario_id="continuity-lifecycle-v1",
        two_pass_counter=_TwoPassCounter(),
    )
    cognitive_input = _cognitive_input()

    async def run() -> None:
        first = await provider.generate_conversation(
            cognitive_input,
            pass_request=pass1,
        )
        await provider.generate_extraction(
            CognitionExtractionInput(
                cognitive_input=cognitive_input,
                assistant_response=first.response,
            ),
            pass_request=pass2,
        )

    asyncio.run(run())

    assert [
        (
            item.completion_observation.finish_reason,
            item.completion_observation.prompt_tokens,
            item.completion_observation.completion_tokens,
            item.completion_observation.total_tokens,
            item.completion_observation.reasoning_tokens,
        )
        for item in provider.observations
    ] == [
        ("stop", None, None, None, None),
        ("stop", None, None, None, None),
    ]


def test_measurement_rejects_request_drift_before_count_or_delegate() -> None:
    plan = load_vllm_screening_plan(PLAN_PATH)
    condition = plan.conditions["A"]
    order: list[str] = []
    provider = VLLMCapacityMeasurementProvider(
        delegate=_FailingSingleDelegate(order),
        condition=condition,
        scenario_id="response-persona-correction-v1",
        single_pass_counter=_SingleCounter(order),
    )

    async def run() -> None:
        with pytest.raises(ValueError, match="pass request"):
            await provider.generate(_cognitive_input(), pass_request=None)

    asyncio.run(run())
    assert order == []
    assert provider.observations == ()
