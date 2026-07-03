"""RelaySCN structured scene classifier candidate boundary."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.analyzer_governance import (
    NON_AUTHORITATIVE_SOURCE_CLASSES,
    TRUSTED_SOURCE_CLASSES,
    build_analyzer_candidate_artifact,
    can_open_runtime_policy,
)
from relaylm.scene_wiki_matcher import match_scene_wiki_definition, scene_wiki_match_public_projection

SCHEMA_VERSION = "relaylm.scene_classifier_candidate.v0"

SCENE_TYPES = frozenset({
    "unknown",
    "casual_chat",
    "implementation_work",
    "review_work",
    "design_talk",
    "formal_document",
    "medical_or_safety",
    "system_ops",
    "recovery",
    "vtuber_roleplay",
    "memory_management",
    "character_workspace",
})
RESTRICTIVE_SCENE_TYPES = frozenset({"medical_or_safety", "formal_document", "recovery"})
MATCH_STRENGTHS = frozenset({"none", "weak", "medium", "strong"})
_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_PUBLIC_REASON_IDS = frozenset({
    "classifier_candidate_non_authoritative",
    "classifier_candidate_restrictive_only",
    "classifier_policy_open_rejected",
    "heuristic_scene_candidate",
    "scene_wiki_candidate_match",
    "trusted_scene_candidate",
    "unrecognized_scene_type",
    "unknown_scene_fail_closed",
})


def build_scene_classifier_candidate(
    *,
    candidate: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    scene_wiki_definitions: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    raw_candidate = candidate if isinstance(candidate, Mapping) else None
    reason_ids: list[str] = []
    validation_errors: list[str] = []

    if raw_candidate is None:
        scene_type, confidence, stability = _estimate_scene_from_messages(payload or {})
        source = "heuristic"
        source_language = "und"
        lookup_scene_id = "unknown"
        lookup_scene_family = _family_for_scene_type(scene_type)
        is_estimate = True
        requested_source_authoritative = False
        requested_candidate_applied = scene_type in RESTRICTIVE_SCENE_TYPES
        requested_policy_authority = "restrictive" if scene_type in RESTRICTIVE_SCENE_TYPES else "none"
        reason_ids.append("heuristic_scene_candidate")
    else:
        scene_type = _safe_scene_type(
            raw_candidate.get("candidate_scene_type") or raw_candidate.get("scene_type"),
            validation_errors,
            reason_ids,
        )
        confidence = _coerce_probability(raw_candidate.get("confidence"), default=0.0)
        stability = _coerce_probability(raw_candidate.get("stability"), default=0.0)
        source = _safe_source(raw_candidate.get("source"))
        source_language = _safe_language(raw_candidate.get("source_language"))
        lookup_scene_id = _safe_token(raw_candidate.get("candidate_scene_id") or raw_candidate.get("scene_id"))
        lookup_scene_family = _safe_token(raw_candidate.get("candidate_scene_family") or raw_candidate.get("scene_family"))
        if lookup_scene_family == "unknown":
            lookup_scene_family = _family_for_scene_type(scene_type)
        is_estimate = _safe_bool(raw_candidate.get("is_estimate"), default=source not in TRUSTED_SOURCE_CLASSES)
        requested_source_authoritative = raw_candidate.get("source_authoritative") is True
        requested_candidate_applied = raw_candidate.get("candidate_applied") is True
        requested_policy_authority = _safe_policy_authority(raw_candidate.get("policy_authority"))

    source_authoritative = source in TRUSTED_SOURCE_CLASSES and requested_source_authoritative
    match = match_scene_wiki_definition(
        candidate_scene_type=scene_type,
        candidate_scene_id=lookup_scene_id,
        candidate_scene_family=lookup_scene_family,
        scene_definitions=scene_wiki_definitions,
    )
    match_strength = _safe_match_strength(match.get("match_strength"))
    matched_scene_wiki_id = _safe_token(match.get("matched_scene_wiki_id"))
    matched_scene_type = _safe_scene_type(match.get("matched_scene_type"), [], [])
    matched_scene_family = _safe_token(match.get("matched_scene_family"))

    if match_strength in {"medium", "strong"}:
        confidence = max(confidence, 0.82 if match_strength == "strong" else 0.72)
        stability = max(stability, 0.78 if match_strength == "strong" else 0.70)
        reason_ids.append("scene_wiki_candidate_match")
        if scene_type == "unknown" and matched_scene_type != "unknown":
            scene_type = matched_scene_type

    candidate_scene_family = (
        matched_scene_family if match_strength in {"medium", "strong"} and matched_scene_family != "unknown" else _family_for_scene_type(scene_type)
    )
    exposed_scene_id = matched_scene_wiki_id if match_strength in {"medium", "strong"} and matched_scene_wiki_id != "unknown" else None

    reason_ids.append("trusted_scene_candidate" if source_authoritative else "classifier_candidate_non_authoritative")

    if source in NON_AUTHORITATIVE_SOURCE_CLASSES:
        policy_authority = "restrictive" if scene_type in RESTRICTIVE_SCENE_TYPES else requested_policy_authority
        if policy_authority not in {"none", "restrictive"}:
            validation_errors.append("policy_authority_not_permitted")
            reason_ids.append("classifier_policy_open_rejected")
        candidate_applied = requested_candidate_applied or scene_type in RESTRICTIVE_SCENE_TYPES
        restrictive_only = True
        reason_ids.append("classifier_candidate_restrictive_only")
    else:
        policy_authority = requested_policy_authority
        candidate_applied = requested_candidate_applied and scene_type != "unknown"
        restrictive_only = not (source_authoritative and candidate_applied and policy_authority == "bounded")
        if not source_authoritative and policy_authority == "bounded":
            validation_errors.append("policy_authority_not_permitted")
            reason_ids.append("classifier_policy_open_rejected")
            policy_authority = "none"
            restrictive_only = True

    if scene_type == "unknown":
        policy_authority = "none" if policy_authority != "restrictive" else "restrictive"
        candidate_applied = False
        restrictive_only = True
        reason_ids.append("unknown_scene_fail_closed")

    governance = build_analyzer_candidate_artifact(
        analyzer_kind="scene_policy_candidate",
        source=source,
        source_language=source_language,
        is_estimate=is_estimate,
        source_authoritative=source_authoritative,
        candidate_applied=candidate_applied,
        policy_authority=policy_authority,
        restrictive_only=restrictive_only,
        confidence=confidence,
        stability=stability,
        content_free=True,
        validation_errors=validation_errors,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "analyzer_kind": "scene_policy_candidate",
        "source": governance["source"],
        "source_language": governance["source_language"],
        "candidate_scene_type": scene_type,
        "candidate_scene_id": exposed_scene_id,
        "candidate_scene_family": candidate_scene_family,
        "matched_scene_wiki_id": exposed_scene_id,
        "match_strength": match_strength,
        "confidence": governance["confidence"],
        "stability": governance["stability"],
        "is_estimate": governance["is_estimate"],
        "source_authoritative": governance["source_authoritative"],
        "candidate_applied": governance["candidate_applied"],
        "policy_authority": governance["policy_authority"],
        "restrictive_only": governance["restrictive_only"],
        "can_open_runtime_policy": can_open_runtime_policy(governance),
        "content_free": True,
        "reason_ids": tuple(_safe_reason_ids([*reason_ids, *governance["reason_ids"]])),
        "validation_errors": tuple(_safe_validation_errors([*validation_errors, *governance["validation_errors"]])),
        "scene_wiki_match": _scene_wiki_match_public_projection_redacted(match, scene_type, candidate_scene_family),
        "governance": governance,
    }


def scene_classifier_public_projection(candidate: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = candidate if isinstance(candidate, Mapping) else {}
    match_id = _safe_token(raw.get("matched_scene_wiki_id"))
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_present": bool(raw),
        "candidate_scene_type": _safe_scene_type(raw.get("candidate_scene_type"), [], []),
        "candidate_scene_family": _safe_token(raw.get("candidate_scene_family")),
        "matched_scene_wiki_id": None if match_id == "unknown" else match_id,
        "match_strength": _safe_match_strength(raw.get("match_strength")),
        "confidence_bucket": _bucket(_coerce_probability(raw.get("confidence"), default=0.0)),
        "stability_bucket": _bucket(_coerce_probability(raw.get("stability"), default=0.0)),
        "source_class": _safe_source(raw.get("source")),
        "source_authoritative": raw.get("source_authoritative") is True,
        "policy_authority": _safe_policy_authority(raw.get("policy_authority")),
        "restrictive_only": raw.get("restrictive_only") is not False,
        "candidate_applied": raw.get("candidate_applied") is True,
        "can_open_runtime_policy": raw.get("can_open_runtime_policy") is True,
        "reason_ids": tuple(_safe_reason_ids(raw.get("reason_ids"))),
        "validation_error_ids": tuple(_safe_validation_errors(raw.get("validation_errors"))),
        "content_free": True,
    }


def _scene_wiki_match_public_projection_redacted(match: Mapping[str, Any], scene_type: str, scene_family: str) -> dict[str, Any]:
    public = scene_wiki_match_public_projection(match)
    public["candidate_scene_type"] = scene_type
    public["candidate_scene_family"] = scene_family
    return public


def _estimate_scene_from_messages(payload: Mapping[str, Any]) -> tuple[str, float, float]:
    text = _latest_user_text(payload).lower()
    if not text:
        return "unknown", 0.35, 0.35
    if any(x in text for x in ("medical", "doctor", "病院", "薬", "医療", "危険", "安全", "safety", "legal")):
        return "medical_or_safety", 0.82, 0.78
    if any(x in text for x in ("formal", "report", "契約", "公的", "公式", "論文", "文書", "document")):
        return "formal_document", 0.80, 0.76
    if any(x in text for x in ("review", "pr ", "pr#", "diff", "レビュー", "検証")) or _contains_ascii_word(text, "pr"):
        return "review_work", 0.78, 0.72
    if any(x in text for x in ("implement", "code", "コード", "repo", "bug", "error", "fix ", "fix this", "ファイル", "実装", "修正", "バグ", "直して", "commit")) or _contains_ascii_word(text, "file"):
        return "implementation_work", 0.78, 0.72
    if any(x in text for x in ("git ", "github", "remote", "push", "branch", "環境", "設定")):
        return "system_ops", 0.76, 0.70
    if any(x in text for x in ("design", "architecture", "設計", "仕様", "policy", "mvp")):
        return "design_talk", 0.74, 0.70
    if any(x in text for x in ("vtuber", "live2d", "tts", "roleplay", "ロールプレイ", "配信")):
        return "vtuber_roleplay", 0.74, 0.70
    if any(x in text for x in ("confused", "lost", "戻る", "わから", "混乱", "文脈", "context repair")):
        return "recovery", 0.82, 0.78
    return "casual_chat", 0.62, 0.60


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
            return "\n".join(item["text"] for item in content if isinstance(item, Mapping) and isinstance(item.get("text"), str))
    return ""


def _contains_ascii_word(text: str, word: str) -> bool:
    return re.search(rf"(?<![a-z0-9_]){re.escape(word)}(?![a-z0-9_])", text) is not None


def _safe_scene_type(value: Any, validation_errors: list[str], reason_ids: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        validation_errors.append("unrecognized_scene_type")
        reason_ids.append("unrecognized_scene_type")
        return "unknown"
    token = value.strip().lower()
    if token == "unknown":
        return "unknown"
    if not _TOKEN_RE.fullmatch(token):
        validation_errors.append("unrecognized_scene_type")
        reason_ids.append("unrecognized_scene_type")
        return "unknown"
    if token in SCENE_TYPES:
        return token
    validation_errors.append("unrecognized_scene_type")
    reason_ids.append("unrecognized_scene_type")
    return "unknown"


def _family_for_scene_type(scene_type: str) -> str:
    if scene_type in {"implementation_work", "review_work", "design_talk", "system_ops"}:
        return "implementation"
    if scene_type in {"memory_management", "character_workspace", "vtuber_roleplay"}:
        return "character_workspace"
    if scene_type in RESTRICTIVE_SCENE_TYPES:
        return "safety"
    if scene_type == "casual_chat":
        return "conversation"
    return "unknown"


def _safe_token(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    token = value.strip().lower()
    if not _TOKEN_RE.fullmatch(token):
        return "unknown"
    return token


def _safe_language(value: Any) -> str:
    token = _safe_token(value)
    return token if token != "unknown" and len(token) <= 16 else "und"


def _safe_source(value: Any) -> str:
    token = _safe_token(value)
    if token in TRUSTED_SOURCE_CLASSES or token in NON_AUTHORITATIVE_SOURCE_CLASSES:
        return token
    return "unknown"


def _safe_policy_authority(value: Any) -> str:
    token = _safe_token(value)
    if token in {"none", "restrictive", "bounded", "broad", "open", "update", "mutation", "rewrite", "scene_policy"}:
        return token
    return "none"


def _safe_match_strength(value: Any) -> str:
    token = _safe_token(value)
    return token if token in MATCH_STRENGTHS else "none"


def _safe_bool(value: Any, *, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _coerce_probability(value: Any, *, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float) and 0.0 <= float(value) <= 1.0:
        return float(value)
    return default


def _safe_reason_ids(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_values = (value,)
    elif isinstance(value, Sequence):
        raw_values = value
    else:
        raw_values = ()
    allowed = _PUBLIC_REASON_IDS | {"candidate_not_applied", "fail_closed_candidate_source", "heuristic_restrictive_only", "llm_candidate_restrictive_only", "non_authoritative_source", "unknown_reason"}
    result: list[str] = []
    for raw in raw_values:
        token = _safe_token(raw)
        if token in allowed and token not in result:
            result.append(token)
    return result


def _safe_validation_errors(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_values = (value,)
    elif isinstance(value, Sequence):
        raw_values = value
    else:
        raw_values = ()
    allowed = {"invalid_analyzer_kind", "invalid_content_free_flag", "invalid_source_class", "invalid_source_language", "malformed_candidate_applied", "malformed_confidence", "malformed_is_estimate", "malformed_reason_id", "malformed_restrictive_only", "malformed_source_authoritative", "malformed_stability", "non_authoritative_source", "policy_authority_not_permitted", "raw_diagnostic_field_dropped", "unrecognized_scene_type", "unknown_enum_value", "unknown_policy_authority", "unsupported_field_dropped"}
    result: list[str] = []
    for raw in raw_values:
        token = _safe_token(raw)
        if token in allowed and token not in result:
            result.append(token)
    return result


def _bucket(value: float) -> str:
    if value >= 0.75:
        return "high"
    if value >= 0.4:
        return "medium"
    return "low"
