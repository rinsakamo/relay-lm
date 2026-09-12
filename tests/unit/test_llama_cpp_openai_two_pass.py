from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.llama_cpp_openai import LlamaCppOpenAICompatibleTwoPassProvider
from relaylm.providers.llama_cpp_reasoning import LlamaCppReasoningCapabilityAttestation
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
)
from relaylm.state import STATE_CLASS_DEFINITIONS


MODEL = "gemma-local"


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "僕の名前はRinです。"},
            event_id="evt-now",
            timestamp="2026-09-09T00:00:00+00:00",
        ),
    )


def _provider(client: httpx.AsyncClient) -> LlamaCppOpenAICompatibleTwoPassProvider:
    return LlamaCppOpenAICompatibleTwoPassProvider(
        base_url="http://127.0.0.1:1234/v1",
        model=MODEL,
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset(
                {"temperature", "top_p", "max_output_tokens"}
            )
        ),
        llama_cpp_reasoning_capability=LlamaCppReasoningCapabilityAttestation(
            request_model=MODEL,
            enable_thinking_supported=True,
        ),
        http_client=client,
    )


def test_llama_cpp_two_pass_carries_reasoning_effort_none_and_native_schema() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        if len(seen) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": "Rinさん、こんにちは。"},
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "state_candidates": [],
                                    "continuity_candidates": [],
                                }
                            )
                        },
                    }
                ]
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = _provider(client)
            conversation = await provider.generate_conversation(
                _cognitive_input(),
                pass_request=CognitionPassRequest(
                    reasoning_mode=CognitionReasoningMode.OFF,
                    temperature=0.0,
                    top_p=1.0,
                    max_output_tokens=256,
                ),
            )
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=_cognitive_input(),
                    assistant_response=conversation.response,
                ),
                pass_request=CognitionPassRequest(
                    reasoning_mode=CognitionReasoningMode.OFF,
                    temperature=0.0,
                    top_p=1.0,
                    max_output_tokens=256,
                    structured_output_mode=CognitionStructuredOutputMode.NATIVE,
                ),
            )

    asyncio.run(run())

    assert len(seen) == 2
    assert all(body["reasoning_effort"] == "none" for body in seen)
    assert all("chat_template_kwargs" not in body for body in seen)
    assert all(body["temperature"] == 0.0 for body in seen)
    assert all(body["top_p"] == 1.0 for body in seen)
    assert all("seed" not in body for body in seen)
    assert all(body["max_tokens"] == 256 for body in seen)
    assert "response_format" not in seen[0]
    response_format = seen[1]["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True


def test_llama_cpp_extraction_restores_aliases_before_source_validation() -> None:
    seen_request: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_request.update(json.loads(request.content.decode("utf-8")))
        wire = {
            "state_candidates": [
                {
                    "state_class": "user.identity",
                    "key": "name",
                    "op": "set",
                    "value": "Rin",
                    "sources": ["E0"],
                }
            ],
            "continuity_candidates": [
                {
                    "kind": "active_task",
                    "key": "name_acknowledgement",
                    "op": "set",
                    "value": "acknowledge the user's name",
                    "sources": ["E0"],
                    "epistemic_role": "user_assertion",
                }
            ],
        }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": json.dumps(wire, ensure_ascii=False)},
                    }
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = _provider(client)
            return await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=_cognitive_input(),
                    assistant_response="Rinさん、こんにちは。",
                )
            )

    output = asyncio.run(run())

    assert output.state_candidates[0].sources == ("evt-now",)
    assert output.continuity_candidates[0].sources == ("evt-now",)
    request_text = json.dumps(seen_request, ensure_ascii=False, sort_keys=True)
    assert "evt-now" not in request_text
    assert "E0" in request_text


def test_llama_cpp_extraction_rejects_unknown_provider_alias() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        wire = {
            "state_candidates": [
                {
                    "state_class": "user.identity",
                    "key": "name",
                    "op": "set",
                    "value": "Rin",
                    "sources": ["E999"],
                }
            ],
            "continuity_candidates": [],
        }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": json.dumps(wire, ensure_ascii=False)},
                    }
                ]
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = _provider(client)
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=_cognitive_input(),
                    assistant_response="Rinさん、こんにちは。",
                )
            )

    with pytest.raises(ProviderProtocolError, match="provenance alias"):
        asyncio.run(run())
