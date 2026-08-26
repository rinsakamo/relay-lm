from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import httpx
import pytest

from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
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
            payload={"content": "最近コーヒーを飲んでる"},
            event_id="evt-now",
            timestamp="2026-08-20T00:00:00+00:00",
        ),
    )


def _empty_extraction_wire() -> dict[str, object]:
    return {
        "state_candidates": [],
        "continuity_candidates": [],
    }


def test_same_openai_provider_instance_uses_plain_conversation_and_relaylm_owned_extraction() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        user_prompt = body["messages"][1]["content"]
        if "<PASS>\nCONVERSATION" in user_prompt:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "最近はコーヒーを飲んでるんだね。"}}
                    ]
                },
            )
        if "<PASS>\nEXTRACTION" in user_prompt:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    _empty_extraction_wire(),
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
            )
        raise AssertionError(user_prompt)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
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

    assert conversation == CognitionConversationOutput(
        response="最近はコーヒーを飲んでるんだね。"
    )
    assert extraction.state_candidates == ()
    assert extraction.continuity_candidates == ()
    assert len(seen) == 2
    assert [body["model"] for body in seen] == ["gemma", "gemma"]

    assert "response_format" not in seen[0]
    assert seen[0]["messages"][0] == seen[1]["messages"][0]
    conversation_prompt = seen[0]["messages"][1]["content"]
    extraction_prompt = seen[1]["messages"][1]["content"]
    marker = "<PASS>\n"
    assert conversation_prompt.split(marker, 1)[0] == extraction_prompt.split(marker, 1)[0]
    assert conversation_prompt.endswith("CONVERSATION\n\nRespond as this character.")

    assert "response_format" not in seen[1]
    assert "turn_interpretation" not in extraction_prompt
    assert "interpretive context only" in extraction_prompt
    assert "must never self-certify" in extraction_prompt
    assert "state_candidates" in extraction_prompt
    assert "continuity_candidates" in extraction_prompt
    assert '"content":"最近はコーヒーを飲んでるんだね。"' in extraction_prompt
    assert '"event_id":"evt-now"' in extraction_prompt


def test_buffered_conversation_rejects_multiple_upstream_choices() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        choice = {"message": {"content": "こんにちは"}}
        return httpx.Response(200, json={"choices": [choice, choice]})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="exactly one"):
                await provider.generate_conversation(_cognitive_input())

    asyncio.run(run())


def test_buffered_extraction_rejects_multiple_upstream_choices() -> None:
    wire = json.dumps(_empty_extraction_wire(), ensure_ascii=False)

    def handler(_: httpx.Request) -> httpx.Response:
        choice = {"message": {"content": wire}}
        return httpx.Response(200, json={"choices": [choice, choice]})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError, match="exactly one"):
                await provider.generate_extraction(
                    CognitionExtractionInput(
                        cognitive_input=_cognitive_input(),
                        assistant_response="了解。",
                    )
                )

    asyncio.run(run())


def test_extraction_without_provider_structured_output_still_fails_closed_on_invalid_ir() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "response_format" not in body
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not-json"}}]},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=_cognitive_input(),
                    assistant_response="了解。",
                )
            )

    with pytest.raises(ProviderProtocolError, match="extraction content is not valid JSON"):
        asyncio.run(run())


def test_extraction_rejects_duplicate_state_candidate_members() -> None:
    content = (
        '{"state_candidates":[{"state_class":"user.preference",'
        '"key":"tea","key":"coffee","op":"set","value":"likes",'
        '"sources":["evt-now"]}],"continuity_candidates":[]}'
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=_cognitive_input(),
                    assistant_response="了解。",
                )
            )

    with pytest.raises(ProviderProtocolError, match="duplicate object member"):
        asyncio.run(run())


def test_extraction_rejects_extra_state_candidate_fields_inside_relaylm() -> None:
    wire = _empty_extraction_wire()
    wire["state_candidates"] = [
        {
            "state_class": "user.preference",
            "key": "coffee",
            "op": "set",
            "value": "likes",
            "sources": ["evt-now"],
            "provider_extra": "must-not-be-accepted",
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "response_format" not in body
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(wire, ensure_ascii=False)}}
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
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=_cognitive_input(),
                    assistant_response="了解。",
                )
            )

    with pytest.raises(
        ProviderProtocolError,
        match=r"state_candidates\[0\] must contain exactly",
    ):
        asyncio.run(run())


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


def test_conversation_pass_streams_plain_visible_text_before_extraction_exists() -> None:
    seen: list[dict[str, object]] = []
    chunks = [
        _sse_chunk(content="こん"),
        _sse_chunk(content="にちは", finish_reason="stop"),
        b"data: [DONE]\n\n",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
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
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            output = await provider.stream_generate_conversation(_cognitive_input(), emit)
        return emitted, output

    emitted, output = asyncio.run(run())

    assert seen[0]["stream"] is True
    assert "response_format" not in seen[0]
    assert "".join(emitted) == "こんにちは"
    assert output.response == "こんにちは"
    assert output.completion.finish_reason == "stop"
    assert output.completion.prompt_tokens is None
    assert output.completion.completion_tokens is None
    assert output.completion.total_tokens is None
    assert output.completion.reasoning_tokens is None
