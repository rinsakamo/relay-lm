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
    runtime_ctx_injection_result: dict[str, Any] | None = None
    runtime_snippet_injection_result: dict[str, Any] | None = None
    relayctx_short_term_source_diagnostics: dict[str, Any] | None = None
    relayctx_short_term_extraction_dry_run: dict[str, Any] | None = None
    relayrun_artifact: dict[str, Any] | None = None

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
        if self.relayrun_artifact:
            run_id = self.relayrun_artifact.get("run_id")
            if isinstance(run_id, str) and run_id:
                headers["x-relaylm-run-id"] = run_id
            run_status = self.relayrun_artifact.get("run_status")
            if isinstance(run_status, str) and run_status:
                headers["x-relaylm-run-status"] = run_status
            resume_mode = self.relayrun_artifact.get("resume_mode")
            if isinstance(resume_mode, str) and resume_mode:
                headers["x-relaylm-resume-mode"] = resume_mode
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


def _content_text_parts(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [
            item["text"]
            for item in content
            if isinstance(item, dict)
            and item.get("type") == "text"
            and isinstance(item.get("text"), str)
        ]
    return []


def _content_text_length(content: Any) -> int:
    return sum(len(part) for part in _content_text_parts(content))


def _content_text(content: Any) -> str:
    return "\n".join(_content_text_parts(content))


def build_relayctx_short_term_source_diagnostics(
    *,
    messages: list[dict[str, Any]],
    enabled: bool = False,
    memory_source: str | None = None,
    relaymem_retrieval_artifact: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build content-free RelayCTX short-term source diagnostics.

    The artifact only records source names, counts, and character lengths from
    inbound OpenWebUI/OpenAI-compatible messages. It does not store, restore,
    rewrite, compress, or inject short-term context and intentionally excludes
    message text, prompt text, snippet text, backend payloads, and final text.
    """

    if not enabled:
        return None

    safe_messages = [message for message in messages if isinstance(message, dict)]
    openwebui_message_count = len(safe_messages)
    recent_user_messages = [
        message for message in safe_messages if message.get("role") == "user"
    ]
    recent_assistant_messages = [
        message for message in safe_messages if message.get("role") == "assistant"
    ]
    latest_user_message = recent_user_messages[-1] if recent_user_messages else None
    latest_user_content = (
        latest_user_message.get("content")
        if isinstance(latest_user_message, dict)
        else None
    )
    latest_user_message_chars = _content_text_length(latest_user_content)
    short_term_candidate_count = len(recent_user_messages) + len(recent_assistant_messages)
    short_term_candidate_present = short_term_candidate_count > 0
    retrieval_candidates = None
    if isinstance(relaymem_retrieval_artifact, dict):
        selected_mem_candidates = relaymem_retrieval_artifact.get(
            "selected_mem_candidates"
        )
        if isinstance(selected_mem_candidates, list):
            retrieval_candidates = len(selected_mem_candidates)

    return {
        "schema_version": "relayctx_short_term_source_diagnostics.v0",
        "diagnostics_only": True,
        "enabled": True,
        "content_free": True,
        "short_term_storage_attempted": False,
        "short_term_restore_attempted": False,
        "short_term_injection_attempted": False,
        "openwebui_messages_present": openwebui_message_count > 0,
        "openwebui_message_count": openwebui_message_count,
        "openwebui_recent_user_count": len(recent_user_messages),
        "openwebui_recent_assistant_count": len(recent_assistant_messages),
        "latest_user_message_present": latest_user_message is not None,
        "latest_user_message_chars": latest_user_message_chars,
        "short_term_candidate_present": short_term_candidate_present,
        "short_term_candidate_count": short_term_candidate_count,
        "short_term_source": "openwebui_messages"
        if openwebui_message_count > 0
        else "none",
        "source_registry": {
            "openwebui_messages": {
                "present": openwebui_message_count > 0,
                "message_count": openwebui_message_count,
            },
            "memory_seed": {
                "present": memory_source is not None,
                "source_name": memory_source,
            },
            "relaymem_retrieval": {
                "present": isinstance(relaymem_retrieval_artifact, dict),
                "candidate_count": retrieval_candidates,
            },
            "relayctx_short_term": {
                "present": short_term_candidate_present,
                "source": "openwebui_messages"
                if short_term_candidate_present
                else "none",
            },
        },
        "safety": {
            "contains_user_content": False,
            "contains_backend_payload": False,
            "contains_response_text": False,
            "contains_prompt_text": False,
            "contains_snippet_text": False,
            "contains_final_text": False,
            "stores_short_term_context": False,
            "restores_cross_thread_context": False,
            "rewrites_openwebui_messages": False,
            "compresses_openwebui_messages": False,
            "backend_payload_mutation_allowed": False,
            "response_body_mutation_allowed": False,
        },
    }


def build_relayctx_short_term_extraction_dry_run(
    *,
    messages: list[dict[str, Any]],
    enabled: bool = False,
    memory_source: str | None = None,
) -> dict[str, Any] | None:
    """Build content-free RelayCTX short-term extraction dry-run diagnostics.

    This deterministic dry-run only classifies OpenWebUI message text into
    aggregate candidate counts. It never stores, restores, injects, rewrites,
    compresses, or copies message content into the artifact.
    """

    if not enabled:
        return None

    safe_messages = [message for message in messages if isinstance(message, dict)]
    user_messages = [message for message in safe_messages if message.get("role") == "user"]
    assistant_messages = [
        message for message in safe_messages if message.get("role") == "assistant"
    ]
    latest_user_message = user_messages[-1] if user_messages else None
    latest_user_content = (
        latest_user_message.get("content")
        if isinstance(latest_user_message, dict)
        else None
    )

    temporary_fact_candidate_count = 0
    temporary_preference_candidate_count = 0
    instruction_candidate_count = 0
    override_candidate_count = 0
    contradiction_candidate_count = 0

    for message in user_messages:
        text = _content_text(message.get("content"))
        if not text:
            continue
        lowered = text.lower()
        if _looks_like_temporary_fact(text, lowered):
            temporary_fact_candidate_count += 1
        if _looks_like_temporary_preference(text, lowered):
            temporary_preference_candidate_count += 1
        if _looks_like_instruction(text, lowered):
            instruction_candidate_count += 1
        if _looks_like_override(text, lowered):
            override_candidate_count += 1
        if _looks_like_contradiction(text, lowered, memory_source=memory_source):
            contradiction_candidate_count += 1

    short_term_candidate_count = (
        temporary_fact_candidate_count
        + temporary_preference_candidate_count
        + instruction_candidate_count
        + override_candidate_count
        + contradiction_candidate_count
    )
    message_count = len(safe_messages)
    blocked_reasons = [] if message_count > 0 else ["no_openwebui_messages"]

    return {
        "schema_version": "relayctx_short_term_extraction_dry_run.v0",
        "enabled": True,
        "dry_run_only": True,
        "applied": False,
        "source": "openwebui_messages",
        "extraction_attempted": message_count > 0,
        "message_count": message_count,
        "user_message_count": len(user_messages),
        "assistant_message_count": len(assistant_messages),
        "latest_user_message_present": latest_user_message is not None,
        "latest_user_message_chars": _content_text_length(latest_user_content),
        "temporary_fact_candidate_count": temporary_fact_candidate_count,
        "temporary_preference_candidate_count": temporary_preference_candidate_count,
        "instruction_candidate_count": instruction_candidate_count,
        "override_candidate_count": override_candidate_count,
        "contradiction_candidate_count": contradiction_candidate_count,
        "short_term_candidate_count": short_term_candidate_count,
        "persistence_allowed": False,
        "restore_allowed": False,
        "injection_allowed": False,
        "backend_payload_mutation_allowed": False,
        "response_mutation_allowed": False,
        "content_free": True,
        "blocked_reasons": blocked_reasons,
    }


def _looks_like_temporary_fact(text: str, lowered: str) -> bool:
    del lowered
    markers = (
        "今日の合言葉",
        "合言葉は",
        "この会話内だけ",
        "この会話だけ",
        "今回だけ",
        "一時情報",
    )
    return any(marker in text for marker in markers)


def _looks_like_temporary_preference(text: str, lowered: str) -> bool:
    markers = ("好み", "prefer", "preference")
    if any(marker in lowered for marker in markers):
        return True
    return "今日は" in text and ("ではなく" in text or "冷たい" in text or "温かい" in text)


def _looks_like_instruction(text: str, lowered: str) -> bool:
    markers = ("優先してください", "この一時設定", "指示", "instruction", "follow this")
    return any(marker in text or marker in lowered for marker in markers)


def _looks_like_override(text: str, lowered: str) -> bool:
    markers = ("優先", "ではなく", "上書き", "override", "instead")
    return any(marker in text or marker in lowered for marker in markers)


def _looks_like_contradiction(
    text: str,
    lowered: str,
    *,
    memory_source: str | None,
) -> bool:
    del memory_source
    markers = ("ではなく", "矛盾", "contradict", "not ")
    return any(marker in text or marker in lowered for marker in markers)


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
