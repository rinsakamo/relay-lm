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

from relaylm.adapter import forward_chat_completion_json, open_chat_completion_stream
from relaylm.config import RelayLMConfig, load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.routing import RouteNotFoundError, list_model_ids, resolve_route


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

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> JSONResponse | StreamingResponse:
        request_id = str(uuid.uuid4())
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            diagnostics = RequestDiagnostics(
                request_id=request_id,
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
                fallback_reason="missing_model",
            )
            return openai_error(
                status_code=400,
                message="Request field 'model' is required.",
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
            )

        try:
            route = resolve_route(config, model)
        except RouteNotFoundError as exc:
            diagnostics = RequestDiagnostics(
                request_id=request_id,
                route_model=model,
                fallback_reason="route_not_found",
            )
            return openai_error(
                status_code=400,
                message=str(exc),
                error_type="invalid_request_error",
                headers=diagnostics.to_headers(),
            )

        stream_enabled = bool(payload.get("stream", False))
        diagnostics = RequestDiagnostics(
            request_id=request_id,
            route_model=route.route_model,
            backend_model=route.backend_model,
            backend_name=route.backend_name,
            character_id=route.character_id,
            mode_requested=route.mode_requested,
            mode_applied=route.mode_applied,
            stream_enabled=stream_enabled,
            compiler_used=False,
        )

        if stream_enabled:
            status_code, content_type, body_iter = await open_chat_completion_stream(
                payload, route
            )
            return StreamingResponse(
                body_iter,
                status_code=status_code,
                media_type=content_type,
                headers=diagnostics.to_headers(),
            )

        status_code, body, response_headers = await forward_chat_completion_json(payload, route)
        headers = diagnostics.to_headers()
        headers.update(response_headers)
        if isinstance(body, dict) or isinstance(body, list):
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
