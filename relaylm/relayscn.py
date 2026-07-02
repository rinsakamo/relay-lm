"""RelaySCN MVP scene-policy dry-run helpers."""

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

LOW_CONFIDENCE_THRESHOLD = 0.70
LOW_STABILITY_THRESHOLD = 0.65

_POLICY_BY_SCENE_TYPE: dict[str, dict[str, Any]] = {
    "casual_chat": {
        "relayctx_mode": "light_context",
        "relayemo_marker_policy": "allowed",
        "relayemo_expression_policy": "allowed",
        "relaymem_retrieval_scope": "relationship_or_recent",
        "relaymem_update_gate": "dry_run_only",
        "relaysoul_update_gate": "blocked",
        "slp_mode": "optional",
        "user_confirmation_required": False,
        "output_rewrite_allowed": False,
    },
    "design_talk": {
        "relayctx_mode": "design_compact",
        "relayemo_marker_policy": "light",
        "relayemo_expression_policy": "light",
        "relaymem_retrieval_scope": "project_context",
        "relaymem_update_gate": "allowed_dry_run",
        "relaysoul_update_gate": "proposal_only",
        "slp_mode": "optional",
        "user_confirmation_required": False,
        "output_rewrite_allowed": False,
    },
    "implementation_work": {
        "relayctx_mode": "repo_task_compact",
        "relayemo_marker_policy": "suppressed_or_light",
        "relayemo_expression_policy": "suppressed_or_light",
        "relaymem_retrieval_scope": "project_context",
        "relaymem_update_gate": "allowed_dry_run",
        "relaysoul_update_gate": "blocked",
        "slp_mode": "optional",
        "user_confirmation_required": False,
        "output_rewrite_allowed": False,
    },
    "review_work": {
        "relayctx_mode": "review_strict",
        "relayemo_marker_policy": "suppressed",
        "relayemo_expression_policy": "suppressed",
        "relaymem_retrieval_scope": "current_project_only",
        "relaymem_update_gate": "allowed_dry_run",
        "relaysoul_update_gate": "blocked",
        "slp_mode": "recommended",
        "user_confirmation_required": False,
        "output_rewrite_allowed": False,
    },
    "formal_document": {
        "relayctx_mode": "formal_output",
        "relayemo_marker_policy": "suppressed",
        "relayemo_expression_policy": "suppressed",
        "relaymem_retrieval_scope": "evidence_only",
        "relaymem_update_gate": "blocked",
        "relaysoul_update_gate": "blocked",
        "slp_mode": "optional",
        "user_confirmation_required": False,
        "output_rewrite_allowed": False,
    },
    "medical_or_safety": {
        "relayctx_mode": "safety_cautious",
        "relayemo_marker_policy": "suppressed",
        "relayemo_expression_policy": "suppressed",
        "relaymem_retrieval_scope": "minimal_or_evidence_only",
        "relaymem_update_gate": "blocked",
        "relaysoul_update_gate": "blocked",
        "slp_mode": "recommended",
        "user_confirmation_required": False,
        "output_rewrite_allowed": False,
    },
    "system_ops": {
        "relayctx_mode": "ops_precise",
        "relayemo_marker_policy": "suppressed_or_light",
        "relayemo_expression_policy": "suppressed_or_light",
        "relaymem_retrieval_scope": "project_or_ops_context",
        "relaymem_update_gate": "dry_run_only",
        "relaysoul_update_gate": "blocked",
        "slp_mode": "optional",
        "user_confirmation_required": False,
        "output_rewrite_allowed": False,
    },
    "vtuber_roleplay": {
        "relayctx_mode": "character_context",
        "relayemo_marker_policy": "allowed",
        "relayemo_expression_policy": "allowed",
        "relaymem_retrieval_scope": "character_or_relationship",
        "relaymem_update_gate": "dry_run_only",
        "relaysoul_update_gate": "proposal_only",
        "slp_mode": "optional",
        "user_confirmation_required": False,
        "output_rewrite_allowed": False,
    },
    "recovery": {
        "relayctx_mode": "context_repair",
        "relayemo_marker_policy": "suppressed",
        "relayemo_expression_policy": "suppressed",
        "relaymem_retrieval_scope": "current_context_only",
        "relaymem_update_gate": "blocked",
        "relaysoul_update_gate": "blocked",
        "slp_mode": "forced_or_recently_attempted",
        "user_confirmation_required": True,
        "output_rewrite_allowed": False,
    },
}

_FAIL_CLOSED_UNKNOWN_POLICY = {
    "relayctx_mode": "context_repair",
    "relayemo_marker_policy": "suppressed",
    "relayemo_expression_policy": "suppressed",
    "relaymem_retrieval_scope": "current_context_only",
    "relaymem_update_gate": "blocked",
    "relaysoul_update_gate": "blocked",
    "slp_mode": "recommended",
    "user_confirmation_required": True,
    "output_rewrite_allowed": False,
}


