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
from relaylm.relayscn import build_relayscn_scene_policy_artifact
from relaylm.relayref import build_relayref_dry_run_artifact
from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact
from relaylm.relaymem_runtime_ctx import (
    maybe_apply_relaymem_runtime_ctx_injection,
    maybe_apply_relaymem_snippet_runtime_injection,
    skipped_relaymem_runtime_ctx_injection_result,
)
from relaylm.relayrun import (
    build_relayrun_node,
    build_runtime_checkpoint_dry_run_artifact,
    new_run_id,
    write_relayrun_checkpoint_if_enabled,
)
from relaylm.relaymem_store import build_relaymem_store_diagnostics
from relaylm.relayemo import (
    load_session_assistant_state,
    run_relayemo,
    save_session_assistant_state,
)
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

        relayrun_run_id = new_run_id()

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
        forwarded_payload = dict(compiled_request.payload)
        token_budget_truncation: dict[str, Any] | None = None
        relayemo_artifact: dict[str, Any] | None = None
        if config.relayemo_enabled:
            session_key, session_key_source = _resolve_relayemo_session_key(
                route=route,
                payload=payload,
                request=request,
                request_scope_identity=request_scope_identity,
                scope_resolution_diagnostics=scope_resolution_diagnostics,
            )
            previous_assistant_state = None
            previous_state_found = False
            state_updated = True
            fallback_reason: str | None = None
            can_use_session_state = (
                config.relayemo_session_state_enabled and session_key is not None
            )
            if config.relayemo_session_state_enabled and session_key is None:
                state_updated = False
                fallback_reason = "session_key_unavailable"
            if can_use_session_state and session_key is not None:
                previous_assistant_state = load_session_assistant_state(
                    session_key,
                    ttl_seconds=config.relayemo_session_state_ttl_seconds,
                )
                previous_state_found = previous_assistant_state is not None
            relayemo_result = run_relayemo(
                config=config,
                messages=_extract_trace_messages(forwarded_payload),
                previous_assistant_state=previous_assistant_state,
            )
            relayemo_artifact = relayemo_result.artifact
            relayemo_artifact["session_state_enabled"] = config.relayemo_session_state_enabled
            relayemo_artifact["session_key_source"] = session_key_source
            relayemo_artifact["previous_state_found"] = previous_state_found
            relayemo_artifact["state_updated"] = state_updated
            relayemo_artifact["state_persisted"] = False
            relayemo_artifact["state_storage"] = "process_memory"
            if fallback_reason is not None:
                relayemo_artifact["fallback_reason"] = fallback_reason
            if can_use_session_state and session_key is not None:
                save_session_assistant_state(
                    session_key,
                    relayemo_result.assistant_state,
                    max_entries=config.relayemo_session_state_max_entries,
                )

        relayscn_scene_policy_artifact = build_relayscn_scene_policy_artifact(
            payload=payload,
            relayemo_artifact=relayemo_artifact,
        )
        relayref_artifact = build_relayref_dry_run_artifact(
            relayscn_artifact=relayscn_scene_policy_artifact,
            messages=_extract_trace_messages(payload),
            ctx_hints=_extract_ctx_hints(payload),
        )
        relaymem_store_diagnostics = build_relaymem_store_diagnostics(
            root_path=config.memory.root_path,
            store_enabled=config.memory.store_enabled,
            retrieval_dry_run_only=config.memory.retrieval_dry_run_only,
        )
        relaymem_retrieval_artifact = build_relaymem_retrieval_dry_run_artifact(
            relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
            relayref_artifact=relayref_artifact,
            messages=_extract_trace_messages(payload),
            token_budget=_resolve_relaymem_retrieval_token_budget(config),
            store_diagnostics=relaymem_store_diagnostics,
            max_candidates=config.memory.candidate_limit,
            ctx_block_apply_enabled=config.memory.ctx_block_apply_enabled,
            snippet_extraction_enabled=config.memory.snippet_extraction_enabled,
            snippet_dry_run_only=config.memory.snippet_dry_run_only,
            snippet_apply_enabled=config.memory.snippet_apply_enabled,
            snippet_budget=config.memory.snippet_budget,
            max_snippet_chars=config.memory.max_snippet_chars,
            max_snippet_candidates=config.memory.max_snippet_candidates,
        )
        forwarded_payload, runtime_snippet_injection_result = (
            maybe_apply_relaymem_snippet_runtime_injection(
                payload=forwarded_payload,
                relaymem_retrieval_artifact=relaymem_retrieval_artifact,
                ctx_block_apply_enabled=config.memory.ctx_block_apply_enabled,
                retrieval_dry_run_only=config.memory.retrieval_dry_run_only,
                snippet_apply_enabled=config.memory.snippet_apply_enabled,
                snippet_dry_run_only=config.memory.snippet_dry_run_only,
                snippet_runtime_injection_enabled=(
                    config.memory.snippet_runtime_injection_enabled
                ),
                snippet_runtime_dry_run_only=config.memory.snippet_runtime_dry_run_only,
                token_budget_truncation_enabled=config.memory.token_budget_truncation_enabled,
                token_budget=config.memory.token_budget,
                chars_per_token=config.memory.chars_per_token,
            )
        )
        if runtime_snippet_injection_result.get("applied") is True:
            runtime_ctx_injection_result = skipped_relaymem_runtime_ctx_injection_result(
                payload=compiled_request.payload,
                reason="skipped_because_snippet_runtime_injection_applied",
            )
        else:
            forwarded_payload, runtime_ctx_injection_result = (
                maybe_apply_relaymem_runtime_ctx_injection(
                    payload=forwarded_payload,
                    relaymem_retrieval_artifact=relaymem_retrieval_artifact,
                    ctx_block_apply_enabled=config.memory.ctx_block_apply_enabled,
                    retrieval_dry_run_only=config.memory.retrieval_dry_run_only,
                    token_budget_truncation_enabled=(
                        config.memory.token_budget_truncation_enabled
                    ),
                    token_budget=config.memory.token_budget,
                    chars_per_token=config.memory.chars_per_token,
                )
            )
        forwarded_payload, token_budget_truncation = _maybe_apply_token_budget_truncation(
            config=config,
            payload=forwarded_payload,
        )

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

        relayrun_artifact = _build_relayrun_runtime_artifact(
            config=config,
            request_id=request_id,
            run_id=relayrun_run_id,
            route=route,
            stream_enabled=stream_enabled,
            relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
            relayref_artifact=relayref_artifact,
            relaymem_retrieval_artifact=relaymem_retrieval_artifact,
            runtime_ctx_injection_result=runtime_ctx_injection_result,
            runtime_snippet_injection_result=runtime_snippet_injection_result,
            token_budget_truncation=token_budget_truncation,
            backend_forward_status="pending",
            stream_started=False,
            first_token_sent=False,
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
            relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
            relayref_artifact=relayref_artifact,
            relaymem_retrieval_artifact=relaymem_retrieval_artifact,
            runtime_ctx_injection_result=runtime_ctx_injection_result,
            runtime_snippet_injection_result=runtime_snippet_injection_result,
            relayrun_artifact=relayrun_artifact,
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
                failed_relayrun_artifact = _build_relayrun_runtime_artifact(
                    config=config,
                    request_id=request_id,
                    run_id=relayrun_run_id,
                    route=route,
                    stream_enabled=stream_enabled,
                    relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
                    relayref_artifact=relayref_artifact,
                    relaymem_retrieval_artifact=relaymem_retrieval_artifact,
                    runtime_ctx_injection_result=runtime_ctx_injection_result,
                    runtime_snippet_injection_result=runtime_snippet_injection_result,
                    token_budget_truncation=token_budget_truncation,
                    backend_forward_status="failed",
                    backend_forward_blocked_reasons=[exc.__class__.__name__],
                    stream_started=False,
                    first_token_sent=False,
                )
                failed_diagnostics = replace(
                    diagnostics,
                    relayrun_artifact=failed_relayrun_artifact,
                )
                trace_runtime_event(
                    config=config,
                    diagnostics=failed_diagnostics,
                    messages=_extract_trace_messages(forwarded_payload),
                    metadata={"event": "backend_error", "error_type": exc.__class__.__name__},
                )
                return openai_error(
                    status_code=502,
                    message=f"RelayLM could not reach backend: {exc}",
                    error_type="backend_connection_error",
                    headers=failed_diagnostics.to_headers(),
                )
            stream_relayrun_artifact = _build_relayrun_runtime_artifact(
                config=config,
                request_id=request_id,
                run_id=relayrun_run_id,
                route=route,
                stream_enabled=stream_enabled,
                relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
                relayref_artifact=relayref_artifact,
                relaymem_retrieval_artifact=relaymem_retrieval_artifact,
                runtime_ctx_injection_result=runtime_ctx_injection_result,
                runtime_snippet_injection_result=runtime_snippet_injection_result,
                token_budget_truncation=token_budget_truncation,
                backend_forward_status="completed",
                stream_started=True,
                first_token_sent=False,
            )
            stream_diagnostics = replace(
                diagnostics,
                relayrun_artifact=stream_relayrun_artifact,
            )
            trace_runtime_event(
                config=config,
                diagnostics=stream_diagnostics,
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
                headers=stream_diagnostics.to_headers(),
            )

        try:
            status_code, body, response_headers = await forward_chat_completion_json(
                forwarded_payload, route
            )
        except BackendRequestError as exc:
            failed_relayrun_artifact = _build_relayrun_runtime_artifact(
                config=config,
                request_id=request_id,
                run_id=relayrun_run_id,
                route=route,
                stream_enabled=stream_enabled,
                relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
                relayref_artifact=relayref_artifact,
                relaymem_retrieval_artifact=relaymem_retrieval_artifact,
                runtime_ctx_injection_result=runtime_ctx_injection_result,
                runtime_snippet_injection_result=runtime_snippet_injection_result,
                token_budget_truncation=token_budget_truncation,
                backend_forward_status="failed",
                backend_forward_blocked_reasons=[exc.__class__.__name__],
                stream_started=False,
                first_token_sent=False,
            )
            failed_diagnostics = replace(
                diagnostics,
                relayrun_artifact=failed_relayrun_artifact,
            )
            trace_runtime_event(
                config=config,
                diagnostics=failed_diagnostics,
                messages=_extract_trace_messages(forwarded_payload),
                metadata={"event": "backend_error", "error_type": exc.__class__.__name__},
            )
            return openai_error(
                status_code=502,
                message=f"RelayLM could not reach backend: {exc}",
                error_type="backend_connection_error",
                headers=failed_diagnostics.to_headers(),
            )
        success_relayrun_artifact = _build_relayrun_runtime_artifact(
            config=config,
            request_id=request_id,
            run_id=relayrun_run_id,
            route=route,
            stream_enabled=stream_enabled,
            relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
            relayref_artifact=relayref_artifact,
            relaymem_retrieval_artifact=relaymem_retrieval_artifact,
            runtime_ctx_injection_result=runtime_ctx_injection_result,
            runtime_snippet_injection_result=runtime_snippet_injection_result,
            token_budget_truncation=token_budget_truncation,
            backend_forward_status="completed",
            stream_started=False,
            first_token_sent=False,
        )
        success_diagnostics = replace(
            diagnostics,
            relayrun_artifact=success_relayrun_artifact,
        )
        headers = success_diagnostics.to_headers()
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
                diagnostics=success_diagnostics,
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


def _resolve_relayemo_session_key(
    *,
    route: ResolvedRoute,
    payload: Mapping[str, Any],
    request: Request,
    request_scope_identity: Any,
    scope_resolution_diagnostics: Any,
) -> tuple[str | None, str]:
    merged_scope = getattr(scope_resolution_diagnostics, "merged_scope", {})
    resolved_session_id = merged_scope.get("session_id") if isinstance(merged_scope, dict) else None
    if isinstance(resolved_session_id, str) and resolved_session_id:
        return (
            f"{resolved_session_id}:{route.route_model}:{route.character_id or 'none'}",
            "resolved_session_id",
        )
    session_id = getattr(request_scope_identity, "session_id", None)
    if isinstance(session_id, str) and session_id:
        return f"{session_id}:{route.route_model}:{route.character_id or 'none'}", "request_session_id"
    route_session_id = getattr(route, "session_id", None)
    if isinstance(route_session_id, str) and route_session_id:
        return (
            f"{route_session_id}:{route.route_model}:{route.character_id or 'none'}",
            "route_session_id",
        )
    return None, "unavailable"


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
    affect_mode = str(affect.get("mode", "unknown"))
    assistant_state = relayemo_artifact.get("assistant_emotion_state", {})
    intensity = float(assistant_state.get("intensity", 0.0))
    confidence = float(affect.get("confidence", 0.0))
    marker_map = {
        "light_positive_estimate": "✨",
        "playful_positive_estimate": "♪",
        "warm_positive_estimate": "☺️",
    }
    base_marker = marker_map.get(affect_mode, "")
    if scene_type in {"review_work", "formal_document", "medical_or_safety"}:
        return {"gate_open": False, "marker": "", "marker_count": 0, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": "scene_suppressed"}
    if confidence < 0.4:
        return {"gate_open": False, "marker": "", "marker_count": 0, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": "low_confidence"}
    if scene_type in {"implementation_work"}:
        preview_marker = base_marker or "✨"
        return {"gate_open": False, "marker": preview_marker, "marker_count": 1 if preview_marker else 0, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": "preview_only_scene"}
    gate_open = intensity >= config.relayemo_marker_open_threshold
    if not base_marker:
        gate_open = False
    marker_count = min(config.relayemo_max_markers, max(1, int(1 + intensity * 2))) if gate_open else 0
    return {"gate_open": gate_open, "marker": base_marker * marker_count if base_marker else "", "marker_count": marker_count, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": None if gate_open else "below_open_threshold_or_no_marker"}


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


def _resolve_relaymem_retrieval_token_budget(config: RelayLMConfig) -> int | None:
    if config.memory.token_budget is not None:
        return config.memory.token_budget
    if (
        isinstance(config.memory.token_budget_hint, int)
        and config.memory.token_budget_hint > 0
    ):
        return config.memory.token_budget_hint
    return None


def _extract_ctx_hints(payload: Mapping[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        return {}
    ctx = metadata.get("ctx")
    hints: dict[str, Any] = dict(ctx) if isinstance(ctx, Mapping) else {}
    if "ctx_handoff_guess" in metadata and "ctx_handoff_guess" not in hints:
        hints["ctx_handoff_guess"] = metadata.get("ctx_handoff_guess")
    return hints


def _build_relayrun_runtime_artifact(
    *,
    config: RelayLMConfig,
    request_id: str,
    run_id: str,
    route: ResolvedRoute,
    stream_enabled: bool,
    relayscn_scene_policy_artifact: Mapping[str, Any] | None,
    relayref_artifact: Mapping[str, Any] | None,
    relaymem_retrieval_artifact: Mapping[str, Any] | None,
    runtime_ctx_injection_result: Mapping[str, Any] | None,
    runtime_snippet_injection_result: Mapping[str, Any] | None,
    token_budget_truncation: Mapping[str, Any] | None,
    backend_forward_status: str,
    backend_forward_blocked_reasons: list[str] | None = None,
    stream_started: bool | None = None,
    first_token_sent: bool | None = None,
) -> dict[str, Any]:
    node_statuses = [
        build_relayrun_node(node_name="request_received", node_status="completed"),
        _relayrun_relayscn_node(relayscn_scene_policy_artifact),
        _relayrun_relayref_node(relayref_artifact),
        _relayrun_relaymem_retrieval_node(relaymem_retrieval_artifact),
        _relayrun_relaymem_runtime_ctx_node(
            runtime_ctx_injection_result=runtime_ctx_injection_result,
            runtime_snippet_injection_result=runtime_snippet_injection_result,
        ),
        _relayrun_token_budget_truncation_node(token_budget_truncation),
        build_relayrun_node(
            node_name="backend_forward",
            node_status=_relayrun_backend_forward_status(backend_forward_status),
            blocked_reasons=backend_forward_blocked_reasons,
            fallback_reason=(
                "backend_request_error"
                if backend_forward_status == "failed"
                else None
            ),
        ),
    ]
    blocked_reasons = _relayrun_collect_blocked_reasons(node_statuses)
    artifact = build_runtime_checkpoint_dry_run_artifact(
        request_id=request_id,
        run_id=run_id,
        turn_id=None,
        route_model=route.route_model,
        backend_name=route.backend_name,
        character_id=route.character_id,
        stream_enabled=stream_enabled,
        node_statuses=node_statuses,
        blocked_reasons=blocked_reasons,
        stream_started=stream_started,
        first_token_sent=first_token_sent,
        resume_allowed=False,
        resume_mode="none",
        checkpoint_persisted=False,
        checkpoint_target_root=config.relayrun_checkpoint_root,
        recovery_transition_created=False,
        applied=False,
    )
    if backend_forward_status == "pending":
        return artifact
    return write_relayrun_checkpoint_if_enabled(
        artifact,
        write_enabled=config.relayrun_checkpoint_write_enabled,
        dry_run_only=config.relayrun_checkpoint_dry_run_only,
    )


def _relayrun_relayscn_node(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return build_relayrun_node(
            node_name="relayscn",
            node_status="failed",
            blocked_reasons=["relayscn_scene_policy_artifact_missing"],
            fallback_reason="relayscn_artifact_missing",
        )
    scene_state = artifact.get("scene_state")
    scene_type = scene_state.get("scene_type") if isinstance(scene_state, Mapping) else None
    scene_policy = artifact.get("scene_policy")
    blocked_reasons = _string_list(artifact.get("persistence_block_reasons"))
    blocked_reasons.extend(
        reason
        for reason in _string_list(
            scene_policy.get("persistence_block_reasons")
            if isinstance(scene_policy, Mapping)
            else None
        )
        if reason not in blocked_reasons
    )
    persistence_block = artifact.get("persistence_block") is True
    if isinstance(scene_policy, Mapping) and scene_policy.get("persistence_block") is True:
        persistence_block = True
    if persistence_block and not blocked_reasons:
        if isinstance(scene_type, str) and scene_type:
            blocked_reasons = [f"scene_policy:{scene_type}"]
        else:
            blocked_reasons = ["scene_policy:blocked"]
    status = "blocked" if blocked_reasons else "completed"
    return build_relayrun_node(
        node_name="relayscn",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason="scene_policy_fail_closed" if blocked_reasons else None,
    )


def _relayrun_relayref_node(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return build_relayrun_node(
            node_name="relayref",
            node_status="failed",
            blocked_reasons=["relayref_artifact_missing"],
            fallback_reason="relayref_artifact_missing",
        )
    blocked_reasons = []
    if artifact.get("unresolved_reference_detected") is True:
        blocked_reasons.append("unresolved_reference_detected")
    blocked_reasons.extend(
        reason
        for reason in _string_list(artifact.get("mode_reasons"))
        if reason not in blocked_reasons
    )
    status = "blocked" if blocked_reasons else "completed"
    return build_relayrun_node(
        node_name="relayref",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason=(
            str(artifact.get("mode"))
            if blocked_reasons and isinstance(artifact.get("mode"), str)
            else None
        ),
    )


def _relayrun_relaymem_retrieval_node(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return build_relayrun_node(
            node_name="relaymem_retrieval",
            node_status="failed",
            blocked_reasons=["relaymem_retrieval_artifact_missing"],
            fallback_reason="relaymem_retrieval_artifact_missing",
        )
    blocked_reasons = []
    apply_decision = artifact.get("apply_decision")
    if isinstance(apply_decision, str) and apply_decision.startswith("blocked_"):
        blocked_reasons.append(f"apply_decision:{apply_decision}")
    fallback_reason = artifact.get("fallback_reason")
    snippet_apply_decision = artifact.get("snippet_apply_decision")
    if (
        isinstance(snippet_apply_decision, str)
        and snippet_apply_decision.startswith("blocked_")
    ):
        blocked_reasons.append(f"snippet_apply_decision:{snippet_apply_decision}")
    status = "blocked" if blocked_reasons else "completed"
    return build_relayrun_node(
        node_name="relaymem_retrieval",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason=fallback_reason if isinstance(fallback_reason, str) else None,
    )


def _relayrun_relaymem_runtime_ctx_node(
    *,
    runtime_ctx_injection_result: Mapping[str, Any] | None,
    runtime_snippet_injection_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if (
        not isinstance(runtime_ctx_injection_result, Mapping)
        or not isinstance(runtime_snippet_injection_result, Mapping)
    ):
        return build_relayrun_node(
            node_name="relaymem_runtime_ctx",
            node_status="failed",
            blocked_reasons=["runtime_ctx_or_snippet_result_missing"],
            fallback_reason="runtime_ctx_result_missing",
        )
    if (
        runtime_ctx_injection_result.get("applied") is True
        or runtime_snippet_injection_result.get("applied") is True
    ):
        return build_relayrun_node(
            node_name="relaymem_runtime_ctx",
            node_status="completed",
        )
    blocked_reasons = _string_list(runtime_snippet_injection_result.get("blocked_reasons"))
    blocked_reasons.extend(
        reason
        for reason in _string_list(runtime_ctx_injection_result.get("blocked_reasons"))
        if reason not in blocked_reasons
    )
    status = "blocked" if blocked_reasons else "skipped"
    return build_relayrun_node(
        node_name="relaymem_runtime_ctx",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason="runtime_ctx_not_applied" if blocked_reasons else None,
    )


def _relayrun_token_budget_truncation_node(
    artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return build_relayrun_node(
            node_name="token_budget_truncation",
            node_status="skipped",
        )
    blocked_reasons = []
    blocked_reason = artifact.get("blocked_reason")
    if isinstance(blocked_reason, str) and blocked_reason:
        blocked_reasons.append(blocked_reason)
    status = "blocked" if blocked_reasons else "completed"
    return build_relayrun_node(
        node_name="token_budget_truncation",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason="token_budget_blocked" if blocked_reasons else None,
    )


def _relayrun_backend_forward_status(status: str) -> str:
    if status in {"completed", "failed", "blocked", "skipped"}:
        return status
    return "pending"


def _relayrun_collect_blocked_reasons(node_statuses: list[dict[str, Any]]) -> list[str]:
    blocked_reasons: list[str] = []
    for node in node_statuses:
        if not isinstance(node, Mapping):
            continue
        node_name = node.get("node_name")
        prefix = f"{node_name}:" if isinstance(node_name, str) and node_name else ""
        for reason in _string_list(node.get("blocked_reasons")):
            value = f"{prefix}{reason}" if prefix else reason
            if value not in blocked_reasons:
                blocked_reasons.append(value)
    return blocked_reasons


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


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
