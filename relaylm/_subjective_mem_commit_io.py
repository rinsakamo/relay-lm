"""Secure POSIX dir-fd persistence for ST-1 Subjective MEM publication.

This helper is intentionally Subjective-MEM-specific.  It reuses the proven
M3e shape (component-by-component dir-fd traversal, O_NOFOLLOW, private staging,
fsync, atomic replacement, and post-install verification) without importing or
forging Primary MEM artifacts.
"""
from __future__ import annotations

import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Literal

from relaylm.character_workspace import (
    CharacterWorkspacePathKind,
    classify_character_workspace_path,
    validate_character_workspace,
)
from relaylm.portable_lock import (
    PortableLockUnavailable,
    acquire_portable_lock,
    release_portable_lock,
)
from relaylm.subjective_mem_markdown import (
    MAX_CANONICAL_PAGE_BYTES,
    MISSING_PAGE_DIGEST,
    canonical_page_digest,
)

PLATFORM_REVISION = "relaylm.subjective_mem_commit.posix_dirfd.v1"
ARTIFACT_DIRECTORY_PARTS = (
    ".relaylm",
    "state",
    "subjective_mem_st1",
    "artifacts",
)
LOCK_DIRECTORY_PARTS = (".relaylm", "state")
LOCK_FILENAME = "subjective_mem_st1.lock"

FaultInjector = Callable[[str], None]
InstalledVerifier = Callable[[bytes], bool]
InstalledFinalizer = Callable[[], bool]
PreImageValidator = Callable[[], bool]


@dataclass(frozen=True, repr=False)
class CanonicalPageSnapshot:
    state: Literal["absent", "present"]
    digest: str
    data: bytes | None


@dataclass(frozen=True)
class CanonicalPageInspectResult:
    snapshot: CanonicalPageSnapshot | None
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArtifactWriteResult:
    status: Literal["created", "duplicate_existing", "failed"]
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class CanonicalPublishResult:
    status: Literal[
        "published",
        "already_post_image",
        "pre_image_conflict",
        "lock_busy",
        "failed",
    ]
    installed_digest: str | None = None
    reasons: tuple[str, ...] = ()
    durability_confirmed: bool = False


def secure_platform_supported() -> bool:
    required = (
        hasattr(os, "O_DIRECTORY"),
        hasattr(os, "O_NOFOLLOW"),
        os.open in getattr(os, "supports_dir_fd", set()),
        os.stat in getattr(os, "supports_dir_fd", set()),
        os.rename in getattr(os, "supports_dir_fd", set()),
    )
    return os.name == "posix" and all(required)


def inspect_canonical_page(
    *, workspace_root: str, character_id: str, relative_path: str
) -> CanonicalPageInspectResult:
    opened, reasons = _open_workspace_page_parent(
        workspace_root=workspace_root,
        character_id=character_id,
        relative_path=relative_path,
    )
    if opened is None:
        return CanonicalPageInspectResult(None, reasons)
    root_fd, character_fd, parent_fd, filename = opened
    try:
        return _inspect_page_fd(parent_fd=parent_fd, filename=filename)
    finally:
        os.close(parent_fd)
        os.close(character_fd)
        os.close(root_fd)