def build_relayscn_scene_policy_artifact(
    *,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a diagnostics-only RelaySCN scene-policy artifact.

    RelaySCN owns normalized same-turn scene state. The MVP helper prefers
    explicit RelaySCN/request metadata, falls back to a lightweight text
    heuristic, and then fails closed for unknown or missing state. It never
    accepts RelayEMO affect artifacts as normalized scene-state input.
    """

    payload = payload or {}
    explicit_scene_state = _extract_explicit_scene_state(payload)

    if explicit_scene_state is not None:
        scene_state = explicit_scene_state
        source = "request_metadata"
    else:
        scene_type, confidence, stability, heuristic_reason = _estimate_scene_from_messages(payload)
        scene_state = {
            "schema_version": "relayscn.scene_state.v0",
            "scene_type": scene_type,
            "confidence": confidence,
            "stability": stability,
            "signals": [heuristic_reason],
        }
        source = "heuristic"

    scene_state = _normalize_scene_state(scene_state, source=source)
    scene_policy, persistence_reasons = _build_scene_policy(scene_state)

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
        if not isinstance(candidate, Mapping):
            continue
        scene_type = candidate.get("scene_type") or candidate.get("type")
        if isinstance(scene_type, str) and scene_type:
            return dict(candidate)
    return None


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
    normalized_signals = (
        [str(x) for x in signals]
        if isinstance(signals, Sequence) and not isinstance(signals, str)
        else []
    )
    if scene_type == "unknown" and "unknown_scene_fail_closed" not in normalized_signals:
        normalized_signals.append("unknown_scene_fail_closed")
    if source == "heuristic" and not normalized_signals:
        normalized_signals.append("heuristic_default")

    return {
        "schema_version": str(raw_scene_state.get("schema_version") or "relayscn.scene_state.v0"),
        "scene_type": scene_type,
        "confidence": confidence,
        "stability": stability,
        "signals": normalized_signals,
        "is_estimate": source != "request_metadata",
        "recovery_mode": raw_scene_state.get("recovery_mode") is True,
        "user_confirmation_required": raw_scene_state.get("user_confirmation_required") is True,
    }


def _build_scene_policy(scene_state: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    scene_type = (
        scene_state.get("scene_type")
        if isinstance(scene_state.get("scene_type"), str)
        else "unknown"
    )
    base_policy = _POLICY_BY_SCENE_TYPE.get(scene_type, _FAIL_CLOSED_UNKNOWN_POLICY)
    policy = {"schema_version": "relayscn.scene_policy.v0", **base_policy}

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
    if policy.get("user_confirmation_required") is True:
        reasons.append("user_confirmation_required")
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        reasons.append("confidence_below_threshold")
    if stability < LOW_STABILITY_THRESHOLD:
        reasons.append("stability_below_threshold")

    signals = scene_state.get("signals")
    signal_values = (
        {str(x) for x in signals}
        if isinstance(signals, Sequence) and not isinstance(signals, str)
        else set()
    )
    for signal, reason in (
        ("slp_confusion_unresolved", "slp_confusion_unresolved"),
        ("contradiction_detected", "contradiction_detected"),
        ("unresolved_reference_detected", "unresolved_reference_detected"),
        ("output_generated_from_recovery_context", "output_generated_from_recovery_context"),
    ):
        if signal in signal_values:
            reasons.append(reason)

    reasons = list(dict.fromkeys(reasons))
    policy["persistence_block"] = bool(reasons) or policy.get("relaymem_update_gate") == "blocked"
    policy["persistence_block_reasons"] = reasons
    policy["diagnostics_required"] = True
    return policy, reasons


def _estimate_scene_from_messages(payload: Mapping[str, Any]) -> tuple[str, float, float, str]:
    text = _latest_user_text(payload).lower()
    if not text:
        return "unknown", 0.35, 0.35, "missing_message_metadata"

    if (
        text.strip() == "pr"
        or "prを確認" in text
        or "check pr" in text
        or "check the pr" in text
    ):
        return "review_work", 0.78, 0.72, "keyword:review_work"

    checks = [
        (
            "recovery",
            ("confused", "lost", "戻る", "わから", "混乱", "文脈", "context repair"),
            0.82,
            0.78,
        ),
        (
            "medical_or_safety",
            ("medical", "doctor", "病院", "薬", "医療", "危険", "安全", "safety", "legal"),
            0.82,
            0.78,
        ),
        (
            "formal_document",
            ("formal", "report", "契約", "公的", "公式", "論文", "文書", "document"),
            0.80,
            0.76,
        ),
        ("review_work", ("review", "pr ", "pr#", "diff", "レビュー", "検証"), 0.78, 0.72),
        (
            "implementation_work",
            (
                "implement",
                "code",
                "コード",
                "repo",
                "file",
                "bug",
                "error",
                "fix ",
                "fix this",
                "ファイル",
                "実装",
                "実装して",
                "修正",
                "修正して",
                "バグ",
                "直して",
                "commit",
            ),
            0.78,
            0.72,
        ),
        (
            "system_ops",
            ("git ", "github", "remote", "push", "branch", "環境", "設定"),
            0.76,
            0.70,
        ),
        (
            "design_talk",
            ("design", "architecture", "設計", "仕様", "policy", "mvp"),
            0.74,
            0.70,
        ),
        (
            "vtuber_roleplay",
            ("vtuber", "live2d", "tts", "roleplay", "ロールプレイ", "配信"),
            0.74,
            0.70,
        ),
    ]
    for scene_type, needles, confidence, stability in checks:
        if any(needle in text for needle in needles):
            return scene_type, confidence, stability, f"keyword:{scene_type}"
    return "casual_chat", 0.62, 0.60, "heuristic_fallback:casual_chat"


def _latest_user_text(payload: Mapping[str, Any]) -> str:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, Mapping) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, Mapping) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts)
    return ""


def _coerce_probability(value: Any, *, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        if 0.0 <= float(value) <= 1.0:
            return float(value)
    return default
