"""RelayMEM Retrieval MVP dry-run artifact helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.relaymem_store import discover_relaymem_page_candidates


KNOWN_SCENE_TYPES = {
    "casual_chat",
    "design_talk",
    "implementation_work",
    "review_work",
    "formal_document",
    "medical_or_safety",
    "system_ops",
    "vtuber_roleplay",
    "recovery",
}
_RETRIEVAL_ELIGIBLE_FALLBACK_REASONS = {
    "memory_store_read_only_dry_run",
    "memory_store_read_only_selection_dry_run",
    "memory_store_files_blocked",
    "memory_store_validation_truncated",
    "memory_store_scan_truncated",
}


def build_relaymem_retrieval_dry_run_artifact(
    *,
    relayscn_scene_policy_artifact: Mapping[str, Any] | None,
    relayref_artifact: Mapping[str, Any] | None = None,
    messages: Sequence[Mapping[str, Any]] | None = None,
    token_budget: int | None = None,
    store_diagnostics: Mapping[str, Any] | None = None,
    max_candidates: int = 3,
    ctx_block_apply_enabled: bool = False,
) -> dict[str, Any]:
    """Build a diagnostics-only RelayMEM runtime retrieval artifact."""

    messages = messages or []
    parsed_scn = _parse_relayscn_artifact(relayscn_scene_policy_artifact)
    scene_type = parsed_scn["scene_type"]
    retrieval_scope = parsed_scn["retrieval_scope"]
    persistence_block = parsed_scn["persistence_block"]
    persistence_block_reasons = parsed_scn["persistence_block_reasons"]
    relayref_unresolved = _relayref_unresolved_reference(relayref_artifact)

    fallback_reason = _resolve_fallback_reason(
        malformed=parsed_scn["malformed"],
        scene_type=scene_type,
        retrieval_scope=retrieval_scope,
        relayref_unresolved=relayref_unresolved,
        store_diagnostics=store_diagnostics,
    )
    normalized_token_budget = _normalize_token_budget(token_budget)
    selected_mem_candidates, discovery_blocked = _select_mem_candidates_dry_run(
        fallback_reason=fallback_reason,
        store_diagnostics=store_diagnostics,
        query_terms=_term_hints(_latest_user_text(messages)),
        max_candidates=max_candidates,
    )
    ctx_block_candidate = _build_ctx_block_candidate(
        selected_mem_candidates=selected_mem_candidates,
        token_limit=normalized_token_budget["limit"],
    )
    apply_readiness = _build_apply_readiness(
        malformed=parsed_scn["malformed"],
        scene_type=scene_type,
        retrieval_scope=retrieval_scope,
        relayref_unresolved=relayref_unresolved,
        ctx_block_candidate=ctx_block_candidate,
        retrieval_dry_run_only=_retrieval_dry_run_only(store_diagnostics),
        ctx_block_apply_enabled=ctx_block_apply_enabled,
    )
    ctx_injection_plan = _build_ctx_injection_plan(
        ctx_block_candidate=ctx_block_candidate,
        apply_decision=apply_readiness["apply_decision"],
        apply_blocked_reasons=apply_readiness["apply_blocked_reasons"],
    )
    blocked = _build_blocked_reasons(
        fallback_reason=fallback_reason,
        scene_type=scene_type,
        relayref_unresolved=relayref_unresolved,
        discovery_blocked=discovery_blocked,
    )
    used_tokens = sum(
        int(candidate.get("estimated_tokens", 0))
        for candidate in selected_mem_candidates
    )

    return {
        "artifact_version": "relaymem_retrieval.v0",
        "diagnostics_only": True,
        "apply_allowed": False,
        "retrieval_scope": retrieval_scope,
        "scene_type": scene_type,
        "query_summary": _build_query_summary(messages),
        "selected": [],
        "selected_mem_candidates": selected_mem_candidates,
        "blocked": blocked,
        "ctx_block": None,
        "ctx_block_candidate": ctx_block_candidate,
        "ctx_injection_plan": ctx_injection_plan,
        "fallback_reason": fallback_reason,
        "token_budget": normalized_token_budget,
        "used_tokens": used_tokens,
        "persistence_block": persistence_block,
        "persistence_block_reasons": persistence_block_reasons,
        "apply_decision": apply_readiness["apply_decision"],
        "apply_readiness_score": apply_readiness["apply_readiness_score"],
        "apply_blocked_reasons": apply_readiness["apply_blocked_reasons"],
        "apply_preconditions": apply_readiness["apply_preconditions"],
        "store_diagnostics": (
            dict(store_diagnostics) if isinstance(store_diagnostics, Mapping) else None
        ),
    }


def _parse_relayscn_artifact(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return _malformed_scene_policy()

    scene_state = artifact.get("scene_state")
    scene_policy = artifact.get("scene_policy")
    if not isinstance(scene_state, Mapping) or not isinstance(scene_policy, Mapping):
        return _malformed_scene_policy()

    scene_type = scene_state.get("scene_type")
    if not isinstance(scene_type, str) or not scene_type:
        scene_type = "unknown"
    if scene_type not in KNOWN_SCENE_TYPES:
        return _unsupported_scene_policy(scene_type)

    retrieval_scope = scene_policy.get("relaymem_retrieval_scope")
    if not isinstance(retrieval_scope, str) or not retrieval_scope:
        retrieval_scope = "current_context_only"

    persistence_reasons = artifact.get("persistence_block_reasons")
    return {
        "malformed": False,
        "scene_type": scene_type,
        "retrieval_scope": retrieval_scope,
        "persistence_block": artifact.get("persistence_block") is True,
        "persistence_block_reasons": _normalize_reasons(persistence_reasons),
    }


def _malformed_scene_policy() -> dict[str, Any]:
    return {
        "malformed": True,
        "scene_type": "unknown",
        "retrieval_scope": "current_context_only",
        "persistence_block": True,
        "persistence_block_reasons": ["malformed_relayscn_artifact"],
    }


def _unsupported_scene_policy(scene_type: str) -> dict[str, Any]:
    return {
        "malformed": False,
        "scene_type": "unknown",
        "retrieval_scope": "current_context_only",
        "persistence_block": True,
        "persistence_block_reasons": [f"unsupported_scene_type:{scene_type}"],
    }


def _resolve_fallback_reason(
    *,
    malformed: bool,
    scene_type: str,
    retrieval_scope: str,
    relayref_unresolved: bool,
    store_diagnostics: Mapping[str, Any] | None = None,
) -> str:
    if malformed or scene_type == "unknown":
        return "scene_policy_blocks_memory"
    if relayref_unresolved:
        return "unresolved_reference_requires_confirmation"
    if scene_type in {"formal_document", "medical_or_safety"}:
        return "external_memory_blocked_by_scene_policy"
    if retrieval_scope == "current_context_only":
        return "current_context_only_no_external_mem"
    store_reason = _store_fallback_reason(store_diagnostics)
    if store_reason is not None:
        return store_reason
    return "memory_store_not_configured"


def _build_blocked_reasons(
    *,
    fallback_reason: str,
    scene_type: str,
    relayref_unresolved: bool,
    discovery_blocked: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    if fallback_reason == "memory_store_not_configured":
        return []
    blocked = [{"reason": fallback_reason}]
    if scene_type in {"formal_document", "medical_or_safety"}:
        blocked.append({"reason": f"scene_type:{scene_type}"})
    if relayref_unresolved:
        blocked.append({"reason": "must_not_silently_resolve_ambiguous_reference"})
    blocked.extend(discovery_blocked or [])
    return blocked


def _select_mem_candidates_dry_run(
    *,
    fallback_reason: str,
    store_diagnostics: Mapping[str, Any] | None,
    query_terms: list[str],
    max_candidates: int,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if fallback_reason not in _RETRIEVAL_ELIGIBLE_FALLBACK_REASONS:
        return [], []
    if not isinstance(store_diagnostics, Mapping):
        return [], []
    root_path = store_diagnostics.get("root_path")
    if not isinstance(root_path, str) or not root_path:
        return [], []
    discovery = discover_relaymem_page_candidates(
        root_path=root_path,
        query_terms=query_terms,
        max_candidates=max(0, max_candidates),
    )
    candidates = []
    for candidate in discovery.get("candidates", []):
        if not isinstance(candidate, Mapping):
            continue
        dry_run_candidate = dict(candidate)
        estimated_chars = dry_run_candidate.get("estimated_chars")
        dry_run_candidate["estimated_tokens"] = (
            max(1, int(estimated_chars) // 4)
            if isinstance(estimated_chars, int) and estimated_chars > 0
            else 0
        )
        dry_run_candidate["applied_to_ctx"] = False
        candidates.append(dry_run_candidate)
    blocked = [
        {"path": str(item.get("path")), "reason": str(item.get("reason"))}
        for item in discovery.get("blocked_files", [])
        if isinstance(item, Mapping)
    ]
    discovery_reason = discovery.get("fallback_reason")
    if isinstance(discovery_reason, str) and discovery_reason not in {
        "memory_store_read_only_selection_dry_run",
    }:
        blocked.append({"reason": discovery_reason})
    return candidates, blocked


def _build_ctx_block_candidate(
    *,
    selected_mem_candidates: list[dict[str, Any]],
    token_limit: int | None,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    blocked: list[dict[str, str]] = []
    estimated_tokens = 0
    truncated = False

    for candidate in selected_mem_candidates:
        estimated = _candidate_estimated_tokens(candidate)
        path = str(candidate.get("path", ""))
        source = str(candidate.get("source", "mem_page"))
        reason = str(candidate.get("reason", "candidate_available"))
        would_exceed_budget = (
            token_limit is not None and estimated_tokens + estimated > token_limit
        )
        included = not would_exceed_budget
        if included:
            estimated_tokens += estimated
        else:
            truncated = True
            blocked.append({"path": path, "reason": "token_budget_exceeded"})
        entries.append(
            {
                "path": path,
                "source": source,
                "reason": reason,
                "estimated_tokens": estimated,
                "included": included,
                "truncated": would_exceed_budget,
                "applied_to_ctx": False,
            }
        )

    return {
        "schema_version": "relaymem.ctx_block_candidate.v0",
        "diagnostics_only": True,
        "applied_to_ctx": False,
        "source": "selected_mem_candidates",
        "budget": {
            "token_limit": token_limit,
            "estimated_tokens": estimated_tokens,
            "truncated": truncated,
        },
        "entries": entries,
        "blocked": blocked,
    }


def _candidate_estimated_tokens(candidate: Mapping[str, Any]) -> int:
    estimated_tokens = candidate.get("estimated_tokens")
    if isinstance(estimated_tokens, int) and estimated_tokens >= 0:
        return estimated_tokens
    estimated_chars = candidate.get("estimated_chars")
    if isinstance(estimated_chars, int) and estimated_chars > 0:
        return max(1, estimated_chars // 4)
    return 0


def _build_ctx_injection_plan(
    *,
    ctx_block_candidate: Mapping[str, Any],
    apply_decision: str,
    apply_blocked_reasons: Sequence[str],
) -> dict[str, Any]:
    included_entries = _included_ctx_candidate_entries(ctx_block_candidate)
    plan_eligible = apply_decision in {"dry_run_only", "eligible_but_not_applied"}
    preview_text = (
        _build_ctx_injection_preview(included_entries)
        if plan_eligible and included_entries
        else None
    )
    plan_source_entries = (
        _ctx_injection_source_entries(included_entries)
        if preview_text is not None
        else []
    )
    estimated_tokens = sum(
        _entry_estimated_tokens(entry) for entry in included_entries
    ) if preview_text else 0
    blocked_reasons = _ctx_injection_blocked_reasons(
        apply_decision=apply_decision,
        apply_blocked_reasons=apply_blocked_reasons,
        has_included_entries=bool(included_entries),
        plan_eligible=plan_eligible,
    )
    return {
        "schema_version": "relaymem.ctx_injection_plan.v0",
        "diagnostics_only": True,
        "applied": False,
        "payload_mutation_allowed": False,
        "target": "backend_messages",
        "insertion_point": "before_latest_user",
        "preview_text": preview_text,
        "estimated_tokens": estimated_tokens,
        "source": "ctx_block_candidate",
        "source_entries": plan_source_entries,
        "blocked_reasons": blocked_reasons,
    }


def _ctx_injection_source_entries(
    included_entries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "path": str(entry.get("path", "")),
            "reason": str(entry.get("reason", "candidate_available")),
            "estimated_tokens": _entry_estimated_tokens(entry),
        }
        for entry in included_entries
    ]


def _included_ctx_candidate_entries(
    ctx_block_candidate: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    entries = ctx_block_candidate.get("entries")
    if not isinstance(entries, Sequence) or isinstance(entries, str):
        return []
    return [
        entry
        for entry in entries
        if isinstance(entry, Mapping) and entry.get("included") is True
    ]


def _build_ctx_injection_preview(entries: Sequence[Mapping[str, Any]]) -> str:
    lines = ["[RelayMEM Context Candidate]"]
    for entry in entries:
        path = str(entry.get("path", ""))
        reason = str(entry.get("reason", "candidate_available"))
        lines.append(f"- {path} (reason: {reason})")
    lines.append("This block is diagnostics-only and was not injected.")
    return "\n".join(lines)


def _ctx_injection_blocked_reasons(
    *,
    apply_decision: str,
    apply_blocked_reasons: Sequence[str],
    has_included_entries: bool,
    plan_eligible: bool,
) -> list[str]:
    reasons: list[str] = []
    if not has_included_entries:
        reasons.append("ctx_block_candidate_has_no_included_entries")
    if not plan_eligible:
        reasons.append(apply_decision)
    reasons.extend(str(reason) for reason in apply_blocked_reasons)
    reasons.append("runtime_ctx_injection_not_implemented")
    reasons.append("backend_payload_mutation_disabled")
    return _dedupe_reasons(reasons)


def _entry_estimated_tokens(entry: Mapping[str, Any]) -> int:
    estimated = entry.get("estimated_tokens")
    if isinstance(estimated, int) and estimated >= 0:
        return estimated
    return 0


def _build_apply_readiness(
    *,
    malformed: bool,
    scene_type: str,
    retrieval_scope: str,
    relayref_unresolved: bool,
    ctx_block_candidate: Mapping[str, Any],
    retrieval_dry_run_only: bool,
    ctx_block_apply_enabled: bool,
) -> dict[str, Any]:
    entries = ctx_block_candidate.get("entries")
    candidate_entries = entries if isinstance(entries, Sequence) else []
    included_entries = [
        entry
        for entry in candidate_entries
        if isinstance(entry, Mapping) and entry.get("included") is True
    ]
    budget = ctx_block_candidate.get("budget")
    budget_truncated = (
        isinstance(budget, Mapping) and budget.get("truncated") is True
    )
    scene_policy_blocks = (
        malformed
        or scene_type == "unknown"
        or retrieval_scope == "current_context_only"
        or scene_type in {"recovery", "formal_document", "medical_or_safety"}
    )
    preconditions = {
        "scene_policy_allows_apply": not scene_policy_blocks,
        "reference_resolved": not relayref_unresolved,
        "candidate_entries_present": bool(candidate_entries),
        "included_entries_present": bool(included_entries),
        "token_budget_allows_candidate": not budget_truncated,
        "retrieval_dry_run_only": bool(retrieval_dry_run_only),
        "ctx_block_apply_enabled": bool(ctx_block_apply_enabled),
        "ctx_block_injection_enabled": False,
        "backend_payload_mutation_allowed": False,
        "mem_soul_mutation_allowed": False,
    }

    if scene_policy_blocks:
        decision = "blocked_scene_policy"
    elif relayref_unresolved:
        decision = "blocked_unresolved_reference"
    elif not candidate_entries:
        decision = "blocked_no_candidates"
    elif budget_truncated:
        decision = "blocked_token_budget"
    elif not included_entries:
        decision = "blocked_no_candidates"
    elif retrieval_dry_run_only or not ctx_block_apply_enabled:
        decision = "dry_run_only"
    else:
        decision = "eligible_but_not_applied"

    blocked_reasons = _apply_blocked_reasons(decision, preconditions)
    return {
        "apply_decision": decision,
        "apply_readiness_score": _apply_readiness_score(preconditions),
        "apply_blocked_reasons": blocked_reasons,
        "apply_preconditions": preconditions,
    }


def _apply_blocked_reasons(decision: str, preconditions: Mapping[str, bool]) -> list[str]:
    if decision == "eligible_but_not_applied":
        return ["runtime_apply_not_implemented"]
    reasons: list[str] = [decision]
    if not preconditions.get("scene_policy_allows_apply", False):
        reasons.append("scene_policy_does_not_allow_apply")
    if not preconditions.get("reference_resolved", False):
        reasons.append("unresolved_reference_requires_confirmation")
    if not preconditions.get("candidate_entries_present", False):
        reasons.append("ctx_block_candidate_entries_empty")
    elif not preconditions.get("included_entries_present", False):
        reasons.append("ctx_block_candidate_has_no_included_entries")
    if not preconditions.get("token_budget_allows_candidate", False):
        reasons.append("token_budget_exceeded")
    if preconditions.get("retrieval_dry_run_only", True):
        reasons.append("retrieval_dry_run_only")
    if not preconditions.get("ctx_block_apply_enabled", False):
        reasons.append("ctx_block_apply_disabled")
    reasons.append("runtime_ctx_injection_not_implemented")
    return _dedupe_reasons(reasons)


def _apply_readiness_score(preconditions: Mapping[str, bool]) -> float:
    readiness_keys = (
        "scene_policy_allows_apply",
        "reference_resolved",
        "candidate_entries_present",
        "included_entries_present",
        "token_budget_allows_candidate",
        "ctx_block_apply_enabled",
    )
    passed = sum(1 for key in readiness_keys if preconditions.get(key) is True)
    return round(passed / len(readiness_keys), 3)


def _dedupe_reasons(reasons: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    return deduped


def _retrieval_dry_run_only(store_diagnostics: Mapping[str, Any] | None) -> bool:
    if not isinstance(store_diagnostics, Mapping):
        return True
    return store_diagnostics.get("retrieval_dry_run_only") is not False


def _store_fallback_reason(store_diagnostics: Mapping[str, Any] | None) -> str | None:
    if not isinstance(store_diagnostics, Mapping):
        return "memory_store_not_configured"
    reason = store_diagnostics.get("fallback_reason")
    if reason == "memory_store_disabled":
        return "memory_store_not_configured"
    if isinstance(reason, str) and reason:
        return reason
    return None


def _relayref_unresolved_reference(relayref_artifact: Mapping[str, Any] | None) -> bool:
    if not isinstance(relayref_artifact, Mapping):
        return False
    return relayref_artifact.get("unresolved_reference_detected") is True


def _build_query_summary(messages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    latest_user_text = _latest_user_text(messages)
    return {
        "source": "latest_user_message",
        "input_chars": len(latest_user_text),
        "term_hints": _term_hints(latest_user_text),
        "ambiguous_reference_terms_present": _has_ambiguous_reference(latest_user_text),
    }


def _latest_user_text(messages: Sequence[Mapping[str, Any]]) -> str:
    for message in reversed(messages):
        if not isinstance(message, Mapping) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, Sequence) and not isinstance(content, str):
            parts: list[str] = []
            for item in content:
                if isinstance(item, Mapping) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts)
    return ""


def _term_hints(text: str) -> list[str]:
    terms: list[str] = []
    for raw in text.replace("\n", " ").split(" "):
        term = raw.strip(".,!?。！？、:;()[]{}\"'")
        if len(term) < 3 or term in terms:
            continue
        terms.append(term[:32])
        if len(terms) >= 6:
            break
    return terms


def _has_ambiguous_reference(text: str) -> bool:
    lowered = text.lower()
    markers = (
        "which one",
        "what was that",
        "それ",
        "これ",
        "あれ",
        "さっき",
        "どっち",
        "どれ",
        "何の話",
        "わから",
    )
    return any(marker in lowered for marker in markers)


def _normalize_token_budget(token_budget: int | None) -> dict[str, Any]:
    if isinstance(token_budget, int) and token_budget > 0:
        return {"limit": token_budget, "source": "runtime_config"}
    return {"limit": None, "source": "unspecified"}


def _normalize_reasons(reasons: Any) -> list[str]:
    if isinstance(reasons, Sequence) and not isinstance(reasons, str):
        return [str(reason) for reason in reasons]
    return []