def write_immutable_rendered_artifact(
    *,
    workspace_root: str,
    character_id: str,
    artifact_id: str,
    data: bytes,
) -> ArtifactWriteResult:
    if not _safe_component(artifact_id) or type(data) is not bytes:
        return ArtifactWriteResult("failed", ("subjective_mem_commit_artifact_invalid",))
    if len(data) > MAX_CANONICAL_PAGE_BYTES:
        return ArtifactWriteResult("failed", ("subjective_mem_commit_artifact_oversize",))
    opened, reasons = _open_character_root(
        workspace_root=workspace_root, character_id=character_id
    )
    if opened is None:
        return ArtifactWriteResult("failed", reasons)
    root_fd, character_fd = opened
    artifact_dir_fd = -1
    try:
        artifact_dir, reasons = _open_or_create_directory_parts(
            character_fd,
            ARTIFACT_DIRECTORY_PARTS,
            create_from_index=2,
        )
        if artifact_dir is None:
            return ArtifactWriteResult("failed", reasons)
        artifact_dir_fd = artifact_dir
        filename = artifact_id + ".md"
        existing, reasons = _read_regular_file_at(
            parent_fd=artifact_dir_fd,
            filename=filename,
            max_bytes=MAX_CANONICAL_PAGE_BYTES,
            missing_allowed=True,
        )
        if reasons:
            return ArtifactWriteResult("failed", reasons)
        if existing is not None:
            if existing != data:
                return ArtifactWriteResult(
                    "failed", ("subjective_mem_commit_artifact_collision",)
                )
            try:
                fd = os.open(
                    filename,
                    os.O_RDONLY
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=artifact_dir_fd,
                )
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
                _fsync_directory(artifact_dir_fd)
            except OSError:
                return ArtifactWriteResult(
                    "failed", ("subjective_mem_commit_artifact_durability_uncertain",)
                )
            return ArtifactWriteResult("duplicate_existing")
        result = _atomic_create_at(
            parent_fd=artifact_dir_fd,
            filename=filename,
            data=data,
            mode=0o600,
        )
        return result
    finally:
        if artifact_dir_fd >= 0:
            os.close(artifact_dir_fd)
        os.close(character_fd)
        os.close(root_fd)


def read_immutable_rendered_artifact(
    *, workspace_root: str, character_id: str, artifact_id: str
) -> tuple[bytes | None, tuple[str, ...]]:
    if not _safe_component(artifact_id):
        return None, ("subjective_mem_commit_artifact_invalid",)
    opened, reasons = _open_character_root(
        workspace_root=workspace_root, character_id=character_id
    )
    if opened is None:
        return None, reasons
    root_fd, character_fd = opened
    artifact_dir_fd = -1
    try:
        directory, reasons = _open_directory_parts(
            character_fd, ARTIFACT_DIRECTORY_PARTS
        )
        if directory is None:
            return None, reasons
        artifact_dir_fd = directory
        data, reasons = _read_regular_file_at(
            parent_fd=artifact_dir_fd,
            filename=artifact_id + ".md",
            max_bytes=MAX_CANONICAL_PAGE_BYTES,
            missing_allowed=False,
        )
        return data, reasons
    finally:
        if artifact_dir_fd >= 0:
            os.close(artifact_dir_fd)
        os.close(character_fd)
        os.close(root_fd)


