from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.llama_cpp_backend import (
    LLAMA_CPP_SUPPORTED_BUILD,
    LLAMA_CPP_SUPPORTED_UPSTREAM_REVISION,
    LlamaCppCapabilityAttestation,
    LlamaCppChatInputCounter,
    LlamaCppInputCounterError,
    LlamaCppRuntimeIdentity,
    resolve_llama_cpp_pass_request,
)
from relaylm.providers.llama_cpp_openai import LlamaCppOpenAICompatibleTwoPassProvider
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingConfig,
)
from relaylm.cognitive import CognitiveInput
from relaylm.state import STATE_CLASS_DEFINITIONS


MODEL = "gemma-local"


def _identity() -> LlamaCppRuntimeIdentity:
    return LlamaCppRuntimeIdentity(
        upstream_revision=LLAMA_CPP_SUPPORTED_UPSTREAM_REVISION,
        build_info=f"llama.cpp {LLAMA_CPP_SUPPORTED_BUILD}",
        model_alias=MODEL,
        model_path="/models/gemma-local.gguf",
        model_ftype="Q4_K_M",
        artifact_sha256="a" * 64,
        chat_template_sha256="b" * 64,
        context_limit=8192,
        total_slots=1,
        context_shift_enabled=False,
    )


def _capability(
    *,
    streaming_supported: bool = True,
    structured_output_supported: bool = True,
    reasoning_off_supported: bool = True,
) -> LlamaCppCapabilityAttestation:
    return LlamaCppCapabilityAttestation(
        runtime_identity=_identity(),
        reasoning_effort_none_supported=reasoning_off_supported,
        native_structured_output_supported=structured_output_supported,
        streaming_supported=streaming_supported,
        decoding_controls=frozenset(
            {"temperature", "top_p", "max_output_tokens"}
        ),
    )


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
            timestamp="2026-09-09T00:00:00+00:00",
        ),
    )


def test_exact_counter_uses_full_and_empty_content_framing() -> None:
    seen: list[tuple[str, dict[str, object], str | None]] = []

    def post_json(url: str, payload: dict[str, object], api_key: str | None) -> object:
        seen.append((url, payload, api_key))
        return {"input_tokens": 31 if len(seen) == 1 else 9}

    counter = LlamaCppChatInputCounter(
        base_url="http://127.0.0.1:1234/v1",
        runtime_identity=_identity(),
        api_key="secret",
        post_json=post_json,
    )
    result = counter.count_input(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": "hello"}],
            "temperature": 0.0,
            "cache_prompt": False,
            "reasoning_effort": "none",
        }
    )

    assert result.total_input_tokens == 31
    assert result.required_input_framing_tokens == 9
    assert len(seen) == 2
    assert seen[0][0].endswith("/v1/chat/completions/input_tokens")
    assert seen[0][1]["messages"] == [{"role": "user", "content": "hello"}]
    assert seen[1][1]["messages"] == [{"role": "user", "content": ""}]
    assert all(payload["cache_prompt"] is False for _, payload, _ in seen)
    assert all(payload["reasoning_effort"] == "none" for _, payload, _ in seen)
    assert all(api_key == "secret" for _, _, api_key in seen)
    assert "secret" not in repr(counter.evidence_identity)


def test_exact_counter_rejects_unknown_or_unproven_fields() -> None:
    counter = LlamaCppChatInputCounter(
        base_url="http://127.0.0.1:1234/v1",
        runtime_identity=_identity(),
        post_json=lambda *_: {"input_tokens": 1},
    )

    with pytest.raises(LlamaCppInputCounterError, match="unsupported llama.cpp"):
        counter.count_input(
            {
                "model": MODEL,
                "messages": [{"role": "user", "content": "hello"}],
                "unknown": True,
            }
        )
    with pytest.raises(LlamaCppInputCounterError, match="cache_prompt=false"):
        counter.count_input(
            {
                "model": MODEL,
                "messages": [{"role": "user", "content": "hello"}],
                "cache_prompt": True,
            }
        )


def test_unattested_streaming_fails_before_transport() -> None:
    with pytest.raises(ValueError):
        resolve_llama_cpp_pass_request(
            pass_request=None,
            reasoning_request=None,
            decoding_config=OpenAICompatibleDecodingConfig(),
            capability=_capability(streaming_supported=False),
            streaming=True,
        )


def test_full_llama_provider_uses_cache_off_on_buffered_streaming_and_pass2() -> None:
    seen: list[dict[str, object]] = []
    pass_request = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.OFF,
        temperature=0.0,
        top_p=1.0,
        max_output_tokens=128,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        seen.append(body)
        if body.get("stream"):
            content = (
                'data: {"choices":[{"delta":{"content":"streamed"},'
                '"finish_reason":null}]}\n\n'
                'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
                "data: [DONE]\n\n"
            )
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=content.encode("utf-8"),
            )
        if "response_format" in body:
            content = json.dumps(
                {"state_candidates": [], "continuity_candidates": []}
            )
        else:
            content = "buffered"
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

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = LlamaCppOpenAICompatibleTwoPassProvider(
                base_url="http://127.0.0.1:1234/v1",
                model=MODEL,
                decoding_capabilities=_capability().decoding_capabilities,
                llama_cpp_capability=_capability(),
                http_client=client,
            )
            await provider.generate_conversation(
                _cognitive_input(), pass_request=pass_request
            )
            await provider.stream_generate_conversation(
                _cognitive_input(),
                lambda _: asyncio.sleep(0),
                pass_request=pass_request,
            )
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=_cognitive_input(),
                    assistant_response="buffered",
                ),
                pass_request=(
                    CognitionPassRequest(
                        reasoning_mode=CognitionReasoningMode.OFF,
                        temperature=0.0,
                        top_p=1.0,
                        max_output_tokens=128,
                        structured_output_mode=CognitionStructuredOutputMode.NATIVE,
                    )
                ),
            )

    asyncio.run(run())

    assert len(seen) == 3
    assert all(body["cache_prompt"] is False for body in seen)
    assert all(body["reasoning_effort"] == "none" for body in seen)
    assert seen[0]["stream"] is False
    assert seen[1]["stream"] is True
    assert seen[2]["stream"] is False
    assert seen[2]["response_format"]["type"] == "json_schema"
