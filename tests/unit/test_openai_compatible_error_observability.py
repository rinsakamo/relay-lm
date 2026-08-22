from __future__ import annotations

import asyncio
import json

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
            timestamp="2026-08-21T00:00:00+00:00",
        ),
    )


@pytest.mark.parametrize("two_pass", [False, True])
def test_buffered_http_error_preserves_bounded_sanitized_upstream_detail(
    two_pass: bool,
) -> None:
    api_key = "super-secret-provider-key"
    long_detail = "prompt exceeds maximum context length " + ("x" * 5000)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": long_detail,
                    "type": "BadRequestError",
                    "echoed_secret": api_key,
                }
            },
        )

    async def run() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider_cls = (
                OpenAICompatibleTwoPassProvider if two_pass else OpenAICompatibleProvider
            )
            provider = provider_cls(
                base_url="http://provider.test/v1",
                model="gemma",
                api_key=api_key,
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError) as caught:
                if two_pass:
                    await provider.generate_conversation(_cognitive_input())
                else:
                    await provider.generate(_cognitive_input())
            return str(caught.value)

    message = asyncio.run(run())

    assert "status=400" in message
    assert "prompt exceeds maximum context length" in message
    assert api_key not in message
    assert "<redacted>" in message
    assert len(message) < 3000


@pytest.mark.parametrize("two_pass", [False, True])
def test_buffered_http_error_redacts_json_escaped_api_key(two_pass: bool) -> None:
    api_key = 'secret"quote\\slash\nline'

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "request rejected",
                    "echoed_secret": api_key,
                }
            },
        )

    async def run() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider_cls = (
                OpenAICompatibleTwoPassProvider if two_pass else OpenAICompatibleProvider
            )
            provider = provider_cls(
                base_url="http://provider.test/v1",
                model="gemma",
                api_key=api_key,
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError) as caught:
                if two_pass:
                    await provider.generate_conversation(_cognitive_input())
                else:
                    await provider.generate(_cognitive_input())
            return str(caught.value)

    message = asyncio.run(run())
    serialized_api_key = json.dumps(api_key, ensure_ascii=False)[1:-1]

    assert api_key not in message
    assert serialized_api_key not in message
    assert "<redacted>" in message


@pytest.mark.parametrize("two_pass", [False, True])
def test_streaming_http_error_preserves_upstream_detail_before_streaming_starts(
    two_pass: bool,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": "input tokens exceed max_model_len"}},
        )

    async def run() -> str:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider_cls = (
                OpenAICompatibleTwoPassProvider if two_pass else OpenAICompatibleProvider
            )
            provider = provider_cls(
                base_url="http://provider.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError) as caught:
                if two_pass:
                    await provider.stream_generate_conversation(_cognitive_input(), emit)
                else:
                    await provider.stream_generate(_cognitive_input(), emit)
            assert emitted == []
            return str(caught.value)

    message = asyncio.run(run())

    assert "status=400" in message
    assert "input tokens exceed max_model_len" in message
