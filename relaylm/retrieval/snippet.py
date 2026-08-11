"""Bounded Retrieval snippet materialization and injection planning."""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any
from relaylm.relaymem_store import build_relaymem_snippet_evidence_dry_run


def _non_negative_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _build_snippet_evidence_dry_run(
    *,
    selected_mem_candidates: list[dict[str, Any]],
    store_diagnostics: Mapping[str, Any] | None,
    scene_type: str,
    retrieval_scope: str,
    malformed: bool,
    relayint_unresolved: bool,
    apply_decision: str,
    snippet_extraction_enabled: bool,
    snippet_dry_run_only: bool,
    max_snippet_chars: int,
    max_snippet_candidates: int,
) -> dict[str, Any]:
    empty = {
        "snippet_candidates": [],
        "evidence_envelope": {
            "schema_version": "relaymem.evidence_envelope.v0",
            "diagnostics_only": True,
            "applied_to_ctx": False,
            "source": "selected_mem_candidates",
            "snippets": [],
            "blocked": [],
        },
    }
    skip_reason = _snippet_extraction_skip_reason(
        malformed=malformed,
        scene_type=scene_type,
        retrieval_scope=retrieval_scope,
        relayint_unresolved=relayint_unresolved,
        selected_mem_candidates=selected_mem_candidates,
        apply_decision=apply_decision,
    )
    if skip_reason is not None:
        if selected_mem_candidates or snippet_extraction_enabled:
            empty["evidence_envelope"]["blocked"].append({"reason": skip_reason})
        return empty
    if not isinstance(store_diagnostics, Mapping):
        empty["evidence_envelope"]["blocked"].append(
            {"reason": "memory_store_not_configured"}
        )
        return empty
    snippet_evidence = build_relaymem_snippet_evidence_dry_run(
        root_path=(
            store_diagnostics.get("root_path")
            if isinstance(store_diagnostics.get("root_path"), str)
            else None
        ),
        selected_mem_candidates=selected_mem_candidates,
        snippet_extraction_enabled=snippet_extraction_enabled,
        snippet_dry_run_only=snippet_dry_run_only,
        max_snippet_chars=max_snippet_chars,
        max_snippet_candidates=max_snippet_candidates,
    )
    return {
        "snippet_candidates": snippet_evidence["snippet_candidates"],
        "evidence_envelope": snippet_evidence["evidence_envelope"],
    }


def _snippet_extraction_skip_reason(
    *,
    malformed: bool,
    scene_type: str,
    retrieval_scope: str,
    relayint_unresolved: bool,
    selected_mem_candidates: Sequence[Mapping[str, Any]],
    apply_decision: str,
) -> str | None:
    if malformed or scene_type == "unknown":
        return "scene_policy_blocks_memory"
    if retrieval_scope == "current_context_only":
        return "current_context_only_no_external_mem"
    if scene_type in {"recovery", "formal_document", "medical_or_safety"}:
        return "external_memory_blocked_by_scene_policy"
    if relayint_unresolved:
        return "unresolved_reference_requires_confirmation"
    if not selected_mem_candidates:
        return "no_selected_mem_candidates"
    if apply_decision == "blocked_token_budget":
        return "token_budget_exceeded"
    return None


