"""Gated RelayMEM runtime context injection helpers."""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping, Sequence
from typing import Any


def maybe_apply_relaymem_runtime_ctx_injection(
    *,
    payload: Mapping[str, Any],
    relaymem_retrieval_artifact: Mapping[str, Any] | None,
    ctx_block_apply_enabled: bool,
    retrieval_dry_run_only: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a copied payload and diagnostics for gated RelayMEM CTX injection.

    The default path is blocked. A system context message is inserted only when
    explicit runtime config gates are enabled and the retrieval artifact says the
    dry-run plan is eligible. This helper never mutates the input payload.
    """

    forwarded_payload = deepcopy(dict(payload))
    original_messages = payload.get("messages")
    original_message_count = len(original_messages) if isinstance(original_messages, list) else 0
    result = _base_result(original_message_count=original_message_count)

    blocked_reasons = _apply_blocked_reasons(
        relaymem_retrieval_artifact=relaymem_retrieval_artifact,
        ctx_block_apply_enabled=ctx_block_apply_enabled,
        retrieval_dry_run_only=retrieval_dry_run_only,
    )
    if blocked_reasons:
        result["blocked_reasons"] = blocked_reasons
        result["forwarded_message_count"] = original_message_count
        return forwarded_payload, result

    assert isinstance(relaymem_retrieval_artifact, Mapping)
    plan = relaymem_retrieval_artifact.get("ctx_injection_plan")
    assert isinstance(plan, Mapping)
    if not isinstance(original_messages, list):
        result["attempted"] = True
        result["blocked_reasons"] = ["messages_not_list"]
        result["forwarded_message_count"] = original_message_count
        return forwarded_payload, result

    insertion_index = _before_latest_user_index(original_messages)
    if insertion_index is None:
        result["attempted"] = True
        result["blocked_reasons"] = ["latest_user_message_not_found"]
        result["forwarded_message_count"] = original_message_count
        return forwarded_payload, result

    inserted_content = _runtime_context_message_content(plan)
    if not inserted_content:
        result["attempted"] = True
        result["blocked_reasons"] = ["ctx_injection_plan_preview_empty"]
        result["forwarded_message_count"] = original_message_count
        return forwarded_payload, result

    forwarded_messages = [
        deepcopy(message) for message in original_messages if isinstance(message, Mapping)
    ]
    if len(forwarded_messages) != original_message_count:
        result["attempted"] = True
        result["blocked_reasons"] = ["messages_contain_non_object_items"]
        result["forwarded_message_count"] = len(forwarded_messages)
        return forwarded_payload, result

    forwarded_messages.insert(
        insertion_index,
        {"role": "system", "content": inserted_content},
    )
    forwarded_payload["messages"] = forwarded_messages
    result.update(
        {
            "attempted": True,
            "applied": True,
            "inserted_chars": len(inserted_content),
            "estimated_tokens": _estimate_tokens(inserted_content),
            "blocked_reasons": [],
            "payload_mutation_applied": True,
            "forwarded_message_count": len(forwarded_messages),
        }
    )
    return forwarded_payload, result


def _base_result(*, original_message_count: int) -> dict[str, Any]:
    return {
        "schema_version": "relaymem.runtime_ctx_injection_result.v0",
        "attempted": False,
        "applied": False,
        "insertion_point": "before_latest_user",
        "inserted_message_role": "system",
        "inserted_chars": 0,
        "estimated_tokens": 0,
        "blocked_reasons": [],
        "payload_mutation_applied": False,
        "original_message_count": original_message_count,
        "forwarded_message_count": original_message_count,
    }


def _apply_blocked_reasons(
    *,
    relaymem_retrieval_artifact: Mapping[str, Any] | None,
    ctx_block_apply_enabled: bool,
    retrieval_dry_run_only: bool,
) -> list[str]:
    reasons: list[str] = []
    if not ctx_block_apply_enabled:
        reasons.append("ctx_block_apply_disabled")
    if retrieval_dry_run_only:
        reasons.append("retrieval_dry_run_only")
    if not isinstance(relaymem_retrieval_artifact, Mapping):
        reasons.append("relaymem_retrieval_artifact_missing")
        return reasons

    if relaymem_retrieval_artifact.get("apply_decision") != "eligible_but_not_applied":
        reasons.append(f"apply_decision:{relaymem_retrieval_artifact.get('apply_decision')}")
    if relaymem_retrieval_artifact.get("ctx_block") is not None:
        reasons.append("ctx_block_already_present")

    plan = relaymem_retrieval_artifact.get("ctx_injection_plan")
    if not isinstance(plan, Mapping):
        reasons.append("ctx_injection_plan_missing")
        return reasons
    preview_text = plan.get("preview_text")
    if not isinstance(preview_text, str) or not preview_text.strip():
        reasons.append("ctx_injection_plan_preview_empty")
    if plan.get("applied") is True:
        reasons.append("ctx_injection_plan_already_applied")
    if _plan_has_blocking_safety_reason(plan):
        reasons.append("ctx_injection_plan_blocked")
    return _dedupe(reasons)


def _plan_has_blocking_safety_reason(plan: Mapping[str, Any]) -> bool:
    raw_reasons = plan.get("blocked_reasons")
    if not isinstance(raw_reasons, Sequence) or isinstance(raw_reasons, str):
        return False
    allowed = {
        "runtime_apply_not_implemented",
        "runtime_ctx_injection_not_implemented",
        "backend_payload_mutation_disabled",
        "dry_run_only",
        "retrieval_dry_run_only",
        "ctx_block_apply_disabled",
    }
    return any(str(reason) not in allowed for reason in raw_reasons)


def _runtime_context_message_content(plan: Mapping[str, Any]) -> str:
    source_entries = plan.get("source_entries")
    if not isinstance(source_entries, Sequence) or isinstance(source_entries, str):
        return ""
    lines = [
        "[RelayMEM Context]",
        "The following memory hints may help answer the user. Treat them as contextual hints, not facts unless supported by the conversation.",
    ]
    for entry in source_entries:
        if not isinstance(entry, Mapping):
            continue
        path = _sanitize_mem_prompt_metadata(entry.get("path"))
        reason = _sanitize_mem_prompt_metadata(entry.get("reason"), max_chars=80)
        if path:
            lines.append(f"- {path} (reason: {reason})")
    return "\n".join(lines) if len(lines) > 2 else ""


def _sanitize_mem_prompt_metadata(value: object, *, max_chars: int = 160) -> str:
    """Normalize RelayMEM metadata before embedding it in runtime prompts."""

    text = "" if value is None else str(value)
    normalized_chars: list[str] = []
    replacements = {
        "`": "'",
        '"': "'",
        "[": "(",
        "]": ")",
        "{": "(",
        "}": ")",
        "<": "(",
        ">": ")",
        ":": " -",
    }
    for char in text:
        codepoint = ord(char)
        if char in {"\r", "\n", "\t"} or codepoint < 32 or codepoint == 127:
            normalized_chars.append(" ")
            continue
        normalized_chars.append(replacements.get(char, char))
    normalized = " ".join("".join(normalized_chars).split())
    max_chars = max(1, int(max_chars))
    if len(normalized) > max_chars:
        return normalized[: max_chars - 3].rstrip() + "..." if max_chars > 3 else normalized[:max_chars]
    return normalized


def _before_latest_user_index(messages: Sequence[Any]) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if isinstance(message, Mapping) and message.get("role") == "user":
            return index
    return None


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _dedupe(reasons: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    return deduped
