"""Shared Reference/Intent Analyzer candidate helpers.

This module centralizes locale marker fallback behavior used by RelayREF and
RelayINT. It emits fixed English enum values and uses the ACG-1 governance
helpers for authority and public diagnostics. Raw input text is never copied
into public projections.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from relaylm.analyzer_governance import (
    build_analyzer_candidate_artifact,
    can_open_runtime_policy,
    content_free_projection,
    normalize_analyzer_candidate_artifact,
)

SCHEMA_VERSION = "relaylm.reference_intent_analyzer.v0"
ANALYZER_KIND = "reference_intent_candidate"

REFERENCE_KINDS = frozenset({
    "none",
    "unresolved_deictic",
    "prior_turn_reference",
    "prior_memory_reference",
    "ambiguous_choice",
    "context_repair_request",
    "unknown",
})
INTENT_KINDS = frozenset({
    "continuation",
    "clarification_request",
    "prior_memory_request",
    "correction_request",
    "review_request",
    "implementation_request",
    "unknown",
})

UNRESOLVED_REFERENCE_MARKERS = (
    "which one",
    "what was that",
    "what were we",
    "それ",
    "これ",
    "あれ",
    "さっき",
    "どっち",
    "どれ",
    "前の",
    "この件",
    "何の話",
    "わから",
)
AMBIGUOUS_CHOICE_MARKERS = ("which one", "どっち", "どれ")
CONTEXT_REPAIR_MARKERS = ("what was that", "what were we", "何の話", "わから")
PRIOR_MEMORY_REQUEST_MARKERS = (
    "前に話した",
    "覚えてる",
    "思い出して",
    "前回",
    "前のスレッド",
    "previous",
    "remember",
)
CONTINUATION_MARKERS = ("続き", "その方向", "それで", "continue")
CORRECTION_MARKERS = ("修正", "直して", "fix", "correct")
REVIEW_MARKERS = ("レビュー", "確認して", "review")
IMPLEMENTATION_MARKERS = ("実装", "進めて", "implement")

_RAW_TEXT_LIKE_KEYS = frozenset({
    "assistant_text",
    "external_signal_body",
    "memory_text",
    "queue_payload",
    "rationale",
    "raw_assistant_text",
    "raw_text",
    "raw_user_text",
    "signals",
    "source_markdown",
    "user_text",
})
_ALLOWED_KEYS = frozenset({
    "schema_version",
    "analyzer_kind",
    "source",
    "source_language",
    "reference_kind",
    "intent_kinds",
    "ambiguity_detected",
    "unresolved_reference_detected",
    "prior_memory_request_detected",
    "continuation_detected",
    "clarification_recommended",
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
    "reference_terms_detected_count",
    "runtime_policy_open_allowed",
    "governance",
    "governance_public",
})


def analyze_reference_intent(
    *,
    messages: Sequence[Mapping[str, Any]] | None = None,
    text: str | None = None,
    ctx_hints: Mapping[str, Any] | None = None,
    source: str = "locale_marker",
    source_language: str | None = None,
) -> dict[str, Any]:
    latest_text = text if isinstance(text, str) else _latest_user_text(messages or [])
    normalized_text = latest_text.lower()
    language = source_language or _detect_language(latest_text)

    prior_memory_count = _count_terms(normalized_text, PRIOR_MEMORY_REQUEST_MARKERS)
    continuation_count = _count_terms(normalized_text, CONTINUATION_MARKERS)
    unresolved_count = _count_terms(normalized_text, UNRESOLVED_REFERENCE_MARKERS)
    ambiguous_choice_count = _count_terms(normalized_text, AMBIGUOUS_CHOICE_MARKERS)
    context_repair_count = _count_terms(normalized_text, CONTEXT_REPAIR_MARKERS)

    prior_memory_request = prior_memory_count > 0
    continuation = continuation_count > 0
    unresolved = unresolved_count > 0
    ctx_signal_present = _ctx_signal_present(ctx_hints or {})
    reference_kind = _reference_kind(
        prior_memory_count=prior_memory_count,
        continuation_count=continuation_count,
        unresolved_count=unresolved_count,
        ambiguous_choice_count=ambiguous_choice_count,
        context_repair_count=context_repair_count,
    )
    intents = _intent_kinds(
        prior_memory_request=prior_memory_request,
        continuation=continuation,
        unresolved=unresolved,
        correction_count=_count_terms(normalized_text, CORRECTION_MARKERS),
        review_count=_count_terms(normalized_text, REVIEW_MARKERS),
        implementation_count=_count_terms(normalized_text, IMPLEMENTATION_MARKERS),
    )
    ambiguity = _ambiguity_detected(
        reference_kind=reference_kind,
        continuation=continuation,
        prior_memory_request=prior_memory_request,
        ctx_signal_present=ctx_signal_present,
    )
    clarification = unresolved or ambiguity
    reference_terms_count = prior_memory_count + continuation_count + unresolved_count
    confidence = _confidence_score(
        reference_kind=reference_kind,
        prior_memory_request=prior_memory_request,
        continuation=continuation,
        ambiguity=ambiguity,
        ctx_signal_present=ctx_signal_present,
    )
    governance = build_analyzer_candidate_artifact(
        analyzer_kind=ANALYZER_KIND,
        source=source,
        source_language=language,
        is_estimate=True,
        source_authoritative=False,
        candidate_applied=reference_terms_count > 0,
        policy_authority="restrictive" if clarification else "none",
        restrictive_only=True,
        confidence=confidence,
        stability=confidence,
        content_free=True,
        reason_ids=_reason_ids(reference_kind, ambiguity, clarification),
    )
    return normalize_reference_intent_artifact({
        "schema_version": SCHEMA_VERSION,
        "analyzer_kind": ANALYZER_KIND,
        "source": governance["source"],
        "source_language": governance["source_language"],
        "reference_kind": reference_kind,
        "intent_kinds": intents,
        "ambiguity_detected": ambiguity,
        "unresolved_reference_detected": unresolved,
        "prior_memory_request_detected": prior_memory_request,
        "continuation_detected": continuation,
        "clarification_recommended": clarification,
        "confidence": governance["confidence"],
        "stability": governance["stability"],
        "is_estimate": governance["is_estimate"],
        "source_authoritative": governance["source_authoritative"],
        "candidate_applied": governance["candidate_applied"],
        "policy_authority": governance["policy_authority"],
        "restrictive_only": governance["restrictive_only"],
        "content_free": True,
        "reason_ids": list(governance["reason_ids"]),
        "validation_errors": list(governance["validation_errors"]),
        "reference_terms_detected_count": reference_terms_count,
        "governance": governance,
    })


def normalize_reference_intent_artifact(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = artifact or {}
    errors: list[str] = _string_list(raw.get("validation_errors"))
    for key in raw:
        if key not in _ALLOWED_KEYS:
            errors.append(
                "raw_diagnostic_field_dropped" if key in _RAW_TEXT_LIKE_KEYS else "unsupported_field_dropped"
            )

    if raw.get("schema_version") != SCHEMA_VERSION:
        errors.append("unknown_enum_value")
    analyzer_kind = raw.get("analyzer_kind") if isinstance(raw.get("analyzer_kind"), str) else "unknown"
    if analyzer_kind != ANALYZER_KIND:
        analyzer_kind = "unknown"
        errors.append("invalid_analyzer_kind")

    reference_kind = _clean_enum(raw.get("reference_kind"), REFERENCE_KINDS, errors)
    raw_intents = raw.get("intent_kinds")
    if isinstance(raw_intents, str):
        intent_values: Iterable[Any] = (raw_intents,)
    elif isinstance(raw_intents, Iterable):
        intent_values = raw_intents
    else:
        intent_values = ()
    intent_kinds = _dedupe(_clean_enum(value, INTENT_KINDS, errors) for value in intent_values)
    if "unknown" in intent_kinds:
        intent_kinds = ["unknown"]

    governance = raw.get("governance")
    if isinstance(governance, Mapping):
        governance = normalize_analyzer_candidate_artifact(governance)
    else:
        governance = build_analyzer_candidate_artifact(
            analyzer_kind=ANALYZER_KIND,
            source=raw.get("source") if isinstance(raw.get("source"), str) else "unknown",
            source_language=raw.get("source_language") if isinstance(raw.get("source_language"), str) else "und",
            is_estimate=True,
            source_authoritative=False,
            candidate_applied=False,
            policy_authority="none",
            restrictive_only=True,
            confidence=0.0,
            stability=0.0,
            content_free=True,
            validation_errors=errors,
        )
    governance_public = content_free_projection(governance)
    return {
        "schema_version": SCHEMA_VERSION,
        "analyzer_kind": analyzer_kind,
        "source": governance["source"],
        "source_language": governance["source_language"],
        "reference_kind": reference_kind,
        "intent_kinds": intent_kinds,
        "ambiguity_detected": raw.get("ambiguity_detected") is True,
        "unresolved_reference_detected": raw.get("unresolved_reference_detected") is True,
        "prior_memory_request_detected": raw.get("prior_memory_request_detected") is True,
        "continuation_detected": raw.get("continuation_detected") is True,
        "clarification_recommended": raw.get("clarification_recommended") is True,
        "confidence": governance["confidence"],
        "stability": governance["stability"],
        "is_estimate": governance["is_estimate"],
        "source_authoritative": governance["source_authoritative"],
        "candidate_applied": governance["candidate_applied"],
        "policy_authority": governance["policy_authority"],
        "restrictive_only": governance["restrictive_only"],
        "content_free": True,
        "reason_ids": list(governance["reason_ids"]),
        "validation_errors": _dedupe([*errors, *list(governance["validation_errors"])]),
        "reference_terms_detected_count": _non_negative_int(raw.get("reference_terms_detected_count")),
        "runtime_policy_open_allowed": can_open_runtime_policy(governance),
        "governance": governance,
        "governance_public": governance_public,
    }


def reference_intent_public_projection(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized = normalize_reference_intent_artifact(artifact)
    return {
        "schema_version": normalized["schema_version"],
        "analyzer_kind": normalized["analyzer_kind"],
        "source": normalized["source"],
        "source_language": normalized["source_language"],
        "reference_kind": normalized["reference_kind"],
        "intent_kinds": tuple(normalized["intent_kinds"]),
        "ambiguity_detected": normalized["ambiguity_detected"],
        "unresolved_reference_detected": normalized["unresolved_reference_detected"],
        "prior_memory_request_detected": normalized["prior_memory_request_detected"],
        "continuation_detected": normalized["continuation_detected"],
        "clarification_recommended": normalized["clarification_recommended"],
        "confidence_bucket": normalized["governance_public"]["confidence_bucket"],
        "is_estimate": normalized["is_estimate"],
        "source_authoritative": normalized["source_authoritative"],
        "candidate_applied": normalized["candidate_applied"],
        "policy_authority": normalized["policy_authority"],
        "restrictive_only": normalized["restrictive_only"],
        "content_free": True,
        "reason_ids": tuple(normalized["reason_ids"]),
        "validation_error_ids": tuple(normalized["validation_errors"]),
        "reference_terms_detected_count": normalized["reference_terms_detected_count"],
        "runtime_policy_open_allowed": normalized["runtime_policy_open_allowed"],
        "governance": normalized["governance_public"],
    }


def relayint_legacy_reference_kind(artifact: Mapping[str, Any] | None) -> str:
    normalized = normalize_reference_intent_artifact(artifact)
    if normalized["prior_memory_request_detected"]:
        return "prior_memory_request"
    if normalized["continuation_detected"]:
        return "continuation"
    if normalized["unresolved_reference_detected"]:
        return "pronoun_like"
    return "none"


def _latest_user_text(messages: Sequence[Mapping[str, Any]]) -> str:
    for message in reversed(messages):
        if isinstance(message, Mapping) and message.get("role") == "user":
            return _content_text(message.get("content"))
    return ""


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence) and not isinstance(content, str):
        return "\n".join(
            item["text"]
            for item in content
            if isinstance(item, Mapping) and isinstance(item.get("text"), str)
        )
    return ""


def _detect_language(text: str) -> str:
    if any("\u3040" <= char <= "\u30ff" or "\u4e00" <= char <= "\u9fff" for char in text):
        return "ja"
    if any(char.isascii() and char.isalpha() for char in text):
        return "en"
    return "und"


def _count_terms(text: str, terms: Sequence[str]) -> int:
    return sum(1 for term in terms if term in text)


def _reference_kind(
    *,
    prior_memory_count: int,
    continuation_count: int,
    unresolved_count: int,
    ambiguous_choice_count: int,
    context_repair_count: int,
) -> str:
    if prior_memory_count > 0:
        return "prior_memory_reference"
    if ambiguous_choice_count > 0:
        return "ambiguous_choice"
    if context_repair_count > 0:
        return "context_repair_request"
    if continuation_count > 0:
        return "prior_turn_reference"
    if unresolved_count > 0:
        return "unresolved_deictic"
    return "none"


def _intent_kinds(
    *,
    prior_memory_request: bool,
    continuation: bool,
    unresolved: bool,
    correction_count: int,
    review_count: int,
    implementation_count: int,
) -> list[str]:
    intents: list[str] = []
    if continuation:
        intents.append("continuation")
    if unresolved:
        intents.append("clarification_request")
    if prior_memory_request:
        intents.append("prior_memory_request")
    if correction_count > 0:
        intents.append("correction_request")
    if review_count > 0:
        intents.append("review_request")
    if implementation_count > 0:
        intents.append("implementation_request")
    return intents


def _ambiguity_detected(
    *,
    reference_kind: str,
    continuation: bool,
    prior_memory_request: bool,
    ctx_signal_present: bool,
) -> bool:
    if reference_kind == "none" or prior_memory_request:
        return False
    if continuation:
        return not ctx_signal_present
    return True


def _confidence_score(
    *,
    reference_kind: str,
    prior_memory_request: bool,
    continuation: bool,
    ambiguity: bool,
    ctx_signal_present: bool,
) -> float:
    if prior_memory_request:
        return 0.82
    if ambiguity:
        return 0.48
    if continuation and ctx_signal_present:
        return 0.84
    if reference_kind == "none":
        return 0.74
    return 0.60


def _reason_ids(reference_kind: str, ambiguity: bool, clarification: bool) -> list[str]:
    reasons: list[str] = []
    if reference_kind != "none":
        reasons.append("fail_closed_candidate_source")
    if ambiguity or clarification:
        reasons.append("candidate_not_applied")
    return reasons


def _ctx_signal_present(ctx_hints: Mapping[str, Any]) -> bool:
    if any(_usable_string(ctx_hints.get(key)) for key in ("current_topic", "active_question", "next_expected_action")):
        return True
    return _usable_referable_item_count(ctx_hints.get("referable_items")) > 0


def _usable_referable_item_count(referable_items: Any) -> int:
    if not isinstance(referable_items, list):
        return 0
    fields = ("label", "kind", "id", "topic_anchor", "text", "name")
    return sum(
        1
        for item in referable_items
        if isinstance(item, Mapping) and any(_usable_string(item.get(field)) for field in fields)
    )


def _usable_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _clean_enum(value: Any, allowed: frozenset[str], errors: list[str]) -> str:
    if not isinstance(value, str) or value.strip().lower() not in allowed:
        errors.append("unknown_enum_value")
        return "unknown"
    return value.strip().lower()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [item for item in value if isinstance(item, str)]


def _non_negative_int(value: Any) -> int:
    return max(0, value) if isinstance(value, int) and not isinstance(value, bool) else 0


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
