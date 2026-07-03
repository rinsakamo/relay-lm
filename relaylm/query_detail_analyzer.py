"""RelayLM Query Detail Analyzer artifact.

This module keeps remembered-detail detection behind the ACG candidate
governance boundary.  It may inspect private request text, but its returned
artifact and public projection are content-free: fixed English enum values,
reason IDs, status fields, and counts only.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from relaylm.analyzer_governance import (
    build_analyzer_candidate_artifact,
    can_open_runtime_policy,
    content_free_projection,
    normalize_analyzer_candidate_artifact,
)

QUERY_DETAIL_ANALYZER_SCHEMA = "relaylm.query_detail_analyzer.v0"
QUERY_DETAIL_ANALYZER_KIND = "query_detail_candidate"

QUERY_DETAIL_TYPES = frozenset({
    "cause_or_reason",
    "date_or_time",
    "identity",
    "location",
    "person_or_name",
    "preference",
    "quantity",
    "relationship",
    "unknown",
})

_RAW_TEXT_LIKE_KEYS = frozenset({
    "assistant_text",
    "external_signal_body",
    "filesystem_path",
    "memory_text",
    "protected_source_body",
    "queue_payload",
    "rationale",
    "raw_assistant_text",
    "raw_text",
    "raw_user_text",
    "regex_match_body",
    "source_body",
    "user_text",
})

_DETAIL_QUERY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("date_or_time", re.compile(r"\b(when|date|day|month|year|time|first hear|first heard)\b|いつ|何年|何月|何日|初めて", re.I)),
    ("person_or_name", re.compile(r"\b(name|who is|who was|who are|who were)\b|名前|誰", re.I)),
    ("quantity", re.compile(r"\b(how many|how much|number|quantity)\b|何個|いくつ|何回", re.I)),
    ("relationship", re.compile(r"\b(relationship|related|friend|family|coworker)\b|関係|友人|家族|同僚", re.I)),
    ("cause_or_reason", re.compile(r"\b(why|because|cause|reason)\b|なぜ|理由|原因", re.I)),
    ("preference", re.compile(r"\b(favorite|favourite|prefer|preference|like|love|dislike|hobby|taste)\b|好き|好み|お気に入り|嫌い", re.I)),
    ("location", re.compile(r"\b(where|location|place|address|city|country)\b|どこ|場所|住所", re.I)),
    ("identity", re.compile(r"\b(who am i|what am i|identity|profile)\b|私は誰|自分.*何者|身元", re.I)),
)

_SELF_IDENTITY_QUERY_RE = re.compile(r"\b(who am i|what am i)\b|私は誰|自分.*何者", re.I)
_JA_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


@dataclass(frozen=True)
class QueryDetailAnalysis:
    """Content-free Query Detail Analyzer result."""

    schema_version: str
    analyzer_kind: str
    source: str
    source_language: str
    requested_detail_types: tuple[str, ...]
    unsupported_detail_risk: bool
    confidence: float
    is_estimate: bool
    source_authoritative: bool
    candidate_applied: bool
    policy_authority: str
    restrictive_only: bool
    content_free: bool
    reason_ids: tuple[str, ...]
    validation_errors: tuple[str, ...]
    governance_artifact: Mapping[str, object] = field(default_factory=dict, repr=False)

    def to_public_dict(self) -> dict[str, object]:
        governance = content_free_projection(self.governance_artifact)
        return {
            "schema_version": self.schema_version,
            "analyzer_kind": self.analyzer_kind,
            "source_class": governance["source_class"],
            "source_language": self.source_language,
            "requested_detail_types": self.requested_detail_types,
            "requested_detail_type_count": len(self.requested_detail_types),
            "unsupported_detail_risk": self.unsupported_detail_risk,
            "source_authoritative": governance["source_authoritative"],
            "policy_authority": governance["policy_authority"],
            "restrictive_only": governance["restrictive_only"],
            "candidate_applied": governance["candidate_applied"],
            "confidence_bucket": governance["confidence_bucket"],
            "stability_bucket": governance["stability_bucket"],
            "reason_ids": governance["reason_ids"],
            "validation_error_ids": tuple(dict.fromkeys((*governance["validation_error_ids"], *self.validation_errors))),
            "content_free": True,
            "raw_user_text_included": False,
            "raw_assistant_text_included": False,
            "raw_memory_text_included": False,
            "protected_source_body_included": False,
            "free_form_rationale_included": False,
            "regex_match_body_included": False,
            "queue_payload_included": False,
            "filesystem_path_included": False,
        }


def analyze_query_detail_candidate(
    *,
    query_text: object = "",
    candidate: object | None = None,
) -> QueryDetailAnalysis:
    """Return a content-free Query Detail Analyzer result.

    ``candidate`` is an optional structured analyzer candidate.  Missing
    candidates fall back to the bounded legacy regex candidate.  Malformed
    candidates fail closed by emitting the fixed ``unknown`` detail enum rather
    than storing or exposing any raw candidate string.
    """

    fallback_types = _legacy_regex_detail_types(query_text)
    fallback_language = _infer_language(query_text)
    if not isinstance(candidate, Mapping):
        if candidate is None:
            return _build_analysis(
                requested_detail_types=fallback_types,
                source="fallback_regex",
                source_language=fallback_language,
                confidence=0.66 if fallback_types else 0.0,
                stability=0.5 if fallback_types else 0.0,
                is_estimate=True,
                source_authoritative=False,
                candidate_applied=bool(fallback_types),
                policy_authority="restrictive" if fallback_types else "none",
                restrictive_only=True,
                reason_ids=("fail_closed_candidate_source",),
                validation_errors=(),
            )
        return _build_analysis(
            requested_detail_types=_union_detail_types(fallback_types, ("unknown",)),
            source="unknown",
            source_language=fallback_language,
            confidence=0.0,
            stability=0.0,
            is_estimate=True,
            source_authoritative=False,
            candidate_applied=False,
            policy_authority="none",
            restrictive_only=True,
            reason_ids=("fail_closed_candidate_source",),
            validation_errors=("unknown_enum_value",),
        )

    candidate_types, detail_errors = _candidate_detail_types(candidate.get("requested_detail_types"))
    if "requested_detail_types" not in candidate:
        detail_errors = _dedupe((*detail_errors, "unknown_enum_value"))
        candidate_types = _union_detail_types(candidate_types, ("unknown",))

    merged_types = _union_detail_types(fallback_types, candidate_types)
    if detail_errors and not merged_types:
        merged_types = ("unknown",)

    source = _token(candidate.get("source"), "unknown")
    source_language = _safe_language(candidate.get("source_language"), fallback_language)
    raw_extra = {
        str(key): value
        for key, value in candidate.items()
        if key not in {
            "schema_version",
            "analyzer_kind",
            "source",
            "source_language",
            "requested_detail_types",
            "unsupported_detail_risk",
            "confidence",
            "stability",
            "is_estimate",
            "source_authoritative",
            "candidate_applied",
            "policy_authority",
            "restrictive_only",
            "content_free",
            "reason_ids",
            "validation_errors",
        }
    }
    raw_key_errors = tuple(
        "raw_diagnostic_field_dropped" if key in _RAW_TEXT_LIKE_KEYS else "unsupported_field_dropped"
        for key in raw_extra
    )

    return _build_analysis(
        requested_detail_types=merged_types,
        source=source,
        source_language=source_language,
        confidence=candidate.get("confidence", 0.0),
        stability=candidate.get("stability", 0.0),
        is_estimate=candidate.get("is_estimate", True),
        source_authoritative=candidate.get("source_authoritative", False),
        candidate_applied=candidate.get("candidate_applied", bool(merged_types)),
        policy_authority=candidate.get("policy_authority", "restrictive" if merged_types else "none"),
        restrictive_only=candidate.get("restrictive_only", True),
        reason_ids=candidate.get("reason_ids", ()),
        validation_errors=_dedupe((*detail_errors, *raw_key_errors, *_input_tokens(candidate.get("validation_errors")))),
        extra=raw_extra,
    )


def query_detail_public_projection(analysis: QueryDetailAnalysis | Mapping[str, object] | None) -> dict[str, object]:
    if isinstance(analysis, QueryDetailAnalysis):
        return analysis.to_public_dict()
    normalized = analyze_query_detail_candidate(candidate=analysis)
    return normalized.to_public_dict()


def requested_detail_types_from_analysis(analysis: QueryDetailAnalysis | Mapping[str, object] | None) -> tuple[str, ...]:
    if isinstance(analysis, QueryDetailAnalysis):
        return analysis.requested_detail_types
    normalized = analyze_query_detail_candidate(candidate=analysis)
    return normalized.requested_detail_types


def _build_analysis(
    *,
    requested_detail_types: Iterable[str],
    source: object,
    source_language: object,
    confidence: object,
    stability: object,
    is_estimate: object,
    source_authoritative: object,
    candidate_applied: object,
    policy_authority: object,
    restrictive_only: object,
    reason_ids: object,
    validation_errors: Iterable[str],
    extra: Mapping[str, object] | None = None,
) -> QueryDetailAnalysis:
    detail_types = _normalize_detail_type_sequence(requested_detail_types)
    errors = tuple(dict.fromkeys(validation_errors))
    unsupported_detail_risk = bool(detail_types)
    governance = build_analyzer_candidate_artifact(
        analyzer_kind=QUERY_DETAIL_ANALYZER_KIND,
        source=_token(source, "unknown"),
        source_language=str(source_language) if isinstance(source_language, str) else "und",
        is_estimate=is_estimate if isinstance(is_estimate, bool) else True,
        source_authoritative=source_authoritative if isinstance(source_authoritative, bool) else False,
        candidate_applied=candidate_applied if isinstance(candidate_applied, bool) else bool(detail_types),
        policy_authority=str(policy_authority) if isinstance(policy_authority, str) else "none",
        restrictive_only=restrictive_only if isinstance(restrictive_only, bool) else True,
        confidence=confidence,
        stability=stability,
        content_free=True,
        validation_errors=errors,
        reason_ids=reason_ids,
        **dict(extra or {}),
    )
    governance = normalize_analyzer_candidate_artifact(governance)
    if can_open_runtime_policy(governance):
        governance = dict(governance)
        governance["validation_errors"] = _dedupe((*governance["validation_errors"], "policy_authority_not_permitted"))
        governance["policy_authority"] = "restrictive"
        governance["restrictive_only"] = True
        governance["source_authoritative"] = False

    if governance["validation_errors"] and not detail_types:
        detail_types = ("unknown",)
        unsupported_detail_risk = True

    return QueryDetailAnalysis(
        schema_version=QUERY_DETAIL_ANALYZER_SCHEMA,
        analyzer_kind=QUERY_DETAIL_ANALYZER_KIND,
        source=str(governance["source"]),
        source_language=str(governance["source_language"]),
        requested_detail_types=tuple(detail_types),
        unsupported_detail_risk=unsupported_detail_risk,
        confidence=float(governance["confidence"]),
        is_estimate=bool(governance["is_estimate"]),
        source_authoritative=bool(governance["source_authoritative"]),
        candidate_applied=bool(governance["candidate_applied"]),
        policy_authority=str(governance["policy_authority"]),
        restrictive_only=bool(governance["restrictive_only"]),
        content_free=True,
        reason_ids=tuple(governance["reason_ids"]),
        validation_errors=tuple(governance["validation_errors"]),
        governance_artifact=governance,
    )


def _legacy_regex_detail_types(query_text: object) -> tuple[str, ...]:
    if not isinstance(query_text, str) or not query_text:
        return ()
    detail_types = [
        detail_type
        for detail_type, pattern in _DETAIL_QUERY_PATTERNS
        if pattern.search(query_text)
    ]
    if _SELF_IDENTITY_QUERY_RE.search(query_text) and "identity" in detail_types:
        detail_types = [detail_type for detail_type in detail_types if detail_type != "person_or_name"]
    return tuple(dict.fromkeys(detail_types))


def _candidate_detail_types(value: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if value is None:
        return (), ()
    if isinstance(value, str):
        raw_values: Iterable[object] = (value,)
    elif isinstance(value, Iterable):
        raw_values = value
    else:
        return ("unknown",), ("unknown_enum_value",)

    detail_types: list[str] = []
    errors: list[str] = []
    for item in raw_values:
        token = _token(item, "unknown")
        if token in QUERY_DETAIL_TYPES:
            detail_types.append(token)
        else:
            detail_types.append("unknown")
            errors.append("unknown_enum_value")
    return _normalize_detail_type_sequence(detail_types), tuple(dict.fromkeys(errors))


def _normalize_detail_type_sequence(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        token = _token(value, "unknown")
        token = token if token in QUERY_DETAIL_TYPES else "unknown"
        if token not in result:
            result.append(token)
    return tuple(result)


def _union_detail_types(*groups: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for group in groups:
        for value in group:
            token = _token(value, "unknown")
            token = token if token in QUERY_DETAIL_TYPES else "unknown"
            if token not in result:
                result.append(token)
    return tuple(result)


def _infer_language(query_text: object) -> str:
    if not isinstance(query_text, str) or not query_text.strip():
        return "und"
    if _JA_RE.search(query_text):
        return "ja"
    if query_text.isascii():
        return "en"
    return "und"


def _safe_language(value: object, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    token = value.strip().lower()
    if len(token) > 16:
        return fallback
    if not all(ch.isascii() and (ch.isalnum() or ch in {"-", "_"}) for ch in token):
        return fallback
    return token


def _token(value: object, default: str) -> str:
    if not isinstance(value, str):
        return default
    token = value.strip().lower()
    return token or default


def _input_tokens(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    return ("unknown_enum_value",)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        token = _token(value, "unknown_enum_value")
        if token not in result:
            result.append(token)
    return tuple(result)


__all__ = [
    "QUERY_DETAIL_ANALYZER_KIND",
    "QUERY_DETAIL_ANALYZER_SCHEMA",
    "QUERY_DETAIL_TYPES",
    "QueryDetailAnalysis",
    "analyze_query_detail_candidate",
    "query_detail_public_projection",
    "requested_detail_types_from_analysis",
]
