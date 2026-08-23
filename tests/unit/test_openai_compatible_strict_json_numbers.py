from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import httpx
import pytest

from relaylm.cognitive import CognitiveInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderProtocolError,
)
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.state import STATE_CLASS_DEFINITIONS


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "こんにちは"},
            event_id="evt-now",
            timestamp="2026-08-23T00:00:00+00:00",
        ),
    )


def _combined_wire() -> str:
    return json.dumps(
        {
            "utterance": "こんにちは。",
            "state_candidates": [],
            "continuity_candidates": [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _envelope(*, content: str, index_token: str) -> bytes:
    encoded_content = json.dumps(content, ensure_ascii=False)
    return (
        '{"choices":[{"index":'
        + index_token
        + ',"message":{"content":'
        + encoded_content
        + '},"finish_reason":"stop"}]}'
    ).encode()


class _StaticSSEStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_buffered_combined_rejects_non_standard_numeric_constants(
    constant: str,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_envelope(content=_combined_wire(), index_token=constant),
            headers={"content-type": "application/json"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="valid JSON"):
                await provider.generate(_cognitive_input())

    asyncio.run(run())


def test_buffered_two_pass_rejects_non_standard_numeric_constant() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_envelope(content="了解。", index_token="NaN"),
            headers={"content-type": "application/json"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="valid JSON"):
                await provider.generate_conversation(_cognitive_input())

    asyncio.run(run())


def test_streaming_combined_rejects_non_standard_numeric_constant() -> None:
    envelope = _envelope(content=_combined_wire(), index_token="Infinity")
    chunks = [b"data: " + envelope + b"\n\n", b"data: [DONE]\n\n"]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_StaticSSEStream(chunks),
        )

    async def run() -> None:
        async def emit(_: str) -> None:
            return None

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="valid JSON"):
                await provider.stream_generate(_cognitive_input(), emit)

    asyncio.run(run())


def test_buffered_combined_preserves_finite_ignored_numeric_field() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_envelope(content=_combined_wire(), index_token="1.5"),
            headers={"content-type": "application/json"},
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            return await provider.generate(_cognitive_input())

    output = asyncio.run(run())
    assert output.response == "こんにちは。"
    assert output.state_candidates == ()
    assert output.continuity_candidates == ()
