"""Post-validation managed chat pipeline orchestration."""

from __future__ import annotations
import asyncio
from copy import deepcopy
from collections.abc import Mapping
from typing import Any
from fastapi import Request
from relaylm.config import RelayLMConfig
from relaylm.diagnostics import (
    build_relayctx_short_term_block_assembly_dry_run,
    build_relayctx_short_term_extraction_dry_run,
    build_relayctx_short_term_runtime_injection_preflight,
)
from relaylm.evidence_runtime import capture_evidence_for_user_input
from relaylm.pipeline_context import PipelineContext
from relaylm.pipeline_stage import run_stage
from relaylm.relayctx_repack import (
    run_relayctx_short_term_injection_stage,
    run_relaymem_runtime_ctx_stage,
)
from relaylm.relayemo import run_relayemo_stage
from relaylm.relayint import run_relayint_stage
from relaylm.relaymem_retrieval import run_relaymem_retrieval_stage
from relaylm.relayrel import run_relayrel_stage
from relaylm.relayrun import new_run_id
from relaylm.relayrun_runtime_artifact import _ManagedRuntimeArtifactContext
from relaylm.relayscn import run_relayscn_stage
from relaylm.request_compiler import (
    CompiledRequest,
    compile_chat_payload_if_enabled,
    consume_compiled_context_blocks_runtime_private,
    restore_compiled_context_blocks_runtime_private,
)
from relaylm.request_scope import (
    build_scope_resolution_diagnostics,
    extract_request_scope_identity,
)
from relaylm.routing import ResolvedRoute
from relaylm.token_budget_truncation import run_token_budget_truncation_stage


