"""RelayCTX Repack helpers for backend-bound payload mutation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from relaylm.config import RelayLMConfig
from relaylm.pipeline_context import PipelineContext, replace_pipeline_forwarded_payload
from relaylm.token_budget_truncation import apply_token_budget_message_truncation
from relaylm.relaymem_runtime_ctx import (
    maybe_apply_relaymem_runtime_ctx_injection,
    maybe_apply_relaymem_snippet_runtime_injection,
    skipped_relaymem_runtime_ctx_injection_result,
)


def apply_relaymem_runtime_injection_phase(
    *,
    config: RelayLMConfig,
    pipeline_context: PipelineContext,
    relaymem_retrieval_artifact: dict[str, Any],
    compiled_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Apply RelayMEM snippet/runtime CTX injection as one CTX Repack phase.

    Returns:
        forwarded_payload,
        runtime_ctx_injection_result,
        runtime_snippet_injection_result
    """

    forwarded_payload, runtime_snippet_injection_result = (
        maybe_apply_relaymem_snippet_runtime_injection(
            payload=pipeline_context.forwarded_payload,
            relaymem_retrieval_artifact=relaymem_retrieval_artifact,
            ctx_block_apply_enabled=config.memory.ctx_block_apply_enabled,
            retrieval_dry_run_only=config.memory.retrieval_dry_run_only,
            snippet_apply_enabled=config.memory.snippet_apply_enabled,
            snippet_dry_run_only=config.memory.snippet_dry_run_only,
            snippet_runtime_injection_enabled=(
                config.memory.snippet_runtime_injection_enabled
            ),
            snippet_runtime_dry_run_only=config.memory.snippet_runtime_dry_run_only,
            token_budget_truncation_enabled=config.memory.token_budget_truncation_enabled,
            token_budget=config.memory.token_budget,
            chars_per_token=config.memory.chars_per_token,
        )
    )
    forwarded_payload = replace_pipeline_forwarded_payload(
        pipeline_context,
        forwarded_payload,
        "relaymem_snippet_runtime_injection",
    )

    if runtime_snippet_injection_result.get("applied") is True:
        runtime_ctx_injection_result = skipped_relaymem_runtime_ctx_injection_result(
            payload=compiled_payload,
            reason="skipped_because_snippet_runtime_injection_applied",
        )
    else:
        forwarded_payload, runtime_ctx_injection_result = (
            maybe_apply_relaymem_runtime_ctx_injection(
                payload=forwarded_payload,
                relaymem_retrieval_artifact=relaymem_retrieval_artifact,
                ctx_block_apply_enabled=config.memory.ctx_block_apply_enabled,
                retrieval_dry_run_only=config.memory.retrieval_dry_run_only,
                token_budget_truncation_enabled=(
                    config.memory.token_budget_truncation_enabled
                ),
                token_budget=config.memory.token_budget,
                chars_per_token=config.memory.chars_per_token,
            )
        )
        forwarded_payload = replace_pipeline_forwarded_payload(
            pipeline_context,
            forwarded_payload,
            "relaymem_runtime_ctx_injection",
        )

    return (
        forwarded_payload,
        runtime_ctx_injection_result,
        runtime_snippet_injection_result,
    )

def apply_token_budget_truncation_phase(
    *,
    config: RelayLMConfig,
    pipeline_context: PipelineContext,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Apply token budget truncation as one CTX Repack phase."""

    forwarded_payload, token_budget_truncation = _maybe_apply_token_budget_truncation(
        config=config,
        payload=pipeline_context.forwarded_payload,
    )
    forwarded_payload = replace_pipeline_forwarded_payload(
        pipeline_context,
        forwarded_payload,
        "token_budget_truncation",
    )
    return forwarded_payload, token_budget_truncation


def _maybe_apply_token_budget_truncation(
    *,
    config: RelayLMConfig,
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    forwarded_payload = dict(payload)
    forwarded_messages = _extract_repack_messages(payload)
    result = _build_token_budget_truncation_dry_run(
        config=config,
        forwarded_messages=forwarded_messages,
    )
    if result is None:
        return forwarded_payload, None

    if not config.memory.token_budget_truncation_enabled:
        return forwarded_payload, result

    blocked_reason = result.get("blocked_reason")
    over_after = result.get("over_budget_after") is True
    dropped_message_count = result.get("dropped_message_count")
    truncated_messages = result.get("truncated_messages")
    if (
        blocked_reason
        or over_after
        or not isinstance(truncated_messages, list)
        or not isinstance(dropped_message_count, int)
        or dropped_message_count <= 0
    ):
        result["applied"] = False
        result["apply_mode"] = "runtime_apply"
        return forwarded_payload, result

    original_messages = payload.get("messages")
    if not isinstance(original_messages, list):
        return forwarded_payload, result

    forwarded_payload["messages"] = [m for m in truncated_messages if isinstance(m, dict)]
    result["applied"] = True
    result["apply_mode"] = "runtime_apply"
    return forwarded_payload, result


def _build_token_budget_truncation_dry_run(
    *,
    config: RelayLMConfig,
    forwarded_messages: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if config.memory.token_budget is None:
        return None
    result = apply_token_budget_message_truncation(
        messages=forwarded_messages,
        token_budget=config.memory.token_budget,
        chars_per_token=config.memory.chars_per_token,
        keep_system=True,
        keep_latest_user=True,
    ).to_log_dict()
    result["enforcement_enabled"] = config.memory.token_budget_truncation_enabled
    result["applied"] = False
    result["apply_mode"] = "dry_run"
    return result


def _extract_repack_messages(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        return []
    return [message for message in raw_messages if isinstance(message, dict)]
