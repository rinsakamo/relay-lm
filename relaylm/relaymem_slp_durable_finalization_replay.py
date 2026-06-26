"""Public I1-GC one-record durable-finalization replay authority.

The convergence implementation is isolated in a private module.  This boundary
owns the nonblocking per-record fence, late-outcome adaptation, and explicit
dependency seams used by production fault-injection smoke coverage.
"""
from __future__ import annotations

import errno
import fcntl
import os
import secrets
import stat
from collections.abc import Mapping
from typing import Any

from . import _relaymem_slp_durable_finalization_replay_impl as _impl

COMPLETION_FIELDS = _impl.COMPLETION_FIELDS
COMPLETION_REVISION = _impl.COMPLETION_REVISION
COMPLETION_SCHEMA = _impl.COMPLETION_SCHEMA
REPLAY_PROJECTION_SCHEMA = _impl.REPLAY_PROJECTION_SCHEMA
RelayMEMSLPDurableFinalizationReplayProjection = (
    _impl.RelayMEMSLPDurableFinalizationReplayProjection
)
RelayMEMSLPDurableFinalizationReplayResult = (
    _impl.RelayMEMSLPDurableFinalizationReplayResult
)

# Explicit dependency seams. They remain exact production authorities; smoke
# tests may replace them temporarily to model late or ambiguous outcomes.
apply_relaymem_slp_runtime_enqueue = _impl.apply_relaymem_slp_runtime_enqueue
prepare_relaymem_slp_runtime_enqueue = _impl.prepare_relaymem_slp_runtime_enqueue
_rename_noreplace = _impl._rename_noreplace
_hash_without = _impl._hash_without


def _acquire_fence(
    root: str,
    locator: str,
) -> tuple[_impl._Fence | None, bool, tuple[str, ...]]:
    """Acquire one durable nonblocking cross-process locator fence."""

    root_fd, reasons = _impl._open_store_root(root)
    if root_fd is None:
        return None, False, reasons
    name = f"{_impl._LOCK_PREFIX}{locator}.lock"
    lock_fd: int | None = None
    acquired = False
    try:
        try:
            before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            before = None
        if before is not None and (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
        ):
            return None, False, (
                "durable_finalization_replay_lock_unsafe_file_type",
            )
        lock_fd = os.open(
            name,
            os.O_RDWR
            | os.O_CREAT
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=root_fd,
        )
        info = os.fstat(lock_fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or (
                before is not None
                and (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino)
            )
        ):
            return None, False, (
                "durable_finalization_replay_lock_unsafe_file_type",
            )
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError:
            return None, True, ("durable_finalization_replay_lock_busy",)
        if before is None:
            os.fsync(lock_fd)
            os.fsync(root_fd)
        fence = _impl._Fence(root_fd, lock_fd)
        root_fd = -1
        lock_fd = None
        acquired = False
        return fence, False, ()
    except OSError:
        return None, False, ("durable_finalization_replay_lock_failed",)
    finally:
        if lock_fd is not None:
            if acquired:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except OSError:
                    pass
            try:
                os.close(lock_fd)
            except OSError:
                pass
        if root_fd >= 0:
            try:
                os.close(root_fd)
            except OSError:
                pass


def _wrap_runtime(
    applied: _impl.RelayMEMSLPRuntimeEnqueueResult,
    persisted: _impl.RelayMEMSLPProtectedSourceStoreResult,
    restart_complete: bool,
) -> _impl.RelayMEMSLPDurableRuntimeEnqueueResult:
    """Project the canonical reread result without guessing a failed mutation."""

    enqueue = applied.enqueue_result
    if restart_complete:
        if applied.status in {"source_retention_failed", "enqueue_failed"}:
            status = "process_local_cache_degraded"
        elif enqueue is not None and enqueue.status == "enqueued_new":
            status = "enqueued"
        else:
            status = "duplicate_existing"
    elif enqueue is not None and enqueue.status == "enqueued_new":
        status = "enqueued"
    elif applied.status == "source_retention_failed":
        status = "process_local_cache_degraded"
    elif enqueue is not None and enqueue.status == "duplicate_existing":
        status = "duplicate_existing"
    else:
        status = "enqueue_failed"
    reasons = (
        applied.blocked_reasons
        if status in {"process_local_cache_degraded", "enqueue_failed"}
        else ()
    )
    return _impl.RelayMEMSLPDurableRuntimeEnqueueResult(
        status=status,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        restart_complete=restart_complete,
        source_persisted_before_enqueue=True,
        blocked_reasons=_impl.dedupe(tuple(reasons)),
        runtime_result=applied,
        source_store_result=persisted,
        orphan_cleanup_result=None,
    )


