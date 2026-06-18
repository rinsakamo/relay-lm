"""Deterministic tokenizer-free token budget helpers.

The estimator is intentionally model-agnostic. It preserves the historical
``chars_per_token`` compatibility input for ASCII-heavy text while counting
CJK, punctuation, symbols, and other non-ASCII classes conservatively.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import unicodedata


_ASCII_PUNCTUATION_CHARS_PER_TOKEN = 2
_WHITESPACE_CHARS_PER_TOKEN = 8


@dataclass(frozen=True)
class TokenEstimate:
    text_characters: int
    estimated_tokens: int
    chars_per_token: int

    def to_log_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class TokenEstimateBreakdown:
    """Content-free deterministic estimator diagnostics."""

    text_characters: int
    estimated_tokens: int
    chars_per_token: int
    legacy_estimated_tokens: int
    ascii_word_characters: int
    ascii_punctuation_characters: int
    whitespace_characters: int
    cjk_characters: int
    symbol_characters: int
    combining_or_format_characters: int
    other_non_ascii_characters: int
    ascii_word_tokens: int
    ascii_punctuation_tokens: int
    whitespace_tokens: int
    cjk_tokens: int
    symbol_tokens: int
    combining_or_format_tokens: int
    other_non_ascii_tokens: int

    def to_log_dict(self) -> dict[str, int]:
        return asdict(self)


def estimate_text_tokens(text: str, *, chars_per_token: int = 4) -> TokenEstimate:
    breakdown = estimate_text_tokens_detailed(
        text,
        chars_per_token=chars_per_token,
    )
    return TokenEstimate(
        text_characters=breakdown.text_characters,
        estimated_tokens=breakdown.estimated_tokens,
        chars_per_token=breakdown.chars_per_token,
    )


def estimate_text_tokens_detailed(
    text: str,
    *,
    chars_per_token: int = 4,
) -> TokenEstimateBreakdown:
    """Return a conservative deterministic estimate without tokenizer IO.

    The final estimate never falls below the historical whole-string estimate.
    Category counts contain no source text and are safe for bounded diagnostics.
    """

    if chars_per_token <= 0:
        raise ValueError("chars_per_token must be positive")

    counts = {
        "ascii_word": 0,
        "ascii_punctuation": 0,
        "whitespace": 0,
        "cjk": 0,
        "symbol": 0,
        "combining_or_format": 0,
        "other_non_ascii": 0,
    }
    for character in text:
        counts[_classify_character(character)] += 1

    text_characters = len(text)
    legacy_estimated_tokens = _ceil_div(text_characters, chars_per_token)
    ascii_word_tokens = _ceil_div(counts["ascii_word"], chars_per_token)
    ascii_punctuation_tokens = _ceil_div(
        counts["ascii_punctuation"],
        _ASCII_PUNCTUATION_CHARS_PER_TOKEN,
    )
    whitespace_tokens = _ceil_div(
        counts["whitespace"],
        _WHITESPACE_CHARS_PER_TOKEN,
    )
    cjk_tokens = counts["cjk"]
    symbol_tokens = counts["symbol"]
    combining_or_format_tokens = counts["combining_or_format"]
    other_non_ascii_tokens = counts["other_non_ascii"]

    category_estimated_tokens = sum(
        (
            ascii_word_tokens,
            ascii_punctuation_tokens,
            whitespace_tokens,
            cjk_tokens,
            symbol_tokens,
            combining_or_format_tokens,
            other_non_ascii_tokens,
        )
    )
    estimated_tokens = max(legacy_estimated_tokens, category_estimated_tokens)

    return TokenEstimateBreakdown(
        text_characters=text_characters,
        estimated_tokens=estimated_tokens,
        chars_per_token=chars_per_token,
        legacy_estimated_tokens=legacy_estimated_tokens,
        ascii_word_characters=counts["ascii_word"],
        ascii_punctuation_characters=counts["ascii_punctuation"],
        whitespace_characters=counts["whitespace"],
        cjk_characters=counts["cjk"],
        symbol_characters=counts["symbol"],
        combining_or_format_characters=counts["combining_or_format"],
        other_non_ascii_characters=counts["other_non_ascii"],
        ascii_word_tokens=ascii_word_tokens,
        ascii_punctuation_tokens=ascii_punctuation_tokens,
        whitespace_tokens=whitespace_tokens,
        cjk_tokens=cjk_tokens,
        symbol_tokens=symbol_tokens,
        combining_or_format_tokens=combining_or_format_tokens,
        other_non_ascii_tokens=other_non_ascii_tokens,
    )


def fits_token_budget(
    text: str,
    *,
    token_budget: int | None,
    chars_per_token: int = 4,
) -> bool:
    if token_budget is None:
        return True
    if token_budget <= 0:
        return False
    return (
        estimate_text_tokens(text, chars_per_token=chars_per_token).estimated_tokens
        <= token_budget
    )


def _ceil_div(value: int, divisor: int) -> int:
    if value <= 0:
        return 0
    return (value + divisor - 1) // divisor


def _classify_character(character: str) -> str:
    if character.isascii():
        if character.isspace():
            return "whitespace"
        if character.isalnum() or character == "_":
            return "ascii_word"
        return "ascii_punctuation"

    category = unicodedata.category(character)
    if category in {"Mn", "Mc", "Me", "Cf"}:
        return "combining_or_format"
    if category.startswith("S") or _is_emoji_codepoint(ord(character)):
        return "symbol"
    if _is_cjk_or_fullwidth(character):
        return "cjk"
    if character.isspace():
        return "whitespace"
    return "other_non_ascii"


def _is_cjk_or_fullwidth(character: str) -> bool:
    codepoint = ord(character)
    if unicodedata.east_asian_width(character) in {"W", "F"}:
        return True
    return any(
        start <= codepoint <= end
        for start, end in (
            (0x2E80, 0x2FFF),
            (0x3040, 0x30FF),
            (0x3100, 0x31FF),
            (0x3400, 0x4DBF),
            (0x4E00, 0x9FFF),
            (0xAC00, 0xD7FF),
            (0xF900, 0xFAFF),
            (0xFF01, 0xFFEE),
            (0x20000, 0x2FA1F),
        )
    )


def _is_emoji_codepoint(codepoint: int) -> bool:
    return any(
        start <= codepoint <= end
        for start, end in (
            (0x1F000, 0x1FAFF),
            (0x2600, 0x27BF),
        )
    )
