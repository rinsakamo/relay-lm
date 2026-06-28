"""RelayCTX Repack helpers for backend-bound payload mutation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from relaylm.config import RelayLMConfig
from relaylm.diagnostics import build_relayctx_short_term_runtime_injection_apply_result
from relaylm.pipeline_context import PipelineContext, replace_pipeline_forwarded_payload
from relaylm.relaymem_grounded_recall_response import build_grounded_recall_context
from relaylm.relaymem_runtime_ctx import (
    maybe_apply_relaymem_runtime_ctx_injection,
    maybe_apply_relaymem_snippet_runtime_injection,
    skipped_relaymem_runtime_ctx_injection_result,
)
from relaylm.token_budget import estimate_text_tokens
from relaylm.token_budget_truncation import apply_token_budget_message_truncation


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

    grounded_payload, grounded_applied = _maybe_apply_grounded_recall_response(
        payload=forwarded_payload,
        relaymem_retrieval_artifact=relaymem_retrieval_artifact,
        pipeline_context=pipeline_context,
    )
    forwarded_payload = grounded_payload
    if grounded_applied:
        forwarded_payload = replace_pipeline_forwarded_payload(
            pipeline_context,
            forwarded_payload,
            "relaymem_grounded_recall_response",
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


def apply_relayctx_short_term_runtime_injection_phase(
    *,
    config: RelayLMConfig,
    pipeline_context: PipelineContext,
    preflight_artifact: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Apply RelayCTX short-term runtime injection as one CTX Repack phase."""

    forwarded_payload, apply_result = _maybe_apply_relayctx_short_term_runtime_injection(
        payload=pipeline_context.forwarded_payload,
        preflight_artifact=preflight_artifact,
        apply_enabled=config.relayctx_short_term_runtime_injection_apply_enabled,
        dry_run_only=config.relayctx_short_term_runtime_injection_dry_run_only,
        token_budget=config.relayctx_short_term_runtime_injection_token_budget,
        chars_per_token=config.memory.chars_per_token,
    )
    forwarded_payload = replace_pipeline_forwarded_payload(
        pipeline_context,
        forwarded_payload,
        "relayctx_short_term_runtime_injection",
    )
    return forwarded_payload, apply_result


def _maybe_apply_grounded_recall_response(
    *,
    payload: Mapping[str, Any],
    relaymem_retrieval_artifact: dict[str, Any],
    pipeline_context: PipelineContext,
) -> tuple[dict[str, Any], bool]:
    forwarded_payload = dict(payload)
    runtime = relaymem_retrieval_artifact.get("primary_recall_runtime")
    selected = runtime.get("selected_memories") if isinstance(runtime, Mapping) else None
    selected_memories = (
        list(selected)
        if isinstance(selected, Sequence) and not isinstance(selected, (str, bytes, bytearray))
        else []
    )
    if not selected_memories:
        result = build_grounded_recall_context(
            retrieved_memories=[],
            query_text=_latest_user_text(payload),
            character_id=pipeline_context.route.character_id,
            namespace=pipeline_context.route.memory_namespace,
        )
        projection = result.to_log_dict()
        projection["applied"] = False
        projection["blocked_reason_ids"] = [
            *projection.get("blocked_reason_ids", []),
            "no_selected_primary_recall_memory",
        ]
        relaymem_retrieval_artifact["grounded_recall_projection"] = projection
        return forwarded_payload, False

    result = build_grounded_recall_context(
        retrieved_memories=selected_memories,
        query_text=_latest_user_text(payload),
        character_id=pipeline_context.route.character_id,
        namespace=pipeline_context.route.memory_namespace,
    )
    projection = result.to_log_dict()
    relaymem_retrieval_artifact["grounded_recall_projection"] = projection
    context = result.grounded_recall_context
    backend_messages = (
        context.get("backend_messages") if isinstance(context, Mapping) else None
    )
    if not isinstance(backend_messages, Sequence) or isinstance(backend_messages, (str, bytes, bytearray)):
        projection["applied"] = False
        projection["blocked_reason_ids"] = [
            *projection.get("blocked_reason_ids", []),
            "backend_messages_missing",
        ]
        return forwarded_payload, False
    inserted = _insert_backend_messages_before_latest_user(forwarded_payload, backend_messages)
    if inserted is None:
        projection["applied"] = False
        projection["blocked_reason_ids"] = [
            *projection.get("blocked_reason_ids", []),
            "latest_user_message_not_found",
        ]
        return forwarded_payload, False
    projection["applied"] = True
    return inserted, True


