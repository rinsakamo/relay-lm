"""RelayCTX Repack helpers for backend-bound payload mutation."""

from __future__ import annotations

from typing import Any

from relaylm.config import RelayLMConfig
from relaylm.pipeline_context import PipelineContext, replace_pipeline_forwarded_payload
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
