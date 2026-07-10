"""Portable advisory file locking for POSIX and Windows.

RelayLM has several modules that take an advisory lock on a file descriptor to
serialize cross-process access to on-disk state. Historically they did this by
importing ``fcntl`` directly and calling ``fcntl.flock``. ``fcntl`` does not
exist on Windows, so any unconditional ``import fcntl`` at module scope makes
``import relaylm.app`` fail at startup on that platform.

This module provides one portable lock abstraction that behaves identically to
the historical ``fcntl.flock`` usage on POSIX, and falls back to
``msvcrt.locking`` on Windows. Callers should use the :func:`portable_lock`
context manager where possible, or the explicit :func:`acquire_portable_lock`
/ :func:`release_portable_lock` functions where a context manager would force
an awkward restructuring (for example when the lock handle is stored on an
object across multiple method calls).
"""
from __future__ import annotations

import errno
import os
import time
from contextlib import contextmanager
from typing import Iterator, Protocol, Union, runtime_checkable

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised only on Windows
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:  # pragma: no cover - exercised only on POSIX
    msvcrt = None  # type: ignore[assignment]


@runtime_checkable
class _HasFileno(Protocol):
    def fileno(self) -> int: ...


FileLike = Union[int, _HasFileno]

# flock()-style non-blocking contention on POSIX normally surfaces as
# EWOULDBLOCK/EAGAIN (both are the same value on Linux), which Python's
# runtime automatically raises as BlockingIOError. EACCES is included for
# completeness/documentation of the fcntl-based lock family even though the
# BSD flock() semantics used here practically only ever raise EAGAIN/EWOULDBLOCK.
_POSIX_LOCK_UNAVAILABLE_ERRNOS = frozenset(
    {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}
)

# msvcrt.locking() reports lock contention through OSError. Keep this set
# conservative so real descriptor/programming failures (for example EBADF)
# still surface immediately instead of being retried forever.
_WINDOWS_LOCK_UNAVAILABLE_ERRNOS = frozenset(
    errno_value
    for errno_value in (
        getattr(errno, "EACCES", None),
        getattr(errno, "EAGAIN", None),
        getattr(errno, "EWOULDBLOCK", None),
        getattr(errno, "EDEADLK", None),
    )
    if errno_value is not None
)

# msvcrt.locking() locks a byte range starting at the current file position.
# There is nothing meaningful about locking more than one byte for an
# advisory whole-file lock, so a fixed 1-byte range is used consistently by
# both the lock and unlock calls.
_WINDOWS_LOCK_NBYTES = 1
_WINDOWS_BLOCKING_RETRY_SLEEP_SECONDS = 0.05


class PortableLockUnavailable(BlockingIOError):
    """Raised when a non-blocking lock acquisition could not be satisfied.

    This is intentionally a subclass of ``BlockingIOError`` (itself a subclass
    of ``OSError``) rather than a bare ``OSError`` subclass. Several existing
    call sites distinguish "lock is busy" from "lock failed for some other
    reason" by catching ``except BlockingIOError`` narrowly before falling
    back to a broader ``except OSError``. Making this exception a
    ``BlockingIOError`` subclass means those call sites keep working exactly
    as before without any changes, on both POSIX and Windows.
    """


def _fileno(fd_or_file: FileLike) -> int:
    if isinstance(fd_or_file, int):
        return fd_or_file
    return fd_or_file.fileno()


def acquire_portable_lock(
    fd_or_file: FileLike, *, mode: str = "exclusive", blocking: bool = True
) -> None:
    """Acquire an advisory lock on ``fd_or_file``.

    ``fd_or_file`` may be a raw integer file descriptor or any object exposing
    ``.fileno()`` (e.g. a file object). ``mode`` is ``"exclusive"`` or
    ``"shared"``. When ``blocking`` is False and the lock is already held
    elsewhere, raises :class:`PortableLockUnavailable`.
    """
    if mode not in ("exclusive", "shared"):
        raise ValueError(f"invalid portable lock mode: {mode!r}")
    fd = _fileno(fd_or_file)
    if fcntl is not None:
        _acquire_posix(fd, mode=mode, blocking=blocking)
    elif msvcrt is not None:
        _acquire_windows(fd, mode=mode, blocking=blocking)
    else:  # pragma: no cover - no supported locking backend on this platform
        raise PortableLockUnavailable(
            "no supported file-locking backend (neither fcntl nor msvcrt) is available"
        )


