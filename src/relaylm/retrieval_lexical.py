from __future__ import annotations

import re
import unicodedata


_CJK_NGRAM_MIN = 2
_CJK_NGRAM_MAX = 3


def lexical_terms(text: str) -> tuple[str, ...]:
    """Return deterministic lexical features while preserving whole-token semantics.

    Existing normalized ``\\w`` tokens remain exact features. Contiguous CJK runs
    additionally contribute bounded 2- and 3-character n-grams so natural CJK
    phrasing differences can still share positive lexical evidence without turning
    Latin/ASCII tokens into substring matches.
    """

    normalized = unicodedata.normalize("NFKC", text).casefold().replace("_", " ")
    features: list[str] = []
    for token in (term for term in re.split(r"[^\w]+", normalized) if term):
        features.append(token)
        for run in _cjk_runs(token):
            for size in range(_CJK_NGRAM_MIN, min(_CJK_NGRAM_MAX, len(run)) + 1):
                features.extend(
                    run[start : start + size]
                    for start in range(len(run) - size + 1)
                )
    return tuple(features)


def lexical_query_terms(text: str) -> frozenset[str]:
    """Return distinct query features eligible for shared retrieval relevance."""

    return frozenset(term for term in lexical_terms(text) if len(term) >= 2)


def _cjk_runs(token: str) -> tuple[str, ...]:
    runs: list[str] = []
    current: list[str] = []
    for char in token:
        if _is_cjk(char):
            current.append(char)
            continue
        if current:
            runs.append("".join(current))
            current = []
    if current:
        runs.append("".join(current))
    return tuple(runs)


def _is_cjk(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x20000 <= codepoint <= 0x2FA1F
        or 0x3040 <= codepoint <= 0x309F
        or 0x30A0 <= codepoint <= 0x30FF
        or 0x31F0 <= codepoint <= 0x31FF
        or 0x1100 <= codepoint <= 0x11FF
        or 0x3130 <= codepoint <= 0x318F
        or 0xAC00 <= codepoint <= 0xD7AF
    )
