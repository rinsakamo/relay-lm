"""Runtime trace writing helpers for RelayLM MVP-3."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from relaylm.client_history_exclusion_preflight import (
    build_client_history_exclusion_preflight_node_result,
    client_message_canonicalization_dependency_enabled,
)
from relaylm.client_instruction_cache import (
    build_client_instruction_cache_dry_run,
    build_client_instruction_cache_node_result,
)
from relaylm.client_instruction_cache_lookup_runtime import (
    build_client_instruction_cache_lookup_runtime_node_result,
)
from relaylm.client_instruction_extraction import (
    build_client_instruction_extraction_dry_run,
    build_client_instruction_extraction_node_result,
)
from relaylm.client_instruction_fingerprint import (
    build_client_instruction_fingerprint_dry_run,
    build_client_instruction_fingerprint_node_result,
)
from relaylm.client_instruction_identity_runtime import (
    build_client_instruction_identity_runtime_node_result,
    client_instruction_identity_dependency_enabled,
)
from relaylm.client_instruction_relayscn_projection import (
    build_client_instruction_relayscn_projection_node_result,
)
from relaylm.client_message_canonicalization import (
    build_client_message_canonicalization_dry_run,
    build_client_message_canonicalization_node_result,
)
from relaylm.config import RelayLMConfig
from relaylm.diagnostics import RequestDiagnostics
from relaylm.pipeline_context import consume_active_pipeline_context
from relaylm.pipeline_node_adapter import record_phase45_node_results
from relaylm.pipeline_node_result import PipelineNodeResult
from relaylm.trace import append_trace_record, build_trace_record


@dataclass(frozen=True)
class _StreamFinalTraceState:
    config: RelayLMConfig
    diagnostics: RequestDiagnostics
    message_count: int
    response_present: bool


_STREAM_FINAL_TRACE_STATES: dict[str, _StreamFinalTraceState] = {}
_LAST_CONSUMED_CONTEXT_EXPECTS_STREAM_FINAL_TRACE = False


def trace_runtime_event(
    *,
    config: RelayLMConfig,
    diagnostics: RequestDiagnostics,
    message_count: int = 0,
    response_present: bool = False,
    metadata: dict[str, Any] | None = None,
    pipeline_node_results: Sequence[PipelineNodeResult] | None = None,
) -> bool:
    """Append one content-free audit record when tracing is enabled."""

    global _LAST_CONSUMED_CONTEXT_EXPECTS_STREAM_FINAL_TRACE
    _LAST_CONSUMED_CONTEXT_EXPECTS_STREAM_FINAL_TRACE = False
    explicit_pipeline_node_results = pipeline_node_results is not None
    resolved_pipeline_node_results = (
        _pipeline_node_results_to_log_dicts(pipeline_node_results)
        if explicit_pipeline_node_results
        else _consume_pipeline_node_results(diagnostics)
    )
    context_expects_stream_final_trace = (
        _LAST_CONSUMED_CONTEXT_EXPECTS_STREAM_FINAL_TRACE
    )
    _LAST_CONSUMED_CONTEXT_EXPECTS_STREAM_FINAL_TRACE = False
    if not config.trace.enabled or not config.trace.path:
        return False

    try:
        trace_metadata = dict(metadata or {})
        metadata_expects_stream_final_trace = bool(
            trace_metadata.pop("stream_final_pipeline_node_results_expected", False)
        )
        if resolved_pipeline_node_results is not None and not explicit_pipeline_node_results:
            trace_metadata["pipeline_node_results"] = resolved_pipeline_node_results
        trace_metadata.update(_supported_diagnostics_metadata(diagnostics))
        record = build_trace_record(
            trace_id=diagnostics.request_id,
            character_id=diagnostics.character_id,
            route_model=diagnostics.route_model,
            mode_applied=diagnostics.mode_applied,
            compiler_used=diagnostics.compiler_used,
            message_count=message_count,
            response_present=response_present,
            metadata=trace_metadata,
        )
        if (
            explicit_pipeline_node_results
            and _is_stream_final_tts_node_results(resolved_pipeline_node_results)
        ):
            record.metadata["event"] = "backend_stream_response"
            record.metadata["pipeline_node_results"] = resolved_pipeline_node_results or []
        append_trace_record(config.trace.path, record)
        if trace_metadata.get("event") == "backend_stream_response" and (
            metadata_expects_stream_final_trace
            or context_expects_stream_final_trace
        ):
            _STREAM_FINAL_TRACE_STATES[diagnostics.request_id] = _StreamFinalTraceState(
                config=config,
                diagnostics=diagnostics,
                message_count=message_count,
                response_present=response_present,
            )
    except Exception:
        return False
    return True


def trace_runtime_stream_final_pipeline_node_results(
    *,
    pipeline_context: Any,
    node_results: Sequence[PipelineNodeResult],
) -> bool:
    """Append stream-final node results after the initial context was consumed."""

    request_id = getattr(pipeline_context, "request_id", None)
    if not isinstance(request_id, str) or not request_id:
        return False
    if not node_results:
        return False
    state = _STREAM_FINAL_TRACE_STATES.pop(request_id, None)
    if state is None:
        return False
    return trace_runtime_event(
        config=state.config,
        diagnostics=state.diagnostics,
        message_count=state.message_count,
        response_present=state.response_present,
        metadata={"event": "backend_stream_response"},
        pipeline_node_results=node_results,
    )


def _pipeline_node_results_to_log_dicts(
    node_results: Sequence[PipelineNodeResult],
) -> list[dict[str, Any]]:
    return [result.to_log_dict() for result in node_results]


def _is_stream_final_tts_node_results(
    node_results: list[dict[str, Any]] | None,
) -> bool:
    if not node_results:
        return False
    allowed = {
        "relayctx_tts_segmentation_hints",
        "relayctx_tts_adapter_handoff",
    }
    return all(result.get("node_name") in allowed for result in node_results)


def _route_expects_stream_final_trace(route: Any) -> bool:
    """Return true only for C2 streams where the finalizer can emit node results."""

    route_values = vars(route) if hasattr(route, "__dict__") else {}
    c2_enabled = any(
        "tts" in name
        and "handoff" in name
        and "runtime" in name
        and bool(value)
        for name, value in route_values.items()
    )
    b2_apply_available = any(
        "stream" in name
        and "suppression" in name
        and ("apply" in name or "runtime" in name)
        and bool(value)
        for name, value in route_values.items()
    )
    return c2_enabled and b2_apply_available


def _supported_diagnostics_metadata(
    diagnostics: RequestDiagnostics,
) -> dict[str, object]:
    output: dict[str, object] = {}
    supported = (
        ("memory_source", diagnostics.memory_source),
        ("memory_selection_summary", diagnostics.memory_selection_summary),
        ("memory_block_assembly", diagnostics.memory_block_assembly),
        ("token_memory_dry_run", diagnostics.token_memory_dry_run),
        ("stable_prefix_hash", diagnostics.stable_prefix_hash),
        ("stable_prefix_block_ids", diagnostics.stable_prefix_block_ids),
        ("compile_decision_dry_run", diagnostics.compile_decision_dry_run),
        ("runtime_ctx_injection_result", diagnostics.runtime_ctx_injection_result),
        (
            "runtime_snippet_injection_result",
            diagnostics.runtime_snippet_injection_result,
        ),
        ("relayrun_artifact", diagnostics.relayrun_artifact),
    )
    for key, value in supported:
        if value is not None:
            output[key] = value
    return output


def _consume_pipeline_node_results(
    diagnostics: RequestDiagnostics,
) -> list[dict[str, Any]] | None:
    global _LAST_CONSUMED_CONTEXT_EXPECTS_STREAM_FINAL_TRACE
    pipeline_context = consume_active_pipeline_context()
    if pipeline_context is None:
        return None

    try:
        _LAST_CONSUMED_CONTEXT_EXPECTS_STREAM_FINAL_TRACE = (
            _route_expects_stream_final_trace(pipeline_context.route)
        )
        managed_route = pipeline_context.route.mode_applied != "pass_through"
        instruction_dependency_enabled = bool(
            client_instruction_identity_dependency_enabled(pipeline_context.route)
            or pipeline_context.route.client_instruction_cache_write_enabled
        )
        canonicalization = build_client_message_canonicalization_dry_run(
            pipeline_context.original_payload,
            enabled=client_message_canonicalization_dependency_enabled(
                pipeline_context.route
            ),
            managed_route=managed_route,
        )
        canonicalization_node = build_client_message_canonicalization_node_result(
            canonicalization
        )
        if canonicalization_node is not None:
            pipeline_context.node_results.insert(0, canonicalization_node)

        extraction = build_client_instruction_extraction_dry_run(
            pipeline_context.original_payload,
            enabled=instruction_dependency_enabled,
            managed_route=managed_route,
        )
        extraction_node = build_client_instruction_extraction_node_result(extraction)
        fingerprint = build_client_instruction_fingerprint_dry_run(
            extraction,
            enabled=instruction_dependency_enabled,
        )
        fingerprint_node = build_client_instruction_fingerprint_node_result(fingerprint)
        identity_node = build_client_instruction_identity_runtime_node_result(
            pipeline_context.client_instruction_identity_result
        )
        cache = build_client_instruction_cache_dry_run(
            fingerprint,
            enabled=instruction_dependency_enabled,
            lookup_requested=(
                pipeline_context.route.client_instruction_cache_lookup_enabled
            ),
            save_requested=(
                pipeline_context.route.client_instruction_cache_write_enabled
            ),
        )
        cache_node = build_client_instruction_cache_node_result(cache)
        cache_lookup_runtime_result = (
            pipeline_context.client_instruction_cache_lookup_runtime_result
        )
        lookup_node = build_client_instruction_cache_lookup_runtime_node_result(
            cache_lookup_runtime_result
        )
        projection_node = build_client_instruction_relayscn_projection_node_result(
            cache_lookup_runtime_result
        )
        history_node = build_client_history_exclusion_preflight_node_result(
            pipeline_context.client_history_exclusion_preflight_result
        )

        record_phase45_node_results(
            pipeline_context,
            relayref_artifact=diagnostics.relayref_artifact,
            relayint_fast_path_dry_run=diagnostics.relayint_fast_path_dry_run,
            relayint_quick_clarification_preflight=(
                diagnostics.relayint_quick_clarification_preflight
            ),
            relayint_quick_clarification_apply_plan=(
                diagnostics.relayint_quick_clarification_apply_plan
            ),
            runtime_ctx_injection_result=diagnostics.runtime_ctx_injection_result,
            runtime_snippet_injection_result=(
                diagnostics.runtime_snippet_injection_result
            ),
            token_budget_truncation=diagnostics.token_budget_truncation,
            relayctx_short_term_runtime_injection_apply_result=(
                diagnostics.relayctx_short_term_runtime_injection_apply_result
            ),
        )

        if extraction_node is not None:
            _insert_after_node_result(
                pipeline_context.node_results,
                extraction_node,
                after_node_name="client_message_canonicalization",
            )
        if fingerprint_node is not None:
            _insert_after_node_result(
                pipeline_context.node_results,
                fingerprint_node,
                after_node_name="client_instruction_extraction",
            )
        if identity_node is not None:
            _insert_after_node_result(
                pipeline_context.node_results,
                identity_node,
                after_node_name="client_instruction_fingerprint",
            )
        if cache_node is not None:
            _insert_after_node_result(
                pipeline_context.node_results,
                cache_node,
                after_node_name=(
                    "client_instruction_identity"
                    if identity_node is not None
                    else "client_instruction_fingerprint"
                ),
            )
        if lookup_node is not None:
            _insert_after_node_result(
                pipeline_context.node_results,
                lookup_node,
                after_node_name="client_instruction_cache",
            )
        if projection_node is not None:
            _insert_after_node_result(
                pipeline_context.node_results,
                projection_node,
                after_node_name=(
                    "client_instruction_cache_lookup"
                    if lookup_node is not None
                    else "client_instruction_cache"
                ),
            )
        typed_parse_anchor = (
            "client_instruction_relayscn_projection"
            if projection_node is not None
            else "client_instruction_cache_lookup"
            if lookup_node is not None
            else "client_instruction_cache"
            if cache_node is not None
            else "client_instruction_identity"
            if identity_node is not None
            else "client_instruction_fingerprint"
        )
        _move_existing_node_after(
            pipeline_context.node_results,
            node_name="client_instruction_typed_parse",
            after_node_name=typed_parse_anchor,
        )
        cache_write_anchor = (
            "client_instruction_typed_parse"
            if _node_result_exists(
                pipeline_context.node_results,
                "client_instruction_typed_parse",
            )
            else typed_parse_anchor
        )
        _move_existing_node_after(
            pipeline_context.node_results,
            node_name="client_instruction_cache_write",
            after_node_name=cache_write_anchor,
        )
        if history_node is not None:
            _insert_after_node_result(
                pipeline_context.node_results,
                history_node,
                after_node_name=(
                    "client_instruction_cache_write"
                    if _node_result_exists(
                        pipeline_context.node_results,
                        "client_instruction_cache_write",
                    )
                    else "client_instruction_typed_parse"
                    if _node_result_exists(
                        pipeline_context.node_results,
                        "client_instruction_typed_parse",
                    )
                    else "client_instruction_relayscn_projection"
                    if projection_node is not None
                    else "client_instruction_cache_lookup"
                    if lookup_node is not None
                    else "client_instruction_cache"
                    if cache_node is not None
                    else "client_message_canonicalization"
                ),
            )
            _move_existing_node_after(
                pipeline_context.node_results,
                node_name="client_history_exclusion_apply",
                after_node_name="client_history_exclusion_preflight",
            )
        return pipeline_context.node_results_to_log_dicts()
    except Exception:
        _LAST_CONSUMED_CONTEXT_EXPECTS_STREAM_FINAL_TRACE = False
        return None


def _insert_after_node_result(
    node_results: list[PipelineNodeResult],
    node_result: PipelineNodeResult,
    *,
    after_node_name: str,
) -> None:
    insert_index = 0
    for index, existing in enumerate(node_results):
        if existing.node_name == after_node_name:
            insert_index = index + 1
            break
    node_results.insert(insert_index, node_result)


def _move_existing_node_after(
    node_results: list[PipelineNodeResult],
    *,
    node_name: str,
    after_node_name: str,
) -> None:
    moving_index = next(
        (index for index, result in enumerate(node_results) if result.node_name == node_name),
        None,
    )
    if moving_index is None:
        return
    moving = node_results.pop(moving_index)
    target_index = next(
        (
            index + 1
            for index, result in enumerate(node_results)
            if result.node_name == after_node_name
        ),
        len(node_results),
    )
    node_results.insert(target_index, moving)


def _node_result_exists(node_results: list[PipelineNodeResult], node_name: str) -> bool:
    return any(result.node_name == node_name for result in node_results)


def extract_response_text(body: Any) -> str | None:
    """Extract text or an empty shape marker from the first response choice."""

    if not isinstance(body, dict):
        return None
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
        if (
            "content" in message
            or "tool_calls" in message
            or "function_call" in message
        ):
            return ""
    text = first.get("text")
    return text if isinstance(text, str) else None
