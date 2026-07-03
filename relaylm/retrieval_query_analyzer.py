"""ACG-governed RelayMEM retrieval query analyzer candidates.

This module keeps backend-private retrieval hints separate from public,
content-free diagnostics. Its analyzer output is a restrictive candidate: it may
provide bounded query terms to the existing read-only RelayMEM candidate
selection path, but it cannot open broader retrieval policy or memory mutation.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from relaylm.analyzer_governance import (
    build_analyzer_candidate_artifact,
    can_open_runtime_policy,
    content_free_projection,
)

RETRIEVAL_QUERY_SCHEMA_VERSION = "relaylm.retrieval_query_analyzer.v0"
ANALYZER_KIND = "retrieval_query_candidate"

QUERY_HINT_STRATEGIES = frozenset({
    "empty_fallback",
    "whitespace_fallback",
    "bounded_ngram_fallback",
    "mixed_fallback",
})

_MAX_HINTS = 6
_MAX_HINT_CHARS = 32
_MAX_NGRAM_HINTS = 6
_MAX_NGRAM_CHARS = 8

_STRIP_CHARS = "\ufeff\u200b\r\n\t .,!?。！？、:;()[]{}\"'`<>«»“”‘’"
_ASCII_WORD_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-./:"
)
_PUNCT_OR_SPACE = frozenset(_STRIP_CHARS) | frozenset(
    "・/\\|=@#$%^&*+~，．；：（）［］｛｝【】『』「」"
)

_AMBIGUOUS_REFERENCE_MARKERS = (
    "which one",
    "what was that",
    "that one",
    "それ",
    "これ",
    "あれ",
    "さっき",
    "どっち",
    "どれ",
    "何の話",
    "わから",
)


def analyze_retrieval_query(
    text: str | None,
    *,
    source: str = "heuristic",
    source_language: str | None = None,
    query_hint_strategy: str | None = None,
    max_hints: int = _MAX_HINTS,
) -> dict[str, Any]:
    """Build a restrictive Retrieval Query Analyzer candidate artifact.

    The returned artifact contains backend-private hint strings. Do not expose
    it directly in public diagnostics; use ``public_retrieval_query_projection``
    for content-free output.
    """

    raw_text = text if isinstance(text, str) else ""
    normalized_max_hints = _bounded_int(
        max_hints,
        default=_MAX_HINTS,
        minimum=0,
        maximum=_MAX_HINTS,
    )
    language = source_language or _estimate_source_language(raw_text)
    validation_errors: list[str] = []

    whitespace_terms = _whitespace_hints(raw_text, max_hints=normalized_max_hints)
    ngram_hints = _bounded_ngram_hints(
        raw_text,
        max_hints=max(0, min(_MAX_NGRAM_HINTS, normalized_max_hints)),
    )

    if query_hint_strategy is None:
        strategy = _select_strategy(
            whitespace_terms=whitespace_terms,
            ngram_hints=ngram_hints,
            text=raw_text,
        )
    elif query_hint_strategy in QUERY_HINT_STRATEGIES:
        strategy = query_hint_strategy
    else:
        strategy = "unknown"
        validation_errors.append("unknown_query_hint_strategy")

    if strategy == "whitespace_fallback":
        backend_private_hints = whitespace_terms[:normalized_max_hints]
    elif strategy == "bounded_ngram_fallback":
        backend_private_hints = ngram_hints[:normalized_max_hints]
    elif strategy == "mixed_fallback":
        backend_private_hints = _dedupe_strings(
            [*whitespace_terms, *ngram_hints],
            max_items=normalized_max_hints,
        )
    elif strategy == "empty_fallback":
        backend_private_hints = []
    else:
        backend_private_hints = []

    confidence = 0.35 if backend_private_hints else 0.0
    stability = 0.4 if backend_private_hints else 0.0
    governance = build_analyzer_candidate_artifact(
        analyzer_kind=ANALYZER_KIND,
        source=source,
        source_language=language,
        is_estimate=True,
        source_authoritative=False,
        candidate_applied=False,
        policy_authority="restrictive",
        restrictive_only=True,
        confidence=confidence,
        stability=stability,
        content_free=True,
        validation_errors=[],
        reason_ids=[],
    )

    return {
        "schema_version": RETRIEVAL_QUERY_SCHEMA_VERSION,
        "analyzer_kind": ANALYZER_KIND,
        "governance": governance,
        "source": governance["source"],
        "source_language": governance["source_language"],
        "query_hint_strategy": strategy,
        "query_hint_count": len(backend_private_hints),
        "has_ambiguous_reference": has_ambiguous_reference(raw_text),
        "structured_terms": tuple(whitespace_terms),
        "bounded_ngram_hints": tuple(ngram_hints),
        "backend_private_hints": tuple(backend_private_hints),
        "confidence": governance["confidence"],
        "is_estimate": governance["is_estimate"],
        "source_authoritative": governance["source_authoritative"],
        "candidate_applied": governance["candidate_applied"],
        "policy_authority": governance["policy_authority"],
        "restrictive_only": governance["restrictive_only"],
        "content_free": False,
        "reason_ids": tuple(governance["reason_ids"]),
        "validation_errors": tuple(
            _dedupe_strings([*governance["validation_errors"], *validation_errors])
        ),
    }


def retrieval_query_backend_hints(artifact: Mapping[str, Any] | None) -> list[str]:
    """Return bounded backend-private hint strings for read-only selection."""

    if not isinstance(artifact, Mapping):
        return []
    if artifact.get("query_hint_strategy") not in QUERY_HINT_STRATEGIES:
        return []
    raw_hints = artifact.get("backend_private_hints")
    if not isinstance(raw_hints, Sequence) or isinstance(raw_hints, str):
        return []
    hints: list[str] = []
    for raw in raw_hints:
        hint = _clean_hint(str(raw), max_chars=_MAX_HINT_CHARS)
        if len(hint) < 2 or hint in hints:
            continue
        hints.append(hint)
        if len(hints) >= _MAX_HINTS:
            break
    return hints


def public_retrieval_query_projection(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return content-free public diagnostics for a retrieval query candidate."""

    if not isinstance(artifact, Mapping):
        artifact = analyze_retrieval_query("")
    governance = artifact.get("governance")
    governance_public = content_free_projection(
        governance if isinstance(governance, Mapping) else None
    )
    validation_errors = _dedupe_strings([
        *_as_string_sequence(governance_public.get("validation_error_ids")),
        *_as_string_sequence(artifact.get("validation_errors")),
    ])
    return {
        "schema_version": RETRIEVAL_QUERY_SCHEMA_VERSION,
        "analyzer_kind": ANALYZER_KIND,
        "source_class": governance_public.get("source_class", "unknown"),
        "source_language": str(artifact.get("source_language", "und")),
        "query_hint_strategy": _public_strategy(artifact.get("query_hint_strategy")),
        "query_hint_count": _bounded_int(
            artifact.get("query_hint_count"),
            default=0,
            minimum=0,
            maximum=_MAX_HINTS,
        ),
        "has_ambiguous_reference": artifact.get("has_ambiguous_reference") is True,
        "source_authoritative": governance_public.get("source_authoritative") is True,
        "policy_authority": governance_public.get("policy_authority", "none"),
        "restrictive_only": governance_public.get("restrictive_only") is not False,
        "candidate_applied": governance_public.get("candidate_applied") is True,
        "confidence_bucket": governance_public.get("confidence_bucket", "low"),
        "stability_bucket": governance_public.get("stability_bucket", "low"),
        "can_open_runtime_policy": can_open_runtime_policy(
            governance if isinstance(governance, Mapping) else None
        ),
        "reason_ids": tuple(_as_string_sequence(governance_public.get("reason_ids"))),
        "validation_error_ids": tuple(validation_errors),
        "content_free": True,
    }


