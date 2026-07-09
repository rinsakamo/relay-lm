"""Tests for the shared `httpx.AsyncClient` introduced to replace the
per-request client that `relaylm/adapter.py` used to create for every
backend call.

These pin the behavior the maintainer signed off on for this refactor:

* one shared client is created (via `relaylm.app`'s lifespan in production,
  or lazily via `relaylm.app_response_finalization.get_shared_http_client`
  when a test harness never runs lifespan) and reused across requests;
* the client itself is timeout-neutral -- `route.backend.timeout_seconds`
  is applied per request;
* only the backend response/stream is closed at the end of a streamed
  request, never the shared client, on every teardown path: normal
  exhaustion, mid-stream client disconnect, and abandonment via
  `close_stream_iterator`.

Most of the non-stream-teardown assertions here (non-stream success,
stream success, backend connect failure, backend HTTP 500) already exist
as characterization tests from PR-5 (see
tests/test_chat_completions_characterization.py and
tests/test_chat_completions_streaming_characterization.py) and must stay
green unchanged -- this file is not a replacement for those, it re-asserts
the same observable behavior through the lens of the shared client (and
adds client-identity/teardown assertions those files don't make).

`TestClient(app)` (used without a `with` block, matching the rest of this
test suite) never runs FastAPI's lifespan, so it only exercises the lazy
`get_shared_http_client` fallback path -- not lifespan startup/shutdown.
Genuine mid-stream client disconnect cannot be observed through
`TestClient`: its synchronous interface drives the whole ASGI call to
completion inside a background-thread portal before handing back a
response, so the server side always finishes producing the full body
regardless of what the local reader does. Tests 3 and 6b instead drive the
app directly over `httpx.ASGITransport` inside a real asyncio event loop,
where closing the client-side response early actually cancels the
in-flight server-side generator.
"""
from __future__ import annotations

import asyncio
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

SSE_CHUNKS = [
    b'data: {"choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}\n\n',
    b'data: {"choices":[{"index":0,"delta":{"content":"Hel"},"finish_reason":null}]}\n\n',
    b'data: {"choices":[{"index":0,"delta":{"content":"lo"},"finish_reason":null}]}\n\n',
    b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n',
    b"data: [DONE]\n\n",
]


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        MINIMAL_CONFIG_YAML.format(base_url=BACKEND_BASE_URL), encoding="utf-8"
    )
    return config_path


def _make_app(tmp_path: Path):
    config_path = _write_config(tmp_path)
    return create_app(str(config_path))


def _chat_request(**overrides: object) -> dict:
    payload: dict = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "Hi"}],
    }
    payload.update(overrides)
    return payload


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# 1. Non-stream success through the shared client
# ---------------------------------------------------------------------------


def test_nonstream_success_through_shared_client(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        response = client.post("/v1/chat/completions", json=_chat_request())

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "Hello there!"
    assert route.call_count == 1

    # TestClient(app) without a `with` block never runs lifespan, so this
    # request must have gone through the lazy get_shared_http_client()
    # fallback -- and it must be a real, still-open httpx.AsyncClient.
    shared_client = app.state.http_client
    assert isinstance(shared_client, httpx.AsyncClient)
    assert not shared_client.is_closed


# ---------------------------------------------------------------------------
# 2. Stream success
# ---------------------------------------------------------------------------


def test_stream_success_through_shared_client(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    payload = _chat_request(stream=True)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(
                200,
                content=b"".join(SSE_CHUNKS),
                headers={"content-type": "text/event-stream"},
            )
        )
        with client.stream("POST", "/v1/chat/completions", json=payload) as response:
            assert response.status_code == 200
            data_lines = [
                line for line in response.iter_lines() if line.startswith("data:")
            ]

    assert route.call_count == 1
    assert data_lines[-1] == "data: [DONE]"
    assert isinstance(app.state.http_client, httpx.AsyncClient)


# ---------------------------------------------------------------------------
# 3. Mid-stream client disconnect
# ---------------------------------------------------------------------------


def test_mid_stream_client_disconnect_closes_backend_stream_not_client(
    tmp_path: Path,
) -> None:
    app = _make_app(tmp_path)
    payload = _chat_request(stream=True)
    call_count = {"count": 0}
    closed = {"value": False}

    class _TrackingStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for chunk in SSE_CHUNKS:
                await asyncio.sleep(0.02)
                yield chunk

        async def aclose(self) -> None:
            closed["value"] = True

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["count"] += 1
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_TrackingStream(),
        )

    backend_transport = httpx.MockTransport(handler)

    async def scenario() -> None:
        # Force the shared client (created lazily on first use, since this
        # test never runs lifespan either) onto the tracking transport
        # above so we can observe the backend stream's close.
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("transport", backend_transport)
            original_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = patched_init
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as frontend_client:
                async with frontend_client.stream(
                    "POST", "/v1/chat/completions", json=payload
                ) as response:
                    assert response.status_code == 200
                    got_first_line = False
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            got_first_line = True
                            break
                    assert got_first_line
                    # Exiting these `async with` blocks now, before the SSE
                    # stream is fully drained, characterizes a client that
                    # disconnects mid-stream.
        finally:
            httpx.AsyncClient.__init__ = original_init

        # Give the server-side task a moment to observe the cancellation
        # and run its teardown.
        for _ in range(20):
            if closed["value"]:
                break
            await asyncio.sleep(0.02)

    _run(scenario())

    assert call_count["count"] == 1
    assert closed["value"] is True, "backend stream must be closed on disconnect"
    shared_client = getattr(app.state, "http_client", None)
    assert shared_client is not None
    assert not shared_client.is_closed, "shared client must survive a client disconnect"


# ---------------------------------------------------------------------------
# 4. Backend connect failure
# ---------------------------------------------------------------------------


def test_backend_connect_failure_returns_502_and_keeps_shared_client(
    tmp_path: Path,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)

    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            side_effect=httpx.ConnectError("boom")
        )
        response = client.post("/v1/chat/completions", json=_chat_request())

    assert response.status_code == 502
    assert response.json()["error"]["type"] == "backend_connection_error"

    shared_client = app.state.http_client
    assert isinstance(shared_client, httpx.AsyncClient)
    assert not shared_client.is_closed, (
        "a failed backend connect attempt must not close the shared client"
    )


# ---------------------------------------------------------------------------
# 5. Backend HTTP 500
# ---------------------------------------------------------------------------


def test_backend_500_passed_through_and_keeps_shared_client(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    backend_error_body = {"error": {"message": "boom", "type": "server_error"}}

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(500, json=backend_error_body)
        )
        response = client.post("/v1/chat/completions", json=_chat_request())

    assert response.status_code == 500
    assert route.call_count == 1
    assert response.json()["error"]["message"] == "boom"

    shared_client = app.state.http_client
    assert isinstance(shared_client, httpx.AsyncClient)
    assert not shared_client.is_closed


# ---------------------------------------------------------------------------
# 6. Backend stream close is ALWAYS called
# ---------------------------------------------------------------------------


def test_backend_stream_closed_on_normal_exhaustion(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    payload = _chat_request(stream=True)
    closed = {"value": False}

    class _TrackingStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for chunk in SSE_CHUNKS:
                yield chunk

        async def aclose(self) -> None:
            closed["value"] = True

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_TrackingStream(),
        )

    backend_transport = httpx.MockTransport(handler)

    async def scenario() -> None:
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("transport", backend_transport)
            original_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = patched_init
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as frontend_client:
                async with frontend_client.stream(
                    "POST", "/v1/chat/completions", json=payload
                ) as response:
                    assert response.status_code == 200
                    async for _line in response.aiter_lines():
                        pass  # Drain fully -- normal exhaustion.
        finally:
            httpx.AsyncClient.__init__ = original_init

    _run(scenario())

    assert closed["value"] is True
    shared_client = getattr(app.state, "http_client", None)
    assert shared_client is not None
    assert not shared_client.is_closed


def test_backend_stream_closed_on_mid_stream_abandonment(tmp_path: Path) -> None:
    # Same shape as test 3 above, phrased as the "always called" pairing
    # the maintainer asked for: an abandoned stream must still close the
    # backend response even though nothing downstream is left reading it.
    app = _make_app(tmp_path)
    payload = _chat_request(stream=True)
    closed = {"value": False}

    class _TrackingStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for chunk in SSE_CHUNKS:
                await asyncio.sleep(0.02)
                yield chunk

        async def aclose(self) -> None:
            closed["value"] = True

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_TrackingStream(),
        )

    backend_transport = httpx.MockTransport(handler)

    async def scenario() -> None:
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("transport", backend_transport)
            original_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = patched_init
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as frontend_client:
                async with frontend_client.stream(
                    "POST", "/v1/chat/completions", json=payload
                ) as response:
                    assert response.status_code == 200
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            break  # Abandon after the first line.
        finally:
            httpx.AsyncClient.__init__ = original_init

        for _ in range(20):
            if closed["value"]:
                break
            await asyncio.sleep(0.02)

    _run(scenario())

    assert closed["value"] is True


# ---------------------------------------------------------------------------
# Shared client identity across sequential requests
# ---------------------------------------------------------------------------


def test_sequential_requests_reuse_the_same_shared_client_instance(
    tmp_path: Path,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)

    with respx.mock(assert_all_called=False) as mock:
        mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
        )
        first_response = client.post("/v1/chat/completions", json=_chat_request())
        first_client_id = id(app.state.http_client)

        second_response = client.post("/v1/chat/completions", json=_chat_request())
        second_client_id = id(app.state.http_client)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_client_id == second_client_id
