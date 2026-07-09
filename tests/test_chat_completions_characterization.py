"""Characterization tests for the non-streaming `/v1/chat/completions` path.

These tests exist to PIN today's observable behavior of
``handle_managed_chat_completion`` (relaylm/managed_chat_runtime.py) so later
refactor PRs (shared httpx client, to_thread offload, decomposition of the
689-line handler) can be checked against them. They intentionally assert on
coarse, stable shapes (status codes, top-level response/error keys, the main
structure of the backend-bound payload) rather than full-dict equality, log
wording, timing values, or run/request IDs beyond format.

Any surprising-but-real behavior observed while writing these tests is noted
inline as a comment rather than "fixed" -- this file characterizes, it does
not correct.

Uses the same minimal-config pattern as tests/test_app_smoke.py (added in
PR-4): a bare pass-through route pointed at a mocked OpenAI-compatible
backend via respx.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

from relaylm.app import create_app

BACKEND_BASE_URL = "http://127.0.0.1:8000/v1"
BACKEND_CHAT_COMPLETIONS_URL = f"{BACKEND_BASE_URL}/chat/completions"

MINIMAL_CONFIG_YAML = """
backends:
  local_backend:
    base_url: {base_url}
    api_key: dummy
    default_model: local-model

model_routes:
  relaylm-default:
    backend: local_backend
    backend_model: local-model
{extra}
""".strip()

# A representative OpenAI-shaped non-stream backend response used across
# the success-path tests below.
BACKEND_CHAT_RESPONSE = {
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "local-model",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Hello there!"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
}

# Matches values produced by relaylm.relayrun.new_run_id() / uuid.uuid4().
_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_RUN_ID_RE = re.compile(r"^run_[0-9a-f-]{36}$")


def _write_config(tmp_path: Path, extra: str = "") -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        MINIMAL_CONFIG_YAML.format(base_url=BACKEND_BASE_URL, extra=extra),
        encoding="utf-8",
    )
    return config_path


def _make_client(tmp_path: Path, extra_config_yaml: str = "") -> TestClient:
    config_path = _write_config(tmp_path, extra=extra_config_yaml)
    app = create_app(str(config_path))
    return TestClient(app)


def _chat_request(**overrides: object) -> dict:
    payload: dict = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "Hi"}],
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# 1. Non-stream success
# ---------------------------------------------------------------------------


def test_nonstream_success_returns_openai_shaped_response(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_chat_request())

    assert response.status_code == 200
    body = response.json()

    # Top-level OpenAI schema keys RelayLM's response actually carries.
    assert body["id"] == "chatcmpl-abc123"
    assert body["object"] == "chat.completion"
    assert body["model"] == "local-model"
    assert isinstance(body["choices"], list) and len(body["choices"]) == 1
    message = body["choices"][0]["message"]
    assert message["role"] == "assistant"
    assert message["content"] == "Hello there!"

    # Diagnostics headers RelayLM attaches to every managed response. Pin
    # presence/format only -- not exact values (fallback_reason wording,
    # run status semantics, etc. are refactor-series internals).
    assert re.fullmatch(_UUID4_RE, response.headers["x-relaylm-request-id"])
    assert "x-relaylm-run-id" in response.headers
    assert _RUN_ID_RE.match(response.headers["x-relaylm-run-id"])
    assert response.headers["x-relaylm-mode"] == "pass_through"

    # RelayLM forwarded exactly one request to the backend.
    assert route.call_count == 1
    sent_payload = json.loads(route.calls[0].request.content)
    # Backend-bound payload's main structure: configured backend_model,
    # and the same message roles/sequence the client sent, in order.
    assert sent_payload["model"] == "local-model"
    assert [m["role"] for m in sent_payload["messages"]] == ["user"]
    assert sent_payload["messages"][0]["content"] == "Hi"
    # The client request had no "stream" key; RelayLM does not add one to
    # the non-stream backend-bound payload.
    assert "stream" not in sent_payload


def test_nonstream_success_forwards_multi_turn_messages_in_order(
    tmp_path: Path,
) -> None:
    client = _make_client(tmp_path)
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "How are you?"},
    ]

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post(
            "/v1/chat/completions", json=_chat_request(messages=messages)
        )

    assert response.status_code == 200
    assert route.call_count == 1
    sent_payload = json.loads(route.calls[0].request.content)
    assert [m["role"] for m in sent_payload["messages"]] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert [m["content"] for m in sent_payload["messages"]] == [
        m["content"] for m in messages
    ]


# ---------------------------------------------------------------------------
# 3. Validation errors
# ---------------------------------------------------------------------------


def test_malformed_json_body_returns_400_invalid_request_error(
    tmp_path: Path,
) -> None:
    client = _make_client(tmp_path)

    response = client.post(
        "/v1/chat/completions",
        content=b"{not valid json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    body = response.json()
    assert set(body.keys()) == {"error"}
    error = body["error"]
    assert set(error.keys()) == {"message", "type", "param", "code"}
    assert error["type"] == "invalid_request_error"
    assert isinstance(error["message"], str) and error["message"]


def test_missing_model_returns_400_invalid_request_error(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["type"] == "invalid_request_error"


def test_unknown_model_returns_400_invalid_request_error(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.post(
        "/v1/chat/completions",
        json=_chat_request(model="no-such-model"),
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["type"] == "invalid_request_error"


def test_invalid_stream_type_returns_400_invalid_request_error(
    tmp_path: Path,
) -> None:
    client = _make_client(tmp_path)

    response = client.post(
        "/v1/chat/completions",
        json=_chat_request(stream="yes"),
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["type"] == "invalid_request_error"


def test_missing_messages_is_not_validated_and_forwards_to_backend(
    tmp_path: Path,
) -> None:
    """Characterization, not endorsement.

    SURPRISING BEHAVIOR: RelayLM does not validate that a `messages` field
    is present at all. A request with only `model` set is accepted, routed,
    and forwarded to the backend with no `messages` key in the backend-bound
    payload -- the missing-field case is NOT rejected with a 4xx the way a
    missing `model` is. This test pins that current behavior; it does not
    assert it is desirable.
    """
    client = _make_client(tmp_path)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post(
            "/v1/chat/completions", json={"model": "relaylm-default"}
        )

    assert response.status_code == 200
    assert route.call_count == 1
    sent_payload = json.loads(route.calls[0].request.content)
    assert "messages" not in sent_payload
    assert sent_payload["model"] == "local-model"


# ---------------------------------------------------------------------------
# 4. Backend connection failure
# ---------------------------------------------------------------------------


def test_backend_connect_error_returns_502_backend_connection_error(
    tmp_path: Path,
) -> None:
    client = _make_client(tmp_path)

    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            side_effect=httpx.ConnectError("boom")
        )
        response = client.post("/v1/chat/completions", json=_chat_request())

    assert response.status_code == 502
    body = response.json()
    assert set(body.keys()) == {"error"}
    error = body["error"]
    assert set(error.keys()) == {"message", "type", "param", "code"}
    assert error["type"] == "backend_connection_error"
    assert isinstance(error["message"], str) and error["message"]


# ---------------------------------------------------------------------------
# 5. Backend HTTP 500
# ---------------------------------------------------------------------------


def test_backend_500_is_passed_through_unwrapped(tmp_path: Path) -> None:
    """Characterization: RelayLM does not translate/wrap backend HTTP error
    status codes the way it wraps connection failures (502). A backend 500
    with a JSON error body is relayed to the client with the same status
    code and the same body shape.
    """
    client = _make_client(tmp_path)
    backend_error_body = {
        "error": {"message": "boom", "type": "server_error"}
    }

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(500, json=backend_error_body)
        )
        response = client.post("/v1/chat/completions", json=_chat_request())

    assert response.status_code == 500
    assert route.call_count == 1
    body = response.json()
    assert set(body.keys()) == {"error"}
    assert body["error"]["message"] == "boom"
    assert body["error"]["type"] == "server_error"


# ---------------------------------------------------------------------------
# 7. Trace/diagnostics artifact
# ---------------------------------------------------------------------------


def test_trace_enabled_writes_artifact_with_stable_top_level_keys(
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "trace.jsonl"
    extra_config = (
        "\ntrace:\n"
        "  enabled: true\n"
        f"  path: {json.dumps(str(trace_path))}\n"
    )
    client = _make_client(tmp_path, extra_config_yaml=extra_config)

    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_chat_request())

    assert response.status_code == 200
    assert trace_path.exists()

    lines = [
        line for line in trace_path.read_text(encoding="utf-8").splitlines() if line
    ]
    assert len(lines) >= 1
    record = json.loads(lines[0])
    # Pin only the top-level key set of the trace artifact; nested pipeline
    # diagnostics are internal and not fixated here.
    assert set(record.keys()) == {
        "character_id",
        "compiler_used",
        "content_free",
        "created_at",
        "message_count",
        "metadata",
        "mode_applied",
        "request_id",
        "response_present",
        "route_model",
        "schema_version",
        "trace_id",
    }
