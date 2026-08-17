from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any

import httpx
import pytest

from relaylm.budget_enforcement import (
    SerializedCognitiveInputTokenCounter,
    SerializedInputTokenCount,
    TokenCountMode,
)
from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleSerializedInputCounter,
)
from relaylm.state import STATE_CLASS_DEFINITIONS, StateRecord


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(
            StateRecord(
                state_id="s1",
                state_class="user.preference",
                key="tea",
                value="likes",
                sources=("old",),
            ),
        ),
        context=(
            ContextItem(
                content="Earlier assistant utterance",
                sources=("evt-old",),
                actor="assistant",
            ),
        ),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "紅茶が好き"},
            event_id="evt-now",
            timestamp="2026-08-17T00:00:00+00:00",
        ),
    )


def test_counter_receives_same_model_input_shape_as_buffered_generation() -> None:
    counted: list[dict[str, Any]] = []
    sent: list[dict[str, Any]] = []

    def count_input(model_input: Mapping[str, Any]) -> SerializedInputTokenCount:
        counted.append(dict(model_input))
        return SerializedInputTokenCount(
            total_input_tokens=321,
            required_input_framing_tokens=123,
            mode=TokenCountMode.EXACT,
        )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        wire = {"utterance": "了解。", "state_candidates": []}
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(wire, ensure_ascii=False)}}]},
        )

    cognitive_input = _cognitive_input()
    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=count_input,
    )
    count = counter.count_serialized_input(cognitive_input)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            await provider.generate(cognitive_input)

    asyncio.run(run())

    assert count.total_input_tokens == 321
    assert len(counted) == 1
    assert len(sent) == 1
    sent_model_input = {key: value for key, value in sent[0].items() if key != "stream"}
    assert counted[0] == sent_model_input
    assert "stream" not in counted[0]


def test_counter_is_a_serialized_cognitive_input_token_counter() -> None:
    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=lambda _: SerializedInputTokenCount(
            total_input_tokens=10,
            required_input_framing_tokens=4,
            mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
        ),
    )

    assert isinstance(counter, SerializedCognitiveInputTokenCounter)
    assert counter.count_serialized_input(_cognitive_input()).mode is TokenCountMode.CONSERVATIVE_ESTIMATE


def test_counting_performs_no_provider_http_request() -> None:
    network_calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("token counting must not call the provider")

    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=lambda _: SerializedInputTokenCount(
            total_input_tokens=10,
            required_input_framing_tokens=4,
            mode=TokenCountMode.EXACT,
        ),
    )

    counter.count_serialized_input(_cognitive_input())

    assert network_calls == 0
    assert handler is not None


def test_counter_rejects_missing_model_and_untyped_result() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        OpenAICompatibleSerializedInputCounter(
            model=" ",
            count_input=lambda _: SerializedInputTokenCount(
                total_input_tokens=1,
                required_input_framing_tokens=0,
                mode=TokenCountMode.EXACT,
            ),
        )

    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=lambda _: 10,  # type: ignore[arg-type,return-value]
    )
    with pytest.raises(TypeError, match="SerializedInputTokenCount"):
        counter.count_serialized_input(_cognitive_input())
