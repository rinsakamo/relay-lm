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
            payload={"content": "こんにちは"},
            event_id="evt-now",
            timestamp="2026-08-23T00:00:00+00:00",
        ),
    )


def _unterminated_stop_event(content: str) -> bytes:
    envelope = {
        "choices": [
            {
                "delta": {"content": content},
                "finish_reason": "stop",
            }
        ]
    }
    # One line ending terminates the field line, but the SSE event itself has no
    # blank-line delimiter before EOF.
    return f"data: {json.dumps(envelope, ensure_ascii=False)}\n".encode()


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


def test_combined_stream_rejects_unterminated_final_sse_event() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_StaticSSEStream([_unterminated_stop_event(_combined_wire())]),
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
            with pytest.raises(ProviderProtocolError, match="unterminated SSE event"):
                await provider.stream_generate(_cognitive_input(), emit)

    asyncio.run(run())


def test_two_pass_conversation_rejects_unterminated_final_sse_event() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_StaticSSEStream([_unterminated_stop_event("こんにちは。")]),
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
            with pytest.raises(ProviderProtocolError, match="unterminated SSE event"):
                await provider.stream_generate_conversation(_cognitive_input(), emit)

    asyncio.run(run())