def _insert_backend_messages_before_latest_user(
    payload: Mapping[str, Any],
    backend_messages: Sequence[Any],
) -> dict[str, Any] | None:
    original_messages = payload.get("messages")
    if not isinstance(original_messages, list):
        return None
    insertion_index = _relayctx_before_latest_user_index(original_messages)
    if insertion_index is None:
        return None
    forwarded_messages = [
        deepcopy(message) for message in original_messages if isinstance(message, Mapping)
    ]
    if len(forwarded_messages) != len(original_messages):
        return None
    sanitized: list[dict[str, str]] = []
    for raw in backend_messages:
        if not isinstance(raw, Mapping):
            continue
        role = raw.get("role")
        content = raw.get("content")
        if role not in {"system", "developer"} or not isinstance(content, str) or not content:
            continue
        sanitized.append({"role": role, "content": content})
    if not sanitized:
        return None
    for offset, message in enumerate(sanitized):
        forwarded_messages.insert(insertion_index + offset, message)
    forwarded_payload = deepcopy(dict(payload))
    forwarded_payload["messages"] = forwarded_messages
    return forwarded_payload


def _latest_user_text(payload: Mapping[str, Any]) -> str:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, Mapping) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if not isinstance(part, Mapping):
                    continue
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
            return "\n".join(parts)
    return ""


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

    forwarded_payload["messages"] = [
        m for m in truncated_messages if isinstance(m, dict)
    ]
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