def _publish_completion(
    root: str,
    locator: str,
    expected: Mapping[str, object],
) -> _impl._Inspect:
    """Publish no-clobber completion and reread every uncertain outcome."""

    data = _impl.canonical_json_bytes(expected)
    if len(data) > _impl._MAX_COMPLETION_BYTES:
        return _impl._Inspect(
            "corrupt", ("durable_finalization_completion_size_exceeded",)
        )
    root_fd, reasons = _impl._open_store_root(root)
    if root_fd is None:
        return _impl._Inspect("retryable", reasons)
    temp = f".durable-finalization-completion-{secrets.token_hex(16)}.tmp"
    temp_exists = False
    try:
        current = _impl._read_completion_fd(root_fd, locator, expected)
        if current.kind == "exact":
            return current
        if current.kind != "absent":
            return current
        try:
            fd = os.open(
                temp,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=root_fd,
            )
            temp_exists = True
        except OSError:
            return _impl._Inspect(
                "retryable",
                ("durable_finalization_completion_temp_create_failed",),
            )
        try:
            _impl._write_all(fd, data)
            os.fsync(fd)
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_size != len(data)
            ):
                raise OSError(errno.EIO, "unsafe completion temp")
        except OSError:
            return _impl._Inspect(
                "retryable",
                ("durable_finalization_completion_temp_write_failed",),
            )
        finally:
            os.close(fd)

        outcome = _rename_noreplace(
            root_fd, temp, _impl.completion_filename(locator)
        )
        if outcome == "published":
            temp_exists = False
            fsync_failed = False
            try:
                os.fsync(root_fd)
            except OSError:
                fsync_failed = True
            reread = _impl._read_completion_fd(root_fd, locator, expected)
            if reread.kind != "exact":
                return reread
            if fsync_failed:
                return _impl._Inspect(
                    "retryable",
                    (
                        "durable_finalization_completion_directory_fsync_ambiguous",
                    ),
                )
            return _impl._Inspect("created")
        if outcome == "exists":
            return _impl._read_completion_fd(root_fd, locator, expected)

        reread = _impl._read_completion_fd(root_fd, locator, expected)
        if reread.kind == "exact":
            try:
                os.fsync(root_fd)
            except OSError:
                return _impl._Inspect(
                    "retryable",
                    (
                        "durable_finalization_completion_directory_fsync_ambiguous",
                    ),
                )
            return reread
        return _impl._Inspect(
            "retryable",
            reread.reasons
            or ("durable_finalization_completion_atomic_publish_ambiguous",),
        )
    finally:
        if temp_exists:
            try:
                os.unlink(temp, dir_fd=root_fd)
                os.fsync(root_fd)
            except OSError:
                pass
        os.close(root_fd)


def _sync_dependency_seams() -> None:
    _impl.apply_relaymem_slp_runtime_enqueue = apply_relaymem_slp_runtime_enqueue
    _impl.prepare_relaymem_slp_runtime_enqueue = prepare_relaymem_slp_runtime_enqueue
    _impl._rename_noreplace = _rename_noreplace
    _impl._acquire_fence = _acquire_fence
    _impl._wrap_runtime = _wrap_runtime
    _impl._publish_completion = _publish_completion


def replay_relaymem_slp_durable_finalization_record(
    config: object,
    *,
    locator_digest: object,
    registry: Any,
    fault_injector: Any = None,
) -> RelayMEMSLPDurableFinalizationReplayResult:
    """Converge one caller-selected locator without discovery or execution."""

    _sync_dependency_seams()
    return _impl.replay_relaymem_slp_durable_finalization_record(
        config,
        locator_digest=locator_digest,
        registry=registry,
        fault_injector=fault_injector,
    )


def build_relaymem_slp_durable_finalization_replay_node_result(
    result: RelayMEMSLPDurableFinalizationReplayResult,
):
    return _impl.build_relaymem_slp_durable_finalization_replay_node_result(result)


def completion_filename(locator_digest: str) -> str:
    return _impl.completion_filename(locator_digest)


def validate_completion_marker(
    value: object,
    *,
    expected_locator: str | None = None,
    expected: Any = None,
):
    return _impl.validate_completion_marker(
        value,
        expected_locator=expected_locator,
        expected=expected,
    )


_sync_dependency_seams()

__all__ = [
    "COMPLETION_FIELDS",
    "COMPLETION_REVISION",
    "COMPLETION_SCHEMA",
    "REPLAY_PROJECTION_SCHEMA",
    "RelayMEMSLPDurableFinalizationReplayProjection",
    "RelayMEMSLPDurableFinalizationReplayResult",
    "build_relaymem_slp_durable_finalization_replay_node_result",
    "completion_filename",
    "replay_relaymem_slp_durable_finalization_record",
    "validate_completion_marker",
]
