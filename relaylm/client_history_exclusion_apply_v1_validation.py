"""Typed source validation for instruction-bearing history exclusion apply."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from relaylm.client_history_exclusion_preflight import (
    ClientHistoryExclusionPreflightResult,
)
from relaylm.client_instruction_identity import (
    ClientInstructionIdentityResult,
    NormalizedInstructionCandidate,
)
from relaylm.compiler import ContextBlock


_PREFLIGHT_SCHEMA_VERSION = "client_history_exclusion_preflight.v0"
_IDENTITY_SCHEMA_VERSION = "client_instruction_identity.v0"
_INSTRUCTION_ROLES = frozenset({"system", "developer"})
_OPTIONAL_CACHE_BLOCK_REASONS = frozenset(
    {
        "instruction_cache_lookup_result_missing",
        "instruction_cache_lookup_blocked",
    }
)


@dataclass(frozen=True, repr=False)
class ValidatedClientHistoryExclusionApplyV1Inputs:
    original_payload: Mapping[str, Any]
    original_messages: tuple[Mapping[str, Any], ...]
    compiled_payload: Mapping[str, Any]
    compiled_messages: tuple[Mapping[str, Any], ...]
    compiled_context_blocks: tuple[ContextBlock, ...]
    preflight_result: ClientHistoryExclusionPreflightResult
    identity_result: ClientInstructionIdentityResult
    candidates: tuple[NormalizedInstructionCandidate, ...]
    current_user_message: Mapping[str, Any]


def validate_client_history_exclusion_apply_v1_inputs(
    original_payload: Mapping[str, Any] | None,
    compiled_payload: Mapping[str, Any] | None,
    compiled_context_blocks: Sequence[ContextBlock] | None,
    preflight_result: ClientHistoryExclusionPreflightResult | None,
    identity_result: ClientInstructionIdentityResult | None,
) -> tuple[ValidatedClientHistoryExclusionApplyV1Inputs | None, tuple[str, ...]]:
    """Validate all request-local typed prerequisites without mutating them."""

    reasons: list[str] = []

    original = original_payload if isinstance(original_payload, Mapping) else None
    original_messages_raw = original.get("messages") if original is not None else None
    if original is None:
        reasons.append("original_payload_missing")
    if not isinstance(original_messages_raw, list):
        reasons.append("original_messages_not_list")
        original_messages: tuple[Mapping[str, Any], ...] = ()
    elif any(not isinstance(message, Mapping) for message in original_messages_raw):
        reasons.append("original_messages_contain_non_object_items")
        original_messages = ()
    else:
        original_messages = tuple(original_messages_raw)

    compiled = compiled_payload if isinstance(compiled_payload, Mapping) else None
    compiled_messages_raw = compiled.get("messages") if compiled is not None else None
    if compiled is None:
        reasons.append("compiled_payload_missing")
    if not isinstance(compiled_messages_raw, list):
        reasons.append("compiled_messages_not_list")
        compiled_messages: tuple[Mapping[str, Any], ...] = ()
    elif any(not isinstance(message, Mapping) for message in compiled_messages_raw):
        reasons.append("compiled_messages_contain_non_object_items")
        compiled_messages = ()
    else:
        compiled_messages = tuple(compiled_messages_raw)

    if compiled_context_blocks is None:
        reasons.append("typed_compiler_blocks_missing")
        blocks: tuple[ContextBlock, ...] = ()
    elif not isinstance(compiled_context_blocks, Sequence) or isinstance(
        compiled_context_blocks,
        (str, bytes, bytearray),
    ):
        reasons.append("typed_compiler_blocks_invalid")
        blocks = ()
    elif any(not isinstance(block, ContextBlock) for block in compiled_context_blocks):
        reasons.append("typed_compiler_blocks_invalid")
        blocks = ()
    else:
        blocks = tuple(compiled_context_blocks)

    typed_preflight = (
        preflight_result
        if isinstance(preflight_result, ClientHistoryExclusionPreflightResult)
        else None
    )
    if preflight_result is None:
        reasons.append("preflight_missing")
    elif typed_preflight is None:
        reasons.append("preflight_type_invalid")
    else:
        reasons.extend(_validate_preflight(typed_preflight))

    typed_identity = (
        identity_result
        if isinstance(identity_result, ClientInstructionIdentityResult)
        else None
    )
    if identity_result is None:
        reasons.append("identity_missing")
    elif typed_identity is None:
        reasons.append("identity_type_invalid")
    else:
        reasons.extend(_validate_identity_result(typed_identity))

    current_user_index, current_user_message = _latest_user_message(original_messages)
    if current_user_message is None:
        reasons.append("current_user_turn_missing")
    elif not _current_user_content_valid(current_user_message.get("content")):
        reasons.append("current_user_content_invalid")
    if _payload_has_active_tool_transaction_after_current_user(
        original_messages,
        current_user_index=current_user_index,
    ):
        reasons.append("active_tool_transaction_requires_preservation")

    identity = typed_identity.identity if typed_identity is not None else None
    candidates = identity.candidates if identity is not None else ()
    if candidates:
        reasons.extend(_validate_candidate_sources(original_messages, candidates))

    if typed_preflight is not None:
        reasons.extend(
            _validate_preflight_counts(
                typed_preflight,
                original_messages,
                candidate_count=len(candidates),
            )
        )
    reasons.extend(
        _validate_compiled_messages(
            compiled_messages,
            preflight_result=typed_preflight,
            current_user_message=current_user_message,
        )
    )

    reasons = _unique(reasons)
    if reasons:
        return None, tuple(reasons)

    assert original is not None
    assert compiled is not None
    assert typed_preflight is not None
    assert typed_identity is not None
    assert current_user_message is not None
    return (
        ValidatedClientHistoryExclusionApplyV1Inputs(
            original_payload=original,
            original_messages=original_messages,
            compiled_payload=compiled,
            compiled_messages=compiled_messages,
            compiled_context_blocks=blocks,
            preflight_result=typed_preflight,
            identity_result=typed_identity,
            candidates=tuple(candidates),
            current_user_message=current_user_message,
        ),
        (),
    )


def _validate_preflight(
    result: ClientHistoryExclusionPreflightResult,
) -> list[str]:
    reasons: list[str] = []
    if result.schema_version != _PREFLIGHT_SCHEMA_VERSION:
        reasons.append("preflight_schema_unsupported")
    if result.managed_route is not True:
        reasons.append("preflight_not_managed")
    if result.runtime_private is not True or result.content_bearing is not True:
        reasons.append("preflight_not_runtime_private")
    if result.applied is not False:
        reasons.append("preflight_already_applied")
    if result.active_tool_transaction_candidate is True:
        reasons.append("active_tool_transaction_requires_preservation")
    if result.current_user_turn_present is not True:
        reasons.append("current_user_turn_missing")
    if result.current_user_content_valid is not True:
        reasons.append("current_user_content_invalid")
    if result.instruction_message_count <= 0:
        reasons.append("instruction_messages_missing")
    if result.raw_instruction_exclusion_candidate is not True:
        reasons.append("raw_instruction_exclusion_not_ready")

    supported_state = (
        result.status == "ready"
        and result.instruction_resolution_mode == "cache_hit"
    ) or (
        result.status == "pending"
        and result.instruction_resolution_mode == "cache_miss_first_pass"
    ) or (
        result.status == "blocked"
        and result.instruction_resolution_mode == "blocked"
        and bool(result.blocked_reasons)
        and set(result.blocked_reasons).issubset(_OPTIONAL_CACHE_BLOCK_REASONS)
    )
    if not supported_state:
        reasons.append("preflight_state_not_supported")
    return reasons


def _validate_identity_result(
    result: ClientInstructionIdentityResult,
) -> list[str]:
    reasons: list[str] = []
    if result.schema_version != _IDENTITY_SCHEMA_VERSION:
        reasons.append("identity_schema_unsupported")
    if result.ready is not True or result.blocked_reasons:
        reasons.append("identity_not_ready")
    identity = result.identity
    if identity is None:
        reasons.append("identity_missing")
        return reasons
    if identity.schema_version != _IDENTITY_SCHEMA_VERSION:
        reasons.append("identity_schema_unsupported")
    if identity.runtime_private is not True or identity.content_bearing is not True:
        reasons.append("identity_not_runtime_private")
    if identity.empty_instruction is True or not identity.candidates:
        reasons.append("identity_empty")
    for candidate in identity.candidates:
        if (
            not isinstance(candidate, NormalizedInstructionCandidate)
            or candidate.role not in _INSTRUCTION_ROLES
            or not isinstance(candidate.source_index, int)
            or isinstance(candidate.source_index, bool)
            or candidate.source_index < 0
            or not isinstance(candidate.normalized_text, str)
            or not candidate.normalized_text
        ):
            reasons.append("identity_candidate_invalid")
    return reasons


def _validate_preflight_counts(
    result: ClientHistoryExclusionPreflightResult,
    original_messages: Sequence[Mapping[str, Any]],
    *,
    candidate_count: int,
) -> list[str]:
    actual_system = sum(
        1 for message in original_messages if message.get("role") == "system"
    )
    actual_developer = sum(
        1 for message in original_messages if message.get("role") == "developer"
    )
    actual_instruction = actual_system + actual_developer
    reasons: list[str] = []
    if (
        result.original_message_count != len(original_messages)
        or result.valid_message_count != len(original_messages)
        or result.system_message_count != actual_system
        or result.developer_message_count != actual_developer
        or result.instruction_message_count != actual_instruction
    ):
        reasons.append("preflight_counts_invalid")
    if candidate_count != actual_instruction:
        reasons.append("identity_candidate_count_mismatch")
    return reasons


def _validate_candidate_sources(
    original_messages: Sequence[Mapping[str, Any]],
    candidates: Sequence[NormalizedInstructionCandidate],
) -> list[str]:
    instruction_indices = [
        index
        for index, message in enumerate(original_messages)
        if message.get("role") in _INSTRUCTION_ROLES
    ]
    if [candidate.source_index for candidate in candidates] != instruction_indices:
        return ["identity_candidate_source_mismatch"]
    for candidate in candidates:
        message = original_messages[candidate.source_index]
        if message.get("role") != candidate.role:
            return ["identity_candidate_source_mismatch"]
    return []


def _validate_compiled_messages(
    messages: Sequence[Mapping[str, Any]],
    *,
    preflight_result: ClientHistoryExclusionPreflightResult | None,
    current_user_message: Mapping[str, Any] | None,
) -> list[str]:
    reasons: list[str] = []
    if preflight_result is not None:
        expected_count = (
            preflight_result.original_message_count
            - preflight_result.instruction_message_count
            + 1
        )
        if len(messages) != expected_count:
            reasons.append("compiled_message_count_mismatch")
    if not messages:
        reasons.append("relay_owned_prefix_missing")
        return reasons
    prefix = messages[0]
    if (
        prefix.get("role") != "system"
        or not isinstance(prefix.get("content"), str)
        or not prefix.get("content")
    ):
        reasons.append("relay_owned_prefix_invalid")
    if any(message.get("role") in _INSTRUCTION_ROLES for message in messages[1:]):
        reasons.append("compiled_payload_contains_unexpected_instruction_messages")
    if current_user_message is not None and messages[-1] != current_user_message:
        reasons.append("current_user_candidate_mismatch")
    return reasons


def _latest_user_message(
    messages: Sequence[Mapping[str, Any]],
) -> tuple[int | None, Mapping[str, Any] | None]:
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].get("role") == "user":
            return index, messages[index]
    return None, None


def _payload_has_active_tool_transaction_after_current_user(
    messages: Sequence[Mapping[str, Any]],
    *,
    current_user_index: int | None,
) -> bool:
    if current_user_index is None:
        return False
    for message in messages[current_user_index + 1 :]:
        if message.get("role") == "tool":
            return True
        if (
            message.get("role") == "assistant"
            and isinstance(message.get("tool_calls"), list)
            and bool(message.get("tool_calls"))
        ):
            return True
    return False


def _current_user_content_valid(content: Any) -> bool:
    if isinstance(content, str):
        return bool(content.strip())
    if not isinstance(content, list) or not content:
        return False
    valid_part_present = False
    for part in content:
        if isinstance(part, str):
            if not part:
                return False
            valid_part_present = True
            continue
        if not isinstance(part, Mapping):
            return False
        part_type = part.get("type")
        if part_type in {"text", "input_text"}:
            text = part.get("text")
            if not isinstance(text, str) or not text.strip():
                return False
        elif not isinstance(part_type, str) or not part_type:
            return False
        valid_part_present = True
    return valid_part_present


def _unique(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result
