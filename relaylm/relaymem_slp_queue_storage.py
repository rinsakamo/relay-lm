"""Internal fail-closed filesystem helpers for Phase 6-B3 queue transitions."""
from __future__ import annotations

import errno
import fcntl
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path

from relaylm.relaymem_slp_queue_record import (
    MAX_RECORD_BYTES,
    bad_text,
    canonical_json_bytes,
    decode_canonical_record,
    record_filename,
    validate_record_mapping,
)


@dataclass(frozen=True)
class RecordSnapshot:
    record: dict[str, object]
    data: bytes
    device: int
    inode: int


@dataclass(frozen=True)
class AtomicReplaceOutcome:
    status: str
    transition_applied: bool
    durability_confirmed: bool
    record: dict[str, object]
    reasons: tuple[str, ...]


def open_queue_root(root_path: str | None) -> tuple[int | None, tuple[str, ...]]:
    if type(root_path) is not str:
        return None, ("queue_root_not_configured",)
    if root_path != root_path.strip() or not root_path or bad_text(root_path):
        return None, ("queue_root_invalid",)
    if not supports_secure_dirfd():
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
            if (
                not stat.S_ISDIR(after.st_mode)
                or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
            ):
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


def acquire_queue_lock(root_fd: int, *, exclusive: bool) -> str | None:
    mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    try:
        fcntl.flock(root_fd, mode | fcntl.LOCK_NB)
    except BlockingIOError:
        return "queue_lock_busy"
    except OSError:
        return "queue_lock_failed"
    return None


def release_queue_lock(root_fd: int) -> None:
    try:
        fcntl.flock(root_fd, fcntl.LOCK_UN)
    except OSError:
        pass


def read_record_snapshot(
    root_fd: int,
    filename: str,
) -> tuple[RecordSnapshot | None, str, tuple[str, ...]]:
    try:
        before = os.stat(filename, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None, "missing", ("queue_record_missing",)
    except OSError:
        return None, "write_failed", ("queue_record_unreadable",)
    if stat.S_ISLNK(before.st_mode):
        return None, "corrupt", ("queue_record_symlink_blocked",)
    if not stat.S_ISREG(before.st_mode):
        return None, "corrupt", ("queue_record_unexpected_file_type",)
    if before.st_nlink != 1:
        return None, "corrupt", ("queue_record_hardlink_count_invalid",)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(filename, flags, dir_fd=root_fd)
    except OSError:
        return None, "write_failed", ("queue_record_unreadable",)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return None, "corrupt", ("queue_record_unexpected_file_type",)
        if info.st_nlink != 1:
            return None, "corrupt", ("queue_record_hardlink_count_invalid",)
        if (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino):
            return None, "corrupt", ("queue_record_changed_during_read",)
        data = _read_bounded(fd)
        if data is None:
            return None, "corrupt", ("queue_record_size_exceeded",)
        record, decode_error = decode_canonical_record(data)
        if decode_error:
            return None, "corrupt", (decode_error,)
        assert record is not None
        try:
            after = os.stat(filename, dir_fd=root_fd, follow_symlinks=False)
        except OSError:
            return None, "corrupt", ("queue_record_changed_during_read",)
        if (
            stat.S_ISLNK(after.st_mode)
            or not stat.S_ISREG(after.st_mode)
            or after.st_nlink != 1
            or (after.st_dev, after.st_ino) != (info.st_dev, info.st_ino)
        ):
            return None, "corrupt", ("queue_record_changed_during_read",)
        errors = validate_record_mapping(record)
        if errors:
            return None, "corrupt", errors
        if record_filename(str(record["dispatch_idempotency_key"])) != filename:
            return None, "corrupt", ("queue_record_key_path_mismatch",)
        return RecordSnapshot(record, data, info.st_dev, info.st_ino), "ok", ()
    except OSError:
        return None, "write_failed", ("queue_record_unreadable",)
    finally:
        os.close(fd)


def atomic_replace_record(
    root_fd: int,
    filename: str,
    snapshot: RecordSnapshot,
    proposal: dict[str, object],
) -> AtomicReplaceOutcome:
    data = canonical_json_bytes(proposal)
    temp_name = f".relay-slp-state-{secrets.token_hex(16)}.tmp"
    temp_created = False
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        try:
            temp_fd = os.open(temp_name, flags, 0o600, dir_fd=root_fd)
            temp_created = True
        except OSError:
            return _failure(proposal, "queue_temp_create_failed")
        try:
            _write_all(temp_fd, data)
            os.fsync(temp_fd)
            info = os.fstat(temp_fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_size != len(data)
            ):
                raise OSError(errno.EIO, "unsafe temp file")
        except OSError:
            return _failure(proposal, "queue_temp_write_failed")
        finally:
            os.close(temp_fd)

        cas_error = reopen_and_compare(root_fd, filename, snapshot)
        if cas_error:
            return AtomicReplaceOutcome(
                "conflict", False, False, dict(snapshot.record), (cas_error,)
            )
        try:
            os.replace(temp_name, filename, src_dir_fd=root_fd, dst_dir_fd=root_fd)
            temp_created = False
        except OSError:
            return _failure(proposal, "queue_atomic_replace_failed")
        try:
            os.fsync(root_fd)
        except OSError:
            return AtomicReplaceOutcome(
                "write_failed", True, False, dict(proposal),
                ("queue_directory_fsync_failed",),
            )
        committed, committed_status, committed_reasons = read_record_snapshot(
            root_fd, filename
        )
        if (
            committed is None
            or committed_status != "ok"
            or committed.data != data
            or committed.record != proposal
        ):
            return AtomicReplaceOutcome(
                "write_failed", True, False, dict(proposal),
                committed_reasons or ("committed_record_verification_failed",),
            )
        return AtomicReplaceOutcome("applied", True, True, dict(proposal), ())
    finally:
        if temp_created:
            try:
                os.unlink(temp_name, dir_fd=root_fd)
            except OSError:
                pass


def reopen_and_compare(
    root_fd: int,
    filename: str,
    snapshot: RecordSnapshot,
) -> str | None:
    current, status_value, _ = read_record_snapshot(root_fd, filename)
    if current is None or status_value != "ok":
        return "queue_record_cas_conflict"
    if (current.device, current.inode) != (snapshot.device, snapshot.inode):
        return "queue_record_inode_changed"
    if current.data != snapshot.data:
        return "queue_record_bytes_changed"
    return None


def supports_secure_dirfd() -> bool:
    return (
        all(
            function in os.supports_dir_fd
            for function in (os.open, os.stat, os.unlink, os.rename)
        )
        and os.stat in os.supports_follow_symlinks
    )


def _read_bounded(fd: int) -> bytes | None:
    chunks: list[bytes] = []
    remaining = MAX_RECORD_BYTES + 1
    while remaining > 0:
        chunk = os.read(fd, min(4096, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b"".join(chunks)
    return None if len(data) > MAX_RECORD_BYTES else data


def _write_all(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0:
            raise OSError(errno.EIO, "short write")
        offset += written


def _failure(proposal: dict[str, object], reason: str) -> AtomicReplaceOutcome:
    return AtomicReplaceOutcome(
        "write_failed", False, False, dict(proposal), (reason,)
    )


__all__ = [
    "AtomicReplaceOutcome", "RecordSnapshot", "acquire_queue_lock",
    "atomic_replace_record", "open_queue_root", "read_record_snapshot",
    "release_queue_lock", "reopen_and_compare",
]
