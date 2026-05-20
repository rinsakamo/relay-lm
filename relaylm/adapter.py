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


async def stream_chat_completion(
    payload: Mapping[str, Any],
    route: ResolvedRoute,
) -> AsyncIterator[bytes]:
    timeout = httpx.Timeout(route.backend.timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            _backend_url(route, OPENAI_CHAT_COMPLETIONS_PATH),
            headers=_headers(route),
            json=build_backend_payload(payload, route),
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk
