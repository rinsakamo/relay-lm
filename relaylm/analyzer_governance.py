"""Analyzer Candidate Governance contract helpers.

This module is intentionally dependency-light and schema-first.  Analyzer
outputs are candidates until a separate trusted authority gate validates that
they may affect runtime policy.  Public diagnostics from this module are
content-free and use English-only schema keys, enum values, and reason IDs.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "relaylm.analyzer_candidate_governance.v0"

ANALYZER_KINDS = frozenset({
    "affect_candidate",
    "query_detail_candidate",
    "reference_intent_candidate",
    "retrieval_query_candidate",
    "scene_policy_candidate",
})

SOURCE_CLASSES = frozenset({
    "confirmed_user_action",
    "fallback_regex",
    "heuristic",
    "llm_candidate",
    "locale_marker",
    "trusted_explicit",
    "trusted_route",
    "trusted_tool_signal",
    "unknown",
})

TRUSTED_SOURCE_CLASSES = frozenset({
    "confirmed_user_action",
    "trusted_explicit",
    "trusted_route",
    "trusted_tool_signal",
})

NON_AUTHORITATIVE_SOURCE_CLASSES = frozenset({
    "fallback_regex",
    "heuristic",
    "llm_candidate",
    "locale_marker",
    "unknown",
})

POLICY_AUTHORITIES = frozenset({
    "bounded",
    "broad",
    "mutation",
    "none",
    "open",
    "restrictive",
    "rewrite",
    "scene_policy",
    "update",
})

# ACG-1 has no target-specific permissive policy compiler.  Only a trusted,
# authoritative bounded candidate may open runtime policy through this generic
# helper.  "restrictive" may still be applied by callers as fail-closed safety
# behavior, but it does not open permissive runtime policy.
RUNTIME_OPEN_AUTHORITIES = frozenset({"bounded"})

CONFIDENCE_BUCKETS = frozenset({"low", "medium", "high"})
STABILITY_BUCKETS = frozenset({"low", "medium", "high"})

KNOWN_REASON_IDS = frozenset({
    "candidate_not_applied",
    "fail_closed_candidate_source",
    "heuristic_restrictive_only",
    "invalid_analyzer_kind",
    "invalid_content_free_flag",
    "invalid_source_class",
    "invalid_source_language",
    "llm_candidate_restrictive_only",
    "malformed_candidate_applied",
    "malformed_confidence",
    "malformed_is_estimate",
    "malformed_reason_id",
    "malformed_restrictive_only",
    "malformed_source_authoritative",
    "malformed_stability",
    "non_authoritative_source",
    "policy_authority_not_permitted",
    "raw_diagnostic_field_dropped",
    "unsupported_field_dropped",
    "unknown_enum_value",
    "unknown_policy_authority",
    "unknown_reason",
})

_ALLOWED_ARTIFACT_KEYS = frozenset({
    "analyzer_kind",
    "candidate_applied",
    "confidence",
    "content_free",
    "enum_values",
    "is_estimate",
    "policy_authority",
    "reason_ids",
    "restrictive_only",
    "schema_version",
    "source",
    "source_authoritative",
    "source_language",
    "stability",
    "validation_errors",
})

_RAW_TEXT_LIKE_KEYS = frozenset({
    "assistant_text",
    "external_signal_body",
    "filesystem_path",
    "memory_text",
    "queue_payload",
    "rationale",
    "raw_assistant_text",
    "raw_text",
    "raw_user_text",
    "relationship_markdown",
    "scene_markdown",
    "signals",
    "source_markdown",
    "user_text",
})

_PUBLIC_KEYS = frozenset({
    "analyzer_kind",
    "candidate_applied",
    "confidence_bucket",
    "content_free",
    "policy_authority",
    "reason_ids",
    "restrictive_only",
    "schema_version",
    "source_authoritative",
    "source_class",
    "stability_bucket",
    "validation_error_ids",
})

_ENGLISH_SCHEMA_KEYS = _ALLOWED_ARTIFACT_KEYS | _PUBLIC_KEYS | frozenset({
    "is_valid",
    "source_class",
    "validation_error_ids",
})


@dataclass(frozen=True)
class AnalyzerCandidateValidation:
    """Content-free validation summary for an analyzer candidate artifact."""

    artifact: dict[str, Any]
    is_valid: bool
    validation_error_ids: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        """Return the content-free public projection for the normalized artifact."""

        projection = content_free_projection(self.artifact)
        projection["is_valid"] = self.is_valid
        return projection


def build_analyzer_candidate_artifact(
    *,
    analyzer_kind: str,
    source: str,
    source_language: str = "und",
    is_estimate: bool = True,
    source_authoritative: bool = False,
    candidate_applied: bool = False,
    policy_authority: str = "none",
    restrictive_only: bool | None = None,
    confidence: float | int | str | None = 0.0,
    stability: float | int | str | None = 0.0,
    content_free: bool = False,
    validation_errors: Iterable[Any] | None = None,
    reason_ids: Iterable[Any] | None = None,
    enum_values: Iterable[Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build and normalize an analyzer candidate artifact.

    Unknown keyword arguments are not copied into the artifact.  Text-like
    diagnostic fields are represented only as stable validation errors so that
    callers can pass raw analyzer payloads without causing public leakage.
    """

    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "analyzer_kind": analyzer_kind,
        "source": source,
        "source_language": source_language,
        "is_estimate": is_estimate,
        "source_authoritative": source_authoritative,
        "candidate_applied": candidate_applied,
        "policy_authority": policy_authority,
        "restrictive_only": restrictive_only,
        "confidence": confidence,
        "stability": stability,
        "content_free": content_free,
        "validation_errors": _input_sequence(validation_errors),
        "reason_ids": _input_sequence(reason_ids),
        "enum_values": _input_sequence(enum_values),
    }

    dropped_errors: list[str] = []
    for key in extra:
        if key in _RAW_TEXT_LIKE_KEYS:
            dropped_errors.append("raw_diagnostic_field_dropped")
        else:
            dropped_errors.append("unsupported_field_dropped")
    artifact["validation_errors"].extend(dropped_errors)

    return normalize_analyzer_candidate_artifact(artifact)


