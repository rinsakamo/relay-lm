"""Durable claim-independent protected-source store for Phase 6-C1-5."""
from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ._relaymem_slp_protected_source_artifact import (
    ARTIFACT_SCHEMA,
    CLEANUP_MARKER_SCHEMA,
    artifact_filename,
    artifact_key_digest,
    build_artifact,
    canonical_json_bytes,
    validate_artifact,
)
from ._relaymem_slp_protected_source_fs import (
    acquire_lock,
    atomic_create,
    open_store_root,
    read_artifact,
    release_lock,
    remove_cleanup_marker,
    write_cleanup_marker,
)
from .relaymem_slp_dispatch_preflight import RelayMEMSLPDurableJobCandidate
from .relaymem_slp_durable_enqueue import _validate_candidate as _validate_b2_candidate
from .relaymem_slp_primary_worker_source_registry import _validate_capture_payload
from .relaymem_slp_queue_record import (
    TERMINAL_STATES, bad_text, dedupe, is_token, validate_record_mapping,
)

PROJECTION_SCHEMA = "relaymem.slp_protected_source_store_projection.v0"
DEFAULT_MAX_ARTIFACT_BYTES = 256 * 1024
MAX_ARTIFACT_BYTES_LIMIT = 1024 * 1024
_MAX_REASONS = 32
StoreStatus = Literal[
    "published_new", "duplicate_existing", "loaded", "removed",
    "already_removed", "orphan_removed", "missing", "collision", "corrupt",
    "retryable", "cleanup_required", "blocked",
]


@dataclass(frozen=True, repr=False)
class RelayMEMSLPProtectedSourceStoreResult:
    status: StoreStatus
    durable: bool
    source_available: bool
    duplicate_existing: bool
    cleanup_required: bool
    cleanup_marker_written: bool
    blocked_reasons: tuple[str, ...]
    source_integrity_digest: str | None = field(default=None, repr=False)
    protected_capture: dict[str, object] | None = field(
        default=None, repr=False, compare=False
    )

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPProtectedSourceStoreResult("
            f"status={self.status!r}, durable={self.durable!r}, "
            f"source_available={self.source_available!r}, "
            f"cleanup_required={self.cleanup_required!r}, "
            "protected_content_omitted=True)"
        )

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_text_included": False,
            "raw_messages_included": False,
            "governed_title_included": False,
            "governed_summary_included": False,
            "identifier_values_included": False,
            "namespace_value_included": False,
            "lineage_fingerprint_included": False,
            "source_digest_included": False,
            "path_included": False,
            "exception_text_included": False,
            "status": self.status,
            "durable": self.durable,
            "restart_complete": self.durable and self.source_available,
            "source_available": self.source_available,
            "duplicate_existing": self.duplicate_existing,
            "cleanup_required": self.cleanup_required,
            "cleanup_marker_written": self.cleanup_marker_written,
            "blocked_reason_ids": list(self.blocked_reasons),
        }