def _build_snippet_apply_readiness(
    *,
    malformed: bool,
    scene_type: str,
    retrieval_scope: str,
    relayint_unresolved: bool,
    ctx_block_candidate: Mapping[str, Any],
    evidence_envelope: Mapping[str, Any],
    snippet_candidates: Sequence[Mapping[str, Any]],
    snippet_dry_run_only: bool,
    snippet_apply_enabled: bool,
    snippet_budget: int | None,
) -> dict[str, Any]:
    entries = ctx_block_candidate.get("entries")
    candidate_entries = (
        entries
        if isinstance(entries, Sequence) and not isinstance(entries, str)
        else []
    )
    included_entries = [
        entry
        for entry in candidate_entries
        if isinstance(entry, Mapping) and entry.get("included") is True
    ]
    included_snippet_entries = [
        entry
        for entry in included_entries
        if isinstance(entry, Mapping) and entry.get("snippet_available") is True
    ]
    envelope_blocked = evidence_envelope.get("blocked")
    evidence_envelope_present = isinstance(evidence_envelope, Mapping)
    snippet_candidates_present = bool(snippet_candidates)
    blocked_evidence_present = (
        isinstance(envelope_blocked, Sequence)
        and not isinstance(envelope_blocked, str)
        and bool(envelope_blocked)
    )
    snippet_tokens = sum(
        _non_negative_int(entry.get("snippet_estimated_tokens"))
        for entry in included_snippet_entries
    )
    normalized_budget = (
        snippet_budget
        if isinstance(snippet_budget, int) and snippet_budget > 0
        else None
    )
    snippet_budget_allows_candidate = (
        normalized_budget is None or snippet_tokens <= normalized_budget
    )
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
        "evidence_envelope_present": evidence_envelope_present,
        "snippet_candidates_present": snippet_candidates_present,
        "included_snippet_entries_present": bool(included_snippet_entries),
        "snippet_budget_allows_candidate": snippet_budget_allows_candidate,
        "snippet_dry_run_only": bool(snippet_dry_run_only),
        "snippet_apply_enabled": bool(snippet_apply_enabled),
        "runtime_snippet_injection_enabled": False,
        "backend_payload_mutation_allowed": False,
        "mem_soul_mutation_allowed": False,
    }

    if scene_policy_blocks:
        decision = "blocked_scene_policy"
    elif relayint_unresolved:
        decision = "blocked_unresolved_reference"
    elif not candidate_entries:
        decision = "blocked_no_candidates"
    elif blocked_evidence_present and not included_snippet_entries:
        decision = "blocked_snippet_evidence"
    elif not included_snippet_entries:
        decision = "blocked_no_snippet"
    elif not snippet_budget_allows_candidate:
        decision = "blocked_snippet_budget"
    elif snippet_dry_run_only or not snippet_apply_enabled:
        decision = "dry_run_only"
    else:
        decision = "eligible_but_not_applied"

    return {
        "snippet_apply_decision": decision,
        "snippet_apply_readiness_score": _snippet_apply_readiness_score(preconditions),
        "snippet_apply_blocked_reasons": _snippet_apply_blocked_reasons(
            decision,
            preconditions,
            blocked_evidence_present=blocked_evidence_present,
        ),
        "snippet_apply_preconditions": preconditions,
    }


def _snippet_apply_blocked_reasons(
    decision: str,
    preconditions: Mapping[str, bool],
    *,
    blocked_evidence_present: bool,
) -> list[str]:
    reasons: list[str] = [decision]
    if decision == "eligible_but_not_applied":
        reasons.append("runtime_snippet_injection_not_implemented")
        return _dedupe_reasons(reasons)
    if not preconditions.get("scene_policy_allows_apply", False):
        reasons.append("scene_policy_does_not_allow_snippet_apply")
    if not preconditions.get("reference_resolved", False):
        reasons.append("unresolved_reference_requires_confirmation")
    if not preconditions.get("candidate_entries_present", False):
        reasons.append("ctx_block_candidate_entries_empty")
    if not preconditions.get("evidence_envelope_present", False):
        reasons.append("evidence_envelope_missing")
    if not preconditions.get("snippet_candidates_present", False):
        reasons.append("snippet_candidates_empty")
    if blocked_evidence_present:
        reasons.append("snippet_evidence_blocked")
    if not preconditions.get("included_snippet_entries_present", False):
        reasons.append("included_snippet_entries_empty")
    if not preconditions.get("snippet_budget_allows_candidate", False):
        reasons.append("snippet_budget_exceeded")
    if preconditions.get("snippet_dry_run_only", True):
        reasons.append("snippet_dry_run_only")
    if not preconditions.get("snippet_apply_enabled", False):
        reasons.append("snippet_apply_disabled")
    reasons.append("runtime_snippet_injection_not_implemented")
    return _dedupe_reasons(reasons)


def _snippet_apply_readiness_score(preconditions: Mapping[str, bool]) -> float:
    readiness_keys = (
        "scene_policy_allows_apply",
        "reference_resolved",
        "candidate_entries_present",
        "evidence_envelope_present",
        "snippet_candidates_present",
        "included_snippet_entries_present",
        "snippet_budget_allows_candidate",
        "snippet_apply_enabled",
    )
    passed = sum(1 for key in readiness_keys if preconditions.get(key) is True)
    return round(passed / len(readiness_keys), 3)


