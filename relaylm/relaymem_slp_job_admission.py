"""Phase 6-A1 helper-only RelaySLP deferred-job admission preflight."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_SCHEMA_VERSION = "relaymem.slp_job_admission_preflight.v0"
_PROJECTION_SCHEMA_VERSION = "relaymem.slp_job_admission_projection.v0"
_SOURCE_LINEAGE_SCHEMA_VERSION = "relaymem.primary_source_lineage.v0"
_TRIGGERS = {
    "turn_end",
    "explicit_memory_request",
    "session_end",
    "communication_end",
    "scheduled_consolidation",
    "recovery_followup",
    "lab_memory_operation",
}
_SUPPORTED_TRIGGERS = {"turn_end", "explicit_memory_request"}
_STAGES = {
    "primary_formation",
    "primary_write_preflight",
    "secondary_consolidation",
    "memory_operation",
    "lint",
}
_SUPPORTED_STAGES = {"primary_formation", "primary_write_preflight"}
_EVENT_KINDS = {"turn", "session", "communication", "manual_import"}
_RUNTIME_STATUSES = {
    "completed",
    "succeeded",
    "idle",
    "blocked",
    "failed",
    "waiting_user",
    "recovery_pending",
    "unresolved_recovery",
}
_BLOCKED_RUNTIME = {
    "blocked",
    "failed",
    "waiting_user",
    "recovery_pending",
    "unresolved_recovery",
}
_POLICIES = {
    "allowed",
    "free_to_update",
    "review_required",
    "explicit_approval_required",
    "blocked",
    "never_auto_promote",
}
_BLOCKED_POLICIES = {
    "explicit_approval_required",
    "blocked",
    "never_auto_promote",
}
_LINEAGE_FIELDS = {
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
_SHAPE_FIELDS = {
    "source_event_id_present",
    "run_id_present",
    "session_id_present",
    "turn_index_present",
}
_MAX_TOKEN = 128
_MAX_SOURCES = 32
_MAX_REASONS = 32


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
    """Validate bounded metadata without queue I/O, workers, or persistence."""

    enabled, reasons = _bool(enabled, "enabled_invalid")
    dry_run_only, extra = _bool(dry_run_only, "dry_run_only_invalid")
    reasons += extra
    enqueue_enabled, extra = _bool(enqueue_enabled, "enqueue_enabled_invalid")
    reasons += extra
    visible_response_finalized, extra = _bool(
        visible_response_finalized, "visible_response_finalized_invalid"
    )
    reasons += extra

    trigger_mode, extra = _enum(
        trigger_mode,
        _TRIGGERS,
        _SUPPORTED_TRIGGERS,
        "trigger_mode_invalid",
        "trigger_mode_unsupported",
    )
    reasons += extra
    processing_stage, extra = _enum(
        processing_stage,
        _STAGES,
        _SUPPORTED_STAGES,
        "processing_stage_invalid",
        "processing_stage_unsupported",
    )
    reasons += extra
    run_id, extra = _token(run_id, "run_id_invalid")
    reasons += extra
    session_id, extra = _optional_token(session_id, "session_id_invalid")
    reasons += extra
    namespace, extra = _token(namespace, "namespace_invalid")
    reasons += extra
    turn_index, extra = _index(turn_index, "turn_index_invalid")
    reasons += extra
    source_count, extra = _source_count(source_count)
    reasons += extra
    source_event_kind, extra = _known_token(
        source_event_kind, _EVENT_KINDS, "source_event_kind_invalid"
    )
    reasons += extra
    runtime_terminal_status, extra = _known_token(
        runtime_terminal_status, _RUNTIME_STATUSES, "runtime_terminal_status_invalid"
    )
    reasons += extra
    persistence_policy_status, extra = _known_token(
        persistence_policy_status, _POLICIES, "persistence_policy_status_invalid"
    )
    reasons += extra

    if not enabled:
        reasons.append("feature_disabled")
    if trigger_mode == "turn_end":
        if turn_index is None:
            reasons.append("turn_index_required_for_turn_end")
        if source_event_kind != "turn":
            reasons.append("turn_end_source_event_kind_mismatch")
        if not visible_response_finalized:
            reasons.append("visible_response_not_finalized")
    if (
        trigger_mode == "explicit_memory_request"
        and source_event_kind not in {"turn", "manual_import"}
    ):
        reasons.append("explicit_request_source_event_kind_unsupported")
    if runtime_terminal_status in _BLOCKED_RUNTIME:
        reasons.append(f"runtime_status_blocks_admission:{runtime_terminal_status}")

    lineage = _parse_lineage(
        source_lineage_artifact,
        namespace,
        source_event_kind,
        required=source_count > 0,
    )
    reasons += lineage["blocked_reasons"]

    hold_reasons: list[str] = []
    if persistence_policy_status == "review_required":
        hold_reasons.append("persistence_policy_requires_review")
    elif persistence_policy_status in _BLOCKED_POLICIES:
        reasons.append(
            f"persistence_policy_blocks_admission:{persistence_policy_status}"
        )
    if not dry_run_only and not enqueue_enabled:
        reasons.append("enqueue_gate_disabled")

    reasons = _dedupe(reasons)[:_MAX_REASONS]
    hold_reasons = _dedupe(hold_reasons)[:_MAX_REASONS]
    status = _status(reasons, hold_reasons, source_count, dry_run_only, enqueue_enabled)
    blocked_reasons = _dedupe(reasons + hold_reasons)[:_MAX_REASONS]
    retry_class = _retry_class(status, reasons)

    projection = {
        "schema_version": _PROJECTION_SCHEMA_VERSION,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "enabled": enabled,
        "dry_run_only": dry_run_only,
        "enqueue_enabled": enqueue_enabled,
        "admission_status": status,
        "trigger_mode": trigger_mode or "unknown",
        "processing_stage": processing_stage or "unknown",
        "source_event_kind": source_event_kind or "unknown",
        "source_count": source_count,
        "source_count_limit": _MAX_SOURCES,
        "correlation": {
            "run_id_present": run_id is not None,
            "turn_index_present": turn_index is not None,
            "session_id_present": session_id is not None,
            "namespace_present": namespace is not None,
        },
        "source_reference_valid": lineage["valid"],
        "visible_response_finalized": visible_response_finalized,
        "runtime_terminal_status": runtime_terminal_status or "unknown",
        "persistence_policy_status": persistence_policy_status or "unknown",
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
        "enabled": enabled,
        "dry_run_only": dry_run_only,
        "enqueue_enabled": enqueue_enabled,
        "admission_status": status,
        "trigger_mode": trigger_mode or "unknown",
        "processing_stage": processing_stage or "unknown",
        "source_event_kind": source_event_kind or "unknown",
        "run_id": run_id,
        "turn_index": turn_index,
        "session_id": session_id,
        "namespace": namespace,
        "source_count": source_count,
        "source_reference_valid": lineage["valid"],
        "source_lineage_fingerprint": lineage["lineage_fingerprint"],
        "visible_response_finalized": visible_response_finalized,
        "runtime_terminal_status": runtime_terminal_status or "unknown",
        "persistence_policy_status": persistence_policy_status or "unknown",
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


def _parse_lineage(
    artifact: Mapping[str, Any] | None,
    namespace: str | None,
    event_kind: str | None,
    *,
    required: bool,
) -> dict[str, Any]:
    if artifact is None and not required:
        return _invalid_lineage(None)
    if not isinstance(artifact, Mapping):
        return _invalid_lineage("source_lineage_missing")
    if set(artifact) - _LINEAGE_FIELDS:
        return _invalid_lineage("source_lineage_unexpected_field")
    checks = (
        ("schema_version", _SOURCE_LINEAGE_SCHEMA_VERSION, "source_lineage_schema_mismatch"),
        ("content_free", True, "source_lineage_not_content_free"),
        ("content_included", False, "source_lineage_content_included"),
        ("raw_text_included", False, "source_lineage_raw_text_included"),
        ("valid", True, "source_lineage_invalid"),
    )
    for field, expected, reason in checks:
        if artifact.get(field) != expected:
            return _invalid_lineage(reason)

    # Validate fixed containers before values; never recursively walk caller metadata.
    shape = artifact.get("lineage_shape")
    if not isinstance(shape, Mapping):
        return _invalid_lineage("source_lineage_shape_invalid")
    if set(shape) != _SHAPE_FIELDS:
        return _invalid_lineage("source_lineage_shape_unexpected_field")
    if any(type(value) is not bool for value in shape.values()):
        return _invalid_lineage("source_lineage_shape_invalid")
    upstream_reasons = artifact.get("blocked_reasons")
    if type(upstream_reasons) is not list or upstream_reasons:
        return _invalid_lineage("source_lineage_blocked_reasons_invalid")

    fingerprint = artifact.get("lineage_fingerprint")
    if not _sha256(fingerprint):
        return _invalid_lineage("source_lineage_fingerprint_invalid")
    upstream_namespace, reasons = _token(
        artifact.get("namespace"), "source_lineage_namespace_invalid"
    )
    upstream_kind, extra = _known_token(
        artifact.get("source_event_kind"),
        _EVENT_KINDS,
        "source_lineage_event_kind_invalid",
    )
    reasons += extra
    if upstream_kind and not _shape_has_identity(upstream_kind, shape):
        reasons.append("source_lineage_missing")
    if upstream_namespace and namespace and upstream_namespace != namespace:
        reasons.append("source_lineage_namespace_mismatch")
    if upstream_kind and event_kind and upstream_kind != event_kind:
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


def _shape_has_identity(kind: str, shape: Mapping[str, Any]) -> bool:
    if shape.get("source_event_id_present") is True:
        return True
    run_or_session = (
        shape.get("run_id_present") is True
        or shape.get("session_id_present") is True
    )
    if kind == "turn":
        return shape.get("turn_index_present") is True and run_or_session
    if kind == "session":
        return run_or_session
    return False


def _invalid_lineage(reason: str | None) -> dict[str, Any]:
    return {
        "valid": False,
        "lineage_fingerprint": "",
        "blocked_reasons": [] if reason is None else [reason],
    }


def _bool(value: Any, reason: str) -> tuple[bool, list[str]]:
    return (value, []) if type(value) is bool else (False, [reason])


def _token(value: Any, reason: str) -> tuple[str | None, list[str]]:
    if not isinstance(value, str):
        return None, [reason]
    value = value.strip()
    safe = value and len(value) <= _MAX_TOKEN and all(
        char.isascii() and (char.isalnum() or char in "-_.:/") for char in value
    )
    return (value, []) if safe else (None, [reason])


def _optional_token(value: Any, reason: str) -> tuple[str | None, list[str]]:
    return (None, []) if value is None else _token(value, reason)


def _known_token(
    value: Any, known: set[str], reason: str
) -> tuple[str | None, list[str]]:
    value, reasons = _token(value, reason)
    if reasons or value not in known:
        return None, [reason]
    return value, []


def _enum(
    value: Any,
    known: set[str],
    supported: set[str],
    invalid: str,
    unsupported: str,
) -> tuple[str | None, list[str]]:
    value, reasons = _known_token(value, known, invalid)
    if reasons:
        return None, reasons
    return (value, []) if value in supported else (value, [unsupported])


def _index(value: Any, reason: str) -> tuple[int | None, list[str]]:
    if value is None:
        return None, []
    return (value, []) if type(value) is int and value >= 0 else (None, [reason])


def _source_count(value: Any) -> tuple[int, list[str]]:
    if type(value) is not int or value < 0:
        return 0, ["source_count_invalid"]
    if value > _MAX_SOURCES:
        return _MAX_SOURCES, ["source_count_limit_exceeded"]
    return value, []


def _status(
    reasons: Sequence[str],
    holds: Sequence[str],
    count: int,
    dry_run: bool,
    enqueue: bool,
) -> str:
    if reasons:
        return "blocked"
    if holds:
        return "held"
    if count == 0:
        return "skipped"
    return "admitted_dry_run" if dry_run or not enqueue else "eligible_for_enqueue"


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


def _sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _dedupe(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
