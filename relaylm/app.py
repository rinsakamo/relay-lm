"""FastAPI entrypoint for RelayLM MVP-0."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from collections.abc import Mapping
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from relaylm.adapter import (
    BackendRequestError,
    forward_chat_completion_json,
    open_chat_completion_stream,
)
from relaylm.config import RelayLMConfig, load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import (
    RouteConfigurationError,
    RouteNotFoundError,
    list_model_ids,
    resolve_route,
)
from relaylm.trace_runtime import trace_runtime_event


def create_app(config_path: str | None = None) -> FastAPI:
    config = load_config(config_path)
    app = FastAPI(title="RelayLM", version="0.1.0")
    app.state.relaylm_config = config

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/models")
    async def models() -> dict[str, Any]:
        return {
            "object": "list",
            "data": [
                {"id": model_id, "object": "model", "owned_by": "relaylm"}
                for model_id in list_model_ids(config)
            ],
        }

    @app.post("/v1/chat/completions", response_model=None)
    async def chat_completions(request: Request) -> JSONResponse | StreamingResponse:
        request_id = str(uuid.uuid4())
        try:
            payload = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            diagnostics = RequestDiagnostics(
                request_id=request_id,
                trace_enabled=config.trace.enabled,
                fallback_reason="invalid_json",
            )
            return openai_error(
                status_code=400,
                message="Request body must be valid JSON.",
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
            )

        if not isinstance(payload, Mapping):
            diagnostics = RequestDiagnostics(
                request_id=request_id,
                trace_enabled=config.trace.enabled,
                fallback_reason="invalid_json_type",
            )
            return openai_error(
                status_code=400,
                message="Request body must be a JSON object.",
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
            )

        model = payload.get("model")
        if not isinstance(model, str) or not model:
            diagnostics = RequestDiagnostics(
                request_id=request_id,
                trace_enabled=config.trace.enabled,
                fallback_reason="missing_model",
            )
            return openai_error(
                status_code=400,
                message="Request field 'model' is required.",
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
            )

        stream_value = payload.get("stream", False)
        if not isinstance(stream_value, bool):
            diagnostics = RequestDiagnostics(
                request_id=request_id,
                route_model=model,
                trace_enabled=config.trace.enabled,
                fallback_reason="invalid_stream_type",
            )
            return openai_error(
                status_code=400,
                message="Request field 'stream' must be a boolean when provided.",
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
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
            return openai_error(
                status_code=400,
                message=str(exc),
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
            )
        except RouteConfigurationError as exc:
            diagnostics = RequestDiagnostics(
                request_id=request_id,
                route_model=model,
                trace_enabled=config.trace.enabled,
                fallback_reason="route_configuration_error",
            )
            return openai_error(
                status_code=500,
                message=str(exc),
                error_type="server_error",
                headers=diagnostics.to_headers(),
            )

        compiled_request = compile_chat_payload_if_enabled(
            config=config,
            route=route,
            payload=payload,
        )

        diagnostics = RequestDiagnostics(
            request_id=request_id,
            route_model=route.route_model,
            backend_model=route.backend_model,
            backend_name=route.backend_name,
            character_id=route.character_id,
            mode_requested=route.mode_requested,
            mode_applied=route.mode_applied,
            stream_enabled=stream_enabled,
            compiler_used=compiled_request.compiler_used,
            memory_block_used=compiled_request.memory_block_used,
            trace_enabled=config.trace.enabled,
            profile_compile_dry_run_enabled=compiled_request.plan.enabled,
            profile_compile_fallback_reason=compiled_request.plan.fallback_reason,
        )
        forwarded_payload = compiled_request.payload

        if stream_enabled:
            try:
                status_code, content_type, body_iter = await open_chat_completion_stream(
                    forwarded_payload, route
                )
            except BackendRequestError as exc:
                trace_runtime_event(
                    config=config,
                    diagnostics=diagnostics,
                    messages=_extract_trace_messages(forwarded_payload),
                    metadata={"event": "backend_error", "error_type": exc.__class__.__name__},
                )
                return openai_error(
                    status_code=502,
                    message=f"RelayLM could not reach backend: {exc}",
                    error_type="backend_connection_error",
                    headers=diagnostics.to_headers(),
                )
            return StreamingResponse(
                body_iter,
                status_code=status_code,
                media_type=content_type,
                headers=diagnostics.to_headers(),
            )

        try:
            status_code, body, response_headers = await forward_chat_completion_json(
                forwarded_payload, route
            )
        except BackendRequestError as exc:
            trace_runtime_event(
                config=config,
                diagnostics=diagnostics,
                messages=_extract_trace_messages(forwarded_payload),
                metadata={"event": "backend_error", "error_type": exc.__class__.__name__},
            )
            return openai_error(
                status_code=502,
                message=f"RelayLM could not reach backend: {exc}",
                error_type="backend_connection_error",
                headers=diagnostics.to_headers(),
            )
        headers = diagnostics.to_headers()
        if isinstance(body, dict) or isinstance(body, list):
            headers.update(response_headers)
            return JSONResponse(status_code=status_code, content=body, headers=headers)
        return JSONResponse(status_code=status_code, content={"raw": body}, headers=headers)

    return app


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


def _extract_trace_messages(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        return []
    return [message for message in raw_messages if isinstance(message, dict)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RelayLM")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    args = parser.parse_args()

    if args.config:
        os.environ["RELAYLM_CONFIG"] = args.config

    config: RelayLMConfig = load_config(args.config)
    uvicorn.run(
        "relaylm.app:create_app",
        factory=True,
        host=config.listen.host,
        port=config.listen.port,
    )


if __name__ == "__main__":
    main()
