"""Managed `/v1/chat/completions` runtime orchestration for RelayLM.

Owns the request validation call, compile/runtime pipeline orchestration,
diagnostics construction, RelayREL/RelaySCN/RelayEMO/RelayINT/RelayMEM/
RelayCTX/token-budget runtime steps, backend forwarding, stream/non-stream
response construction, tracing, and response finalization/background
enqueue integration for the managed chat completion route. `relaylm/app.py`
stays a thin FastAPI entrypoint that delegates to
``handle_managed_chat_completion``.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
import uuid
from collections.abc import Mapping
from typing import Any

from fastapi import Request
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
    get_shared_http_client,
)
from relaylm.config import RelayLMConfig
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
from relaylm.request_compiler import (
    CompiledRequest,
    compile_chat_payload_if_enabled,
    consume_compiled_context_blocks_runtime_private,
    restore_compiled_context_blocks_runtime_private,
)
from relaylm.relayint import (
    build_relayint_fast_path_dry_run,
    build_relayint_quick_clarification_apply_plan,
    build_relayint_quick_clarification_preflight,
    build_relayint_request_compatibility_gate,
    run_relayint_stage,
)
from relaylm.relayscn import run_relayscn_stage
from relaylm.relayrel import run_relayrel_stage
from relaylm.relaymem_retrieval import run_relaymem_retrieval_stage
from relaylm.relayrun import new_run_id
from relaylm.relayrun_runtime_artifact import (
    _ManagedRuntimeArtifactContext,
    _build_relayrun_runtime_artifact_for_context,
)
from relaylm.relayrun_stream_timing import (
    emit_relayrun_stream_timing_trace,
    wrap_stream_with_relayrun_stream_timing,
)
from relaylm.relayemo import run_relayemo_stage
from relaylm.relayemo_response_marker import (
    apply_relayemo_marker_to_response as _apply_relayemo_marker_to_response,
    build_relayemo_text_marker_preview as _build_relayemo_text_marker_preview,
)
from relaylm.request_scope import build_scope_resolution_diagnostics, extract_request_scope_identity
from relaylm.routing import ResolvedRoute
from relaylm.token_budget import estimate_text_tokens
from relaylm.token_budget_truncation import (
    apply_token_budget_message_truncation,
    run_token_budget_truncation_stage,
)
from relaylm.token_policy_signal import (
    build_token_policy_decision_artifact,
    build_token_policy_readiness_check,
    build_token_policy_signal,
)
from relaylm.trace_runtime import extract_response_text, trace_runtime_event
from relaylm.pipeline_context import PipelineContext, replace_pipeline_forwarded_payload
from relaylm.pipeline_stage import _finalize_timing, _start_timing, run_stage
from relaylm.relayctx_repack import (
    run_relayctx_short_term_injection_stage,
    run_relaymem_runtime_ctx_stage,
)


def _compile_chat_payload_and_capture_context_blocks(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
    payload: Mapping[str, Any],
) -> tuple[CompiledRequest, tuple[Any, ...] | None]:
    """Run the compile stage on a worker thread and capture its ContextVar handoff.

    Executed inside ``asyncio.to_thread``. ``compile_chat_payload_if_enabled``
    reads character workspace files (persona/soul/output policy, memory seed)
    and is otherwise called unmodified with plain arguments. It also stashes
    typed pre-render compiler blocks in a request-local ``ContextVar`` for
    ``PipelineContext`` to pick up; that ``.set()`` would not survive the
    worker thread's copied context, so it is consumed here and returned
    alongside the compiled request for the async caller to replay (see
    ``restore_compiled_context_blocks_runtime_private``).
    """

    compiled_request = compile_chat_payload_if_enabled(
        config=config,
        route=route,
        payload=payload,
    )
    compiled_context_blocks = consume_compiled_context_blocks_runtime_private()
    return compiled_request, compiled_context_blocks


async def handle_managed_chat_completion(
    *,
    request: Request,
    config: RelayLMConfig,
    source_registry: RelayMEMSLPPrimaryWorkerSourceRegistry,
) -> JSONResponse | StreamingResponse:
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

    compiled_request, compiled_context_blocks = await asyncio.to_thread(
        _compile_chat_payload_and_capture_context_blocks,
        config=config,
        route=route,
        payload=payload,
    )
    # The worker thread's ContextVar.set (inside compile_chat_payload_if_enabled)
    # ran in a copied context that asyncio.to_thread discards on return, so it
    # never reaches this request's own context. Replay the captured blocks here
    # before PipelineContext.__post_init__ consumes them.
    restore_compiled_context_blocks_runtime_private(compiled_context_blocks)
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
    relayrel_relationship_projection = await run_stage(
        node_timings,
        "relayrel",
        run_relayrel_stage,
        route=route,
        request_scope_identity=request_scope_identity,
    )
    relayscn_scene_policy_artifact = await run_stage(
        node_timings,
        "relayscn",
        run_relayscn_stage,
        payload=payload,
    )
    relayemo_artifact: dict[str, Any] | None = None
    if config.relayemo_enabled:
        relayemo_artifact = await run_stage(
            node_timings,
            "relayemo",
            run_relayemo_stage,
            config=config,
            route=route,
            payload=payload,
            request=request,
            request_scope_identity=request_scope_identity,
            scope_resolution_diagnostics=scope_resolution_diagnostics,
            messages=_extract_trace_messages(forwarded_payload),
        )

    relayint_intent_artifact = await run_stage(
        node_timings,
        "relayint",
        run_relayint_stage,
        relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
        messages=_extract_trace_messages(payload),
        ctx_hints=_extract_ctx_hints(payload),
    )
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

    relaymem_store_diagnostics, relaymem_retrieval_artifact = await run_stage(
        node_timings,
        "relaymem_retrieval",
        run_relaymem_retrieval_stage,
        config=config,
        route=route,
        relaymem_configured_store_root=config.memory.root_path,
        relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
        relayint_intent_artifact=relayint_intent_artifact,
        messages=_extract_trace_messages(payload),
        offload=True,
    )
    (
        forwarded_payload,
        runtime_ctx_injection_result,
        runtime_snippet_injection_result,
    ) = await run_stage(
        node_timings,
        "relaymem_runtime_ctx",
        run_relaymem_runtime_ctx_stage,
        config=config,
        pipeline_context=pipeline_context,
        relaymem_retrieval_artifact=relaymem_retrieval_artifact,
        compiled_payload=compiled_request.payload,
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
    (
        forwarded_payload,
        relayctx_short_term_runtime_injection_apply_result,
    ) = await run_stage(
        node_timings,
        "relayctx_short_term_injection",
        run_relayctx_short_term_injection_stage,
        config=config,
        pipeline_context=pipeline_context,
        preflight_artifact=relayctx_short_term_runtime_injection_preflight,
    )

    # token_budget_truncation runs last among CTX Repack mutations so it is
    # the final gate on the forwarded payload's estimated token total.
    forwarded_payload, token_budget_truncation = await run_stage(
        node_timings,
        "token_budget_truncation",
        run_token_budget_truncation_stage,
        config=config,
        pipeline_context=pipeline_context,
    )

    compile_decision_dry_run = _build_compile_decision_dry_run_artifact(
        request_id=request_id,
        route=route,
        compiled_request=compiled_request,
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

    # One httpx.AsyncClient is shared across all backend requests for the
    # life of the app (see relaylm.app's lifespan); it is looked up here
    # rather than imported as a module-level global so the dependency stays
    # explicit and request-scoped.
    http_client = get_shared_http_client(request.app)

    if stream_enabled:
        backend_forward_started_at, backend_forward_start_monotonic = _start_timing()
        try:
            status_code, content_type, body_iter = await open_chat_completion_stream(
                forwarded_payload, route, http_client
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
        backend_forward_timing = _finalize_timing(
            backend_forward_started_at, backend_forward_start_monotonic
        )
        stream_relayrun_artifact = _build_relayrun_runtime_artifact_for_context(
            runtime_artifact_context,
            backend_forward_status="completed",
            backend_forward_timing=backend_forward_timing,
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
                    registry=source_registry,
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
        if config.trace.enabled and config.trace.path:
            # LAT-2: measure perceived stream latency (time to first chunk,
            # drain time, chunk count) as a second, later trace record. This
            # cannot be folded into the checkpoint built above -- that
            # artifact is finalized before any stream byte is sent -- so it
            # is emitted separately once the stream finishes or errors. See
            # docs/architecture/lat2_mobile_perceived_latency.md.
            body_iter = wrap_stream_with_relayrun_stream_timing(
                body_iter,
                stream_open_start_monotonic=backend_forward_start_monotonic,
                stream_open_ms=backend_forward_timing.get("duration_ms"),
                on_finalize=lambda artifact: emit_relayrun_stream_timing_trace(
                    config=config,
                    request_id=request_id,
                    character_id=route.character_id,
                    route_model=route.route_model,
                    mode_applied=route.mode_applied,
                    stream_timing=artifact,
                ),
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
            forwarded_payload, route, http_client
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
                    registry=source_registry,
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


def _build_compile_decision_dry_run_artifact(
    *,
    request_id: str,
    route: ResolvedRoute,
    compiled_request: CompiledRequest,
) -> dict[str, Any]:
    """Build the compile-gate/compile-decision dry-run diagnostics artifact.

    Derives the COMPILE_APPLY/COMPILE_DRY_RUN decision state, diagnostics-only
    flag, fallback reason, and blocking reasons from
    ``compiled_request.plan``/``compiled_request.decision``, then hands them
    to ``build_compile_decision_dry_run``. This is pure diagnostics-artifact
    construction: it does not touch ``PipelineContext`` or the backend-bound
    payload, and (matching the handler's inline version before this
    extraction) is not wrapped in a ``run_stage`` timing bracket -- there was
    never a ``node_timings`` entry for it. Its sole consumer is
    ``relayint_runtime_diagnostics_kwargs`` a few lines below the call site,
    which stays untouched: that kwargs-assembly glue belongs with the rest of
    the handler's diagnostics construction, not here.
    """

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

    return build_compile_decision_dry_run(
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


def _extract_ctx_hints(payload: Mapping[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        return {}
    ctx = metadata.get("ctx")
    hints: dict[str, Any] = dict(ctx) if isinstance(ctx, Mapping) else {}
    if "ctx_handoff_guess" in metadata and "ctx_handoff_guess" not in hints:
        hints["ctx_handoff_guess"] = metadata.get("ctx_handoff_guess")
    return hints
