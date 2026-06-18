#!/usr/bin/env python3
"""Phase 5-D1 RelayMEM runtime-injection estimate alignment smoke."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.relaymem_runtime_ctx import (
    maybe_apply_relaymem_runtime_ctx_injection,
    maybe_apply_relaymem_snippet_runtime_injection,
)
from relaylm.token_budget import estimate_text_tokens


def _inserted_content(forwarded: dict[str, object], prefix: str) -> str:
    messages = forwarded.get("messages")
    assert isinstance(messages, list), forwarded
    matches = [
        message.get("content")
        for message in messages
        if isinstance(message, dict)
        and message.get("role") == "system"
        and isinstance(message.get("content"), str)
        and message["content"].startswith(prefix)
    ]
    assert len(matches) == 1, forwarded
    return str(matches[0])


def main() -> int:
    chars_per_token = 7
    payload = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "最新の質問です"}],
    }

    japanese_path = "memory/mem/projects/日本語の長期記憶" + "日本語" * 30 + ".md"
    context_artifact = {
        "apply_decision": "eligible_but_not_applied",
        "ctx_block": None,
        "ctx_injection_plan": {
            "preview_text": "preview",
            "applied": False,
            "blocked_reasons": ["runtime_ctx_injection_not_implemented"],
            "source_entries": [
                {
                    "path": japanese_path,
                    "reason": "日本語の関連理由" * 8,
                }
            ],
        },
    }
    context_forwarded, context_result = maybe_apply_relaymem_runtime_ctx_injection(
        payload=payload,
        relaymem_retrieval_artifact=context_artifact,
        ctx_block_apply_enabled=True,
        retrieval_dry_run_only=False,
        chars_per_token=chars_per_token,
    )
    assert context_result["applied"] is True, context_result
    context_content = _inserted_content(context_forwarded, "[RelayMEM Context]")
    context_expected = estimate_text_tokens(
        context_content,
        chars_per_token=chars_per_token,
    ).estimated_tokens
    assert context_result["estimated_tokens"] == context_expected, context_result
    assert context_expected > max(1, len(context_content) // 4)

    snippet_body = "日本語スニペットの本文です。" * 40
    snippet_artifact = {
        "snippet_apply_decision": "eligible_but_not_applied",
        "ctx_block": None,
        "apply_allowed": False,
        "snippet_runtime_injection_plan": {
            "preview_text": "header\nmetadata\n---\n" + snippet_body,
            "applied": False,
            "blocked_reasons": ["runtime_snippet_injection_not_implemented"],
        },
    }
    snippet_forwarded, snippet_result = maybe_apply_relaymem_snippet_runtime_injection(
        payload=payload,
        relaymem_retrieval_artifact=snippet_artifact,
        ctx_block_apply_enabled=True,
        retrieval_dry_run_only=False,
        snippet_apply_enabled=True,
        snippet_dry_run_only=False,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
        chars_per_token=chars_per_token,
    )
    assert snippet_result["applied"] is True, snippet_result
    snippet_content = _inserted_content(
        snippet_forwarded,
        "[RelayMEM Snippet Context]",
    )
    snippet_expected = estimate_text_tokens(
        snippet_content,
        chars_per_token=chars_per_token,
    ).estimated_tokens
    assert snippet_result["estimated_tokens"] == snippet_expected, snippet_result
    assert snippet_expected > max(1, len(snippet_content) // 4)

    encoded = json.dumps(
        {"context": context_result, "snippet": snippet_result},
        ensure_ascii=False,
        sort_keys=True,
    )
    assert japanese_path not in encoded
    assert snippet_body not in encoded

    print("relaylm_relaymem_cjk_runtime_estimation_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
