"""Shared low-level text-feature helpers for RelayLM analyzer candidates.

This module is internal to the analyzer layer (query detail / retrieval
query / reference intent). It centralizes bounded CJK/language detection,
token normalization, and marker-catalog primitives that were previously
duplicated across those analyzers, so future policy changes land in one
place.

This is not a public API and does not define any analyzer contract,
artifact schema, or reason ID. Each analyzer module keeps its own public
API, schema, and reason IDs; where an analyzer's existing behavior
differs subtly from another's (for example language inference), this
module keeps the distinct original logic under a distinct name rather
than merging it into a single implementation that would change behavior.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

_HIRAGANA_KATAKANA = ("぀", "ヿ")
_CJK_UNIFIED = ("㐀", "鿿")
_CJK_COMPAT = ("豈", "﫿")
_HANGUL_SYLLABLES = ("가", "힯")

_ASCII_WORD_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-./:"
)

_JA_CORE_RE = re.compile(r"[぀-ヿ㐀-鿿]")
_JA_UNIFIED_NO_EXT_A_RE = re.compile(r"[぀-ヿ一-鿿]")


def has_cjk(text: str) -> bool:
    """Return True if ``text`` contains any CJK-family codepoint.

    Uses the extended range set (hiragana/katakana, CJK unified, CJK
    compatibility, hangul) historically used by the retrieval query
    analyzer's mixed-fallback strategy selection.
    """
    for char in text:
        if _HIRAGANA_KATAKANA[0] <= char <= _HIRAGANA_KATAKANA[1]:
            return True
        if _CJK_UNIFIED[0] <= char <= _CJK_UNIFIED[1]:
            return True
        if _CJK_COMPAT[0] <= char <= _CJK_COMPAT[1]:
            return True
        if _HANGUL_SYLLABLES[0] <= char <= _HANGUL_SYLLABLES[1]:
            return True
    return False


def has_core_cjk(text: str) -> bool:
    """Narrower CJK check: hiragana/katakana + CJK unified only.

    Matches the query detail analyzer's original ``_JA_RE`` check.
    """
    return bool(_JA_CORE_RE.search(text))


def estimate_query_language(text: str) -> str:
    """Estimate a coarse ja/ko/zh/en/und language tag for a query string.

    Mirrors the retrieval query analyzer's original source-language
    estimate: CJK-family scripts take priority over ASCII word chars.
    """
    if any(_HIRAGANA_KATAKANA[0] <= char <= _HIRAGANA_KATAKANA[1] for char in text):
        return "ja"
    if any(_HANGUL_SYLLABLES[0] <= char <= _HANGUL_SYLLABLES[1] for char in text):
        return "ko"
    if any(
        _CJK_UNIFIED[0] <= char <= _CJK_UNIFIED[1] or _CJK_COMPAT[0] <= char <= _CJK_COMPAT[1]
        for char in text
    ):
        return "zh"
    if any(char in _ASCII_WORD_CHARS for char in text):
        return "en"
    return "und"


def infer_simple_language(text: object) -> str:
    """und/ja/en language inference used by the query detail analyzer.

    Whitespace-only or non-string input is "und". Core CJK codepoints win
    as "ja"; otherwise pure-ASCII text is "en"; anything else is "und".
    """
    if not isinstance(text, str) or not text.strip():
        return "und"
    if has_core_cjk(text):
        return "ja"
    if text.isascii():
        return "en"
    return "und"


def detect_reference_language(text: str) -> str:
    """und/ja/en language detection used by the reference intent analyzer."""
    if _JA_UNIFIED_NO_EXT_A_RE.search(text):
        return "ja"
    if any(char.isascii() and char.isalpha() for char in text):
        return "en"
    return "und"


def normalize_token(value: object, default: str) -> str:
    """Strip/lower a string value, falling back to ``default`` when empty."""
    if not isinstance(value, str):
        return default
    token = value.strip().lower()
    return token or default


def unique_preserve_order(values: Iterable[object], *, max_items: int | None = None) -> list[str]:
    """Deduplicate ``values`` (stringified) preserving first-seen order.

    Falsy/empty stringified values are dropped.
    """
    result: list[str] = []
    for raw in values:
        value = str(raw)
        if not value or value in result:
            continue
        result.append(value)
        if max_items is not None and len(result) >= max_items:
            break
    return result


def as_string_sequence(value: object) -> list[str]:
    """Coerce a sequence (or bare string) into a list of strings."""
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


# --- marker catalog ---------------------------------------------------------
#
# Marker literals below are moved verbatim from the analyzers that owned
# them; sets that differ across analyzers are kept as distinct constants
# rather than merged, so marker-match behavior does not change.

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

RETRIEVAL_AMBIGUOUS_REFERENCE_MARKERS = (
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


def contains_any_marker(text: str, markers: Sequence[str]) -> bool:
    """Case-insensitive substring match against a marker catalog entry."""
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def count_markers(text: str, markers: Sequence[str]) -> int:
    """Count how many markers appear in already-normalized ``text``."""
    return sum(1 for marker in markers if marker in text)


__all__ = [
    "AMBIGUOUS_CHOICE_MARKERS",
    "CONTEXT_REPAIR_MARKERS",
    "CONTINUATION_MARKERS",
    "CORRECTION_MARKERS",
    "IMPLEMENTATION_MARKERS",
    "PRIOR_MEMORY_REQUEST_MARKERS",
    "RETRIEVAL_AMBIGUOUS_REFERENCE_MARKERS",
    "REVIEW_MARKERS",
    "UNRESOLVED_REFERENCE_MARKERS",
    "as_string_sequence",
    "contains_any_marker",
    "count_markers",
    "detect_reference_language",
    "estimate_query_language",
    "has_cjk",
    "has_core_cjk",
    "infer_simple_language",
    "normalize_token",
    "unique_preserve_order",
]
