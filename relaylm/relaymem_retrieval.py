"""RelayMEM Retrieval MVP dry-run artifact helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.relaymem_store import (
    build_relaymem_snippet_evidence_dry_run,
    discover_relaymem_page_candidates,
)


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
    snippet_extraction_enabled: bool = False,
    snippet_dry_run_only: bool = True,
    snippet_apply_enabled: bool = False,
    snippet_budget: int | None = 512,
    max_snippet_chars: int = 512,
    max_snippet_candidates: int = 3,
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
    snippet_evidence = _build_snippet_evidence_dry_run(
        selected_mem_candidates=selected_mem_candidates,
        store_diagnostics=store_diagnostics,
        scene_type=scene_type,
        retrieval_scope=retrieval_scope,
        malformed=parsed_scn["malformed"],
        relayref_unresolved=relayref_unresolved,
        apply_decision=apply_readiness["apply_decision"],
        snippet_extraction_enabled=snippet_extraction_enabled,
        snippet_dry_run_only=snippet_dry_run_only,
        max_snippet_chars=max_snippet_chars,
        max_snippet_candidates=max_snippet_candidates,
    )
    ctx_block_candidate = _attach_evidence_metadata_to_ctx_block_candidate(
        ctx_block_candidate=ctx_block_candidate,
        evidence_envelope=snippet_evidence["evidence_envelope"],
    )
    snippet_apply_readiness = _build_snippet_apply_readiness(
        malformed=parsed_scn["malformed"],
        scene_type=scene_type,
        retrieval_scope=retrieval_scope,
        relayref_unresolved=relayref_unresolved,
        ctx_block_candidate=ctx_block_candidate,
        evidence_envelope=snippet_evidence["evidence_envelope"],
        snippet_candidates=snippet_evidence["snippet_candidates"],
        snippet_dry_run_only=snippet_dry_run_only,
        snippet_apply_enabled=snippet_apply_enabled,
        snippet_budget=snippet_budget,
    )
    ctx_block_snippet_candidate = _build_ctx_block_snippet_candidate(
        snippet_apply_decision=snippet_apply_readiness["snippet_apply_decision"],
        snippet_candidates=snippet_evidence["snippet_candidates"],
        evidence_envelope=snippet_evidence["evidence_envelope"],
        snippet_budget=snippet_budget,
    )
    snippet_runtime_injection_plan = _build_snippet_runtime_injection_plan(
        snippet_apply_decision=snippet_apply_readiness["snippet_apply_decision"],
        ctx_block_snippet_candidate=ctx_block_snippet_candidate,
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
        "ctx_block_snippet_candidate": ctx_block_snippet_candidate,
        "ctx_injection_plan": ctx_injection_plan,
        "snippet_runtime_injection_plan": snippet_runtime_injection_plan,
        "snippet_candidates": snippet_evidence["snippet_candidates"],
        "evidence_envelope": snippet_evidence["evidence_envelope"],
        "fallback_reason": fallback_reason,
        "token_budget": normalized_token_budget,
        "used_tokens": used_tokens,
        "persistence_block": persistence_block,
        "persistence_block_reasons": persistence_block_reasons,
        "apply_decision": apply_readiness["apply_decision"],
        "apply_readiness_score": apply_readiness["apply_readiness_score"],
        "apply_blocked_reasons": apply_readiness["apply_blocked_reasons"],
        "apply_preconditions": apply_readiness["apply_preconditions"],
        "snippet_apply_decision": snippet_apply_readiness["snippet_apply_decision"],
        "snippet_apply_readiness_score": snippet_apply_readiness[
            "snippet_apply_readiness_score"
        ],
        "snippet_apply_blocked_reasons": snippet_apply_readiness[
            "snippet_apply_blocked_reasons"
        ],
        "snippet_apply_preconditions": snippet_apply_readiness[
            "snippet_apply_preconditions"
        ],
        "store_diagnostics": (
            dict(store_diagnostics) if isinstance(store_diagnostics, Mapping) else None
        ),
    }


def _build_snippet_evidence_dry_run(
    *,
    selected_mem_candidates: list[dict[str, Any]],
    store_diagnostics: Mapping[str, Any] | None,
    scene_type: str,
    retrieval_scope: str,
    malformed: bool,
    relayref_unresolved: bool,
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
        relayref_unresolved=relayref_unresolved,
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
    relayref_unresolved: bool,
    selected_mem_candidates: Sequence[Mapping[str, Any]],
    apply_decision: str,
) -> str | None:
    if malformed or scene_type == "unknown":
        return "scene_policy_blocks_memory"
    if retrieval_scope == "current_context_only":
        return "current_context_only_no_external_mem"
    if scene_type in {"recovery", "formal_document", "medical_or_safety"}:
        return "external_memory_blocked_by_scene_policy"
    if relayref_unresolved:
        return "unresolved_reference_requires_confirmation"
    if not selected_mem_candidates:
        return "no_selected_mem_candidates"
    if apply_decision == "blocked_token_budget":
        return "token_budget_exceeded"
    return None


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
    if scene_type in {"recovery", "formal_document", "medical_or_safety"}:
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
        evidence_envelope.get("snippets") if isinstance(evidence_envelope, Mapping) else None
    )
    blocked_by_key = _evidence_items_by_entry_key(
        evidence_envelope.get("blocked") if isinstance(evidence_envelope, Mapping) else None
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


def _evidence_items_by_entry_key(raw_items: object) -> dict[tuple[str, int], Mapping[str, Any]]:
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


def _non_negative_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0

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


def _build_snippet_apply_readiness(
    *,
    malformed: bool,
    scene_type: str,
    retrieval_scope: str,
    relayref_unresolved: bool,
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
        "reference_resolved": not relayref_unresolved,
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
    elif relayref_unresolved:
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
        would_exceed_budget = (
            budget_blocked
            or (
                normalized_budget is not None
                and estimated_tokens + snippet_tokens > normalized_budget
            )
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
    plan_eligible = snippet_apply_decision in {"dry_run_only", "eligible_but_not_applied"}
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
