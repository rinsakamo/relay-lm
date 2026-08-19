from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import httpx

from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
)
from relaylm.events import Event
from relaylm.identity import Identity
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


def test_same_openai_provider_instance_runs_distinct_conversation_and_extraction_schemas() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        schema_name = body["response_format"]["json_schema"]["name"]
        if schema_name == "relaylm_conversation_output":
            wire = {"utterance": "最近はコーヒーを飲んでるんだね。"}
        elif schema_name == "relaylm_structured_cognition_output":
            wire = {
                "state_candidates": [],
                "continuity_candidates": [],
            }
        else:
            raise AssertionError(schema_name)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(wire, ensure_ascii=False)}}
                ]
            },
        )

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
    assert seen[0]["response_format"]["json_schema"]["schema"]["required"] == [
        "utterance"
    ]
    assert seen[1]["response_format"]["json_schema"]["schema"]["required"] == [
        "state_candidates",
        "continuity_candidates",
    ]
    assert "utterance" not in seen[1]["response_format"]["json_schema"]["schema"][
        "properties"
    ]

    extraction_prompt = seen[1]["messages"][0]["content"]
    assert "interpretive context" in extraction_prompt
    assert "must never self-certify" in extraction_prompt
    extraction_payload = json.loads(seen[1]["messages"][1]["content"])
    assert extraction_payload["assistant_response"] == "最近はコーヒーを飲んでるんだね。"
    assert extraction_payload["cognitive_input"]["input"]["event_id"] == "evt-now"


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


def test_conversation_pass_streams_only_visible_utterance_before_extraction_exists() -> None:
    seen: list[dict[str, object]] = []
    chunks = [
        _sse_chunk(content='{"utterance":"こん'),
        _sse_chunk(content='にちは"}', finish_reason="stop"),
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
    assert seen[0]["response_format"]["json_schema"]["name"] == "relaylm_conversation_output"
    assert "".join(emitted) == "こんにちは"
    assert output == CognitionConversationOutput(response="こんにちは")