def _maybe_apply_relayctx_short_term_runtime_injection(
    *,
    payload: Mapping[str, Any],
    preflight_artifact: Mapping[str, Any] | None,
    apply_enabled: bool,
    dry_run_only: bool,
    token_budget: int,
    chars_per_token: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    forwarded_payload = deepcopy(dict(payload))
    original_messages = payload.get("messages")
    original_message_count = (
        len(original_messages) if isinstance(original_messages, list) else 0
    )

    if not apply_enabled:
        return forwarded_payload, None

    preflight_present = isinstance(preflight_artifact, Mapping)
    blocked_reasons: list[str] = []
    if dry_run_only:
        blocked_reasons.append("dry_run_only")
    if not preflight_present:
        blocked_reasons.append("preflight_missing")
    if preflight_present and preflight_artifact.get("injection_plan_present") is not True:
        blocked_reasons.append("injection_plan_missing")
    if preflight_present and preflight_artifact.get("input_assembled_block_present") is not True:
        blocked_reasons.append("assembled_block_missing")
    input_short_term_candidate_count = _non_negative_int(
        preflight_artifact.get("input_short_term_candidate_count")
        if preflight_present
        else None
    )
    if preflight_present and input_short_term_candidate_count <= 0:
        blocked_reasons.append("no_short_term_candidates")
    if preflight_present and preflight_artifact.get("content_free") is not True:
        blocked_reasons.append("preflight_not_content_free")
    if not isinstance(original_messages, list):
        blocked_reasons.append("messages_not_list")

    insertion_index = None
    if isinstance(original_messages, list):
        insertion_index = _relayctx_before_latest_user_index(original_messages)
        if insertion_index is None:
            blocked_reasons.append("latest_user_message_not_found")

    inserted_content = (
        _relayctx_short_term_inserted_content(preflight_artifact)
        if preflight_present
        else ""
    )
    if not inserted_content:
        blocked_reasons.append("inserted_content_empty")

    estimated_tokens = _estimate_text_tokens(inserted_content, chars_per_token)
    if token_budget <= 0 or estimated_tokens > token_budget:
        blocked_reasons.append("token_budget_exceeded")

    if blocked_reasons:
        if dry_run_only or not apply_enabled:
            blocked_reasons.append("payload_mutation_disabled")
        result = build_relayctx_short_term_runtime_injection_apply_result(
            preflight_artifact=dict(preflight_artifact) if preflight_present else None,
            enabled=True,
            dry_run_only=dry_run_only,
            attempted=not dry_run_only,
            applied=False,
            original_message_count=original_message_count,
            forwarded_message_count=original_message_count,
            inserted_chars=0,
            estimated_inserted_tokens=0,
            blocked_reasons=blocked_reasons,
        )
        return forwarded_payload, result

    assert isinstance(original_messages, list)
    assert insertion_index is not None
    forwarded_messages = [
        deepcopy(message) for message in original_messages if isinstance(message, Mapping)
    ]
    if len(forwarded_messages) != original_message_count:
        result = build_relayctx_short_term_runtime_injection_apply_result(
            preflight_artifact=dict(preflight_artifact) if preflight_present else None,
            enabled=True,
            dry_run_only=dry_run_only,
            attempted=True,
            applied=False,
            original_message_count=original_message_count,
            forwarded_message_count=len(forwarded_messages),
            inserted_chars=0,
            estimated_inserted_tokens=0,
            blocked_reasons=["messages_contain_non_object_items"],
        )
        return forwarded_payload, result

    forwarded_messages.insert(
        insertion_index,
        {"role": "system", "content": inserted_content},
    )
    forwarded_payload["messages"] = forwarded_messages
    result = build_relayctx_short_term_runtime_injection_apply_result(
        preflight_artifact=dict(preflight_artifact) if preflight_present else None,
        enabled=True,
        dry_run_only=dry_run_only,
        attempted=True,
        applied=True,
        original_message_count=original_message_count,
        forwarded_message_count=len(forwarded_messages),
        inserted_chars=len(inserted_content),
        estimated_inserted_tokens=estimated_tokens,
        blocked_reasons=[],
    )
    return forwarded_payload, result


def _relayctx_before_latest_user_index(messages: list[Any]) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if isinstance(message, Mapping) and message.get("role") == "user":
            return index
    return None


def _relayctx_short_term_inserted_content(
    preflight_artifact: Mapping[str, Any],
) -> str:
    return "\n".join(
        [
            "[RelayCTX Short-Term Context]",
            (
                "The current thread contains short-term context candidates. Treat current "
                "user instructions and current-thread temporary context as higher priority "
                "than stable memory. Do not treat these hints as long-term memory."
            ),
            "",
            "Candidate summary:",
            f"- temporary facts: {_non_negative_int(preflight_artifact.get('temporary_fact_count'))}",
            f"- temporary preferences: {_non_negative_int(preflight_artifact.get('temporary_preference_count'))}",
            f"- instructions: {_non_negative_int(preflight_artifact.get('instruction_count'))}",
            f"- overrides: {_non_negative_int(preflight_artifact.get('override_count'))}",
            f"- contradictions: {_non_negative_int(preflight_artifact.get('contradiction_count'))}",
            "",
            "Rules:",
            "- Prefer current user instruction and current-thread temporary context over memory_seed when they conflict.",
            "- Do not persist these hints as long-term memory.",
            "- Do not mention this block unless asked about context handling.",
        ]
    )


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _estimate_text_tokens(text: str, chars_per_token: int) -> int:
    return estimate_text_tokens(
        text,
        chars_per_token=max(1, int(chars_per_token)),
    ).estimated_tokens
