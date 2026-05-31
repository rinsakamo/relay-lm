"""RelayMEM Retrieval MVP dry-run artifact helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


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


def build_relaymem_retrieval_dry_run_artifact(
    *,
    relayscn_scene_policy_artifact: Mapping[str, Any] | None,
    relayref_artifact: Mapping[str, Any] | None = None,
    messages: Sequence[Mapping[str, Any]] | None = None,
    token_budget: int | None = None,
    store_diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a diagnostics-only RelayMEM runtime retrieval artifact.

    This MVP does not search a long-term memory store. It only exposes the
    scene-policy-derived retrieval posture that a future read path can consume.
    """

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
    blocked = _build_blocked_reasons(
        fallback_reason=fallback_reason,
        scene_type=scene_type,
        relayref_unresolved=relayref_unresolved,
    )

    return {
        "artifact_version": "relaymem_retrieval.v0",
        "diagnostics_only": True,
        "apply_allowed": False,
        "retrieval_scope": retrieval_scope,
        "scene_type": scene_type,
        "query_summary": _build_query_summary(messages),
        "selected": [],
        "blocked": blocked,
        "ctx_block": None,
        "fallback_reason": fallback_reason,
        "token_budget": _normalize_token_budget(token_budget),
        "used_tokens": 0,
        "persistence_block": persistence_block,
        "persistence_block_reasons": persistence_block_reasons,
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
) -> list[dict[str, str]]:
    if fallback_reason == "memory_store_not_configured":
        return []
    blocked = [{"reason": fallback_reason}]
    if scene_type in {"formal_document", "medical_or_safety"}:
        blocked.append({"reason": f"scene_type:{scene_type}"})
    if relayref_unresolved:
        blocked.append({"reason": "must_not_silently_resolve_ambiguous_reference"})
    return blocked


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
