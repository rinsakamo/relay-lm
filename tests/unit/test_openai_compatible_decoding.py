from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import httpx
import pytest

from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.cognitive import CognitiveInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_budget import OpenAICompatibleSerializedInputCounter
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
    ProviderCapabilityError,
)
from relaylm.state import STATE_CLASS_DEFINITIONS


class _StaticSSEStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "hi"},
            event_id="evt-now",
            timestamp="2026-08-18T00:00:00+00:00",
        ),
    )


def _wire_text() -> str:
    return json.dumps(
        {
            "utterance": "了解。",
            "state_candidates": [],
            "continuity_candidates": [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _sse_chunk(*, content: str | None = None, finish_reason: str | None = None) -> bytes:
    envelope = {
        "choices": [
            {
                "delta": {} if content is None else {"content": content},
                "finish_reason": finish_reason,
            }
        ]
    }
    return f"data: {json.dumps(envelope, ensure_ascii=False)}\n\n".encode("utf-8")


def _all_capabilities() -> OpenAICompatibleDecodingCapabilities:
    return OpenAICompatibleDecodingCapabilities(
        supported_controls=frozenset(
            {"temperature", "top_p", "seed", "max_output_tokens"}
        )
    )


def test_explicit_decoding_controls_are_carried_exactly_on_buffered_and_streaming_requests() -> None:
    seen: list[dict[str, object]] = []
    config = OpenAICompatibleDecodingConfig(
        temperature=0,
        top_p=0.875,
        seed=12345,
        max_output_tokens=256,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        if body["stream"] is False:
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": _wire_text()}}]},
            )
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_StaticSSEStream(
                [
                    _sse_chunk(content=_wire_text(), finish_reason="stop"),
                    b"data: [DONE]\n\n",
                ]
            ),
        )

    async def run() -> tuple[dict[str, int | float], list[str]]:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                api_key="secret-not-identity",
                decoding_config=config,
                decoding_capabilities=_all_capabilities(),
                http_client=client,
            )
            await provider.generate(_cognitive_input())
            await provider.stream_generate(_cognitive_input(), emit)
            return provider.effective_decoding_configuration, emitted

    effective, emitted = asyncio.run(run())

    assert len(seen) == 2
    assert [body["stream"] for body in seen] == [False, True]
    for body in seen:
        assert body["temperature"] == 0
        assert body["top_p"] == 0.875
        assert body["seed"] == 12345
        assert body["max_tokens"] == 256
    assert effective == {
        "temperature": 0,
        "top_p": 0.875,
        "seed": 12345,
        "max_tokens": 256,
    }
    assert "secret-not-identity" not in repr(effective)
    assert "".join(emitted) == "了解。"


def test_absent_decoding_controls_remain_absent_from_provider_request() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": _wire_text()}}]},
        )

    async def run() -> dict[str, int | float]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            await provider.generate(_cognitive_input())
            return provider.effective_decoding_configuration

    effective = asyncio.run(run())

    assert effective == {}
    assert len(seen) == 1
    assert all(
        control not in seen[0]
        for control in ("temperature", "top_p", "seed", "max_tokens")
    )


@pytest.mark.parametrize(
    ("config", "supported", "missing"),
    [
        (OpenAICompatibleDecodingConfig(temperature=0.2), frozenset(), "temperature"),
        (OpenAICompatibleDecodingConfig(top_p=0.9), frozenset({"temperature"}), "top_p"),
        (OpenAICompatibleDecodingConfig(seed=7), frozenset({"temperature", "top_p"}), "seed"),
        (
            OpenAICompatibleDecodingConfig(max_output_tokens=128),
            frozenset({"temperature", "top_p", "seed"}),
            "max_output_tokens",
        ),
    ],
)
def test_unsupported_requested_control_fails_before_network(
    config: OpenAICompatibleDecodingConfig,
    supported: frozenset[str],
    missing: str,
) -> None:
    network_calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("unsupported decoding control must fail before network")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ProviderCapabilityError, match=missing):
            OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                decoding_config=config,
                decoding_capabilities=OpenAICompatibleDecodingCapabilities(
                    supported_controls=supported  # type: ignore[arg-type]
                ),
                http_client=client,
            )
    finally:
        asyncio.run(client.aclose())

    assert network_calls == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"temperature": True},
        {"temperature": float("nan")},
        {"temperature": float("inf")},
        {"top_p": "0.9"},
        {"top_p": float("-inf")},
        {"seed": True},
        {"seed": 1.5},
        {"max_output_tokens": True},
        {"max_output_tokens": 1.5},
        {"max_output_tokens": 0},
        {"max_output_tokens": -1},
    ],
)
def test_decoding_config_rejects_untyped_or_non_finite_values(kwargs: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        OpenAICompatibleDecodingConfig(**kwargs)  # type: ignore[arg-type]


def test_serialized_counter_can_use_the_same_explicit_decoding_request_shape() -> None:
    config = OpenAICompatibleDecodingConfig(
        temperature=0.1,
        top_p=0.95,
        seed=99,
        max_output_tokens=320,
    )
    counted: list[dict[str, object]] = []
    sent: list[dict[str, object]] = []

    def count_input(model_input):
        counted.append(dict(model_input))
        return SerializedInputTokenCount(
            total_input_tokens=10,
            required_input_framing_tokens=4,
            mode=TokenCountMode.EXACT,
        )

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": _wire_text()}}]},
        )

    cognitive_input = _cognitive_input()
    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=count_input,
        decoding_config=config,
    )
    counter.count_serialized_input(cognitive_input)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                decoding_config=config,
                decoding_capabilities=_all_capabilities(),
                http_client=client,
            )
            await provider.generate(cognitive_input)

    asyncio.run(run())

    assert len(counted) == 1
    assert len(sent) == 1
    sent_model_input = {key: value for key, value in sent[0].items() if key != "stream"}
    assert counted[0] == sent_model_input
    assert counted[0]["temperature"] == 0.1
    assert counted[0]["top_p"] == 0.95
    assert counted[0]["seed"] == 99
    assert counted[0]["max_tokens"] == 320
