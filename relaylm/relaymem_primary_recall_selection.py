"""Validated Primary candidate selection and bounded handoff construction."""

from __future__ import annotations
import re
from collections.abc import Mapping, Sequence
from typing import Any
from .token_budget import estimate_text_tokens
from .relaymem_primary_recall_store import (
    _load_control_state,
    _load_validated_page,
    _primary_relative_path,
    _safe_root,
    _token,
)

RUNTIME_SCHEMA = "relaymem.primary_recall_runtime.v0"
PROJECTION_SCHEMA = "relaymem.primary_recall_projection.v0"
_NO_CANDIDATE_REASON_IDS = frozenset(
    {
        "blocked_no_candidates",
        "ctx_block_candidate_entries_empty",
        "no_selected_mem_candidates",
        "snippet_candidates_empty",
        "included_snippet_entries_empty",
    }
)
_PROHIBITED_SCENE_TYPES = frozenset(
    {"recovery", "formal_document", "medical_or_safety"}
)
_EXPLICIT_FALLBACK_BLOCKERS = frozenset(
    {
        "scene_policy_blocks_memory",
        "current_context_only_no_external_mem",
        "external_memory_blocked_by_scene_policy",
        "unresolved_reference_requires_confirmation",
        "scene_policy_does_not_allow_snippet_apply",
        "must_not_silently_resolve_ambiguous_reference",
        "memory_store_disabled",
        "blocked_scene_policy",
        "blocked_unresolved_reference",
    }
)


def run_primary_recall_selection(artifact, root, namespace, state):
    reasons = state["reasons"]
    selected, used_tokens = [], 0
    discovery_attempted, discovered_count, discovery_status = False, 0, "disabled"
    if (
        root is not None
        and namespace is not None
        and (state["gate_allowed"] or state["fallback_allowed"])
    ):
        control, control_reasons = _load_control_state(root)
        reasons.extend(_candidate_public_reasons(control_reasons))
        if control is None:
            discovery_status = "character_store_missing"
        else:
            from .relaymem_primary_retrieval_eligibility import (
                load_primary_retrieval_eligibility_index,
            )

            lifecycle = load_primary_retrieval_eligibility_index(
                root, namespace=namespace
            )
            common = dict(
                root=root,
                namespace=namespace,
                control=control,
                lifecycle_index=lifecycle,
                max_candidates=state["max_candidates"],
                max_chars=state["max_chars"],
                budget=state["budget"],
                chars_per_token=state["chars_per_token"],
                used_tokens=0,
                seen_identities=set(),
                reasons=reasons,
            )
            if state["gate_allowed"]:
                selected, used_tokens = _select_validated_primary_candidates(
                    raw_candidates=state["candidates"],
                    require_keyword_match=True,
                    query_terms=(),
                    require_relevance=False,
                    **common,
                )
                common["used_tokens"] = used_tokens
            if not selected and state["fallback_allowed"]:
                discovery_attempted = True
                discovered, discovered_reasons = (
                    _discover_scoped_primary_candidates_from_control(
                        control=control, namespace=namespace
                    )
                )
                reasons.extend(discovered_reasons)
                discovered_count = len(discovered)
                query_terms = _query_terms_from_artifact(artifact)
                if discovered and not query_terms:
                    discovery_status = "primary_candidates_require_query_terms"
                    reasons.append("primary_candidate_query_terms_missing")
                elif discovered:
                    discovery_status = "primary_candidates_discovered"
                    selected, used_tokens = _select_validated_primary_candidates(
                        raw_candidates=discovered,
                        require_keyword_match=False,
                        query_terms=query_terms,
                        require_relevance=True,
                        **common,
                    )
                else:
                    discovery_status = "primary_candidates_empty"
    if selected:
        reasons.append("primary_candidate_selected")
        if discovery_attempted:
            reasons.append("primary_recall_grounding_applied")
    elif "primary_recall_no_scoped_match" not in reasons:
        reasons.append("primary_recall_no_scoped_match")
    return (
        selected,
        used_tokens,
        discovery_attempted,
        discovered_count,
        discovery_status,
    )