def publish_canonical_page(
    *,
    workspace_root: str,
    character_id: str,
    relative_path: str,
    expected_pre_state: Literal["absent", "present"],
    expected_pre_digest: str,
    post_image: bytes,
    expected_post_digest: str,
    verify_installed: InstalledVerifier,
    finalize_installed: InstalledFinalizer | None = None,
    validate_pre_image: PreImageValidator | None = None,
    fault_injector: FaultInjector | None = None,
) -> CanonicalPublishResult:
    if type(post_image) is not bytes or len(post_image) > MAX_CANONICAL_PAGE_BYTES:
        return _publish_failed("subjective_mem_commit_post_image_invalid")
    if canonical_page_digest(post_image) != expected_post_digest:
        return _publish_failed("subjective_mem_commit_post_image_digest_invalid")
    opened, reasons = _open_character_root(
        workspace_root=workspace_root, character_id=character_id
    )
    if opened is None:
        return CanonicalPublishResult("failed", reasons=reasons)
    root_fd, character_fd = opened
    lock_dir_fd = -1
    lock_fd = -1
    parent_fd = -1
    try:
        lock_dir, reasons = _open_directory_parts(character_fd, LOCK_DIRECTORY_PARTS)
        if lock_dir is None:
            return CanonicalPublishResult("failed", reasons=reasons)
        lock_dir_fd = lock_dir
        try:
            lock_fd = os.open(
                LOCK_FILENAME,
                os.O_RDWR
                | os.O_CREAT
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=lock_dir_fd,
            )
            lock_info = os.fstat(lock_fd)
            if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_nlink != 1:
                return _publish_failed("subjective_mem_commit_writer_lock_invalid")
            acquire_portable_lock(lock_fd, mode="exclusive", blocking=False)
        except PortableLockUnavailable:
            return CanonicalPublishResult(
                "lock_busy", reasons=("subjective_mem_commit_writer_lock_busy",)
            )
        except OSError:
            return _publish_failed("subjective_mem_commit_writer_lock_unavailable")

        relative, reasons = _validate_page_relative_path(relative_path)
        if relative is None:
            return CanonicalPublishResult("failed", reasons=reasons)
        parent, reasons = _open_directory_parts(character_fd, relative.parts[:-1])
        if parent is None:
            return CanonicalPublishResult("failed", reasons=reasons)
        parent_fd = parent
        filename = relative.parts[-1]
        snapshot_result = _inspect_page_fd(parent_fd=parent_fd, filename=filename)
        if snapshot_result.snapshot is None:
            return CanonicalPublishResult("failed", reasons=snapshot_result.reasons)
        snapshot = snapshot_result.snapshot
        if snapshot.digest == expected_post_digest:
            if snapshot.data != post_image or not _safe_verify(
                verify_installed, snapshot.data
            ):
                return _publish_failed("subjective_mem_commit_post_image_unverifiable")
            try:
                _fsync_directory(parent_fd)
            except OSError:
                return CanonicalPublishResult(
                    "failed",
                    installed_digest=snapshot.digest,
                    reasons=("subjective_mem_commit_durability_uncertain",),
                )
            if finalize_installed is not None and not _safe_finalize(finalize_installed):
                return CanonicalPublishResult(
                    "failed",
                    installed_digest=snapshot.digest,
                    reasons=("subjective_mem_commit_receipt_finalization_failed",),
                    durability_confirmed=True,
                )
            return CanonicalPublishResult(
                "already_post_image",
                installed_digest=snapshot.digest,
                durability_confirmed=True,
            )
        if (
            snapshot.state != expected_pre_state
            or snapshot.digest != expected_pre_digest
        ):
            return CanonicalPublishResult(
                "pre_image_conflict",
                installed_digest=snapshot.digest,
                reasons=("subjective_mem_commit_foreign_image",),
            )
        if validate_pre_image is not None and not _safe_finalize(validate_pre_image):
            return _publish_failed("subjective_mem_commit_pre_image_authority_changed")
        _fault(fault_injector, "before_staging")
        result = _atomic_replace_at(
            parent_fd=parent_fd,
            filename=filename,
            expected_pre_state=expected_pre_state,
            expected_pre_digest=expected_pre_digest,
            data=post_image,
            verify_installed=verify_installed,
            finalize_installed=finalize_installed,
            fault_injector=fault_injector,
        )
        return result
    except (OSError, RuntimeError, TypeError, ValueError):
        return _publish_failed("subjective_mem_commit_writer_failed")
    finally:
        if parent_fd >= 0:
            os.close(parent_fd)
        if lock_fd >= 0:
            try:
                release_portable_lock(lock_fd)
            except OSError:
                pass
            os.close(lock_fd)
        if lock_dir_fd >= 0:
            os.close(lock_dir_fd)
        os.close(character_fd)
        os.close(root_fd)


def _open_workspace_page_parent(
    *, workspace_root: str, character_id: str, relative_path: str
) -> tuple[tuple[int, int, int, str] | None, tuple[str, ...]]:
    opened, reasons = _open_character_root(
        workspace_root=workspace_root, character_id=character_id
    )
    if opened is None:
        return None, reasons
    root_fd, character_fd = opened
    relative, reasons = _validate_page_relative_path(relative_path)
    if relative is None:
        os.close(character_fd)
        os.close(root_fd)
        return None, reasons
    parent, reasons = _open_directory_parts(character_fd, relative.parts[:-1])
    if parent is None:
        os.close(character_fd)
        os.close(root_fd)
        return None, reasons
    return (root_fd, character_fd, parent, relative.parts[-1]), ()