class RelayMEMSLPDurableProtectedSourceStore:
    __slots__ = ("_root_path", "_max_artifact_bytes")

    def __init__(
        self, root_path: str, *, max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES
    ) -> None:
        if type(root_path) is not str or not root_path or root_path != root_path.strip():
            raise ValueError("protected_source_root_invalid")
        if bad_text(root_path) or not Path(root_path).is_absolute():
            raise ValueError("protected_source_root_invalid")
        if type(max_artifact_bytes) is not int or not (
            1 <= max_artifact_bytes <= MAX_ARTIFACT_BYTES_LIMIT
        ):
            raise ValueError("protected_source_max_artifact_bytes_invalid")
        self._root_path = root_path
        self._max_artifact_bytes = max_artifact_bytes

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableProtectedSourceStore("
            f"max_artifact_bytes={self._max_artifact_bytes}, "
            "root_omitted=True, runtime_private=True)"
        )

    @property
    def max_artifact_bytes(self) -> int:
        return self._max_artifact_bytes

    def persist(
        self, *, source_payload: object, durable_job: object, character_id: object
    ) -> RelayMEMSLPProtectedSourceStoreResult:
        _, runtime, reasons = _validate_candidate(durable_job)
        if runtime is None:
            return _result("blocked", reasons)
        if not is_token(character_id):
            reasons = dedupe((*reasons, "character_id_invalid"))
        payload, payload_reasons = _validate_capture_payload(source_payload, runtime)
        reasons = dedupe((*reasons, *payload_reasons))
        if reasons or payload is None:
            return _result("blocked", reasons)
        artifact, digest = build_artifact(
            payload, job_id=str(runtime["job_id"]),
            dispatch_key=str(runtime["dispatch_idempotency_key"]),
            character_id=str(character_id),
        )
        try:
            data = canonical_json_bytes(artifact)
        except (TypeError, ValueError, RecursionError, OverflowError):
            return _result("blocked", ("protected_source_artifact_invalid",))
        if len(data) > self._max_artifact_bytes:
            return _result("blocked", ("protected_source_artifact_size_exceeded",))
        root_fd, root_reasons = open_store_root(self._root_path)
        if root_fd is None:
            return _result("retryable", root_reasons)
        try:
            lock_reason = acquire_lock(root_fd, exclusive=True)
            if lock_reason:
                return _result("retryable", (lock_reason,))
            filename = artifact_filename(
                str(runtime["job_id"]), str(runtime["dispatch_idempotency_key"])
            )
            existing, status_value, read_reasons = read_artifact(
                root_fd, filename, max_bytes=self._max_artifact_bytes
            )
            if status_value == "ok" and existing is not None:
                return self._duplicate_or_collision(existing, data, digest)
            if status_value != "missing":
                return _result("corrupt", read_reasons, durable=True)
            write_status, write_reasons = atomic_create(
                root_fd, filename, data, max_bytes=self._max_artifact_bytes
            )
            if write_status == "created":
                return _result(
                    "published_new", (), durable=True, source_available=True,
                    source_integrity_digest=digest,
                )
            if write_status == "exists":
                raced, raced_status, raced_reasons = read_artifact(
                    root_fd, filename, max_bytes=self._max_artifact_bytes
                )
                if raced_status == "ok" and raced is not None:
                    return self._duplicate_or_collision(raced, data, digest)
                return _result("corrupt", raced_reasons, durable=True)
            return _result("retryable", write_reasons)
        finally:
            release_lock(root_fd)
            os.close(root_fd)

    def load_for_claim(
        self, *, claimed_record: object, character_id: object
    ) -> RelayMEMSLPProtectedSourceStoreResult:
        record, reasons = _validate_record(claimed_record, "claimed")
        if not is_token(character_id):
            reasons = dedupe((*reasons, "character_id_invalid"))
        if record is None or reasons:
            return _result("blocked", reasons)
        root_fd, root_reasons = open_store_root(self._root_path)
        if root_fd is None:
            return _result("retryable", root_reasons)
        try:
            lock_reason = acquire_lock(root_fd, exclusive=False)
            if lock_reason:
                return _result("retryable", (lock_reason,))
            filename = artifact_filename(
                str(record["job_id"]), str(record["dispatch_idempotency_key"])
            )
            artifact, status_value, read_reasons = read_artifact(
                root_fd, filename, max_bytes=self._max_artifact_bytes
            )
            if status_value == "missing":
                return _result("missing", ("protected_source_artifact_missing",))
            if status_value != "ok" or artifact is None:
                return _result("corrupt", read_reasons, durable=True)
            payload, digest, artifact_reasons = validate_artifact(
                artifact, expected_record=record,
                expected_character_id=str(character_id),
            )
            if payload is None or digest is None or artifact_reasons:
                return _result(
                    "corrupt", artifact_reasons, durable=True, source_available=True
                )
            return _result(
                "loaded", (), durable=True, source_available=True,
                source_integrity_digest=digest, protected_capture=payload,
            )
        finally:
            release_lock(root_fd)
            os.close(root_fd)

    def cleanup_after_terminal(
        self, *, terminal_record: object, character_id: object
    ) -> RelayMEMSLPProtectedSourceStoreResult:
        record, reasons = _validate_record(terminal_record, None)
        if record is not None and record.get("state") not in TERMINAL_STATES:
            reasons = dedupe((*reasons, "terminal_queue_record_required"))
        if not is_token(character_id):
            reasons = dedupe((*reasons, "character_id_invalid"))
        if record is None or reasons:
            return _result("blocked", reasons)
        root_fd, root_reasons = open_store_root(self._root_path)
        if root_fd is None:
            return _result("cleanup_required", root_reasons, cleanup_required=True)
        filename = artifact_filename(
            str(record["job_id"]), str(record["dispatch_idempotency_key"])
        )
        key_digest = artifact_key_digest(
            str(record["job_id"]), str(record["dispatch_idempotency_key"])
        )
        try:
            lock_reason = acquire_lock(root_fd, exclusive=True)
            if lock_reason:
                return self._cleanup_required(root_fd, key_digest, lock_reason)
            artifact, status_value, read_reasons = read_artifact(
                root_fd, filename, max_bytes=self._max_artifact_bytes
            )
            if status_value == "missing":
                remove_cleanup_marker(root_fd, filename)
                return _result("already_removed", (), durable=True)
            if status_value != "ok" or artifact is None:
                return self._cleanup_required(
                    root_fd, key_digest, "protected_source_cleanup_validation_failed",
                    read_reasons,
                )
            _, _, artifact_reasons = validate_artifact(
                artifact, expected_record=record,
                expected_character_id=str(character_id),
            )
            if artifact_reasons:
                return self._cleanup_required(
                    root_fd, key_digest, "protected_source_cleanup_identity_mismatch",
                    artifact_reasons,
                )
            try:
                os.unlink(filename, dir_fd=root_fd)
                os.fsync(root_fd)
            except OSError:
                return self._cleanup_required(
                    root_fd, key_digest, "protected_source_cleanup_failed"
                )
            remove_cleanup_marker(root_fd, filename)
            return _result("removed", (), durable=True)
        finally:
            release_lock(root_fd)
            os.close(root_fd)

    def discard_unqueued(
        self, *, source_payload: object, durable_job: object, character_id: object
    ) -> RelayMEMSLPProtectedSourceStoreResult:
        _, runtime, reasons = _validate_candidate(durable_job)
        if runtime is None:
            return _result("blocked", reasons)
        payload, payload_reasons = _validate_capture_payload(source_payload, runtime)
        reasons = dedupe((*reasons, *payload_reasons))
        if not is_token(character_id):
            reasons = dedupe((*reasons, "character_id_invalid"))
        if reasons or payload is None:
            return _result("blocked", reasons)
        expected, _ = build_artifact(
            payload, job_id=str(runtime["job_id"]),
            dispatch_key=str(runtime["dispatch_idempotency_key"]),
            character_id=str(character_id),
        )
        root_fd, root_reasons = open_store_root(self._root_path)
        if root_fd is None:
            return _result("cleanup_required", root_reasons, cleanup_required=True)
        try:
            lock_reason = acquire_lock(root_fd, exclusive=True)
            if lock_reason:
                return _result("cleanup_required", (lock_reason,), cleanup_required=True)
            filename = artifact_filename(
                str(runtime["job_id"]), str(runtime["dispatch_idempotency_key"])
            )
            existing, status_value, read_reasons = read_artifact(
                root_fd, filename, max_bytes=self._max_artifact_bytes
            )
            if status_value == "missing":
                return _result("already_removed", (), durable=True)
            if status_value != "ok" or existing is None:
                return _result(
                    "cleanup_required", read_reasons, durable=True,
                    cleanup_required=True,
                )
            if canonical_json_bytes(existing) != canonical_json_bytes(expected):
                return _result(
                    "collision", ("protected_source_orphan_identity_collision",),
                    durable=True, source_available=True,
                )
            try:
                os.unlink(filename, dir_fd=root_fd)
                os.fsync(root_fd)
            except OSError:
                return _result(
                    "cleanup_required", ("protected_source_orphan_cleanup_failed",),
                    durable=True, source_available=True, cleanup_required=True,
                )
            return _result("orphan_removed", (), durable=True)
        finally:
            release_lock(root_fd)
            os.close(root_fd)

    @staticmethod
    def _duplicate_or_collision(
        existing: Mapping[str, object], expected: bytes, digest: str
    ) -> RelayMEMSLPProtectedSourceStoreResult:
        if canonical_json_bytes(existing) == expected:
            return _result(
                "duplicate_existing", (), durable=True, source_available=True,
                duplicate_existing=True, source_integrity_digest=digest,
            )
        return _result(
            "collision", ("protected_source_identity_collision",),
            durable=True, source_available=True,
        )

    @staticmethod
    def _cleanup_required(
        root_fd: int, key_digest: str, reason_id: str,
        reasons: Sequence[str] = (),
    ) -> RelayMEMSLPProtectedSourceStoreResult:
        marker = write_cleanup_marker(root_fd, key_digest, reason_id)
        return _result(
            "cleanup_required", tuple(reasons) or (reason_id,), durable=True,
            source_available=True, cleanup_required=True,
            cleanup_marker_written=marker,
        )


