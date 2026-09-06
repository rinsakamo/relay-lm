from __future__ import annotations

import json

import httpx
import pytest

from relaylm.v2_transfer_actual_model import StructureProposalError
from tools.v2_cognitive_ir_calibration_reasoning_off import (
    ReasoningOffOpenAICompatibleStructuredCalibrationClient,
    build_reasoning_off_lmstudio_calibration_client,
)


_MESSAGES = (
    {"role": "system", "content": "Return the requested object."},
    {"role": "user", "content": "{}"},
)
_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "integer"}},
    "required": ["answer"],
    "additionalProperties": False,
}


def _response(
    *,
    finish_reason: str = "stop",
    reasoning_tokens: int = 0,
    reasoning_content: str | None = None,
    include_details: bool = True,
) -> dict[str, object]:
    message: dict[str, object] = {"content": '{"answer":1}'}
    if reasoning_content is not None:
        message["reasoning_content"] = reasoning_content
    usage: dict[str, object] = {
        "prompt_tokens": 10,
        "completion_tokens": 6,
    }
    if include_details:
        usage["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
    return {
        "id": "resp-1",
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": message,
            }
        ],
        "usage": usage,
    }


def test_reasoning_off_client_keeps_openai_wire_and_requires_zero_reasoning_tokens():
    observed_body: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal observed_body
        assert request.url.path == "/v1/chat/completions"
        observed_body = json.loads(request.content)
        return httpx.Response(200, json=_response())

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = ReasoningOffOpenAICompatibleStructuredCalibrationClient(
            base_url="http://lmstudio:1234/v1",
            model="google/gemma-4-12b",
            http_client=http_client,
        )
        completion = client.complete_structured(
            _MESSAGES,
            schema_name="answer",
            schema=_SCHEMA,
        )

    assert completion.content == '{"answer":1}'
    assert completion.input_tokens == 10
    assert completion.output_tokens == 6
    assert client.provider_attempts == client.provider_completions == 1
    assert "reasoning" not in observed_body
    assert observed_body["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "answer",
            "strict": True,
            "schema": _SCHEMA,
        },
    }
    assert client.transport_identity["reasoning_mode"] == "off"
    assert client.transport_identity["reasoning_verification"] == (
        "usage.completion_tokens_details.reasoning_tokens==0"
    )


def test_reasoning_off_client_rejects_nonzero_reasoning_tokens():
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json=_response(reasoning_tokens=4))

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = ReasoningOffOpenAICompatibleStructuredCalibrationClient(
            base_url="http://lmstudio:1234/v1",
            model="google/gemma-4-12b",
            http_client=http_client,
        )
        with pytest.raises(StructureProposalError, match="reasoning_tokens=4"):
            client.complete_structured(_MESSAGES, schema_name="answer", schema=_SCHEMA)

    assert client.provider_attempts == 1
    assert client.provider_completions == 0


def test_reasoning_off_client_rejects_nonempty_reasoning_content():
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json=_response(reasoning_content="hidden work"))

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = ReasoningOffOpenAICompatibleStructuredCalibrationClient(
            base_url="http://lmstudio:1234/v1",
            model="google/gemma-4-12b",
            http_client=http_client,
        )
        with pytest.raises(StructureProposalError, match="non-empty reasoning content"):
            client.complete_structured(_MESSAGES, schema_name="answer", schema=_SCHEMA)


def test_reasoning_off_client_reports_exact_nonstop_finish_reason():
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json=_response(finish_reason="length"))

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = ReasoningOffOpenAICompatibleStructuredCalibrationClient(
            base_url="http://lmstudio:1234/v1",
            model="google/gemma-4-12b",
            http_client=http_client,
        )
        with pytest.raises(StructureProposalError, match="'length'"):
            client.complete_structured(_MESSAGES, schema_name="answer", schema=_SCHEMA)


def test_reasoning_off_client_requires_explicit_reasoning_accounting():
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json=_response(include_details=False))

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = ReasoningOffOpenAICompatibleStructuredCalibrationClient(
            base_url="http://lmstudio:1234/v1",
            model="google/gemma-4-12b",
            http_client=http_client,
        )
        with pytest.raises(StructureProposalError, match="requires completion_tokens_details"):
            client.complete_structured(_MESSAGES, schema_name="answer", schema=_SCHEMA)


def test_default_reasoning_off_builder_freezes_existing_calibration_budget():
    client = build_reasoning_off_lmstudio_calibration_client(
        base_url="http://lmstudio:1234",
        model="google/gemma-4-12b",
    )
    try:
        assert client.transport_identity == {
            "api": "openai-chat-completions-json-schema-v1",
            "model": "google/gemma-4-12b",
            "timeout_seconds": 300.0,
            "max_tokens": 128,
            "temperature": 0.0,
            "seed": None,
            "structured_output": True,
            "reasoning_mode": "off",
            "reasoning_verification": (
                "usage.completion_tokens_details.reasoning_tokens==0"
            ),
        }
    finally:
        client.close()
