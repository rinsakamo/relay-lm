"""Deterministic Retrieval candidate discovery and readiness."""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any
from relaylm.retrieval.priority import prioritize_relaymem_candidates
from relaylm.relaymem_store import discover_relaymem_page_candidates
from relaylm.retrieval.query_analyzer import public_retrieval_query_projection
from relaylm.retrieval.snippet import _dedupe_reasons, _non_negative_int

_MAX_PRIORITY_DISCOVERY_CANDIDATES = 128
_RETRIEVAL_ELIGIBLE_FALLBACK_REASONS = {
    "memory_store_read_only_dry_run",
    "memory_store_read_only_selection_dry_run",
    "memory_store_files_blocked",
    "memory_store_validation_truncated",
    "memory_store_scan_truncated",
}


def _priority_discovery_cap(max_candidates: int) -> int:
    normalized = max(0, int(max_candidates))
    if normalized == 0:
        return 0
    return _MAX_PRIORITY_DISCOVERY_CANDIDATES


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

    final_limit = max(0, int(max_candidates))
    discovery_cap = _priority_discovery_cap(final_limit)
    discovery = discover_relaymem_page_candidates(
        root_path=root_path,
        query_terms=query_terms,
        max_candidates=discovery_cap,
        max_scan=discovery_cap,
    )
    candidates: list[dict[str, Any]] = []
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

    prioritized = prioritize_relaymem_candidates(candidates, max_candidates=final_limit)
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
    return list(prioritized["selected_candidates"]), blocked


def _attach_evidence_metadata_to_ctx_block_candidate(
    *,
    ctx_block_candidate: Mapping[str, Any],
    evidence_envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    candidate = dict(ctx_block_candidate)
    raw_entries = candidate.get("entries")
    if not isinstance(raw_entries, Sequence) or isinstance(raw_entries, str):
        candidate["entries"] = []
        return candidate

    snippets_by_key = _evidence_items_by_entry_key(
        evidence_envelope.get("snippets")
        if isinstance(evidence_envelope, Mapping)
        else None
    )
    blocked_by_key = _evidence_items_by_entry_key(
        evidence_envelope.get("blocked")
        if isinstance(evidence_envelope, Mapping)
        else None
    )
    entries: list[dict[str, Any]] = []
    for selected_index, raw_entry in enumerate(raw_entries):
        if not isinstance(raw_entry, Mapping):
            continue
        entry = dict(raw_entry)
        key = (str(entry.get("path", "")), selected_index)
        snippet = snippets_by_key.get(key)
        blocked = blocked_by_key.get(key)
        if snippet is not None:
            entry.update(
                {
                    "evidence_id": str(
                        snippet.get("evidence_id", f"evidence:{selected_index}")
                    ),
                    "snippet_available": True,
                    "evidence_kind": str(
                        snippet.get("evidence_kind", "bounded_page_snippet")
                    ),
                    "snippet_chars": _non_negative_int(snippet.get("snippet_chars")),
                    "snippet_estimated_tokens": _non_negative_int(
                        snippet.get("estimated_tokens")
                    ),
                    "snippet_included_in_runtime_prompt": False,
                }
            )
        else:
            evidence_id = None
            blocked_reason = None
            if blocked is not None:
                evidence_id = str(
                    blocked.get("evidence_id", f"evidence:{selected_index}")
                )
                blocked_reason = str(blocked.get("reason", "snippet_unavailable"))
            entry.update(
                {
                    "evidence_id": evidence_id,
                    "snippet_available": False,
                    "evidence_kind": "none",
                    "snippet_chars": 0,
                    "snippet_estimated_tokens": 0,
                    "snippet_included_in_runtime_prompt": False,
                }
            )
            if blocked_reason is not None:
                entry["evidence_blocked_reason"] = blocked_reason
        entries.append(entry)
    candidate["entries"] = entries
    return candidate


def _evidence_items_by_entry_key(
    raw_items: object,
) -> dict[tuple[str, int], Mapping[str, Any]]:
    if not isinstance(raw_items, Sequence) or isinstance(raw_items, str):
        return {}
    indexed: dict[tuple[str, int], Mapping[str, Any]] = {}
    fallback_counts: dict[str, int] = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, Mapping):
            continue
        path = str(raw_item.get("path", ""))
        selected_index = raw_item.get("selected_index")
        if isinstance(selected_index, int) and selected_index >= 0:
            key = (path, selected_index)
        else:
            occurrence = fallback_counts.get(path, 0)
            fallback_counts[path] = occurrence + 1
            key = (path, occurrence)
        indexed[key] = raw_item
    return indexed


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
    estimated_tokens = (
        sum(_entry_estimated_tokens(entry) for entry in included_entries)
        if preview_text
        else 0
    )
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
    relayint_unresolved: bool,
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
    budget_truncated = isinstance(budget, Mapping) and budget.get("truncated") is True
    scene_policy_blocks = (
        malformed
        or scene_type == "unknown"
        or retrieval_scope == "current_context_only"
        or scene_type in {"recovery", "formal_document", "medical_or_safety"}
    )
    preconditions = {
        "scene_policy_allows_apply": not scene_policy_blocks,
        "reference_resolved": not relayint_unresolved,
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
    elif relayint_unresolved:
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


def _apply_blocked_reasons(
    decision: str, preconditions: Mapping[str, bool]
) -> list[str]:
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


def _content_free_query_summary(
    *,
    latest_user_text: str,
    retrieval_query_candidate: Mapping[str, Any],
) -> dict[str, Any]:
    projection = public_retrieval_query_projection(retrieval_query_candidate)
    return {
        "source": "latest_user_message",
        "input_chars": len(latest_user_text),
        "term_hints": [],
        "term_hints_content_free": True,
        "query_hint_strategy": projection["query_hint_strategy"],
        "query_hint_count": projection["query_hint_count"],
        "ambiguous_reference_terms_present": projection["has_ambiguous_reference"],
        "content_free": True,
    }


def _retrieval_priority_projection(
    selected_mem_candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    prioritized = prioritize_relaymem_candidates(selected_mem_candidates)
    return {
        "schema_version": "relaymem.retrieval_priority_runtime.v0",
        "diagnostics_only": True,
        "read_only": True,
        "runtime_wiring": "dry_run_only",
        "source": "selected_mem_candidates",
        "content_included": False,
        "path_included": False,
        "snippet_included": False,
        "applied_to_ctx": False,
        "payload_mutation_allowed": False,
        "writes_memory": False,
        "mutates_soul": False,
        "candidate_count": prioritized["candidate_count"],
        "selected_count": prioritized["selected_count"],
        "selection_policy": prioritized["selection_policy"],
        "layer_counts": prioritized["layer_counts"],
        "selected_layer_counts": prioritized["selected_layer_counts"],
        "selection_projection": prioritized["selection_projection"],
    }
