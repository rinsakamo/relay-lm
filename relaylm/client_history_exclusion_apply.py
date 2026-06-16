"""Pure apply contract for managed-route client history exclusion."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal

from relaylm.client_history_exclusion_preflight import (
    ClientHistoryExclusionPreflightResult,
)
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result

_SCHEMA_VERSION = "client_history_exclusion_apply.v0"
_PREFLIGHT_SCHEMA_VERSION = "client_history_exclusion_preflight.v0"
_INSTRUCTION_ROLES = frozenset({"system", "developer"})
_RELAY_OWNED_PREFIX_MESSAGE_COUNT = 1
_ALLOWED_STATUSES = frozenset({"ready", "applied", "blocked", "skipped"})
_ALLOWED_INSTRUCTION_RESOLUTION_MODES = frozenset(
    {"none", "cache_hit", "cache_miss_first_pass", "blocked", "not_applicable"}
)
_ALLOWED_BLOCKED_REASONS = frozenset(
    {
        "pass_through_route_exempt",
        "compiled_profile_required",
        "compiled_payload_missing",
        "compiled_messages_not_list",
        "compiled_messages_contain_non_object_items",
        "preflight_missing",
        "preflight_type_invalid",
        "preflight_schema_unsupported",
        "preflight_not_managed",
        "preflight_not_runtime_private",
        "preflight_already_applied",
        "preflight_not_ready",
        "preflight_apply_not_ready",
        "instruction_resolution_not_supported",
        "instruction_messages_present",
        "raw_instruction_exclusion_not_supported",
        "active_tool_transaction_requires_preservation",
        "current_user_turn_missing",
        "current_user_content_invalid",
        "current_user_candidate_missing",
        "current_user_candidate_invalid",
        "original_message_count_invalid",
        "valid_message_count_mismatch",
        "preserved_client_message_count_mismatch",
        "excluded_client_message_count_mismatch",
        "compiled_message_count_mismatch",
        "relay_owned_prefix_missing",
        "relay_owned_prefix_invalid",
        "compiled_payload_contains_unexpected_instruction_messages",
        "current_user_candidate_mismatch",
        "dry_run_only_invalid",
    }
)


@dataclass(frozen=True)
class ClientHistoryExclusionApplyResult:
    """Request-local result for the no-instruction history-exclusion slice.

    ``forwarded_payload`` may contain user content and must remain request-local.
    Diagnostics and pipeline-node adapters below copy only explicit scalar fields.
    """

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
    instruction_resolution_mode: str = "not_applicable"
    payload_candidate_present: bool = False
    payload_mutation_applied: bool = False
    blocked_reasons: tuple[str, ...] = ()
    runtime_private: bool = True
    content_bearing: bool = True


def build_client_history_exclusion_apply(
    compiled_payload: Mapping[str, Any] | None,
    preflight_result: ClientHistoryExclusionPreflightResult | None,
    *,
    enabled: bool,
    dry_run_only: bool,
    managed_route: bool,
    compiler_used: bool,
) -> ClientHistoryExclusionApplyResult | None:
    """Build a fresh backend payload for the no-client-instruction case only.

    This first Phase 5-C slice deliberately supports exactly the current compiler
    layout: one RelayLM-owned compiled system message followed by the untrusted
    client message chain. It retains that one server-owned prefix message and the
    detached current-user candidate from the preflight result. Cache hit/miss and
    client instruction evidence remain unsupported here.

    The input payload is never mutated. When ``dry_run_only`` is true, the rebuilt
    payload is returned as a private candidate but is not marked as applied.
    """

    if enabled is not True:
        return None

    if managed_route is not True:
        return _result(
            status="skipped",
            dry_run_only=dry_run_only,
            managed_route=False,
            compiler_used=compiler_used,
            blocked_reasons=("pass_through_route_exempt",),
        )

    blocked_reasons: list[str] = []
    payload = compiled_payload if isinstance(compiled_payload, Mapping) else None
    messages = payload.get("messages") if payload is not None else None
    compiled_message_count = len(messages) if isinstance(messages, list) else 0

    if compiler_used is not True:
        blocked_reasons.append("compiled_profile_required")
    if not isinstance(dry_run_only, bool):
        blocked_reasons.append("dry_run_only_invalid")
        dry_run_only = True
    if payload is None:
        blocked_reasons.append("compiled_payload_missing")
    if not isinstance(messages, list):
        blocked_reasons.append("compiled_messages_not_list")
    elif any(not isinstance(message, Mapping) for message in messages):
        blocked_reasons.append("compiled_messages_contain_non_object_items")

    typed_preflight = (
        preflight_result
        if isinstance(preflight_result, ClientHistoryExclusionPreflightResult)
        else None
    )
    if preflight_result is None:
        blocked_reasons.append("preflight_missing")
    elif typed_preflight is None:
        blocked_reasons.append("preflight_type_invalid")
    else:
        blocked_reasons.extend(_validate_preflight(typed_preflight))

    current_user_message = (
        typed_preflight.current_user_message if typed_preflight is not None else None
    )

    if isinstance(messages, list) and all(
        isinstance(message, Mapping) for message in messages
    ):
        blocked_reasons.extend(
            _validate_compiled_messages(
                messages,
                preflight_result=typed_preflight,
                current_user_message=current_user_message,
            )
        )

    blocked_reasons = _unique(blocked_reasons)
    if blocked_reasons:
        return _result(
            status="blocked",
            dry_run_only=dry_run_only,
            managed_route=True,
            compiler_used=compiler_used,
            original_compiled_message_count=compiled_message_count,
            instruction_resolution_mode=(
                _safe_instruction_resolution_mode(
                    typed_preflight.instruction_resolution_mode
                )
                if typed_preflight is not None
                else "not_applicable"
            ),
            blocked_reasons=tuple(blocked_reasons),
        )

    assert payload is not None
    assert isinstance(messages, list)
    assert isinstance(typed_preflight, ClientHistoryExclusionPreflightResult)
    assert isinstance(current_user_message, Mapping)

    rebuilt_payload = deepcopy(dict(payload))
    rebuilt_messages = [
        deepcopy(dict(messages[0])),
        deepcopy(dict(current_user_message)),
    ]
    rebuilt_payload["messages"] = rebuilt_messages
    applied = not dry_run_only

    return _result(
        status="applied" if applied else "ready",
        forwarded_payload=rebuilt_payload,
        dry_run_only=dry_run_only,
        managed_route=True,
        compiler_used=True,
        relay_owned_prefix_message_count=_RELAY_OWNED_PREFIX_MESSAGE_COUNT,
        original_compiled_message_count=len(messages),
        forwarded_message_count=len(rebuilt_messages),
        excluded_client_message_count=(
            typed_preflight.excluded_message_count_candidate
        ),
        preserved_client_message_count=1,
        instruction_resolution_mode="none",
        payload_candidate_present=True,
        payload_mutation_applied=applied,
    )


def build_client_history_exclusion_apply_diagnostics(
    result: ClientHistoryExclusionApplyResult | None,
) -> dict[str, Any] | None:
    """Project one exact content-free diagnostic shape."""

    if result is None:
        return None
    return {
        "schema_version": _SCHEMA_VERSION,
        "enabled": result.enabled is True,
        "status": _safe_status(result.status),
        "dry_run_only": result.dry_run_only is True,
        "managed_route": result.managed_route is True,
        "compiler_used": result.compiler_used is True,
        "relay_owned_prefix_message_count": _non_negative_int(
            result.relay_owned_prefix_message_count
        ),
        "original_compiled_message_count": _non_negative_int(
            result.original_compiled_message_count
        ),
        "forwarded_message_count": _non_negative_int(
            result.forwarded_message_count
        ),
        "excluded_client_message_count": _non_negative_int(
            result.excluded_client_message_count
        ),
        "preserved_client_message_count": _non_negative_int(
            result.preserved_client_message_count
        ),
        "instruction_resolution_mode": _safe_instruction_resolution_mode(
            result.instruction_resolution_mode
        ),
        "payload_candidate_present": result.forwarded_payload is not None,
        "payload_mutation_applied": (
            result.payload_mutation_applied is True
            and result.forwarded_payload is not None
            and _safe_status(result.status) == "applied"
        ),
        "blocked_reasons": _safe_blocked_reasons(result.blocked_reasons),
        "runtime_private_source": True,
        "content_bearing_candidate_persisted": False,
    }


def build_client_history_exclusion_apply_node_result(
    result: ClientHistoryExclusionApplyResult | None,
) -> PipelineNodeResult | None:
    """Build a content-free pipeline result without exposing the payload candidate."""

    diagnostics = build_client_history_exclusion_apply_diagnostics(result)
    if diagnostics is None or result is None:
        return None

    projected_status = diagnostics["status"]
    if projected_status == "skipped":
        status = "skipped"
        decision = "pass_through_route_exempt"
    elif projected_status == "blocked":
        status = "blocked"
        decision = "client_history_exclusion_apply_blocked"
    elif projected_status == "applied":
        status = "applied"
        decision = "client_history_exclusion_applied"
    else:
        status = "diagnostic_only"
        decision = "client_history_exclusion_apply_ready"

    blocked_reasons = diagnostics.pop("blocked_reasons")
    return build_pipeline_node_result(
        node_name="client_history_exclusion_apply",
        status=status,
        decision=decision,
        blocked_reasons=blocked_reasons,
        diagnostics=diagnostics,
        artifacts=[
            {
                "artifact_name": "client_history_exclusion_apply_summary",
                "schema_version": _SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": projected_status != "applied",
                "content_free": True,
                "runtime_private_source": True,
                "payload_candidate_present": diagnostics["payload_candidate_present"],
                "payload_mutation_applied": diagnostics["payload_mutation_applied"],
                "content_bearing_candidate_persisted": False,
            }
        ],
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
    if result.status != "ready":
        reasons.append("preflight_not_ready")
    if result.history_exclusion_apply_ready is not True:
        reasons.append("preflight_apply_not_ready")
    if result.instruction_resolution_mode != "none":
        reasons.append("instruction_resolution_not_supported")
    if result.instruction_message_count != 0:
        reasons.append("instruction_messages_present")
    if result.raw_instruction_exclusion_candidate is not False:
        reasons.append("raw_instruction_exclusion_not_supported")
    if result.active_tool_transaction_candidate is True:
        reasons.append("active_tool_transaction_requires_preservation")
    if result.current_user_turn_present is not True:
        reasons.append("current_user_turn_missing")
    if result.current_user_content_valid is not True:
        reasons.append("current_user_content_invalid")
    if not isinstance(result.current_user_message, Mapping):
        reasons.append("current_user_candidate_missing")
    elif result.current_user_message.get("role") != "user":
        reasons.append("current_user_candidate_invalid")
    if (
        not _is_non_negative_int(result.original_message_count)
        or result.original_message_count <= 0
    ):
        reasons.append("original_message_count_invalid")
    if (
        not _is_non_negative_int(result.valid_message_count)
        or result.valid_message_count != result.original_message_count
    ):
        reasons.append("valid_message_count_mismatch")
    if (
        not _is_non_negative_int(result.preserved_client_message_count_candidate)
        or result.preserved_client_message_count_candidate != 1
    ):
        reasons.append("preserved_client_message_count_mismatch")
    if not _is_non_negative_int(result.excluded_message_count_candidate):
        reasons.append("excluded_client_message_count_mismatch")
    elif _is_non_negative_int(result.original_message_count) and (
        result.excluded_message_count_candidate
        != max(0, result.original_message_count - 1)
    ):
        reasons.append("excluded_client_message_count_mismatch")
    return reasons


def _validate_compiled_messages(
    messages: list[Any],
    *,
    preflight_result: ClientHistoryExclusionPreflightResult | None,
    current_user_message: Mapping[str, Any] | None,
) -> list[str]:
    reasons: list[str] = []
    if preflight_result is None:
        return reasons

    if _is_non_negative_int(preflight_result.original_message_count):
        expected_message_count = preflight_result.original_message_count + 1
        if len(messages) != expected_message_count:
            reasons.append("compiled_message_count_mismatch")

    if not messages:
        reasons.append("relay_owned_prefix_missing")
        return reasons

    prefix = messages[0]
    if not isinstance(prefix, Mapping):
        reasons.append("relay_owned_prefix_invalid")
    elif prefix.get("role") != "system":
        reasons.append("relay_owned_prefix_invalid")
    elif not isinstance(prefix.get("content"), str) or not prefix.get("content"):
        reasons.append("relay_owned_prefix_invalid")

    tail = messages[_RELAY_OWNED_PREFIX_MESSAGE_COUNT:]
    if any(
        isinstance(message, Mapping) and message.get("role") in _INSTRUCTION_ROLES
        for message in tail
    ):
        reasons.append("compiled_payload_contains_unexpected_instruction_messages")

    if not isinstance(current_user_message, Mapping):
        return reasons
    if not messages or messages[-1] != current_user_message:
        reasons.append("current_user_candidate_mismatch")
    return reasons


def _result(
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
    instruction_resolution_mode: str = "not_applicable",
    payload_candidate_present: bool = False,
    payload_mutation_applied: bool = False,
    blocked_reasons: tuple[str, ...] = (),
) -> ClientHistoryExclusionApplyResult:
    return ClientHistoryExclusionApplyResult(
        schema_version=_SCHEMA_VERSION,
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
        instruction_resolution_mode=_safe_instruction_resolution_mode(
            instruction_resolution_mode
        ),
        payload_candidate_present=payload_candidate_present,
        payload_mutation_applied=payload_mutation_applied,
        blocked_reasons=tuple(_safe_blocked_reasons(blocked_reasons)),
    )


def _safe_status(value: Any) -> str:
    return value if isinstance(value, str) and value in _ALLOWED_STATUSES else "blocked"


def _safe_instruction_resolution_mode(value: Any) -> str:
    if isinstance(value, str) and value in _ALLOWED_INSTRUCTION_RESOLUTION_MODES:
        return value
    return "blocked"


def _safe_blocked_reasons(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return [
        value
        for value in values
        if isinstance(value, str) and value in _ALLOWED_BLOCKED_REASONS
    ]


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _non_negative_int(value: Any) -> int:
    return value if _is_non_negative_int(value) else 0


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
