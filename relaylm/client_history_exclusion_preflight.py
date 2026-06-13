"""Diagnostics-only preflight for future managed-route client history exclusion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING, Any, Literal

from relaylm.client_message_canonicalization import (
    build_client_message_canonicalization_dry_run,
)
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result

if TYPE_CHECKING:
    from relaylm.client_instruction_cache_lookup_runtime import (
        ClientInstructionCacheLookupRuntimeResult,
    )
    from relaylm.pipeline_context import PipelineContext

_SCHEMA_VERSION = "client_history_exclusion_preflight.v0"
_RUNTIME_FAILURE_REASON = "history_exclusion_preflight_preparation_failed"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_KEYS = frozenset(
    {
        "current_user_message",
        "content",
        "text",
        "image_url",
        "audio",
        "input_audio",
        "url",
        "data",
        "raw_instruction",
        "normalized_instruction",
        "cache_key",
        "fingerprint",
        "hash",
        "cache_root",
        "root_path",
        "path",
        "cache_entry",
        "scene",
        "scene_role",
        "scene_context",
        "scene_constraints",
        "route_model",
        "character_id",
        "tool_call_id",
        "tool_calls",
        "arguments",
        "exception",
        "exception_text",
        "messages",
        "original_payload",
        "forwarded_payload",
        "message_indexes",
    }
)


@dataclass(frozen=True)
class ClientHistoryExclusionPreflightResult:
    schema_version: str
    status: Literal["ready", "pending", "blocked", "skipped"]
    current_user_message: Mapping[str, Any] | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    instruction_resolution_mode: Literal[
        "none",
        "cache_hit",
        "cache_miss_first_pass",
        "blocked",
        "not_applicable",
    ] = "not_applicable"
    original_message_count: int = 0
    excluded_message_count_candidate: int = 0
    preserved_client_message_count_candidate: int = 0
    first_pass_evidence_required: bool = False
    history_exclusion_apply_ready: bool = False
    blocked_reasons: tuple[str, ...] = ()
    applied: bool = False
    runtime_private: bool = True
    content_bearing: bool = True
    managed_route: bool = False
    valid_message_count: int = 0
    system_message_count: int = 0
    developer_message_count: int = 0
    instruction_message_count: int = 0
    prior_user_message_count: int = 0
    prior_assistant_message_count: int = 0
    tool_message_count: int = 0
    current_user_turn_present: bool = False
    current_user_content_valid: bool = False
    current_user_content_kind: str = "missing"
    current_user_multimodal: bool = False
    current_user_text_part_count: int = 0
    current_user_non_text_part_count: int = 0
    active_tool_transaction_candidate: bool = False
    cache_lookup_status: str | None = None
    raw_instruction_exclusion_candidate: bool = False


def client_message_canonicalization_dependency_enabled(route: Any) -> bool:
    return bool(
        getattr(route, "client_message_canonicalization_dry_run_enabled", False)
        or getattr(route, "client_history_exclusion_preflight_enabled", False)
    )


def build_client_history_exclusion_preflight(
    payload: Mapping[str, Any] | None,
    canonicalization_artifact: Mapping[str, Any] | None,
    cache_lookup_runtime_result: ClientInstructionCacheLookupRuntimeResult | None,
    *,
    enabled: bool,
    managed_route: bool,
) -> ClientHistoryExclusionPreflightResult | None:
    if not enabled:
        return None

    base = _base(canonicalization_artifact, managed_route=managed_route)
    if not managed_route:
        return _result(
            base,
            status="skipped",
            blocked_reasons=("pass_through_route_exempt",),
        )

    reasons: list[str] = []
    messages = payload.get("messages") if isinstance(payload, Mapping) else None
    invalid_messages = not isinstance(messages, list) or any(
        not isinstance(message, Mapping) for message in messages
    )
    if not isinstance(messages, list):
        reasons.append("messages_not_list")
    elif invalid_messages:
        reasons.append("messages_contain_non_object_items")

    if not isinstance(canonicalization_artifact, Mapping):
        reasons.append("source_canonicalization_missing")
    elif (
        canonicalization_artifact.get("schema_version")
        != "client_message_canonicalization_dry_run.v0"
    ):
        reasons.append("source_canonicalization_schema_unsupported")
    elif canonicalization_artifact.get("canonicalization_candidate_ready") is not True:
        reasons.extend(
            _strings(canonicalization_artifact.get("blocked_reasons"))
            or ["source_canonicalization_blocked"]
        )

    current_user_index: int | None = None
    current_user_message: Mapping[str, Any] | None = None
    if isinstance(messages, list) and not invalid_messages:
        current_user_index, current_user_message = _latest_user_message(messages)

    if current_user_message is None:
        reasons.append("current_user_turn_missing")
    elif not _current_user_content_valid(current_user_message.get("content")):
        reasons.append("current_user_content_invalid")

    if isinstance(canonicalization_artifact, Mapping) and isinstance(messages, list):
        if canonicalization_artifact.get("message_count") != len(messages):
            reasons.append("current_user_candidate_mismatch")
        if canonicalization_artifact.get("current_user_turn_present") != (
            current_user_message is not None
        ):
            reasons.append("current_user_candidate_mismatch")
        if current_user_message is not None and (
            canonicalization_artifact.get("current_user_content_valid")
            != _current_user_content_valid(current_user_message.get("content"))
        ):
            reasons.append("current_user_candidate_mismatch")

    active_tool_transaction = bool(base["active_tool_transaction_candidate"])
    if not active_tool_transaction:
        active_tool_transaction = _payload_has_active_tool_transaction_after_current_user(
            messages,
            current_user_index=current_user_index,
        )
    if (
        active_tool_transaction
        or "active_tool_transaction_requires_preservation" in reasons
    ):
        base["active_tool_transaction_candidate"] = True
        reasons.append("active_tool_transaction_requires_preservation")

    reasons = _unique(reasons)
    candidate = (
        deepcopy(dict(current_user_message))
        if current_user_message is not None and not reasons
        else None
    )
    if reasons:
        return _result(
            base,
            status="blocked",
            current_user_message=None,
            instruction_resolution_mode="blocked",
            blocked_reasons=tuple(reasons),
        )

    instruction_count = int(base["instruction_message_count"])
    preserved = 1
    excluded = max(0, int(base["original_message_count"]) - preserved)
    if instruction_count == 0:
        return _result(
            base,
            status="ready",
            current_user_message=candidate,
            instruction_resolution_mode="none",
            excluded=excluded,
            preserved=preserved,
            apply_ready=True,
        )

    lookup_status = getattr(cache_lookup_runtime_result, "status", None)
    base["cache_lookup_status"] = lookup_status
    if lookup_status == "hit":
        return _result(
            base,
            status="ready",
            current_user_message=candidate,
            instruction_resolution_mode="cache_hit",
            excluded=excluded,
            preserved=preserved,
            apply_ready=True,
            raw_instruction=True,
        )
    if lookup_status == "miss":
        return _result(
            base,
            status="pending",
            current_user_message=candidate,
            instruction_resolution_mode="cache_miss_first_pass",
            excluded=excluded,
            preserved=preserved,
            first_pass=True,
            decision_ready=False,
            raw_instruction=True,
        )

    reason = (
        "instruction_cache_lookup_result_missing"
        if cache_lookup_runtime_result is None
        else "instruction_cache_lookup_blocked"
    )
    return _result(
        base,
        status="blocked",
        instruction_resolution_mode="blocked",
        blocked_reasons=(reason,),
        raw_instruction=True,
    )


def prepare_client_history_exclusion_preflight_runtime_private(
    *,
    pipeline_context: PipelineContext,
) -> None:
    if not getattr(
        pipeline_context.route,
        "client_history_exclusion_preflight_enabled",
        False,
    ):
        pipeline_context.set_client_history_exclusion_preflight_result(None)
        return

    try:
        managed = pipeline_context.route.mode_applied != "pass_through"
        artifact = build_client_message_canonicalization_dry_run(
            pipeline_context.original_payload,
            enabled=client_message_canonicalization_dependency_enabled(
                pipeline_context.route
            ),
            managed_route=managed,
        )
        result = build_client_history_exclusion_preflight(
            pipeline_context.original_payload,
            artifact,
            pipeline_context.client_instruction_cache_lookup_runtime_result,
            enabled=True,
            managed_route=managed,
        )
    except Exception:
        result = ClientHistoryExclusionPreflightResult(
            schema_version=_SCHEMA_VERSION,
            status="blocked",
            blocked_reasons=(_RUNTIME_FAILURE_REASON,),
        )
    pipeline_context.set_client_history_exclusion_preflight_result(result)


def build_client_history_exclusion_preflight_diagnostics(
    result: ClientHistoryExclusionPreflightResult | None,
) -> dict[str, Any] | None:
    if result is None:
        return None

    diagnostics = {
        "schema_version": result.schema_version,
        "enabled": True,
        "status": result.status,
        "managed_route": result.managed_route,
        "preflight_ready": result.status == "ready",
        "history_exclusion_apply_ready": result.history_exclusion_apply_ready,
        "instruction_resolution_mode": result.instruction_resolution_mode,
        "first_pass_evidence_required": result.first_pass_evidence_required,
        "original_message_count": result.original_message_count,
        "valid_message_count": result.valid_message_count,
        "excluded_message_count_candidate": result.excluded_message_count_candidate,
        "preserved_client_message_count_candidate": (
            result.preserved_client_message_count_candidate
        ),
        "system_message_count": result.system_message_count,
        "developer_message_count": result.developer_message_count,
        "instruction_message_count": result.instruction_message_count,
        "prior_user_message_count": result.prior_user_message_count,
        "prior_assistant_message_count": result.prior_assistant_message_count,
        "tool_message_count": result.tool_message_count,
        "current_user_turn_present": result.current_user_turn_present,
        "current_user_content_valid": result.current_user_content_valid,
        "current_user_content_kind": result.current_user_content_kind,
        "current_user_multimodal": result.current_user_multimodal,
        "current_user_text_part_count": result.current_user_text_part_count,
        "current_user_non_text_part_count": result.current_user_non_text_part_count,
        "active_tool_transaction_candidate": result.active_tool_transaction_candidate,
        "cache_lookup_status": result.cache_lookup_status,
        "raw_instruction_exclusion_candidate": (
            result.raw_instruction_exclusion_candidate
        ),
        "payload_mutation_applied": False,
        "blocked_reasons": result.blocked_reasons,
        "runtime_private_source": True,
    }
    assert_client_history_exclusion_preflight_diagnostics_content_free(diagnostics)
    return diagnostics


def build_client_history_exclusion_preflight_node_result(
    result: ClientHistoryExclusionPreflightResult | None,
) -> PipelineNodeResult | None:
    diagnostics = build_client_history_exclusion_preflight_diagnostics(result)
    if diagnostics is None:
        return None

    decision = "history_exclusion_preflight_ready"
    if result.status == "pending":
        decision = "client_instruction_first_pass_required"
    elif result.status == "skipped":
        decision = "pass_through_route_exempt"
    elif result.status == "blocked":
        decision = (
            _RUNTIME_FAILURE_REASON
            if _RUNTIME_FAILURE_REASON in result.blocked_reasons
            else "history_exclusion_preflight_blocked"
        )

    blocked_reasons = _strings(diagnostics.pop("blocked_reasons"))
    node = build_pipeline_node_result(
        node_name="client_history_exclusion_preflight",
        status="diagnostic_only",
        decision=decision,
        blocked_reasons=blocked_reasons,
        diagnostics=diagnostics,
        artifacts=[
            {
                "artifact_name": "client_history_exclusion_preflight_summary",
                "schema_version": _SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": True,
                "content_free": True,
                "runtime_private_source": True,
                "payload_mutation_applied": False,
                "applied": False,
            }
        ],
    )
    assert_client_history_exclusion_preflight_diagnostics_content_free(
        node.to_log_dict()
    )
    return node


def assert_client_history_exclusion_preflight_diagnostics_content_free(
    value: Any,
) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _FORBIDDEN_KEYS:
                raise ValueError(f"private/content-bearing diagnostics key: {key}")
            assert_client_history_exclusion_preflight_diagnostics_content_free(nested)
    elif isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        for nested in value:
            assert_client_history_exclusion_preflight_diagnostics_content_free(nested)
    elif isinstance(value, str) and _SHA256_RE.fullmatch(value):
        raise ValueError("hash value is not allowed in diagnostics")


def _base(
    artifact: Mapping[str, Any] | None,
    *,
    managed_route: bool,
) -> dict[str, Any]:
    artifact = artifact if isinstance(artifact, Mapping) else {}
    return {
        "managed_route": managed_route,
        "original_message_count": int(artifact.get("message_count") or 0),
        "valid_message_count": int(artifact.get("valid_message_count") or 0),
        "system_message_count": int(artifact.get("system_message_count") or 0),
        "developer_message_count": int(
            artifact.get("developer_message_count") or 0
        ),
        "instruction_message_count": int(
            artifact.get("instruction_message_count") or 0
        ),
        "prior_user_message_count": int(
            artifact.get("prior_user_message_count") or 0
        ),
        "prior_assistant_message_count": int(
            artifact.get("prior_assistant_message_count") or 0
        ),
        "tool_message_count": int(artifact.get("tool_message_count") or 0),
        "current_user_turn_present": bool(
            artifact.get("current_user_turn_present")
        ),
        "current_user_content_valid": bool(
            artifact.get("current_user_content_valid")
        ),
        "current_user_content_kind": str(
            artifact.get("current_user_content_kind") or "missing"
        ),
        "current_user_multimodal": bool(artifact.get("current_user_multimodal")),
        "current_user_text_part_count": int(
            artifact.get("current_user_text_part_count") or 0
        ),
        "current_user_non_text_part_count": int(
            artifact.get("current_user_non_text_part_count") or 0
        ),
        "active_tool_transaction_candidate": bool(
            artifact.get("active_tool_transaction_candidate")
        ),
        "cache_lookup_status": None,
    }


def _result(
    base: dict[str, Any],
    *,
    status: str,
    current_user_message: Mapping[str, Any] | None = None,
    instruction_resolution_mode: str = "not_applicable",
    excluded: int = 0,
    preserved: int = 0,
    first_pass: bool = False,
    apply_ready: bool = False,
    decision_ready: bool = True,
    blocked_reasons: Sequence[str] = (),
    raw_instruction: bool = False,
) -> ClientHistoryExclusionPreflightResult:
    return ClientHistoryExclusionPreflightResult(
        schema_version=_SCHEMA_VERSION,
        status=status,  # type: ignore[arg-type]
        current_user_message=current_user_message,
        instruction_resolution_mode=instruction_resolution_mode,  # type: ignore[arg-type]
        original_message_count=base["original_message_count"],
        excluded_message_count_candidate=excluded,
        preserved_client_message_count_candidate=preserved,
        first_pass_evidence_required=first_pass,
        history_exclusion_apply_ready=apply_ready and decision_ready,
        blocked_reasons=tuple(blocked_reasons),
        managed_route=base["managed_route"],
        valid_message_count=base["valid_message_count"],
        system_message_count=base["system_message_count"],
        developer_message_count=base["developer_message_count"],
        instruction_message_count=base["instruction_message_count"],
        prior_user_message_count=base["prior_user_message_count"],
        prior_assistant_message_count=base["prior_assistant_message_count"],
        tool_message_count=base["tool_message_count"],
        current_user_turn_present=base["current_user_turn_present"],
        current_user_content_valid=base["current_user_content_valid"],
        current_user_content_kind=base["current_user_content_kind"],
        current_user_multimodal=base["current_user_multimodal"],
        current_user_text_part_count=base["current_user_text_part_count"],
        current_user_non_text_part_count=base[
            "current_user_non_text_part_count"
        ],
        active_tool_transaction_candidate=base[
            "active_tool_transaction_candidate"
        ],
        cache_lookup_status=base.get("cache_lookup_status"),
        raw_instruction_exclusion_candidate=raw_instruction,
    )


def _latest_user_message(
    messages: Sequence[Mapping[str, Any]],
) -> tuple[int | None, Mapping[str, Any] | None]:
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if message.get("role") == "user":
            return index, message
    return None, None


def _payload_has_active_tool_transaction_after_current_user(
    messages: Any,
    *,
    current_user_index: int | None,
) -> bool:
    if not isinstance(messages, list) or current_user_index is None:
        return False
    for message in messages[current_user_index + 1 :]:
        if not isinstance(message, Mapping):
            continue
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


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _unique(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result