def _select_validated_primary_candidates(
    *,
    root: Path,
    namespace: str,
    control: Mapping[str, Sequence[Mapping[str, Any]]],
    lifecycle_index: Any,
    raw_candidates: Sequence[Any],
    require_keyword_match: bool,
    max_candidates: int,
    max_chars: int,
    budget: int,
    chars_per_token: int,
    used_tokens: int,
    seen_identities: set[str],
    reasons: list[str],
    query_terms: Sequence[str],
    require_relevance: bool,
) -> tuple[list[dict[str, Any]], int]:
    """Revalidate raw candidates (M2-selected or bounded-discovered) into evidence.

    ``require_keyword_match`` keeps availability-only M2 candidates out of an
    ordinary recall prompt. ``require_relevance`` keeps discovery-sourced
    candidates from being selected without lexical/n-gram overlap with the
    query terms.
    """
    selected: list[dict[str, Any]] = []
    for raw_candidate in raw_candidates:
        if len(selected) >= max_candidates:
            reasons.append("primary_recall_candidate_cap_reached")
            break
        if not isinstance(raw_candidate, Mapping):
            reasons.append("primary_recall_candidate_shape_invalid")
            continue
        if raw_candidate.get("memory_layer") != "primary":
            continue
        if require_keyword_match and raw_candidate.get("reason") != "keyword_match":
            continue
        loaded, blocked = _load_validated_page(
            root,
            raw_candidate,
            expected_namespace=namespace,
            control=control,
        )
        if loaded is None:
            reasons.extend(_candidate_public_reasons(blocked))
            continue
        if require_relevance and _candidate_summary_score(loaded, query_terms) <= 0:
            reasons.append("primary_candidate_excluded_by_query")
            continue
        physical_identity = loaded["idempotency_key"]
        eligibility = lifecycle_index.evaluate(
            physical_identity,
            candidate_namespace=loaded.get("namespace"),
        )
        if not eligibility.eligible:
            reasons.append(eligibility.reason_id)
            continue
        identity = eligibility.logical_memory_id
        revision = eligibility.current_revision
        if identity is None or revision is None:
            reasons.append("excluded_unresolved_identity")
            continue
        loaded["physical_idempotency_key"] = physical_identity
        loaded["idempotency_key"] = identity
        loaded["revision"] = revision
        loaded["lifecycle_state"] = "active"
        loaded["current"] = True
        if identity in seen_identities:
            reasons.append("primary_recall_duplicate_identity_deduped")
            continue
        summary = loaded["summary"]
        if len(summary) > max_chars:
            reasons.append("primary_recall_summary_exceeds_bound")
            continue
        token_estimate = estimate_text_tokens(
            summary, chars_per_token=chars_per_token
        ).estimated_tokens
        if used_tokens + token_estimate > budget:
            reasons.append("primary_recall_snippet_budget_exceeded")
            continue
        seen_identities.add(identity)
        used_tokens += token_estimate
        selected.append(
            {
                **loaded,
                "evidence_id": f"evidence:{len(selected)}",
                "snippet_text": summary,
                "snippet_chars": len(summary),
                "estimated_tokens": token_estimate,
            }
        )
    return selected, used_tokens


