from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import OpenAICompatibleProvider, ProviderProtocolError
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
            payload={"content": "hello"},
            event_id="evt-now",
            timestamp="2026-08-23T00:00:00+00:00",
        ),
    )


async def _provider_with_response(
    provider_type,
    content: bytes,
):
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=content,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = provider_type(
        base_url="http://provider.test/v1",
        model="test-model",
        http_client=client,
    )
    return provider, client


def test_buffered_combined_rejects_invalid_utf8_before_semantic_parse() -> None:
    async def run() -> None:
        response = (
            b'{"choices":[{"message":{"content":"{\\"utterance\\":\\"hello '
            b'\xff\\",\\"state_candidates\\":[],\\"continuity_candidates\\":[]}"}}]}'
        )
        provider, client = await _provider_with_response(OpenAICompatibleProvider, response)
        try:
            with pytest.raises(ProviderProtocolError, match="UTF-8"):
                await provider.generate(_cognitive_input())
        finally:
            await client.aclose()

    asyncio.run(run())


def test_buffered_combined_rejects_non_utf8_json_encoding() -> None:
    async def run() -> None:
        response = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "utterance": "hello",
                                    "state_candidates": [],
                                    "continuity_candidates": [],
                                },
                                separators=(",", ":"),
                            )
                        }
                    }
                ]
            },
            separators=(",", ":"),
        ).encode("utf-16")
        provider, client = await _provider_with_response(OpenAICompatibleProvider, response)
        try:
            with pytest.raises(ProviderProtocolError, match="UTF-8"):
                await provider.generate(_cognitive_input())
        finally:
            await client.aclose()

    asyncio.run(run())


def test_buffered_two_pass_conversation_rejects_invalid_utf8() -> None:
    async def run() -> None:
        response = b'{"choices":[{"message":{"content":"hello \xff"}}]}'
        provider, client = await _provider_with_response(
            OpenAICompatibleTwoPassProvider,
            response,
        )
        try:
            with pytest.raises(ProviderProtocolError, match="UTF-8"):
                await provider.generate_conversation(_cognitive_input())
        finally:
            await client.aclose()

    asyncio.run(run())


def test_buffered_two_pass_extraction_rejects_invalid_utf8() -> None:
    async def run() -> None:
        response = (
            b'{"choices":[{"message":{"content":"{\\"state_candidates\\":[{'
            b'\\"state_class\\":\\"user.preference\\",\\"key\\":\\"tea\\",'
            b'\\"op\\":\\"set\\",\\"value\\":\\"li\xffkes\\",'
            b'\\"sources\\":[\\"evt-now\\"]}],\\"continuity_candidates\\":[]}"}}]}'
        )
        provider, client = await _provider_with_response(
            OpenAICompatibleTwoPassProvider,
            response,
        )
        try:
            with pytest.raises(ProviderProtocolError, match="UTF-8"):
                await provider.generate_extraction(
                    CognitionExtractionInput(
                        cognitive_input=_cognitive_input(),
                        assistant_response="hello",
                    )
                )
        finally:
            await client.aclose()

    asyncio.run(run())