def _open_character_root(
    *, workspace_root: str, character_id: str
) -> tuple[tuple[int, int] | None, tuple[str, ...]]:
    if not secure_platform_supported():
        return None, ("subjective_mem_commit_platform_unsupported",)
    if not _safe_component(character_id):
        return None, ("subjective_mem_commit_character_id_invalid",)
    if type(workspace_root) is not str or not workspace_root:
        return None, ("subjective_mem_commit_workspace_root_missing",)
    root_path = Path(workspace_root)
    if not root_path.is_absolute() or any(
        part in {".", ".."} for part in root_path.parts[1:]
    ):
        return None, ("subjective_mem_commit_workspace_root_invalid",)
    root_fd, reasons = _open_absolute_directory(root_path)
    if root_fd is None:
        return None, reasons
    character_fd, reasons = _open_child_directory(
        root_fd,
        character_id,
        missing="subjective_mem_commit_character_workspace_missing",
        invalid="subjective_mem_commit_character_workspace_invalid",
        symlink="subjective_mem_commit_character_workspace_symlink",
    )
    if character_fd is None:
        os.close(root_fd)
        return None, reasons
    validation = validate_character_workspace(
        root_path / character_id, character_id=character_id, public=False
    )
    try:
        root_path_info = os.stat(root_path, follow_symlinks=False)
        character_path_info = os.stat(
            character_id, dir_fd=root_fd, follow_symlinks=False
        )
        root_fd_info = os.fstat(root_fd)
        character_fd_info = os.fstat(character_fd)
    except OSError:
        os.close(character_fd)
        os.close(root_fd)
        return None, ("subjective_mem_commit_workspace_authority_changed",)
    if (
        not getattr(validation, "is_valid", False)
        or stat.S_ISLNK(root_path_info.st_mode)
        or stat.S_ISLNK(character_path_info.st_mode)
        or (root_path_info.st_dev, root_path_info.st_ino)
        != (root_fd_info.st_dev, root_fd_info.st_ino)
        or (character_path_info.st_dev, character_path_info.st_ino)
        != (character_fd_info.st_dev, character_fd_info.st_ino)
    ):
        os.close(character_fd)
        os.close(root_fd)
        return None, ("subjective_mem_commit_character_workspace_not_valid",)
    return (root_fd, character_fd), ()


def _validate_page_relative_path(
    relative_path: str,
) -> tuple[PurePosixPath | None, tuple[str, ...]]:
    if type(relative_path) is not str or not relative_path:
        return None, ("subjective_mem_commit_target_path_invalid",)
    classification = classify_character_workspace_path(relative_path)
    if (
        classification.kind != CharacterWorkspacePathKind.MEMORY_PAGE
        or classification.normalized_path != relative_path
        or relative_path.startswith(".relaylm/")
        or "primary" in PurePosixPath(relative_path).parts
    ):
        return None, ("subjective_mem_commit_target_path_invalid",)
    relative = PurePosixPath(relative_path)
    if any(part in {"", ".", ".."} for part in relative.parts):
        return None, ("subjective_mem_commit_target_path_invalid",)
    return relative, ()


def _open_absolute_directory(
    path: Path,
) -> tuple[int | None, tuple[str, ...]]:
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path.anchor, flags)
    except OSError:
        return None, ("subjective_mem_commit_workspace_root_unopenable",)
    for part in path.parts[1:]:
        child, reasons = _open_child_directory(
            fd,
            part,
            missing="subjective_mem_commit_workspace_root_missing",
            invalid="subjective_mem_commit_workspace_root_invalid",
            symlink="subjective_mem_commit_workspace_root_symlink",
        )
        if child is None:
            os.close(fd)
            return None, reasons
        os.close(fd)
        fd = child
    return fd, ()


