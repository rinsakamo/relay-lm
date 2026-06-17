"""Typed result shape for Phase 5-C4a instruction-bearing apply."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal


SCHEMA_VERSION = "client_history_exclusion_apply.v1"
ALLOWED_STATUSES = frozenset({"ready", "applied", "blocked", "skipped"})
ALLOWED_INSTRUCTION_RESOLUTION_MODES = frozenset(
    {"cache_hit", "cache_miss_first_pass", "blocked"}
)
ALLOWED_BLOCKED_REASONS = frozenset(
    {
        "pass_through_route_exempt",
        "compiled_profile_required",
        "original_payload_missing",
        "original_messages_not_list",
        "original_messages_contain_non_object_items",
        "compiled_payload_missing",
        "compiled_messages_not_list",
        "compiled_messages_contain_non_object_items",
        "compiled_message_count_mismatch",
        "relay_owned_prefix_missing",
        "relay_owned_prefix_invalid",
        "compiled_payload_contains_unexpected_instruction_messages",
        "typed_compiler_blocks_missing",
        "typed_compiler_blocks_invalid",
        "legacy_incoming_system_prompt_missing",
        "legacy_incoming_system_prompt_multiple",
        "instruction_evidence_block_already_present",
        "preflight_missing",
        "preflight_type_invalid",
        "preflight_schema_unsupported",
        "preflight_not_managed",
        "preflight_not_runtime_private",
        "preflight_already_applied",
        "preflight_state_not_supported",
        "preflight_counts_invalid",
        "instruction_messages_missing",
        "raw_instruction_exclusion_not_ready",
        "identity_missing",
        "identity_type_invalid",
        "identity_schema_unsupported",
        "identity_not_ready",
        "identity_not_runtime_private",
        "identity_empty",
        "identity_candidate_count_mismatch",
        "identity_candidate_source_mismatch",
        "identity_candidate_invalid",
        "active_tool_transaction_requires_preservation",
        "current_user_turn_missing",
        "current_user_content_invalid",
        "current_user_candidate_mismatch",
        "instruction_evidence_oversize",
        "instruction_evidence_render_failed",
        "dry_run_only_invalid",
        "client_history_exclusion_apply_preparation_failed",
    }
)


@dataclass(frozen=True)
class ClientHistoryExclusionApplyV1Result:
    """Request-local v1 result; the payload candidate must never be persisted."""

    schema_version: str
    status: Literal["ready", "applied", "blocked", "skipped"]
    forwarded_payload: Mapping[str, Any] | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    enabled: bool = True
    dry_run_only: bool = True
    managed_route: bool = False
    compiler_used: bool = False
    relay_owned_prefix_message_count: int = 0
    original_compiled_message_count: int = 0
    forwarded_message_count: int = 0
    excluded_client_message_count: int = 0
    preserved_client_message_count: int = 0
    instruction_resolution_mode: str = "blocked"
    instruction_candidate_count: int = 0
    instruction_evidence_block_present: bool = False
    instruction_evidence_rendered_char_count: int = 0
    legacy_incoming_system_prompt_replaced: bool = False
    raw_instruction_message_forwarded: bool = False
    cache_entry_content_injected: bool = False
    cache_projection_applied: bool = False
    payload_candidate_present: bool = False
    payload_mutation_applied: bool = False
    blocked_reasons: tuple[str, ...] = ()
    runtime_private: bool = True
    content_bearing: bool = True


def build_client_history_exclusion_apply_v1_result(
    *,
    status: Literal["ready", "applied", "blocked", "skipped"],
    forwarded_payload: Mapping[str, Any] | None = None,
    dry_run_only: bool,
    managed_route: bool,
    compiler_used: bool,
    relay_owned_prefix_message_count: int = 0,
    original_compiled_message_count: int = 0,
    forwarded_message_count: int = 0,
    excluded_client_message_count: int = 0,
    preserved_client_message_count: int = 0,
    instruction_resolution_mode: str = "blocked",
    instruction_candidate_count: int = 0,
    instruction_evidence_block_present: bool = False,
    instruction_evidence_rendered_char_count: int = 0,
    legacy_incoming_system_prompt_replaced: bool = False,
    payload_candidate_present: bool = False,
    payload_mutation_applied: bool = False,
    blocked_reasons: tuple[str, ...] = (),
) -> ClientHistoryExclusionApplyV1Result:
    return ClientHistoryExclusionApplyV1Result(
        schema_version=SCHEMA_VERSION,
        status=status,
        forwarded_payload=forwarded_payload,
        dry_run_only=dry_run_only,
        managed_route=managed_route,
        compiler_used=compiler_used,
        relay_owned_prefix_message_count=relay_owned_prefix_message_count,
        original_compiled_message_count=original_compiled_message_count,
        forwarded_message_count=forwarded_message_count,
        excluded_client_message_count=excluded_client_message_count,
        preserved_client_message_count=preserved_client_message_count,
        instruction_resolution_mode=safe_instruction_resolution_mode(
            instruction_resolution_mode
        ),
        instruction_candidate_count=instruction_candidate_count,
        instruction_evidence_block_present=instruction_evidence_block_present,
        instruction_evidence_rendered_char_count=(
            instruction_evidence_rendered_char_count
        ),
        legacy_incoming_system_prompt_replaced=(
            legacy_incoming_system_prompt_replaced
        ),
        raw_instruction_message_forwarded=False,
        cache_entry_content_injected=False,
        cache_projection_applied=False,
        payload_candidate_present=payload_candidate_present,
        payload_mutation_applied=payload_mutation_applied,
        blocked_reasons=tuple(safe_blocked_reasons(blocked_reasons)),
    )


def safe_status(value: Any) -> str:
    return value if isinstance(value, str) and value in ALLOWED_STATUSES else "blocked"


def safe_instruction_resolution_mode(value: Any) -> str:
    if (
        isinstance(value, str)
        and value in ALLOWED_INSTRUCTION_RESOLUTION_MODES
    ):
        return value
    return "blocked"


def safe_blocked_reasons(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return [
        value
        for value in values
        if isinstance(value, str) and value in ALLOWED_BLOCKED_REASONS
    ]


def non_negative_int(value: Any) -> int:
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        else 0
    )
