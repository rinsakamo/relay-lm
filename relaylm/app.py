"""FastAPI entrypoint for RelayLM MVP-0."""

from __future__ import annotations

import argparse
from dataclasses import replace
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
from relaylm.diagnostics import (
    RequestDiagnostics,
    build_compile_decision_dry_run,
    build_relaysoul_runtime_feedback_summary,
)
from relaylm.memory_adapter import (
    build_memory_adapter_shadow_delta,
    build_memory_adapter_conflict_diagnostics,
    build_memory_adapter_readiness_check,
    build_memory_adapter_shadow_dry_run_with_scope,
)
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.relayemo import run_relayemo
from relaylm.request_scope import build_scope_resolution_diagnostics, extract_request_scope_identity
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
        request_scope_identity = extract_request_scope_identity(request.headers, payload)
        scope_resolution_diagnostics = build_scope_resolution_diagnostics(route, request_scope_identity)
        merged_scope = dict(scope_resolution_diagnostics.merged_scope)
        merged_scope["character_id"] = route.character_id
        merged_scope["memory_namespace"] = route.memory_namespace
        merged_scope["cache_namespace"] = route.cache_namespace
        memory_adapter_shadow_dry_run = build_memory_adapter_shadow_dry_run_with_scope(
            base_dry_run=compiled_request.memory_adapter_dry_run,
            merged_scope=merged_scope,
        )
        memory_adapter_shadow_readiness = (
            build_memory_adapter_readiness_check(memory_adapter_shadow_dry_run).to_log_dict()
            if memory_adapter_shadow_dry_run is not None
            else None
        )
        memory_adapter_shadow_conflicts = (
            build_memory_adapter_conflict_diagnostics(memory_adapter_shadow_dry_run).to_log_dict()
            if memory_adapter_shadow_dry_run is not None
            else None
        )
        memory_adapter_shadow_delta = (
            build_memory_adapter_shadow_delta(
                base_dry_run=compiled_request.memory_adapter_dry_run,
                shadow_dry_run=memory_adapter_shadow_dry_run,
                base_readiness=compiled_request.memory_adapter_readiness,
                shadow_readiness=memory_adapter_shadow_readiness,
                base_conflicts=compiled_request.memory_adapter_conflicts,
                shadow_conflicts=memory_adapter_shadow_conflicts,
            ).to_log_dict()
            if memory_adapter_shadow_dry_run is not None
            else None
        )
        forwarded_payload, token_budget_truncation = _maybe_apply_token_budget_truncation(
            config=config,
            payload=compiled_request.payload,
        )
        relayemo_artifact: dict[str, Any] | None = None
        if config.relayemo_enabled:
            relayemo_result = run_relayemo(
                config=config,
                messages=_extract_trace_messages(forwarded_payload),
            )
            relayemo_artifact = relayemo_result.artifact

        compiled_message_count = (
            compiled_request.plan.compiled_message_count
            if compiled_request.plan.enabled
            else None
        )

        apply_compiled_messages = compiled_request.decision.should_apply is True
        if apply_compiled_messages:
            compile_decision_state = "COMPILE_APPLY"
            compile_diagnostics_only = False
            compile_fallback_reason = None
            compile_blocking_reasons: list[str] = []
        else:
            compile_decision_state = "COMPILE_DRY_RUN"
            compile_diagnostics_only = True
            compile_fallback_reason = (
                compiled_request.plan.fallback_reason or compiled_request.decision.reason
            )
            compile_blocking_reasons = []
            if compiled_request.decision.reason:
                compile_blocking_reasons.append(compiled_request.decision.reason)
            if (
                compiled_request.plan.fallback_reason
                and compiled_request.plan.fallback_reason not in compile_blocking_reasons
            ):
                compile_blocking_reasons.append(compiled_request.plan.fallback_reason)

        compile_decision_dry_run = build_compile_decision_dry_run(
            decision_id=f"{request_id}:compile-decision-dry-run",
            plan_id=f"{request_id}:compile-plan",
            result_id=f"{request_id}:compile-result",
            selected_route=route.route_model,
            selected_mode=route.mode_applied,
            backend=route.backend_name,
            character_id=route.character_id,
            compiled_message_count=compiled_message_count,
            fallback_reason=compile_fallback_reason,
            blocking_reasons=compile_blocking_reasons,
            omitted_block_ids=[],
            token_budget_status=None,
            decision_state=compile_decision_state,
            apply_compiled_messages=apply_compiled_messages,
            diagnostics_only=compile_diagnostics_only,
        )

        base_diagnostics = RequestDiagnostics(
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
            context_block_summary=compiled_request.context_block_summary,
            persona_source_budget_diagnostics=compiled_request.persona_source_budget_diagnostics,
            request_scope_identity=request_scope_identity.to_log_dict(),
            scope_resolution_diagnostics=scope_resolution_diagnostics.to_log_dict(),
            memory_adapter_shadow_dry_run=memory_adapter_shadow_dry_run,
            memory_adapter_shadow_readiness=memory_adapter_shadow_readiness,
            memory_adapter_shadow_conflicts=memory_adapter_shadow_conflicts,
            memory_adapter_shadow_delta=memory_adapter_shadow_delta,
            trace_enabled=config.trace.enabled,
            profile_compile_dry_run_enabled=compiled_request.plan.enabled,
            profile_compile_fallback_reason=compiled_request.plan.fallback_reason,
            compile_decision_dry_run=compile_decision_dry_run,
            relayemo_artifact=relayemo_artifact,
        )
        feedback_summary = (
            build_relaysoul_runtime_feedback_summary(base_diagnostics)
            if base_diagnostics.compiler_used
            else None
        )
        diagnostics = replace(
            base_diagnostics,
            relaysoul_runtime_feedback_summary=feedback_summary,
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
            trace_runtime_event(
                config=config,
                diagnostics=diagnostics,
                messages=_extract_trace_messages(forwarded_payload),
                metadata={
                    "event": "backend_stream_response",
                    "status_code": status_code,
                    "content_type": content_type,
                },
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
        if (
            isinstance(body, dict)
            and relayemo_artifact is not None
            and config.relayemo_text_marker_enabled
        ):
            marker_preview = _build_relayemo_text_marker_preview(config, relayemo_artifact)
            relayemo_artifact["text_marker_preview"] = marker_preview
            apply_mode = config.relayemo_text_marker_apply_mode
            if apply_mode == "apply":
                body = _apply_relayemo_marker_to_response(body, marker_preview)
                relayemo_artifact["text_marker_apply"]["applied_to_text"] = bool(
                    marker_preview.get("gate_open")
                )
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


def _build_relayemo_text_marker_preview(
    config: RelayLMConfig,
    relayemo_artifact: dict[str, Any],
) -> dict[str, Any]:
    scene_type = relayemo_artifact.get("scene_state", {}).get("scene_type", "unknown")
    affect = relayemo_artifact.get("user_affect_estimate", {})
    assistant_state = relayemo_artifact.get("assistant_emotion_state", {})
    intensity = float(assistant_state.get("intensity", 0.0))
    confidence = float(affect.get("confidence", 0.0))
    if scene_type in {"review_work", "formal_document", "medical_or_safety"}:
        return {"gate_open": False, "marker": "", "marker_count": 0, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": "scene_suppressed"}
    if confidence < 0.4:
        return {"gate_open": False, "marker": "", "marker_count": 0, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": "low_confidence"}
    if scene_type in {"implementation_work"}:
        return {"gate_open": False, "marker": "✨", "marker_count": 1, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": "preview_only_scene"}
    gate_open = intensity >= config.relayemo_marker_open_threshold
    marker_count = min(config.relayemo_max_markers, max(1, int(1 + intensity * 2))) if gate_open else 0
    return {"gate_open": gate_open, "marker": "✨" * marker_count, "marker_count": marker_count, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": None if gate_open else "below_open_threshold"}


def _apply_relayemo_marker_to_response(body: dict[str, Any], preview: dict[str, Any]) -> dict[str, Any]:
    if not preview.get("gate_open"):
        return body
    marker = preview.get("marker") or ""
    if not marker:
        return body
    choices = body.get("choices")
    if not isinstance(choices, list):
        return body
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, str) or not content:
            continue
        if content.endswith(("。", "！", "!", ".")):
            message["content"] = content[:-1] + marker
        elif content.endswith(("？", "?")):
            message["content"] = content + marker
        else:
            message["content"] = content + marker
    return body


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