def _open_directory_parts(
    root_fd: int, parts: tuple[str, ...]
) -> tuple[int | None, tuple[str, ...]]:
    try:
        fd = os.dup(root_fd)
    except OSError:
        return None, ("subjective_mem_commit_directory_unopenable",)
    for part in parts:
        if not _safe_component(part):
            os.close(fd)
            return None, ("subjective_mem_commit_target_path_invalid",)
        child, reasons = _open_child_directory(
            fd,
            part,
            missing="subjective_mem_commit_target_parent_missing",
            invalid="subjective_mem_commit_target_parent_invalid",
            symlink="subjective_mem_commit_target_parent_symlink",
        )
        if child is None:
            os.close(fd)
            return None, reasons
        os.close(fd)
        fd = child
    return fd, ()


def _open_or_create_directory_parts(
    root_fd: int,
    parts: tuple[str, ...],
    *,
    create_from_index: int,
) -> tuple[int | None, tuple[str, ...]]:
    try:
        fd = os.dup(root_fd)
    except OSError:
        return None, ("subjective_mem_commit_directory_unopenable",)
    for index, part in enumerate(parts):
        if not _safe_component(part):
            os.close(fd)
            return None, ("subjective_mem_commit_artifact_path_invalid",)
        if index >= create_from_index:
            try:
                os.mkdir(part, 0o700, dir_fd=fd)
                _fsync_directory(fd)
            except FileExistsError:
                pass
            except OSError:
                os.close(fd)
                return None, ("subjective_mem_commit_artifact_directory_failed",)
        child, reasons = _open_child_directory(
            fd,
            part,
            missing="subjective_mem_commit_artifact_parent_missing",
            invalid="subjective_mem_commit_artifact_parent_invalid",
            symlink="subjective_mem_commit_artifact_parent_symlink",
        )
        if child is None:
            os.close(fd)
            return None, reasons
        os.close(fd)
        fd = child
    return fd, ()


def _open_child_directory(
    parent_fd: int,
    name: str,
    *,
    missing: str,
    invalid: str,
    symlink: str,
) -> tuple[int | None, tuple[str, ...]]:
    try:
        before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None, (missing,)
    except OSError:
        return None, (invalid,)
    if stat.S_ISLNK(before.st_mode):
        return None, (symlink,)
    if not stat.S_ISDIR(before.st_mode):
        return None, (invalid,)
    child_fd = -1
    try:
        child_fd = os.open(
            name,
            os.O_RDONLY
            | os.O_DIRECTORY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        after = os.fstat(child_fd)
    except OSError:
        if child_fd >= 0:
            os.close(child_fd)
        return None, (invalid,)
    if (
        not stat.S_ISDIR(after.st_mode)
        or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
    ):
        os.close(child_fd)
        return None, (symlink,)
    return child_fd, ()


def _inspect_page_fd(
    *, parent_fd: int, filename: str
) -> CanonicalPageInspectResult:
    data, reasons = _read_regular_file_at(
        parent_fd=parent_fd,
        filename=filename,
        max_bytes=MAX_CANONICAL_PAGE_BYTES,
        missing_allowed=True,
    )
    if reasons:
        return CanonicalPageInspectResult(None, reasons)
    if data is None:
        return CanonicalPageInspectResult(
            CanonicalPageSnapshot("absent", MISSING_PAGE_DIGEST, None)
        )
    return CanonicalPageInspectResult(
        CanonicalPageSnapshot("present", canonical_page_digest(data), data)
    )


def _read_regular_file_at(
    *, parent_fd: int, filename: str, max_bytes: int, missing_allowed: bool
) -> tuple[bytes | None, tuple[str, ...]]:
    if not _safe_component(filename):
        return None, ("subjective_mem_commit_target_path_invalid",)
    try:
        before = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return (
            (None, ())
            if missing_allowed
            else (None, ("subjective_mem_commit_file_missing",))
        )
    except OSError:
        return None, ("subjective_mem_commit_file_unreadable",)
    if stat.S_ISLNK(before.st_mode):
        return None, ("subjective_mem_commit_target_symlink",)
    if not stat.S_ISREG(before.st_mode):
        return None, ("subjective_mem_commit_target_not_regular",)
    if before.st_nlink != 1:
        return None, ("subjective_mem_commit_target_link_count_invalid",)
    try:
        fd = os.open(
            filename,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except OSError:
        return None, ("subjective_mem_commit_file_unreadable",)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino)
        ):
            return None, ("subjective_mem_commit_target_changed",)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                return None, ("subjective_mem_commit_file_oversize",)
        data = b"".join(chunks)
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return None, ("subjective_mem_commit_file_not_utf8",)
        current = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
        if (
            stat.S_ISLNK(current.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino)
        ):
            return None, ("subjective_mem_commit_target_changed",)
        return data, ()
    except OSError:
        return None, ("subjective_mem_commit_file_unreadable",)
    finally:
        os.close(fd)


