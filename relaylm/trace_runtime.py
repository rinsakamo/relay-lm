"""Runtime trace writing helpers for RelayLM MVP-3."""

from __future__ import annotations

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


def trace_runtime_event(
    *,
    config: RelayLMConfig,
    diagnostics: RequestDiagnostics,
    message_count: int = 0,
    response_present: bool = False,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Append one content-free audit record when tracing is enabled.

    Runtime producers pass only request/response shape and explicitly supported
    audit artifacts. Unsupported RequestDiagnostics fields never enter the
    projection boundary. This write API is intentionally shape-only.
    """

    pipeline_node_results = _consume_pipeline_node_results(diagnostics)
    if not config.trace.enabled or not config.trace.path:
        return False

    try:
        trace_metadata = dict(metadata or {})
        if pipeline_node_results is not None:
            trace_metadata["pipeline_node_results"] = pipeline_node_results
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
        append_trace_record(config.trace.path, record)
    except Exception:
        return False
    return True


def _supported_diagnostics_metadata(
    diagnostics: RequestDiagnostics,
) -> dict[str, object]:
    """Return only artifacts with registered top-level projectors."""

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
    pipeline_context = consume_active_pipeline_context()
    if pipeline_context is None:
        return None

    try:
        managed_route = pipeline_context.route.mode_applied != "pass_through"
        instruction_dependency_enabled = client_instruction_identity_dependency_enabled(
            pipeline_context.route
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
            save_requested=False,
        )
        cache_node = build_client_instruction_cache_node_result(cache)
        lookup_node = build_client_instruction_cache_lookup_runtime_node_result(
            pipeline_context.client_instruction_cache_lookup_runtime_result
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
        if history_node is not None:
            _insert_after_node_result(
                pipeline_context.node_results,
                history_node,
                after_node_name=(
                    "client_instruction_cache_lookup"
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
    """Move one already-recorded runtime node behind its semantic predecessor."""

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


def extract_response_text(body: Any) -> str | None:
    """Extract compact text from common OpenAI-compatible responses."""

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
    text = first.get("text")
    return text if isinstance(text, str) else None
