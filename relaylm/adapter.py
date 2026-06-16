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
from relaylm.pipeline_context import get_active_pipeline_context
from relaylm.relayctx_unpack_runtime import apply_relayctx_unpack_runtime
from relaylm.routing import ResolvedRoute


OPENAI_CHAT_COMPLETIONS_PATH = "/chat/completions"


class BackendRequestError(RuntimeError):
    """Raised when RelayLM cannot safely forward to or reach the backend."""


def _backend_url(route: ResolvedRoute, path: str) -> str:
    base_url = str(route.backend.base_url).rstrip("/")
    return f"{base_url}{path}"


def _headers(route: ResolvedRoute) -> dict[str, str]:
    headers = {"content-type": "application/json"}
    if route.backend.api_key:
        headers["authorization"] = f"Bearer {route.backend.api_key}"
    return headers


def build_backend_payload(payload: Mapping[str, Any], route: ResolvedRoute) -> dict[str, Any]:
    backend_payload = dict(payload)
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


def _ensure_backend_forward_allowed(route: ResolvedRoute) -> None:
    pipeline_context = get_active_pipeline_context()
    if pipeline_context is None:
        return
    result = pipeline_context.client_history_exclusion_apply_result
    if client_history_exclusion_apply_blocks_backend(route, result):
        raise BackendRequestError(
            client_history_exclusion_apply_failure_reason(result)
        )


async def forward_chat_completion_json(
    payload: Mapping[str, Any],
    route: ResolvedRoute,
) -> tuple[int, Any, dict[str, str]]:
    _ensure_backend_forward_allowed(route)
    timeout = httpx.Timeout(route.backend.timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                _backend_url(route, OPENAI_CHAT_COMPLETIONS_PATH),
                headers=_headers(route),
                json=build_backend_payload(payload, route),
            )
    except httpx.HTTPError as exc:
        raise BackendRequestError(str(exc)) from exc

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
) -> tuple[int, str, AsyncIterator[bytes]]:
    """Open a backend streaming response and return status before proxying bytes.

    This intentionally does not call ``raise_for_status``. Backend 4xx/5xx
    responses should keep their status code and body instead of surfacing as a
    RelayLM generator exception.
    """

    _ensure_backend_forward_allowed(route)
    timeout = httpx.Timeout(route.backend.timeout_seconds)
    client = httpx.AsyncClient(timeout=timeout)
    stream_context = client.stream(
        "POST",
        _backend_url(route, OPENAI_CHAT_COMPLETIONS_PATH),
        headers=_headers(route),
        json=build_backend_payload(payload, route),
    )
    try:
        response = await stream_context.__aenter__()
    except httpx.HTTPError as exc:
        await client.aclose()
        raise BackendRequestError(str(exc)) from exc

    content_type = response.headers.get("content-type", "text/event-stream")

    async def iter_bytes() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk
        finally:
            await stream_context.__aexit__(None, None, None)
            await client.aclose()

    return response.status_code, content_type, iter_bytes()
