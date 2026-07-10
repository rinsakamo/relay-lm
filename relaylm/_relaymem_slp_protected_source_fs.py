"""Secure filesystem primitives for Phase 6-C1-5 protected sources."""
from __future__ import annotations

import ctypes
import errno
import os
import secrets
import stat
from pathlib import Path

from .portable_lock import PortableLockUnavailable, acquire_portable_lock, release_portable_lock
from ._relaymem_slp_protected_source_artifact import (
    CLEANUP_MARKER_FIELDS,
    CLEANUP_MARKER_SCHEMA,
    canonical_json_bytes,
    cleanup_marker_filename,
    decode_canonical_json,
)


def open_store_root(root_path: str) -> tuple[int | None, tuple[str, ...]]:
    if not supports_secure_dirfd():
        return None, ("protected_source_platform_unsupported",)
    absolute = Path(root_path)
    if not absolute.is_absolute() or any(part in {".", ".."} for part in absolute.parts[1:]):
        return None, ("protected_source_root_invalid",)
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(absolute.anchor, flags)
    except OSError:
        return None, ("protected_source_root_unopenable",)
    for part in absolute.parts[1:]:
        try:
            before = os.stat(part, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            os.close(fd)
            return None, ("protected_source_root_missing",)
        except OSError:
            os.close(fd)
            return None, ("protected_source_root_unopenable",)
        if stat.S_ISLNK(before.st_mode):
            os.close(fd)
            return None, ("protected_source_root_symlink_blocked",)
        if not stat.S_ISDIR(before.st_mode):
            os.close(fd)
            return None, ("protected_source_root_not_directory",)
        try:
            child = os.open(
                part, flags | getattr(os, "O_NOFOLLOW", 0), dir_fd=fd
            )
        except OSError:
            os.close(fd)
            return None, ("protected_source_root_unopenable",)
        after = os.fstat(child)
        if not stat.S_ISDIR(after.st_mode) or (
            before.st_dev, before.st_ino
        ) != (after.st_dev, after.st_ino):
            os.close(child)
            os.close(fd)
            return None, ("protected_source_root_changed",)
        os.close(fd)
        fd = child
    return fd, ()


def read_artifact(
    root_fd: int, filename: str, *, max_bytes: int
) -> tuple[dict[str, object] | None, str, tuple[str, ...]]:
    try:
        before = os.stat(filename, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None, "missing", ("protected_source_artifact_missing",)
    except OSError:
        return None, "retryable", ("protected_source_artifact_unreadable",)
    if stat.S_ISLNK(before.st_mode):
        return None, "corrupt", ("protected_source_artifact_symlink_blocked",)
    if not stat.S_ISREG(before.st_mode):
        return None, "corrupt", ("protected_source_artifact_not_regular",)
    if before.st_nlink != 1:
        return None, "corrupt", ("protected_source_artifact_hardlink_invalid",)
    if before.st_size > max_bytes:
        return None, "corrupt", ("protected_source_artifact_size_exceeded",)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(filename, flags, dir_fd=root_fd)
    except FileNotFoundError:
        return None, "missing", ("protected_source_artifact_missing",)
    except OSError:
        return None, "retryable", ("protected_source_artifact_unreadable",)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            return None, "corrupt", ("protected_source_artifact_not_regular",)
        if (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino):
            return None, "corrupt", ("protected_source_artifact_changed_during_read",)
        data = read_bounded(fd, max_bytes)
        if data is None:
            return None, "corrupt", ("protected_source_artifact_size_exceeded",)
    except OSError:
        return None, "retryable", ("protected_source_artifact_unreadable",)
    finally:
        os.close(fd)
    try:
        after = os.stat(filename, dir_fd=root_fd, follow_symlinks=False)
    except OSError:
        return None, "corrupt", ("protected_source_artifact_changed_during_read",)
    if (
        stat.S_ISLNK(after.st_mode) or not stat.S_ISREG(after.st_mode)
        or after.st_nlink != 1
        or (after.st_dev, after.st_ino) != (info.st_dev, info.st_ino)
        or after.st_size != info.st_size
    ):
        return None, "corrupt", ("protected_source_artifact_changed_during_read",)
    value, reason = decode_canonical_json(data)
    return (value, "ok", ()) if reason is None else (None, "corrupt", (reason,))


def atomic_create(
    root_fd: int, filename: str, data: bytes, *, max_bytes: int
) -> tuple[str, tuple[str, ...]]:
    temp = f".protected-source-{secrets.token_hex(16)}.tmp"
    created = False
    flags = (
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        try:
            fd = os.open(temp, flags, 0o600, dir_fd=root_fd)
            created = True
        except OSError:
            return "failed", ("protected_source_temp_create_failed",)
        try:
            write_all(fd, data)
            os.fsync(fd)
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_size != len(data) or info.st_size > max_bytes
            ):
                raise OSError(errno.EIO, "unsafe protected source temp")
        except OSError:
            return "failed", ("protected_source_temp_write_failed",)
        finally:
            os.close(fd)
        published = rename_noreplace(root_fd, temp, filename)
        if published == "exists":
            return "exists", ()
        if published != "published":
            return "failed", ("protected_source_atomic_publish_failed",)
        created = False
        try:
            os.fsync(root_fd)
        except OSError:
            return "failed", ("protected_source_directory_fsync_failed",)
        value, status_value, reasons = read_artifact(
            root_fd, filename, max_bytes=max_bytes
        )
        if status_value != "ok" or value is None or canonical_json_bytes(value) != data:
            return "failed", reasons or ("protected_source_publish_verification_failed",)
        return "created", ()
    finally:
        if created:
            try:
                os.unlink(temp, dir_fd=root_fd)
                os.fsync(root_fd)
            except OSError:
                pass


def write_cleanup_marker(root_fd: int, key_digest: str, reason_id: str) -> bool:
    marker = {
        "schema_version": CLEANUP_MARKER_SCHEMA,
        "runtime_private": True,
        "content_free": True,
        "cleanup_required": True,
        "artifact_key_digest": key_digest,
        "reason_id": reason_id,
    }
    if set(marker) != CLEANUP_MARKER_FIELDS:
        return False
    status_value, _ = atomic_create(
        root_fd, f".protected-source-cleanup-{key_digest}.json",
        canonical_json_bytes(marker), max_bytes=4096,
    )
    return status_value in {"created", "exists"}


def remove_cleanup_marker(root_fd: int, artifact_name: str) -> None:
    try:
        os.unlink(cleanup_marker_filename(artifact_name), dir_fd=root_fd)
        os.fsync(root_fd)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def acquire_lock(root_fd: int, *, exclusive: bool) -> str | None:
    mode = "exclusive" if exclusive else "shared"
    try:
        acquire_portable_lock(root_fd, mode=mode, blocking=False)
    except PortableLockUnavailable:
        return "protected_source_store_lock_busy"
    except OSError:
        return "protected_source_store_lock_failed"
    return None


def release_lock(root_fd: int) -> None:
    try:
        release_portable_lock(root_fd)
    except OSError:
        pass


def rename_noreplace(root_fd: int, source: str, destination: str) -> str:
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, "renameat2", None)
    if function is None:
        return "unsupported"
    function.argtypes = [
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint
    ]
    function.restype = ctypes.c_int
    if function(root_fd, os.fsencode(source), root_fd, os.fsencode(destination), 1) == 0:
        return "published"
    error = ctypes.get_errno()
    if error == errno.EEXIST:
        return "exists"
    return "unsupported" if error in {errno.ENOSYS, errno.EINVAL} else "failed"


def read_bounded(fd: int, max_bytes: int) -> bytes | None:
    chunks: list[bytes] = []
    remaining = max_bytes + 1
    while remaining > 0:
        chunk = os.read(fd, min(4096, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b"".join(chunks)
    return None if len(data) > max_bytes else data


def write_all(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0:
            raise OSError(errno.EIO, "short write")
        offset += written


def supports_secure_dirfd() -> bool:
    return all(function in os.supports_dir_fd for function in (os.open, os.stat, os.unlink)) \
        and os.stat in os.supports_follow_symlinks


__all__ = [
    "acquire_lock", "atomic_create", "open_store_root", "read_artifact",
    "release_lock", "remove_cleanup_marker", "write_cleanup_marker",
]
