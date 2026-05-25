"""Runtime trace writing helpers for RelayLM MVP-3."""

from __future__ import annotations

from typing import Any

from relaylm.config import RelayLMConfig
from relaylm.diagnostics import RequestDiagnostics
from relaylm.trace import append_trace_record, build_trace_record


def trace_runtime_event(
    *,
    config: RelayLMConfig,
    diagnostics: RequestDiagnostics,
    messages: list[dict[str, Any]],
    response_text: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Append one runtime trace record when tracing is enabled.

    Returns whether a record was written. Trace writing is best-effort and must
    never change request handling behavior.
    """

    if not config.trace.enabled or not config.trace.path:
        return False

    try:
        trace_metadata = dict(metadata or {})
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
        record = build_trace_record(
            trace_id=diagnostics.request_id,
            character_id=diagnostics.character_id,
            route_model=diagnostics.route_model,
            mode_applied=diagnostics.mode_applied,
            compiler_used=diagnostics.compiler_used,
            messages=messages,
            response_text=response_text,
            metadata=trace_metadata,
        )
        append_trace_record(config.trace.path, record)
    except Exception:
        return False
    return True


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
