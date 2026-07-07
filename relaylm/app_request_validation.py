"""Managed chat request validation and OpenAI-compatible error responses.

Extracted from `relaylm.app` to keep the app module focused on route
wiring and runtime orchestration. Behavior, status codes, fallback
reason strings, and diagnostics headers are unchanged from the
inline implementation this replaces.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from collections.abc import Mapping
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from relaylm.config import RelayLMConfig
from relaylm.diagnostics import RequestDiagnostics
from relaylm.routing import (
    ResolvedRoute,
    RouteConfigurationError,
    RouteNotFoundError,
    resolve_route,
)


def openai_error(
    *,
    status_code: int,
    message: str,
    error_type: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "param": None,
                "code": None,
            }
        },
        headers=headers,
    )


@dataclass
class _ManagedChatRequestValidationResult:
    """Outcome of validating and route-resolving a managed chat request."""

    error_response: JSONResponse | None
    payload: Mapping[str, Any] | None = None
    model: str | None = None
    stream_enabled: bool = False
    route: ResolvedRoute | None = None


async def _validate_and_resolve_managed_chat_request(
    request: Request,
    *,
    request_id: str,
    config: RelayLMConfig,
) -> _ManagedChatRequestValidationResult:
    """Parse, validate, and route-resolve a managed chat completion request.

    Preserves the exact fallback_reason values, status codes, and header
    shape of each early-return branch from the original inline validation.
    """

    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        diagnostics = RequestDiagnostics(
            request_id=request_id,
            trace_enabled=config.trace.enabled,
            fallback_reason="invalid_json",
        )
        return _ManagedChatRequestValidationResult(
            error_response=openai_error(
                status_code=400,
                message="Request body must be valid JSON.",
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
            )
        )

    if not isinstance(payload, Mapping):
        diagnostics = RequestDiagnostics(
            request_id=request_id,
            trace_enabled=config.trace.enabled,
            fallback_reason="invalid_json_type",
        )
        return _ManagedChatRequestValidationResult(
            error_response=openai_error(
                status_code=400,
                message="Request body must be a JSON object.",
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
            )
        )

    model = payload.get("model")
    if not isinstance(model, str) or not model:
        diagnostics = RequestDiagnostics(
            request_id=request_id,
            trace_enabled=config.trace.enabled,
            fallback_reason="missing_model",
        )
        return _ManagedChatRequestValidationResult(
            error_response=openai_error(
                status_code=400,
                message="Request field 'model' is required.",
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
            )
        )

    stream_value = payload.get("stream", False)
    if not isinstance(stream_value, bool):
        diagnostics = RequestDiagnostics(
            request_id=request_id,
            route_model=model,
            trace_enabled=config.trace.enabled,
            fallback_reason="invalid_stream_type",
        )
        return _ManagedChatRequestValidationResult(
            error_response=openai_error(
                status_code=400,
                message="Request field 'stream' must be a boolean when provided.",
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
            )
        )
    stream_enabled = stream_value

    try:
        route = resolve_route(config, model)
    except RouteNotFoundError as exc:
        diagnostics = RequestDiagnostics(
            request_id=request_id,
            route_model=model,
            trace_enabled=config.trace.enabled,
            fallback_reason="route_not_found",
        )
        return _ManagedChatRequestValidationResult(
            error_response=openai_error(
                status_code=400,
                message=str(exc),
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
            )
        )
    except RouteConfigurationError as exc:
        diagnostics = RequestDiagnostics(
            request_id=request_id,
            route_model=model,
            trace_enabled=config.trace.enabled,
            fallback_reason="route_configuration_error",
        )
        return _ManagedChatRequestValidationResult(
            error_response=openai_error(
                status_code=500,
                message=str(exc),
                error_type="server_error",
                headers=diagnostics.to_headers(),
            )
        )

    return _ManagedChatRequestValidationResult(
        error_response=None,
        payload=payload,
        model=model,
        stream_enabled=stream_enabled,
        route=route,
    )
