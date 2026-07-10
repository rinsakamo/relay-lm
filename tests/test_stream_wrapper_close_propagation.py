"""Regression tests for close propagation through backend stream wrappers."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx

from relaylm.adapter import (
    _ClosePropagatingAsyncIterator,
    open_chat_completion_stream,
)

BACKEND_BASE_URL = "http://127.0.0.1:8000/v1"
BACKEND_CHAT_COMPLETIONS_URL = f"{BACKEND_BASE_URL}/chat/completions"

SSE_CHUNKS = [
    b'data: {"choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}\n\n',
    b'data: {"choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}\n\n',
    b"data: [DONE]\n\n",
]


def _route_with_stream_wrappers_enabled():
    return SimpleNamespace(
        backend=SimpleNamespace(
            base_url=BACKEND_BASE_URL,
            api_key="dummy",
            timeout_seconds=60.0,
        ),
        backend_model="local-model",
        mode_applied="memory_light",
        client_history_exclusion_apply_enabled=False,
        client_history_exclusion_apply_dry_run_only=True,
        relayctx_stream_unpack_dry_run_enabled=True,
        relayctx_stream_unpack_dry_run_only=False,
        relayctx_stream_unpack_max_buffer_chars=256,
        relayctx_tts_adapter_handoff_runtime_enabled=True,
        relayctx_tts_adapter_handoff_runtime_dry_run_only=True,
        relayctx_tts_adapter_handoff_max_segment_chars=120,
        relayctx_tts_adapter_handoff_min_segment_chars=8,
    )


def _chat_request() -> dict[str, object]:
    return {
        "model": "relaylm-default",
        "stream": True,
        "messages": [{"role": "user", "content": "Hi"}],
    }


def test_abandoned_wrapped_stream_closes_backend_before_iteration() -> None:
    """Unstarted RelayCTX/TTS async-generator wrappers must not hide backend close.

    Durable-finalization fail-closed branches can call ``close_stream_iterator``
    immediately after ``open_chat_completion_stream`` returns, before any body
    chunk is requested. Plain ``aclose()`` on an unstarted async generator does
    not enter that generator's body/finally, so the adapter must preserve a
    direct close hook to the backend response iterator even when the public
    iterator has been wrapped by RelayCTX and TTS stream observers.
    """

    closed = {"value": False}

    class _TrackingStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for chunk in SSE_CHUNKS:
                yield chunk

        async def aclose(self) -> None:
            closed["value"] = True

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == BACKEND_CHAT_COMPLETIONS_URL
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_TrackingStream(),
        )

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            status_code, content_type, body_iter = await open_chat_completion_stream(
                _chat_request(),
                _route_with_stream_wrappers_enabled(),
                client,
            )
            assert status_code == 200
            assert content_type == "text/event-stream"

            # Close before the first __anext__ call. This is the path that used to
            # leak the checked-out backend response when stream wrappers were active.
            await body_iter.aclose()  # type: ignore[attr-defined]

            assert closed["value"] is True
            assert not client.is_closed

    asyncio.run(scenario())


def test_wrapper_terminal_completion_closes_direct_backend_target() -> None:
    """A wrapper that ends early must still close the direct backend target."""

    closed = {"value": False}

    class _CloseTarget:
        async def aclose(self) -> None:
            closed["value"] = True

    async def empty_wrapper():
        if False:
            yield b"unreachable"

    async def scenario() -> None:
        body_iter = _ClosePropagatingAsyncIterator(
            empty_wrapper(),
            close_targets=(_CloseTarget(),),
        )
        try:
            await body_iter.__anext__()
        except StopAsyncIteration:
            pass
        else:  # pragma: no cover - defensive assertion branch
            raise AssertionError("empty wrapper unexpectedly yielded a chunk")
        assert closed["value"] is True

    asyncio.run(scenario())
