"""Managed `/v1/chat/completions` runtime orchestration for RelayLM.

Owns the request validation call, compile/runtime pipeline orchestration
(RelayREL/RelaySCN/RelayEMO/RelayINT/RelayMEM/RelayCTX/token-budget runtime
steps), and request diagnostics construction for the managed chat completion
route. Once diagnostics are assembled, the handler hands everything off in
one call to ``relaylm.managed_chat_response.build_managed_chat_response``,
which owns backend forwarding, stream/non-stream response construction,
tracing, and response finalization/background enqueue integration.
`relaylm/app.py` stays a thin FastAPI entrypoint that delegates to
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

from relaylm.app_request_validation import (
    _validate_and_resolve_managed_chat_request,
)
from relaylm.config import RelayLMConfig
from relaylm.managed_chat_response import build_managed_chat_response
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
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
from relaylm.relayemo import run_relayemo_stage
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
    request_scope_identity = extract_request_scope_identity(request.headers, payload)
    scope_resolution_diagnostics = build_scope_resolution_diagnostics(route, request_scope_identity)
    merged_scope = dict(scope_resolution_diagnostics.merged_scope)
    merged_scope["character_id"] = route.character_id
    merged_scope["memory_namespace"] = route.memory_namespace
    merged_scope["cache_namespace"] = route.cache_namespace

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

    diagnostics = _build_request_diagnostics(
        runtime_artifact_context=runtime_artifact_context,
        compiled_request=compiled_request,
        payload=payload,
        merged_scope=merged_scope,
        relaymem_diagnostics_artifact=relaymem_diagnostics_artifact,
        request_scope_identity=request_scope_identity,
        scope_resolution_diagnostics=scope_resolution_diagnostics,
        relayctx_short_term_extraction_dry_run=relayctx_short_term_extraction_dry_run,
        relayctx_short_term_block_assembly_dry_run=relayctx_short_term_block_assembly_dry_run,
        relayctx_short_term_runtime_injection_preflight=(
            relayctx_short_term_runtime_injection_preflight
        ),
    )

    return await build_managed_chat_response(
        request=request,
        config=config,
        source_registry=source_registry,
        request_id=request_id,
        route=route,
        stream_enabled=stream_enabled,
        forwarded_payload=forwarded_payload,
        forwarded_message_count=len(_extract_trace_messages(forwarded_payload)),
        pipeline_context=pipeline_context,
        merged_scope=merged_scope,
        diagnostics=diagnostics,
        runtime_artifact_context=runtime_artifact_context,
    )


def _build_request_diagnostics(
    *,
    runtime_artifact_context: _ManagedRuntimeArtifactContext,
    compiled_request: CompiledRequest,
    payload: Mapping[str, Any],
    merged_scope: Mapping[str, Any],
    relaymem_diagnostics_artifact: Mapping[str, Any],
    request_scope_identity: Any,
    scope_resolution_diagnostics: Any,
    relayctx_short_term_extraction_dry_run: dict[str, Any] | None,
    relayctx_short_term_block_assembly_dry_run: dict[str, Any] | None,
    relayctx_short_term_runtime_injection_preflight: dict[str, Any] | None,
) -> RequestDiagnostics:
    """Assemble the full ``RequestDiagnostics`` for one managed chat completion.

    This bundles every dry-run/shadow/preflight diagnostics artifact that,
    unlike the pipeline stage outputs already bundled in
    ``runtime_artifact_context``, exists purely to describe request handling
    and is never consumed by an actual stage call: the token-policy shadow
    evaluation, the memory-adapter shadow delta, the RelayINT fast-path and
    quick-clarification dry runs, the RelayCTX short-term source
    diagnostics, and the compile-decision dry run. None of those gate or
    feed the real pipeline stage calls in ``handle_managed_chat_completion``
    -- the three RelayCTX short-term artifacts accepted as parameters here
    are the exception, since they *do* feed the real
    ``relayctx_short_term_injection`` stage and so are computed in the
    handler before that stage runs, then just passed through here for their
    diagnostics kwargs. Keeping this assembly in its own function is what
    lets the handler's body stay limited to request validation and pipeline
    orchestration.
    """

    config = runtime_artifact_context.config
    route = runtime_artifact_context.route

    effective_shadow_enabled, shadow_source = _resolve_token_policy_shadow_setting(config, route)
    token_policy_signal = build_token_policy_signal(compiled_request.token_memory_dry_run)
    token_policy_decision = build_token_policy_decision_artifact(
        token_policy_signal,
        shadow_enabled=effective_shadow_enabled,
        shadow_source=shadow_source,
    )
    token_policy_readiness = build_token_policy_readiness_check(token_policy_decision)

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
            relayscn_scene_policy_artifact=(
                runtime_artifact_context.relayscn_scene_policy_artifact
            ),
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
            stream_enabled=runtime_artifact_context.stream_enabled,
            response_max_chars=config.relayint_quick_clarification_response_max_chars,
            request_compatibility_gate=build_relayint_request_compatibility_gate(payload),
        )
    )

    relayctx_short_term_source_diagnostics = (
        build_relayctx_short_term_source_diagnostics(
            messages=_extract_trace_messages(payload),
            enabled=config.relayctx_short_term_source_diagnostics_enabled,
            memory_source=compiled_request.memory_source,
            relaymem_retrieval_artifact=runtime_artifact_context.relaymem_retrieval_artifact,
        )
    )

    compile_decision_dry_run = _build_compile_decision_dry_run_artifact(
        request_id=runtime_artifact_context.request_id,
        route=route,
        compiled_request=compiled_request,
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
        request_id=runtime_artifact_context.request_id,
        route_model=route.route_model,
        backend_model=route.backend_model,
        backend_name=route.backend_name,
        character_id=route.character_id,
        mode_requested=route.mode_requested,
        mode_applied=route.mode_applied,
        stream_enabled=runtime_artifact_context.stream_enabled,
        **compiled_request_diagnostics_kwargs(compiled_request),
        **token_policy_diagnostics_kwargs(
            token_policy_signal=token_policy_signal,
            token_policy_decision=token_policy_decision,
            token_policy_readiness=token_policy_readiness,
            token_budget_truncation=runtime_artifact_context.token_budget_truncation,
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
            relayrel_relationship_projection=(
                runtime_artifact_context.relayrel_relationship_projection
            ),
            relayemo_artifact=runtime_artifact_context.relayemo_artifact,
            relayscn_scene_policy_artifact=(
                runtime_artifact_context.relayscn_scene_policy_artifact
            ),
            relayint_intent_artifact=runtime_artifact_context.relayint_intent_artifact,
            relaymem_retrieval_artifact=relaymem_diagnostics_artifact,
            runtime_ctx_injection_result=runtime_artifact_context.runtime_ctx_injection_result,
            runtime_snippet_injection_result=(
                runtime_artifact_context.runtime_snippet_injection_result
            ),
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
                runtime_artifact_context.relayctx_short_term_runtime_injection_apply_result
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
    return replace(
        base_diagnostics,
        relaysoul_runtime_feedback_summary=feedback_summary,
    )


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
    ``relayint_runtime_diagnostics_kwargs``, called from
    ``_build_request_diagnostics``, which stays untouched: that kwargs-
    assembly glue belongs with the rest of the diagnostics construction, not
    here.
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
