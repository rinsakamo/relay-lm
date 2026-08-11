"""Legacy M2 Retrieval dry-run artifact assembly."""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any
from relaylm._relaymem_retrieval_candidates import (
    _attach_evidence_metadata_to_ctx_block_candidate,
    _build_apply_readiness,
    _build_ctx_block_candidate,
    _build_ctx_injection_plan,
    _content_free_query_summary,
    _retrieval_priority_projection,
    _select_mem_candidates_dry_run,
)
from relaylm.retrieval.snippet import (
    _build_ctx_block_snippet_candidate,
    _build_snippet_apply_readiness,
    _build_snippet_evidence_dry_run,
    _build_snippet_runtime_injection_plan,
)
from relaylm.retrieval_query_analyzer import (
    analyze_retrieval_query,
    public_retrieval_query_projection,
    retrieval_query_backend_hints,
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
_JAPANESE_RECALL_PHRASES = (
    "朝の集中作業",
    "集中作業",
    "落ち着く",
    "落ち着き",
    "飲み物",
    "浅煎り",
    "エチオピアコーヒー",
    "エチオピア",
    "コーヒー",
    "紅茶",
)


def build_relaymem_retrieval_dry_run_artifact(
    *,
    relayscn_scene_policy_artifact: Mapping[str, Any] | None,
    relayint_intent_artifact: Mapping[str, Any] | None = None,
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
    relayint_unresolved = _relayint_unresolved_reference(relayint_intent_artifact)

    fallback_reason = _resolve_fallback_reason(
        malformed=parsed_scn["malformed"],
        scene_type=scene_type,
        retrieval_scope=retrieval_scope,
        relayint_unresolved=relayint_unresolved,
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
        relayint_unresolved=relayint_unresolved,
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
        relayint_unresolved=relayint_unresolved,
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
        relayint_unresolved=relayint_unresolved,
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
        relayint_unresolved=relayint_unresolved,
        discovery_blocked=discovery_blocked,
    )
    used_tokens = sum(
        int(candidate.get("estimated_tokens", 0))
        for candidate in selected_mem_candidates
    )
    latest_user_text = _latest_user_text(messages)
    retrieval_query_candidate_analysis = analyze_retrieval_query(
        latest_user_text,
        source="heuristic",
    )
    retrieval_query_backend_private_hints = retrieval_query_backend_hints(
        retrieval_query_candidate_analysis
    )

    return {
        "artifact_version": "relaymem_retrieval.v0",
        "diagnostics_only": True,
        "apply_allowed": False,
        "retrieval_scope": retrieval_scope,
        "scene_type": scene_type,
        "query_summary": _content_free_query_summary(
            latest_user_text=latest_user_text,
            retrieval_query_candidate=retrieval_query_candidate_analysis,
        ),
        "retrieval_query_candidate": public_retrieval_query_projection(
            retrieval_query_candidate_analysis
        ),
        "retrieval_query_private": {
            "schema_version": "relaymem.retrieval_query_private_hints.v0",
            "runtime_private": True,
            "content_free": False,
            "source": "retrieval_query_analyzer",
            "backend_private_hints": tuple(retrieval_query_backend_private_hints),
            "query_hint_count": len(retrieval_query_backend_private_hints),
        },
        "retrieval_priority": _retrieval_priority_projection(selected_mem_candidates),
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
    relayint_unresolved: bool,
    store_diagnostics: Mapping[str, Any] | None = None,
) -> str:
    if malformed or scene_type == "unknown":
        return "scene_policy_blocks_memory"
    if relayint_unresolved:
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
    relayint_unresolved: bool,
    discovery_blocked: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    if fallback_reason == "memory_store_not_configured":
        return []
    blocked = [{"reason": fallback_reason}]
    if scene_type in {"formal_document", "medical_or_safety"}:
        blocked.append({"reason": f"scene_type:{scene_type}"})
    if relayint_unresolved:
        blocked.append({"reason": "must_not_silently_resolve_ambiguous_reference"})
    blocked.extend(discovery_blocked or [])
    return blocked


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


def _relayint_unresolved_reference(
    relayint_intent_artifact: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(relayint_intent_artifact, Mapping):
        return False
    return relayint_intent_artifact.get("unresolved_reference_detected") is True


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
    analysis = analyze_retrieval_query(
        text,
        source="heuristic",
        max_hints=12,
    )
    terms = retrieval_query_backend_hints(analysis)

    for phrase in _JAPANESE_RECALL_PHRASES:
        if phrase in text or phrase in "\n".join(terms):
            _add_japanese_phrase(terms, phrase)
            if len(terms) >= 12:
                break
    return terms[:12]


def _add_japanese_phrase(terms: list[str], phrase: str) -> None:
    phrase = _clean_term(phrase)
    if len(phrase) < 2 or phrase in terms:
        return
    terms.append(phrase)


def _clean_term(term: str) -> str:
    return term.strip(".,!?。！？、:;()[]{}\"'")[:32]


def _normalize_token_budget(token_budget: int | None) -> dict[str, Any]:
    if isinstance(token_budget, int) and token_budget > 0:
        return {"limit": token_budget, "source": "runtime_config"}
    return {"limit": None, "source": "unspecified"}


def _normalize_reasons(reasons: Any) -> list[str]:
    if isinstance(reasons, Sequence) and not isinstance(reasons, str):
        return [str(reason) for reason in reasons]
    return []
