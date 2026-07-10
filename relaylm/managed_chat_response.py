"""Response-side service for the managed `/v1/chat/completions` route.

Owns everything from the backend forward call onward:

* opening/forwarding the backend request (stream and non-stream) and the
  ``BackendRequestError`` -> 502 error-response path,
* wrapping the stream body with the RelayMEM SLP finalized-turn capture and
  the LAT-2 stream timing wrapper (RelayCTX suppression and the TTS adapter
  handoff wrapping already live inside
  ``relaylm.adapter.open_chat_completion_stream`` and are untouched here --
  they wrap the raw backend byte stream before it is ever handed to this
  module),
* building the ``JSONResponse``/``StreamingResponse`` (status, headers,
  media type, background task),
* the durable-finalization gate checks and admission/start calls, and
* the post-response RelayMEM SLP ``BackgroundTask`` enqueue and the
  response-side ``trace_runtime_event`` calls.

``relaylm.managed_chat_runtime.handle_managed_chat_completion`` builds the
request-scoped diagnostics and pipeline artifacts, then hands everything off
to :func:`build_managed_chat_response` here in one call.

A second, finalization-only module was considered and rejected: the durable-
finalization gate checks, the ``BackgroundTask`` construction, and the
response object construction are woven together statement-by-statement in
both the stream and non-stream branches below (a gate failure returns early
*instead of* building the normal response, sharing the same
``status_code``/``diagnostics`` locals the success path needs), so splitting
them would mean threading the same half-built response state back and forth
between two modules for no real decoupling benefit.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from relaylm.adapter import (
    BackendRequestError,
    forward_chat_completion_json,
    open_chat_completion_stream,
)
from relaylm.app_request_validation import openai_error
from relaylm.app_response_finalization import (
    close_stream_iterator,
    durable_finalization_apply_mode,
    durable_finalization_gate_relevant,
    durable_finalization_gate_valid,
    durable_finalization_server_error,
    get_shared_http_client,
)
from relaylm.config import RelayLMConfig
from relaylm.diagnostics import RequestDiagnostics
from relaylm.pipeline_context import PipelineContext
from relaylm.pipeline_stage import _finalize_timing, _start_timing
from relaylm.relayemo_response_marker import (
    apply_relayemo_marker_to_response,
    build_relayemo_text_marker_preview,
)
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
from relaylm.relayrun_runtime_artifact import (
    _ManagedRuntimeArtifactContext,
    _build_relayrun_runtime_artifact_for_context,
)
from relaylm.relayrun_stream_timing import (
    emit_relayrun_stream_timing_trace,
    wrap_stream_with_relayrun_stream_timing,
)
from relaylm.routing import ResolvedRoute
from relaylm.trace_runtime import extract_response_text, trace_runtime_event


async def build_managed_chat_response(
    *,
    request: Request,
    config: RelayLMConfig,
    source_registry: RelayMEMSLPPrimaryWorkerSourceRegistry,
    request_id: str,
    route: ResolvedRoute,
    stream_enabled: bool,
    forwarded_payload: Mapping[str, Any],
    forwarded_message_count: int,
    pipeline_context: PipelineContext,
    merged_scope: Mapping[str, Any],
    diagnostics: RequestDiagnostics,
    runtime_artifact_context: _ManagedRuntimeArtifactContext,
) -> JSONResponse | StreamingResponse:
    """Forward ``forwarded_payload`` to the backend and build its response.

    ``forwarded_message_count`` is ``len(_extract_trace_messages(forwarded_payload))``
    computed once by the caller: every trace/background-enqueue call site
    below needs that same count and recomputing it from ``forwarded_payload``
    at each site would just be redundant work (the helper that derives it,
    ``_extract_trace_messages``, stays in ``managed_chat_runtime`` since it is
    also used by the pre-backend pipeline stages there).

    One ``httpx.AsyncClient`` is shared across all backend requests for the
    life of the app (see ``relaylm.app``'s lifespan); it is looked up here via
    ``request.app`` rather than imported as a module-level global so the
    dependency stays explicit and request-scoped.
    """

    http_client = get_shared_http_client(request.app)
    if stream_enabled:
        return await _build_stream_response(
            config=config,
            source_registry=source_registry,
            request_id=request_id,
            route=route,
            forwarded_payload=forwarded_payload,
            forwarded_message_count=forwarded_message_count,
            pipeline_context=pipeline_context,
            merged_scope=merged_scope,
            diagnostics=diagnostics,
            runtime_artifact_context=runtime_artifact_context,
            http_client=http_client,
        )
    return await _build_nonstream_response(
        config=config,
        source_registry=source_registry,
        route=route,
        forwarded_payload=forwarded_payload,
        forwarded_message_count=forwarded_message_count,
        pipeline_context=pipeline_context,
        merged_scope=merged_scope,
        diagnostics=diagnostics,
        runtime_artifact_context=runtime_artifact_context,
        http_client=http_client,
    )


async def _build_stream_response(
    *,
    config: RelayLMConfig,
    source_registry: RelayMEMSLPPrimaryWorkerSourceRegistry,
    request_id: str,
    route: ResolvedRoute,
    forwarded_payload: Mapping[str, Any],
    forwarded_message_count: int,
    pipeline_context: PipelineContext,
    merged_scope: Mapping[str, Any],
    diagnostics: RequestDiagnostics,
    runtime_artifact_context: _ManagedRuntimeArtifactContext,
    http_client: httpx.AsyncClient,
) -> JSONResponse | StreamingResponse:
    relayscn_scene_policy_artifact = runtime_artifact_context.relayscn_scene_policy_artifact
    relayemo_artifact = runtime_artifact_context.relayemo_artifact

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
            forwarded_message_count=forwarded_message_count,
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
                message_count=forwarded_message_count,
            )
    trace_runtime_event(
        config=config,
        diagnostics=stream_diagnostics,
        message_count=forwarded_message_count,
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


async def _build_nonstream_response(
    *,
    config: RelayLMConfig,
    source_registry: RelayMEMSLPPrimaryWorkerSourceRegistry,
    route: ResolvedRoute,
    forwarded_payload: Mapping[str, Any],
    forwarded_message_count: int,
    pipeline_context: PipelineContext,
    merged_scope: Mapping[str, Any],
    diagnostics: RequestDiagnostics,
    runtime_artifact_context: _ManagedRuntimeArtifactContext,
    http_client: httpx.AsyncClient,
) -> JSONResponse:
    relayscn_scene_policy_artifact = runtime_artifact_context.relayscn_scene_policy_artifact
    relayemo_artifact = runtime_artifact_context.relayemo_artifact

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
            forwarded_message_count=forwarded_message_count,
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
        marker_preview = build_relayemo_text_marker_preview(config, relayemo_artifact)
        relayemo_artifact["text_marker_preview"] = marker_preview
        apply_mode = config.relayemo_text_marker_apply_mode
        if apply_mode == "apply":
            body = apply_relayemo_marker_to_response(body, marker_preview)
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
                    message_count=forwarded_message_count,
                )
        trace_runtime_event(
            config=config,
            diagnostics=success_diagnostics,
            message_count=forwarded_message_count,
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


def _build_backend_request_error_response(
    *,
    config: RelayLMConfig,
    exc: BackendRequestError,
    diagnostics: RequestDiagnostics,
    runtime_artifact_context: _ManagedRuntimeArtifactContext,
    forwarded_message_count: int,
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
        message_count=forwarded_message_count,
        response_present=False,
        metadata={"event": "backend_error", "error_type": exc.__class__.__name__},
    )
    return openai_error(
        status_code=502,
        message=f"RelayLM could not reach backend: {exc}",
        error_type="backend_connection_error",
        headers=failed_diagnostics.to_headers(),
    )
