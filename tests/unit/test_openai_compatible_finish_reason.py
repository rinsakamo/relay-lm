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


class _StaticSSEStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


def _sse_chunk(*, content: str, finish_reason: object) -> bytes:
    envelope = {
        "choices": [
            {
                "delta": {"content": content},
                "finish_reason": finish_reason,
            }
        ]
    }
    return f"data: {json.dumps(envelope, ensure_ascii=False)}\n\n".encode()


@pytest.mark.parametrize(
    "finish_reason",
    ["length", "content_filter", "tool_calls", "function_call", "vendor_stop", 7],
)
def test_buffered_combined_cognition_rejects_explicit_non_stop_finish_reason(
    finish_reason: object,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": _combined_wire()},
                        "finish_reason": finish_reason,
                    }
                ]
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="finish_reason"):
                await provider.generate(_cognitive_input())

    asyncio.run(run())


@pytest.mark.parametrize("finish_reason", ["stop", None])
def test_buffered_combined_cognition_accepts_supported_finish_reason_compatibility(
    finish_reason: str | None,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": _combined_wire()},
                        "finish_reason": finish_reason,
                    }
                ]
            },
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


def test_streaming_combined_cognition_rejects_explicit_length_finish_reason() -> None:
    chunks = [
        _sse_chunk(content=_combined_wire(), finish_reason="length"),
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
            with pytest.raises(ProviderProtocolError, match="finish_reason"):
                await provider.stream_generate(_cognitive_input(), emit)

    asyncio.run(run())


def test_buffered_two_pass_conversation_rejects_explicit_length_finish_reason() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": "途中で切れた応答"},
                        "finish_reason": "length",
                    }
                ]
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="finish_reason"):
                await provider.generate_conversation(_cognitive_input())

    asyncio.run(run())


def test_buffered_two_pass_extraction_rejects_explicit_length_finish_reason() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": _extraction_wire()},
                        "finish_reason": "length",
                    }
                ]
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="finish_reason"):
                await provider.generate_extraction(
                    CognitionExtractionInput(
                        cognitive_input=_cognitive_input(),
                        assistant_response="了解。",
                    )
                )

    asyncio.run(run())


def test_streaming_two_pass_conversation_rejects_explicit_length_finish_reason() -> None:
    chunks = [
        _sse_chunk(content="途中で切れた応答", finish_reason="length"),
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
            with pytest.raises(ProviderProtocolError, match="finish_reason"):
                await provider.stream_generate_conversation(_cognitive_input(), emit)

    asyncio.run(run())