def has_ambiguous_reference(text: str | None) -> bool:
    raw_text = text if isinstance(text, str) else ""
    lowered = raw_text.lower()
    return any(marker in lowered for marker in _AMBIGUOUS_REFERENCE_MARKERS)


def whitespace_fallback_hints(text: str | None, *, max_hints: int = _MAX_HINTS) -> list[str]:
    return _whitespace_hints(text if isinstance(text, str) else "", max_hints=max_hints)


def _select_strategy(
    *,
    whitespace_terms: Sequence[str],
    ngram_hints: Sequence[str],
    text: str,
) -> str:
    if whitespace_terms and ngram_hints and _has_no_whitespace_text(text):
        return "mixed_fallback"
    if whitespace_terms and ngram_hints and _contains_cjk(text):
        return "mixed_fallback"
    if whitespace_terms:
        return "whitespace_fallback"
    if ngram_hints:
        return "bounded_ngram_fallback"
    return "empty_fallback"


def _whitespace_hints(text: str, *, max_hints: int) -> list[str]:
    terms: list[str] = []
    for raw in text.replace("\n", " ").split(" "):
        term = _clean_hint(raw, max_chars=_MAX_HINT_CHARS)
        if len(term) < 3 or term in terms:
            continue
        terms.append(term)
        if len(terms) >= max(0, max_hints):
            break
    return terms


