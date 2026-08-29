from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import httpx
import pytest

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionExecutionCapabilityError,
    CognitionExtractionInput,
    CognitionPassRequest,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
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
            payload={"content": "hello"},
            event_id="evt-now",
            timestamp="2026-08-29T00:00:00+00:00",
        ),
    )


def _output_limit_capability() -> OpenAICompatibleDecodingCapabilities:
    return OpenAICompatibleDecodingCapabilities(
        supported_controls=frozenset({"max_output_tokens"})
    )


def test_two_pass_buffered_requests_carry_distinct_hard_output_limits() -> None:
    async def run() -> list[dict[str, object]]:
        bodies: list[dict[str, object]] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            bodies.append(body)
            if len(bodies) == 1:
                return httpx.Response(
                    200,
                    json={
                        "choices": [
                            {"message": {"content": "visible"}, "finish_reason": "stop"}
                        ]
                    },
                )
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "state_candidates": [],
                                        "continuity_candidates": [],
                                    }
                                )
                            },
                            "finish_reason": "stop",
                        }
                    ]
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://provider.test/v1",
                model="gemma",
                decoding_capabilities=_output_limit_capability(),
                http_client=client,
            )
            cognitive_input = _cognitive_input()
            conversation = await provider.generate_conversation(
                cognitive_input,
                pass_request=CognitionPassRequest(max_output_tokens=384),
            )
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=cognitive_input,
                    assistant_response=conversation.response,
                ),
                pass_request=CognitionPassRequest(max_output_tokens=192),
            )
        return bodies

    bodies = asyncio.run(run())

    assert len(bodies) == 2
    assert bodies[0]["max_tokens"] == 384
    assert bodies[1]["max_tokens"] == 192


def test_two_pass_streaming_pass1_carries_hard_output_limit() -> None:
    async def run() -> tuple[list[dict[str, object]], list[str]]:
        bodies: list[dict[str, object]] = []
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        async def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            bodies.append(body)
            chunks = [
                b'data: {"choices":[{"delta":{"content":"visible"},"finish_reason":null}]}\n\n',
                b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n',
                b"data: [DONE]\n\n",
            ]
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                stream=_StaticSSEStream(chunks),
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://provider.test/v1",
                model="gemma",
                decoding_capabilities=_output_limit_capability(),
                http_client=client,
            )
            result = await provider.stream_generate_conversation(
                _cognitive_input(),
                emit,
                pass_request=CognitionPassRequest(max_output_tokens=256),
            )
            assert result.response == "visible"
        return bodies, emitted

    bodies, emitted = asyncio.run(run())

    assert len(bodies) == 1
    assert bodies[0]["stream"] is True
    assert bodies[0]["max_tokens"] == 256
    assert emitted == ["visible"]


def test_two_pass_explicit_output_limit_without_capability_fails_before_network() -> None:
    async def run() -> int:
        calls = 0

        async def handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            raise AssertionError("network must not be reached")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://provider.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(
                CognitionExecutionCapabilityError,
                match="max_output_tokens",
            ):
                await provider.generate_conversation(
                    _cognitive_input(),
                    pass_request=CognitionPassRequest(max_output_tokens=128),
                )
        return calls

    assert asyncio.run(run()) == 0
