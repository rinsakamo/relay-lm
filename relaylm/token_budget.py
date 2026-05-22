"""Deterministic token budget helpers for RelayLM MVP-7.

This module intentionally avoids tokenizer dependencies. It provides a stable
rough estimate that can be used for deterministic trimming and diagnostics while
runtime-specific tokenizers remain out of scope.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TokenEstimate:
    text_characters: int
    estimated_tokens: int
    chars_per_token: int

    def to_log_dict(self) -> dict[str, int]:
        return asdict(self)


def estimate_text_tokens(text: str, *, chars_per_token: int = 4) -> TokenEstimate:
    if chars_per_token <= 0:
        raise ValueError("chars_per_token must be positive")
    text_characters = len(text)
    estimated_tokens = (text_characters + chars_per_token - 1) // chars_per_token
    return TokenEstimate(
        text_characters=text_characters,
        estimated_tokens=estimated_tokens,
        chars_per_token=chars_per_token,
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
    return estimate_text_tokens(text, chars_per_token=chars_per_token).estimated_tokens <= token_budget
