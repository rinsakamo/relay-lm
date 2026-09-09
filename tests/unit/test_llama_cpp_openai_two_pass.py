from __future__ import annotations

import asyncio
import json

import httpx

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
            provider = LlamaCppOpenAICompatibleTwoPassProvider(
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