def _build_ctx_block_snippet_candidate(
    *,
    snippet_apply_decision: str,
    snippet_candidates: Sequence[Mapping[str, Any]],
    evidence_envelope: Mapping[str, Any],
    snippet_budget: int | None,
) -> dict[str, Any]:
    normalized_budget = (
        snippet_budget
        if isinstance(snippet_budget, int) and snippet_budget > 0
        else None
    )
    candidate: dict[str, Any] = {
        "schema_version": "relaymem.ctx_block_snippet_candidate.v0",
        "diagnostics_only": True,
        "applied_to_ctx": False,
        "runtime_prompt_included": False,
        "source": "evidence_envelope",
        "apply_decision_source": "snippet_apply_decision",
        "snippet_apply_decision": snippet_apply_decision,
        "budget": {
            "token_limit": normalized_budget,
            "estimated_tokens": 0,
            "truncated": False,
        },
        "estimated_tokens": 0,
        "entries": [],
        "blocked": [],
    }
    envelope_blocked = evidence_envelope.get("blocked")
    if isinstance(envelope_blocked, Sequence) and not isinstance(envelope_blocked, str):
        candidate["blocked"].extend(
            _snippet_candidate_blocked_item(item)
            for item in envelope_blocked
            if isinstance(item, Mapping)
        )
    budget_blocked = snippet_apply_decision == "blocked_snippet_budget"
    if snippet_apply_decision not in {
        "dry_run_only",
        "eligible_but_not_applied",
        "blocked_snippet_budget",
    }:
        blocked_reasons = {
            str(item.get("reason"))
            for item in candidate["blocked"]
            if isinstance(item, Mapping)
        }
        if snippet_apply_decision not in blocked_reasons:
            candidate["blocked"].append({"reason": snippet_apply_decision})
        return candidate

    estimated_tokens = 0
    truncated = False
    for raw_snippet in snippet_candidates:
        if not isinstance(raw_snippet, Mapping):
            continue
        snippet_tokens = _non_negative_int(raw_snippet.get("estimated_tokens"))
        would_exceed_budget = budget_blocked or (
            normalized_budget is not None
            and estimated_tokens + snippet_tokens > normalized_budget
        )
        if would_exceed_budget:
            truncated = True
            candidate["blocked"].append(
                {
                    "evidence_id": str(raw_snippet.get("evidence_id", "")),
                    "path": str(raw_snippet.get("path", "")),
                    "reason": "snippet_budget_exceeded",
                    "estimated_tokens": snippet_tokens,
                    "token_limit": normalized_budget,
                }
            )
            continue
        estimated_tokens += snippet_tokens
        candidate["entries"].append(
            {
                "evidence_id": str(raw_snippet.get("evidence_id", "")),
                "path": str(raw_snippet.get("path", "")),
                "evidence_kind": str(
                    raw_snippet.get("evidence_kind", "bounded_page_snippet")
                ),
                "snippet_text": str(raw_snippet.get("snippet_text", "")),
                "snippet_chars": _non_negative_int(raw_snippet.get("snippet_chars")),
                "estimated_tokens": snippet_tokens,
                "included": True,
                "applied_to_ctx": False,
                "runtime_prompt_included": False,
            }
        )
    candidate["estimated_tokens"] = estimated_tokens
    candidate["budget"] = {
        "token_limit": normalized_budget,
        "estimated_tokens": estimated_tokens,
        "truncated": truncated,
    }
    return candidate


