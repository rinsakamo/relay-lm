from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import httpx
import pytest

from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.continuity import ContinuityCandidate
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderProtocolError,
)
from relaylm.state import STATE_CLASS_DEFINITIONS, StateCandidate


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(
            ContextItem(
                content="Earlier exchange",
                sources=("evt-old",),
                actor="user",
            ),
        ),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "紅茶の話を続けたい"},
            event_id="evt-now",
            timestamp="2026-08-18T00:00:00+00:00",
        ),
    )


def _wire() -> dict[str, object]:
    return {
        "utterance": "次もこの話を続けよう。",
        "state_candidates": [
            {
                "state_class": "user.preference",
                "key": "tea",
                "op": "set",
                "value": "likes",
                "sources": ["evt-now"],
            }
        ],
        "continuity_candidates": [
            {
                "kind": "active_task",
                "key": "task.tea",
                "op": "set",
                "value": {"topic": "tea", "next": "compare"},
                "sources": ["evt-now"],
                "epistemic_role": "assistant_inference",
            },
            {
                "kind": "unresolved",
                "key": "tea.pending_question",
                "op": "resolve",
                "value": None,
                "sources": ["evt-now"],
                "epistemic_role": "assistant_inference",
            },
        ],
    }


class _StaticSSEStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


class _GatedSSEStream(httpx.AsyncByteStream):
    def __init__(
        self,
        *,
        first_chunk: bytes,
        tail_chunks: list[bytes],
        release_tail: asyncio.Event,
    ) -> None:
        self.first_chunk = first_chunk
        self.tail_chunks = tail_chunks
        self.release_tail = release_tail
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.first_chunk
        await self.release_tail.wait()
        for chunk in self.tail_chunks:
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


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


def _split_after_utterance(wire: dict[str, object]) -> tuple[str, str]:
    serialized = json.dumps(wire, ensure_ascii=False, separators=(",", ":"))
    split_at = serialized.index(',"state_candidates"')
    return serialized[:split_at], serialized[split_at:]


def test_buffered_rejects_multiple_upstream_choices() -> None:
    content = json.dumps(_wire(), ensure_ascii=False, separators=(",", ":"))

    def handler(_: httpx.Request) -> httpx.Response:
        choice = {"message": {"content": content}}
        return httpx.Response(200, json={"choices": [choice, choice]})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="exactly one"):
                await provider.generate(_cognitive_input())

    asyncio.run(run())


def test_streaming_rejects_multiple_upstream_choices_before_visible_selection() -> None:
    content = json.dumps(_wire(), ensure_ascii=False, separators=(",", ":"))
    choice = {"delta": {"content": content}, "finish_reason": "stop"}
    envelope = {"choices": [choice, choice]}
    chunks = [
        f"data: {json.dumps(envelope, ensure_ascii=False)}\n\n".encode("utf-8"),
        b"data: [DONE]\n\n",
    ]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_StaticSSEStream(chunks),
        )

    async def run() -> list[str]:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="exactly one"):
                await provider.stream_generate(_cognitive_input(), emit)
        return emitted

    assert asyncio.run(run()) == []


def test_buffered_and_streaming_return_identical_semantic_output() -> None:
    wire = _wire()
    first, tail = _split_after_utterance(wire)
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        if body["stream"] is False:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    wire,
                                    ensure_ascii=False,
                                    separators=(",", ":"),
                                )
                            }
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_StaticSSEStream(
                [
                    _sse_chunk(content=first),
                    _sse_chunk(content=tail, finish_reason="stop"),
                    b"data: [DONE]\n\n",
                ]
            ),
        )

    async def run() -> tuple[object, object, list[str]]:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            buffered = await provider.generate(_cognitive_input())
            streamed = await provider.stream_generate(_cognitive_input(), emit)
        return buffered, streamed, emitted

    buffered, streamed, emitted = asyncio.run(run())

    assert buffered == streamed
    assert "".join(emitted) == wire["utterance"]
    assert [request["stream"] for request in seen] == [False, True]
    assert streamed.state_candidates == (
        StateCandidate.set(
            state_class="user.preference",
            key="tea",
            value="likes",
            sources=("evt-now",),
        ),
    )
    assert streamed.continuity_candidates == (
        ContinuityCandidate.set(
            kind="active_task",
            key="task.tea",
            value={"topic": "tea", "next": "compare"},
            sources=("evt-now",),
            epistemic_role="assistant_inference",
        ),
        ContinuityCandidate.resolve(
            kind="unresolved",
            key="tea.pending_question",
            sources=("evt-now",),
            epistemic_role="assistant_inference",
        ),
    )


def test_streaming_withholds_semantic_output_until_candidate_tail_finishes() -> None:
    wire = _wire()
    first, tail = _split_after_utterance(wire)
    release_tail = asyncio.Event()
    stream = _GatedSSEStream(
        first_chunk=_sse_chunk(content=first),
        tail_chunks=[
            _sse_chunk(content=tail, finish_reason="stop"),
            b"data: [DONE]\n\n",
        ],
        release_tail=release_tail,
    )
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=stream,
        )

    async def run():
        emitted: list[str] = []
        visible = asyncio.Event()

        async def emit(text: str) -> None:
            emitted.append(text)
            visible.set()

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            generation = asyncio.create_task(
                provider.stream_generate(_cognitive_input(), emit)
            )
            await asyncio.wait_for(visible.wait(), timeout=1)
            assert "".join(emitted) == wire["utterance"]
            assert generation.done() is False
            release_tail.set()
            output = await generation
        return output

    output = asyncio.run(run())

    assert requests == 1
    assert len(output.continuity_candidates) == 2
    assert stream.closed is True


def test_malformed_continuity_tail_fails_closed_after_visible_delta() -> None:
    wire = _wire()
    first, _ = _split_after_utterance(wire)
    malformed_tail = (
        ',"state_candidates":[],"continuity_candidates":'
        '[{"kind":"active_task","key":"task.tea"'
    )
    seen = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal seen
        seen += 1
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_StaticSSEStream(
                [
                    _sse_chunk(content=first),
                    _sse_chunk(content=malformed_tail, finish_reason="stop"),
                    b"data: [DONE]\n\n",
                ]
            ),
        )

    async def run() -> list[str]:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(
                ProviderProtocolError,
                match="streamed content is not complete JSON",
            ):
                await provider.stream_generate(_cognitive_input(), emit)
        return emitted

    emitted = asyncio.run(run())

    assert seen == 1
    assert "".join(emitted) == wire["utterance"]


def test_cancelled_stream_never_returns_semantic_output() -> None:
    wire = _wire()
    first, tail = _split_after_utterance(wire)
    release_tail = asyncio.Event()
    stream = _GatedSSEStream(
        first_chunk=_sse_chunk(content=first),
        tail_chunks=[
            _sse_chunk(content=tail, finish_reason="stop"),
            b"data: [DONE]\n\n",
        ],
        release_tail=release_tail,
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=stream,
        )

    async def run() -> list[str]:
        emitted: list[str] = []
        visible = asyncio.Event()

        async def emit(text: str) -> None:
            emitted.append(text)
            visible.set()

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            generation = asyncio.create_task(
                provider.stream_generate(_cognitive_input(), emit)
            )
            await asyncio.wait_for(visible.wait(), timeout=1)
            assert generation.done() is False
            generation.cancel()
            with pytest.raises(asyncio.CancelledError):
                await generation
        return emitted

    emitted = asyncio.run(run())

    assert "".join(emitted) == wire["utterance"]
    assert stream.closed is True