def _validate_candidate(
    value: object,
) -> tuple[RelayMEMSLPDurableJobCandidate | None, dict[str, object] | None, tuple[str, ...]]:
    if type(value) is not RelayMEMSLPDurableJobCandidate:
        return None, None, ("exact_b1_durable_job_candidate_required",)
    validated, reasons = _validate_b2_candidate(value, allow_timestamps=False)
    if validated is None or reasons:
        return None, None, reasons or ("b1_durable_job_invalid",)
    try:
        runtime = validated.to_runtime_dict()
    except (AttributeError, KeyError, TypeError, ValueError):
        return None, None, ("b1_durable_job_runtime_shape_invalid",)
    return (
        (validated, runtime, ())
        if type(runtime) is dict
        else (None, None, ("b1_durable_job_runtime_shape_invalid",))
    )


def _validate_record(
    value: object, required_state: str | None
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("exact_durable_record_required",)
    reasons = validate_record_mapping(value)
    if reasons:
        return None, reasons
    if required_state is not None and value.get("state") != required_state:
        return None, (f"durable_record_{required_state}_required",)
    return value, ()


def _result(
    status: StoreStatus, reasons: Sequence[str], *, durable: bool = False,
    source_available: bool = False, duplicate_existing: bool = False,
    cleanup_required: bool = False, cleanup_marker_written: bool = False,
    source_integrity_digest: str | None = None,
    protected_capture: dict[str, object] | None = None,
) -> RelayMEMSLPProtectedSourceStoreResult:
    return RelayMEMSLPProtectedSourceStoreResult(
        status=status, durable=durable, source_available=source_available,
        duplicate_existing=duplicate_existing, cleanup_required=cleanup_required,
        cleanup_marker_written=cleanup_marker_written,
        blocked_reasons=dedupe(tuple(reasons))[:_MAX_REASONS],
        source_integrity_digest=source_integrity_digest,
        protected_capture=protected_capture,
    )


__all__ = [
    "ARTIFACT_SCHEMA", "CLEANUP_MARKER_SCHEMA", "DEFAULT_MAX_ARTIFACT_BYTES",
    "MAX_ARTIFACT_BYTES_LIMIT", "PROJECTION_SCHEMA",
    "RelayMEMSLPDurableProtectedSourceStore", "RelayMEMSLPProtectedSourceStoreResult",
]
