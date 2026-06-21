"""Phase 6-B2 atomic durable RelaySLP enqueue helper.

This helper consumes only an exact successful Phase 6-B1 result and its exact
runtime-private durable-job candidate.  It never invokes a worker, RelaySLP,
RelayMEM apply, or RelaySOUL mutation.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import secrets
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relaymem_slp_dispatch_preflight import (
    RelayMEMSLPDispatchPreflightResult,
    RelayMEMSLPDurableJobCandidate,
)

_RESULT_SCHEMA = "relaymem.slp_durable_enqueue.v0"
_DURABLE_JOB_SCHEMA = "relaymem.slp_durable_job.v0"
_PROJECTION_SCHEMA = "relaymem.slp_queue_status_projection.v0"
_SOURCE_RESULT_SCHEMA = "relaymem.slp_dispatch_preflight.v0"
_DISPATCH_KEY_VERSION = "relaymem.slp_dispatch_key.v0"
_JOB_ID_VERSION = "relaymem.slp_job_id.v0"
_DISPATCH_KEY_PREFIX = "slp-dispatch-v0:"
_JOB_ID_PREFIX = "slp-job-v0:"
_FILENAME_PREFIX = "slp-dispatch-v0-"
_MAX_RECORD_BYTES = 32 * 1024
_MAX_TOKEN = 128
_MAX_REASONS = 32
_MAX_SOURCES = 32

_B1_RESULT_FIELDS = {
    "schema_version", "helper_only", "diagnostics_only", "read_only", "enabled",
    "dry_run_only", "status", "source_candidate_valid", "response_finalized",
    "durable_job_count", "durable_job_created", "durable_job",
    "queue_io_performed", "enqueue_attempted", "enqueue_applied",
    "duplicate_detected", "worker_invoked", "invokes_slp", "writes_memory",
    "mutates_soul", "changes_visible_response", "blocked_reasons",
}
_DURABLE_JOB_FIELDS = {
    "schema_version", "job_id", "dispatch_idempotency_key", "dispatch_key_version",
    "candidate_schema_version", "candidate_kind", "trigger_mode", "processing_stage",
    "source_event_kind", "run_id", "turn_index", "session_id", "namespace",
    "source_count", "source_lineage_fingerprint", "source_admission_status",
    "runtime_terminal_status", "persistence_policy_status", "state",
    "record_revision", "created_at", "updated_at", "attempt_count",
    "claim_generation", "claim_owner", "lease_token", "lease_acquired_at",
    "lease_expires_at", "retry_class", "retry_not_before", "failure_class",
    "terminal_reason_id",
}
_IDENTITY_FIELDS = (
    "dispatch_key_version", "candidate_schema_version", "candidate_kind",
    "trigger_mode", "processing_stage", "source_event_kind", "run_id",
    "turn_index", "session_id", "namespace", "source_count",
    "source_lineage_fingerprint",
)
_ALLOWED_STAGES = ("primary_formation", "primary_write_preflight")
_ALLOWED_ADMISSION_STATUSES = ("admitted_dry_run", "eligible_for_enqueue")
_ALLOWED_RUNTIME_STATUSES = ("completed", "succeeded", "idle")
_ALLOWED_POLICY_STATUSES = ("allowed", "free_to_update")

RelayMEMSLPDurableEnqueueStatus = Literal[
    "disabled",
    "invalid_input",
    "blocked",
    "dry_run_ready",
    "enqueued_new",
    "duplicate_existing",
    "blocked_collision",
    "blocked_corrupt",
    "write_failed",
]
RelayMEMSLPDurableEnqueueOutcome = Literal[
    "enqueued_new",
    "duplicate_existing",
    "blocked_collision",
    "blocked_corrupt",
    "write_failed",
]


@dataclass(frozen=True)
class RelayMEMSLPDurableEnqueueResult:
    """Runtime-private B2 result with a content-free public projection."""

    status: RelayMEMSLPDurableEnqueueStatus
    outcome: RelayMEMSLPDurableEnqueueOutcome | None
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    source_valid: bool
    response_finalized: bool
    queue_io_performed: bool
    enqueue_attempted: bool
    enqueue_applied: bool
    duplicate_detected: bool
    durability_confirmed: bool
    cleanup_complete: bool
    durable_record: dict[str, object] | None
    blocked_reasons: tuple[str, ...]

    def to_runtime_dict(self) -> dict[str, object]:
        return {
            "schema_version": _RESULT_SCHEMA,
            "helper_only": True,
            "runtime_private_record": True,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "status": self.status,
            "outcome": self.outcome,
            "source_valid": self.source_valid,
            "response_finalized": self.response_finalized,
            "queue_io_performed": self.queue_io_performed,
            "enqueue_attempted": self.enqueue_attempted,
            "enqueue_applied": self.enqueue_applied,
            "duplicate_detected": self.duplicate_detected,
            "durability_confirmed": self.durability_confirmed,
            "cleanup_complete": self.cleanup_complete,
            "durable_record": dict(self.durable_record) if self.durable_record else None,
            "worker_invoked": False,
            "invokes_slp": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
            "blocked_reasons": list(self.blocked_reasons),
        }

    def to_log_dict(self) -> dict[str, object]:
        record = self.durable_record
        return {
            "schema_version": _PROJECTION_SCHEMA,
            "status": self.status,
            "state": record.get("state") if record else None,
            "trigger_mode": record.get("trigger_mode") if record else None,
            "processing_stage": record.get("processing_stage") if record else None,
            "source_event_kind": record.get("source_event_kind") if record else None,
            "source_count": record.get("source_count", 0) if record else 0,
            "attempt_count": record.get("attempt_count", 0) if record else 0,
            "retry_class": record.get("retry_class") if record else None,
            "response_finalized": self.response_finalized,
            "enqueue_attempted": self.enqueue_attempted,
            "enqueue_applied": self.enqueue_applied,
            "duplicate_detected": self.duplicate_detected,
            "claim_active": False,
            "lease_present": False,
            "terminal": False,
            "failure_class": record.get("failure_class", "none") if record else "none",
            "blocked_reason_ids": list(self.blocked_reasons),
        }


def enqueue_relaymem_slp_durable_job(
    preflight_result: object,
    *,
    queue_root: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> RelayMEMSLPDurableEnqueueResult:
    """Inspect or atomically create one durable RelaySLP queue record."""

    enabled_value, enabled_errors = _strict_bool(enabled, "enabled_invalid")
    dry_run_value, dry_run_errors = _strict_bool(dry_run_only, "dry_run_only_invalid")
    apply_value, apply_errors = _strict_bool(apply_enabled, "apply_enabled_invalid")
    gate_errors = _dedupe((*enabled_errors, *dry_run_errors, *apply_errors))
    if gate_errors:
        return _result(
            "invalid_input", None, enabled_value, dry_run_value, apply_value,
            False, False, False, False, False, False, False, True, None, gate_errors,
        )
    if not enabled_value:
        return _result(
            "disabled", None, False, dry_run_value, apply_value,
            False, False, False, False, False, False, False, True, None, (),
        )

    source, candidate, source_errors = _validate_preflight_result(preflight_result)
    if source is None or candidate is None:
        return _result(
            "invalid_input", None, True, dry_run_value, apply_value,
            False, False, False, False, False, False, False, True, None, source_errors,
        )

    root_fd, root_errors = _open_queue_root(queue_root)
    if root_fd is None:
        return _result(
            "write_failed", "write_failed", True, dry_run_value, apply_value,
            True, True, False, bool(apply_value and not dry_run_value), False,
            False, False, True, candidate.to_runtime_dict(), root_errors,
        )

    try:
        apply_requested = bool(apply_value and not dry_run_value)
        return _inspect_or_enqueue(
            root_fd=root_fd,
            source=source,
            candidate=candidate,
            enabled=True,
            dry_run_only=dry_run_value,
            apply_enabled=apply_value,
            apply_requested=apply_requested,
        )
    finally:
        os.close(root_fd)


def build_relaymem_slp_durable_enqueue_node_result(
    result: RelayMEMSLPDurableEnqueueResult,
) -> PipelineNodeResult:
    """Build the content-free Phase 6-B2 diagnostics projection."""

    node_status = {
        "disabled": "skipped",
        "invalid_input": "failed",
        "blocked": "blocked",
        "blocked_collision": "blocked",
        "blocked_corrupt": "blocked",
        "write_failed": "failed",
    }.get(result.status, "diagnostic_only")
    return build_pipeline_node_result(
        node_name="relaymem_slp_durable_enqueue",
        status=node_status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=result.to_log_dict(),
        artifacts=[{
            "artifact_name": "relaymem_slp_durable_queue_record",
            "schema_version": _DURABLE_JOB_SCHEMA,
            "present": result.durable_record is not None,
            "content_free": True,
            "runtime_private": True,
            "record_omitted": True,
            "dispatch_idempotency_key_included": False,
            "job_id_included": False,
            "queue_path_included": False,
            "timestamps_included": False,
            "queue_io_performed": result.queue_io_performed,
            "enqueue_attempted": result.enqueue_attempted,
            "enqueue_applied": result.enqueue_applied,
            "duplicate_detected": result.duplicate_detected,
            "worker_invoked": False,
            "writes_memory": False,
        }],
    )


def _validate_preflight_result(
    value: object,
) -> tuple[
    RelayMEMSLPDispatchPreflightResult | None,
    RelayMEMSLPDurableJobCandidate | None,
    tuple[str, ...],
]:
    if type(value) is not RelayMEMSLPDispatchPreflightResult:
        return None, None, ("exact_b1_preflight_result_required",)
    source = value
    if type(source.durable_job) is not RelayMEMSLPDurableJobCandidate:
        return None, None, ("exact_b1_durable_job_candidate_required",)
    if type(source.blocked_reasons) is not tuple:
        return None, None, ("b1_blocked_reasons_invalid",)
    try:
        runtime = source.to_runtime_dict()
        candidate_runtime = source.durable_job.to_runtime_dict()
    except (AttributeError, KeyError, TypeError, ValueError):
        return None, None, ("b1_preflight_runtime_shape_invalid",)
    if not isinstance(runtime, Mapping):
        return None, None, ("b1_preflight_runtime_shape_invalid",)
    if len(runtime) != len(_B1_RESULT_FIELDS) or set(runtime) != _B1_RESULT_FIELDS:
        return None, None, ("b1_preflight_runtime_shape_mismatch",)
    if runtime.get("schema_version") != _SOURCE_RESULT_SCHEMA:
        return None, None, ("b1_preflight_schema_mismatch",)
    for field in ("helper_only", "diagnostics_only", "read_only"):
        if runtime.get(field) is not True:
            return None, None, (f"b1_preflight_{field}_invalid",)
    if (
        source.status != "dry_run_ready"
        or runtime.get("status") != "dry_run_ready"
        or source.enabled is not True
        or runtime.get("enabled") is not True
        or source.dry_run_only is not True
        or runtime.get("dry_run_only") is not True
        or source.source_candidate_valid is not True
        or runtime.get("source_candidate_valid") is not True
        or source.response_finalized is not True
        or runtime.get("response_finalized") is not True
    ):
        return None, None, ("b1_preflight_not_eligible",)
    if source.blocked_reasons or runtime.get("blocked_reasons") != []:
        return None, None, ("b1_blocked_reasons_not_empty",)
    if source.durable_job_count != 1 or source.durable_job_created is not True:
        return None, None, ("b1_durable_job_cardinality_invalid",)
    if (
        type(runtime.get("durable_job_count")) is not int
        or runtime.get("durable_job_count") != 1
        or runtime.get("durable_job_created") is not True
    ):
        return None, None, ("b1_runtime_durable_job_cardinality_invalid",)
    for field in (
        "queue_io_performed", "enqueue_attempted", "enqueue_applied",
        "duplicate_detected", "worker_invoked", "invokes_slp", "writes_memory",
        "mutates_soul", "changes_visible_response",
    ):
        if runtime.get(field) is not False:
            return None, None, (f"b1_preflight_{field}_invalid",)
    candidate, candidate_errors = _validate_candidate(source.durable_job, allow_timestamps=False)
    if candidate is None:
        return None, None, candidate_errors
    if runtime.get("durable_job") != candidate_runtime:
        return None, None, ("b1_durable_job_runtime_mismatch",)
    return source, candidate, ()


def _validate_candidate(
    value: object,
    *,
    allow_timestamps: bool,
) -> tuple[RelayMEMSLPDurableJobCandidate | None, tuple[str, ...]]:
    if type(value) is not RelayMEMSLPDurableJobCandidate:
        return None, ("exact_b1_durable_job_candidate_required",)
    candidate = value
    try:
        runtime = candidate.to_runtime_dict()
    except (AttributeError, KeyError, TypeError, ValueError):
        return None, ("b1_durable_job_runtime_shape_invalid",)
    errors = _validate_record_mapping(runtime, expected=None, allow_timestamps=allow_timestamps)
    if errors:
        return None, errors
    return candidate, ()


def _validate_record_mapping(
    runtime: object,
    *,
    expected: Mapping[str, object] | None,
    allow_timestamps: bool,
) -> tuple[str, ...]:
    if not isinstance(runtime, Mapping):
        return ("durable_job_shape_invalid",)
    if len(runtime) != len(_DURABLE_JOB_FIELDS) or set(runtime) != _DURABLE_JOB_FIELDS:
        return ("durable_job_shape_mismatch",)
    if runtime.get("schema_version") != _DURABLE_JOB_SCHEMA:
        return ("durable_job_schema_mismatch",)
    if runtime.get("dispatch_key_version") != _DISPATCH_KEY_VERSION:
        return ("durable_job_dispatch_key_version_invalid",)
    if runtime.get("candidate_schema_version") != "relaymem.slp_enqueue_candidate.v0":
        return ("durable_job_candidate_schema_invalid",)
    if runtime.get("candidate_kind") != "relayslp_deferred_job":
        return ("durable_job_candidate_kind_invalid",)
    if runtime.get("trigger_mode") != "turn_end":
        return ("durable_job_trigger_mode_invalid",)
    if runtime.get("processing_stage") not in _ALLOWED_STAGES:
        return ("durable_job_processing_stage_invalid",)
    if runtime.get("source_event_kind") != "turn":
        return ("durable_job_source_event_kind_invalid",)
    for field in (
        "run_id", "namespace", "source_admission_status", "runtime_terminal_status",
        "persistence_policy_status",
    ):
        if not _is_token(runtime.get(field)):
            return (f"durable_job_{field}_invalid",)
    session_id = runtime.get("session_id")
    if session_id is not None and not _is_token(session_id):
        return ("durable_job_session_id_invalid",)
    if type(runtime.get("turn_index")) is not int or runtime["turn_index"] < 0:
        return ("durable_job_turn_index_invalid",)
    if type(runtime.get("source_count")) is not int or not 1 <= runtime["source_count"] <= _MAX_SOURCES:
        return ("durable_job_source_count_invalid",)
    if not _is_sha256(runtime.get("source_lineage_fingerprint")):
        return ("durable_job_lineage_invalid",)
    if runtime.get("source_admission_status") not in _ALLOWED_ADMISSION_STATUSES:
        return ("durable_job_source_admission_status_invalid",)
    if runtime.get("runtime_terminal_status") not in _ALLOWED_RUNTIME_STATUSES:
        return ("durable_job_runtime_terminal_status_invalid",)
    if runtime.get("persistence_policy_status") not in _ALLOWED_POLICY_STATUSES:
        return ("durable_job_persistence_policy_status_invalid",)
    dispatch_key = runtime.get("dispatch_idempotency_key")
    job_id = runtime.get("job_id")
    if not _has_prefixed_digest(dispatch_key, _DISPATCH_KEY_PREFIX):
        return ("durable_job_dispatch_key_invalid",)
    if dispatch_key != _derive_dispatch_key(runtime):
        return ("durable_job_dispatch_key_mismatch",)
    if not _has_prefixed_digest(job_id, _JOB_ID_PREFIX):
        return ("durable_job_job_id_invalid",)
    if job_id != _derive_job_id(str(dispatch_key)):
        return ("durable_job_job_id_mismatch",)
    if runtime.get("state") != "queued":
        return ("durable_job_state_invalid",)
    for field in ("record_revision", "attempt_count", "claim_generation"):
        if type(runtime.get(field)) is not int or runtime[field] != 0:
            return (f"durable_job_{field}_invalid",)
    if runtime.get("claim_owner") != "" or runtime.get("lease_token") != "":
        return ("durable_job_claim_identity_invalid",)
    for field in ("lease_acquired_at", "lease_expires_at", "retry_not_before"):
        if runtime.get(field) is not None:
            return (f"durable_job_{field}_invalid",)
    if runtime.get("retry_class") != "unclassified":
        return ("durable_job_retry_class_invalid",)
    if runtime.get("failure_class") != "none":
        return ("durable_job_failure_class_invalid",)
    if runtime.get("terminal_reason_id") != "":
        return ("durable_job_terminal_reason_invalid",)
    created_at = runtime.get("created_at")
    updated_at = runtime.get("updated_at")
    if allow_timestamps:
        if not _is_utc_timestamp(created_at) or updated_at != created_at:
            return ("durable_job_timestamp_invalid",)
    elif created_at is not None or updated_at is not None:
        return ("durable_job_timestamp_prepopulated",)
    if expected is not None:
        if runtime.get("dispatch_idempotency_key") != expected.get("dispatch_idempotency_key"):
            return ("durable_job_dispatch_key_mismatch",)
    return ()


def _inspect_or_enqueue(
    *,
    root_fd: int,
    source: RelayMEMSLPDispatchPreflightResult,
    candidate: RelayMEMSLPDurableJobCandidate,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    apply_requested: bool,
) -> RelayMEMSLPDurableEnqueueResult:
    candidate_record = candidate.to_runtime_dict()
    filename = _record_filename(candidate.dispatch_idempotency_key)
    existing = _inspect_existing(root_fd, filename, candidate_record)
    if existing["classification"] != "absent":
        return _classification_result(
            existing,
            enabled=enabled,
            dry_run_only=dry_run_only,
            apply_enabled=apply_enabled,
            source=source,
            fallback_record=candidate_record,
            enqueue_attempted=apply_requested,
        )
    if not apply_requested:
        return _result(
            "dry_run_ready", None, enabled, dry_run_only, apply_enabled,
            True, source.response_finalized, True, False, False, False,
            False, True, candidate_record, (),
        )
    timestamp = _utc_now()
    durable_record = dict(candidate_record)
    durable_record["created_at"] = timestamp
    durable_record["updated_at"] = timestamp
    return _atomic_create(
        root_fd=root_fd,
        filename=filename,
        expected_candidate=candidate_record,
        durable_record=durable_record,
        source=source,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
    )


def _inspect_existing(
    root_fd: int,
    filename: str,
    expected_candidate: Mapping[str, object],
) -> dict[str, object]:
    try:
        before = os.stat(filename, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return {"classification": "absent", "record": None, "reasons": ()}
    except OSError:
        return _classified("write_failed", None, "queue_record_unreadable")
    if stat.S_ISLNK(before.st_mode):
        return _classified("blocked_corrupt", None, "queue_record_symlink_blocked")
    if not stat.S_ISREG(before.st_mode):
        return _classified("blocked_corrupt", None, "queue_record_unexpected_file_type")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(filename, flags, dir_fd=root_fd)
    except FileNotFoundError:
        return {"classification": "absent", "record": None, "reasons": ()}
    except OSError:
        return _classified("write_failed", None, "queue_record_unreadable")
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return _classified("blocked_corrupt", None, "queue_record_unexpected_file_type")
        if (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino):
            return _classified("blocked_corrupt", None, "queue_record_changed_during_read")
        data = _read_bounded(fd)
        if data is None:
            return _classified("blocked_corrupt", None, "queue_record_size_exceeded")
        record, decode_error = _decode_canonical_record(data)
        if decode_error:
            return _classified("blocked_corrupt", None, decode_error)
        try:
            current = os.stat(filename, dir_fd=root_fd, follow_symlinks=False)
        except OSError:
            return _classified("blocked_corrupt", None, "queue_record_changed_during_read")
        if (
            stat.S_ISLNK(current.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino)
        ):
            return _classified("blocked_corrupt", None, "queue_record_changed_during_read")
        assert record is not None
        if record.get("dispatch_idempotency_key") != expected_candidate.get("dispatch_idempotency_key"):
            return _classified("blocked_corrupt", record, "queue_record_key_path_mismatch")
        if any(record.get(field) != expected_candidate.get(field) for field in _IDENTITY_FIELDS):
            return _classified("blocked_collision", record, "dispatch_identity_collision")
        errors = _validate_record_mapping(record, expected=expected_candidate, allow_timestamps=True)
        if errors:
            return {"classification": "blocked_corrupt", "record": record, "reasons": errors}
        return {"classification": "duplicate_existing", "record": record, "reasons": ()}
    except OSError:
        return _classified("write_failed", None, "queue_record_unreadable")
    finally:
        os.close(fd)


def _atomic_create(
    *,
    root_fd: int,
    filename: str,
    expected_candidate: Mapping[str, object],
    durable_record: Mapping[str, object],
    source: RelayMEMSLPDispatchPreflightResult,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
) -> RelayMEMSLPDurableEnqueueResult:
    data = _canonical_json_bytes(durable_record)
    temp_name = f".relay-slp-{secrets.token_hex(16)}.tmp"
    temp_created = False
    linked = False
    flags = (
        os.O_WRONLY | os.O_CREAT | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        try:
            temp_fd = os.open(temp_name, flags, 0o600, dir_fd=root_fd)
            temp_created = True
        except OSError:
            return _result(
                "write_failed", "write_failed", enabled, dry_run_only, apply_enabled,
                True, source.response_finalized, True, True, False, False,
                False, True, dict(durable_record), ("queue_temp_create_failed",),
            )
        try:
            _write_all(temp_fd, data)
            os.fsync(temp_fd)
            info = os.fstat(temp_fd)
            if info.st_size != len(data):
                raise OSError(errno.EIO, "queue temp size mismatch")
        except OSError:
            return _result(
                "write_failed", "write_failed", enabled, dry_run_only, apply_enabled,
                True, source.response_finalized, True, True, False, False,
                False, True, dict(durable_record), ("queue_temp_write_failed",),
            )
        finally:
            os.close(temp_fd)

        try:
            os.link(
                temp_name,
                filename,
                src_dir_fd=root_fd,
                dst_dir_fd=root_fd,
                follow_symlinks=False,
            )
            linked = True
        except FileExistsError:
            existing = _inspect_existing(root_fd, filename, expected_candidate)
            return _classification_result(
                existing,
                enabled=enabled,
                dry_run_only=dry_run_only,
                apply_enabled=apply_enabled,
                source=source,
                fallback_record=durable_record,
                enqueue_attempted=True,
            )
        except OSError:
            return _result(
                "write_failed", "write_failed", enabled, dry_run_only, apply_enabled,
                True, source.response_finalized, True, True, False, False,
                False, True, dict(durable_record), ("queue_atomic_link_failed",),
            )

        published = _inspect_existing(root_fd, filename, expected_candidate)
        if published["classification"] != "duplicate_existing":
            return _result(
                "write_failed", "write_failed", enabled, dry_run_only, apply_enabled,
                True, source.response_finalized, True, True, True, False,
                False, False, dict(durable_record), ("queue_publish_verification_failed",),
            )
        try:
            os.fsync(root_fd)
        except OSError:
            return _result(
                "write_failed", "write_failed", enabled, dry_run_only, apply_enabled,
                True, source.response_finalized, True, True, True, False,
                False, False, dict(durable_record), ("queue_directory_fsync_failed",),
            )
        cleanup_complete = True
        try:
            os.unlink(temp_name, dir_fd=root_fd)
            temp_created = False
            os.fsync(root_fd)
        except OSError:
            cleanup_complete = False
        return _result(
            "enqueued_new", "enqueued_new", enabled, dry_run_only, apply_enabled,
            True, source.response_finalized, True, True, True, False,
            True, cleanup_complete, dict(durable_record),
            () if cleanup_complete else ("queue_temp_cleanup_failed",),
        )
    finally:
        if temp_created:
            try:
                os.unlink(temp_name, dir_fd=root_fd)
            except OSError:
                pass
        if not linked:
            # The final path was never created by this call.
            pass


def _classification_result(
    classified: Mapping[str, object],
    *,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    source: RelayMEMSLPDispatchPreflightResult,
    fallback_record: Mapping[str, object],
    enqueue_attempted: bool,
) -> RelayMEMSLPDurableEnqueueResult:
    classification = str(classified.get("classification"))
    record = classified.get("record")
    record_mapping = dict(record) if isinstance(record, Mapping) else dict(fallback_record)
    reasons_value = classified.get("reasons")
    reasons = tuple(reasons_value) if isinstance(reasons_value, Sequence) and not isinstance(reasons_value, (str, bytes)) else ()
    if classification == "duplicate_existing":
        return _result(
            "duplicate_existing", "duplicate_existing", enabled, dry_run_only,
            apply_enabled, True, source.response_finalized, True, enqueue_attempted,
            False, True, True, True, record_mapping, reasons,
        )
    if classification == "blocked_collision":
        return _result(
            "blocked_collision", "blocked_collision", enabled, dry_run_only,
            apply_enabled, True, source.response_finalized, True, enqueue_attempted,
            False, False, False, True, record_mapping, reasons,
        )
    if classification == "blocked_corrupt":
        return _result(
            "blocked_corrupt", "blocked_corrupt", enabled, dry_run_only,
            apply_enabled, True, source.response_finalized, True, enqueue_attempted,
            False, False, False, True, record_mapping, reasons,
        )
    return _result(
        "write_failed", "write_failed", enabled, dry_run_only, apply_enabled,
        True, source.response_finalized, True, enqueue_attempted,
        False, False, False, True, record_mapping,
        reasons or ("queue_record_inspection_failed",),
    )


def _open_queue_root(root_path: str | None) -> tuple[int | None, tuple[str, ...]]:
    if type(root_path) is not str:
        return None, ("queue_root_not_configured",)
    if root_path != root_path.strip() or not root_path or _bad_text(root_path):
        return None, ("queue_root_invalid",)
    if not _supports_secure_dirfd():
        return None, ("queue_platform_unsupported",)
    absolute = Path(root_path)
    if not absolute.is_absolute():
        return None, ("queue_root_must_be_absolute",)
    parts = absolute.parts
    if not parts or not absolute.anchor:
        return None, ("queue_root_invalid",)
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(absolute.anchor, flags)
    except OSError:
        return None, ("queue_root_unopenable",)
    for part in parts[1:]:
        try:
            before = os.stat(part, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            os.close(fd)
            return None, ("queue_root_missing",)
        except OSError:
            os.close(fd)
            return None, ("queue_root_unopenable",)
        if stat.S_ISLNK(before.st_mode):
            os.close(fd)
            return None, ("queue_root_symlink_blocked",)
        if not stat.S_ISDIR(before.st_mode):
            os.close(fd)
            return None, ("queue_root_not_directory",)
        try:
            child_fd = os.open(
                part,
                flags | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=fd,
            )
        except OSError:
            os.close(fd)
            return None, ("queue_root_unopenable",)
        try:
            after = os.fstat(child_fd)
            if not stat.S_ISDIR(after.st_mode) or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                os.close(child_fd)
                os.close(fd)
                return None, ("queue_root_changed",)
        except OSError:
            os.close(child_fd)
            os.close(fd)
            return None, ("queue_root_unopenable",)
        os.close(fd)
        fd = child_fd
    return fd, ()


def _record_filename(dispatch_key: str) -> str:
    digest = dispatch_key.removeprefix(_DISPATCH_KEY_PREFIX)
    return f"{_FILENAME_PREFIX}{digest}.json"


def _decode_canonical_record(data: bytes) -> tuple[dict[str, object] | None, str | None]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, "queue_record_malformed_utf8"
    duplicate = False

    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        nonlocal duplicate
        output: dict[str, object] = {}
        for key, value in pairs:
            if key in output:
                duplicate = True
            output[key] = value
        return output

    try:
        value = json.loads(text, object_pairs_hook=object_pairs)
    except (json.JSONDecodeError, RecursionError):
        return None, "queue_record_malformed_json"
    if duplicate:
        return None, "queue_record_duplicate_json_key"
    if not isinstance(value, dict):
        return None, "queue_record_json_not_object"
    if _canonical_json_bytes(value) != data:
        return None, "queue_record_noncanonical_json"
    return value, None


def _read_bounded(fd: int) -> bytes | None:
    chunks: list[bytes] = []
    remaining = _MAX_RECORD_BYTES + 1
    while remaining > 0:
        chunk = os.read(fd, min(4096, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b"".join(chunks)
    return None if len(data) > _MAX_RECORD_BYTES else data


def _write_all(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0:
            raise OSError(errno.EIO, "short write")
        offset += written


def _canonical_json_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _derive_dispatch_key(record: Mapping[str, object]) -> str:
    session_id = record["session_id"]
    canonical_input = [
        ["dispatch_key_version", record["dispatch_key_version"]],
        ["candidate_schema_version", record["candidate_schema_version"]],
        ["candidate_kind", record["candidate_kind"]],
        ["trigger_mode", record["trigger_mode"]],
        ["processing_stage", record["processing_stage"]],
        ["source_event_kind", record["source_event_kind"]],
        ["run_id", record["run_id"]],
        ["turn_index", record["turn_index"]],
        ["session_id_present", session_id is not None],
        ["session_id", session_id if session_id is not None else ""],
        ["namespace", record["namespace"]],
        ["source_count", record["source_count"]],
        ["source_lineage_fingerprint", record["source_lineage_fingerprint"]],
    ]
    encoded = json.dumps(
        canonical_input,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _DISPATCH_KEY_PREFIX + hashlib.sha256(encoded).hexdigest()


def _derive_job_id(dispatch_key: str) -> str:
    encoded = (_JOB_ID_VERSION + "\0" + dispatch_key).encode("utf-8")
    return _JOB_ID_PREFIX + hashlib.sha256(encoded).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _is_utc_timestamp(value: object) -> bool:
    if type(value) is not str or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _strict_bool(value: Any, reason: str) -> tuple[bool, tuple[str, ...]]:
    return (value, ()) if type(value) is bool else (False, (reason,))


def _is_token(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= _MAX_TOKEN
        and value == value.strip()
        and not _bad_text(value)
        and not any(character in value for character in "/\\")
    )


def _is_sha256(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _has_prefixed_digest(value: object, prefix: str) -> bool:
    return type(value) is str and value.startswith(prefix) and _is_sha256(value[len(prefix):])


def _bad_text(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _supports_secure_dirfd() -> bool:
    return all(
        function in os.supports_dir_fd
        for function in (os.open, os.stat, os.link, os.unlink)
    ) and os.stat in os.supports_follow_symlinks


def _classified(classification: str, record: object, reason: str) -> dict[str, object]:
    return {"classification": classification, "record": record, "reasons": (reason,)}


def _result(
    status: RelayMEMSLPDurableEnqueueStatus,
    outcome: RelayMEMSLPDurableEnqueueOutcome | None,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    source_valid: bool,
    response_finalized: bool,
    queue_io_performed: bool,
    enqueue_attempted: bool,
    enqueue_applied: bool,
    duplicate_detected: bool,
    durability_confirmed: bool,
    cleanup_complete: bool,
    durable_record: Mapping[str, object] | None,
    reasons: Sequence[str],
) -> RelayMEMSLPDurableEnqueueResult:
    return RelayMEMSLPDurableEnqueueResult(
        status=status,
        outcome=outcome,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        source_valid=source_valid,
        response_finalized=response_finalized,
        queue_io_performed=queue_io_performed,
        enqueue_attempted=enqueue_attempted,
        enqueue_applied=enqueue_applied,
        duplicate_detected=duplicate_detected,
        durability_confirmed=durability_confirmed,
        cleanup_complete=cleanup_complete,
        durable_record=dict(durable_record) if durable_record is not None else None,
        blocked_reasons=_dedupe(reasons)[:_MAX_REASONS],
    )


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if type(value) is str and value))


__all__ = [
    "RelayMEMSLPDurableEnqueueResult",
    "build_relaymem_slp_durable_enqueue_node_result",
    "enqueue_relaymem_slp_durable_job",
]