def validate_analyzer_candidate_artifact(
    artifact: Mapping[str, Any] | None,
) -> AnalyzerCandidateValidation:
    """Validate an artifact and return a fail-closed normalized summary."""

    normalized = normalize_analyzer_candidate_artifact(artifact)
    validation_error_ids = tuple(normalized["validation_errors"])
    return AnalyzerCandidateValidation(
        artifact=normalized,
        is_valid=not validation_error_ids,
        validation_error_ids=validation_error_ids,
    )


def normalize_analyzer_candidate_artifact(
    artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a normalized, fail-closed analyzer candidate artifact."""

    raw: Mapping[str, Any] = artifact or {}
    validation_errors: list[str] = []
    reason_ids: list[str] = []

    for key in raw:
        if key not in _ALLOWED_ARTIFACT_KEYS:
            if key in _RAW_TEXT_LIKE_KEYS:
                validation_errors.append("raw_diagnostic_field_dropped")
            else:
                validation_errors.append("unsupported_field_dropped")

    if raw.get("schema_version") != SCHEMA_VERSION:
        validation_errors.append("unknown_enum_value")

    analyzer_kind = _as_token(raw.get("analyzer_kind"))
    if analyzer_kind not in ANALYZER_KINDS:
        analyzer_kind = "unknown"
        validation_errors.append("invalid_analyzer_kind")

    source_class = _as_token(raw.get("source"))
    if source_class not in SOURCE_CLASSES:
        source_class = "unknown"
        validation_errors.append("invalid_source_class")

    source_language = _normalize_language(raw.get("source_language"), validation_errors)
    is_estimate = _normalize_bool(raw.get("is_estimate"), True, "malformed_is_estimate", validation_errors)
    source_authoritative = _normalize_bool(
        raw.get("source_authoritative"),
        False,
        "malformed_source_authoritative",
        validation_errors,
    )
    candidate_applied = _normalize_bool(
        raw.get("candidate_applied"),
        False,
        "malformed_candidate_applied",
        validation_errors,
    )

    policy_authority = _as_token(raw.get("policy_authority"))
    if policy_authority not in POLICY_AUTHORITIES:
        policy_authority = "none"
        validation_errors.append("unknown_policy_authority")

    confidence = _bounded_float(raw.get("confidence"), "malformed_confidence", validation_errors)
    stability = _bounded_float(raw.get("stability"), "malformed_stability", validation_errors)

    restrictive_only = _normalize_optional_bool(
        raw.get("restrictive_only"),
        "malformed_restrictive_only",
        validation_errors,
    )
    content_free = _normalize_bool(
        raw.get("content_free"),
        False,
        "invalid_content_free_flag",
        validation_errors,
    )

    reason_ids.extend(_sanitize_reason_ids(raw.get("reason_ids"), validation_errors))
    validation_errors.extend(_sanitize_reason_ids(raw.get("validation_errors"), validation_errors))
    enum_values = _sanitize_enum_values(raw.get("enum_values"), validation_errors)

    if source_class in NON_AUTHORITATIVE_SOURCE_CLASSES:
        if source_authoritative:
            validation_errors.append("non_authoritative_source")
        source_authoritative = False
        candidate_applied = False if source_class == "unknown" else candidate_applied
        if policy_authority not in {"none", "restrictive"}:
            validation_errors.append("policy_authority_not_permitted")
        policy_authority = "none" if policy_authority != "restrictive" else "restrictive"
        restrictive_only = True
        if source_class == "heuristic":
            reason_ids.append("heuristic_restrictive_only")
        elif source_class == "llm_candidate":
            reason_ids.append("llm_candidate_restrictive_only")
        else:
            reason_ids.append("fail_closed_candidate_source")
    else:
        if restrictive_only is None:
            restrictive_only = policy_authority not in RUNTIME_OPEN_AUTHORITIES
        if not source_authoritative and policy_authority in RUNTIME_OPEN_AUTHORITIES:
            validation_errors.append("policy_authority_not_permitted")
            policy_authority = "none"
            restrictive_only = True
        if source_authoritative and not candidate_applied:
            reason_ids.append("candidate_not_applied")

    if analyzer_kind == "unknown" or source_class == "unknown":
        source_authoritative = False
        policy_authority = "none"
        restrictive_only = True
        candidate_applied = False

    validation_errors = _dedupe_tokens(validation_errors)
    reason_ids = _dedupe_tokens(reason_ids)
    enum_values = _dedupe_enum_tokens(enum_values)

    return {
        "schema_version": SCHEMA_VERSION,
        "analyzer_kind": analyzer_kind,
        "source": source_class,
        "source_language": source_language,
        "is_estimate": is_estimate,
        "source_authoritative": source_authoritative,
        "candidate_applied": candidate_applied,
        "policy_authority": policy_authority,
        "restrictive_only": bool(restrictive_only),
        "confidence": confidence,
        "stability": stability,
        "content_free": content_free,
        "validation_errors": validation_errors,
        "reason_ids": reason_ids,
        "enum_values": enum_values,
    }


def is_policy_authoritative(artifact: Mapping[str, Any] | None) -> bool:
    """Return whether the artifact carries trusted, validated policy authority."""

    normalized = normalize_analyzer_candidate_artifact(artifact)
    if normalized["validation_errors"]:
        return False
    return (
        normalized["source"] in TRUSTED_SOURCE_CLASSES
        and normalized["source_authoritative"] is True
        and normalized["policy_authority"] != "none"
    )


def can_open_runtime_policy(artifact: Mapping[str, Any] | None) -> bool:
    """Return whether this artifact may open bounded runtime policy.

    ACG-1 only recognizes trusted authoritative bounded policy as an opener.
    Candidate, heuristic, locale, fallback, unknown, malformed, and merely
    restrictive artifacts return ``False``.
    """

    normalized = normalize_analyzer_candidate_artifact(artifact)
    return (
        is_policy_authoritative(normalized)
        and normalized["candidate_applied"] is True
        and normalized["policy_authority"] in RUNTIME_OPEN_AUTHORITIES
        and normalized["restrictive_only"] is False
    )


def content_free_projection(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a bounded public projection without raw text or free-form rationale."""

    normalized = normalize_analyzer_candidate_artifact(artifact)
    return {
        "schema_version": SCHEMA_VERSION,
        "analyzer_kind": normalized["analyzer_kind"],
        "source_class": normalized["source"],
        "source_authoritative": normalized["source_authoritative"],
        "policy_authority": normalized["policy_authority"],
        "restrictive_only": normalized["restrictive_only"],
        "candidate_applied": normalized["candidate_applied"],
        "confidence_bucket": _bucket(normalized["confidence"]),
        "stability_bucket": _bucket(normalized["stability"]),
        "reason_ids": tuple(normalized["reason_ids"]),
        "validation_error_ids": tuple(normalized["validation_errors"]),
        "content_free": True,
    }


def analyzer_governance_enum_values() -> dict[str, tuple[str, ...]]:
    """Expose fixed English enum registries for smoke tests and docs checks."""

    return {
        "analyzer_kind": tuple(sorted(ANALYZER_KINDS | {"unknown"})),
        "source_class": tuple(sorted(SOURCE_CLASSES)),
        "policy_authority": tuple(sorted(POLICY_AUTHORITIES)),
        "confidence_bucket": tuple(sorted(CONFIDENCE_BUCKETS)),
        "stability_bucket": tuple(sorted(STABILITY_BUCKETS)),
        "reason_id": tuple(sorted(KNOWN_REASON_IDS)),
        "schema_key": tuple(sorted(_ENGLISH_SCHEMA_KEYS)),
    }


def _input_sequence(value: Iterable[Any] | None) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def _as_token(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    token = value.strip().lower()
    if not token:
        return "unknown"
    return token


def _normalize_language(value: Any, errors: list[str]) -> str:
    if not isinstance(value, str):
        errors.append("invalid_source_language")
        return "und"
    token = value.strip().lower()
    if not token or len(token) > 16:
        errors.append("invalid_source_language")
        return "und"
    if not all(ch.isascii() and (ch.isalnum() or ch in {"-", "_"}) for ch in token):
        errors.append("invalid_source_language")
        return "und"
    return token


def _normalize_bool(value: Any, default: bool, reason_id: str, errors: list[str]) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    errors.append(reason_id)
    return default


def _normalize_optional_bool(value: Any, reason_id: str, errors: list[str]) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    errors.append(reason_id)
    return None


def _bounded_float(value: Any, reason_id: str, errors: list[str]) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(reason_id)
        return 0.0
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        errors.append(reason_id)
        return 0.0
    return number


def _sanitize_reason_ids(value: Any, errors: list[str]) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values: Iterable[Any] = (value,)
    elif isinstance(value, Iterable):
        values = value
    else:
        errors.append("malformed_reason_id")
        return ["unknown_reason"]

    sanitized: list[str] = []
    for item in values:
        token = _as_token(item)
        if token in KNOWN_REASON_IDS:
            sanitized.append(token)
        else:
            errors.append("malformed_reason_id")
            sanitized.append("unknown_reason")
    return sanitized


def _sanitize_enum_values(value: Any, errors: list[str]) -> list[str]:
    known_values = (
        ANALYZER_KINDS
        | SOURCE_CLASSES
        | POLICY_AUTHORITIES
        | CONFIDENCE_BUCKETS
        | STABILITY_BUCKETS
        | KNOWN_REASON_IDS
        | {SCHEMA_VERSION, "unknown"}
    )
    if value is None:
        return []
    if isinstance(value, str):
        values: Iterable[Any] = (value,)
    elif isinstance(value, Iterable):
        values = value
    else:
        errors.append("unknown_enum_value")
        return ["unknown_enum_value"]

    sanitized: list[str] = []
    for item in values:
        if not isinstance(item, str):
            errors.append("unknown_enum_value")
            sanitized.append("unknown_enum_value")
            continue
        token = item.strip().lower()
        if token in known_values:
            sanitized.append(token)
        else:
            errors.append("unknown_enum_value")
            sanitized.append("unknown_enum_value")
    return sanitized


def _dedupe_tokens(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        token = _as_token(value)
        if token not in KNOWN_REASON_IDS:
            token = "unknown_reason"
        if token not in seen:
            seen.add(token)
            result.append(token)
    return result


def _dedupe_enum_tokens(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        token = _as_token(value)
        if token not in seen:
            seen.add(token)
            result.append(token)
    return result


def _bucket(value: float) -> str:
    if value >= 0.75:
        return "high"
    if value >= 0.4:
        return "medium"
    return "low"
