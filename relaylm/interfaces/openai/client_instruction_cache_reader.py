"""Read-only client instruction cache filesystem reader."""

from __future__ import annotations

import errno
import json
import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

_SCHEMA_VERSION = "client_instruction_cache_reader.v0"
_DEFAULT_MAX_ENTRY_BYTES = 65536
_MAX_ENTRY_BYTES_LIMIT = 1048576
_VALID_CACHE_KEY_LENGTH = 64
_VALID_CACHE_KEY_CHARS = frozenset("0123456789abcdef")
_DIR_FD_SUPPORTED = os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd


class _DuplicateJsonKeyError(ValueError):
    pass


class _NonstandardJsonNumberError(ValueError):
    pass


@dataclass(frozen=True)
class ClientInstructionCacheReadResult:
    schema_version: str
    status: Literal["found", "missing", "blocked"]
    candidate_entry: Mapping[str, Any] | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    entry_present: bool = False
    bytes_read: int = 0
    max_entry_bytes: int = _DEFAULT_MAX_ENTRY_BYTES
    miss_reason: str | None = None
    blocked_reasons: tuple[str, ...] = ()
    runtime_private: bool = True
    content_bearing: bool = True


def read_client_instruction_cache_candidate(
    *,
    root_path: str | Path | None,
    cache_key_sha256: str,
    enabled: bool,
    max_entry_bytes: int = _DEFAULT_MAX_ENTRY_BYTES,
) -> ClientInstructionCacheReadResult | None:
    """Read one cache entry candidate without mutating the filesystem."""

    if not enabled:
        return None

    max_entry_bytes = _normalize_max_entry_bytes(max_entry_bytes)
    root_fd: int | None = None

    try:
        if not _is_valid_cache_key(cache_key_sha256):
            return _blocked("cache_key_invalid", max_entry_bytes=max_entry_bytes)
        if root_path is None or str(root_path) == "":
            return _missing(
                "cache_root_not_configured",
                max_entry_bytes=max_entry_bytes,
            )

        root = Path(root_path)
        try:
            root_lstat = root.lstat()
        except FileNotFoundError:
            return _missing("cache_root_missing", max_entry_bytes=max_entry_bytes)
        except OSError:
            return _blocked(
                "cache_reader_failure",
                max_entry_bytes=max_entry_bytes,
            )

        if stat.S_ISLNK(root_lstat.st_mode) or _has_symlink_component(root):
            return _blocked(
                "cache_root_symlink_blocked",
                max_entry_bytes=max_entry_bytes,
            )
        if not stat.S_ISDIR(root_lstat.st_mode):
            return _blocked(
                "cache_root_not_directory",
                max_entry_bytes=max_entry_bytes,
            )

        root_fd_or_reason = _open_validated_root_fd(root, root_lstat)
        if isinstance(root_fd_or_reason, str):
            if root_fd_or_reason == "cache_root_missing":
                return _missing(root_fd_or_reason, max_entry_bytes=max_entry_bytes)
            return _blocked(root_fd_or_reason, max_entry_bytes=max_entry_bytes)
        root_fd = root_fd_or_reason

        filename = f"{cache_key_sha256}.json"
        entry_lstat_or_reason = _stat_entry_at(root_fd, filename)
        if isinstance(entry_lstat_or_reason, str):
            if entry_lstat_or_reason == "cache_entry_not_found":
                return _missing(
                    entry_lstat_or_reason,
                    max_entry_bytes=max_entry_bytes,
                )
            return _blocked(
                entry_lstat_or_reason,
                entry_present=entry_lstat_or_reason
                not in {"cache_entry_unreadable", "cache_entry_not_found"},
                max_entry_bytes=max_entry_bytes,
            )
        entry_lstat = entry_lstat_or_reason

        if stat.S_ISLNK(entry_lstat.st_mode):
            return _blocked(
                "cache_path_symlink_blocked",
                entry_present=True,
                max_entry_bytes=max_entry_bytes,
            )
        if not stat.S_ISREG(entry_lstat.st_mode):
            return _blocked(
                "cache_entry_not_regular_file",
                entry_present=True,
                max_entry_bytes=max_entry_bytes,
            )

        data_or_reason = _read_entry_bytes_at(
            root_fd,
            filename,
            entry_lstat,
            max_entry_bytes,
        )
        if isinstance(data_or_reason, str):
            return _blocked(
                data_or_reason,
                entry_present=True,
                max_entry_bytes=max_entry_bytes,
            )
        data = data_or_reason
        bytes_read = len(data)
        if bytes_read > max_entry_bytes:
            return _blocked(
                "cache_entry_read_limit_exceeded",
                entry_present=True,
                bytes_read=bytes_read,
                max_entry_bytes=max_entry_bytes,
            )

        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return _blocked(
                "cache_entry_malformed_utf8",
                entry_present=True,
                bytes_read=bytes_read,
                max_entry_bytes=max_entry_bytes,
            )

        parsed_or_reason = _parse_strict_json_object(text)
        if isinstance(parsed_or_reason, str):
            return _blocked(
                parsed_or_reason,
                entry_present=True,
                bytes_read=bytes_read,
                max_entry_bytes=max_entry_bytes,
            )

        return ClientInstructionCacheReadResult(
            schema_version=_SCHEMA_VERSION,
            status="found",
            candidate_entry=parsed_or_reason,
            entry_present=True,
            bytes_read=bytes_read,
            max_entry_bytes=max_entry_bytes,
        )
    except Exception:
        return _blocked(
            "cache_reader_failure",
            max_entry_bytes=max_entry_bytes,
        )
    finally:
        if root_fd is not None:
            os.close(root_fd)


