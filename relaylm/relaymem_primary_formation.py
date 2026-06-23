"""RelayMEM primary memory formation candidate helpers.

MEM-M3a is helper-only. It classifies whether governed experience evidence could
become Primary MEM, but it does not write memory, mutate RelaySOUL, invoke SLP,
or expose raw message text in its public projection.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any

_SCHEMA_VERSION = "relaymem.primary_formation_dry_run.v0"
_PROJECTION_SCHEMA_VERSION = "relaymem.primary_formation_projection.v0"
_MAX_CANDIDATE_ID = 128
_KNOWN_SCENE_TYPES = {
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
_SCENE_BLOCK_REASONS = {
    "formal_document": "scene_policy_blocks_persistence:formal_document",
    "medical_or_safety": "scene_policy_blocks_persistence:medical_or_safety",
    "recovery": "scene_policy_blocks_persistence:recovery",
}


def build_relaymem_primary_formation_dry_run(
    *,
    relayscn_scene_policy_artifact: Mapping[str, Any] | None,
    relayemo_artifact: Mapping[str, Any] | None = None,
    messages: Sequence[Mapping[str, Any]] | None = None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
    source_event_kind: str = "turn",
    candidate_id: str = "primary_candidate:0",
) -> dict[str, Any]:
    """Build Primary MEM formation candidates without applying them.

    ``candidate_id`` is content-free identity supplied by the exact governed
    experience owner. The historical fixed value remains the compatibility
    default for direct helper callers.
    """

    parsed_scn = _parse_relayscn(relayscn_scene_policy_artifact)
    safe_messages = [
        message for message in messages or [] if isinstance(message, Mapping)
    ]
    source_summary = _source_summary(safe_messages)
    salience_band = _salience_band(relayemo_artifact)
    stability_band = _stability_band(parsed_scn)
    safe_candidate_id, candidate_id_reasons = _candidate_identifier(candidate_id)
    blocked_reasons = _dedupe(
        candidate_id_reasons
        + _blocked_reasons(
            enabled=enabled,
            parsed_scn=parsed_scn,
            source_summary=source_summary,
        )
    )
    candidates: list[dict[str, Any]] = []
    if not blocked_reasons:
        candidates.append(
            _candidate(
                candidate_id=safe_candidate_id,
                parsed_scn=parsed_scn,
                source_summary=source_summary,
                salience_band=salience_band,
                stability_band=stability_band,
                source_event_kind=source_event_kind,
            )
        )

    projection = _projection(
        candidates=candidates,
        blocked_reasons=blocked_reasons,
        parsed_scn=parsed_scn,
        source_summary=source_summary,
    )
    return {
        "schema_version": _SCHEMA_VERSION,
        "diagnostics_only": True,
        "helper_only": True,
        "read_only": True,
        "enabled": bool(enabled),
        "dry_run_only": bool(dry_run_only),
        "apply_enabled": bool(apply_enabled),
        "apply_allowed": False,
        "writes_memory": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "lab_api_exposed": False,
        "source_event_kind": _safe_enum(source_event_kind, "turn"),
        "scene_type": parsed_scn["scene_type"],
        "source_summary": source_summary,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "blocked_reasons": blocked_reasons,
        "projection": projection,
    }


def _candidate_identifier(value: object) -> tuple[str, list[str]]:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not 0 < len(value) <= _MAX_CANDIDATE_ID
        or not all(
            character.isascii()
            and (character.isalnum() or character in "-_.:/")
            for character in value
        )
    ):
        return "", ["primary_candidate_id_invalid"]
    return value, []


def _parse_relayscn(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return _malformed_scene_policy()
    scene_state = artifact.get("scene_state")
    scene_policy = artifact.get("scene_policy")
    if not isinstance(scene_state, Mapping) or not isinstance(scene_policy, Mapping):
        return _malformed_scene_policy()
    scene_type = scene_state.get("scene_type")
    if not isinstance(scene_type, str) or scene_type not in _KNOWN_SCENE_TYPES:
        scene_type = "unknown"
    persistence_reasons = _string_list(artifact.get("persistence_block_reasons"))
    for reason in _string_list(scene_policy.get("persistence_block_reasons")):
        if reason not in persistence_reasons:
            persistence_reasons.append(reason)
    persistence_block = artifact.get("persistence_block") is True
    if scene_policy.get("persistence_block") is True:
        persistence_block = True
    return {
        "malformed": False,
        "scene_type": scene_type,
        "persistence_block": persistence_block,
        "persistence_block_reasons": persistence_reasons,
        "confidence": scene_state.get("confidence"),
        "stability": scene_state.get("stability"),
    }


def _malformed_scene_policy() -> dict[str, Any]:
    return {
        "malformed": True,
        "scene_type": "unknown",
        "persistence_block": True,
        "persistence_block_reasons": ["malformed_relayscn_artifact"],
        "confidence": None,
        "stability": None,
    }


def _source_summary(messages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    user_messages = [message for message in messages if message.get("role") == "user"]
    assistant_messages = [
        message for message in messages if message.get("role") == "assistant"
    ]
    latest_user = user_messages[-1] if user_messages else None
    latest_user_chars = (
        _content_length(latest_user.get("content")) if latest_user else 0
    )
    return {
        "schema_version": "relaymem.primary_source_summary.v0",
        "content_included": False,
        "message_count": len(messages),
        "user_message_count": len(user_messages),
        "assistant_message_count": len(assistant_messages),
        "latest_user_message_present": latest_user is not None,
        "latest_user_message_chars": latest_user_chars,
    }


def _candidate(
    *,
    candidate_id: str,
    parsed_scn: Mapping[str, Any],
    source_summary: Mapping[str, Any],
    salience_band: str,
    stability_band: str,
    source_event_kind: str,
) -> dict[str, Any]:
    memory_kind = _memory_kind(str(parsed_scn.get("scene_type", "unknown")))
    promotion_policy = _promotion_policy(
        str(parsed_scn.get("scene_type", "unknown"))
    )
    return {
        "candidate_id": candidate_id,
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "source_event_kind": _safe_enum(source_event_kind, "turn"),
        "scene_type": str(parsed_scn.get("scene_type", "unknown")),
        "promotion_policy": promotion_policy,
        "safety_scope": _safety_scope(promotion_policy),
        "salience_band": salience_band,
        "stability_band": stability_band,
        "source_summary": dict(source_summary),
        "content_included": False,
        "raw_text_included": False,
        "raw_affect_estimates_included": False,
        "writes_memory": False,
        "mutates_soul": False,
        "applied": False,
    }


def _blocked_reasons(
    *,
    enabled: bool,
    parsed_scn: Mapping[str, Any],
    source_summary: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    scene_type = str(parsed_scn.get("scene_type", "unknown"))
    if not enabled:
        reasons.append("primary_formation_disabled")
    if parsed_scn.get("malformed") is True or scene_type == "unknown":
        reasons.append("scene_policy_blocks_memory")
    if parsed_scn.get("persistence_block") is True:
        persistence_reasons = _string_list(
            parsed_scn.get("persistence_block_reasons")
        )
        reasons.extend(persistence_reasons or ["relayscn_persistence_block"])
    if scene_type in _SCENE_BLOCK_REASONS:
        reasons.append(_SCENE_BLOCK_REASONS[scene_type])
    if source_summary.get("latest_user_message_present") is not True:
        reasons.append("latest_user_message_missing")
    return _dedupe(reasons)


def _projection(
    *,
    candidates: Sequence[Mapping[str, Any]],
    blocked_reasons: Sequence[str],
    parsed_scn: Mapping[str, Any],
    source_summary: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": _PROJECTION_SCHEMA_VERSION,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "raw_affect_estimates_included": False,
        "writes_memory": False,
        "mutates_soul": False,
        "candidate_count": len(candidates),
        "scene_type": str(parsed_scn.get("scene_type", "unknown")),
        "source_counts": {
            "message_count": _non_negative_int(
                source_summary.get("message_count")
            ),
            "user_message_count": _non_negative_int(
                source_summary.get("user_message_count")
            ),
            "assistant_message_count": _non_negative_int(
                source_summary.get("assistant_message_count")
            ),
        },
        "promotion_policy_counts": _count_by_key(
            candidates, "promotion_policy"
        ),
        "memory_kind_counts": _count_by_key(candidates, "memory_kind"),
        "blocked_reasons": [str(reason) for reason in blocked_reasons],
        "candidates": [
            {
                "candidate_id": str(candidate.get("candidate_id", "")),
                "memory_layer": "primary",
                "memory_kind": str(candidate.get("memory_kind", "unknown")),
                "promotion_policy": str(
                    candidate.get("promotion_policy", "unknown")
                ),
                "safety_scope": str(candidate.get("safety_scope", "unknown")),
                "salience_band": str(candidate.get("salience_band", "unknown")),
                "stability_band": str(
                    candidate.get("stability_band", "unknown")
                ),
            }
            for candidate in candidates
        ],
    }


def _memory_kind(scene_type: str) -> str:
    if scene_type in {"design_talk", "implementation_work", "review_work"}:
        return "recent_project_event"
    if scene_type in {"casual_chat", "vtuber_roleplay"}:
        return "relationship_moment"
    if scene_type == "system_ops":
        return "session_episode"
    return "experience_event"


def _promotion_policy(scene_type: str) -> str:
    if scene_type in {
        "formal_document",
        "medical_or_safety",
        "recovery",
        "unknown",
    }:
        return "never_auto_promote"
    if scene_type == "system_ops":
        return "review_required"
    return "free_to_update"


def _safety_scope(promotion_policy: str) -> str:
    if promotion_policy == "free_to_update":
        return "ordinary_memory"
    if promotion_policy == "review_required":
        return "held_for_review"
    if promotion_policy == "explicit_approval_required":
        return "approval_required"
    return "blocked"


def _salience_band(relayemo_artifact: Mapping[str, Any] | None) -> str:
    if not isinstance(relayemo_artifact, Mapping):
        return "unknown"
    assistant_state = relayemo_artifact.get("assistant_emotion_state")
    affect_estimate = relayemo_artifact.get("user_affect_estimate")
    intensity = _finite_float(
        assistant_state.get("intensity")
        if isinstance(assistant_state, Mapping)
        else None
    )
    confidence = _finite_float(
        affect_estimate.get("confidence")
        if isinstance(affect_estimate, Mapping)
        else None
    )
    score = max(intensity or 0.0, confidence or 0.0)
    if score >= 0.75:
        return "high"
    if score >= 0.4:
        return "medium"
    if score > 0:
        return "low"
    return "unknown"


def _stability_band(parsed_scn: Mapping[str, Any]) -> str:
    stability = _finite_float(parsed_scn.get("stability"))
    confidence = _finite_float(parsed_scn.get("confidence"))
    numeric_values = [
        item for item in (stability, confidence) if item is not None
    ]
    if not numeric_values:
        return "unknown"
    score = min(numeric_values)
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def _content_length(content: Any) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(
            len(item.get("text", ""))
            for item in content
            if isinstance(item, Mapping) and isinstance(item.get("text"), str)
        )
    return 0


def _count_by_key(
    candidates: Sequence[Mapping[str, Any]], key: str
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        value = str(candidate.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _string_list(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _dedupe(reasons: Sequence[str]) -> list[str]:
    output: list[str] = []
    for reason in reasons:
        text = str(reason)
        if text and text not in output:
            output.append(text)
    return output


def _finite_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        number = float(value)
        if not isfinite(number):
            return None
        return max(0.0, min(1.0, number))
    return None


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _safe_enum(value: object, default: str) -> str:
    if isinstance(value, str) and value:
        return value
    return default
