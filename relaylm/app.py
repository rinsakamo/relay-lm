"""FastAPI entrypoint for RelayLM MVP-0."""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import os
from pathlib import Path
import time
import uuid
from collections.abc import Mapping
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from relaylm.adapter import (
    BackendRequestError,
    forward_chat_completion_json,
    open_chat_completion_stream,
)
from relaylm.app_request_validation import (
    _validate_and_resolve_managed_chat_request,
    openai_error,
)
from relaylm.app_response_finalization import (
    close_stream_iterator,
    durable_finalization_apply_mode,
    durable_finalization_gate_relevant,
    durable_finalization_gate_valid,
    durable_finalization_server_error,
)
from relaylm.config import RelayLMConfig, load_config
from relaylm.relaymem_slp_durable_finalization_publication import (
    RelayMEMSLPDurableFinalizationPreparedTurnHolder,
    admit_relaymem_slp_durable_finalization_nonstream,
    start_relaymem_slp_durable_finalization_stream,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_runtime_finalization import (
    RelayMEMSLPFinalizedVisibleTextCapture,
    run_relaymem_slp_runtime_enqueue_after_response,
    wrap_stream_with_relaymem_slp_finalized_turn_capture,
)
from relaylm.diagnostics import (
    RequestDiagnostics,
    build_compile_decision_dry_run,
    build_relayctx_short_term_block_assembly_dry_run,
    build_relayctx_short_term_extraction_dry_run,
    build_relayctx_short_term_runtime_injection_apply_result,
    build_relayctx_short_term_runtime_injection_preflight,
    build_relayctx_short_term_source_diagnostics,
    build_relaysoul_runtime_feedback_summary,
)
from relaylm.diagnostics_builder import (
    build_base_request_diagnostics,
    compiled_request_diagnostics_kwargs,
    memory_adapter_shadow_diagnostics_kwargs,
    relayctx_short_term_diagnostics_kwargs,
    relayint_runtime_diagnostics_kwargs,
    relayrun_diagnostics_kwargs,
    request_scope_diagnostics_kwargs,
    runtime_artifact_diagnostics_kwargs,
    token_policy_diagnostics_kwargs,
)
from relaylm.memory_adapter import (
    build_memory_adapter_shadow_delta,
    build_memory_adapter_conflict_diagnostics,
    build_memory_adapter_readiness_check,
    build_memory_adapter_shadow_dry_run_with_scope,
)
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.relayint import (
    build_relayint_fast_path_dry_run,
    build_relayint_quick_clarification_apply_plan,
    build_relayint_quick_clarification_preflight,
    build_relayint_reference_intent_artifact,
    build_relayint_request_compatibility_gate,
)
from relaylm.relayscn import build_relayscn_scene_policy_artifact
from relaylm.relayrel import build_relayrel_relationship_projection
from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact
from relaylm.relaymem_primary_recall import (
    apply_relaymem_primary_recall_scope,
    resolve_relaymem_character_store_root,
)
from relaylm.relayrun import new_run_id
from relaylm.relayrun_runtime_artifact import (
    _ManagedRuntimeArtifactContext,
    _build_relayrun_runtime_artifact,
    _build_relayrun_runtime_artifact_for_context,
    _relayrun_relayscn_node,
)
from relaylm.relaymem_store import build_relaymem_store_diagnostics
from relaylm.relayemo import (
    load_session_assistant_state,
    run_relayemo,
    save_session_assistant_state,
)
from relaylm.relayemo_response_marker import (
    apply_relayemo_marker_to_response as _apply_relayemo_marker_to_response,
    build_relayemo_text_marker_preview as _build_relayemo_text_marker_preview,
)
from relaylm.request_scope import build_scope_resolution_diagnostics, extract_request_scope_identity
from relaylm.routing import ResolvedRoute, list_model_ids
from relaylm.token_budget import estimate_text_tokens
from relaylm.token_budget_truncation import apply_token_budget_message_truncation
from relaylm.token_policy_signal import (
    build_token_policy_decision_artifact,
    build_token_policy_readiness_check,
    build_token_policy_signal,
)
from relaylm.trace_runtime import extract_response_text, trace_runtime_event
from relaylm.pipeline_context import PipelineContext, replace_pipeline_forwarded_payload
from relaylm.relayctx_repack import (
    apply_relayctx_short_term_runtime_injection_phase,
    apply_relaymem_runtime_injection_phase,
    apply_token_budget_truncation_phase,
)


def _start_timing() -> tuple[str, float]:
    """Capture a node's start for LAT-1 RelayRUN timing (measurement only)."""

    return datetime.now(timezone.utc).isoformat(), time.monotonic()


def _finalize_timing(started_at: str, start_monotonic: float) -> dict[str, Any]:
    """Finish a node timing bracket started by ``_start_timing``.

    Wall-clock ISO timestamps are recorded for ``started_at``/``completed_at``;
    ``duration_ms`` is derived from a monotonic clock so it stays accurate even
    if the wall clock is adjusted mid-request.
    """

    return {
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": max(0, round((time.monotonic() - start_monotonic) * 1000)),
    }


def create_app(config_path: str | None = None) -> FastAPI:
    config = load_config(config_path)
    app = FastAPI(title="RelayLM", version="0.1.0")
    app.state.relaylm_config = config
    app.state.relaymem_slp_primary_worker_source_registry = (
        RelayMEMSLPPrimaryWorkerSourceRegistry(
            max_entries=config.relaymem_slp_source_registry_max_entries,
            ttl_seconds=config.relaymem_slp_source_registry_ttl_seconds,
        )
    )

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
        request_received_started_at, request_received_start_monotonic = _start_timing()
        validation = await _validate_and_resolve_managed_chat_request(
            request,
            request_id=request_id,
            config=config,
        )
        if validation.error_response is not None:
            return validation.error_response
        node_timings: dict[str, dict[str, Any] | None] = {
            "request_received": _finalize_timing(
                request_received_started_at, request_received_start_monotonic
            )
        }
        payload = validation.payload
        stream_enabled = validation.stream_enabled
        route = validation.route

        relayrun_run_id = new_run_id()

        compiled_request = compile_chat_payload_if_enabled(
            config=config,
            route=route,
            payload=payload,
        )
        pipeline_context = PipelineContext(
            request_id=request_id,
            run_id=relayrun_run_id,
            original_payload=payload,
            forwarded_payload=dict(compiled_request.payload),
            route=route,
            stream_enabled=stream_enabled,
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
        forwarded_payload = pipeline_context.forwarded_payload
        token_budget_truncation: dict[str, Any] | None = None
        relayrel_started_at, relayrel_start_monotonic = _start_timing()
        relayrel_relationship_projection = build_relayrel_relationship_projection(
            route=route,
            request_scope_identity=request_scope_identity,
        )
        node_timings["relayrel"] = _finalize_timing(relayrel_started_at, relayrel_start_monotonic)
        relayscn_started_at, relayscn_start_monotonic = _start_timing()
        relayscn_scene_policy_artifact = build_relayscn_scene_policy_artifact(
            payload=payload,
        )
        node_timings["relayscn"] = _finalize_timing(relayscn_started_at, relayscn_start_monotonic)
        relayemo_artifact: dict[str, Any] | None = None
        if config.relayemo_enabled:
            relayemo_started_at, relayemo_start_monotonic = _start_timing()
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
            node_timings["relayemo"] = _finalize_timing(
                relayemo_started_at, relayemo_start_monotonic
            )

        relayint_started_at, relayint_start_monotonic = _start_timing()
        relayint_intent_artifact = build_relayint_reference_intent_artifact(
            relayscn_artifact=relayscn_scene_policy_artifact,
            messages=_extract_trace_messages(payload),
            ctx_hints=_extract_ctx_hints(payload),
        )
        node_timings["relayint"] = _finalize_timing(relayint_started_at, relayint_start_monotonic)
        relayint_fast_path_dry_run = build_relayint_fast_path_dry_run(
            messages=_extract_trace_messages(payload),
            ctx_hints=_extract_ctx_hints(payload),
            enabled=config.relayint_fast_path_dry_run_enabled,
            high_confidence_threshold=(
                config.relayint_fast_path_high_confidence_threshold
            ),
            low_confidence_threshold=(
                config.relayint_fast_path_low_confidence_threshold
            ),
        )
        relayint_quick_clarification_preflight = (
            build_relayint_quick_clarification_preflight(
                relayint_fast_path_dry_run=relayint_fast_path_dry_run,
                relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
                enabled=config.relayint_quick_clarification_preflight_enabled,
                dry_run_only=config.relayint_quick_clarification_dry_run_only,
            )
        )
        relayint_quick_clarification_apply_plan = (
            build_relayint_quick_clarification_apply_plan(
                relayint_quick_clarification_preflight=(
                    relayint_quick_clarification_preflight
                ),
                enabled=config.relayint_quick_clarification_apply_enabled,
                dry_run_only=config.relayint_quick_clarification_apply_dry_run_only,
                stream_enabled=stream_enabled,
                response_max_chars=config.relayint_quick_clarification_response_max_chars,
                request_compatibility_gate=build_relayint_request_compatibility_gate(payload),
            )
        )

        relaymem_configured_store_root = config.memory.root_path
        relaymem_scoped_store_root = resolve_relaymem_character_store_root(
            relaymem_configured_store_root,
            route.character_id,
        )

        relaymem_retrieval_started_at, relaymem_retrieval_start_monotonic = _start_timing()
        relaymem_store_diagnostics = build_relaymem_store_diagnostics(
            root_path=relaymem_scoped_store_root,
            store_enabled=config.memory.store_enabled,
            retrieval_dry_run_only=config.memory.retrieval_dry_run_only,
        )
        relaymem_retrieval_artifact = build_relaymem_retrieval_dry_run_artifact(
            relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
            relayint_intent_artifact=relayint_intent_artifact,
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
        if _relaymem_primary_recall_scope_allowed(relaymem_store_diagnostics):
            relaymem_retrieval_artifact = apply_relaymem_primary_recall_scope(
                relaymem_retrieval_artifact,
                scoped_store_root=relaymem_scoped_store_root,
                expected_namespace=route.memory_namespace,
                max_snippet_chars=config.memory.max_snippet_chars,
                max_snippet_candidates=config.memory.max_snippet_candidates,
                snippet_budget=config.memory.snippet_budget,
                chars_per_token=config.memory.chars_per_token,
            )
        node_timings["relaymem_retrieval"] = _finalize_timing(
            relaymem_retrieval_started_at, relaymem_retrieval_start_monotonic
        )
        relaymem_runtime_ctx_started_at, relaymem_runtime_ctx_start_monotonic = _start_timing()
        (
            forwarded_payload,
            runtime_ctx_injection_result,
            runtime_snippet_injection_result,
        ) = apply_relaymem_runtime_injection_phase(
            config=config,
            pipeline_context=pipeline_context,
            relaymem_retrieval_artifact=relaymem_retrieval_artifact,
            compiled_payload=compiled_request.payload,
        )
        node_timings["relaymem_runtime_ctx"] = _finalize_timing(
            relaymem_runtime_ctx_started_at, relaymem_runtime_ctx_start_monotonic
        )
        relaymem_primary_recall_projection = relaymem_retrieval_artifact.get(
            "primary_recall_projection"
        )
        if isinstance(relaymem_primary_recall_projection, dict):
            relaymem_primary_recall_projection["injection_performed"] = (
                runtime_snippet_injection_result.get("applied") is True
                or runtime_ctx_injection_result.get("applied") is True
            )
            relaymem_primary_recall_projection["memory_used"] = (
                relaymem_primary_recall_projection["injection_performed"]
            )
        relaymem_diagnostics_artifact = {
            "artifact_version": "relaymem_retrieval_projection.v0",
            "diagnostics_only": True,
            "content_free": True,
            "primary_recall_projection": deepcopy(
                relaymem_primary_recall_projection
            )
            if isinstance(relaymem_primary_recall_projection, dict)
            else None,
        }
        inbound_messages = _extract_trace_messages(payload)
        relayctx_short_term_source_diagnostics = (
            build_relayctx_short_term_source_diagnostics(
                messages=inbound_messages,
                enabled=config.relayctx_short_term_source_diagnostics_enabled,
                memory_source=compiled_request.memory_source,
                relaymem_retrieval_artifact=relaymem_retrieval_artifact,
            )
        )
        relayctx_short_term_extraction_dry_run = (
            build_relayctx_short_term_extraction_dry_run(
                messages=inbound_messages,
                enabled=config.relayctx_short_term_extraction_dry_run_enabled,
                memory_source=compiled_request.memory_source,
            )
        )
        relayctx_short_term_block_assembly_dry_run = (
            build_relayctx_short_term_block_assembly_dry_run(
                extraction_artifact=relayctx_short_term_extraction_dry_run,
                enabled=config.relayctx_short_term_block_assembly_dry_run_enabled,
            )
        )
        relayctx_short_term_runtime_injection_preflight = (
            build_relayctx_short_term_runtime_injection_preflight(
                assembly_artifact=relayctx_short_term_block_assembly_dry_run,
                enabled=config.relayctx_short_term_runtime_injection_preflight_enabled,
                dry_run_only=config.relayctx_short_term_runtime_injection_dry_run_only,
            )
        )
        relayctx_short_term_injection_started_at, relayctx_short_term_injection_start_monotonic = (
            _start_timing()
        )
        (
            forwarded_payload,
            relayctx_short_term_runtime_injection_apply_result,
        ) = apply_relayctx_short_term_runtime_injection_phase(
            config=config,
            pipeline_context=pipeline_context,
            preflight_artifact=relayctx_short_term_runtime_injection_preflight,
        )
        node_timings["relayctx_short_term_injection"] = _finalize_timing(
            relayctx_short_term_injection_started_at,
            relayctx_short_term_injection_start_monotonic,
        )

        # token_budget_truncation runs last among CTX Repack mutations so it is
        # the final gate on the forwarded payload's estimated token total.
        token_budget_truncation_started_at, token_budget_truncation_start_monotonic = (
            _start_timing()
        )
        forwarded_payload, token_budget_truncation = apply_token_budget_truncation_phase(
            config=config,
            pipeline_context=pipeline_context,
        )
        node_timings["token_budget_truncation"] = _finalize_timing(
            token_budget_truncation_started_at, token_budget_truncation_start_monotonic
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

        # runtime_artifact_context freezes the fields shared by every
        # RelayRUN artifact build below; only backend_forward_status and the
        # stream/backend-progress flags vary across the pending/failed/
        # completed call sites.
        runtime_artifact_context = _ManagedRuntimeArtifactContext(
            config=config,
            request_id=request_id,
            run_id=relayrun_run_id,
            route=route,
            stream_enabled=stream_enabled,
            relayrel_relationship_projection=relayrel_relationship_projection,
            relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
            relayemo_artifact=relayemo_artifact,
            relayint_intent_artifact=relayint_intent_artifact,
            relaymem_retrieval_artifact=relaymem_retrieval_artifact,
            runtime_ctx_injection_result=runtime_ctx_injection_result,
            runtime_snippet_injection_result=runtime_snippet_injection_result,
            relayctx_short_term_runtime_injection_apply_result=(
                relayctx_short_term_runtime_injection_apply_result
            ),
            token_budget_truncation=token_budget_truncation,
            node_timings=node_timings,
        )

        # relayrun_artifact is built after all CTX Repack mutations (relaymem
        # injection, short-term injection, token_budget_truncation) so node
        # statuses reflect the final forwarded payload state.
        relayrun_artifact = _build_relayrun_runtime_artifact_for_context(
            runtime_artifact_context,
            backend_forward_status="pending",
            stream_started=False,
            first_token_sent=False,
        )

        base_diagnostics = build_base_request_diagnostics(
            request_id=request_id,
            route_model=route.route_model,
            backend_model=route.backend_model,
            backend_name=route.backend_name,
            character_id=route.character_id,
            mode_requested=route.mode_requested,
            mode_applied=route.mode_applied,
            stream_enabled=stream_enabled,
            **compiled_request_diagnostics_kwargs(compiled_request),
            **token_policy_diagnostics_kwargs(
                token_policy_signal=token_policy_signal,
                token_policy_decision=token_policy_decision,
                token_policy_readiness=token_policy_readiness,
                token_budget_truncation=token_budget_truncation,
            ),
            **request_scope_diagnostics_kwargs(
                request_scope_identity=request_scope_identity,
                scope_resolution_diagnostics=scope_resolution_diagnostics,
            ),
            **memory_adapter_shadow_diagnostics_kwargs(
                memory_adapter_shadow_dry_run=memory_adapter_shadow_dry_run,
                memory_adapter_shadow_readiness=memory_adapter_shadow_readiness,
                memory_adapter_shadow_conflicts=memory_adapter_shadow_conflicts,
                memory_adapter_shadow_delta=memory_adapter_shadow_delta,
            ),
            **relayint_runtime_diagnostics_kwargs(
                relayint_fast_path_dry_run=relayint_fast_path_dry_run,
                relayint_quick_clarification_preflight=(
                    relayint_quick_clarification_preflight
                ),
                relayint_quick_clarification_apply_plan=(
                    relayint_quick_clarification_apply_plan
                ),
                trace_enabled=config.trace.enabled,
                compile_decision_dry_run=compile_decision_dry_run,
            ),
            **runtime_artifact_diagnostics_kwargs(
                relayrel_relationship_projection=relayrel_relationship_projection,
                relayemo_artifact=relayemo_artifact,
                relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
                relayint_intent_artifact=relayint_intent_artifact,
                relaymem_retrieval_artifact=relaymem_diagnostics_artifact,
                runtime_ctx_injection_result=runtime_ctx_injection_result,
                runtime_snippet_injection_result=runtime_snippet_injection_result,
            ),
            **relayctx_short_term_diagnostics_kwargs(
                relayctx_short_term_source_diagnostics=(
                    relayctx_short_term_source_diagnostics
                ),
                relayctx_short_term_extraction_dry_run=(
                    relayctx_short_term_extraction_dry_run
                ),
                relayctx_short_term_block_assembly_dry_run=(
                    relayctx_short_term_block_assembly_dry_run
                ),
                relayctx_short_term_runtime_injection_preflight=(
                    relayctx_short_term_runtime_injection_preflight
                ),
                relayctx_short_term_runtime_injection_apply_result=(
                    relayctx_short_term_runtime_injection_apply_result
                ),
            ),
            **relayrun_diagnostics_kwargs(
                relayrun_artifact=relayrun_artifact,
            ),
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
            backend_forward_started_at, backend_forward_start_monotonic = _start_timing()
            try:
                status_code, content_type, body_iter = await open_chat_completion_stream(
                    forwarded_payload, route
                )
            except BackendRequestError as exc:
                return _build_backend_request_error_response(
                    config=config,
                    exc=exc,
                    diagnostics=diagnostics,
                    runtime_artifact_context=runtime_artifact_context,
                    forwarded_payload=forwarded_payload,
                    backend_forward_timing=_finalize_timing(
                        backend_forward_started_at, backend_forward_start_monotonic
                    ),
                )
            stream_relayrun_artifact = _build_relayrun_runtime_artifact_for_context(
                runtime_artifact_context,
                backend_forward_status="completed",
                backend_forward_timing=_finalize_timing(
                    backend_forward_started_at, backend_forward_start_monotonic
                ),
                stream_started=True,
                first_token_sent=False,
            )
            stream_diagnostics = replace(
                diagnostics,
                relayrun_artifact=stream_relayrun_artifact,
            )
            stream_background = None
            if route.mode_applied != "pass_through" and (
                config.relaymem_slp_runtime_enqueue_enabled
                or durable_finalization_gate_relevant(config)
            ):
                if not durable_finalization_gate_valid(config):
                    await close_stream_iterator(body_iter)
                    return durable_finalization_server_error()
                stream_capture = RelayMEMSLPFinalizedVisibleTextCapture()
                durable_holder = RelayMEMSLPDurableFinalizationPreparedTurnHolder()
                durable_session, durable_result = (
                    start_relaymem_slp_durable_finalization_stream(
                        config=config,
                        pipeline_context=pipeline_context,
                        status_code=status_code,
                        resolved_session_id=merged_scope.get("session_id"),
                        relayscn_scene_policy_artifact=(
                            relayscn_scene_policy_artifact
                        ),
                        relayemo_artifact=relayemo_artifact,
                        holder=durable_holder,
                    )
                )
                if (
                    durable_finalization_apply_mode(config)
                    and durable_result.status not in {
                        "published", "duplicate_existing"
                    }
                ):
                    await close_stream_iterator(body_iter)
                    return durable_finalization_server_error()
                if config.relaymem_slp_runtime_enqueue_enabled:
                    body_iter = wrap_stream_with_relaymem_slp_finalized_turn_capture(
                        body_iter,
                        capture=stream_capture,
                        durable_session=durable_session,
                    )
                    stream_background = BackgroundTask(
                        run_relaymem_slp_runtime_enqueue_after_response,
                        config=config,
                        diagnostics=stream_diagnostics,
                        pipeline_context=pipeline_context,
                        registry=(
                            app.state.relaymem_slp_primary_worker_source_registry
                        ),
                        status_code=status_code,
                        resolved_session_id=merged_scope.get("session_id"),
                        relayscn_scene_policy_artifact=(
                            relayscn_scene_policy_artifact
                        ),
                        relayemo_artifact=relayemo_artifact,
                        stream_capture=stream_capture,
                        prepared_turn_holder=(
                            durable_holder if durable_session is not None else None
                        ),
                        message_count=len(_extract_trace_messages(forwarded_payload)),
                    )
            trace_runtime_event(
                config=config,
                diagnostics=stream_diagnostics,
                message_count=len(_extract_trace_messages(forwarded_payload)),
                response_present=False,
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
                background=stream_background,
            )

        backend_forward_started_at, backend_forward_start_monotonic = _start_timing()
        try:
            status_code, body, response_headers = await forward_chat_completion_json(
                forwarded_payload, route
            )
        except BackendRequestError as exc:
            return _build_backend_request_error_response(
                config=config,
                exc=exc,
                diagnostics=diagnostics,
                runtime_artifact_context=runtime_artifact_context,
                forwarded_payload=forwarded_payload,
                backend_forward_timing=_finalize_timing(
                    backend_forward_started_at, backend_forward_start_monotonic
                ),
            )
        success_relayrun_artifact = _build_relayrun_runtime_artifact_for_context(
            runtime_artifact_context,
            backend_forward_status="completed",
            backend_forward_timing=_finalize_timing(
                backend_forward_started_at, backend_forward_start_monotonic
            ),
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
            assistant_visible_text = extract_response_text(body)
            response_background = None
            durable_prepared = None
            if route.mode_applied != "pass_through" and (
                config.relaymem_slp_runtime_enqueue_enabled
                or durable_finalization_gate_relevant(config)
            ):
                if not durable_finalization_gate_valid(config):
                    return durable_finalization_server_error()
                if not isinstance(assistant_visible_text, str):
                    if (
                        config.relaymem_slp_durable_finalization_enabled
                        and config.relaymem_slp_durable_finalization_apply_enabled
                        and not config.relaymem_slp_durable_finalization_dry_run_only
                    ):
                        return durable_finalization_server_error()
                else:
                    durable_result = (
                        admit_relaymem_slp_durable_finalization_nonstream(
                            config=config,
                            pipeline_context=pipeline_context,
                            status_code=status_code,
                            resolved_session_id=merged_scope.get("session_id"),
                            relayscn_scene_policy_artifact=(
                                relayscn_scene_policy_artifact
                            ),
                            relayemo_artifact=relayemo_artifact,
                            assistant_visible_text=assistant_visible_text,
                        )
                    )
                    if (
                        durable_finalization_apply_mode(config)
                        and durable_result.status not in {
                            "published", "duplicate_existing"
                        }
                    ):
                        return durable_finalization_server_error()
                    durable_prepared = durable_result.prepared_turn
                if (
                    config.relaymem_slp_runtime_enqueue_enabled
                    and isinstance(assistant_visible_text, str)
                ):
                    response_background = BackgroundTask(
                        run_relaymem_slp_runtime_enqueue_after_response,
                        config=config,
                        diagnostics=success_diagnostics,
                        pipeline_context=pipeline_context,
                        registry=(
                            app.state.relaymem_slp_primary_worker_source_registry
                        ),
                        status_code=status_code,
                        resolved_session_id=merged_scope.get("session_id"),
                        relayscn_scene_policy_artifact=(
                            relayscn_scene_policy_artifact
                        ),
                        relayemo_artifact=relayemo_artifact,
                        assistant_visible_text=assistant_visible_text,
                        prepared_turn=durable_prepared,
                        message_count=len(_extract_trace_messages(forwarded_payload)),
                    )
            trace_runtime_event(
                config=config,
                diagnostics=success_diagnostics,
                message_count=len(_extract_trace_messages(forwarded_payload)),
                response_present=isinstance(extract_response_text(body), str),
                metadata={"event": "backend_response", "status_code": status_code},
            )
            headers.update(response_headers)
            return JSONResponse(
                status_code=status_code,
                content=body,
                headers=headers,
                background=response_background,
            )
        return JSONResponse(status_code=status_code, content={"raw": body}, headers=headers)

    return app


def _build_backend_request_error_response(
    *,
    config: RelayLMConfig,
    exc: BackendRequestError,
    diagnostics: RequestDiagnostics,
    runtime_artifact_context: _ManagedRuntimeArtifactContext,
    forwarded_payload: Mapping[str, Any],
    backend_forward_timing: Mapping[str, Any] | None = None,
) -> JSONResponse:
    """Build the shared 502 response for a failed backend forward attempt.

    Used by both the stream and non-stream forwarding paths, which must
    build an identical failed RelayRUN artifact, trace event, and error body.
    """

    failed_relayrun_artifact = _build_relayrun_runtime_artifact_for_context(
        runtime_artifact_context,
        backend_forward_status="failed",
        backend_forward_blocked_reasons=[exc.__class__.__name__],
        backend_forward_timing=backend_forward_timing,
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
        message_count=len(_extract_trace_messages(forwarded_payload)),
        response_present=False,
        metadata={"event": "backend_error", "error_type": exc.__class__.__name__},
    )
    return openai_error(
        status_code=502,
        message=f"RelayLM could not reach backend: {exc}",
        error_type="backend_connection_error",
        headers=failed_diagnostics.to_headers(),
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


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _estimate_text_tokens(text: str, chars_per_token: int) -> int:
    return estimate_text_tokens(
        text,
        chars_per_token=max(1, int(chars_per_token)),
    ).estimated_tokens


def _relaymem_primary_recall_scope_allowed(
    store_diagnostics: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(store_diagnostics, Mapping):
        return True
    compatibility = store_diagnostics.get("layout_compatibility")
    if (
        store_diagnostics.get("root_present") is True
        and isinstance(compatibility, Mapping)
        and compatibility.get("target_primary_secondary_present") is False
    ):
        return False
    return True


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
