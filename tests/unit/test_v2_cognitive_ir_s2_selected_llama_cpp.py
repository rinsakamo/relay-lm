from __future__ import annotations

import json

import httpx
import pytest

from relaylm.v2_transfer_actual_model import StructureProposalError
from tools.v2_cognitive_ir_s2_host import S2HostError
from tools.v2_cognitive_ir_s2_selected_llama_cpp import (
    LlamaCppThinkingOffInputCounter,
    S2_SELECTED_LLAMA_CPP_CALL_PLAN,
    S2_SELECTED_LLAMA_CPP_ENDPOINT,
    S2_SELECTED_LLAMA_CPP_REASONING_EFFORT,
    S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS,
    SelectedS2LlamaCppClient,
    probe_llama_cpp_selected_s2_binding,
)


def _messages() -> tuple[dict[str, str], ...]:
    return (
        {"role": "system", "content": "Return a concise answer."},
        {"role": "user", "content": "hello"},
    )


def test_selected_llama_cpp_client_carries_reasoning_none_through_generation_and_counting() -> None:
    counted: list[dict[str, object]] = []
    generated: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if request.url.path.endswith("/chat/completions/input_tokens"):
            counted.append(body)
            empty = all(message["content"] == "" for message in body["messages"])
            return httpx.Response(200, json={"input_tokens": 3 if empty else 11})
        if request.url.path.endswith("/chat/completions"):
            generated.append(body)
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-test",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": "ok"},
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 11,
                        "completion_tokens": 1,
                    },
                },
            )
        raise AssertionError(request.url.path)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = SelectedS2LlamaCppClient(
            base_url=S2_SELECTED_LLAMA_CPP_ENDPOINT,
            model="fresh-request-model",
            http_client=http_client,
        )
        completion = client.complete(_messages())

    assert completion.input_tokens == 11
    assert client.provider_attempts == 1
    assert client.provider_completions == 1
    assert client.input_count_attempts == 2
    assert client.input_count_completions == 2
    assert len(counted) == 2
    assert len(generated) == 1

    for body in (*counted, *generated):
        assert body["reasoning_effort"] == S2_SELECTED_LLAMA_CPP_REASONING_EFFORT
        assert body["model"] == "fresh-request-model"
        assert body["stream"] is False

    assert counted[0] == generated[0]
    expected_framing = dict(generated[0])
    expected_framing["messages"] = [
        {"role": message["role"], "content": ""}
        for message in generated[0]["messages"]
    ]
    assert counted[1] == expected_framing


def test_selected_llama_cpp_exact_counter_fail_closes_missing_or_wrong_reasoning_effort() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("invalid reasoning control must fail before HTTP")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        counter = LlamaCppThinkingOffInputCounter(
            base_url=S2_SELECTED_LLAMA_CPP_ENDPOINT,
            model="fresh-request-model",
            http_client=http_client,
        )
        base = {
            "model": "fresh-request-model",
            "messages": [
                {"role": "user", "content": "hello"},
            ],
            "stream": False,
        }
        with pytest.raises(S2HostError, match="reasoning_effort"):
            counter.count_input(base)
        with pytest.raises(S2HostError, match="reasoning_effort"):
            counter.count_input({**base, "reasoning_effort": "low"})