def _atomic_create_at(
    *, parent_fd: int, filename: str, data: bytes, mode: int
) -> ArtifactWriteResult:
    temp = "." + filename + "." + secrets.token_hex(8) + ".tmp"
    temp_created = False
    try:
        fd = os.open(
            temp,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            mode,
            dir_fd=parent_fd,
        )
        temp_created = True
        try:
            _write_all(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.link(
                temp,
                filename,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            existing, reasons = _read_regular_file_at(
                parent_fd=parent_fd,
                filename=filename,
                max_bytes=MAX_CANONICAL_PAGE_BYTES,
                missing_allowed=False,
            )
            if reasons or existing != data:
                return ArtifactWriteResult(
                    "failed", ("subjective_mem_commit_artifact_collision",)
                )
            try:
                existing_fd = os.open(
                    filename,
                    os.O_RDONLY
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=parent_fd,
                )
                try:
                    os.fsync(existing_fd)
                finally:
                    os.close(existing_fd)
            except OSError:
                return ArtifactWriteResult(
                    "failed",
                    ("subjective_mem_commit_artifact_durability_uncertain",),
                )
            if not _remove_temp_and_sync(
                parent_fd=parent_fd, temp=temp
            ):
                return ArtifactWriteResult(
                    "failed", ("subjective_mem_commit_artifact_cleanup_failed",)
                )
            temp_created = False
            return ArtifactWriteResult("duplicate_existing")
        if not _remove_temp_and_sync(parent_fd=parent_fd, temp=temp):
            return ArtifactWriteResult(
                "failed", ("subjective_mem_commit_artifact_cleanup_failed",)
            )
        temp_created = False
        return ArtifactWriteResult("created")
    except OSError:
        return ArtifactWriteResult(
            "failed", ("subjective_mem_commit_artifact_write_failed",)
        )
    finally:
        if temp_created:
            try:
                os.unlink(temp, dir_fd=parent_fd)
                _fsync_directory(parent_fd)
            except OSError:
                pass


def _remove_temp_and_sync(*, parent_fd: int, temp: str) -> bool:
    try:
        os.unlink(temp, dir_fd=parent_fd)
        _fsync_directory(parent_fd)
    except OSError:
        return False
    return True


def _atomic_replace_at(
    *,
    parent_fd: int,
    filename: str,
    expected_pre_state: Literal["absent", "present"],
    expected_pre_digest: str,
    data: bytes,
    verify_installed: InstalledVerifier,
    finalize_installed: InstalledFinalizer | None,
    fault_injector: FaultInjector | None,
) -> CanonicalPublishResult:
    temp = "." + filename + "." + secrets.token_hex(8) + ".tmp"
    temp_created = False
    replaced = False
    try:
        fd = os.open(
            temp,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent_fd,
        )
        temp_created = True
        staged_info = None
        try:
            _write_all(fd, data)
            os.fsync(fd)
            staged_info = os.fstat(fd)
            if not stat.S_ISREG(staged_info.st_mode) or staged_info.st_nlink != 1:
                return _publish_failed("subjective_mem_commit_staging_not_regular")
        finally:
            os.close(fd)
        _fault(fault_injector, "after_staging_before_replace")
        immediate = _inspect_page_fd(parent_fd=parent_fd, filename=filename)
        if immediate.snapshot is None:
            return CanonicalPublishResult("failed", reasons=immediate.reasons)
        if (
            immediate.snapshot.state != expected_pre_state
            or immediate.snapshot.digest != expected_pre_digest
        ):
            return CanonicalPublishResult(
                "pre_image_conflict",
                installed_digest=immediate.snapshot.digest,
                reasons=("subjective_mem_commit_foreign_image",),
            )
        os.rename(
            temp,
            filename,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        temp_created = False
        replaced = True
        _fault(fault_injector, "after_replace_before_verify")
        installed, reasons = _read_regular_file_at(
            parent_fd=parent_fd,
            filename=filename,
            max_bytes=MAX_CANONICAL_PAGE_BYTES,
            missing_allowed=False,
        )
        try:
            installed_info = os.stat(
                filename, dir_fd=parent_fd, follow_symlinks=False
            )
        except OSError:
            installed_info = None
        if (
            reasons
            or installed != data
            or staged_info is None
            or installed_info is None
            or (installed_info.st_dev, installed_info.st_ino)
            != (staged_info.st_dev, staged_info.st_ino)
        ):
            return CanonicalPublishResult(
                "failed",
                reasons=("subjective_mem_commit_post_install_mismatch",),
            )
        if not _safe_verify(verify_installed, installed):
            return CanonicalPublishResult(
                "failed",
                installed_digest=canonical_page_digest(installed),
                reasons=("subjective_mem_commit_post_image_lineage_invalid",),
            )
        _fault(fault_injector, "after_verify_before_directory_fsync")
        _fsync_directory(parent_fd)
        if finalize_installed is not None and not _safe_finalize(finalize_installed):
            return CanonicalPublishResult(
                "failed",
                installed_digest=canonical_page_digest(installed),
                reasons=("subjective_mem_commit_receipt_finalization_failed",),
                durability_confirmed=True,
            )
        return CanonicalPublishResult(
            "published",
            installed_digest=canonical_page_digest(installed),
            durability_confirmed=True,
        )
    except OSError:
        return CanonicalPublishResult(
            "failed",
            reasons=(
                "subjective_mem_commit_durability_uncertain"
                if replaced
                else "subjective_mem_commit_replace_failed"
            ,),
        )
    finally:
        if temp_created:
            try:
                os.unlink(temp, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            except OSError:
                pass


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short write")
        view = view[written:]


def _fsync_directory(fd: int) -> None:
    os.fsync(fd)


def _fault(injector: FaultInjector | None, stage: str) -> None:
    if injector is not None:
        injector(stage)


def _safe_finalize(finalizer: InstalledFinalizer) -> bool:
    try:
        return finalizer() is True
    except Exception:
        return False


def _safe_verify(verifier: InstalledVerifier, data: bytes | None) -> bool:
    if data is None:
        return False
    try:
        return verifier(data) is True
    except Exception:
        return False


def _publish_failed(reason: str) -> CanonicalPublishResult:
    return CanonicalPublishResult("failed", reasons=(reason,))


def _safe_component(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 256
        and value not in {".", ".."}
        and all(ch not in value for ch in ("/", "\\", "\x00", "\n", "\r"))
    )


__all__ = [
    "ARTIFACT_DIRECTORY_PARTS",
    "CanonicalPageInspectResult",
    "CanonicalPageSnapshot",
    "CanonicalPublishResult",
    "PLATFORM_REVISION",
    "inspect_canonical_page",
    "publish_canonical_page",
    "read_immutable_rendered_artifact",
    "secure_platform_supported",
    "write_immutable_rendered_artifact",
]