def _extract_trace_messages(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return []
    return [item for item in messages if isinstance(item, Mapping)]


def _extract_ctx_hints(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    ctx_hints = payload.get("ctx_hints")
    if not isinstance(ctx_hints, list):
        return []
    return [item for item in ctx_hints if isinstance(item, Mapping)]


def _compile_chat_payload_and_capture_context_blocks(
    *, config: RelayLMConfig, route: ResolvedRoute, payload: Mapping[str, Any]
) -> tuple[CompiledRequest, tuple[Any, ...] | None]:
    compiled_request = compile_chat_payload_if_enabled(
        config=config, route=route, payload=payload
    )
    return compiled_request, consume_compiled_context_blocks_runtime_private()


async def _initialize_pipeline(request_bundle, capture_evidence):
    request, config, request_id, route, payload, stream_enabled = request_bundle
    run_id = new_run_id()
    compiled, blocks = await asyncio.to_thread(
        _compile_chat_payload_and_capture_context_blocks,
        config=config,
        route=route,
        payload=payload,
    )
    restore_compiled_context_blocks_runtime_private(blocks)
    context = PipelineContext(
        request_id=request_id,
        run_id=run_id,
        original_payload=payload,
        forwarded_payload=dict(compiled.payload),
        route=route,
        stream_enabled=stream_enabled,
    )
    identity = extract_request_scope_identity(request.headers, payload)
    scope_diagnostics = build_scope_resolution_diagnostics(route, identity)
    scope = dict(scope_diagnostics.merged_scope)
    evidence = capture_evidence(
        config=config, pipeline_context=context, resolved_scope=scope
    )
    if evidence is not None:
        context.record_node_result(evidence)
        rejected = (
            config.evidence_capture_enabled
            and config.evidence_capture_apply_enabled
            and not config.evidence_capture_dry_run_only
            and evidence.decision != "admitted"
        )
        if rejected:
            return {"evidence_rejected": True}
    scope.update(
        character_id=route.character_id,
        memory_namespace=route.memory_namespace,
        cache_namespace=route.cache_namespace,
    )
    return {
        "run_id": run_id,
        "compiled": compiled,
        "context": context,
        "identity": identity,
        "scope_diagnostics": scope_diagnostics,
        "scope": scope,
        "forwarded": context.forwarded_payload,
    }


async def _run_memory_stages(
    state, config, route, payload, node_timings, scene, intent
):
    store, retrieval = await run_stage(
        node_timings,
        "relaymem_retrieval",
        run_relaymem_retrieval_stage,
        config=config,
        route=route,
        relaymem_configured_store_root=config.memory.root_path,
        relayscn_scene_policy_artifact=scene,
        relayint_intent_artifact=intent,
        messages=_extract_trace_messages(payload),
        offload=True,
    )
    forwarded, ctx_result, snippet_result = await run_stage(
        node_timings,
        "relaymem_runtime_ctx",
        run_relaymem_runtime_ctx_stage,
        config=config,
        pipeline_context=state["context"],
        relaymem_retrieval_artifact=retrieval,
        compiled_payload=state["compiled"].payload,
    )
    projection = retrieval.get("primary_recall_projection")
    if isinstance(projection, dict):
        projection["injection_performed"] = (
            snippet_result.get("applied") is True or ctx_result.get("applied") is True
        )
        projection["memory_used"] = projection["injection_performed"]
    diagnostics = {
        "artifact_version": "relaymem_retrieval_projection.v0",
        "diagnostics_only": True,
        "content_free": True,
        "primary_recall_projection": (
            deepcopy(projection) if isinstance(projection, dict) else None
        ),
    }
    return forwarded, retrieval, ctx_result, snippet_result, diagnostics


async def _run_ctx_repack(state, config, payload, node_timings):
    inbound = _extract_trace_messages(payload)
    extraction = build_relayctx_short_term_extraction_dry_run(
        messages=inbound,
        enabled=config.relayctx_short_term_extraction_dry_run_enabled,
        memory_source=state["compiled"].memory_source,
    )
    assembly = build_relayctx_short_term_block_assembly_dry_run(
        extraction_artifact=extraction,
        enabled=config.relayctx_short_term_block_assembly_dry_run_enabled,
    )
    preflight = build_relayctx_short_term_runtime_injection_preflight(
        assembly_artifact=assembly,
        enabled=config.relayctx_short_term_runtime_injection_preflight_enabled,
        dry_run_only=config.relayctx_short_term_runtime_injection_dry_run_only,
    )
    forwarded, apply_result = await run_stage(
        node_timings,
        "relayctx_short_term_injection",
        run_relayctx_short_term_injection_stage,
        config=config,
        pipeline_context=state["context"],
        preflight_artifact=preflight,
    )
    forwarded, truncation = await run_stage(
        node_timings,
        "token_budget_truncation",
        run_token_budget_truncation_stage,
        config=config,
        pipeline_context=state["context"],
    )
    return forwarded, extraction, assembly, preflight, apply_result, truncation


def _build_runtime_context(
    state,
    config,
    request_id,
    route,
    stream_enabled,
    semantic_stages,
    memory_stages,
    short_apply,
    truncation,
    node_timings,
):
    relationship, scene, emotion, intent = semantic_stages
    retrieval, ctx_result, snippet_result = memory_stages
    return _ManagedRuntimeArtifactContext(
        config=config,
        request_id=request_id,
        run_id=state["run_id"],
        route=route,
        stream_enabled=stream_enabled,
        relayrel_relationship_projection=relationship,
        relayscn_scene_policy_artifact=scene,
        relayemo_artifact=emotion,
        relayint_intent_artifact=intent,
        relaymem_retrieval_artifact=retrieval,
        runtime_ctx_injection_result=ctx_result,
        runtime_snippet_injection_result=snippet_result,
        relayctx_short_term_runtime_injection_apply_result=short_apply,
        token_budget_truncation=truncation,
        node_timings=node_timings,
    )


async def run_managed_chat_pipeline(
    *,
    request: Request,
    config: RelayLMConfig,
    request_id: str,
    route: ResolvedRoute,
    payload: Mapping[str, Any],
    stream_enabled: bool,
    node_timings: dict[str, Any],
    capture_evidence=capture_evidence_for_user_input,
) -> dict[str, Any]:
    """Execute the ordered post-validation pipeline exactly once."""
    state = await _initialize_pipeline(
        (request, config, request_id, route, payload, stream_enabled), capture_evidence
    )
    if state.get("evidence_rejected"):
        return state
    relationship = await run_stage(
        node_timings,
        "relayrel",
        run_relayrel_stage,
        route=route,
        request_scope_identity=state["identity"],
    )
    scene = await run_stage(
        node_timings, "relayscn", run_relayscn_stage, payload=payload
    )
    emotion = None
    if config.relayemo_enabled:
        emotion = await run_stage(
            node_timings,
            "relayemo",
            run_relayemo_stage,
            config=config,
            route=route,
            payload=payload,
            request=request,
            request_scope_identity=state["identity"],
            scope_resolution_diagnostics=state["scope_diagnostics"],
            messages=_extract_trace_messages(state["forwarded"]),
        )
    intent = await run_stage(
        node_timings,
        "relayint",
        run_relayint_stage,
        relayscn_scene_policy_artifact=scene,
        messages=_extract_trace_messages(payload),
        ctx_hints=_extract_ctx_hints(payload),
    )
    forwarded, retrieval, ctx_result, snippet_result, memory_diagnostics = (
        await _run_memory_stages(
            state, config, route, payload, node_timings, scene, intent
        )
    )
    forwarded, extraction, assembly, preflight, short_apply, truncation = (
        await _run_ctx_repack(state, config, payload, node_timings)
    )
    runtime_context = _build_runtime_context(
        state,
        config,
        request_id,
        route,
        stream_enabled,
        (relationship, scene, emotion, intent),
        (retrieval, ctx_result, snippet_result),
        short_apply,
        truncation,
        node_timings,
    )
    state.update(
        forwarded=forwarded,
        runtime_context=runtime_context,
        memory_diagnostics=memory_diagnostics,
        extraction=extraction,
        assembly=assembly,
        preflight=preflight,
    )
    return state
