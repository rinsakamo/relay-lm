"""Content-free dry-run helpers for instruction extraction candidates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result


_SCHEMA_VERSION = "client_instruction_extraction_dry_run.v0"
_INSTRUCTION_ROLES = frozenset({"system", "developer"})
_TEXT_PART_TYPES = frozenset({"text", "input_text"})
_FORBIDDEN_CONTENT_KEYS = frozenset(
    {
        "content",
        "text",
        "raw_content",
        "raw_message",
        "prompt",
        "messages",
        "history",
        "body",
    }
)


def build_client_instruction_extraction_dry_run(
    payload: Mapping[str, Any] | None,
    *,
    enabled: bool,
) -> dict[str, Any] | None:
    """Classify instruction candidates without mutating or copying content.

    Only ``system`` and ``developer`` messages are instruction candidates. User,
    assistant, and tool message bodies are never fingerprint targets and are not
    copied into this content-free artifact.
    """

    if not enabled:
        return None

    blocked_reasons: list[str] = []
    artifact: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "enabled": True,
        "diagnostics_only": True,
        "content_free": True,
        "messages_present": False,
        "message_count": 0,
        "valid_message_count": 0,
        "invalid_message_count": 0,
        "instruction_candidate_count": 0,
        "candidate_roles": [],
        "candidate_indices": [],
        "content_shape_counts": {},
        "invalid_instruction_candidate_count": 0,
        "unknown_instruction_candidate_shape_count": 0,
        "multimodal_instruction_candidate_count": 0,
        "has_multimodal_instruction_candidate": False,
        "active_tool_transaction_candidate": False,
        "assistant_tool_call_message_count_after_latest_user": 0,
        "tool_message_count_after_latest_user": 0,
        "fingerprint_candidate_ready": False,
        "blocked_reasons": [],
    }

    if not isinstance(payload, Mapping):
        artifact["blocked_reasons"] = ["payload_not_object"]
        return artifact

    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        artifact["blocked_reasons"] = ["messages_not_list"]
        return artifact

    artifact["messages_present"] = True
    artifact["message_count"] = len(raw_messages)

    valid_messages: list[tuple[int, Mapping[str, Any]]] = []
    invalid_message_count = 0
    for index, message in enumerate(raw_messages):
        if isinstance(message, Mapping):
            valid_messages.append((index, message))
        else:
            invalid_message_count += 1
    if invalid_message_count:
        blocked_reasons.append("messages_contain_non_object_items")

    candidate_roles: list[str] = []
    candidate_indices: list[int] = []
    content_shape_counts: dict[str, int] = {}
    invalid_instruction_candidate_count = 0
    unknown_instruction_candidate_shape_count = 0
    multimodal_instruction_candidate_count = 0

    for index, message in valid_messages:
        role = message.get("role")
        if role not in _INSTRUCTION_ROLES:
            continue
        candidate_roles.append(str(role))
        candidate_indices.append(index)
        shape = _classify_instruction_candidate_content(message.get("content"))
        content_shape_counts[shape["kind"]] = content_shape_counts.get(shape["kind"], 0) + 1
        if not shape["valid"]:
            invalid_instruction_candidate_count += 1
        if shape["kind"] == "unknown":
            unknown_instruction_candidate_shape_count += 1
        if shape["multimodal"]:
            multimodal_instruction_candidate_count += 1

    latest_user_index = _latest_user_message_index(valid_messages)
    tool_state = _active_tool_transaction_state(valid_messages, latest_user_index)
    if tool_state["active"]:
        blocked_reasons.append("active_tool_transaction_requires_preservation")
    if invalid_instruction_candidate_count:
        blocked_reasons.append("instruction_candidate_content_invalid")
    if unknown_instruction_candidate_shape_count:
        blocked_reasons.append("instruction_candidate_content_unknown")
    if multimodal_instruction_candidate_count:
        blocked_reasons.append("multimodal_instruction_candidate_requires_preservation")

    blocked_reasons = _unique_in_order(blocked_reasons)
    artifact.update(
        {
            "valid_message_count": len(valid_messages),
            "invalid_message_count": invalid_message_count,
            "instruction_candidate_count": len(candidate_indices),
            "candidate_roles": _unique_in_order(candidate_roles),
            "candidate_indices": candidate_indices,
            "content_shape_counts": content_shape_counts,
            "invalid_instruction_candidate_count": invalid_instruction_candidate_count,
            "unknown_instruction_candidate_shape_count": unknown_instruction_candidate_shape_count,
            "multimodal_instruction_candidate_count": multimodal_instruction_candidate_count,
            "has_multimodal_instruction_candidate": multimodal_instruction_candidate_count > 0,
            "active_tool_transaction_candidate": tool_state["active"],
            "assistant_tool_call_message_count_after_latest_user": tool_state[
                "assistant_tool_call_message_count"
            ],
            "tool_message_count_after_latest_user": tool_state["tool_message_count"],
            "blocked_reasons": blocked_reasons,
            "fingerprint_candidate_ready": not blocked_reasons,
        }
    )
    return artifact


def build_client_instruction_extraction_node_result(
    artifact: Mapping[str, Any] | None,
) -> PipelineNodeResult | None:
    """Build a content-free pipeline node result for future runtime wiring."""

    if not isinstance(artifact, Mapping):
        return None

    ready = artifact.get("fingerprint_candidate_ready") is True
    blocked_reasons = _strings(artifact.get("blocked_reasons"))
    decision = (
        "instruction_fingerprint_candidate_ready"
        if ready
        else "instruction_fingerprint_candidate_blocked"
    )
    diagnostics = {key: value for key, value in artifact.items() if key != "blocked_reasons"}
    return build_pipeline_node_result(
        node_name="client_instruction_extraction",
        status="diagnostic_only",
        decision=decision,
        blocked_reasons=blocked_reasons,
        diagnostics=diagnostics,
        artifacts=[
            {
                "artifact_name": "client_instruction_extraction_dry_run",
                "schema_version": _SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": True,
                "content_free": True,
                "applied": False,
            }
        ],
    )


def assert_client_instruction_extraction_content_free(value: Any) -> None:
    """Fail if a dry-run artifact or node result exposes content-bearing keys."""

    if isinstance(value, PipelineNodeResult):
        assert_client_instruction_extraction_content_free(value.to_log_dict())
        return

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _FORBIDDEN_CONTENT_KEYS:
                raise ValueError(f"content-bearing key is not allowed: {key}")
            assert_client_instruction_extraction_content_free(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            assert_client_instruction_extraction_content_free(nested)


def _classify_instruction_candidate_content(content: Any) -> dict[str, Any]:
    if isinstance(content, str):
        return {
            "valid": bool(content.strip()),
            "kind": "string" if content.strip() else "empty_string",
            "multimodal": False,
        }

    if not isinstance(content, list):
        return {
            "valid": False,
            "kind": "missing" if content is None else "unknown",
            "multimodal": False,
        }

    if not content:
        return {"valid": False, "kind": "empty_parts", "multimodal": False}

    text_part_count = 0
    non_text_part_count = 0
    invalid_part_count = 0
    unknown_part_count = 0
    for part in content:
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
            unknown_part_count += 1
            invalid_part_count += 1

    if unknown_part_count:
        kind = "unknown"
    elif non_text_part_count:
        kind = "multimodal_parts"
    else:
        kind = "text_parts"
    return {
        "valid": text_part_count > 0 and non_text_part_count == 0 and invalid_part_count == 0,
        "kind": kind,
        "multimodal": non_text_part_count > 0,
    }


def _latest_user_message_index(
    messages: Sequence[tuple[int, Mapping[str, Any]]],
) -> int | None:
    for index, message in reversed(messages):
        if message.get("role") == "user":
            return index
    return None


def _active_tool_transaction_state(
    messages: Sequence[tuple[int, Mapping[str, Any]]],
    latest_user_index: int | None,
) -> dict[str, Any]:
    post_user_messages = [
        message
        for index, message in messages
        if latest_user_index is not None and index > latest_user_index
    ]
    assistant_tool_call_message_count = sum(
        1
        for message in post_user_messages
        if message.get("role") == "assistant"
        and isinstance(message.get("tool_calls"), list)
        and bool(message.get("tool_calls"))
    )
    tool_message_count = sum(
        1 for message in post_user_messages if message.get("role") == "tool"
    )
    return {
        "active": assistant_tool_call_message_count > 0 or tool_message_count > 0,
        "assistant_tool_call_message_count": assistant_tool_call_message_count,
        "tool_message_count": tool_message_count,
    }


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _unique_in_order(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
