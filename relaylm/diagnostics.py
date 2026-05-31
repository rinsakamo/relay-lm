"""Small diagnostics helpers for RelayLM MVP-0."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RequestDiagnostics:
    request_id: str
    route_model: str | None = None
    backend_model: str | None = None
    backend_name: str | None = None
    character_id: str | None = None
    mode_requested: str | None = None
    mode_applied: str | None = None
    stream_enabled: bool | None = None
    compiler_used: bool = False
    memory_block_used: bool = False
    memory_source: str | None = None
    memory_selection_summary: dict[str, Any] | None = None
    memory_block_assembly: dict[str, Any] | None = None
    token_memory_dry_run: dict[str, Any] | None = None
    token_policy_signal: dict[str, Any] | None = None
    token_policy_decision: dict[str, Any] | None = None
    token_policy_readiness: dict[str, Any] | None = None
    token_budget_truncation: dict[str, Any] | None = None
    stable_prefix_hash: str | None = None
    stable_prefix_block_ids: list[str] | None = None
    memory_adapter_dry_run: dict[str, Any] | None = None
    memory_adapter_readiness: dict[str, Any] | None = None
    memory_adapter_conflicts: dict[str, Any] | None = None
    context_block_summary: dict[str, Any] | None = None
    persona_source_budget_diagnostics: dict[str, Any] | None = None
    request_scope_identity: dict[str, Any] | None = None
    scope_resolution_diagnostics: dict[str, Any] | None = None
    memory_adapter_shadow_dry_run: dict[str, Any] | None = None
    memory_adapter_shadow_readiness: dict[str, Any] | None = None
    memory_adapter_shadow_conflicts: dict[str, Any] | None = None
    memory_adapter_shadow_delta: dict[str, Any] | None = None
    relaysoul_runtime_feedback_summary: dict[str, Any] | None = None
    trace_enabled: bool = False
    profile_compile_dry_run_enabled: bool | None = None
    profile_compile_fallback_reason: str | None = None
    fallback_reason: str | None = None
    compile_decision_dry_run: dict[str, Any] | None = None
    relayemo_artifact: dict[str, Any] | None = None
    relayscn_scene_policy_artifact: dict[str, Any] | None = None
    relayref_artifact: dict[str, Any] | None = None
    relaymem_retrieval_artifact: dict[str, Any] | None = None

    def to_headers(self) -> dict[str, str]:
        headers = {"x-relaylm-request-id": self.request_id}
        if self.mode_applied:
            headers["x-relaylm-mode"] = self.mode_applied
        headers["x-relaylm-compiler-used"] = "true" if self.compiler_used else "false"
        headers["x-relaylm-memory-block-used"] = "true" if self.memory_block_used else "false"
        if self.memory_source:
            headers["x-relaylm-memory-source"] = self.memory_source
        headers["x-relaylm-trace-enabled"] = "true" if self.trace_enabled else "false"
        if self.profile_compile_dry_run_enabled is not None:
            headers["x-relaylm-profile-compile-dry-run"] = (
                "true" if self.profile_compile_dry_run_enabled else "false"
            )
        if self.profile_compile_fallback_reason:
            headers["x-relaylm-profile-compile-fallback-reason"] = (
                self.profile_compile_fallback_reason
            )
        if self.fallback_reason:
            headers["x-relaylm-fallback-reason"] = self.fallback_reason
        return headers

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)


def build_relaysoul_runtime_feedback_summary(diagnostics: RequestDiagnostics) -> dict[str, object]:
    persona_budget = diagnostics.persona_source_budget_diagnostics or {}
    context_summary = diagnostics.context_block_summary or {}
    token_policy_readiness = diagnostics.token_policy_readiness or {}
    token_budget_truncation = diagnostics.token_budget_truncation or {}
    memory_adapter_conflicts = diagnostics.memory_adapter_conflicts or {}
    memory_adapter_readiness = diagnostics.memory_adapter_readiness or {}
    scope_resolution = diagnostics.scope_resolution_diagnostics or {}
    shadow_delta = diagnostics.memory_adapter_shadow_delta or {}

    warning_reasons: list[str] = []
    blocking_reasons: list[str] = []

    persona_budget_status = (
        persona_budget.get("budget_status")
        if isinstance(persona_budget.get("budget_status"), str)
        else None
    )
    persona_budget_warning_count = (
        persona_budget.get("source_warning_count")
        if isinstance(persona_budget.get("source_warning_count"), int)
        else 0
    )
    if persona_budget_status == "warning" or persona_budget_warning_count > 0:
        warning_reasons.append("persona_source_budget_warning")

    if memory_adapter_conflicts.get("conflict_status") == "warning":
        warning_reasons.append("memory_adapter_conflict_warning")
    if scope_resolution.get("resolution_status") == "conflict":
        warning_reasons.append("scope_resolution_conflict")
    if memory_adapter_readiness.get("blocked_reason") is not None:
        warning_reasons.append("memory_adapter_not_ready")
    if token_policy_readiness.get("ready_for_future_enforcement") is False:
        warning_reasons.append("token_policy_not_ready")

    if blocking_reasons:
        feedback_status = "blocked_candidate"
    elif warning_reasons:
        feedback_status = "warning"
    else:
        feedback_status = "ok"

    return {
        "feedback_status": feedback_status,
        "warning_reasons": warning_reasons,
        "blocking_reasons": blocking_reasons,
        "persona_budget_status": persona_budget_status,
        "persona_budget_warning_count": persona_budget_warning_count,
        "stable_prefix_hash_present": diagnostics.stable_prefix_hash is not None,
        "scene_state_present": bool(context_summary.get("scene_state_present")),
        "retrieved_memory_present": bool(context_summary.get("retrieved_memory_present")),
        "context_block_count": (
            context_summary.get("block_count")
            if isinstance(context_summary.get("block_count"), int)
            else None
        ),
        "token_policy_ready": token_policy_readiness.get("ready_for_future_enforcement")
        if isinstance(token_policy_readiness.get("ready_for_future_enforcement"), bool)
        else None,
        "token_truncation_applied": token_budget_truncation.get("applied")
        if isinstance(token_budget_truncation.get("applied"), bool)
        else None,
        "memory_adapter_conflict_status": memory_adapter_conflicts.get("conflict_status")
        if isinstance(memory_adapter_conflicts.get("conflict_status"), str)
        else None,
        "memory_adapter_readiness_blocked_reason": memory_adapter_readiness.get("blocked_reason")
        if isinstance(memory_adapter_readiness.get("blocked_reason"), str)
        else None,
        "scope_resolution_status": scope_resolution.get("resolution_status")
        if isinstance(scope_resolution.get("resolution_status"), str)
        else None,
        "shadow_delta_status": shadow_delta.get("delta_status")
        if isinstance(shadow_delta.get("delta_status"), str)
        else None,
    }


def build_compile_decision_dry_run(
    *,
    decision_id: str | None = None,
    plan_id: str | None = None,
    result_id: str | None = None,
    selected_route: str | None = None,
    selected_mode: str | None = None,
    backend: str | None = None,
    character_id: str | None = None,
    compiled_message_count: int | None = None,
    fallback_reason: str | None = None,
    blocking_reasons: list[str] | None = None,
    omitted_block_ids: list[str] | None = None,
    token_budget_status: str | None = None,
    decision_state: str = "COMPILE_DRY_RUN",
    apply_compiled_messages: bool = False,
    diagnostics_only: bool = True,
    schema_version: str = "mvp-ctx-apply-0",
) -> dict[str, Any]:
    """Build a compile decision dry-run diagnostics payload.

    This helper is fail-safe and never raises on missing/unknown values.
    It intentionally excludes prompt text and full messages.
    """

    safe_blocking_reasons = [str(x) for x in (blocking_reasons or [])]
    safe_omitted_block_ids = [str(x) for x in (omitted_block_ids or [])]

    safe_compiled_message_count: int | None
    if isinstance(compiled_message_count, int) and compiled_message_count >= 0:
        safe_compiled_message_count = compiled_message_count
    else:
        safe_compiled_message_count = None

    safe_decision_state = decision_state if isinstance(decision_state, str) else "COMPILE_DRY_RUN"
    safe_apply_compiled_messages = (
        apply_compiled_messages if isinstance(apply_compiled_messages, bool) else False
    )
    safe_diagnostics_only = diagnostics_only if isinstance(diagnostics_only, bool) else True

    return {
        "schema_version": schema_version,
        "decision_id": decision_id,
        "plan_id": plan_id,
        "result_id": result_id,
        "decision_state": safe_decision_state,
        "apply_compiled_messages": safe_apply_compiled_messages,
        "diagnostics_only": safe_diagnostics_only,
        "fallback_reason": fallback_reason,
        "blocking_reasons": safe_blocking_reasons,
        "selected_route": selected_route,
        "selected_mode": selected_mode,
        "backend": backend,
        "character_id": character_id,
        "compiled_message_count": safe_compiled_message_count,
        "omitted_block_ids": safe_omitted_block_ids,
        "token_budget_status": token_budget_status,
    }
