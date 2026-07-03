"""RelayREF MVP dry-run artifact helpers."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.reference_intent_analyzer import analyze_reference_intent, reference_intent_public_projection

LOW_CONFIDENCE_THRESHOLD = 0.70
LOW_STABILITY_THRESHOLD = 0.65


def build_relayref_dry_run_artifact(*, relayscn_artifact: Mapping[str, Any] | None, messages: Sequence[Mapping[str, Any]] | None = None, ctx_hints: Mapping[str, Any] | None = None) -> dict[str, Any]:
    messages = messages or []
    ctx_hints = ctx_hints or {}
    parsed = _parse_relayscn_artifact(relayscn_artifact)
    scene_state = parsed["scene_state"]
    scene_policy = parsed["scene_policy"]
    scene_type = scene_state.get("scene_type") if isinstance(scene_state, Mapping) else "unknown"
    confidence = _coerce_probability(scene_state.get("confidence"), default=0.0)
    stability = _coerce_probability(scene_state.get("stability"), default=0.0)
    reference_intent = analyze_reference_intent(messages=messages, ctx_hints=ctx_hints)
    unresolved_reference = bool(reference_intent["unresolved_reference_detected"])
    reasons: list[str] = []
    if parsed["malformed"]:
        reasons.append("malformed_relayscn_artifact")
    if scene_type == "recovery":
        reasons.append("recovery_scene")
    if scene_type == "unknown":
        reasons.append("unknown_scene")
    if unresolved_reference:
        reasons.append("unresolved_reference_detected")
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        reasons.append("scene_confidence_below_threshold")
    if stability < LOW_STABILITY_THRESHOLD:
        reasons.append("scene_stability_below_threshold")
    mode = _select_mode(scene_type=scene_type, malformed=parsed["malformed"], unresolved_reference=unresolved_reference, confidence=confidence, stability=stability)
    return {
        "schema_version": "relayref.dry_run_artifact.v0",
        "diagnostics_only": True,
        "mode": mode,
        "mode_reasons": list(dict.fromkeys(reasons)),
        "apply_allowed": False,
        "auto_resume_allowed": False,
        "scene_type": scene_type,
        "scene_confidence": confidence,
        "scene_stability": stability,
        "unresolved_reference_detected": unresolved_reference,
        "reference_intent_analyzer": reference_intent_public_projection(reference_intent),
        "persistence_guard": _build_persistence_guard(parsed),
        "ctx_handoff_guess": _extract_ctx_handoff_guess(ctx_hints),
        "context_rewrite": {"candidate": mode in {"context_repair", "suggest_reflect"}, "applied": False, "auto_resume_allowed": False},
        "forced_sleep_candidate": _build_forced_sleep_candidate(scene_policy),
    }


def _parse_relayscn_artifact(relayscn_artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(relayscn_artifact, Mapping):
        return {"malformed": True, "scene_state": {"scene_type": "unknown", "confidence": 0.0, "stability": 0.0}, "scene_policy": {}, "persistence_block": True, "persistence_block_reasons": ["malformed_relayscn_artifact"]}
    scene_state = relayscn_artifact.get("scene_state")
    scene_policy = relayscn_artifact.get("scene_policy")
    persistence_reasons = relayscn_artifact.get("persistence_block_reasons")
    return {
        "malformed": not isinstance(scene_state, Mapping) or not isinstance(scene_policy, Mapping),
        "scene_state": dict(scene_state) if isinstance(scene_state, Mapping) else {},
        "scene_policy": dict(scene_policy) if isinstance(scene_policy, Mapping) else {},
        "persistence_block": relayscn_artifact.get("persistence_block"),
        "persistence_block_reasons": [str(reason) for reason in persistence_reasons] if isinstance(persistence_reasons, Sequence) and not isinstance(persistence_reasons, str) else [],
    }


def _build_persistence_guard(parsed: Mapping[str, Any]) -> dict[str, Any]:
    reasons = parsed.get("persistence_block_reasons")
    safe_reasons = [str(reason) for reason in reasons] if isinstance(reasons, list) else []
    malformed = bool(parsed.get("malformed"))
    persistence_block = parsed.get("persistence_block")
    safe_block = persistence_block if isinstance(persistence_block, bool) else True
    if malformed and "malformed_relayscn_artifact" not in safe_reasons:
        safe_reasons.append("malformed_relayscn_artifact")
    return {"source": "relayscn_scene_policy_artifact", "persistence_block": safe_block or malformed, "persistence_block_reasons": safe_reasons, "safe_to_persist": not (safe_block or malformed)}


def _select_mode(*, scene_type: object, malformed: bool, unresolved_reference: bool, confidence: float, stability: float) -> str:
    if scene_type == "recovery":
        return "context_repair"
    if malformed or scene_type == "unknown" or unresolved_reference or confidence < LOW_CONFIDENCE_THRESHOLD or stability < LOW_STABILITY_THRESHOLD:
        return "suggest_reflect"
    return "none"


def _detect_unresolved_reference(messages: Sequence[Mapping[str, Any]]) -> bool:
    return bool(analyze_reference_intent(messages=messages)["unresolved_reference_detected"])


def _latest_user_text(messages: Sequence[Mapping[str, Any]]) -> str:
    for message in reversed(messages):
        if isinstance(message, Mapping) and message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, Sequence) and not isinstance(content, str):
                return "\n".join(item["text"] for item in content if isinstance(item, Mapping) and isinstance(item.get("text"), str))
    return ""


def _extract_ctx_handoff_guess(ctx_hints: Mapping[str, Any]) -> dict[str, Any] | None:
    raw = ctx_hints.get("ctx_handoff_guess")
    if raw is None:
        return None
    value = (raw.get("value") or raw.get("text") or raw.get("summary")) if isinstance(raw, Mapping) else raw
    if not isinstance(value, str) or not value:
        return None
    return {"value": value, "use_as": "confirmation_candidate", "auto_resume_allowed": False, "trusted_context": False}


def _build_forced_sleep_candidate(scene_policy: Mapping[str, Any]) -> dict[str, Any]:
    slp_mode = scene_policy.get("slp_mode") if isinstance(scene_policy, Mapping) else None
    candidate = slp_mode in {"forced", "forced_or_recently_attempted"}
    return {"candidate": candidate, "slp_mode": slp_mode if isinstance(slp_mode, str) else None, "apply_allowed": False, "reason": "relayscn_slp_mode" if candidate else None}


def _coerce_probability(value: Any, *, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        numeric = float(value)
        if 0.0 <= numeric <= 1.0:
            return numeric
    return default