def release_portable_lock(fd_or_file: FileLike) -> None:
    """Release a lock previously acquired with :func:`acquire_portable_lock`."""
    fd = _fileno(fd_or_file)
    if fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_UN)
    elif msvcrt is not None:
        _release_windows(fd)
    else:  # pragma: no cover - no supported locking backend on this platform
        raise PortableLockUnavailable(
            "no supported file-locking backend (neither fcntl nor msvcrt) is available"
        )


@contextmanager
def portable_lock(
    fd_or_file: FileLike, *, mode: str = "exclusive", blocking: bool = True
) -> Iterator[None]:
    """Context manager acquiring and releasing a portable advisory lock.

    Example::

        with portable_lock(fd_or_file, mode="exclusive", blocking=True):
            ...
    """
    acquire_portable_lock(fd_or_file, mode=mode, blocking=blocking)
    try:
        yield
    finally:
        release_portable_lock(fd_or_file)


def _acquire_posix(fd: int, *, mode: str, blocking: bool) -> None:
    flags = fcntl.LOCK_EX if mode == "exclusive" else fcntl.LOCK_SH
    if not blocking:
        flags |= fcntl.LOCK_NB
    try:
        fcntl.flock(fd, flags)
    except (BlockingIOError, OSError) as exc:
        if not blocking and getattr(exc, "errno", None) in _POSIX_LOCK_UNAVAILABLE_ERRNOS:
            raise PortableLockUnavailable(*exc.args) from exc
        raise


def _acquire_windows(fd: int, *, mode: str, blocking: bool) -> None:
    # Windows fallback uses msvcrt byte-range locking. Shared locks are
    # conservatively degraded to exclusive locks because msvcrt has no
    # LOCK_SH equivalent.
    del mode

    # msvcrt.locking() locks a byte range starting at the CURRENT file
    # position, not a fixed offset like fcntl.flock(). Save the caller's file
    # position, seek to a fixed offset (0) so the locked byte range is
    # deterministic and matches what _release_windows() unlocks, then restore
    # the caller's position afterward.
    saved_position = os.lseek(fd, 0, os.SEEK_CUR)
    os.lseek(fd, 0, os.SEEK_SET)
    try:
        # LK_LOCK retries internally for roughly 10 seconds before giving up
        # and raising OSError. POSIX flock(..., LOCK_EX) blocks indefinitely,
        # so preserve that contract by retrying lock-contention failures until
        # the lock is acquired. Non-contention OSErrors still surface.
        if blocking:
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_LOCK, _WINDOWS_LOCK_NBYTES)
                    return
                except OSError as exc:
                    if getattr(exc, "errno", None) not in _WINDOWS_LOCK_UNAVAILABLE_ERRNOS:
                        raise
                    time.sleep(_WINDOWS_BLOCKING_RETRY_SLEEP_SECONDS)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, _WINDOWS_LOCK_NBYTES)
        except OSError as exc:
            raise PortableLockUnavailable(*exc.args) from exc
    finally:
        os.lseek(fd, saved_position, os.SEEK_SET)


def _release_windows(fd: int) -> None:
    saved_position = os.lseek(fd, 0, os.SEEK_CUR)
    os.lseek(fd, 0, os.SEEK_SET)
    try:
        msvcrt.locking(fd, msvcrt.LK_UNLCK, _WINDOWS_LOCK_NBYTES)
    finally:
        os.lseek(fd, saved_position, os.SEEK_SET)


__all__ = [
    "FileLike",
    "PortableLockUnavailable",
    "acquire_portable_lock",
    "portable_lock",
    "release_portable_lock",
]
