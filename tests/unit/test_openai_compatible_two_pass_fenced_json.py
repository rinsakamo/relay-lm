from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError
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
            payload={"content": "最近コーヒーを飲んでる"},
            event_id="evt-now",
            timestamp="2026-08-25T00:00:00+00:00",
        ),
    )


def _extraction_input() -> CognitionExtractionInput:
    return CognitionExtractionInput(
        cognitive_input=_cognitive_input(),
        assistant_response="最近はコーヒーを飲んでるんだね。",
    )


def _wire() -> dict[str, object]:
    return {
        "state_candidates": [],
        "continuity_candidates": [],
    }


def _response_with_content(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": content},
                }
            ]
        },
    )


def _run_extraction(content: str):
    async def run():
        def handler(_: httpx.Request) -> httpx.Response:
            return _response_with_content(content)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://provider.test/v1",
                model="gemma",
                http_client=client,
            )
            return await provider.generate_extraction(_extraction_input())

    return asyncio.run(run())


def test_extraction_accepts_single_complete_json_fence_observed_by_stage_r() -> None:
    plain = json.dumps(_wire(), ensure_ascii=False)
    fenced = f"```json\n{plain}\n```"

    output = _run_extraction(fenced)

    assert output.state_candidates == ()
    assert output.continuity_candidates == ()


def test_extraction_still_accepts_plain_exact_json() -> None:
    output = _run_extraction(json.dumps(_wire(), ensure_ascii=False))

    assert output.state_candidates == ()
    assert output.continuity_candidates == ()


@pytest.mark.parametrize(
    "content",
    [
        "prefix\n```json\n{}\n```",
        "```json\n{}\n```\nsuffix",
        "```json\n{}\n```\n```json\n{}\n```",
        "```json\n{}",
        "```JSON\n{}\n```",
        "```\n{}\n```",
        "```python\n{}\n```",
    ],
)
def test_extraction_rejects_broader_markdown_recovery_forms(content: str) -> None:
    with pytest.raises(ProviderProtocolError, match="extraction content is not valid JSON"):
        _run_extraction(content)


def test_extraction_rejects_malformed_json_inside_exact_fence() -> None:
    with pytest.raises(ProviderProtocolError, match="extraction content is not valid JSON"):
        _run_extraction("```json\n{not-json}\n```")


def test_buffered_two_pass_http_failures_name_conversation_vs_extraction() -> None:
    async def run() -> tuple[str, str]:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": {"message": "request rejected"}},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://provider.test/v1",
                model="gemma",
                http_client=client,
            )
            with pytest.raises(ProviderProtocolError) as conversation_caught:
                await provider.generate_conversation(_cognitive_input())
            with pytest.raises(ProviderProtocolError) as extraction_caught:
                await provider.generate_extraction(_extraction_input())
            return str(conversation_caught.value), str(extraction_caught.value)

    conversation_message, extraction_message = asyncio.run(run())

    assert "conversation" in conversation_message
    assert "extraction" in extraction_message
    assert conversation_message != extraction_message
    assert "status=400" in conversation_message
    assert "status=400" in extraction_message
