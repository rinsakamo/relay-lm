"""OpenAI-compatible backend adapter for RelayLM MVP-0."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx

from relaylm.routing import ResolvedRoute


OPENAI_CHAT_COMPLETIONS_PATH = "/chat/completions"


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


async def forward_chat_completion_json(
    payload: Mapping[str, Any],
    route: ResolvedRoute,
) -> tuple[int, Any, dict[str, str]]:
    timeout = httpx.Timeout(route.backend.timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            _backend_url(route, OPENAI_CHAT_COMPLETIONS_PATH),
            headers=_headers(route),
            json=build_backend_payload(payload, route),
        )
    content_type = response.headers.get("content-type", "application/json")
    if "application/json" in content_type:
        body: Any = response.json()
    else:
        body = response.text
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

    timeout = httpx.Timeout(route.backend.timeout_seconds)
    client = httpx.AsyncClient(timeout=timeout)
    stream_context = client.stream(
        "POST",
        _backend_url(route, OPENAI_CHAT_COMPLETIONS_PATH),
        headers=_headers(route),
        json=build_backend_payload(payload, route),
    )
    response = await stream_context.__aenter__()
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