def _discover_scoped_primary_candidates_from_control(
    *,
    control: Mapping[str, Sequence[Mapping[str, Any]]],
    namespace: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Derive bounded Primary MEM page candidates for the exact namespace.

    Page reads are not performed here; every returned candidate must still
    pass ``_load_validated_page`` before it can be selected as evidence.
    """
    candidates: list[dict[str, Any]] = []
    reasons: list[str] = []
    for entry in control.get("index", []):
        if not isinstance(entry, Mapping):
            reasons.append("primary_candidate_shape_invalid")
            continue
        if entry.get("memory_layer") != "primary":
            continue
        if entry.get("namespace") != namespace:
            reasons.append("primary_candidate_excluded_by_namespace")
            continue
        relative = entry.get("page_relative_path")
        if not isinstance(relative, str) or not _primary_relative_path(relative):
            reasons.append("primary_recall_path_invalid")
            continue
        candidates.append(
            {
                "path": relative,
                "source": "mem_page",
                "reason": "primary_candidate_bridge_match",
                "estimated_chars": 0,
                "memory_layer": "primary",
                "layout_profile": "target_primary_secondary",
                "applied_to_ctx": False,
            }
        )
    if not candidates:
        reasons.append("primary_candidates_empty")
    return candidates, reasons


def _build_primary_recall_projection(
    *,
    artifact: Mapping[str, Any],
    attempted: bool,
    root: Path | None,
    namespace: str | None,
    selected: Sequence[Mapping[str, Any]],
    used_tokens: int,
    reasons: list[str],
    discovery_attempted: bool,
    discovered_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": PROJECTION_SCHEMA,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "memory_text_included": False,
        "title_or_summary_included": False,
        "character_value_included": False,
        "namespace_value_included": False,
        "runtime_identifier_values_included": False,
        "path_values_included": False,
        "digest_values_included": False,
        "lineage_values_included": False,
        "idempotency_values_included": False,
        "backend_prompt_included": False,
        "retrieval_attempted": attempted,
        "scene_type": _token(artifact.get("scene_type")) or "unknown",
        "retrieval_scope": _token(artifact.get("retrieval_scope"))
        or "current_context_only",
        "fallback_reason": _projection_fallback_reason(artifact),
        "persistence_block": artifact.get("persistence_block") is True,
        "ctx_block_present": artifact.get("ctx_block") is not None,
        "primary_candidate_discovery_attempted": discovery_attempted,
        "primary_candidate_count": discovered_count,
        "grounding_enabled": bool(selected),
        "grounded_item_count": len(selected),
        "unsupported_detail_policy": "suppress",
        "evidence_content_included": False,
        "runtime_private_evidence_omitted": True,
        "selected_count": len(selected),
        "selected_layer_counts": {"primary": len(selected)},
        "character_scope_resolved": root is not None,
        "namespace_scope_valid": namespace is not None,
        "scope_matched": bool(selected),
        "injection_candidate_present": bool(selected),
        "estimated_chars": sum(int(item.get("snippet_chars", 0)) for item in selected),
        "estimated_tokens": used_tokens,
        "memory_used": False,
        "blocked_reason_ids": reasons,
    }


def _sequence(value: object) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _fallback_no_candidate_trigger(
    *,
    original_decision: str,
    artifact: Mapping[str, Any],
    candidates: Sequence[Any],
) -> bool:
    if candidates:
        return False
    if original_decision == "blocked_no_candidates":
        return True
    return bool(_NO_CANDIDATE_REASON_IDS.intersection(_artifact_reason_ids(artifact)))


def _fallback_policy_blocker(
    *,
    artifact: Mapping[str, Any],
    original_decision: str,
) -> str | None:
    if original_decision == "blocked_scene_policy":
        return "scene_policy_blocks_memory"
    if original_decision == "blocked_unresolved_reference":
        return "unresolved_reference_requires_confirmation"

    scene_type = _token(artifact.get("scene_type")) or "unknown"
    retrieval_scope = _token(artifact.get("retrieval_scope")) or "current_context_only"
    if scene_type == "unknown":
        return "scene_policy_blocks_memory"
    if retrieval_scope == "current_context_only":
        return "current_context_only_no_external_mem"
    if scene_type in _PROHIBITED_SCENE_TYPES:
        return "external_memory_blocked_by_scene_policy"

    fallback_reason = _projection_fallback_reason(artifact)
    if (
        isinstance(fallback_reason, str)
        and fallback_reason in _EXPLICIT_FALLBACK_BLOCKERS
    ):
        return _public_fallback_blocker(fallback_reason)
    for reason in _artifact_reason_ids(artifact):
        if reason in _EXPLICIT_FALLBACK_BLOCKERS:
            return _public_fallback_blocker(reason)
    return None


def _public_fallback_blocker(reason: str) -> str:
    mapping = {
        "blocked_scene_policy": "scene_policy_blocks_memory",
        "blocked_unresolved_reference": "unresolved_reference_requires_confirmation",
        "scene_policy_does_not_allow_snippet_apply": "scene_policy_blocks_memory",
        "must_not_silently_resolve_ambiguous_reference": "unresolved_reference_requires_confirmation",
    }
    return mapping.get(reason, reason)


def _artifact_reason_ids(artifact: Mapping[str, Any]) -> list[str]:
    output: list[str] = []

    def add(value: object) -> None:
        if isinstance(value, str) and value and value not in output:
            output.append(value)

    for key in ("snippet_apply_blocked_reasons", "apply_blocked_reasons"):
        for reason in _sequence(artifact.get(key)):
            add(reason)
    for key in ("blocked",):
        for item in _sequence(artifact.get(key)):
            if isinstance(item, Mapping):
                add(item.get("reason"))
            else:
                add(item)
    ctx_block_snippet_candidate = artifact.get("ctx_block_snippet_candidate")
    if isinstance(ctx_block_snippet_candidate, Mapping):
        for item in _sequence(ctx_block_snippet_candidate.get("blocked")):
            if isinstance(item, Mapping):
                add(item.get("reason"))
    return output


def _primary_recall_handoff_decision(
    *,
    original_decision: str,
    artifact: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
    discovery_attempted: bool,
    fallback_no_candidate_trigger: bool,
) -> str:
    decision = original_decision or "blocked"
    if selected and discovery_attempted and fallback_no_candidate_trigger:
        if "snippet_dry_run_only" in _artifact_reason_ids(artifact):
            return "dry_run_only"
        return "eligible_but_not_applied"
    return decision


def _query_terms_from_artifact(artifact: Mapping[str, Any]) -> list[str]:
    retrieval_query_private = artifact.get("retrieval_query_private")
    private_terms = (
        retrieval_query_private.get("backend_private_hints")
        if isinstance(retrieval_query_private, Mapping)
        else None
    )
    terms = _normalized_query_terms(private_terms)
    if terms:
        return terms

    query_summary = artifact.get("query_summary")
    raw_terms = (
        query_summary.get("term_hints") if isinstance(query_summary, Mapping) else None
    )
    return _normalized_query_terms(raw_terms)


def _normalized_query_terms(raw_terms: object) -> list[str]:
    if not isinstance(raw_terms, Sequence) or isinstance(
        raw_terms, (str, bytes, bytearray)
    ):
        return []
    terms: list[str] = []
    for value in raw_terms:
        if not isinstance(value, str):
            continue
        term = value.strip().lower()
        if term and term not in terms:
            terms.append(term[:64])
        if len(terms) >= 8:
            break
    return terms


def _candidate_summary_score(
    candidate: Mapping[str, Any], query_terms: Sequence[str]
) -> int:
    if not query_terms:
        return 0
    haystack = "\n".join(
        str(candidate.get(key, "")).lower() for key in ("summary", "title")
    )
    lexical_score = 0
    gram_score = 0
    for term in query_terms:
        if term in haystack:
            lexical_score += 16
        for word in re.findall(r"[a-z0-9_:/-]{3,}", term):
            if word in haystack:
                lexical_score += 3
        for gram in _cjk_ngrams(term):
            if gram in haystack:
                gram_score += 1
    if lexical_score > 0:
        return lexical_score + gram_score
    if gram_score >= 12:
        return gram_score
    return 0


def _cjk_ngrams(text: str) -> list[str]:
    compact = "".join(
        char
        for char in text
        if not char.isspace() and char not in "。！？、,.!?;:()[]{}\"'"
    )
    if len(compact) < 2:
        return []
    grams: list[str] = []
    for size in (2, 3, 4):
        if len(compact) < size:
            continue
        for index in range(0, len(compact) - size + 1):
            gram = compact[index : index + size]
            if gram not in grams:
                grams.append(gram)
            if len(grams) >= 48:
                return grams
    return grams


def _candidate_public_reasons(reasons: Sequence[str]) -> list[str]:
    mapping = {
        "primary_recall_namespace_mismatch": "primary_candidate_excluded_by_namespace",
        "primary_recall_page_policy_invalid": "primary_candidate_excluded_by_scope",
        "primary_recall_index_mismatch": "primary_candidate_digest_mismatch",
        "primary_recall_log_mismatch": "primary_candidate_digest_mismatch",
        "primary_recall_log_lineage_mismatch": "primary_candidate_digest_mismatch",
        "primary_recall_index_log_link_mismatch": "primary_candidate_log_missing",
        "primary_recall_reconciliation_missing_or_duplicate": "primary_candidate_log_missing",
    }
    return [mapping.get(str(reason), str(reason)) for reason in reasons if reason]


def _replace_primary_recall_handoff(
    artifact: dict[str, Any],
    selected: Sequence[Mapping[str, Any]],
    *,
    original_decision: str,
    snippet_budget: int,
    reasons: list[str],
) -> None:
    candidates: list[dict[str, Any]] = []
    snippets: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    ctx_entries: list[dict[str, Any]] = []
    plan_entries: list[dict[str, Any]] = []
    for index, item in enumerate(selected):
        evidence_id = str(item["evidence_id"])
        candidates.append(
            {
                "path": item["path"],
                "source": "mem_page",
                "reason": "keyword_match",
                "estimated_chars": item["snippet_chars"],
                "estimated_tokens": item["estimated_tokens"],
                "memory_layer": "primary",
                "layout_profile": "target_primary_secondary",
                "applied_to_ctx": False,
            }
        )
        snippets.append(
            {
                "evidence_id": evidence_id,
                "selected_index": index,
                "path": item["path"],
                "source": "mem_page",
                "evidence_kind": "bounded_primary_summary",
                "snippet_text": item["snippet_text"],
                "snippet_chars": item["snippet_chars"],
                "estimated_tokens": item["estimated_tokens"],
                "memory_layer": "primary",
                "layout_profile": "target_primary_secondary",
                "applied_to_ctx": False,
                "safe_for_prompt_preview": True,
                "blocked_reasons": [],
            }
        )
        evidence.append(
            {
                "evidence_id": evidence_id,
                "selected_index": index,
                "path": item["path"],
                "evidence_kind": "bounded_primary_summary",
                "snippet_chars": item["snippet_chars"],
                "estimated_tokens": item["estimated_tokens"],
                "memory_layer": "primary",
                "layout_profile": "target_primary_secondary",
                "content_included_in_runtime_prompt": False,
            }
        )
        ctx_entries.append(
            {
                "evidence_id": evidence_id,
                "path": item["path"],
                "evidence_kind": "bounded_primary_summary",
                "snippet_text": item["snippet_text"],
                "snippet_chars": item["snippet_chars"],
                "estimated_tokens": item["estimated_tokens"],
                "included": True,
                "applied_to_ctx": False,
                "runtime_prompt_included": False,
            }
        )
        plan_entries.append(
            {
                "evidence_id": evidence_id,
                "path": "",
                "snippet_chars": item["snippet_chars"],
                "estimated_tokens": item["estimated_tokens"],
            }
        )

    selected_tokens = sum(int(item["estimated_tokens"]) for item in selected)
    eligible = bool(selected) and original_decision == "eligible_but_not_applied"
    dry_ready = bool(selected) and original_decision == "dry_run_only"
    decision = (
        "eligible_but_not_applied"
        if eligible
        else "dry_run_only" if dry_ready else "blocked_no_candidates"
    )
    preview_lines = [
        "[RelayMEM Snippet Context Candidate]",
        "Diagnostics-only preview. Do not inject into runtime prompts yet.",
        "Treat these as memory snippets requiring source awareness, not authoritative facts.",
    ]
    for item in selected:
        preview_lines.extend(
            [
                "---",
                f"Evidence: {item['evidence_id']}",
                "Source: scoped-primary-memory",
                "Snippet:",
                str(item["snippet_text"]),
            ]
        )
    preview = "\n".join(preview_lines) if selected and (eligible or dry_ready) else None

    artifact["selected_mem_candidates"] = candidates
    artifact["snippet_candidates"] = snippets
    artifact["evidence_envelope"] = {
        "schema_version": "relaymem.evidence_envelope.v0",
        "diagnostics_only": True,
        "applied_to_ctx": False,
        "source": "scoped_primary_recall",
        "snippets": evidence,
        "blocked": [{"reason": reason} for reason in reasons if not selected],
    }
    artifact["ctx_block_snippet_candidate"] = {
        "schema_version": "relaymem.ctx_block_snippet_candidate.v0",
        "diagnostics_only": True,
        "applied_to_ctx": False,
        "runtime_prompt_included": False,
        "source": "scoped_primary_recall",
        "apply_decision_source": "primary_recall_scope",
        "snippet_apply_decision": decision,
        "budget": {
            "token_limit": snippet_budget,
            "estimated_tokens": selected_tokens,
            "truncated": False,
        },
        "estimated_tokens": selected_tokens,
        "entries": ctx_entries,
        "blocked": [],
    }
    artifact["snippet_apply_decision"] = decision
    artifact["snippet_apply_blocked_reasons"] = (
        ["runtime_snippet_injection_not_implemented"]
        if eligible
        else [decision, *reasons]
    )
    artifact["snippet_runtime_injection_plan"] = {
        "schema_version": "relaymem.snippet_runtime_injection_plan.v0",
        "diagnostics_only": True,
        "applied": False,
        "payload_mutation_allowed": False,
        "target": "backend_messages",
        "insertion_point": "before_latest_user",
        "source": "scoped_primary_recall",
        "apply_decision_source": "primary_recall_scope",
        "snippet_apply_decision": decision,
        "preview_text": preview,
        "estimated_tokens": selected_tokens if preview else 0,
        "source_entries": plan_entries if preview else [],
        "blocked_reasons": (
            [
                "runtime_snippet_injection_not_implemented",
                "backend_payload_mutation_disabled",
                "snippet_prompt_apply_disabled",
            ]
            if preview
            else [decision, *reasons]
        ),
    }


def _projection_fallback_reason(artifact: Mapping[str, Any]) -> str | None:
    artifact_reason = _token(artifact.get("fallback_reason"))
    store_diagnostics = artifact.get("store_diagnostics")
    if isinstance(store_diagnostics, Mapping):
        store_reason = _token(store_diagnostics.get("fallback_reason"))
        if (
            store_reason == "memory_store_disabled"
            and artifact_reason == "memory_store_not_configured"
        ):
            return store_reason
    return artifact_reason


def _reason_ids(values: Sequence[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        normalized = (
            value
            if re.fullmatch(r"[a-z0-9][a-z0-9_:-]{0,127}", value)
            else "invalid_reason_id"
        )
        if normalized not in output:
            output.append(normalized)
        if len(output) >= 32:
            break
    return output
