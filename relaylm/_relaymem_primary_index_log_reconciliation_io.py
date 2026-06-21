"""Secure bounded read-only store access for RelayMEM M3f."""
from __future__ import annotations

import os
import stat
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from ._relaymem_primary_page_writer_common import bad_text


def read_store_file(
    *, root_path: str | None, relative_path: str, max_bytes: int, role: str
) -> dict[str, Any]:
    root = _open_root_directory(root_path)
    if root.get("valid") is not True:
        return root
    root_fd = root["fd"]
    parent_fd = -1
    try:
        parts = PurePosixPath(relative_path).parts
        parent = _open_directory_parts(root_fd, parts[:-1], role)
        if parent.get("valid") is not True:
            if (
                role == "page"
                and "primary_reconciliation_page_directory_missing"
                in parent["blocked_reasons"]
            ):
                return {"valid": False, "status": "missing", "blocked_reasons": []}
            return parent
        parent_fd = parent["fd"]
        return _read_regular_file(parent_fd, parts[-1], max_bytes, role)
    finally:
        if parent_fd >= 0:
            os.close(parent_fd)
        os.close(root_fd)


def _open_root_directory(root_path: str | None) -> dict[str, Any]:
    if not isinstance(root_path, str):
        return _invalid("memory_store_root_not_configured")
    safe = root_path.strip()
    if (
        safe != root_path
        or not safe
        or bad_text(safe)
        or any(char in safe for char in "\n\r\t")
    ):
        return _invalid("memory_store_root_invalid")
    if not _supports_secure_dirfd():
        return _invalid("primary_reconciliation_platform_unsupported")

    absolute = Path(os.path.abspath(safe))
    if not absolute.anchor:
        return _invalid("memory_store_root_invalid")
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(absolute.anchor, flags)
    except OSError:
        return _invalid("memory_store_root_unopenable")
    for part in absolute.parts[1:]:
        child = _open_child_directory(
            fd,
            part,
            "memory_store_root_missing",
            "memory_store_root_not_directory",
            "memory_store_root_symlink_blocked",
            "memory_store_root_unopenable",
        )
        if child.get("valid") is not True:
            os.close(fd)
            return child
        next_fd = child["fd"]
        os.close(fd)
        fd = next_fd
    return {"valid": True, "fd": fd, "blocked_reasons": []}


def _open_directory_parts(
    root_fd: int, parts: Sequence[str], role: str
) -> dict[str, Any]:
    try:
        fd = os.dup(root_fd)
    except OSError:
        return _invalid("memory_store_root_unopenable")
    for part in parts:
        if part in {"", ".", ".."}:
            os.close(fd)
            return _invalid("primary_reconciliation_path_invalid")
        missing = (
            "primary_reconciliation_page_directory_missing"
            if role == "page"
            else f"primary_reconciliation_{role}_directory_missing"
        )
        child = _open_child_directory(
            fd,
            part,
            missing,
            f"primary_reconciliation_{role}_directory_invalid",
            f"primary_reconciliation_{role}_symlink_blocked",
            f"primary_reconciliation_{role}_directory_unopenable",
        )
        if child.get("valid") is not True:
            os.close(fd)
            return child
        next_fd = child["fd"]
        os.close(fd)
        fd = next_fd
    return {"valid": True, "fd": fd, "blocked_reasons": []}


def _open_child_directory(
    parent_fd: int,
    name: str,
    missing: str,
    invalid: str,
    symlink: str,
    unopenable: str,
) -> dict[str, Any]:
    try:
        before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return _invalid(missing)
    except OSError:
        return _invalid(unopenable)
    if stat.S_ISLNK(before.st_mode):
        return _invalid(symlink)
    if not stat.S_ISDIR(before.st_mode):
        return _invalid(invalid)

    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    child_fd = -1
    try:
        child_fd = os.open(name, flags, dir_fd=parent_fd)
        after = os.fstat(child_fd)
    except OSError:
        if child_fd >= 0:
            os.close(child_fd)
        return _invalid(unopenable)
    if not stat.S_ISDIR(after.st_mode) or (before.st_dev, before.st_ino) != (
        after.st_dev,
        after.st_ino,
    ):
        os.close(child_fd)
        return _invalid(symlink)
    return {"valid": True, "fd": child_fd, "blocked_reasons": []}


def _read_regular_file(
    parent_fd: int, name: str, max_bytes: int, role: str
) -> dict[str, Any]:
    try:
        before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return {
            "valid": False,
            "status": "missing",
            "blocked_reasons": [f"primary_reconciliation_{role}_file_missing"],
        }
    except OSError:
        return _invalid(f"primary_reconciliation_{role}_file_unreadable")
    if stat.S_ISLNK(before.st_mode):
        return _invalid(f"primary_reconciliation_{role}_symlink_blocked")
    if not stat.S_ISREG(before.st_mode):
        return _invalid(f"primary_reconciliation_{role}_file_not_regular")
    if before.st_size > max_bytes:
        return _invalid(f"primary_reconciliation_{role}_size_exceeded")

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
    except OSError:
        return _invalid(f"primary_reconciliation_{role}_file_unreadable")
    try:
        opened = os.fstat(fd)
        identity = (opened.st_dev, opened.st_ino)
        if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != identity:
            return _invalid(f"primary_reconciliation_{role}_symlink_blocked")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(fd, min(8192, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > max_bytes:
            return _invalid(f"primary_reconciliation_{role}_size_exceeded")

        after_path = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        after_fd = os.fstat(fd)
        if (after_path.st_dev, after_path.st_ino) != identity or (
            after_fd.st_dev,
            after_fd.st_ino,
        ) != identity:
            return _invalid(f"primary_reconciliation_{role}_changed_during_read")
        before_state = (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        opened_state = (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
        after_state = (after_fd.st_size, after_fd.st_mtime_ns, after_fd.st_ctime_ns)
        path_state = (
            after_path.st_size,
            after_path.st_mtime_ns,
            after_path.st_ctime_ns,
        )
        if (
            before_state != opened_state
            or opened_state != after_state
            or after_state != path_state
            or after_fd.st_size != len(content)
        ):
            return _invalid(f"primary_reconciliation_{role}_changed_during_read")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return _invalid(f"primary_reconciliation_{role}_utf8_invalid")
        return {
            "valid": True,
            "status": "present",
            "content": content,
            "blocked_reasons": [],
        }
    except OSError:
        return _invalid(f"primary_reconciliation_{role}_file_unreadable")
    finally:
        os.close(fd)


def _supports_secure_dirfd() -> bool:
    return (
        {os.open, os.stat}.issubset(os.supports_dir_fd)
        and os.stat in os.supports_follow_symlinks
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    )


def _invalid(*reasons: str) -> dict[str, Any]:
    return {
        "valid": False,
        "blocked_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
    }


__all__ = ["read_store_file"]
