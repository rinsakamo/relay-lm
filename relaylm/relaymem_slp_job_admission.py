"""Deferred RelaySLP job-admission preflight helpers.

Phase 6-A1 is helper-only. It validates bounded deferred-job metadata and a
content-free RelayMEM source-lineage artifact. It never enqueues work, invokes a
worker, writes memory, mutates RelaySOUL, or changes visible response delivery.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_SCHEMA_VERSION = "relaymem.slp_job_admission_preflight.v0"
_PROJECTION_SCHEMA_VERSION = "relaymem.slp_job_admission_projection.v0"
_SOURCE_LINEAGE_SCHEMA_VERSION = "relaymem.primary_source_lineage.v0"

_KNOWN_TRIGGER_MODES = {
    "turn_end",
    "explicit_memory_request",
    "session_end",
    "communication_end",
    "scheduled_consolidation",
    "recovery_followup",
    "lab_memory_operation",
}
_SUPPORTED_TRIGGER_MODES = {"turn_end", "explicit_memory_request"}
_KNOWN_PROCESSING_STAGES = {
    "primary_formation",
    "primary_write_preflight",
    "secondary_consolidation",
    "memory_operation",
    "lint",
}
_SUPPORTED_PROCESSING_STAGES = {"primary_formation", "primary_write_preflight"}
_KNOWN_SOURCE_EVENT_KINDS = {"turn", "session", "communication", "manual_import"}
_KNOWN_RUNTIME_TERMINAL_STATUSES = {
    "completed",
    "succeeded",
    "idle",
    "blocked",
    "failed",
    "waiting_user",
    "recovery_pending",
    "unresolved_recovery",
}
_ALLOWED_RUNTIME_TERMINAL_STATUSES = {"completed", "succeeded", "idle"}
_BLOCKED_RUNTIME_TERMINAL_STATUSES = {
    "blocked",
    "failed",
    "waiting_user",
    "recovery_pending",
    "unresolved_recovery",
}
_KNOWN_PERSISTENCE_POLICY_STATUSES = {
    "allowed",
    "free_to_update",
    "review_required",
    "explicit_approval_required",
    "blocked",
    "never_auto_promote",
}
_ALLOWED_PERSISTENCE_POLICY_STATUSES = {"allowed", "free_to_update"}
_HELD_PERSISTENCE_POLICY_STATUSES = {"review_required"}
_BLOCKED_PERSISTENCE_POLICY_STATUSES = {
    "explicit_approval_required",
    "blocked",
    "never_auto_promote",
}
_ALLOWED_LINEAGE_FIELDS = {
    "schema_version",
    "content_free",
    "content_included",
    "raw_text_included",
    "source_event_kind",
    "namespace",
    "valid",
    "lineage_fingerprint",
    "lineage_shape",
    "blocked_reasons",
}
_ALLOWED_LINEAGE_SHAPE_FIELDS = {
    "source_event_id_present",
    "run_id_present",
    "session_id_present",
    "turn_index_present",
}
_MAX_TOKEN_LENGTH = 128
_MAX_SOURCE_COUNT = 32
_MAX_BLOCKED_REASONS = 32


def build_relaymem_slp_job_admission_preflight(
    *,
    enabled: bool = False,
    dry_run_only: bool = True,
    enqueue_enabled: bool = False,
    trigger_mode: str = "turn_end",
    processing_stage: str = "primary_formation",
    run_id: str | None = None,
    turn_index: int | None = None,
    session_id: str | None = None,
    namespace: str = "default",
    source_event_kind: str = "turn",
    source_lineage_artifact: Mapping[str, Any] | None = None,
    source_count: int = 1,
    visible_response_finalized: bool = False,
    runtime_terminal_status: str = "completed",
    persistence_policy_status: str = "allowed",
) -> dict[str, Any]:
    """Build a bounded RelaySLP deferred-job admission decision.

    The returned private artifact may contain bounded runtime correlation tokens.
    Its nested ``projection`` is the only public diagnostics shape and never
    includes those tokens, lineage fingerprints, or idempotency material.
    """

    safe_enabled, enabled_reasons = _required_bool(enabled, "enabled_invalid")
    safe_dry_run_only, dry_run_reasons = _required_bool(
        dry_run_only, "dry_run_only_invalid"
    )
    safe_enqueue_enabled, enqueue_reasons = _required_bool(
        enqueue_enabled, "enqueue_enabled_invalid"
    )
    safe_visible_finalized, visible_reasons = _required_bool(
        visible_response_finalized, "visible_response_finalized_invalid"
    )

    safe_trigger, trigger_reasons = _validated_enum(
        trigger_mode,
        known=_KNOWN_TRIGGER_MODES,
        supported=_SUPPORTED_TRIGGER_MODES,
        invalid_reason="trigger_mode_invalid",
        unsupported_reason="trigger_mode_unsupported",
    )
    safe_stage, stage_reasons = _validated_enum(
        processing_stage,
        known=_KNOWN_PROCESSING_STAGES,
        supported=_SUPPORTED_PROCESSING_STAGES,
        invalid_reason="processing_stage_invalid",
        unsupported_reason="processing_stage_unsupported",
    )
    safe_run_id, run_id_reasons = _required_token(run_id, "run_id_invalid")
    safe_session_id, session_id_reasons = _optional_token(
        session_id, "session_id_invalid"
    )
    safe_namespace, namespace_reasons = _required_token(
        namespace, "namespace_invalid"
    )
    safe_turn_index, turn_index_reasons = _optional_non_negative_int(
        turn_index, "turn_index_invalid"
    )
    safe_source_count, source_count_reasons = _bounded_source_count(source_count)
    safe_source_event_kind, source_event_reasons = _validated_source_event_kind(
        source_event_kind
    )
    safe_runtime_status, runtime_status_reasons = _validated_runtime_status(
        runtime_terminal_status
    )
    safe_policy_status, policy_status_reasons = _validated_policy_status(
        persistence_policy_status
    )

    structural_reasons = _dedupe(
        enabled_reasons
        + dry_run_reasons
        + enqueue_reasons
        + visible_reasons
        + trigger_reasons
        + stage_reasons
        + run_id_reasons
        + session_id_reasons
        + namespace_reasons
        + turn_index_reasons
        + source_count_reasons
        + source_event_reasons
        + runtime_status_reasons
        + policy_status_reasons
    )

    if safe_enabled is False:
        structural_reasons.append("feature_disabled")

    if safe_trigger == "turn_end" and safe_turn_index is None:
        structural_reasons.append("turn_index_required_for_turn_end")
    if safe_trigger == "turn_end" and safe_source_event_kind != "turn":
        structural_reasons.append("turn_end_source_event_kind_mismatch")
    if safe_trigger == "explicit_memory_request" and safe_source_event_kind not in {
        "turn",
        "manual_import",
    }:
        structural_reasons.append("explicit_request_source_event_kind_unsupported")

    if safe_runtime_status in _BLOCKED_RUNTIME_TERMINAL_STATUSES:
        structural_reasons.append(f"runtime_status_blocks_admission:{safe_runtime_status}")
    elif safe_runtime_status and safe_runtime_status not in _ALLOWED_RUNTIME_TERMINAL_STATUSES:
        structural_reasons.append("runtime_status_not_admissible")

    if safe_trigger == "turn_end" and safe_visible_finalized is not True:
        structural_reasons.append("visible_response_not_finalized")

    parsed_lineage = _parse_source_lineage(
        source_lineage_artifact,
        expected_namespace=safe_namespace,
        expected_source_event_kind=safe_source_event_kind,
        required=safe_source_count > 0,
    )
    structural_reasons.extend(parsed_lineage["blocked_reasons"])

    hold_reasons: list[str] = []
    if safe_policy_status in _HELD_PERSISTENCE_POLICY_STATUSES:
        hold_reasons.append("persistence_policy_requires_review")
    elif safe_policy_status in _BLOCKED_PERSISTENCE_POLICY_STATUSES:
        structural_reasons.append(
            f"persistence_policy_blocks_admission:{safe_policy_status}"
        )
    elif safe_policy_status and safe_policy_status not in _ALLOWED_PERSISTENCE_POLICY_STATUSES:
        structural_reasons.append("persistence_policy_not_admissible")

    if safe_dry_run_only is False and safe_enqueue_enabled is False:
        structural_reasons.append("enqueue_gate_disabled")

    structural_reasons = _dedupe(structural_reasons)[:_MAX_BLOCKED_REASONS]
    hold_reasons = _dedupe(hold_reasons)[:_MAX_BLOCKED_REASONS]

    status = _admission_status(
        structural_reasons=structural_reasons,
        hold_reasons=hold_reasons,
        source_count=safe_source_count,
        dry_run_only=safe_dry_run_only,
        enqueue_enabled=safe_enqueue_enabled,
    )
    retry_class = _retry_class(status, structural_reasons)
    blocked_reasons = _dedupe(structural_reasons + hold_reasons)[:_MAX_BLOCKED_REASONS]

    projection = {
        "schema_version": _PROJECTION_SCHEMA_VERSION,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "enabled": safe_enabled,
        "dry_run_only": safe_dry_run_only,
        "enqueue_enabled": safe_enqueue_enabled,
        "admission_status": status,
        "trigger_mode": safe_trigger or "unknown",
        "processing_stage": safe_stage or "unknown",
        "source_event_kind": safe_source_event_kind or "unknown",
        "source_count": safe_source_count,
        "source_count_limit": _MAX_SOURCE_COUNT,
        "correlation": {
            "run_id_present": safe_run_id is not None,
            "turn_index_present": safe_turn_index is not None,
            "session_id_present": safe_session_id is not None,
            "namespace_present": safe_namespace is not None,
        },
        "source_reference_valid": parsed_lineage["valid"],
        "visible_response_finalized": safe_visible_finalized,
        "runtime_terminal_status": safe_runtime_status or "unknown",
        "persistence_policy_status": safe_policy_status or "unknown",
        "retry_class": retry_class,
        "blocked_reasons": blocked_reasons,
        "runtime_private_reference_included": False,
        "lineage_fingerprint_included": False,
        "dispatch_idempotency_key_included": False,
        "memory_write_idempotency_key_included": False,
    }

    return {
        "schema_version": _SCHEMA_VERSION,
        "helper_only": True,
        "diagnostics_only": True,
        "read_only": True,
        "enabled": safe_enabled,
        "dry_run_only": safe_dry_run_only,
        "enqueue_enabled": safe_enqueue_enabled,
        "admission_status": status,
        "trigger_mode": safe_trigger or "unknown",
        "processing_stage": safe_stage or "unknown",
        "source_event_kind": safe_source_event_kind or "unknown",
        "run_id": safe_run_id,
        "turn_index": safe_turn_index,
        "session_id": safe_session_id,
        "namespace": safe_namespace,
        "source_count": safe_source_count,
        "source_reference_valid": parsed_lineage["valid"],
        "source_lineage_fingerprint": parsed_lineage["lineage_fingerprint"],
        "visible_response_finalized": safe_visible_finalized,
        "runtime_terminal_status": safe_runtime_status or "unknown",
        "persistence_policy_status": safe_policy_status or "unknown",
        "retry_class": retry_class,
        "blocked_reasons": blocked_reasons,
        "enqueue_eligible": status == "eligible_for_enqueue",
        "queue_io_performed": False,
        "enqueued": False,
        "worker_invoked": False,
        "invokes_slp": False,
        "writes_memory": False,
        "mutates_soul": False,
        "changes_visible_response": False,
        "dispatch_idempotency_key": "",
        "memory_write_idempotency_key": "",
        "projection": projection,
    }


def _parse_source_lineage(
    artifact: Mapping[str, Any] | None,
    *,
    expected_namespace: str | None,
    expected_source_event_kind: str | None,
    required: bool,
) -> dict[str, Any]:
    if artifact is None and not required:
        return {
            "valid": False,
            "lineage_fingerprint": "",
            "blocked_reasons": [],
        }
    if not isinstance(artifact, Mapping):
        return _invalid_lineage("source_lineage_missing")

    unexpected_fields = sorted(set(artifact) - _ALLOWED_LINEAGE_FIELDS)
    if unexpected_fields:
        return _invalid_lineage("source_lineage_unexpected_field")
    if _contains_forbidden_content_key(artifact):
        return _invalid_lineage("source_lineage_content_field_forbidden")
    if artifact.get("schema_version") != _SOURCE_LINEAGE_SCHEMA_VERSION:
        return _invalid_lineage("source_lineage_schema_mismatch")
    if artifact.get("content_free") is not True:
        return _invalid_lineage("source_lineage_not_content_free")
    if artifact.get("content_included") is not False:
        return _invalid_lineage("source_lineage_content_included")
    if artifact.get("raw_text_included") is not False:
        return _invalid_lineage("source_lineage_raw_text_included")
    if artifact.get("valid") is not True:
        return _invalid_lineage("source_lineage_invalid")

    shape = artifact.get("lineage_shape")
    if not isinstance(shape, Mapping):
        return _invalid_lineage("source_lineage_shape_invalid")
    if set(shape) != _ALLOWED_LINEAGE_SHAPE_FIELDS:
        return _invalid_lineage("source_lineage_shape_unexpected_field")
    if any(not isinstance(value, bool) for value in shape.values()):
        return _invalid_lineage("source_lineage_shape_invalid")

    lineage_reasons = artifact.get("blocked_reasons")
    if not isinstance(lineage_reasons, list) or lineage_reasons:
        return _invalid_lineage("source_lineage_blocked_reasons_invalid")

    fingerprint = artifact.get("lineage_fingerprint")
    if not _is_sha256_hex(fingerprint):
        return _invalid_lineage("source_lineage_fingerprint_invalid")

    lineage_namespace, namespace_reasons = _required_token(
        artifact.get("namespace"), "source_lineage_namespace_invalid"
    )
    lineage_event_kind, source_event_reasons = _validated_source_event_kind(
        artifact.get("source_event_kind"),
        invalid_reason="source_lineage_event_kind_invalid",
    )
    reasons = _dedupe(namespace_reasons + source_event_reasons)
    if (
        lineage_namespace
        and expected_namespace
        and lineage_namespace != expected_namespace
    ):
        reasons.append("source_lineage_namespace_mismatch")
    if (
        lineage_event_kind
        and expected_source_event_kind
        and lineage_event_kind != expected_source_event_kind
    ):
        reasons.append("source_lineage_event_kind_mismatch")
    if reasons:
        return {
            "valid": False,
            "lineage_fingerprint": "",
            "blocked_reasons": _dedupe(reasons),
        }
    return {
        "valid": True,
        "lineage_fingerprint": str(fingerprint),
        "blocked_reasons": [],
    }


def _invalid_lineage(reason: str) -> dict[str, Any]:
    return {
        "valid": False,
        "lineage_fingerprint": "",
        "blocked_reasons": [reason],
    }


def _required_bool(value: Any, reason: str) -> tuple[bool, list[str]]:
    if isinstance(value, bool):
        return value, []
    return False, [reason]


def _required_token(value: Any, reason: str) -> tuple[str | None, list[str]]:
    if not isinstance(value, str):
        return None, [reason]
    token = value.strip()
    if not token or len(token) > _MAX_TOKEN_LENGTH or not _is_safe_token(token):
        return None, [reason]
    return token, []


def _optional_token(value: Any, reason: str) -> tuple[str | None, list[str]]:
    if value is None:
        return None, []
    return _required_token(value, reason)


def _optional_non_negative_int(
    value: Any, reason: str
) -> tuple[int | None, list[str]]:
    if value is None:
        return None, []
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None, [reason]
    return value, []


def _bounded_source_count(value: Any) -> tuple[int, list[str]]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0, ["source_count_invalid"]
    if value > _MAX_SOURCE_COUNT:
        return _MAX_SOURCE_COUNT, ["source_count_limit_exceeded"]
    return value, []


def _validated_enum(
    value: Any,
    *,
    known: set[str],
    supported: set[str],
    invalid_reason: str,
    unsupported_reason: str,
) -> tuple[str | None, list[str]]:
    token, reasons = _required_token(value, invalid_reason)
    if reasons:
        return None, reasons
    assert token is not None
    if token not in known:
        return None, [invalid_reason]
    if token not in supported:
        return token, [unsupported_reason]
    return token, []


def _validated_source_event_kind(
    value: Any,
    *,
    invalid_reason: str = "source_event_kind_invalid",
) -> tuple[str | None, list[str]]:
    token, reasons = _required_token(value, invalid_reason)
    if reasons:
        return None, reasons
    assert token is not None
    if token not in _KNOWN_SOURCE_EVENT_KINDS:
        return None, [invalid_reason]
    return token, []


def _validated_runtime_status(value: Any) -> tuple[str | None, list[str]]:
    token, reasons = _required_token(value, "runtime_terminal_status_invalid")
    if reasons:
        return None, reasons
    assert token is not None
    if token not in _KNOWN_RUNTIME_TERMINAL_STATUSES:
        return None, ["runtime_terminal_status_invalid"]
    return token, []


def _validated_policy_status(value: Any) -> tuple[str | None, list[str]]:
    token, reasons = _required_token(value, "persistence_policy_status_invalid")
    if reasons:
        return None, reasons
    assert token is not None
    if token not in _KNOWN_PERSISTENCE_POLICY_STATUSES:
        return None, ["persistence_policy_status_invalid"]
    return token, []


def _admission_status(
    *,
    structural_reasons: Sequence[str],
    hold_reasons: Sequence[str],
    source_count: int,
    dry_run_only: bool,
    enqueue_enabled: bool,
) -> str:
    if structural_reasons:
        return "blocked"
    if hold_reasons:
        return "held"
    if source_count == 0:
        return "skipped"
    if dry_run_only or not enqueue_enabled:
        return "admitted_dry_run"
    return "eligible_for_enqueue"


def _retry_class(status: str, reasons: Sequence[str]) -> str:
    if status == "held":
        return "policy_hold"
    if status in {"admitted_dry_run", "eligible_for_enqueue"}:
        return "not_dispatched"
    if status == "skipped":
        return "not_applicable"
    if any(
        reason.startswith("runtime_status_blocks_admission:")
        and reason.endswith(("failed", "recovery_pending", "unresolved_recovery"))
        for reason in reasons
    ):
        return "retry_requires_recovery"
    return "non_retryable"


def _contains_forbidden_content_key(value: Any) -> bool:
    forbidden_fragments = {
        "text",
        "content",
        "prompt",
        "message",
        "snippet",
        "summary",
        "page",
        "patch",
        "soul",
        "payload",
        "candidate",
        "path",
        "idempotency",
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized not in {
                "content_free",
                "content_included",
                "raw_text_included",
            } and any(fragment in normalized for fragment in forbidden_fragments):
                return True
            if _contains_forbidden_content_key(item):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_forbidden_content_key(item) for item in value)
    return False


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _is_safe_token(value: str) -> bool:
    return all(
        char.isascii()
        and (char.isalnum() or char in {"-", "_", ".", ":", "/"})
        for char in value
    )


def _dedupe(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
