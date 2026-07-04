#!/usr/bin/env python3
"""Smoke coverage for the CTX Repack final token-budget gate ordering fix.

Before this fix, `apply_relayctx_short_term_runtime_injection_phase` ran after
`apply_token_budget_truncation_phase` in `relaylm/app.py`, so a short-term
injection could grow the forwarded payload past `config.memory.token_budget`
with nothing left to catch it (`token_budget_truncation` was assumed to be
the final mutation gate, but was not in the actual call order). This smoke
drives the CTX Repack phase functions directly, in the fixed order, and
proves two invariants:

1. the final truncated forwarded payload's estimated token total never
   exceeds `config.memory.token_budget`, even though short-term injection
   applied and grew the payload first; and
2. token_budget_truncation preserves the short-term injected system block
   through to the final payload (system-role messages are protected from
   drop by `keep_system=True`, regardless of position) instead of discarding
   it.

It also pins `pipeline_context.last_mutating_step == "token_budget_truncation"`
as the expected terminal mutating step after the reorder.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig, load_config
from relaylm.diagnostics import (
    build_relayctx_short_term_block_assembly_dry_run,
    build_relayctx_short_term_extraction_dry_run,
    build_relayctx_short_term_runtime_injection_preflight,
)
from relaylm.pipeline_context import PipelineContext
from relaylm.relayctx_repack import (
    apply_relayctx_short_term_runtime_injection_phase,
    apply_token_budget_truncation_phase,
)
from relaylm.routing import resolve_route
from relaylm.token_budget import estimate_text_tokens

TOKEN_BUDGET = 250
FILLER_MESSAGE_COUNT = 10
FILLER_MESSAGE_CHARS = 400


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _build_config() -> RelayLMConfig:
    data = load_config(REPO_ROOT / "config.example.yaml").model_dump()
    data["relayctx_short_term_source_diagnostics_enabled"] = True
    data["relayctx_short_term_extraction_dry_run_enabled"] = True
    data["relayctx_short_term_block_assembly_dry_run_enabled"] = True
    data["relayctx_short_term_runtime_injection_preflight_enabled"] = True
    data["relayctx_short_term_runtime_injection_apply_enabled"] = True
    data["relayctx_short_term_runtime_injection_dry_run_only"] = False
    data["relayctx_short_term_runtime_injection_token_budget"] = 400
    data["memory"]["token_budget"] = TOKEN_BUDGET
    data["memory"]["token_budget_truncation_enabled"] = True
    data["memory"]["chars_per_token"] = 4
    return RelayLMConfig.model_validate(data)


def _filler_messages() -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for index in range(FILLER_MESSAGE_COUNT):
        role = "assistant" if index % 2 == 0 else "user"
        messages.append(
            {
                "role": role,
                "content": f"filler turn {index} " + ("padding text " * (FILLER_MESSAGE_CHARS // 13)),
            }
        )
    return messages


def _short_term_candidate_messages() -> list[dict[str, Any]]:
    # Deliberately mirrors the candidate phrases used by
    # relaylm_relayctx_short_term_runtime_injection_apply_smoke.py so this
    # smoke exercises the same extraction/assembly/preflight/apply chain.
    return [
        {"role": "user", "content": "今日の合言葉は青いカモメ"},
        {"role": "user", "content": "この一時設定を優先してください"},
        {"role": "user", "content": "今日は温かいお茶ではなく冷たい水にしてください"},
    ]


def _payload_messages() -> list[dict[str, Any]]:
    return _filler_messages() + _short_term_candidate_messages()


def main() -> int:
    config = _build_config()
    route = resolve_route(config, "relaylm-default")
    messages = _payload_messages()
    payload = {"model": "relaylm-default", "messages": messages, "stream": False}

    pipeline_context = PipelineContext(
        request_id="ctx-repack-final-gate-smoke",
        run_id="run-ctx-repack-final-gate-smoke",
        original_payload=payload,
        forwarded_payload=dict(payload),
        route=route,
        stream_enabled=False,
    )

    extraction_dry_run = build_relayctx_short_term_extraction_dry_run(
        messages=messages,
        enabled=config.relayctx_short_term_extraction_dry_run_enabled,
        memory_source=None,
    )
    require(extraction_dry_run is not None, "extraction dry-run must build")
    require(
        extraction_dry_run.get("short_term_candidate_count", 0) > 0,
        (
            "fixture messages must produce short-term candidates; "
            f"extraction_dry_run={extraction_dry_run}"
        ),
    )

    block_assembly_dry_run = build_relayctx_short_term_block_assembly_dry_run(
        extraction_artifact=extraction_dry_run,
        enabled=config.relayctx_short_term_block_assembly_dry_run_enabled,
    )
    preflight = build_relayctx_short_term_runtime_injection_preflight(
        assembly_artifact=block_assembly_dry_run,
        enabled=config.relayctx_short_term_runtime_injection_preflight_enabled,
        dry_run_only=config.relayctx_short_term_runtime_injection_dry_run_only,
    )

    # Fixed order: short-term injection runs before token_budget_truncation,
    # so truncation is the final mutation gate on the forwarded payload.
    _, apply_result = apply_relayctx_short_term_runtime_injection_phase(
        config=config,
        pipeline_context=pipeline_context,
        preflight_artifact=preflight,
    )
    require(isinstance(apply_result, dict), apply_result)
    require(apply_result.get("applied") is True, apply_result)
    require(pipeline_context.last_mutating_step == "relayctx_short_term_runtime_injection", pipeline_context.last_mutating_step)

    inserted_before_truncation = [
        message
        for message in pipeline_context.forwarded_payload.get("messages", [])
        if isinstance(message, dict)
        and message.get("role") == "system"
        and isinstance(message.get("content"), str)
        and message["content"].startswith("[RelayCTX Short-Term Context]")
    ]
    require(len(inserted_before_truncation) == 1, pipeline_context.forwarded_payload)

    pre_truncation_tokens = estimate_text_tokens(
        "\n".join(
            f"{m.get('role')}: {m.get('content')}"
            for m in pipeline_context.forwarded_payload["messages"]
            if isinstance(m, dict)
        ),
        chars_per_token=config.memory.chars_per_token,
    ).estimated_tokens
    require(
        pre_truncation_tokens > TOKEN_BUDGET,
        (
            "fixture must actually exceed config.memory.token_budget before "
            f"truncation runs (got {pre_truncation_tokens} tokens)"
        ),
    )

    _, token_budget_truncation = apply_token_budget_truncation_phase(
        config=config,
        pipeline_context=pipeline_context,
    )
    require(isinstance(token_budget_truncation, dict), token_budget_truncation)
    require(token_budget_truncation.get("over_budget_before") is True, token_budget_truncation)
    require(token_budget_truncation.get("dropped_message_count", 0) > 0, token_budget_truncation)
    require(token_budget_truncation.get("over_budget_after") is False, token_budget_truncation)
    require(token_budget_truncation.get("blocked_reason") is None, token_budget_truncation)
    require(
        token_budget_truncation.get("truncated_estimated_tokens", TOKEN_BUDGET + 1)
        <= TOKEN_BUDGET,
        (
            "final forwarded payload must not exceed config.memory.token_budget "
            f"even with short-term injection applied: {token_budget_truncation}"
        ),
    )
    print(
        "ok final truncated payload stays within config.memory.token_budget "
        "after short-term injection applied first"
    )

    require(
        pipeline_context.last_mutating_step == "token_budget_truncation",
        pipeline_context.last_mutating_step,
    )
    print("ok token_budget_truncation is the terminal CTX Repack mutating step")

    final_messages = pipeline_context.forwarded_payload.get("messages")
    require(isinstance(final_messages, list) and final_messages, pipeline_context.forwarded_payload)
    inserted_after_truncation = [
        message
        for message in final_messages
        if isinstance(message, dict)
        and message.get("role") == "system"
        and isinstance(message.get("content"), str)
        and message["content"].startswith("[RelayCTX Short-Term Context]")
    ]
    require(
        len(inserted_after_truncation) == 1,
        (
            "token_budget_truncation must preserve the short-term injected "
            f"system block instead of dropping it: {final_messages}"
        ),
    )
    print(
        "ok token_budget_truncation preserves the short-term injected system "
        "block through the final gate"
    )

    require(len(final_messages) < len(messages), (len(final_messages), len(messages)))
    print("ok truncation actually dropped filler messages rather than no-op")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
