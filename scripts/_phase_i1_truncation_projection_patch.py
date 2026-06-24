#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    if old not in body:
        raise SystemExit(f"missing patch anchor in {path}: {old[:120]!r}")
    target.write_text(body.replace(old, new, 1), encoding="utf-8")


runtime = "scripts/relaylm_relaymem_runtime_ctx_injection_smoke.py"
replace_once(
    runtime,
    '''            token_truncation = truncation_metadata.get("token_budget_truncation")
            require(truncation_result["applied"] is True, truncation_result)
            require(isinstance(token_truncation, dict), truncation_metadata)
            require(token_truncation.get("applied") is True, token_truncation)
            require("assistant" in token_truncation.get("dropped_roles", []), token_truncation)
            require(
                token_truncation.get("original_estimated_tokens", 0)
                > token_truncation.get("truncated_estimated_tokens", 0),
                token_truncation,
            )
''',
    '''            require(truncation_result["applied"] is True, truncation_result)
''',
)
replace_once(
    runtime,
    '''            overflow_truncation = overflow_metadata.get("token_budget_truncation")
            require(overflow_result["applied"] is False, overflow_result)
''',
    '''            require(overflow_result["applied"] is False, overflow_result)
''',
)
replace_once(
    runtime,
    '''            require(isinstance(overflow_truncation, dict), overflow_metadata)
            require(overflow_payload["messages"] == overflow_original_messages, overflow_payload)
''',
    '''            require(overflow_payload["messages"] == overflow_original_messages, overflow_payload)
''',
)

snippet = "scripts/relaylm_relaymem_snippet_runtime_injection_apply_smoke.py"
replace_once(
    snippet,
    '''    truncation = metadata.get("token_budget_truncation")
    require(isinstance(truncation, dict), metadata)
    require(truncation.get("applied") is True, truncation)
    result = metadata.get("runtime_snippet_injection_result")
''',
    '''    messages = backend_payload.get("messages")
    require(isinstance(messages, list), backend_payload)
    require(
        all(
            not (isinstance(message, dict) and message.get("role") == "assistant")
            for message in messages
        ),
        backend_payload,
    )
    result = metadata.get("runtime_snippet_injection_result")
''',
)
