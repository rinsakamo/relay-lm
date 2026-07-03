"""RelaySCN MVP scene-policy dry-run helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.scene_classifier import build_scene_classifier_candidate, scene_classifier_public_projection

KNOWN_SCENE_TYPES = {
    "unknown", "casual_chat", "design_talk", "implementation_work", "review_work",
    "formal_document", "medical_or_safety", "system_ops", "vtuber_roleplay",
    "recovery", "memory_management", "character_workspace",
}
LOW_CONFIDENCE_THRESHOLD = 0.70
LOW_STABILITY_THRESHOLD = 0.65
_RESTRICTIVE_HEURISTIC_SCENE_TYPES = {"medical_or_safety", "formal_document", "recovery"}
_AUTHORITATIVE_SCENE_STATE_SOURCES = {"request_metadata", "trusted_explicit", "trusted_route", "trusted_tool_signal", "confirmed_user_action"}


def _policy(relayctx_mode: str, relaymem_scope: str, relaymem_gate: str, relaysoul_gate: str, *, relayemo: str = "suppressed", slp: str = "optional", confirm: bool = False) -> dict[str, Any]:
    return {
        "relayctx_mode": relayctx_mode,
        "relayemo_marker_policy": relayemo,
        "relayemo_expression_policy": relayemo,
        "relaymem_retrieval_scope": relaymem_scope,
        "relaymem_update_gate": relaymem_gate,
        "relaysoul_update_gate": relaysoul_gate,
        "slp_mode": slp,
        "user_confirmation_required": confirm,
        "output_rewrite_allowed": False,
    }


_FAIL_CLOSED_UNKNOWN_POLICY = _policy("context_repair", "current_context_only", "blocked", "blocked", slp="recommended", confirm=True)
_POLICY_BY_SCENE_TYPE: dict[str, dict[str, Any]] = {
    "casual_chat": _policy("light_context", "relationship_or_recent", "dry_run_only", "blocked", relayemo="allowed"),
    "design_talk": _policy("design_compact", "project_context", "allowed_dry_run", "proposal_only", relayemo="light"),
    "implementation_work": _policy("repo_task_compact", "project_context", "allowed_dry_run", "blocked", relayemo="suppressed_or_light"),
    "review_work": _policy("review_strict", "current_project_only", "allowed_dry_run", "blocked", slp="recommended"),
    "formal_document": _policy("formal_output", "evidence_only", "blocked", "blocked"),
    "medical_or_safety": _policy("safety_cautious", "minimal_or_evidence_only", "blocked", "blocked", slp="recommended"),
    "system_ops": _policy("ops_precise", "project_or_ops_context", "dry_run_only", "blocked", relayemo="suppressed_or_light"),
    "vtuber_roleplay": _policy("character_context", "character_or_relationship", "dry_run_only", "proposal_only", relayemo="allowed"),
    "memory_management": _policy("memory_governance_compact", "current_context_only", "blocked", "blocked", slp="recommended", confirm=True),
    "character_workspace": _policy("workspace_compact", "current_context_only", "blocked", "blocked"),
    "recovery": _policy("context_repair", "current_context_only", "blocked", "blocked", slp="forced_or_recently_attempted", confirm=True),
}


def build_relayscn_scene_policy_artifact(*, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    explicit_scene_state = _extract_explicit_scene_state(payload)
    classifier_candidate = _build_classifier_candidate(payload)
    if explicit_scene_state is not None:
        scene_state = explicit_scene_state
        source = "request_metadata"
    else:
        scene_state, source = _scene_state_from_classifier_candidate(classifier_candidate)
    scene_state = _normalize_scene_state(scene_state, source=source)
    scene_policy, persistence_reasons = _build_scene_policy(scene_state)
    classifier_public = scene_classifier_public_projection(classifier_candidate)
    return {
        "schema_version": "relayscn.scene_policy_artifact.v0",
        "diagnostics_only": True,
        "content_free": True,
        "scene_state_source": source,
        "scene_state": scene_state,
        "scene_policy": scene_policy,
        "persistence_block": scene_policy["persistence_block"],
        "persistence_block_reasons": persistence_reasons,
        "diagnostics_required": scene_policy["diagnostics_required"],
        "scene_classifier_candidate_present": classifier_public["candidate_present"],
        "scene_classifier_candidate_public": classifier_public,
        "scene_wiki_match": classifier_candidate.get("scene_wiki_match"),
    }


def _extract_explicit_scene_state(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    metadata = payload.get("metadata")
    candidates: list[Any] = []
    if isinstance(metadata, Mapping):
        relayscn = metadata.get("relayscn")
        if isinstance(relayscn, Mapping):
            candidates.extend([relayscn.get("scene_state"), relayscn])
        candidates.extend([metadata.get("scene_state"), metadata])
    candidates.append(payload.get("scene_state"))
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            scene_type = candidate.get("scene_type") or candidate.get("type")
            if isinstance(scene_type, str) and scene_type:
                return dict(candidate)
    return None


def _build_classifier_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_candidate = payload.get("scene_classifier_candidate")
    if not isinstance(raw_candidate, Mapping):
        metadata = payload.get("metadata")
        if isinstance(metadata, Mapping):
            relayscn = metadata.get("relayscn")
            if isinstance(relayscn, Mapping) and isinstance(relayscn.get("scene_classifier_candidate"), Mapping):
                raw_candidate = relayscn.get("scene_classifier_candidate")
            elif isinstance(metadata.get("scene_classifier_candidate"), Mapping):
                raw_candidate = metadata.get("scene_classifier_candidate")
    return build_scene_classifier_candidate(
        candidate=raw_candidate if isinstance(raw_candidate, Mapping) else None,
        payload=payload,
        scene_wiki_definitions=_extract_scene_wiki_definitions(payload),
    )


def _extract_scene_wiki_definitions(payload: Mapping[str, Any]) -> Sequence[Mapping[str, Any]] | None:
    definitions = payload.get("scene_wiki_definitions")
    if isinstance(definitions, Sequence) and not isinstance(definitions, str):
        return [item for item in definitions if isinstance(item, Mapping)]
    metadata = payload.get("metadata")
    if isinstance(metadata, Mapping):
        relayscn = metadata.get("relayscn")
        if isinstance(relayscn, Mapping):
            relayscn_definitions = relayscn.get("scene_wiki_definitions")
            if isinstance(relayscn_definitions, Sequence) and not isinstance(relayscn_definitions, str):
                return [item for item in relayscn_definitions if isinstance(item, Mapping)]
        metadata_definitions = metadata.get("scene_wiki_definitions")
        if isinstance(metadata_definitions, Sequence) and not isinstance(metadata_definitions, str):
            return [item for item in metadata_definitions if isinstance(item, Mapping)]
    return None


def _scene_state_from_classifier_candidate(classifier_candidate: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    scene_type = classifier_candidate.get("candidate_scene_type")
    if not isinstance(scene_type, str):
        scene_type = "unknown"
    source = _relayscn_source_from_classifier_candidate(classifier_candidate)
    return ({
        "schema_version": "relayscn.scene_state.v0",
        "scene_type": scene_type,
        "confidence": _coerce_probability(classifier_candidate.get("confidence"), default=0.35),
        "stability": _coerce_probability(classifier_candidate.get("stability"), default=0.35),
        "signals": [_signal_from_classifier_candidate(classifier_candidate)],
    }, source)


def _signal_from_classifier_candidate(classifier_candidate: Mapping[str, Any]) -> str:
    scene_type = classifier_candidate.get("candidate_scene_type")
    if scene_type in KNOWN_SCENE_TYPES and scene_type != "unknown":
        return f"keyword:{scene_type}"
    if classifier_candidate.get("match_strength") in {"medium", "strong"}:
        return "scene_wiki_candidate_match"
    return "heuristic_default"


def _relayscn_source_from_classifier_candidate(classifier_candidate: Mapping[str, Any]) -> str:
    if classifier_candidate.get("can_open_runtime_policy") is True:
        source = classifier_candidate.get("source")
        if isinstance(source, str) and source in _AUTHORITATIVE_SCENE_STATE_SOURCES:
            return source
    return "heuristic"


def _normalize_scene_state(raw_scene_state: Mapping[str, Any], *, source: str) -> dict[str, Any]:
    raw_scene_type = raw_scene_state.get("scene_type") or raw_scene_state.get("type")
    scene_type = raw_scene_type if isinstance(raw_scene_type, str) and raw_scene_type else "unknown"
    if scene_type not in KNOWN_SCENE_TYPES:
        scene_type = "unknown"
    confidence = _coerce_probability(raw_scene_state.get("confidence"), default=0.35)
    stability = _coerce_probability(raw_scene_state.get("stability"), default=0.35)
    if scene_type == "unknown":
        confidence = min(confidence, 0.35)
        stability = min(stability, 0.35)
    signals = raw_scene_state.get("signals")
    normalized_signals = [_normalize_content_free_signal(x, source=source) for x in signals] if isinstance(signals, Sequence) and not isinstance(signals, str) else []
    normalized_signals = list(dict.fromkeys(normalized_signals))
    if scene_type == "unknown" and "unknown_scene_fail_closed" not in normalized_signals:
        normalized_signals.append("unknown_scene_fail_closed")
    if source == "heuristic" and not normalized_signals:
        normalized_signals.append("heuristic_default")
    source_authoritative = source in _AUTHORITATIVE_SCENE_STATE_SOURCES
    return {
        "schema_version": "relayscn.scene_state.v0",
        "scene_type": scene_type,
        "confidence": confidence,
        "stability": stability,
        "signals": normalized_signals,
        "is_estimate": not source_authoritative,
        "scene_state_authority": "authoritative" if source_authoritative else "heuristic",
        "source_authoritative": source_authoritative,
        "recovery_mode": raw_scene_state.get("recovery_mode") is True,
        "user_confirmation_required": raw_scene_state.get("user_confirmation_required") is True,
    }


def _normalize_content_free_signal(signal: Any, *, source: str) -> str:
    signal_text = str(signal)
    allowed_exact = {"unknown_scene_fail_closed", "heuristic_default", "missing_message_metadata", "slp_confusion_unresolved", "contradiction_detected", "unresolved_reference_detected", "output_generated_from_recovery_context", "scene_wiki_candidate_match"}
    if signal_text in allowed_exact:
        return signal_text
    if source == "heuristic" and (signal_text.startswith("keyword:") or signal_text.startswith("heuristic_fallback:")):
        suffix = signal_text.split(":", 1)[1]
        if suffix in KNOWN_SCENE_TYPES:
            return signal_text
    return "redacted_signal"


def _build_scene_policy(scene_state: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    scene_type = scene_state.get("scene_type") if isinstance(scene_state.get("scene_type"), str) else "unknown"
    source_authoritative = scene_state.get("source_authoritative") is True
    heuristic_may_restrict = scene_state.get("is_estimate") is True and scene_type in _RESTRICTIVE_HEURISTIC_SCENE_TYPES
    if source_authoritative or heuristic_may_restrict:
        base_policy = _POLICY_BY_SCENE_TYPE.get(scene_type, _FAIL_CLOSED_UNKNOWN_POLICY)
        policy_authority = "authoritative" if source_authoritative else "heuristic_restrictive"
    else:
        base_policy = _FAIL_CLOSED_UNKNOWN_POLICY
        policy_authority = "heuristic_non_authoritative"
    policy = {"schema_version": "relayscn.scene_policy.v0", **base_policy, "policy_authority": policy_authority, "source_authoritative": source_authoritative}
    confidence = _coerce_probability(scene_state.get("confidence"), default=0.0)
    stability = _coerce_probability(scene_state.get("stability"), default=0.0)
    reasons: list[str] = []
    if scene_type == "unknown":
        reasons.append("unknown_scene")
    if scene_type == "recovery":
        reasons.append("scene_type_is_recovery")
    if scene_type == "medical_or_safety":
        reasons.append("scene_type_is_medical_or_safety")
    if scene_type == "formal_document":
        reasons.append("scene_type_is_formal_document")
    if policy_authority == "heuristic_non_authoritative":
        reasons.append("heuristic_scene_state_non_authoritative")
    if policy.get("user_confirmation_required") is True:
        reasons.append("user_confirmation_required")
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        reasons.append("confidence_below_threshold")
    if stability < LOW_STABILITY_THRESHOLD:
        reasons.append("stability_below_threshold")
    signals = scene_state.get("signals")
    signal_values = {str(x) for x in signals} if isinstance(signals, Sequence) and not isinstance(signals, str) else set()
    for signal, reason in (("slp_confusion_unresolved", "slp_confusion_unresolved"), ("contradiction_detected", "contradiction_detected"), ("unresolved_reference_detected", "unresolved_reference_detected"), ("output_generated_from_recovery_context", "output_generated_from_recovery_context")):
        if signal in signal_values:
            reasons.append(reason)
    reasons = list(dict.fromkeys(reasons))
    policy["persistence_block"] = bool(reasons) or policy.get("relaymem_update_gate") == "blocked"
    policy["persistence_block_reasons"] = reasons
    policy["diagnostics_required"] = True
    return policy, reasons


def _coerce_probability(value: Any, *, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float) and 0.0 <= float(value) <= 1.0:
        return float(value)
    return default
