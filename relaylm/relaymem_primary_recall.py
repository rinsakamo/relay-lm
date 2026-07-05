"""Phase I-1 scoped Primary MEM recall adapter.

The existing RelayMEM M2 dry-run remains the preferred candidate-discovery
owner.  This adapter narrows those candidates to durable, reconciled Primary
MEM pages from one character-partitioned store root and one exact namespace,
then rebuilds the existing bounded snippet handoff consumed by RelayCTX.

When M2 selects no eligible scoped Primary candidate and scene policy allows
external memory, this adapter also performs a bounded fallback discovery from
the character-scoped Primary MEM index/log/page controls (folded in from the
former E1-R5 candidate bridge runtime patch), revalidating any discovered
candidate through the same page/index/log/lifecycle checks before it can be
selected.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

from ._relaymem_primary_page_writer_common import (
    EVENT_KINDS,
    FRONT_MATTER_KEYS,
    KIND_TARGET,
    MAX_PAGE_BYTES,
    PAGE_SCHEMA,
    TARGET_DIR,
    bad_text,
    is_sha256,
    parse_page_markdown,
    stable_hash,
)
from .token_budget import estimate_text_tokens

RUNTIME_SCHEMA = "relaymem.primary_recall_runtime.v0"
PROJECTION_SCHEMA = "relaymem.primary_recall_projection.v0"
_CHARACTER_PARTITION_VERSION = "relaymem-character-store-v0"
# Scope/namespace tokens allow an internal slash so they can align with
# durable queue namespaces and scoped path conventions (e.g.
# "character/default"). This is not a path-traversal allowance -- path
# validation for on-disk reads stays with `_primary_relative_path`,
# `_contains_symlink`, and `PurePosixPath` below.
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")
_MAX_CONTROL_BYTES = 65_536
_MAX_MARKERS = 256
_MAX_MARKER_LINE_BYTES = 4_096
_PRIMARY_DIRS = tuple(TARGET_DIR.values())
_INDEX_SCHEMA = "relaymem.primary_index_entry.v0"
_LOG_SCHEMA = "relaymem.primary_log_entry.v0"
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


def resolve_relaymem_character_store_root(
    configured_root: object,
    character_id: object,
) -> str | None:
    """Resolve one opaque character partition below the configured store root.

    The configured root remains the operator-owned RelayMEM root.  Character
    values are not used as path components and are never returned by the public
    projection.
    """

    if not isinstance(configured_root, str) or not configured_root.strip():
        return None
    if configured_root != configured_root.strip() or "\x00" in configured_root:
        return None
    if not isinstance(character_id, str) or _TOKEN_RE.fullmatch(character_id) is None:
        return None
    root = Path(configured_root)
    if _path_has_symlink_component(root):
        return None
    if root.exists() and not root.is_dir():
        return None
    character_root = root / "characters"
    if character_root.is_symlink():
        return None
    if character_root.exists() and not character_root.is_dir():
        return None
    digest = stable_hash((_CHARACTER_PARTITION_VERSION, character_id))
    return str(character_root / digest)


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
    """Narrow an existing M2 artifact to exact scoped Primary MEM evidence.

    M2 remains the preferred relevance owner: candidates it already selected
    are revalidated against page, index, log, namespace, path, digest, and
    bounded-content contracts. When M2 yields no eligible scoped Primary
    candidate, scene policy allows external memory, and query terms are
    available, a bounded fallback discovers candidates directly from the
    character-scoped Primary MEM index/log/page controls and revalidates them
    through the same contracts before they can be selected.
    """

    artifact = deepcopy(dict(retrieval_artifact or {}))
    attempted = isinstance(retrieval_artifact, Mapping)
    reasons: list[str] = []
    selected: list[dict[str, Any]] = []

    root = _safe_root(scoped_store_root)
    namespace = _token(expected_namespace)
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
        artifact=artifact,
        original_decision=original_decision_text,
    )
    # Fallback discovery is *considered* whenever M2's own gate already permits
    # external memory (gate_allowed) or M2's block was purely "no candidates"
    # (fallback_no_candidate_trigger) -- but considering it is never enough on
    # its own. `fallback_policy_blocker` (scene policy / unresolved reference /
    # current_context_only / prohibited scene type / memory store disabled)
    # must independently be absent before the control-index scan may run.
    fallback_discovery_considered = gate_allowed or fallback_no_candidate_trigger
    fallback_discovery_allowed = (
        root is not None
        and namespace is not None
        and fallback_discovery_considered
        and fallback_policy_blocker is None
    )
    if not gate_allowed and not fallback_discovery_allowed:
        reasons.append("existing_retrieval_gate_blocked")
    if fallback_discovery_considered and fallback_policy_blocker is not None:
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
        control, control_reasons = _load_control_state(root)
        reasons.extend(_candidate_public_reasons(control_reasons))
        if control is not None:
            # M2 remains relevance owner. I-4D applies one bounded,
            # request-scoped read-only lifecycle view before snippet construction.
            from .relaymem_primary_retrieval_eligibility import (
                load_primary_retrieval_eligibility_index,
            )

            lifecycle_index = load_primary_retrieval_eligibility_index(
                root, namespace=namespace
            )
            if gate_allowed:
                selected, used_tokens = _select_validated_primary_candidates(
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
            if not selected and fallback_discovery_allowed:
                discovery_attempted = True
                discovered_candidates, discovered_reasons = _discover_scoped_primary_candidates_from_control(
                    control=control,
                    namespace=namespace,
                )
                reasons.extend(discovered_reasons)
                discovered_count = len(discovered_candidates)
                if discovered_candidates and not query_terms:
                    discovery_status = "primary_candidates_require_query_terms"
                    reasons.append("primary_candidate_query_terms_missing")
                elif discovered_candidates:
                    discovery_status = "primary_candidates_discovered"
                    selected, used_tokens = _select_validated_primary_candidates(
                        root=root,
                        namespace=namespace,
                        control=control,
                        lifecycle_index=lifecycle_index,
                        raw_candidates=discovered_candidates,
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
    handoff_decision = _primary_recall_handoff_decision(
        original_decision=original_decision_text,
        artifact=artifact,
        selected=selected,
        discovery_attempted=discovery_attempted,
        fallback_no_candidate_trigger=fallback_no_candidate_trigger,
    )
    _replace_primary_recall_handoff(
        artifact,
        selected,
        original_decision=handoff_decision,
        snippet_budget=budget,
        reasons=public_reasons,
    )
    runtime = {
        "schema_version": RUNTIME_SCHEMA,
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
    projection = _build_primary_recall_projection(
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
        "retrieval_scope": _token(artifact.get("retrieval_scope")) or "current_context_only",
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
        else "dry_run_only"
        if dry_ready
        else "blocked_no_candidates"
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


def _load_validated_page(
    root: Path,
    candidate: Mapping[str, Any],
    *,
    expected_namespace: str,
    control: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[dict[str, Any] | None, list[str]]:
    relative = candidate.get("path")
    if not isinstance(relative, str) or not _primary_relative_path(relative):
        return None, ["primary_recall_path_invalid"]
    path = root / PurePosixPath(relative)
    if _contains_symlink(root, path) or not path.is_file():
        return None, ["primary_recall_page_unsafe_or_missing"]
    try:
        raw = path.read_bytes()
    except OSError:
        return None, ["primary_recall_page_unreadable"]
    if not raw or len(raw) > MAX_PAGE_BYTES:
        return None, ["primary_recall_page_size_invalid"]
    try:
        markdown = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, ["primary_recall_page_utf8_invalid"]
    parsed = parse_page_markdown(markdown)
    if parsed.get("valid") is not True:
        return None, ["primary_recall_page_schema_invalid"]
    metadata = parsed["metadata"]
    if set(metadata) != set(FRONT_MATTER_KEYS):
        return None, ["primary_recall_page_schema_invalid"]
    fixed = {
        "schema_version": PAGE_SCHEMA,
        "memory_layer": "primary",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "summary_origin": "trusted_in_process_summary",
        "content_role": "evidence",
    }
    if any(metadata.get(key) != value for key, value in fixed.items()):
        return None, ["primary_recall_page_policy_invalid"]
    if metadata.get("namespace") != expected_namespace:
        return None, ["primary_recall_namespace_mismatch"]
    memory_kind = metadata.get("memory_kind")
    target_category = KIND_TARGET.get(str(memory_kind))
    if target_category is None:
        return None, ["primary_recall_memory_kind_invalid"]
    if metadata.get("source_event_kind") not in EVENT_KINDS:
        return None, ["primary_recall_event_kind_invalid"]
    identity = metadata.get("idempotency_key")
    lineage = metadata.get("lineage_fingerprint")
    if not is_sha256(identity) or not is_sha256(lineage):
        return None, ["primary_recall_lineage_invalid"]
    expected_path = f"{TARGET_DIR[target_category]}/{identity}.md"
    if relative != expected_path:
        return None, ["primary_recall_path_identity_mismatch"]
    summary = metadata.get("summary")
    title = metadata.get("title")
    if (
        not isinstance(summary, str)
        or not summary
        or summary != summary.strip()
        or bad_text(summary)
        or not isinstance(title, str)
        or title != title.strip()
        or bad_text(title)
    ):
        return None, ["primary_recall_page_content_invalid"]
    expected_body = f"# Primary memory\n\n## Summary\n\n{summary}\n"
    if parsed.get("body") != expected_body:
        return None, ["primary_recall_page_body_mismatch"]

    digest = sha256(raw).hexdigest()
    index_matches = [
        entry
        for entry in control["index"]
        if entry.get("page_relative_path") == relative
        and entry.get("idempotency_key") == identity
    ]
    log_matches = [
        entry
        for entry in control["log"]
        if entry.get("page_relative_path") == relative
        and entry.get("idempotency_key") == identity
    ]
    if len(index_matches) != 1 or len(log_matches) != 1:
        return None, ["primary_recall_reconciliation_missing_or_duplicate"]
    index_entry = index_matches[0]
    log_entry = log_matches[0]
    shared = {
        "page_relative_path": relative,
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "target_category": target_category,
        "namespace": expected_namespace,
        "source_event_kind": metadata["source_event_kind"],
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "idempotency_key": identity,
        "page_digest": digest,
    }
    if any(index_entry.get(key) != value for key, value in shared.items()):
        return None, ["primary_recall_index_mismatch"]
    if any(log_entry.get(key) != value for key, value in shared.items()):
        return None, ["primary_recall_log_mismatch"]
    if log_entry.get("lineage_fingerprint") != lineage:
        return None, ["primary_recall_log_lineage_mismatch"]
    if log_entry.get("index_entry_id") != index_entry.get("entry_id"):
        return None, ["primary_recall_index_log_link_mismatch"]
    return {
        "path": relative,
        "idempotency_key": identity,
        "lineage_fingerprint": lineage,
        "page_digest": digest,
        "summary": summary,
        "title": title,
        "memory_kind": memory_kind,
        "namespace": expected_namespace,
        "source_event_kind": metadata["source_event_kind"],
    }, []


def _load_control_state(
    root: Path,
) -> tuple[dict[str, list[dict[str, Any]]] | None, list[str]]:
    index, index_reason = _read_markers(
        root, "memory/mem/index.md", "# Index", "relaymem-primary-index-entry-v0"
    )
    log, log_reason = _read_markers(
        root, "memory/mem/log.md", "# Log", "relaymem-primary-log-entry-v0"
    )
    reasons = [reason for reason in (index_reason, log_reason) if reason]
    if reasons:
        return None, reasons
    assert index is not None and log is not None
    if any(not _valid_index_entry(entry) for entry in index):
        return None, ["primary_recall_index_invalid"]
    if any(not _valid_log_entry(entry) for entry in log):
        return None, ["primary_recall_log_invalid"]
    return {"index": index, "log": log}, []


def _read_markers(
    root: Path,
    relative: str,
    header: str,
    marker: str,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    path = root / PurePosixPath(relative)
    if _contains_symlink(root, path) or not path.is_file():
        return None, "primary_recall_control_file_unsafe_or_missing"
    try:
        raw = path.read_bytes()
    except OSError:
        return None, "primary_recall_control_file_unreadable"
    if len(raw) > _MAX_CONTROL_BYTES:
        return None, "primary_recall_control_file_size_exceeded"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "primary_recall_control_file_utf8_invalid"
    lines = text.splitlines()
    if not lines or lines[0] != header:
        return None, "primary_recall_control_file_header_mismatch"
    prefix = f"<!-- {marker} "
    suffix = " -->"
    entries: list[dict[str, Any]] = []
    for line in lines[1:]:
        if line.lstrip().startswith("<!-- relaymem-primary-") and marker not in line:
            return None, "primary_recall_control_file_schema_conflict"
        if marker not in line:
            continue
        if len(line.encode("utf-8")) > _MAX_MARKER_LINE_BYTES:
            return None, "primary_recall_control_marker_too_large"
        if not line.startswith(prefix) or not line.endswith(suffix):
            return None, "primary_recall_control_marker_malformed"
        if len(entries) >= _MAX_MARKERS:
            return None, "primary_recall_control_marker_count_exceeded"
        payload = line[len(prefix) : -len(suffix)]
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:
            return None, "primary_recall_control_marker_malformed"
        if not isinstance(value, dict):
            return None, "primary_recall_control_marker_malformed"
        canonical = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        if canonical != payload:
            return None, "primary_recall_control_marker_noncanonical"
        entries.append(value)
    return entries, None


def _valid_index_entry(entry: Mapping[str, Any]) -> bool:
    expected_keys = {
        "schema_version", "entry_id", "page_relative_path", "memory_layer",
        "memory_kind", "target_category", "namespace", "source_event_kind",
        "promotion_policy", "safety_scope", "idempotency_key", "page_digest",
    }
    if set(entry) != expected_keys or any(not isinstance(value, str) or not value for value in entry.values()):
        return False
    if entry.get("schema_version") != _INDEX_SCHEMA:
        return False
    if not _valid_shared_control_entry(entry):
        return False
    expected = stable_hash(
        (
            "relaymem-primary-index-entry-v0",
            str(entry["idempotency_key"]),
            str(entry["page_digest"]),
            str(entry["page_relative_path"]),
        )
    )
    return entry.get("entry_id") == expected


def _valid_log_entry(entry: Mapping[str, Any]) -> bool:
    expected_keys = {
        "schema_version", "entry_id", "index_entry_id", "operation",
        "page_relative_path", "memory_layer", "memory_kind", "target_category",
        "namespace", "source_event_kind", "promotion_policy", "safety_scope",
        "lineage_fingerprint", "idempotency_key", "page_digest",
    }
    if set(entry) != expected_keys or any(not isinstance(value, str) or not value for value in entry.values()):
        return False
    if entry.get("schema_version") != _LOG_SCHEMA or entry.get("operation") != "primary_page_published":
        return False
    if not _valid_shared_control_entry(entry) or not is_sha256(entry.get("lineage_fingerprint")):
        return False
    expected_index = stable_hash(
        (
            "relaymem-primary-index-entry-v0",
            str(entry["idempotency_key"]),
            str(entry["page_digest"]),
            str(entry["page_relative_path"]),
        )
    )
    expected_log = stable_hash(
        (
            "relaymem-primary-log-entry-v0",
            str(entry["idempotency_key"]),
            str(entry["page_digest"]),
            str(entry["page_relative_path"]),
        )
    )
    return entry.get("index_entry_id") == expected_index and entry.get("entry_id") == expected_log


def _valid_shared_control_entry(entry: Mapping[str, Any]) -> bool:
    kind = entry.get("memory_kind")
    category = entry.get("target_category")
    identity = entry.get("idempotency_key")
    digest = entry.get("page_digest")
    relative = entry.get("page_relative_path")
    if (
        entry.get("memory_layer") != "primary"
        or entry.get("promotion_policy") != "free_to_update"
        or entry.get("safety_scope") != "ordinary_memory"
        or kind not in KIND_TARGET
        or category != KIND_TARGET[kind]
        or entry.get("source_event_kind") not in EVENT_KINDS
        or _token(entry.get("namespace")) is None
        or not is_sha256(identity)
        or not is_sha256(digest)
    ):
        return False
    expected_path = f"{TARGET_DIR[str(category)]}/{identity}.md"
    return relative == expected_path and _primary_relative_path(str(relative))


def _safe_root(value: object) -> Path | None:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        return None
    path = Path(value)
    if _path_has_symlink_component(path) or not path.exists() or not path.is_dir():
        return None
    try:
        return path.resolve(strict=True)
    except OSError:
        return None


def _path_has_symlink_component(path: Path) -> bool:
    absolute = path if path.is_absolute() else Path.cwd() / path
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _contains_symlink(root: Path, target: Path) -> bool:
    try:
        parts = target.relative_to(root).parts
    except ValueError:
        return True
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            return True
    try:
        resolved = target.resolve(strict=False)
    except OSError:
        return True
    return resolved != root and root not in resolved.parents


def _primary_relative_path(value: str) -> bool:
    if not value or value.startswith("/") or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return (
        path.as_posix() == value
        and value.endswith(".md")
        and all(part not in {"", ".", ".."} for part in path.parts)
        and any(value.startswith(f"{directory}/") for directory in _PRIMARY_DIRS)
    )


def _token(value: object) -> str | None:
    if not isinstance(value, str) or _TOKEN_RE.fullmatch(value) is None or bad_text(value):
        return None
    return value


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
        normalized = value if re.fullmatch(r"[a-z0-9][a-z0-9_:-]{0,127}", value) else "invalid_reason_id"
        if normalized not in output:
            output.append(normalized)
        if len(output) >= 32:
            break
    return output


__all__ = [
    "PROJECTION_SCHEMA",
    "RUNTIME_SCHEMA",
    "apply_relaymem_primary_recall_scope",
    "resolve_relaymem_character_store_root",
]