def _build_snippet_runtime_injection_plan(
    *,
    snippet_apply_decision: str,
    ctx_block_snippet_candidate: Mapping[str, Any],
) -> dict[str, Any]:
    entries = ctx_block_snippet_candidate.get("entries")
    snippet_entries = (
        entries
        if isinstance(entries, Sequence) and not isinstance(entries, str)
        else []
    )
    plan_eligible = snippet_apply_decision in {
        "dry_run_only",
        "eligible_but_not_applied",
    }
    preview_text = (
        _build_snippet_runtime_preview(snippet_entries)
        if plan_eligible and snippet_entries
        else None
    )
    source_entries = (
        _snippet_runtime_source_entries(snippet_entries)
        if preview_text is not None
        else []
    )
    estimated_tokens = (
        sum(
            _non_negative_int(entry.get("estimated_tokens"))
            for entry in snippet_entries
            if isinstance(entry, Mapping)
        )
        if preview_text is not None
        else 0
    )
    return {
        "schema_version": "relaymem.snippet_runtime_injection_plan.v0",
        "diagnostics_only": True,
        "applied": False,
        "payload_mutation_allowed": False,
        "target": "backend_messages",
        "insertion_point": "before_latest_user",
        "source": "ctx_block_snippet_candidate",
        "apply_decision_source": "snippet_apply_decision",
        "snippet_apply_decision": snippet_apply_decision,
        "preview_text": preview_text,
        "estimated_tokens": estimated_tokens,
        "source_entries": source_entries,
        "blocked_reasons": _snippet_runtime_plan_blocked_reasons(
            snippet_apply_decision=snippet_apply_decision,
            has_entries=bool(snippet_entries),
            plan_eligible=plan_eligible,
        ),
    }


def _build_snippet_runtime_preview(entries: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "[RelayMEM Snippet Context Candidate]",
        "Diagnostics-only preview. Do not inject into runtime prompts yet.",
        "Treat these as memory snippets requiring source awareness, not authoritative facts.",
    ]
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        path = _sanitize_preview_metadata(entry.get("path"))
        evidence_id = _sanitize_preview_metadata(entry.get("evidence_id"), max_chars=80)
        snippet_text = str(entry.get("snippet_text", ""))
        lines.extend(
            [
                "---",
                f"Evidence: {evidence_id}" if evidence_id else "Evidence: unknown",
                f"Source: {path}" if path else "Source: unknown",
                "Snippet:",
                snippet_text,
            ]
        )
    return "\n".join(lines) if len(lines) > 3 else ""


def _snippet_runtime_source_entries(
    entries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "evidence_id": str(entry.get("evidence_id", "")),
            "path": str(entry.get("path", "")),
            "snippet_chars": _non_negative_int(entry.get("snippet_chars")),
            "estimated_tokens": _non_negative_int(entry.get("estimated_tokens")),
        }
        for entry in entries
        if isinstance(entry, Mapping)
    ]


def _snippet_runtime_plan_blocked_reasons(
    *,
    snippet_apply_decision: str,
    has_entries: bool,
    plan_eligible: bool,
) -> list[str]:
    reasons: list[str] = []
    if not has_entries:
        reasons.append("ctx_block_snippet_candidate_empty")
    if not plan_eligible:
        reasons.append(snippet_apply_decision)
    reasons.extend(
        [
            "runtime_snippet_injection_not_implemented",
            "backend_payload_mutation_disabled",
            "snippet_prompt_apply_disabled",
        ]
    )
    return _dedupe_reasons(reasons)


def _sanitize_preview_metadata(value: object, *, max_chars: int = 160) -> str:
    text = "" if value is None else str(value)
    normalized_chars: list[str] = []
    replacements = {
        "`": "'",
        '"': "'",
        "[": "(",
        "]": ")",
        "{": "(",
        "}": ")",
        "<": "(",
        ">": ")",
        ":": " -",
    }
    for char in text:
        codepoint = ord(char)
        if char in {"\r", "\n", "\t"} or codepoint < 32 or codepoint == 127:
            normalized_chars.append(" ")
            continue
        normalized_chars.append(replacements.get(char, char))
    normalized = " ".join("".join(normalized_chars).split())
    max_chars = max(1, int(max_chars))
    if len(normalized) > max_chars:
        if max_chars > 3:
            return normalized[: max_chars - 3].rstrip() + "..."
        return normalized[:max_chars]
    return normalized


def _snippet_candidate_blocked_item(item: Mapping[str, Any]) -> dict[str, str]:
    blocked: dict[str, str] = {"reason": str(item.get("reason", "snippet_blocked"))}
    evidence_id = item.get("evidence_id")
    path = item.get("path")
    if evidence_id is not None:
        blocked["evidence_id"] = str(evidence_id)
    if path is not None:
        blocked["path"] = str(path)
    return blocked


def _dedupe_reasons(reasons: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    return deduped
