"""OpenAI-compatible backend adapter for RelayLM MVP-0."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx

from relaylm.client_history_exclusion_apply_runtime import (
    client_history_exclusion_apply_blocks_backend,
    client_history_exclusion_apply_failure_reason,
)
from relaylm.client_instruction_source import strip_relaylm_control
from relaylm.pipeline_context import get_active_pipeline_context
from relaylm.relayctx_stream_suppression_runtime import (
    wrap_stream_with_relayctx_suppression,
)
from relaylm.relayctx_tts_adapter_handoff_runtime import (
    wrap_stream_with_tts_adapter_handoff,
)
from relaylm.relayctx_unpack_runtime import apply_relayctx_unpack_runtime
from relaylm.routing import ResolvedRoute


OPENAI_CHAT_COMPLETIONS_PATH = "/chat/completions"


class BackendRequestError(RuntimeError):
    """Raised when RelayLM cannot safely forward to or reach the backend."""


class _BackendResponseByteIterator:
    """Closeable async byte iterator for one backend streaming response.

    This wrapper owns the response stream context returned by the shared
    httpx.AsyncClient. Unlike a bare async generator, its ``aclose()`` closes
    the backend response even before iteration starts, which lets fail-closed
    callers abandon a just-opened backend stream immediately without waiting for
    the first token/chunk.
    """

    def __init__(self, response: httpx.Response, stream_context: Any) -> None:
        self._response = response
        self._stream_context = stream_context
        self._aiter: AsyncIterator[bytes] | None = None
        self._closed = False

    def __aiter__(self) -> "_BackendResponseByteIterator":
        return self

    async def __anext__(self) -> bytes:
        if self._closed:
            raise StopAsyncIteration
        if self._aiter is None:
            self._aiter = self._response.aiter_bytes().__aiter__()
        try:
            while True:
                chunk = await self._aiter.__anext__()
                if chunk:
                    return chunk
        except StopAsyncIteration:
            await self.aclose()
            raise
        except BaseException:
            await self.aclose()
            raise

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._stream_context.__aexit__(None, None, None)


def _backend_url(route: ResolvedRoute, path: str) -> str:
    base_url = str(route.backend.base_url).rstrip("/")
    return f"{base_url}{path}"


def _headers(route: ResolvedRoute) -> dict[str, str]:
    headers = {"content-type": "application/json"}
    if route.backend.api_key:
        headers["authorization"] = f"Bearer {route.backend.api_key}"
    return headers


def _clear_backend_cookies(client: httpx.AsyncClient) -> None:
    """Prevent backend Set-Cookie state from crossing frontend requests.

    The shared AsyncClient is used only for connection pooling. Backend cookies
    are request state and must not persist across users, routes, or API keys.
    Clearing immediately before and after each backend exchange preserves
    keep-alive connections while restoring the previous per-request-client
    behavior of discarding backend cookie state.
    """

    client.cookies.clear()


def build_backend_payload(payload: Mapping[str, Any], route: ResolvedRoute) -> dict[str, Any]:
    backend_payload = (
        dict(payload)
        if route.mode_applied == "pass_through"
        else strip_relaylm_control(payload)
    )
    backend_payload["model"] = route.backend_model
    return backend_payload


def _decode_response_body(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "application/json")
    if "application/json" not in content_type:
        return response.text

    try:
        return response.json()
    except json.JSONDecodeError:
        return response.text


def _ensure_backend_forward_allowed(
    route: ResolvedRoute,
    payload: Mapping[str, Any],
) -> None:
    pipeline_context = get_active_pipeline_context()
    result = (
        pipeline_context.client_history_exclusion_apply_result
        if pipeline_context is not None
        else None
    )
    if client_history_exclusion_apply_blocks_backend(
        route,
        result,
        forwarded_payload=payload,
    ):
        raise BackendRequestError(
            client_history_exclusion_apply_failure_reason(result)
        )


async def forward_chat_completion_json(
    payload: Mapping[str, Any],
    route: ResolvedRoute,
    client: httpx.AsyncClient,
) -> tuple[int, Any, dict[str, str]]:
    """Forward one non-stream chat completion request through ``client``.

    ``client`` is a shared ``httpx.AsyncClient`` owned by the app (see
    ``relaylm.app``'s lifespan) and reused across requests for connection
    pooling/keep-alive. This function never creates or closes a client of
    its own. The per-route backend timeout is applied per request (instead
    of on the client) so the shared client stays timeout-neutral and safe
    to reuse across routes with different ``timeout_seconds``.
    """
    _ensure_backend_forward_allowed(route, payload)
    timeout = httpx.Timeout(route.backend.timeout_seconds)
    _clear_backend_cookies(client)
    try:
        response = await client.post(
            _backend_url(route, OPENAI_CHAT_COMPLETIONS_PATH),
            headers=_headers(route),
            json=build_backend_payload(payload, route),
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        _clear_backend_cookies(client)
        raise BackendRequestError(str(exc)) from exc

    _clear_backend_cookies(client)
    content_type = response.headers.get("content-type", "application/json")
    body = _decode_response_body(response)
    if route.relayctx_unpack_enabled:
        unpack_runtime_result = apply_relayctx_unpack_runtime(
            body,
            status_code=response.status_code,
            apply_enabled=route.relayctx_unpack_apply_enabled,
            dry_run_only=route.relayctx_unpack_dry_run_only,
            max_update_chars=route.relayctx_unpack_max_update_chars,
        )
        body = unpack_runtime_result.response_body
        pipeline_context = get_active_pipeline_context()
        if pipeline_context is not None:
            pipeline_context.record_node_result(unpack_runtime_result.node_result)
            pipeline_context.set_ctx_working_update_candidate(
                unpack_runtime_result.ctx_working_update_candidate
            )
    return response.status_code, body, {"content-type": content_type}


async def open_chat_completion_stream(
    payload: Mapping[str, Any],
    route: ResolvedRoute,
    client: httpx.AsyncClient,
) -> tuple[int, str, AsyncIterator[bytes]]:
    """Open a backend streaming response and return status before proxying bytes.

    This intentionally does not call ``raise_for_status``. Backend 4xx/5xx
    responses should keep their status code and body instead of surfacing as a
    RelayLM generator exception.

    ``client`` is a shared ``httpx.AsyncClient`` owned by the app (see
    ``relaylm.app``'s lifespan). Only the backend response/stream opened here
    is closed by the returned iterator's ``aclose()``/iteration teardown; the
    shared client itself is never closed here since it outlives any single
    request.
    """

    _ensure_backend_forward_allowed(route, payload)
    timeout = httpx.Timeout(route.backend.timeout_seconds)
    _clear_backend_cookies(client)
    stream_context = client.stream(
        "POST",
        _backend_url(route, OPENAI_CHAT_COMPLETIONS_PATH),
        headers=_headers(route),
        json=build_backend_payload(payload, route),
        timeout=timeout,
    )
    try:
        response = await stream_context.__aenter__()
    except httpx.HTTPError as exc:
        # stream_context.__aenter__() failing means the `stream()`
        # asynccontextmanager generator raised before its `yield`, so
        # __aexit__ must not (and cannot) be called -- there is nothing to
        # tear down beyond propagating the error. The shared client is not
        # ours to close either way.
        _clear_backend_cookies(client)
        raise BackendRequestError(str(exc)) from exc

    _clear_backend_cookies(client)
    content_type = response.headers.get("content-type", "text/event-stream")
    body_iter: AsyncIterator[bytes] = _BackendResponseByteIterator(response, stream_context)
    pipeline_context = get_active_pipeline_context()
    if route.relayctx_stream_unpack_dry_run_enabled:
        body_iter = wrap_stream_with_relayctx_suppression(
            body_iter,
            enabled=True,
            dry_run_only=route.relayctx_stream_unpack_dry_run_only,
            max_buffer_chars=route.relayctx_stream_unpack_max_buffer_chars,
            pipeline_context=pipeline_context,
        )
    if route.relayctx_tts_adapter_handoff_runtime_enabled:
        body_iter = wrap_stream_with_tts_adapter_handoff(
            body_iter,
            enabled=True,
            dry_run_only=route.relayctx_tts_adapter_handoff_runtime_dry_run_only,
            b2_safe_visible_output_available=(
                route.relayctx_stream_unpack_dry_run_enabled
                and not route.relayctx_stream_unpack_dry_run_only
            ),
            max_segment_chars=route.relayctx_tts_adapter_handoff_max_segment_chars,
            min_segment_chars=route.relayctx_tts_adapter_handoff_min_segment_chars,
            pipeline_context=pipeline_context,
        )

    return response.status_code, content_type, body_iter
