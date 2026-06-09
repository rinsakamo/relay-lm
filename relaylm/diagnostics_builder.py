"""Diagnostics builder helpers for RelayLM pipeline separation."""

from __future__ import annotations

from typing import Any

from relaylm.diagnostics import RequestDiagnostics


def build_base_request_diagnostics(**kwargs: Any) -> RequestDiagnostics:
    """Build the base request diagnostics artifact.

    This helper is intentionally thin for the first diagnostics-builder split.
    Keeping the argument shape identical to RequestDiagnostics lets app.py move
    diagnostics construction behind a stable module boundary without changing
    runtime behavior.
    """

    return RequestDiagnostics(**kwargs)
    

def compiled_request_diagnostics_kwargs(compiled_request: Any) -> dict[str, Any]:
    """Return RequestDiagnostics kwargs derived from compiled_request."""

    return {
        "compiler_used": compiled_request.compiler_used,
        "memory_block_used": compiled_request.memory_block_used,
        "memory_source": compiled_request.memory_source,
        "memory_selection_summary": (
            compiled_request.memory_selection_summary.to_log_dict()
            if compiled_request.memory_selection_summary is not None
            else None
        ),
        "memory_block_assembly": (
            compiled_request.memory_block_assembly.to_log_dict()
            if compiled_request.memory_block_assembly is not None
            else None
        ),
        "token_memory_dry_run": compiled_request.token_memory_dry_run,
        "stable_prefix_hash": compiled_request.stable_prefix_hash,
        "stable_prefix_block_ids": compiled_request.stable_prefix_block_ids,
        "memory_adapter_dry_run": compiled_request.memory_adapter_dry_run,
        "memory_adapter_readiness": compiled_request.memory_adapter_readiness,
        "memory_adapter_conflicts": compiled_request.memory_adapter_conflicts,
        "context_block_summary": compiled_request.context_block_summary,
        "persona_source_budget_diagnostics": (
            compiled_request.persona_source_budget_diagnostics
        ),
        "profile_compile_dry_run_enabled": compiled_request.plan.enabled,
        "profile_compile_fallback_reason": compiled_request.plan.fallback_reason,
    }


def token_policy_diagnostics_kwargs(
    *,
    token_policy_signal: Any,
    token_policy_decision: Any,
    token_policy_readiness: Any,
    token_budget_truncation: Any,
) -> dict[str, Any]:
    """Return RequestDiagnostics kwargs derived from token policy artifacts."""

    return {
        "token_policy_signal": token_policy_signal.to_log_dict(),
        "token_policy_decision": token_policy_decision.to_log_dict(),
        "token_policy_readiness": token_policy_readiness.to_log_dict(),
        "token_budget_truncation": token_budget_truncation,
    }


def request_scope_diagnostics_kwargs(
    *,
    request_scope_identity: Any,
    scope_resolution_diagnostics: Any,
) -> dict[str, Any]:
    """Return RequestDiagnostics kwargs derived from request scope artifacts."""

    return {
        "request_scope_identity": request_scope_identity.to_log_dict(),
        "scope_resolution_diagnostics": scope_resolution_diagnostics.to_log_dict(),
    }


def memory_adapter_shadow_diagnostics_kwargs(
    *,
    memory_adapter_shadow_dry_run: Any,
    memory_adapter_shadow_readiness: Any,
    memory_adapter_shadow_conflicts: Any,
    memory_adapter_shadow_delta: Any,
) -> dict[str, Any]:
    """Return RequestDiagnostics kwargs derived from memory adapter shadow artifacts."""

    return {
        "memory_adapter_shadow_dry_run": memory_adapter_shadow_dry_run,
        "memory_adapter_shadow_readiness": memory_adapter_shadow_readiness,
        "memory_adapter_shadow_conflicts": memory_adapter_shadow_conflicts,
        "memory_adapter_shadow_delta": memory_adapter_shadow_delta,
    }


def relayint_runtime_diagnostics_kwargs(
    *,
    relayint_fast_path_dry_run: Any,
    relayint_quick_clarification_preflight: Any,
    trace_enabled: bool,
    compile_decision_dry_run: Any,
) -> dict[str, Any]:
    """Return RequestDiagnostics kwargs derived from RelayINT/runtime artifacts."""

    return {
        "relayint_fast_path_dry_run": relayint_fast_path_dry_run,
        "relayint_quick_clarification_preflight": relayint_quick_clarification_preflight,
        "trace_enabled": trace_enabled,
        "compile_decision_dry_run": compile_decision_dry_run,
    }


def runtime_artifact_diagnostics_kwargs(
    *,
    relayemo_artifact: Any,
    relayscn_scene_policy_artifact: Any,
    relayref_artifact: Any,
    relaymem_retrieval_artifact: Any,
    runtime_ctx_injection_result: Any,
    runtime_snippet_injection_result: Any,
) -> dict[str, Any]:
    """Return RequestDiagnostics kwargs derived from runtime artifacts."""

    return {
        "relayemo_artifact": relayemo_artifact,
        "relayscn_scene_policy_artifact": relayscn_scene_policy_artifact,
        "relayref_artifact": relayref_artifact,
        "relaymem_retrieval_artifact": relaymem_retrieval_artifact,
        "runtime_ctx_injection_result": runtime_ctx_injection_result,
        "runtime_snippet_injection_result": runtime_snippet_injection_result,
    }
