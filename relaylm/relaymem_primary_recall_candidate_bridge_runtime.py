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
        gate_allowed = original_decision in {"eligible_but_not_applied", "dry_run_only"}
        if not gate_allowed:
            reasons.append("existing_retrieval_gate_blocked")

        candidates = _sequence(artifact.get("selected_mem_candidates"))
        if not candidates:
            reasons.append("existing_retrieval_selected_no_candidates")

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

        if root is not None and namespace is not None and gate_allowed:
            control, control_reasons = target._load_control_state(root)
            reasons.extend(_candidate_public_reasons(control_reasons))
            if control is not None:
                from .relaymem_primary_retrieval_eligibility import (
                    load_primary_retrieval_eligibility_index,
                )

                lifecycle_index = load_primary_retrieval_eligibility_index(
                    root, namespace=namespace
                )
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
                if not selected:
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
        target._replace_legacy_handoff(
            artifact,
            selected,
            original_decision=str(original_decision or "blocked"),
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


def _query_terms_from_artifact(artifact: Mapping[str, Any]) -> list[str]:
    query_summary = artifact.get("query_summary")
    raw_terms = query_summary.get("term_hints") if isinstance(query_summary, Mapping) else None
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
    score = 0
    for term in query_terms:
        if term in haystack:
            score += 16
        for word in re.findall(r"[a-z0-9_:/-]{3,}", term):
            if word in haystack:
                score += 3
        for gram in _cjk_ngrams(term):
            if gram in haystack:
                score += 1
                if score >= 12:
                    return score
    return score


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
