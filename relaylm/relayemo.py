"""RelayEMO MVP initial runtime helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from relaylm.config import RelayLMConfig


SCENE_TYPES = {
    "casual_chat",
    "design_talk",
    "implementation_work",
    "review_work",
    "formal_document",
    "medical_or_safety",
    "vtuber_roleplay",
    "unknown",
}


def latest_user_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user" and isinstance(message.get("content"), str):
            return message["content"]
    return ""


def estimate_user_affect(text: str) -> dict[str, Any]:
    low_conf = {"valence": 0.0, "arousal": 0.0, "dominance": 0.0, "intensity": 0.0, "confidence": 0.2}
    t = text.strip().lower()
    if not t:
        score = low_conf
        mode, evidence = "unknown", "none"
    elif (
        "!" in t
        or "！" in t
        or "嬉" in t
        or "楽" in t
        or "良い" in text
        or "いいね" in text
        or "最高" in text
        or "好き" in text
        or "楽しい" in text
        or "すごい" in text
        or "面白い" in text
        or "エモい" in text
    ):
        score = {"valence": 0.4, "arousal": 0.6, "dominance": 0.2, "intensity": 0.7, "confidence": 0.55}
        mode, evidence = "light_positive_estimate", "light_text_heuristic"
    elif "?" in t or "不安" in t or "心配" in t:
        score = {"valence": -0.2, "arousal": 0.35, "dominance": -0.2, "intensity": 0.45, "confidence": 0.5}
        mode, evidence = "uncertain_estimate", "light_text_heuristic"
    else:
        score = {"valence": 0.0, "arousal": 0.1, "dominance": 0.0, "intensity": 0.2, "confidence": 0.35}
        mode, evidence = "neutral_estimate", "light_text_heuristic"
    return {
        **score,
        "mode": mode,
        "evidence_level": evidence,
        "is_estimate": True,
    }


def infer_scene_type(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["仕様", "設計", "design"]):
        return "design_talk"
    if any(k in t for k in ["実装", "コード", "fix", "bug", "implement"]):
        return "implementation_work"
    if any(k in t for k in ["レビュー", "review", "pr"]):
        return "review_work"
    if any(k in t for k in ["医療", "安全", "safety", "medical"]):
        return "medical_or_safety"
    if any(k in t for k in ["文書", "formal", "proposal", "report"]):
        return "formal_document"
    if any(k in t for k in ["vtuber", "配信", "roleplay"]):
        return "vtuber_roleplay"
    if t.strip():
        return "casual_chat"
    return "unknown"


@dataclass(frozen=True)
class RelayEmoRuntimeResult:
    artifact: dict[str, Any]
    assistant_state: dict[str, Any]


def run_relayemo(
    *,
    config: RelayLMConfig,
    messages: list[dict[str, Any]],
    previous_assistant_state: dict[str, Any] | None = None,
) -> RelayEmoRuntimeResult:
    text = latest_user_text(messages)
    affect = estimate_user_affect(text)
    scene_type = infer_scene_type(text)
    previous = previous_assistant_state or {
        "valence": 0.0, "arousal": 0.0, "dominance": 0.0, "intensity": 0.0, "mode": "neutral",
        "stability": 1.0, "updated_by": "init",
    }
    delta = 0.2
    decay = 0.05
    confidence = float(affect.get("confidence", 0.0))
    if previous_assistant_state is None and confidence >= 0.4:
        next_state = dict(previous)
        next_state["valence"] = float(affect.get("valence", 0.0))
        next_state["arousal"] = float(affect.get("arousal", 0.0))
        next_state["dominance"] = float(affect.get("dominance", 0.0))
        next_state["intensity"] = float(affect.get("intensity", 0.0))
        next_state["updated_by"] = "bootstrap_from_user_affect_estimate"
    elif confidence < 0.4:
        next_state = dict(previous)
        next_state["intensity"] = max(0.0, float(previous.get("intensity", 0.0)) - decay)
        next_state["updated_by"] = "decay_only"
    else:
        next_state = dict(previous)
        for k in ("valence", "arousal", "dominance", "intensity"):
            cur = float(previous.get(k, 0.0))
            target = float(affect.get(k, 0.0))
            step = max(-delta, min(delta, target - cur))
            next_state[k] = cur + step
        next_state["updated_by"] = "user_affect_estimate"
    next_state["mode"] = "expressive_support_estimate"
    next_state["stability"] = max(0.0, min(1.0, 1.0 - abs(float(next_state["intensity"]) - float(previous.get("intensity", 0.0)))))

    artifact: dict[str, Any] = {
        "user_affect_estimate": affect,
        "assistant_emotion_state": next_state,
        "scene_state": {"scene_type": scene_type},
        "text_marker_preview": {
            "gate_open": False,
            "marker": "",
            "marker_count": 0,
            "placement": "postfix_replace_punctuation",
            "applied_to_text": False,
            "suppression_reason": "relayemo_disabled_or_scene_gate",
        },
        "text_marker_apply": {
            "applied_to_text": False,
            "applied_to_soul": False,
            "applied_to_mem": False,
            "applied_to_tts": False,
            "persisted_user_affect": False,
        },
        "user_affect_estimate_is_estimate": True,
    }
    return RelayEmoRuntimeResult(artifact=artifact, assistant_state=next_state)