def _bounded_ngram_hints(text: str, *, max_hints: int) -> list[str]:
    if max_hints <= 0:
        return []
    compact = _compact_for_ngram(text)
    if len(compact) < 2:
        return []
    width = 3 if len(compact) >= 3 else 2
    hints: list[str] = []
    for index in range(0, max(1, len(compact) - width + 1)):
        hint = compact[index : index + width]
        hint = _clean_hint(hint, max_chars=_MAX_NGRAM_CHARS)
        if len(hint) < 2 or hint in hints:
            continue
        hints.append(hint)
        if len(hints) >= max_hints:
            break
    return hints


def _compact_for_ngram(text: str) -> str:
    chars: list[str] = []
    for char in text:
        if char in _PUNCT_OR_SPACE or ord(char) < 32 or ord(char) == 127:
            continue
        chars.append(char)
    return "".join(chars)[:128]


def _clean_hint(raw: str, *, max_chars: int) -> str:
    term = str(raw).strip(_STRIP_CHARS)
    term = " ".join(term.split())
    if len(term) > max_chars:
        term = term[:max_chars]
    return term


def _public_strategy(value: object) -> str:
    token = str(value) if isinstance(value, str) else "unknown"
    if token in QUERY_HINT_STRATEGIES:
        return token
    return "unknown"


def _bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        numeric = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, numeric))


def _dedupe_strings(values: Iterable[str], *, max_items: int | None = None) -> list[str]:
    deduped: list[str] = []
    for raw in values:
        value = str(raw)
        if not value or value in deduped:
            continue
        deduped.append(value)
        if max_items is not None and len(deduped) >= max_items:
            break
    return deduped


def _as_string_sequence(value: object) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


def _has_no_whitespace_text(text: str) -> bool:
    return bool(text) and not any(char.isspace() for char in text)


def _contains_cjk(text: str) -> bool:
    return any(
        "\u3040" <= char <= "\u30ff"
        or "\u3400" <= char <= "\u9fff"
        or "\uf900" <= char <= "\ufaff"
        or "\uac00" <= char <= "\ud7af"
        for char in text
    )


def _estimate_source_language(text: str) -> str:
    if any("\u3040" <= char <= "\u30ff" for char in text):
        return "ja"
    if any("\uac00" <= char <= "\ud7af" for char in text):
        return "ko"
    if any("\u3400" <= char <= "\u9fff" or "\uf900" <= char <= "\ufaff" for char in text):
        return "zh"
    if any(char in _ASCII_WORD_CHARS for char in text):
        return "en"
    return "und"
