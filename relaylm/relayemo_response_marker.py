"""RelayEMO response text marker preview and application helpers."""

from __future__ import annotations

from typing import Any

from relaylm.config import RelayLMConfig


def build_relayemo_text_marker_preview(
    config: RelayLMConfig,
    relayemo_artifact: dict[str, Any],
) -> dict[str, Any]:
    scene_type = relayemo_artifact.get("scene_state", {}).get("scene_type", "unknown")
    affect = relayemo_artifact.get("user_affect_estimate", {})
    affect_mode = str(affect.get("mode", "unknown"))
    assistant_state = relayemo_artifact.get("assistant_emotion_state", {})
    intensity = float(assistant_state.get("intensity", 0.0))
    confidence = float(affect.get("confidence", 0.0))
    marker_map = {
        "light_positive_estimate": "✨",
        "playful_positive_estimate": "♪",
        "warm_positive_estimate": "☺️",
    }
    base_marker = marker_map.get(affect_mode, "")
    if scene_type in {"review_work", "formal_document", "medical_or_safety"}:
        return {"gate_open": False, "marker": "", "marker_count": 0, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": "scene_suppressed"}
    if confidence < 0.4:
        return {"gate_open": False, "marker": "", "marker_count": 0, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": "low_confidence"}
    if scene_type in {"implementation_work"}:
        preview_marker = base_marker or "✨"
        return {"gate_open": False, "marker": preview_marker, "marker_count": 1 if preview_marker else 0, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": "preview_only_scene"}
    gate_open = intensity >= config.relayemo_marker_open_threshold
    if not base_marker:
        gate_open = False
    marker_count = min(config.relayemo_max_markers, max(1, int(1 + intensity * 2))) if gate_open else 0
    return {"gate_open": gate_open, "marker": base_marker * marker_count if base_marker else "", "marker_count": marker_count, "placement": "postfix_replace_punctuation", "applied_to_text": False, "suppression_reason": None if gate_open else "below_open_threshold_or_no_marker"}


def apply_relayemo_marker_to_response(body: dict[str, Any], preview: dict[str, Any]) -> dict[str, Any]:
    if not preview.get("gate_open"):
        return body
    marker = preview.get("marker") or ""
    if not marker:
        return body
    choices = body.get("choices")
    if not isinstance(choices, list):
        return body
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, str) or not content:
            continue
        if content.endswith(("。", "！", "!", ".")):
            message["content"] = content[:-1] + marker
        elif content.endswith(("？", "?")):
            message["content"] = content + marker
        else:
            message["content"] = content + marker
    return body
