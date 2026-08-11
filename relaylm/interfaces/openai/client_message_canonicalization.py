"""Content-free dry-run helpers for the client-message authority boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.compiler import extract_instruction_text
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result


_SCHEMA_VERSION = "client_message_canonicalization_dry_run.v0"
_INSTRUCTION_ROLES = frozenset({"system", "developer"})
_TEXT_PART_TYPES = frozenset({"text", "input_text"})


def build_client_message_canonicalization_dry_run(
    payload: Mapping[str, Any],
    *,
    enabled: bool,
    managed_route: bool,
) -> dict[str, Any] | None:
    """Inspect current-request evidence without mutating or copying message content.

    The artifact is intentionally content-free. It records counts, content-shape
    classes, and readiness/block reasons only. It does not return the current
    user message, instruction text, history text, tool arguments, or attachments.
    """

    if not enabled:
        return None

    raw_messages = payload.get("messages")
    blocked_reasons: list[str] = []
    if not managed_route:
        blocked_reasons.append("pass_through_route_exempt")
    if not isinstance(raw_messages, list):
        blocked_reasons.append("messages_not_list")
        raw_messages = []

    valid_messages: list[tuple[int, Mapping[str, Any]]] = []
    invalid_message_count = 0
    for index, message in enumerate(raw_messages):
        if isinstance(message, Mapping):
            valid_messages.append((index, message))
        else:
            invalid_message_count += 1
    if invalid_message_count:
        blocked_reasons.append("messages_contain_non_object_items")

    role_counts = _role_counts(valid_messages)
    latest_user_index, latest_user_message = _latest_user_message(valid_messages)
    user_shape = _classify_user_content(
        latest_user_message.get("content") if latest_user_message is not None else None
    )

    if latest_user_message is None:
        blocked_reasons.append("current_user_turn_missing")
    elif not user_shape["valid"]:
        blocked_reasons.append("current_user_content_invalid")

    instruction_messages = [
        message
        for _, message in valid_messages
        if message.get("role") in _INSTRUCTION_ROLES
    ]
    instruction_text_message_count = sum(
        1
        for message in instruction_messages
        if extract_instruction_text(message.get("content")) is not None
    )
    instruction_without_text_count = (
        len(instruction_messages) - instruction_text_message_count
    )

    messages_before_current_user_count = (
        latest_user_index if latest_user_index is not None else 0
    )
    messages_after_current_user_count = (
        len(raw_messages) - latest_user_index - 1
        if latest_user_index is not None
        else 0
    )
    post_user_messages = [
        message
        for index, message in valid_messages
        if latest_user_index is not None and index > latest_user_index
    ]
    assistant_tool_call_message_count = sum(
        1
        for message in post_user_messages
        if message.get("role") == "assistant"
        and isinstance(message.get("tool_calls"), list)
        and bool(message.get("tool_calls"))
    )
    post_user_tool_message_count = sum(
        1 for message in post_user_messages if message.get("role") == "tool"
    )
    active_tool_transaction_candidate = (
        assistant_tool_call_message_count > 0 or post_user_tool_message_count > 0
    )
    if active_tool_transaction_candidate:
        blocked_reasons.append("active_tool_transaction_requires_preservation")

    canonicalization_candidate_ready = managed_route and not blocked_reasons
    return {
        "schema_version": _SCHEMA_VERSION,
        "enabled": True,
        "diagnostics_only": True,
        "content_free": True,
        "managed_route": bool(managed_route),
        "route_policy": "relay_managed" if managed_route else "pass_through",
        "messages_present": isinstance(payload.get("messages"), list),
        "message_count": len(raw_messages),
        "valid_message_count": len(valid_messages),
        "invalid_message_count": invalid_message_count,
        "system_message_count": role_counts.get("system", 0),
        "developer_message_count": role_counts.get("developer", 0),
        "instruction_message_count": len(instruction_messages),
        "instruction_text_message_count": instruction_text_message_count,
        "instruction_without_text_count": instruction_without_text_count,
        "current_user_turn_present": latest_user_message is not None,
        "current_user_content_valid": bool(user_shape["valid"]),
        "current_user_content_kind": user_shape["kind"],
        "current_user_text_part_count": user_shape["text_part_count"],
        "current_user_non_text_part_count": user_shape["non_text_part_count"],
        "current_user_invalid_part_count": user_shape["invalid_part_count"],
        "current_user_multimodal": user_shape["non_text_part_count"] > 0,
        "messages_before_current_user_count": messages_before_current_user_count,
        "messages_after_current_user_count": messages_after_current_user_count,
        "prior_user_message_count": _count_role_before(
            valid_messages, latest_user_index, "user"
        ),
        "prior_assistant_message_count": _count_role_before(
            valid_messages, latest_user_index, "assistant"
        ),
        "tool_message_count": role_counts.get("tool", 0),
        "assistant_tool_call_message_count": assistant_tool_call_message_count,
        "post_user_tool_message_count": post_user_tool_message_count,
        "active_tool_transaction_candidate": active_tool_transaction_candidate,
        "canonicalization_candidate_ready": canonicalization_candidate_ready,
        "blocked_reasons": blocked_reasons,
    }


def build_client_message_canonicalization_node_result(
    artifact: Mapping[str, Any] | None,
) -> PipelineNodeResult | None:
    """Build one content-free pipeline result from the dry-run artifact."""

    if not isinstance(artifact, Mapping):
        return None

    managed_route = artifact.get("managed_route") is True
    ready = artifact.get("canonicalization_candidate_ready") is True
    if not managed_route:
        status = "skipped"
        decision = "pass_through_route_exempt"
    elif ready:
        status = "diagnostic_only"
        decision = "current_request_evidence_identified"
    else:
        status = "diagnostic_only"
        decision = "canonicalization_candidate_blocked"

    blocked_reasons = _strings(artifact.get("blocked_reasons"))
    diagnostics = {
        key: value
        for key, value in artifact.items()
        if key != "blocked_reasons"
    }
    return build_pipeline_node_result(
        node_name="client_message_canonicalization",
        status=status,
        decision=decision,
        blocked_reasons=blocked_reasons,
        diagnostics=diagnostics,
        artifacts=[
            {
                "artifact_name": "client_message_canonicalization_dry_run",
                "schema_version": _SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": True,
                "content_free": True,
                "applied": False,
            }
        ],
    )


def _role_counts(
    messages: Sequence[tuple[int, Mapping[str, Any]]],
) -> dict[str, int]:
    result: dict[str, int] = {}
    for _, message in messages:
        role = message.get("role")
        if isinstance(role, str):
            result[role] = result.get(role, 0) + 1
    return result


def _latest_user_message(
    messages: Sequence[tuple[int, Mapping[str, Any]]],
) -> tuple[int | None, Mapping[str, Any] | None]:
    for index, message in reversed(messages):
        if message.get("role") == "user":
            return index, message
    return None, None


def _classify_user_content(content: Any) -> dict[str, Any]:
    if isinstance(content, str):
        return {
            "valid": bool(content.strip()),
            "kind": "text" if content.strip() else "empty_text",
            "text_part_count": 1 if content.strip() else 0,
            "non_text_part_count": 0,
            "invalid_part_count": 0,
        }

    if not isinstance(content, list):
        return {
            "valid": False,
            "kind": "missing" if content is None else "unsupported",
            "text_part_count": 0,
            "non_text_part_count": 0,
            "invalid_part_count": 0,
        }

    text_part_count = 0
    non_text_part_count = 0
    invalid_part_count = 0
    for part in content:
        if isinstance(part, str):
            if part:
                text_part_count += 1
            else:
                invalid_part_count += 1
            continue
        if not isinstance(part, Mapping):
            invalid_part_count += 1
            continue
        part_type = part.get("type")
        if part_type in _TEXT_PART_TYPES:
            part_text = part.get("text")
            if isinstance(part_text, str) and part_text.strip():
                text_part_count += 1
            else:
                invalid_part_count += 1
        elif isinstance(part_type, str) and part_type:
            non_text_part_count += 1
        else:
            invalid_part_count += 1

    valid_part_count = text_part_count + non_text_part_count
    valid = bool(content) and valid_part_count > 0 and invalid_part_count == 0
    kind = (
        "multimodal_parts"
        if valid and non_text_part_count > 0
        else "text_parts"
        if valid
        else "invalid_parts"
    )
    return {
        "valid": valid,
        "kind": kind,
        "text_part_count": text_part_count,
        "non_text_part_count": non_text_part_count,
        "invalid_part_count": invalid_part_count,
    }


def _count_role_before(
    messages: Sequence[tuple[int, Mapping[str, Any]]],
    boundary_index: int | None,
    role: str,
) -> int:
    if boundary_index is None:
        return 0
    return sum(
        1
        for index, message in messages
        if index < boundary_index and message.get("role") == role
    )


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [item for item in value if isinstance(item, str) and item]
