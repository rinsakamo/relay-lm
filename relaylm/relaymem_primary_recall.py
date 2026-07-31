"""Public facade for scoped Primary MEM recall."""

from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from typing import Any
from .relaymem_primary_recall_store import (
    _load_control_state,
    _load_validated_page,
    _safe_root,
    _token,
    resolve_relaymem_character_store_root,
)
from .relaymem_primary_recall_selection import (
    PROJECTION_SCHEMA,
    RUNTIME_SCHEMA,
    _build_primary_recall_projection,
    _candidate_summary_score,
    _discover_scoped_primary_candidates_from_control,
    _fallback_no_candidate_trigger,
    _fallback_policy_blocker,
    _primary_recall_handoff_decision,
    _reason_ids,
    _replace_primary_recall_handoff,
    _sequence,
    run_primary_recall_selection,
)


def prepare_primary_recall_selection(
    artifact, root, namespace, max_candidates, max_chars, budget, chars_per_token
):
    reasons = []
    if root is None:
        reasons.append("character_store_scope_unavailable")
    if namespace is None:
        reasons.append("memory_namespace_invalid")
    decision = artifact.get("snippet_apply_decision")
    decision = decision if isinstance(decision, str) else ""
    gate_allowed = decision in {"eligible_but_not_applied", "dry_run_only"}
    candidates = _sequence(artifact.get("selected_mem_candidates"))
    if not candidates:
        reasons.append("existing_retrieval_selected_no_candidates")
    no_candidate = _fallback_no_candidate_trigger(
        original_decision=decision, artifact=artifact, candidates=candidates
    )
    blocker = _fallback_policy_blocker(artifact=artifact, original_decision=decision)
    considered = gate_allowed or no_candidate
    fallback_allowed = (
        root is not None and namespace is not None and considered and blocker is None
    )
    if not gate_allowed and not fallback_allowed:
        reasons.append("existing_retrieval_gate_blocked")
    if considered and blocker is not None:
        reasons.append(blocker)
    return {
        "reasons": reasons,
        "decision": decision,
        "gate_allowed": gate_allowed,
        "fallback_allowed": fallback_allowed,
        "no_candidate": no_candidate,
        "candidates": candidates,
        "max_candidates": max(0, int(max_candidates)),
        "max_chars": max(1, int(max_chars)),
        "budget": max(1, int(budget)),
        "chars_per_token": max(1, int(chars_per_token)),
    }


def compose_primary_recall_results(artifact, attempted, root, namespace, state, result):
    selected, used_tokens, discovery_attempted, discovered_count, discovery_status = (
        result
    )
    reasons = _reason_ids(state["reasons"])
    decision = _primary_recall_handoff_decision(
        original_decision=state["decision"],
        artifact=artifact,
        selected=selected,
        discovery_attempted=discovery_attempted,
        fallback_no_candidate_trigger=state["no_candidate"],
    )
    _replace_primary_recall_handoff(
        artifact,
        selected,
        original_decision=decision,
        snippet_budget=state["budget"],
        reasons=reasons,
    )
    artifact["primary_recall_runtime"] = {
        "schema_version": RUNTIME_SCHEMA,
        "runtime_private": True,
        "content_included": bool(selected),
        "request_local": True,
        "primary_candidate_discovery_attempted": discovery_attempted,
        "primary_candidate_count": discovered_count,
        "discovery_status": discovery_status if discovery_attempted else "ready",
        "selected_count": len(selected),
        "selected_memories": selected,
        "blocked_reason_ids": reasons,
    }
    artifact["primary_recall_projection"] = _build_primary_recall_projection(
        artifact=artifact,
        attempted=attempted,
        root=root,
        namespace=namespace,
        selected=selected,
        used_tokens=used_tokens,
        reasons=reasons,
        discovery_attempted=discovery_attempted,
        discovered_count=discovered_count,
    )
    return artifact


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
    """Narrow an existing M2 artifact to exact scoped Primary MEM evidence."""
    artifact = deepcopy(dict(retrieval_artifact or {}))
    attempted = isinstance(retrieval_artifact, Mapping)
    root = _safe_root(scoped_store_root)
    namespace = _token(expected_namespace)
    state = prepare_primary_recall_selection(
        artifact,
        root,
        namespace,
        max_snippet_candidates,
        max_snippet_chars,
        snippet_budget,
        chars_per_token,
    )
    result = run_primary_recall_selection(artifact, root, namespace, state)
    return compose_primary_recall_results(
        artifact, attempted, root, namespace, state, result
    )


__all__ = [
    "apply_relaymem_primary_recall_scope",
    "resolve_relaymem_character_store_root",
]
