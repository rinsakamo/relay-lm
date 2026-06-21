"""Secure filesystem operations for the RelayMEM M3e page writer."""

from __future__ import annotations

import errno
import os
import secrets
import stat
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

_MAX_PAGE_BYTES = 8192


def write_or_inspect_primary_page(
    *,
    root_path: str | None,
    handoff: Mapping[str, Any],
    apply_requested: bool,
) -> dict[str, Any]:
    state = empty_primary_page_write_state()
    root_result = _open_root_directory(root_path)
    if root_result.get("valid") is not True:
        state["blocked_reasons"] = root_result["blocked_reasons"]
        return state

    root_fd = root_result["fd"]
    parent_fd = -1
    try:
        relative = PurePosixPath(str(handoff["target_relative_path"]))
        parent_result = _open_directory_parts(root_fd, relative.parts[:-1])
        if parent_result.get("valid") is not True:
            state["blocked_reasons"] = parent_result["blocked_reasons"]
            return state
        parent_fd = parent_result["fd"]
        filename = relative.parts[-1]
        existing = _inspect_existing(
            parent_fd=parent_fd,
            filename=filename,
            expected_digest=str(handoff["page_digest"]),
            expected_bytes=int(handoff["page_bytes"]),
        )
        if existing["status"] == "match":
            state.update(
                receipt_status="already_applied",
                idempotent_noop=True,
                durability_confirmed=False,
            )
            return state
        if existing["status"] == "conflict":
            state["blocked_reasons"] = ["primary_page_writer_target_conflict"]
            return state
        if existing["status"] == "invalid":
            state["blocked_reasons"] = existing["blocked_reasons"]
            return state

        state["target_absent"] = True
        if not apply_requested:
            state["receipt_status"] = "dry_run_ready"
            return state
        return _atomic_publish(parent_fd=parent_fd, filename=filename, handoff=handoff)
    finally:
        if parent_fd >= 0:
            os.close(parent_fd)
        os.close(root_fd)


def _open_root_directory(root_path: str | None) -> dict[str, Any]:
    if not isinstance(root_path, str):
        return _invalid("memory_store_root_not_configured")
    safe = root_path.strip()
    if safe != root_path or not safe or _bad(safe) or any(char in safe for char in "\n\r\t"):
        return _invalid("memory_store_root_invalid")
    if not _supports_secure_dirfd():
        return _invalid("primary_page_writer_platform_unsupported")

    absolute = Path(os.path.abspath(safe))
    parts = absolute.parts
    if not parts or not absolute.anchor:
        return _invalid("memory_store_root_invalid")
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(absolute.anchor, flags)
    except OSError:
        return _invalid("memory_store_root_unopenable")
    for part in parts[1:]:
        child = _open_child_directory(
            parent_fd=fd,
            name=part,
            missing_reason="memory_store_root_missing",
            invalid_reason="memory_store_root_not_directory",
            symlink_reason="memory_store_root_symlink_blocked",
            unopenable_reason="memory_store_root_unopenable",
        )
        if child.get("valid") is not True:
            os.close(fd)
            return child
        next_fd = child["fd"]
        os.close(fd)
        fd = next_fd
    return {"valid": True, "fd": fd, "blocked_reasons": []}


def _open_directory_parts(root_fd: int, parts: Sequence[str]) -> dict[str, Any]:
    try:
        fd = os.dup(root_fd)
    except OSError:
        return _invalid("memory_store_root_unopenable")
    for part in parts:
        if part in {"", ".", ".."}:
            os.close(fd)
            return _invalid("primary_page_writer_target_path_invalid")
        child = _open_child_directory(
            parent_fd=fd,
            name=part,
            missing_reason="memory_store_primary_target_directory_missing",
            invalid_reason="memory_store_primary_target_directory_invalid",
            symlink_reason="memory_store_target_symlink_blocked",
            unopenable_reason="memory_store_primary_target_directory_unopenable",
        )
        if child.get("valid") is not True:
            os.close(fd)
            return child
        next_fd = child["fd"]
        os.close(fd)
        fd = next_fd
    return {"valid": True, "fd": fd, "blocked_reasons": []}