def build_client_instruction_cache_read_diagnostics(
    result: ClientInstructionCacheReadResult | None,
) -> dict[str, Any] | None:
    """Build content-free diagnostics for a cache reader result."""

    if result is None:
        return {
            "schema_version": _SCHEMA_VERSION,
            "enabled": False,
            "status": None,
            "read_attempted": False,
            "entry_present": False,
            "entry_parsed": False,
            "bytes_read": 0,
            "max_entry_bytes": _DEFAULT_MAX_ENTRY_BYTES,
            "cache_root_configured": False,
            "cache_root_present": False,
            "miss_reason": None,
            "blocked_reasons": (),
            "read_only": True,
        }

    reasons = set(result.blocked_reasons)
    miss_reason = result.miss_reason
    root_configured = miss_reason != "cache_root_not_configured"
    root_present = (
        root_configured
        and miss_reason != "cache_root_missing"
        and "cache_root_symlink_blocked" not in reasons
    )

    return {
        "schema_version": result.schema_version,
        "enabled": True,
        "status": result.status,
        "read_attempted": True,
        "entry_present": result.entry_present,
        "entry_parsed": result.status == "found",
        "bytes_read": result.bytes_read,
        "max_entry_bytes": result.max_entry_bytes,
        "cache_root_configured": root_configured,
        "cache_root_present": root_present,
        "miss_reason": result.miss_reason,
        "blocked_reasons": result.blocked_reasons,
        "read_only": True,
    }


def _normalize_max_entry_bytes(max_entry_bytes: int) -> int:
    return min(_MAX_ENTRY_BYTES_LIMIT, max(1, int(max_entry_bytes)))


def _is_valid_cache_key(cache_key_sha256: str) -> bool:
    if not isinstance(cache_key_sha256, str):
        return False
    return (
        len(cache_key_sha256) == _VALID_CACHE_KEY_LENGTH
        and all(char in _VALID_CACHE_KEY_CHARS for char in cache_key_sha256)
    )


def _open_validated_root_fd(
    root: Path,
    root_lstat: os.stat_result,
) -> int | str:
    if not _DIR_FD_SUPPORTED:
        return "cache_reader_failure"

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    fd: int | None = None
    try:
        fd = os.open(root, flags)
        opened_stat = os.fstat(fd)
        if not stat.S_ISDIR(opened_stat.st_mode):
            return "cache_root_not_directory"
        if (
            opened_stat.st_dev != root_lstat.st_dev
            or opened_stat.st_ino != root_lstat.st_ino
        ):
            return "cache_path_outside_root"
        result = fd
        fd = None
        return result
    except FileNotFoundError:
        return "cache_root_missing"
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            return "cache_root_symlink_blocked"
        return "cache_reader_failure"
    finally:
        if fd is not None:
            os.close(fd)


def _stat_entry_at(root_fd: int, filename: str) -> os.stat_result | str:
    try:
        return os.stat(
            filename,
            dir_fd=root_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return "cache_entry_not_found"
    except OSError:
        return "cache_entry_unreadable"


def _read_entry_bytes_at(
    root_fd: int,
    filename: str,
    entry_lstat: os.stat_result,
    max_entry_bytes: int,
) -> bytes | str:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    fd: int | None = None
    try:
        fd = os.open(filename, flags, dir_fd=root_fd)
        opened_stat = os.fstat(fd)
        if not stat.S_ISREG(opened_stat.st_mode):
            return "cache_entry_not_regular_file"
        if (
            opened_stat.st_dev != entry_lstat.st_dev
            or opened_stat.st_ino != entry_lstat.st_ino
        ):
            return "cache_path_symlink_blocked"
        with os.fdopen(fd, "rb") as handle:
            fd = None
            return handle.read(max_entry_bytes + 1)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            return "cache_path_symlink_blocked"
        return "cache_entry_unreadable"
    finally:
        if fd is not None:
            os.close(fd)


def _parse_strict_json_object(text: str) -> Mapping[str, Any] | str:
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonstandard_json_number,
        )
    except _DuplicateJsonKeyError:
        return "cache_entry_duplicate_json_key"
    except _NonstandardJsonNumberError:
        return "cache_entry_nonstandard_number"
    except json.JSONDecodeError:
        return "cache_entry_malformed_json"
    if not isinstance(parsed, dict):
        return "cache_entry_not_object"
    return parsed


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise _DuplicateJsonKeyError(key)
        seen.add(key)
        result[key] = value
    return result


def _reject_nonstandard_json_number(value: str) -> None:
    raise _NonstandardJsonNumberError(value)


def _has_symlink_component(path: Path) -> bool:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    parts = candidate.parts
    if not parts:
        return False

    current = Path(parts[0])
    start_index = 1
    if current == Path("."):
        current = Path.cwd()
        start_index = 0
    for part in parts[start_index:]:
        current = current / part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                return True
        except OSError:
            return False
    return False


def _missing(
    miss_reason: str,
    *,
    max_entry_bytes: int,
) -> ClientInstructionCacheReadResult:
    return ClientInstructionCacheReadResult(
        schema_version=_SCHEMA_VERSION,
        status="missing",
        max_entry_bytes=max_entry_bytes,
        miss_reason=miss_reason,
    )


def _blocked(
    reason: str,
    *,
    entry_present: bool = False,
    bytes_read: int = 0,
    max_entry_bytes: int,
) -> ClientInstructionCacheReadResult:
    return ClientInstructionCacheReadResult(
        schema_version=_SCHEMA_VERSION,
        status="blocked",
        entry_present=entry_present,
        bytes_read=bytes_read,
        max_entry_bytes=max_entry_bytes,
        blocked_reasons=(reason,),
    )
