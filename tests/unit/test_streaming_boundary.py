from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator

import httpx
from fastapi.testclient import TestClient

from relaylm.cognitive import CognitiveInput, CognitiveOutput, ContextItem
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderProtocolError,
)
from relaylm.server import create_app
from relaylm.state import STATE_CLASS_DEFINITIONS, StateCandidate, StateRecord
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.storage.filesystem import CharacterDirectory


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(
            StateRecord(
                state_id="s1",
                state_class="user.preference",
                key="coffee",
                value="likes",
                sources=("old",),
            ),
        ),
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
            payload={"content": "紅茶が好き"},
            event_id="evt-now",
            timestamp="2026-08-17T00:00:00+00:00",
        ),
    )


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(
        "# ReLM\n\nNever invent history.\n", encoding="utf-8"
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}', encoding="utf-8"
    )
    return CharacterDirectory(root)


def _profile(character: CharacterDirectory, provider: object) -> CognitiveProfileRuntime:
    return CognitiveProfileRuntime(
        name="relaylm",
        package=CognitivePackageDirectory(character.root),
        provider=provider,
        physical_model="streaming-test-model",
    )


def _profiles(character: CharacterDirectory, provider: object) -> CognitiveProfileRegistry:
    return CognitiveProfileRegistry((_profile(character, provider),))


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
    return f"data: {json.dumps(envelope, ensure_ascii=False)}\n\n".encode("utf-8")


def test_provider_streams_safe_utterance_before_final_candidate_parse() -> None:
    seen: list[dict[str, object]] = []
    wire_fragments = [
        '{"utterance":"こん',
        'にちは","state_candidates":[',
        (
            '{"state_class":"user.preference","key":"tea","op":"set",'
            '"value":"likes","sources":["evt-now"]}],'
            '"continuity_candidates":[]}'
        ),
    ]
    chunks = [
        _sse_chunk(content=wire_fragments[0]),
        _sse_chunk(content=wire_fragments[1]),
        _sse_chunk(content=wire_fragments[2], finish_reason="stop"),
        b"data: [DONE]\n\n",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_ChunkedSSEStream(chunks),
        )

    async def run() -> tuple[list[str], CognitiveOutput]:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            output = await provider.stream_generate(_cognitive_input(), emit)
        return emitted, output

    emitted, output = asyncio.run(run())

    assert len(seen) == 1
    assert seen[0]["stream"] is True
    assert "".join(emitted) == "こんにちは"
    assert output.response == "こんにちは"
    assert output.state_candidates == (
        StateCandidate.set(
            state_class="user.preference",
            key="tea",
            value="likes",
            sources=("evt-now",),
        ),
    )
    assert output.continuity_candidates == ()


class _SuccessfulStreamingProvider:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.inputs: list[CognitiveInput] = []
        self.state_during_stream = None
        self.events_during_stream: list[Event] = []

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("stream=true must not use buffered generate")

    async def stream_generate(self, cognitive_input: CognitiveInput, emit) -> CognitiveOutput:
        self.inputs.append(cognitive_input)
        await emit("紅茶")
        snapshot = CharacterDirectory(self.root)
        self.state_during_stream = snapshot.load_state()
        self.events_during_stream = list(snapshot.iter_events())
        await emit("が好きって覚えてるよ。")
        return CognitiveOutput(
            response="紅茶が好きって覚えてるよ。",
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="tea",
                    value="likes",
                    sources=(cognitive_input.input.id,),
                ),
            ),
        )


def test_streaming_api_exposes_text_before_committing_state(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    provider = _SuccessfulStreamingProvider(tmp_path)
    app = create_app(profiles=_profiles(character, provider))

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "relaylm",
                "stream": True,
                "messages": [{"role": "user", "content": "前に話した好み、覚えてる？"}],
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "紅茶" in response.text
    assert "が好きって覚えてるよ。" in response.text
    assert "data: [DONE]" in response.text

    assert provider.state_during_stream is not None
    assert provider.state_during_stream.states == ()
    assert [event.actor for event in provider.events_during_stream] == ["user"]

    persisted = CharacterDirectory(tmp_path)
    assert [event.actor for event in persisted.iter_events()] == ["user", "assistant"]
    assert [
        (record.state_class, record.key, record.value)
        for record in persisted.load_state().states
    ] == [("user.preference", "tea", "likes")]


class _TruncatedStreamingProvider:
    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("stream=true must not use buffered generate")

    async def stream_generate(self, _: CognitiveInput, emit) -> CognitiveOutput:
        await emit("途中まで")
        raise ProviderProtocolError("truncated structured stream")


def test_truncated_stream_keeps_user_event_but_never_commits_assistant_or_state(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    app = create_app(profiles=_profiles(character, _TruncatedStreamingProvider()))

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "relaylm",
                "stream": True,
                "messages": [{"role": "user", "content": "この話を覚えて"}],
            },
        )

    assert response.status_code == 200
    assert "途中まで" in response.text
    assert "data: [DONE]" not in response.text

    persisted = CharacterDirectory(tmp_path)
    events = list(persisted.iter_events())
    assert [event.actor for event in events] == ["user"]
    assert persisted.load_state().states == ()


class _ClientCancelledStreamingProvider:
    def __init__(self) -> None:
        self.cancelled = False

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("stream=true must not use buffered generate")

    async def stream_generate(self, _: CognitiveInput, emit) -> CognitiveOutput:
        try:
            await emit("見えている途中")
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        raise AssertionError("unreachable")


def test_downstream_stream_close_cancels_turn_before_assistant_or_state_commit(
    tmp_path: Path,
) -> None:
    from relaylm.api.openai import _stream_chat_completion

    async def run() -> _ClientCancelledStreamingProvider:
        character = _make_character(tmp_path)
        provider = _ClientCancelledStreamingProvider()
        stream = _stream_chat_completion(
            profile=_profile(character, provider),
            turn_lock=asyncio.Lock(),
            content="途中で切断する",
            completion_id="chatcmpl-test",
            created=0,
        )

        first_chunk = await anext(stream)
        assert "見えている途中" in first_chunk.decode("utf-8")
        await stream.aclose()
        assert provider.cancelled is True
        return provider

    asyncio.run(run())

    persisted = CharacterDirectory(tmp_path)
    assert [event.actor for event in persisted.iter_events()] == ["user"]
    assert persisted.load_state().states == ()
