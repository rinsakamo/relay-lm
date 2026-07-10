"""Characterization tests for the streaming `/v1/chat/completions` path.

Split from tests/test_chat_completions_characterization.py because stream
setup (SSE fixture bytes, `client.stream(...)` usage) is a distinct enough
shape to warrant its own file. See that file's module docstring for the
overall goals of this PR: pin observable behavior, not internals, ahead of
the shared-httpx-client / to_thread / handler-decomposition refactor PRs.
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
""".strip()

_RUN_ID_RE = re.compile(r"^run_[0-9a-f-]{36}$")

# A representative OpenAI-compatible SSE stream: a role-opening chunk,
# two content-delta chunks (in order), a terminal finish_reason chunk, then
# the `[DONE]` sentinel line OpenAI-compatible backends emit.
SSE_CHUNK_ROLE = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
}
SSE_CHUNK_CONTENT_1 = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "choices": [{"index": 0, "delta": {"content": "Hel"}, "finish_reason": None}],
}
SSE_CHUNK_CONTENT_2 = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "choices": [{"index": 0, "delta": {"content": "lo"}, "finish_reason": None}],
}
SSE_CHUNK_FINISH = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
}


def _sse_body() -> bytes:
    chunks = [SSE_CHUNK_ROLE, SSE_CHUNK_CONTENT_1, SSE_CHUNK_CONTENT_2, SSE_CHUNK_FINISH]
    lines = [f"data: {json.dumps(chunk)}\n\n".encode() for chunk in chunks]
    lines.append(b"data: [DONE]\n\n")
    return b"".join(lines)


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        MINIMAL_CONFIG_YAML.format(base_url=BACKEND_BASE_URL), encoding="utf-8"
    )
    return config_path


def _make_client(tmp_path: Path) -> TestClient:
    config_path = _write_config(tmp_path)
    app = create_app(str(config_path))
    return TestClient(app)


def _chat_stream_request(**overrides: object) -> dict:
    payload: dict = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "Hi"}],
        "stream": True,
    }
    payload.update(overrides)
    return payload


def _parsed_data_lines(raw_lines: list[str]) -> list[str]:
    """Collapse an SSE line stream into the ``data: ...`` payload lines."""
    return [line for line in raw_lines if line.startswith("data:")]


# ---------------------------------------------------------------------------
# 2. Stream success
# ---------------------------------------------------------------------------


def test_stream_success_returns_chunks_in_order_with_done_terminal(
    tmp_path: Path,
) -> None:
    client = _make_client(tmp_path)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(
                200,
                content=_sse_body(),
                headers={"content-type": "text/event-stream"},
            )
        )
        with client.stream(
            "POST", "/v1/chat/completions", json=_chat_stream_request()
        ) as response:
            assert response.status_code == 200
            # Coarse media-type check; do not pin an incidental charset
            # suffix Starlette/TestClient may append.
            assert response.headers["content-type"].startswith("text/event-stream")
            assert "x-relaylm-run-id" in response.headers
            assert _RUN_ID_RE.match(response.headers["x-relaylm-run-id"])

            raw_lines = list(response.iter_lines())

    data_lines = _parsed_data_lines(raw_lines)
    assert len(data_lines) == 5  # 4 chunks + terminal [DONE]

    # First chunk carries the opening role/delta structure.
    first_chunk = json.loads(data_lines[0].removeprefix("data: "))
    assert first_chunk["choices"][0]["delta"]["role"] == "assistant"

    # Content deltas arrive in order.
    second_chunk = json.loads(data_lines[1].removeprefix("data: "))
    third_chunk = json.loads(data_lines[2].removeprefix("data: "))
    assert second_chunk["choices"][0]["delta"]["content"] == "Hel"
    assert third_chunk["choices"][0]["delta"]["content"] == "lo"

    # Finish-reason chunk precedes the terminal [DONE] line.
    fourth_chunk = json.loads(data_lines[3].removeprefix("data: "))
    assert fourth_chunk["choices"][0]["finish_reason"] == "stop"
    assert data_lines[-1] == "data: [DONE]"

    # RelayLM forwarded exactly one request to the backend for this stream.
    assert route.call_count == 1
    sent_payload = json.loads(route.calls[0].request.content)
    assert sent_payload["model"] == "local-model"
    assert sent_payload["stream"] is True
    assert [m["role"] for m in sent_payload["messages"]] == ["user"]


# ---------------------------------------------------------------------------
# 6. Stream teardown
# ---------------------------------------------------------------------------


def test_stream_teardown_after_full_consumption_calls_backend_once(
    tmp_path: Path,
) -> None:
    """After a stream is fully consumed, the backend route was hit exactly
    once and iterating to completion does not hang or raise.
    """
    client = _make_client(tmp_path)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(
                200,
                content=_sse_body(),
                headers={"content-type": "text/event-stream"},
            )
        )
        with client.stream(
            "POST", "/v1/chat/completions", json=_chat_stream_request()
        ) as response:
            assert response.status_code == 200
            drained = b"".join(response.iter_bytes())

    assert route.call_count == 1
    assert drained  # bytes were actually produced, not an empty body
    assert drained.rstrip().endswith(b"data: [DONE]")


def test_stream_client_disconnect_before_full_consumption_does_not_hang(
    tmp_path: Path,
) -> None:
    """Coarse characterization of client-closes-mid-stream behavior.

    Reads only the first SSE line, then closes the response without
    draining the rest. This should not hang and the backend should still
    only have been called once. Kept intentionally coarse: TestClient does
    not give us a reliable hook into server-side cleanup timing, only that
    the overall request/response cycle completes promptly.
    """
    client = _make_client(tmp_path)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(
                200,
                content=_sse_body(),
                headers={"content-type": "text/event-stream"},
            )
        )
        with client.stream(
            "POST", "/v1/chat/completions", json=_chat_stream_request()
        ) as response:
            assert response.status_code == 200
            first_line = next(response.iter_lines())
            assert first_line.startswith("data:")
            # Exit the `with` block here without reading the rest of the
            # body -- characterizes an early client close.

    assert route.call_count == 1
