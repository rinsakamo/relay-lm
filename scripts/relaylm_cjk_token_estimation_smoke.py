#!/usr/bin/env python3
"""Deterministic Phase 5-D1 CJK-aware token estimation smoke."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.memory_candidate import MemoryCandidate
from relaylm.memory_token_budget import assemble_token_budget_memory_block
from relaylm.token_budget import (
    estimate_text_tokens,
    estimate_text_tokens_detailed,
    fits_token_budget,
)
from relaylm.token_budget_truncation import apply_token_budget_message_truncation


def legacy_estimate(text: str, chars_per_token: int = 4) -> int:
    return (len(text) + chars_per_token - 1) // chars_per_token


def main() -> int:
    empty = estimate_text_tokens_detailed("")
    assert empty.text_characters == 0
    assert empty.estimated_tokens == 0
    assert empty.to_log_dict()["cjk_characters"] == 0

    ascii_text = "hello world"
    ascii_estimate = estimate_text_tokens_detailed(ascii_text)
    assert ascii_estimate.ascii_word_characters == 10
    assert ascii_estimate.whitespace_characters == 1
    assert ascii_estimate.estimated_tokens >= legacy_estimate(ascii_text)

    japanese_text = "これは日本語です。"
    japanese_estimate = estimate_text_tokens_detailed(japanese_text)
    assert japanese_estimate.cjk_characters == len(japanese_text)
    assert japanese_estimate.cjk_tokens == len(japanese_text)
    assert japanese_estimate.estimated_tokens == len(japanese_text)
    assert japanese_estimate.estimated_tokens > legacy_estimate(japanese_text)

    mixed_text = "RelayLMは日本語OKです"
    mixed_estimate = estimate_text_tokens_detailed(mixed_text)
    assert mixed_estimate.ascii_word_characters > 0
    assert mixed_estimate.cjk_characters > 0
    assert mixed_estimate.estimated_tokens >= legacy_estimate(mixed_text)

    markdown_code = "## 見出し\n```python\nvalue = {'日本語': 1}\n```"
    markdown_estimate = estimate_text_tokens_detailed(markdown_code)
    assert markdown_estimate.ascii_punctuation_characters > 0
    assert markdown_estimate.cjk_characters > 0
    assert markdown_estimate.estimated_tokens >= legacy_estimate(markdown_code)

    family_emoji = "👨‍👩‍👧‍👦"
    emoji_estimate = estimate_text_tokens_detailed(family_emoji)
    assert emoji_estimate.symbol_characters == 4
    assert emoji_estimate.combining_or_format_characters == 3
    assert emoji_estimate.estimated_tokens == 7

    combining = estimate_text_tokens_detailed("e\u0301")
    assert combining.ascii_word_characters == 1
    assert combining.combining_or_format_characters == 1
    assert combining.estimated_tokens == 2

    whitespace = estimate_text_tokens_detailed("   \n")
    assert whitespace.whitespace_characters == 4
    assert whitespace.estimated_tokens == 1

    detailed_payload = json.dumps(
        japanese_estimate.to_log_dict(),
        ensure_ascii=False,
        sort_keys=True,
    )
    assert japanese_text not in detailed_payload
    assert "estimated_tokens" in detailed_payload

    exact = estimate_text_tokens(japanese_text).estimated_tokens
    assert fits_token_budget(japanese_text, token_budget=exact)
    assert not fits_token_budget(japanese_text, token_budget=exact - 1)

    candidates = [
        MemoryCandidate(
            memory_id="ja-a",
            content="日本語の短い記憶です。",
            importance=2,
        ),
        MemoryCandidate(
            memory_id="ja-b",
            content="追加の日本語記憶です。",
            importance=1,
        ),
    ]
    first_line_only = assemble_token_budget_memory_block(
        candidates[:1],
        token_budget=None,
    )
    assert first_line_only.block is not None
    one_line_budget = first_line_only.estimated_tokens
    assembled = assemble_token_budget_memory_block(
        candidates,
        token_budget=one_line_budget,
    )
    assert assembled.included_memory_ids == ["ja-a"]
    assert assembled.dropped_memory_ids == ["ja-b"]
    assert assembled.estimated_tokens <= one_line_budget

    truncation = apply_token_budget_message_truncation(
        messages=[
            {"role": "system", "content": "固定システム指示"},
            {"role": "assistant", "content": "古い日本語履歴" * 20},
            {"role": "user", "content": "最新の質問"},
        ],
        token_budget=25,
        chars_per_token=4,
    )
    assert truncation.dropped_roles == ["assistant"]
    assert truncation.preserved_system is True
    assert truncation.preserved_latest_user is True
    assert truncation.over_budget_after is False

    blocked = apply_token_budget_message_truncation(
        messages=[
            {"role": "system", "content": "必須" * 20},
            {"role": "user", "content": "質問" * 20},
        ],
        token_budget=10,
        chars_per_token=4,
    )
    assert blocked.over_budget_after is True
    assert blocked.blocked_reason == "preserved_messages_exceed_budget"

    print("relaylm_cjk_token_estimation_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
