from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import httpx
import pytest

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
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


def _extraction_wire() -> str:
    return json.dumps(
        {"state_candidates": [], "continuity_candidates": []},
        separators=(",", ":"),
    )


def _duplicate_finish_envelope(content: str) -> bytes:
    encoded = json.dumps(content, ensure_ascii=False)
    return (
        '{"choices":[{"message":{"content":'
        + encoded
        + '},"finish_reason":"length","finish_reason":"stop"}]}'
    ).encode()


def _duplicate_finish_sse(content: str) -> bytes:
    encoded = json.dumps(content, ensure_ascii=False)
    return (
        'data: {"choices":[{"delta":{"content":'
        + encoded
        + '},"finish_reason":"length","finish_reason":"stop"}]}\n\n'
    ).encode()


class _StaticSSEStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


def test_buffered_combined_rejects_duplicate_provider_envelope_member() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_duplicate_finish_envelope(_combined_wire()),
            headers={"content-type": "application/json"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="duplicate"):
                await provider.generate(_cognitive_input())

    asyncio.run(run())


def test_buffered_two_pass_conversation_rejects_duplicate_provider_envelope_member() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_duplicate_finish_envelope("こんにちは。"),
            headers={"content-type": "application/json"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="duplicate"):
                await provider.generate_conversation(_cognitive_input())

    asyncio.run(run())


def test_buffered_two_pass_extraction_rejects_duplicate_provider_envelope_member() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_duplicate_finish_envelope(_extraction_wire()),
            headers={"content-type": "application/json"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="duplicate"):
                await provider.generate_extraction(
                    CognitionExtractionInput(
                        cognitive_input=_cognitive_input(),
                        assistant_response="了解。",
                    )
                )

    asyncio.run(run())


def test_streaming_combined_rejects_duplicate_provider_envelope_member() -> None:
    chunks = [
        _duplicate_finish_sse(_combined_wire()),
        b"data: [DONE]\n\n",
    ]

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
            with pytest.raises(ProviderProtocolError, match="duplicate"):
                await provider.stream_generate(_cognitive_input(), emit)

    asyncio.run(run())


def test_streaming_two_pass_conversation_rejects_duplicate_provider_envelope_member() -> None:
    chunks = [
        _duplicate_finish_sse("こんにちは。"),
        b"data: [DONE]\n\n",
    ]

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
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="duplicate"):
                await provider.stream_generate_conversation(_cognitive_input(), emit)

    asyncio.run(run())
