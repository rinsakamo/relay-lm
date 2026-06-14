"""Runtime trace writing helpers for RelayLM MVP-3."""

from __future__ import annotations

from typing import Any

from relaylm.client_instruction_cache import (
    build_client_instruction_cache_dry_run,
    build_client_instruction_cache_node_result,
)
from relaylm.client_instruction_cache_lookup_runtime import (
    build_client_instruction_cache_lookup_runtime_node_result,
)
from relaylm.client_history_exclusion_preflight import (
    build_client_history_exclusion_preflight_node_result,
    client_message_canonicalization_dependency_enabled,
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
    messages: list[dict[str, Any]] | None = None,
    message_count: int | None = None,
    response_text: str | None = None,
    response_present: bool | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Append one runtime trace record when tracing is enabled.

    Returns whether a record was written. Trace writing and PipelineNodeResult
    recording are best-effort and must never change request handling behavior.
    """

    pipeline_node_results: list[dict[str, Any]] | None = None
    pipeline_context = consume_active_pipeline_context()
    if pipeline_context is not None:
        try:
            managed_route = pipeline_context.route.mode_applied != "pass_through"
            instruction_dependency_enabled = (
                client_instruction_identity_dependency_enabled(pipeline_context.route)
            )
            client_message_canonicalization_dry_run = (
                build_client_message_canonicalization_dry_run(
                    pipeline_context.original_payload,
                    enabled=client_message_canonicalization_dependency_enabled(
                        pipeline_context.route
                    ),
                    managed_route=managed_route,
                )
            )
            client_message_canonicalization_node_result = (
                build_client_message_canonicalization_node_result(
                    client_message_canonicalization_dry_run
                )
            )
            if client_message_canonicalization_node_result is not None:
                pipeline_context.node_results.insert(
                    0,
                    client_message_canonicalization_node_result,
                )

            client_instruction_extraction_dry_run = (
                build_client_instruction_extraction_dry_run(
                    pipeline_context.original_payload,
                    enabled=instruction_dependency_enabled,
                    managed_route=managed_route,
                )
            )
            client_instruction_extraction_node_result = (
                build_client_instruction_extraction_node_result(
                    client_instruction_extraction_dry_run
                )
            )
            client_instruction_fingerprint_dry_run = (
                build_client_instruction_fingerprint_dry_run(
                    client_instruction_extraction_dry_run,
                    enabled=instruction_dependency_enabled,
                )
            )
            client_instruction_fingerprint_node_result = (
                build_client_instruction_fingerprint_node_result(
                    client_instruction_fingerprint_dry_run
                )
            )
            client_instruction_identity_node_result = (
                build_client_instruction_identity_runtime_node_result(
                    pipeline_context.client_instruction_identity_result
                )
            )
            client_instruction_cache_dry_run = build_client_instruction_cache_dry_run(
                client_instruction_fingerprint_dry_run,
                enabled=instruction_dependency_enabled,
                lookup_requested=(
                    pipeline_context.route.client_instruction_cache_lookup_enabled
                ),
                save_requested=False,
            )
            client_instruction_cache_node_result = (
                build_client_instruction_cache_node_result(
                    client_instruction_cache_dry_run
                )
            )
            client_instruction_cache_lookup_node_result = (
                build_client_instruction_cache_lookup_runtime_node_result(
                    pipeline_context.client_instruction_cache_lookup_runtime_result
                )
            )
            client_history_exclusion_preflight_node_result = (
                build_client_history_exclusion_preflight_node_result(
                    pipeline_context.client_history_exclusion_preflight_result
                )
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
            if client_instruction_extraction_node_result is not None:
                _insert_after_node_result(
                    pipeline_context.node_results,
                    client_instruction_extraction_node_result,
                    after_node_name="client_message_canonicalization",
                )
            if client_instruction_fingerprint_node_result is not None:
                _insert_after_node_result(
                    pipeline_context.node_results,
                    client_instruction_fingerprint_node_result,
                    after_node_name="client_instruction_extraction",
                )
            if client_instruction_identity_node_result is not None:
                _insert_after_node_result(
                    pipeline_context.node_results,
                    client_instruction_identity_node_result,
                    after_node_name="client_instruction_fingerprint",
                )
            if client_instruction_cache_node_result is not None:
                cache_after_node = (
                    "client_instruction_identity"
                    if client_instruction_identity_node_result is not None
                    else "client_instruction_fingerprint"
                )
                _insert_after_node_result(
                    pipeline_context.node_results,
                    client_instruction_cache_node_result,
                    after_node_name=cache_after_node,
                )
            if client_instruction_cache_lookup_node_result is not None:
                _insert_after_node_result(
                    pipeline_context.node_results,
                    client_instruction_cache_lookup_node_result,
                    after_node_name="client_instruction_cache",
                )
            if client_history_exclusion_preflight_node_result is not None:
                preflight_after_node = (
                    "client_instruction_cache_lookup"
                    if client_instruction_cache_lookup_node_result is not None
                    else "client_instruction_cache"
                    if client_instruction_cache_node_result is not None
                    else "client_message_canonicalization"
                )
                _insert_after_node_result(
                    pipeline_context.node_results,
                    client_history_exclusion_preflight_node_result,
                    after_node_name=preflight_after_node,
                )
            pipeline_node_results = pipeline_context.node_results_to_log_dicts()
        except Exception:
            pipeline_node_results = None

    if not config.trace.enabled or not config.trace.path:
        return False

    try:
        trace_metadata = dict(metadata or {})
        if pipeline_node_results is not None:
            trace_metadata["pipeline_node_results"] = pipeline_node_results
        if diagnostics.memory_source is not None:
            trace_metadata["memory_source"] = diagnostics.memory_source
        if diagnostics.memory_selection_summary is not None:
            trace_metadata["memory_selection_summary"] = diagnostics.memory_selection_summary
        if diagnostics.memory_block_assembly is not None:
            trace_metadata["memory_block_assembly"] = diagnostics.memory_block_assembly
        if diagnostics.token_memory_dry_run is not None:
            trace_metadata["token_memory_dry_run"] = diagnostics.token_memory_dry_run
        if diagnostics.token_policy_signal is not None:
            trace_metadata["token_policy_signal"] = diagnostics.token_policy_signal
        if diagnostics.token_policy_decision is not None:
            trace_metadata["token_policy_decision"] = diagnostics.token_policy_decision
        if diagnostics.token_policy_readiness is not None:
            trace_metadata["token_policy_readiness"] = diagnostics.token_policy_readiness
        if diagnostics.token_budget_truncation is not None:
            trace_metadata["token_budget_truncation"] = diagnostics.token_budget_truncation
        if diagnostics.stable_prefix_hash is not None:
            trace_metadata["stable_prefix_hash"] = diagnostics.stable_prefix_hash
        if diagnostics.stable_prefix_block_ids is not None:
            trace_metadata["stable_prefix_block_ids"] = diagnostics.stable_prefix_block_ids
        if diagnostics.memory_adapter_dry_run is not None:
            trace_metadata["memory_adapter_dry_run"] = diagnostics.memory_adapter_dry_run
        if diagnostics.memory_adapter_readiness is not None:
            trace_metadata["memory_adapter_readiness"] = diagnostics.memory_adapter_readiness
        if diagnostics.memory_adapter_conflicts is not None:
            trace_metadata["memory_adapter_conflicts"] = diagnostics.memory_adapter_conflicts
        if diagnostics.context_block_summary is not None:
            trace_metadata["context_block_summary"] = diagnostics.context_block_summary
        if diagnostics.persona_source_budget_diagnostics is not None:
            trace_metadata["persona_source_budget_diagnostics"] = diagnostics.persona_source_budget_diagnostics
        if diagnostics.request_scope_identity is not None:
            trace_metadata["request_scope_identity"] = diagnostics.request_scope_identity
        if diagnostics.scope_resolution_diagnostics is not None:
            trace_metadata["scope_resolution_diagnostics"] = diagnostics.scope_resolution_diagnostics
        if diagnostics.memory_adapter_shadow_dry_run is not None:
            trace_metadata["memory_adapter_shadow_dry_run"] = diagnostics.memory_adapter_shadow_dry_run
        if diagnostics.memory_adapter_shadow_readiness is not None:
            trace_metadata["memory_adapter_shadow_readiness"] = diagnostics.memory_adapter_shadow_readiness
        if diagnostics.memory_adapter_shadow_conflicts is not None:
            trace_metadata["memory_adapter_shadow_conflicts"] = diagnostics.memory_adapter_shadow_conflicts
        if diagnostics.memory_adapter_shadow_delta is not None:
            trace_metadata["memory_adapter_shadow_delta"] = diagnostics.memory_adapter_shadow_delta
        if diagnostics.relaysoul_runtime_feedback_summary is not None:
            trace_metadata["relaysoul_runtime_feedback_summary"] = diagnostics.relaysoul_runtime_feedback_summary
        if diagnostics.relayint_fast_path_dry_run is not None:
            trace_metadata["relayint_fast_path_dry_run"] = (
                diagnostics.relayint_fast_path_dry_run
            )
        if diagnostics.relayint_quick_clarification_preflight is not None:
            trace_metadata["relayint_quick_clarification_preflight"] = (
                diagnostics.relayint_quick_clarification_preflight
            )
        if diagnostics.relayint_quick_clarification_apply_plan is not None:
            trace_metadata["relayint_quick_clarification_apply_plan"] = (
                diagnostics.relayint_quick_clarification_apply_plan
            )
        if diagnostics.compile_decision_dry_run is not None:
            trace_metadata["compile_decision_dry_run"] = diagnostics.compile_decision_dry_run
        if diagnostics.relayemo_artifact is not None:
            trace_metadata["relayemo_artifact"] = diagnostics.relayemo_artifact
        if diagnostics.relayscn_scene_policy_artifact is not None:
            trace_metadata["relayscn_scene_policy_artifact"] = (
                diagnostics.relayscn_scene_policy_artifact
            )
        if diagnostics.relayref_artifact is not None:
            trace_metadata["relayref_artifact"] = diagnostics.relayref_artifact
        if diagnostics.relaymem_retrieval_artifact is not None:
            trace_metadata["relaymem_retrieval_artifact"] = (
                diagnostics.relaymem_retrieval_artifact
            )
            evidence_envelope = diagnostics.relaymem_retrieval_artifact.get(
                "evidence_envelope"
            )
            if evidence_envelope is not None:
                trace_metadata["evidence_envelope"] = evidence_envelope
        if diagnostics.runtime_ctx_injection_result is not None:
            trace_metadata["runtime_ctx_injection_result"] = (
                diagnostics.runtime_ctx_injection_result
            )
        if diagnostics.runtime_snippet_injection_result is not None:
            trace_metadata["runtime_snippet_injection_result"] = (
                diagnostics.runtime_snippet_injection_result
            )
        if diagnostics.relayctx_short_term_source_diagnostics is not None:
            trace_metadata["relayctx_short_term_source_diagnostics"] = (
                diagnostics.relayctx_short_term_source_diagnostics
            )
        if diagnostics.relayctx_short_term_extraction_dry_run is not None:
            trace_metadata["relayctx_short_term_extraction_dry_run"] = (
                diagnostics.relayctx_short_term_extraction_dry_run
            )
        if diagnostics.relayctx_short_term_block_assembly_dry_run is not None:
            trace_metadata["relayctx_short_term_block_assembly_dry_run"] = (
                diagnostics.relayctx_short_term_block_assembly_dry_run
            )
        if diagnostics.relayctx_short_term_runtime_injection_preflight is not None:
            trace_metadata["relayctx_short_term_runtime_injection_preflight"] = (
                diagnostics.relayctx_short_term_runtime_injection_preflight
            )
        if diagnostics.relayctx_short_term_runtime_injection_apply_result is not None:
            trace_metadata["relayctx_short_term_runtime_injection_apply_result"] = (
                diagnostics.relayctx_short_term_runtime_injection_apply_result
            )
        if diagnostics.relayrun_artifact is not None:
            trace_metadata["relayrun_artifact"] = diagnostics.relayrun_artifact
        record = build_trace_record(
            trace_id=diagnostics.request_id,
            character_id=diagnostics.character_id,
            route_model=diagnostics.route_model,
            mode_applied=diagnostics.mode_applied,
            compiler_used=diagnostics.compiler_used,
            message_count=message_count if message_count is not None else len(messages or []),
            response_present=(
                response_present
                if response_present is not None
                else isinstance(response_text, str)
            ),
            metadata=trace_metadata,
        )
        append_trace_record(config.trace.path, record)
    except Exception:
        return False
    return True


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


def extract_response_text(body: Any) -> str | None:
    """Extract a compact text field from common OpenAI-compatible responses."""

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
    if isinstance(text, str):
        return text
    return None