def _open_child_directory(
    *,
    parent_fd: int,
    name: str,
    missing_reason: str,
    invalid_reason: str,
    symlink_reason: str,
    unopenable_reason: str,
) -> dict[str, Any]:
    try:
        before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return _invalid(missing_reason)
    except OSError:
        return _invalid(unopenable_reason)
    if stat.S_ISLNK(before.st_mode):
        return _invalid(symlink_reason)
    if not stat.S_ISDIR(before.st_mode):
        return _invalid(invalid_reason)
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    try:
        child_fd = os.open(
            name,
            flags | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except FileNotFoundError:
        return _invalid(missing_reason)
    except OSError:
        return _invalid(unopenable_reason)
    try:
        after = os.fstat(child_fd)
        if not stat.S_ISDIR(after.st_mode):
            os.close(child_fd)
            return _invalid(invalid_reason)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            os.close(child_fd)
            return _invalid(symlink_reason)
        return {"valid": True, "fd": child_fd, "blocked_reasons": []}
    except OSError:
        os.close(child_fd)
        return _invalid(unopenable_reason)


def _inspect_existing(
    *,
    parent_fd: int,
    filename: str,
    expected_digest: str,
    expected_bytes: int,
) -> dict[str, Any]:
    try:
        before = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return {"status": "absent", "blocked_reasons": []}
    except OSError:
        return {"status": "invalid", "blocked_reasons": ["memory_store_target_unreadable"]}
    if stat.S_ISLNK(before.st_mode):
        return {"status": "invalid", "blocked_reasons": ["memory_store_target_symlink_blocked"]}
    if not stat.S_ISREG(before.st_mode):
        return {"status": "invalid", "blocked_reasons": ["memory_store_target_not_file"]}
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(filename, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        return {"status": "absent", "blocked_reasons": []}
    except OSError:
        return {"status": "invalid", "blocked_reasons": ["memory_store_target_unreadable"]}
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return {"status": "invalid", "blocked_reasons": ["memory_store_target_not_file"]}
        if (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino):
            return {"status": "invalid", "blocked_reasons": ["memory_store_target_changed"]}
        chunks: list[bytes] = []
        remaining = _MAX_PAGE_BYTES + 1
        while remaining > 0:
            chunk = os.read(fd, min(4096, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > _MAX_PAGE_BYTES:
            return {"status": "invalid", "blocked_reasons": ["memory_store_target_size_exceeded"]}
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return {"status": "invalid", "blocked_reasons": ["memory_store_target_malformed_utf8"]}
        try:
            current = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return {"status": "invalid", "blocked_reasons": ["memory_store_target_changed"]}
        except OSError:
            return {"status": "invalid", "blocked_reasons": ["memory_store_target_unreadable"]}
        if stat.S_ISLNK(current.st_mode):
            return {"status": "invalid", "blocked_reasons": ["memory_store_target_symlink_blocked"]}
        if not stat.S_ISREG(current.st_mode):
            return {"status": "invalid", "blocked_reasons": ["memory_store_target_not_file"]}
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            return {"status": "invalid", "blocked_reasons": ["memory_store_target_changed"]}
        if len(data) == expected_bytes and sha256(data).hexdigest() == expected_digest:
            return {"status": "match", "blocked_reasons": []}
        return {"status": "conflict", "blocked_reasons": []}
    except OSError:
        return {"status": "invalid", "blocked_reasons": ["memory_store_target_unreadable"]}
    finally:
        os.close(fd)


def _atomic_publish(
    *,
    parent_fd: int,
    filename: str,
    handoff: Mapping[str, Any],
) -> dict[str, Any]:
    state = empty_primary_page_write_state()
    temp_name = f".relaymem-{handoff['idempotency_key']}-{secrets.token_hex(8)}.tmp"
    temp_created = False
    linked = False
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        temp_fd = os.open(temp_name, flags, 0o600, dir_fd=parent_fd)
        temp_created = True
        try:
            data = str(handoff["page_markdown"]).encode("utf-8")
            offset = 0
            while offset < len(data):
                written = os.write(temp_fd, data[offset:])
                if written <= 0:
                    raise OSError(errno.EIO, "short write")
                offset += written
            os.fsync(temp_fd)
            info = os.fstat(temp_fd)
            if info.st_size != int(handoff["page_bytes"]):
                state["blocked_reasons"] = ["primary_page_writer_temp_size_mismatch"]
                return state
        finally:
            os.close(temp_fd)

        try:
            os.link(
                temp_name,
                filename,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
            linked = True
            if not _published_target_matches(
                parent_fd=parent_fd,
                filename=filename,
                temp_info=info,
            ):
                state.update(
                    receipt_status="applied_state_uncertain",
                    writes_memory=True,
                    page_applied=True,
                    durability_confirmed=False,
                    cleanup_complete=False,
                    blocked_reasons=["primary_page_writer_published_target_changed"],
                )
                return state
        except FileExistsError:
            existing = _inspect_existing(
                parent_fd=parent_fd,
                filename=filename,
                expected_digest=str(handoff["page_digest"]),
                expected_bytes=int(handoff["page_bytes"]),
            )
            if existing["status"] == "match":
                state.update(
                    receipt_status="already_applied",
                    idempotent_noop=True,
                    durability_confirmed=False,
                )
                return state
            state["blocked_reasons"] = ["primary_page_writer_target_conflict"]
            return state

        try:
            os.fsync(parent_fd)
            if not _published_target_matches(
                parent_fd=parent_fd,
                filename=filename,
                temp_info=info,
            ):
                state.update(
                    receipt_status="applied_state_uncertain",
                    writes_memory=True,
                    page_applied=True,
                    durability_confirmed=False,
                    cleanup_complete=False,
                    blocked_reasons=["primary_page_writer_published_target_changed"],
                )
                return state
        except OSError:
            state.update(
                receipt_status="applied_durability_unconfirmed",
                writes_memory=True,
                page_applied=True,
                durability_confirmed=False,
                cleanup_complete=False,
                blocked_reasons=["primary_page_writer_directory_fsync_failed"],
            )
            return state

        try:
            os.unlink(temp_name, dir_fd=parent_fd)
            temp_created = False
            os.fsync(parent_fd)
        except OSError:
            state.update(
                receipt_status="applied_cleanup_incomplete",
                writes_memory=True,
                page_applied=True,
                durability_confirmed=True,
                cleanup_complete=False,
                blocked_reasons=["primary_page_writer_temp_cleanup_failed"],
            )
            return state

        state.update(
            receipt_status="applied",
            writes_memory=True,
            page_applied=True,
            durability_confirmed=True,
            cleanup_complete=True,
        )
        return state
    except OSError:
        state["blocked_reasons"] = ["primary_page_writer_apply_failed"]
        if linked:
            state.update(
                receipt_status="applied_state_uncertain",
                writes_memory=True,
                page_applied=True,
                durability_confirmed=False,
                cleanup_complete=False,
            )
        return state
    finally:
        if temp_created:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except OSError:
                state["cleanup_complete"] = False


def _published_target_matches(
    *,
    parent_fd: int,
    filename: str,
    temp_info: os.stat_result,
) -> bool:
    try:
        published = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        return False
    return (
        stat.S_ISREG(published.st_mode)
        and not stat.S_ISLNK(published.st_mode)
        and (published.st_dev, published.st_ino)
        == (temp_info.st_dev, temp_info.st_ino)
    )


def _supports_secure_dirfd() -> bool:
    required_dir_fd = {os.open, os.unlink, os.link, os.stat}
    required_no_follow = {os.link, os.stat}
    return (
        required_dir_fd.issubset(os.supports_dir_fd)
        and required_no_follow.issubset(os.supports_follow_symlinks)
        and hasattr(os, "O_DIRECTORY")
    )


def empty_primary_page_write_state() -> dict[str, Any]:
    return {
        "target_absent": False,
        "receipt_status": "",
        "writes_memory": False,
        "page_applied": False,
        "idempotent_noop": False,
        "durability_confirmed": False,
        "cleanup_complete": True,
        "blocked_reasons": [],
    }


def _invalid(*reasons: str) -> dict[str, Any]:
    return {
        "valid": False,
        "blocked_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
    }


def _bad(value: str) -> bool:
    return any(
        (ord(char) < 32 and char not in "\n\t")
        or 0xD800 <= ord(char) <= 0xDFFF
        for char in value
    )


__all__ = ["empty_primary_page_write_state", "write_or_inspect_primary_page"]
