"""RelayEMO MVP initial runtime helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import time
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
    llm_probe = build_llm_affect_probe_candidate(
        config=config,
        user_text=text,
        recent_assistant_text=latest_assistant_text(messages),
        scene_hint=scene_type,
    )
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
        "affect_probe_mode": config.relayemo_affect_probe_mode,
        "heuristic_user_affect_estimate": affect,
        "llm_user_affect_estimate_candidate": llm_probe.get("user_affect_estimate_candidate"),
        "llm_scene_state_candidate": llm_probe.get("scene_state_candidate"),
        "llm_affect_probe_meta": llm_probe.get("classifier_meta"),
        "llm_candidate_applied": False,
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


def latest_assistant_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "assistant" and isinstance(message.get("content"), str):
            return message["content"]
    return ""


def _clamp(v: Any, lo: float, hi: float) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, f))


def _is_numeric(v: Any) -> bool:
    if isinstance(v, bool):
        return False
    if not isinstance(v, (int, float)):
        return False
    return math.isfinite(float(v))


def build_llm_affect_probe_prompt(*, user_text: str, recent_assistant_text: str, scene_hint: str) -> str:
    return (
        "You are an affect probe. Estimate only, never assert certainty.\n"
        "Return JSON only with keys user_affect_estimate_candidate, scene_state_candidate, classifier_meta.\n"
        f"user_text: {user_text}\n"
        f"recent_assistant_text: {recent_assistant_text}\n"
        f"scene_hint: {scene_hint}\n"
    )


def parse_llm_affect_probe_output(raw_text: str) -> dict[str, Any]:
    errors: list[str] = []
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "user_affect_estimate_candidate": None,
            "scene_state_candidate": None,
            "classifier_meta": {
                "probe_mode": "llm_structured_dry_run",
                "applied": False,
                "skipped": False,
                "skip_reason": None,
                "parse_ok": False,
                "validation_errors": ["invalid_json"],
            },
        }
    cand_raw = payload.get("user_affect_estimate_candidate", {}) if isinstance(payload, dict) else {}
    scene_raw = payload.get("scene_state_candidate", {}) if isinstance(payload, dict) else {}
    if not isinstance(cand_raw, dict):
        errors.append("user_affect_estimate_candidate_not_object")
        cand = {}
    else:
        cand = cand_raw
    if not isinstance(scene_raw, dict):
        errors.append("scene_state_candidate_not_object")
        scene = {}
    else:
        scene = scene_raw
    scene_type = scene.get("scene_type")
    if scene_type not in SCENE_TYPES:
        errors.append("invalid_scene_type")
        scene_type = "unknown"
    if "confidence" not in scene:
        errors.append("missing_numeric_field:scene_state_candidate.confidence")
        scene_confidence = 0.0
    else:
        scene_confidence_raw = scene.get("confidence")
        if scene_confidence_raw is None or not _is_numeric(scene_confidence_raw):
            errors.append("invalid_numeric_field:scene_state_candidate.confidence")
            scene_confidence = 0.0
        else:
            scene_confidence = _clamp(scene_confidence_raw, 0.0, 1.0)
    numeric_fields = ("valence", "arousal", "dominance", "intensity", "confidence")
    for field in numeric_fields:
        if field not in cand:
            errors.append(f"missing_numeric_field:{field}")
            continue
        value = cand.get(field)
        if value is None or not _is_numeric(value):
            errors.append(f"invalid_numeric_field:{field}")

    parse_ok = len(errors) == 0
    if parse_ok:
        valence = _clamp(cand.get("valence"), -1.0, 1.0)
        arousal = _clamp(cand.get("arousal"), 0.0, 1.0)
        dominance = _clamp(cand.get("dominance"), -1.0, 1.0)
        intensity = _clamp(cand.get("intensity"), 0.0, 1.0)
        confidence = _clamp(cand.get("confidence"), 0.0, 1.0)
    else:
        valence = 0.0
        arousal = 0.0
        dominance = 0.0
        intensity = 0.0
        confidence = 0.0
    parsed = {
        "user_affect_estimate_candidate": {
            "valence": valence,
            "arousal": arousal,
            "dominance": dominance,
            "intensity": intensity,
            "confidence": confidence,
            "mode": str(cand.get("mode", "unknown")),
            "evidence_level": "llm_structured_dry_run",
            "is_estimate": True,
        },
        "scene_state_candidate": {
            "scene_type": scene_type,
            "confidence": scene_confidence,
        },
        "classifier_meta": {
            "probe_mode": "llm_structured_dry_run",
            "applied": False,
            "skipped": False,
            "skip_reason": None,
            "parse_ok": parse_ok,
            "validation_errors": errors,
        },
    }
    return parsed


def build_llm_affect_probe_candidate(
    *,
    config: RelayLMConfig,
    user_text: str,
    recent_assistant_text: str,
    scene_hint: str,
) -> dict[str, Any]:
    if not config.relayemo_llm_affect_probe_enabled or config.relayemo_affect_probe_mode != "llm_structured_dry_run":
        return {
            "user_affect_estimate_candidate": None,
            "scene_state_candidate": None,
            "classifier_meta": {
                "probe_mode": "llm_structured_dry_run",
                "applied": False,
                "skipped": True,
                "skip_reason": "probe_disabled_or_mode_not_selected",
                "parse_ok": False,
                "validation_errors": [],
            },
        }
    prompt = build_llm_affect_probe_prompt(
        user_text=user_text[: config.relayemo_llm_affect_probe_max_input_chars],
        recent_assistant_text=recent_assistant_text[: config.relayemo_llm_affect_probe_max_input_chars],
        scene_hint=scene_hint,
    )
    _ = prompt
    synthetic = json.dumps(
        {
            "user_affect_estimate_candidate": {
                "valence": 0.2,
                "arousal": 0.5,
                "dominance": 0.1,
                "intensity": 0.6,
                "confidence": 0.5,
                "mode": "light_positive_estimate",
            },
            "scene_state_candidate": {"scene_type": scene_hint, "confidence": 0.6},
        }
    )
    return parse_llm_affect_probe_output(synthetic)


_RELAYEMO_SESSION_STATE: dict[str, dict[str, Any]] = {}


def load_session_assistant_state(
    session_key: str,
    *,
    ttl_seconds: int,
) -> dict[str, Any] | None:
    entry = _RELAYEMO_SESSION_STATE.get(session_key)
    if not isinstance(entry, dict):
        return None
    ts = entry.get("updated_at")
    state = entry.get("assistant_state")
    if not isinstance(ts, (float, int)) or not isinstance(state, dict):
        _RELAYEMO_SESSION_STATE.pop(session_key, None)
        return None
    if time.time() - float(ts) > ttl_seconds:
        _RELAYEMO_SESSION_STATE.pop(session_key, None)
        return None
    return dict(state)


def save_session_assistant_state(
    session_key: str,
    assistant_state: dict[str, Any],
    *,
    max_entries: int,
) -> None:
    _RELAYEMO_SESSION_STATE[session_key] = {
        "assistant_state": dict(assistant_state),
        "updated_at": time.time(),
    }
    if len(_RELAYEMO_SESSION_STATE) <= max_entries:
        return
    for key, _ in sorted(
        _RELAYEMO_SESSION_STATE.items(),
        key=lambda item: float(item[1].get("updated_at", 0.0)),
    )[: max(0, len(_RELAYEMO_SESSION_STATE) - max_entries)]:
        _RELAYEMO_SESSION_STATE.pop(key, None)
