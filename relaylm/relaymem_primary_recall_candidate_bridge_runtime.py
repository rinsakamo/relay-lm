"""E1-R5 runtime patch for scoped Primary MEM recall candidate discovery.

The base Phase I-1 adapter intentionally relied on M2 to provide selected
candidates. E1-R5 keeps M2 as the preferred relevance owner, but adds a bounded
fallback bridge from character-scoped Primary MEM index/log/page controls when
M2 returns no scoped Primary candidate.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from .token_budget import estimate_text_tokens

_TOKEN_WITH_SLASH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")
_SAFE_REASON_RE = re.compile(r"[a-z0-9][a-z0-9_:-]{0,127}")
_PATCHED_FLAG = "_e1r5_candidate_bridge_installed"
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


def install_relaymem_primary_recall_candidate_bridge_runtime() -> None:
    """Install the E1-R5 bridge into ``relaymem_primary_recall`` once."""

    from . import relaymem_primary_recall as target

    if getattr(target, _PATCHED_FLAG, False) is True:
        return
    target._TOKEN_RE = _TOKEN_WITH_SLASH_RE
    target.apply_relaymem_primary_recall_scope = _build_apply(target)
    setattr(target, _PATCHED_FLAG, True)


def _build_apply(target: Any):
    def apply_relaymem_primary_recall_scope(
        retrieval_artifact: Mapping[str, Any] | None,
        *,
        scoped_store_root: object,
        expected_namespace: object,
        max_snippet_chars: int,
        max_snippet_candidates: int,
        snippet_budget: int,
        chars_per_token: int = 4,
    ) -> dict[str, Any]:
        artifact = deepcopy(dict(retrieval_artifact or {}))
        attempted = isinstance(retrieval_artifact, Mapping)
        reasons: list[str] = []
        selected: list[dict[str, Any]] = []

        root = target._safe_root(scoped_store_root)
        namespace = target._token(expected_namespace)
        if root is None:
            reasons.append("character_store_scope_unavailable")
        if namespace is None:
            reasons.append("memory_namespace_invalid")

        original_decision = artifact.get("snippet_apply_decision")
        original_decision_text = original_decision if isinstance(original_decision, str) else ""
        gate_allowed = original_decision_text in {"eligible_but_not_applied", "dry_run_only"}

        candidates = _sequence(artifact.get("selected_mem_candidates"))
        if not candidates:
            reasons.append("existing_retrieval_selected_no_candidates")
        fallback_no_candidate_trigger = _fallback_no_candidate_trigger(
            original_decision=original_decision_text,
            artifact=artifact,
            candidates=candidates,
        )
        fallback_policy_blocker = _fallback_policy_blocker(
            target=target,
            artifact=artifact,
            original_decision=original_decision_text,
        )
        fallback_discovery_allowed = (
            root is not None
            and namespace is not None
            and fallback_no_candidate_trigger
            and fallback_policy_blocker is None
        )
        if not gate_allowed and not fallback_discovery_allowed:
            reasons.append("existing_retrieval_gate_blocked")
        if fallback_no_candidate_trigger and fallback_policy_blocker is not None:
            reasons.append(fallback_policy_blocker)

        max_candidates = max(0, int(max_snippet_candidates))
        max_chars = max(1, int(max_snippet_chars))
        budget = max(1, int(snippet_budget))
        cpt = max(1, int(chars_per_token))
        used_tokens = 0
        seen_identities: set[str] = set()
        discovery_attempted = False
        discovered_count = 0
        discovery_status = "disabled"
        query_terms = _query_terms_from_artifact(artifact)

        if root is not None and namespace is not None and (gate_allowed or fallback_discovery_allowed):
            control, control_reasons = target._load_control_state(root)
            reasons.extend(_candidate_public_reasons(control_reasons))
            if control is not None:
                from .relaymem_primary_retrieval_eligibility import (
                    load_primary_retrieval_eligibility_index,
                )

                lifecycle_index = load_primary_retrieval_eligibility_index(
                    root, namespace=namespace
                )
                if gate_allowed:
                    selected, used_tokens = _select_validated_candidates(
                        target=target,
                        root=root,
                        namespace=namespace,
                        control=control,
                        lifecycle_index=lifecycle_index,
                        raw_candidates=candidates,
                        require_keyword_match=True,
                        max_candidates=max_candidates,
                        max_chars=max_chars,
                        budget=budget,
                        chars_per_token=cpt,
                        used_tokens=used_tokens,
                        seen_identities=seen_identities,
                        reasons=reasons,
                        query_terms=(),
                        require_relevance=False,
                    )
                if not selected and (gate_allowed or fallback_discovery_allowed):
                    discovery_attempted = True
                    bridge_candidates, bridge_reasons = _discover_primary_candidates_from_control(
                        target=target,
                        control=control,
                        namespace=namespace,
                    )
                    reasons.extend(bridge_reasons)
                    discovered_count = len(bridge_candidates)
                    if bridge_candidates and not query_terms:
                        discovery_status = "primary_candidates_require_query_terms"
                        reasons.append("primary_candidate_query_terms_missing")
                    elif bridge_candidates:
                        discovery_status = "primary_candidates_discovered"
                        selected, used_tokens = _select_validated_candidates(
                            target=target,
                            root=root,
                            namespace=namespace,
                            control=control,
                            lifecycle_index=lifecycle_index,
                            raw_candidates=bridge_candidates,
                            require_keyword_match=False,
                            max_candidates=max_candidates,
                            max_chars=max_chars,
                            budget=budget,
                            chars_per_token=cpt,
                            used_tokens=used_tokens,
                            seen_identities=seen_identities,
                            reasons=reasons,
                            query_terms=query_terms,
                            require_relevance=True,
                        )
                    else:
                        discovery_status = "primary_candidates_empty"
            else:
                discovery_status = "character_store_missing"

        if selected:
            reasons.append("primary_candidate_selected")
            if discovery_attempted:
                reasons.append("primary_recall_grounding_applied")
        elif "primary_recall_no_scoped_match" not in reasons:
            reasons.append("primary_recall_no_scoped_match")

        public_reasons = _reason_ids(reasons)
        handoff_decision = _bridge_handoff_decision(
            original_decision=original_decision_text,
            artifact=artifact,
            selected=selected,
            discovery_attempted=discovery_attempted,
            fallback_no_candidate_trigger=fallback_no_candidate_trigger,
        )
        target._replace_legacy_handoff(
            artifact,
            selected,
            original_decision=handoff_decision,
            snippet_budget=budget,
            reasons=public_reasons,
        )
        runtime = {
            "schema_version": target.RUNTIME_SCHEMA,
            "runtime_private": True,
            "content_included": bool(selected),
            "request_local": True,
            "primary_candidate_discovery_attempted": discovery_attempted,
            "primary_candidate_count": discovered_count,
            "discovery_status": discovery_status if discovery_attempted else "ready",
            "selected_count": len(selected),
            "selected_memories": selected,
            "blocked_reason_ids": public_reasons,
        }
        projection = _projection(
            target=target,
            artifact=artifact,
            attempted=attempted,
            root=root,
            namespace=namespace,
            selected=selected,
            used_tokens=used_tokens,
            reasons=public_reasons,
            discovery_attempted=discovery_attempted,
            discovered_count=discovered_count,
        )
        artifact["primary_recall_runtime"] = runtime
        artifact["primary_recall_projection"] = projection
        return artifact

    return apply_relaymem_primary_recall_scope


def _select_validated_candidates(
    *,
    target: Any,
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
        loaded, blocked = target._load_validated_page(
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


def _discover_primary_candidates_from_control(
    *,
    target: Any,
    control: Mapping[str, Sequence[Mapping[str, Any]]],
    namespace: str,
) -> tuple[list[dict[str, Any]], list[str]]:
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
        if not isinstance(relative, str) or not target._primary_relative_path(relative):
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


def _projection(
    *,
    target: Any,
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
        "schema_version": target.PROJECTION_SCHEMA,
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
        "scene_type": target._token(artifact.get("scene_type")) or "unknown",
        "retrieval_scope": target._token(artifact.get("retrieval_scope")) or "current_context_only",
        "fallback_reason": target._projection_fallback_reason(artifact),
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
    target: Any,
    artifact: Mapping[str, Any],
    original_decision: str,
) -> str | None:
    if original_decision == "blocked_scene_policy":
        return "scene_policy_blocks_memory"
    if original_decision == "blocked_unresolved_reference":
        return "unresolved_reference_requires_confirmation"

    scene_type = target._token(artifact.get("scene_type")) or "unknown"
    retrieval_scope = target._token(artifact.get("retrieval_scope")) or "current_context_only"
    if scene_type == "unknown":
        return "scene_policy_blocks_memory"
    if retrieval_scope == "current_context_only":
        return "current_context_only_no_external_mem"
    if scene_type in _PROHIBITED_SCENE_TYPES:
        return "external_memory_blocked_by_scene_policy"

    fallback_reason = target._projection_fallback_reason(artifact)
    if isinstance(fallback_reason, str) and fallback_reason in _EXPLICIT_FALLBACK_BLOCKERS:
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


def _bridge_handoff_decision(
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
    raw_terms = query_summary.get("term_hints") if isinstance(query_summary, Mapping) else None
    return _normalized_query_terms(raw_terms)


def _normalized_query_terms(raw_terms: object) -> list[str]:
    if not isinstance(raw_terms, Sequence) or isinstance(raw_terms, (str, bytes, bytearray)):
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


def _candidate_summary_score(candidate: Mapping[str, Any], query_terms: Sequence[str]) -> int:
    if not query_terms:
        return 0
    haystack = "\n".join(
        str(candidate.get(key, "")).lower()
        for key in ("summary", "title")
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
        char for char in text if not char.isspace() and char not in "。！？、,.!?;:()[]{}\"'"
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


def _reason_ids(values: Sequence[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        normalized = value if _SAFE_REASON_RE.fullmatch(value) else "invalid_reason_id"
        if normalized not in output:
            output.append(normalized)
        if len(output) >= 32:
            break
    return output


__all__ = ["install_relaymem_primary_recall_candidate_bridge_runtime"]