def test_selected_llama_cpp_client_rejects_nonzero_reasoning_tokens_when_exposed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if request.url.path.endswith("/chat/completions/input_tokens"):
            empty = all(message["content"] == "" for message in body["messages"])
            return httpx.Response(200, json={"input_tokens": 3 if empty else 11})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "ok"},
                    }
                ],
                "usage": {
                    "prompt_tokens": 11,
                    "completion_tokens": 4,
                    "completion_tokens_details": {"reasoning_tokens": 3},
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = SelectedS2LlamaCppClient(
            base_url=S2_SELECTED_LLAMA_CPP_ENDPOINT,
            model="fresh-request-model",
            http_client=http_client,
        )
        with pytest.raises(StructureProposalError, match="reasoning_tokens=3"):
            client.complete(_messages())


def test_selected_llama_cpp_transport_identity_freezes_explicit_reasoning_control() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("transport identity is non-generative")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = SelectedS2LlamaCppClient(
            base_url=S2_SELECTED_LLAMA_CPP_ENDPOINT,
            model="fresh-request-model",
            http_client=http_client,
        )
        identity = client.transport_identity

    assert identity["reasoning"] == "off"
    assert identity["reasoning_control"] == "openai-top-level-reasoning_effort"
    assert identity["reasoning_effort"] == "none"
    assert identity["timeout_seconds"] == S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS
    assert identity["exact_input_accounting"] == (
        "chat-completions-input-tokens-full+empty-message-framing-v1"
    )


def test_selected_llama_cpp_endpoint_is_loopback_only_and_has_no_lmstudio_fallback() -> None:
    with pytest.raises(S2HostError, match="endpoint"):
        SelectedS2LlamaCppClient(
            base_url="http://192.168.50.26:1234/v1",
            model="fresh-request-model",
        )
    with pytest.raises(S2HostError, match="endpoint"):
        SelectedS2LlamaCppClient(
            base_url="http://127.0.0.1:1235/v1",
            model="fresh-request-model",
        )


def _controller_identity() -> dict[str, object]:
    return {
        "upstream_revision": "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d",
        "build_info": "llama.cpp build 10874 e2d2c0d6",
        "binary_path": "/tmp/llama-server",
        "binary_sha256": "a" * 64,
        "model_path": "/tmp/model.gguf",
        "artifact_sha256": "b" * 64,
        "context_shift_enabled": False,
        "launch": {"context": 8192, "context_shift": False},
        "hardware": {"gpu": "test-gpu"},
        "capacity_evidence": {"slots": 2},
    }


def test_selected_llama_cpp_binding_uses_fresh_request_alias_and_attests_context(monkeypatch) -> None:
    controller = _controller_identity()

    def fake_sha(path: str) -> str:
        if path.endswith("llama-server"):
            return "a" * 64
        if path.endswith("model.gguf"):
            return "b" * 64
        raise AssertionError(path)

    monkeypatch.setattr(
        "tools.v2_cognitive_ir_s2_selected_llama_cpp._sha256_file",
        fake_sha,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/v1/models":
            return httpx.Response(
                200,
                json={"data": [{"id": "fresh-request-model"}]},
            )
        if request.url.path == "/props":
            return httpx.Response(
                200,
                json={
                    "build_info": controller["build_info"],
                    "model_alias": "fresh-request-model",
                    "model_path": controller["model_path"],
                    "model_ftype": "Q4_K_M",
                    "chat_template": "{{ messages }}",
                    "default_generation_settings": {"n_ctx": 8192},
                    "total_slots": 2,
                },
            )
        if request.url.path == "/slots":
            return httpx.Response(
                200,
                json=[
                    {"id": 0, "n_ctx": 8192},
                    {"id": 1, "n_ctx": 8192},
                ],
            )
        raise AssertionError(request.url.path)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        binding = probe_llama_cpp_selected_s2_binding(
            base_url=S2_SELECTED_LLAMA_CPP_ENDPOINT,
            model="fresh-request-model",
            controller_identity=controller,
            http_client=http_client,
        )

    assert binding["model"] == "fresh-request-model"
    runtime = binding["runtime_attestation"]
    assert runtime["model_alias"] == "fresh-request-model"
    assert runtime["context_limit"] == 8192
    assert runtime["total_slots"] == 2
    assert runtime["context_shift_enabled"] is False


def test_selected_llama_cpp_binding_rejects_live_context_mismatch(monkeypatch) -> None:
    controller = _controller_identity()
    monkeypatch.setattr(
        "tools.v2_cognitive_ir_s2_selected_llama_cpp._sha256_file",
        lambda path: "a" * 64 if str(path).endswith("llama-server") else "b" * 64,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "fresh-request-model"}]})
        if request.url.path == "/props":
            return httpx.Response(
                200,
                json={
                    "build_info": controller["build_info"],
                    "model_alias": "fresh-request-model",
                    "model_path": controller["model_path"],
                    "model_ftype": "Q4_K_M",
                    "chat_template": "{{ messages }}",
                    "default_generation_settings": {"n_ctx": 4352},
                    "total_slots": 1,
                },
            )
        if request.url.path == "/slots":
            return httpx.Response(200, json=[{"id": 0, "n_ctx": 4352}])
        raise AssertionError(request.url.path)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(S2HostError, match="context_length=8192"):
            probe_llama_cpp_selected_s2_binding(
                base_url=S2_SELECTED_LLAMA_CPP_ENDPOINT,
                model="fresh-request-model",
                controller_identity=controller,
                http_client=http_client,
            )


def test_selected_llama_cpp_preserves_preregistered_exact_ten_call_schedule() -> None:
    assert S2_SELECTED_LLAMA_CPP_CALL_PLAN == (
        "form-p2",
        "form-p3",
        "form-p4",
        "probe-p0",
        "probe-p1",
        "probe-p2",
        "probe-p3",
        "probe-p4",
        "probe-p5",
        "probe-p6",
    )
