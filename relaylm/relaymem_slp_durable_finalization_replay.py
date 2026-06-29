"""Public I1-GC one-record durable-finalization replay authority."""
from __future__ import annotations

import fcntl
import os
import stat
from collections.abc import Mapping
from typing import Any

from . import _relaymem_slp_durable_finalization_replay_impl as _impl
from .relaymem_slp_durable_finalization_replay_current_source import (
    reconstruct_current_finalized_source as _reconstruct_source,
)

COMPLETION_FIELDS = _impl.COMPLETION_FIELDS
COMPLETION_REVISION = _impl.COMPLETION_REVISION
COMPLETION_SCHEMA = _impl.COMPLETION_SCHEMA
REPLAY_PROJECTION_SCHEMA = _impl.REPLAY_PROJECTION_SCHEMA
RelayMEMSLPDurableFinalizationReplayProjection = _impl.RelayMEMSLPDurableFinalizationReplayProjection
RelayMEMSLPDurableFinalizationReplayResult = _impl.RelayMEMSLPDurableFinalizationReplayResult

apply_relaymem_slp_runtime_enqueue = _impl.apply_relaymem_slp_runtime_enqueue
prepare_relaymem_slp_runtime_enqueue = _impl.prepare_relaymem_slp_runtime_enqueue
_rename_noreplace = _impl._rename_noreplace
_hash_without = _impl._hash_without
_publish_completion = _impl._publish_completion


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
    """Project canonical reread convergence without guessing a failed mutation."""

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


def _read_completion_fd(
    root_fd: int,
    locator: str,
    expected: Mapping[str, object],
) -> _impl._Inspect:
    """Read one completion and distinguish invalid bytes from valid collisions."""

    name = _impl.completion_filename(locator)
    try:
        before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return _impl._Inspect("absent")
    except OSError:
        return _impl._Inspect(
            "retryable", ("durable_finalization_completion_unreadable",)
        )
    if stat.S_ISLNK(before.st_mode):
        return _impl._Inspect(
            "corrupt", ("durable_finalization_completion_symlink_blocked",)
        )
    if not stat.S_ISREG(before.st_mode):
        return _impl._Inspect(
            "corrupt", ("durable_finalization_completion_unsafe_file_type",)
        )
    if before.st_nlink != 1:
        return _impl._Inspect(
            "corrupt", ("durable_finalization_completion_hardlink_invalid",)
        )
    if before.st_size > _impl._MAX_COMPLETION_BYTES:
        return _impl._Inspect(
            "corrupt", ("durable_finalization_completion_size_exceeded",)
        )
    try:
        fd = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=root_fd,
        )
    except FileNotFoundError:
        return _impl._Inspect("absent")
    except OSError:
        return _impl._Inspect(
            "retryable", ("durable_finalization_completion_unreadable",)
        )
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino)
        ):
            return _impl._Inspect(
                "corrupt",
                ("durable_finalization_completion_changed_during_read",),
            )
        data = _impl._read_bounded(fd, _impl._MAX_COMPLETION_BYTES)
    finally:
        os.close(fd)
    if data is None:
        return _impl._Inspect(
            "corrupt", ("durable_finalization_completion_size_exceeded",)
        )
    try:
        after = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except OSError:
        return _impl._Inspect(
            "corrupt", ("durable_finalization_completion_changed_during_read",)
        )
    if (
        stat.S_ISLNK(after.st_mode)
        or not stat.S_ISREG(after.st_mode)
        or after.st_nlink != 1
        or (after.st_dev, after.st_ino) != (info.st_dev, info.st_ino)
        or after.st_size != info.st_size
    ):
        return _impl._Inspect(
            "corrupt", ("durable_finalization_completion_changed_during_read",)
        )
    value, reason = _impl.decode_canonical_json(data)
    if value is None or reason:
        return _impl._Inspect(
            "corrupt",
            (reason or "durable_finalization_completion_decode_failed",),
        )
    _, reasons = _impl.validate_completion_marker(
        value,
        expected_locator=locator,
        expected=expected,
    )
    if reasons:
        collision_reason = "durable_finalization_completion_identity_collision"
        return _impl._Inspect(
            "collision" if reasons == (collision_reason,) else "corrupt",
            reasons,
        )
    return _impl._Inspect("exact")


def _sync_dependency_seams() -> None:
    _impl.apply_relaymem_slp_runtime_enqueue = apply_relaymem_slp_runtime_enqueue
    _impl.prepare_relaymem_slp_runtime_enqueue = prepare_relaymem_slp_runtime_enqueue
    _impl._rename_noreplace = _rename_noreplace
    _impl._acquire_fence = _acquire_fence
    _impl._wrap_runtime = _wrap_runtime
    _impl._reconstruct_source = _reconstruct_source
    _impl._read_completion_fd = _read_completion_fd
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
