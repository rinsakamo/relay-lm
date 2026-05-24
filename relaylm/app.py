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
    ResolvedRoute,
    RouteConfigurationError,
    RouteNotFoundError,
    list_model_ids,
    resolve_route,
)
from relaylm.token_budget_truncation import apply_token_budget_message_truncation
from relaylm.token_policy_signal import (
    build_token_policy_decision_artifact,
    build_token_policy_readiness_check,
    build_token_policy_signal,
)
from relaylm.trace_runtime import extract_response_text, trace_runtime_event


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
        effective_shadow_enabled, shadow_source = _resolve_token_policy_shadow_setting(config, route)
        token_policy_signal = build_token_policy_signal(compiled_request.token_memory_dry_run)
        token_policy_decision = build_token_policy_decision_artifact(
            token_policy_signal,
            shadow_enabled=effective_shadow_enabled,
            shadow_source=shadow_source,
        )
        token_policy_readiness = build_token_policy_readiness_check(token_policy_decision)
        forwarded_payload, token_budget_truncation = _maybe_apply_token_budget_truncation(
            config=config,
            payload=compiled_request.payload,
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
            memory_source=compiled_request.memory_source,
            memory_selection_summary=(
                compiled_request.memory_selection_summary.to_log_dict()
                if compiled_request.memory_selection_summary is not None
                else None
            ),
            memory_block_assembly=(
                compiled_request.memory_block_assembly.to_log_dict()
                if compiled_request.memory_block_assembly is not None
                else None
            ),
            token_memory_dry_run=compiled_request.token_memory_dry_run,
            token_policy_signal=token_policy_signal.to_log_dict(),
            token_policy_decision=token_policy_decision.to_log_dict(),
            token_policy_readiness=token_policy_readiness.to_log_dict(),
            token_budget_truncation=token_budget_truncation,
            stable_prefix_hash=compiled_request.stable_prefix_hash,
            stable_prefix_block_ids=compiled_request.stable_prefix_block_ids,
            memory_adapter_dry_run=compiled_request.memory_adapter_dry_run,
            memory_adapter_readiness=compiled_request.memory_adapter_readiness,
            memory_adapter_conflicts=compiled_request.memory_adapter_conflicts,
            trace_enabled=config.trace.enabled,
            profile_compile_dry_run_enabled=compiled_request.plan.enabled,
            profile_compile_fallback_reason=compiled_request.plan.fallback_reason,
        )

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
            trace_runtime_event(
                config=config,
                diagnostics=diagnostics,
                messages=_extract_trace_messages(forwarded_payload),
                response_text=extract_response_text(body),
                metadata={"event": "backend_response", "status_code": status_code},
            )
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


def _resolve_token_policy_shadow_setting(
    config: RelayLMConfig,
    route: ResolvedRoute,
) -> tuple[bool, str]:
    if route.character_id is None:
        return config.memory.token_policy_shadow_enabled, "global"
    character = config.characters.get(route.character_id)
    if character is None:
        return config.memory.token_policy_shadow_enabled, "global"
    if character.token_policy_shadow_enabled is None:
        return config.memory.token_policy_shadow_enabled, "global"
    return character.token_policy_shadow_enabled, "character"


def _maybe_apply_token_budget_truncation(
    *,
    config: RelayLMConfig,
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    forwarded_payload = dict(payload)
    forwarded_messages = _extract_trace_messages(payload)
    result = _build_token_budget_truncation_dry_run(
        config=config,
        forwarded_messages=forwarded_messages,
    )
    if result is None:
        return forwarded_payload, None

    if not config.memory.token_budget_truncation_enabled:
        return forwarded_payload, result

    blocked_reason = result.get("blocked_reason")
    over_after = result.get("over_budget_after") is True
    dropped_message_count = result.get("dropped_message_count")
    truncated_messages = result.get("truncated_messages")
    if (
        blocked_reason
        or over_after
        or not isinstance(truncated_messages, list)
        or not isinstance(dropped_message_count, int)
        or dropped_message_count <= 0
    ):
        result["applied"] = False
        result["apply_mode"] = "runtime_apply"
        return forwarded_payload, result

    original_messages = payload.get("messages")
    if not isinstance(original_messages, list):
        return forwarded_payload, result

    forwarded_payload["messages"] = [m for m in truncated_messages if isinstance(m, dict)]
    result["applied"] = True
    result["apply_mode"] = "runtime_apply"
    return forwarded_payload, result


def _build_token_budget_truncation_dry_run(
    *,
    config: RelayLMConfig,
    forwarded_messages: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if config.memory.token_budget is None:
        return None
    result = apply_token_budget_message_truncation(
        messages=forwarded_messages,
        token_budget=config.memory.token_budget,
        chars_per_token=config.memory.chars_per_token,
        keep_system=True,
        keep_latest_user=True,
    ).to_log_dict()
    result["enforcement_enabled"] = config.memory.token_budget_truncation_enabled
    result["applied"] = False
    result["apply_mode"] = "dry_run"
    return result


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
