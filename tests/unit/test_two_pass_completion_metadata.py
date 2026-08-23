from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import httpx

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.state import STATE_CLASS_DEFINITIONS


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "hello"},
            event_id="evt-now",
            timestamp="2026-08-23T00:00:00+00:00",
        ),
    )


def _completion_envelope(content: str) -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 101,
            "completion_tokens": 7,
            "total_tokens": 108,
            "completion_tokens_details": {"reasoning_tokens": 3},
        },
    }


def test_buffered_two_pass_outputs_retain_provider_completion_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        system_prompt = body["messages"][0]["content"]
        if "conversation pass" in system_prompt:
            return httpx.Response(200, json=_completion_envelope("hello there"))
        wire = json.dumps(
            {"state_candidates": [], "continuity_candidates": []},
            separators=(",", ":"),
        )
        return httpx.Response(200, json=_completion_envelope(wire))

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://provider.test/v1",
                model="gemma",
                http_client=client,
            )
            conversation = await provider.generate_conversation(_cognitive_input())
            extraction = await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=_cognitive_input(),
                    assistant_response=conversation.response,
                )
            )
            return conversation, extraction

    conversation, extraction = asyncio.run(run())

    for output in (conversation, extraction):
        assert output.completion.finish_reason == "stop"
        assert output.completion.prompt_tokens == 101
        assert output.completion.completion_tokens == 7
        assert output.completion.total_tokens == 108
        assert output.completion.reasoning_tokens == 3


def test_buffered_missing_usage_stays_missing() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": "hello there"},
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://provider.test/v1",
                model="gemma",
                http_client=client,
            )
            return await provider.generate_conversation(_cognitive_input())

    output = asyncio.run(run())
    assert output.completion.finish_reason == "stop"
    assert output.completion.prompt_tokens is None
    assert output.completion.completion_tokens is None
    assert output.completion.total_tokens is None
    assert output.completion.reasoning_tokens is None


class _ChunkedSSEStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


def _sse_chunk(*, content: str | None = None, finish_reason: str | None = None) -> bytes:
    envelope = {
        "choices": [
            {
                "delta": {} if content is None else {"content": content},
                "finish_reason": finish_reason,
            }
        ]
    }
    return f"data: {json.dumps(envelope)}\n\n".encode()


def test_streaming_conversation_retains_finish_reason_without_inventing_usage() -> None:
    chunks = [
        _sse_chunk(content="hello"),
        _sse_chunk(content=" there", finish_reason="stop"),
        b"data: [DONE]\n\n",
    ]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_ChunkedSSEStream(chunks),
        )

    async def run():
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://provider.test/v1",
                model="gemma",
                http_client=client,
            )
            output = await provider.stream_generate_conversation(
                _cognitive_input(),
                emit,
            )
        return emitted, output

    emitted, output = asyncio.run(run())
    assert "".join(emitted) == "hello there"
    assert output.completion.finish_reason == "stop"
    assert output.completion.prompt_tokens is None
    assert output.completion.completion_tokens is None
    assert output.completion.total_tokens is None
    assert output.completion.reasoning_tokens is None
