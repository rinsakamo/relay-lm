from __future__ import annotations

import json

import httpx
import pytest

from tools.v2_cognitive_ir_s2_host import S2HostError
from tools.v2_cognitive_ir_s3_llama_cpp import S3LlamaCppClient


def test_s3_transport_preserves_reasoning_off_and_two_exact_counts() -> None:
    seen: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append((request.url.path, body))
        if request.url.path.endswith("/input_tokens"):
            return httpx.Response(200, json={"input_tokens": 17})
        return httpx.Response(
            200,
            json={
                "id": "s3-test",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "[1,2,3,4]", "reasoning": ""},
                    }
                ],
                "usage": {
                    "prompt_tokens": 17,
                    "completion_tokens": 5,
                    "completion_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = S3LlamaCppClient(
        base_url="http://127.0.0.1:1234/v1",
        model="model.gguf",
        call_plan=("q1",),
        http_client=http_client,
    )
    try:
        completion = client.complete_named(
            "q1",
            ({"role": "user", "content": "solve"},),
            output_kind="vector",
        )
        client.require_complete_plan()
    finally:
        client.close()
        http_client.close()

    assert completion.input_tokens == 17
    assert client.provider_attempts == client.provider_completions == 1
    assert client.input_count_attempts == client.input_count_completions == 2
    assert [path for path, _ in seen] == [
        "/v1/chat/completions/input_tokens",
        "/v1/chat/completions/input_tokens",
        "/v1/chat/completions",
    ]
    full = seen[0][1]
    framing = seen[1][1]
    generation = seen[2][1]
    assert full == generation
    assert full["reasoning_effort"] == "none"
    assert framing["reasoning_effort"] == "none"
    assert framing["messages"] == [{"role": "user", "content": ""}]
    assert generation["stream"] is False
    assert generation["temperature"] == 0.0
    assert generation["max_tokens"] == 512
    assert generation["response_format"]["json_schema"]["strict"] is True


def test_s3_transport_fails_closed_on_order_and_endpoint() -> None:
    http_client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    with pytest.raises(S2HostError):
        S3LlamaCppClient(
            base_url="http://192.168.50.26:1234/v1",
            model="model.gguf",
            call_plan=("q1",),
            http_client=http_client,
        )
    client = S3LlamaCppClient(
        base_url="http://127.0.0.1:1234/v1",
        model="model.gguf",
        call_plan=("q1",),
        http_client=http_client,
    )
    try:
        with pytest.raises(Exception, match="call order drift"):
            client.complete_named(
                "q2",
                ({"role": "user", "content": "solve"},),
                output_kind="vector",
            )
    finally:
        client.close()
        http_client.close()
