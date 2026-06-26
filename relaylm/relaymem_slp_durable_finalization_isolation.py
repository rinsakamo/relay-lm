"""Immutable content-free isolation marker for I1-GD maintenance.

The marker filename deliberately occupies a reserved non-segment member of the
existing I1-G component namespace.  I1-GC's canonical segment inventory sees it
as an unexpected component and therefore fails closed even when a crash leaves
sealed evidence beside the marker.  I1-GD is the only authority that interprets
this exact filename as a valid isolation record.
"""
from __future__ import annotations

import errno
import hashlib
import os
import re
import secrets
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from .relaymem_slp_durable_finalization_record import (
    RECORD_SCHEMA,
    canonical_json_bytes,
    decode_canonical_json,
)
from .relaymem_slp_durable_finalization_store import (
    _open_store_root,
    _read_bounded,
    _rename_noreplace,
    _write_all,
)
from .relaymem_slp_queue_record import dedupe

ISOLATION_SCHEMA = "relaymem.slp_durable_finalization_isolation.v0"
ISOLATION_REVISION = 0
ISOLATION_FIELDS = frozenset({
    "schema_version",
    "runtime_private",
    "content_included",
    "record_kind",
    "record_revision",
    "locator_digest",
    "sealed_record_schema",
    "classification",
    "reason_id",
    "observed_component_flags",
    "isolation_digest",
})
OBSERVED_COMPONENT_FIELDS = frozenset({
    "base_present",
    "segment_present",
    "seal_present",
    "completion_present",
    "corrupt_observed",
    "unsupported_observed",
})
ISOLATION_MAX_BYTES = 16 * 1024
_PREFIX = "durable-finalization-v0-"
_SUFFIX = ".segment-isolation.json"
_TOKEN = re.compile(r"^[a-z][a-z0-9_]{0,95}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_MAX_REASONS = 16

IsolationStatus = Literal[
    "absent",
    "loaded",
    "published_new",
    "duplicate_existing",
    "collision",
    "corrupt",
    "unsafe",
    "ambiguous",
    "failed",
]


@dataclass(frozen=True, repr=False)
class RelayMEMSLPDurableFinalizationIsolationResult:
    status: IsolationStatus
    present: bool
    durable: bool
    duplicate_existing: bool = False
    reason_ids: tuple[str, ...] = ()
    marker: dict[str, object] | None = field(default=None, repr=False, compare=False)
    mtime_ns: int | None = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationIsolationResult("
            f"status={self.status!r}, present={self.present!r}, "
            "content_free=True, identifier_values_omitted=True)"
        )


def isolation_filename(locator_digest: str) -> str:
    if not _is_digest(locator_digest):
        raise ValueError("durable_finalization_isolation_locator_invalid")
    return f"{_PREFIX}{locator_digest}{_SUFFIX}"


def build_isolation_marker(
    *,
    locator_digest: str,
    classification: str,
    reason_id: str,
    observed_component_flags: Mapping[str, object],
) -> dict[str, object]:
    marker: dict[str, object] = {
        "schema_version": ISOLATION_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "record_kind": "isolation",
        "record_revision": ISOLATION_REVISION,
        "locator_digest": locator_digest,
        "sealed_record_schema": RECORD_SCHEMA,
        "classification": classification,
        "reason_id": reason_id,
        "observed_component_flags": dict(observed_component_flags),
    }
    marker["isolation_digest"] = _hash_without(marker, "isolation_digest")
    validated, reasons = validate_isolation_marker(
        marker,
        expected_locator=locator_digest,
    )
    if validated is None or reasons:
        raise ValueError(
            reasons[0] if reasons else "durable_finalization_isolation_invalid"
        )
    return validated


def validate_isolation_marker(
    value: object,
    *,
    expected_locator: str | None = None,
    expected: Mapping[str, object] | None = None,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("durable_finalization_isolation_shape_invalid",)
    reasons: list[str] = []
    if len(value) != len(ISOLATION_FIELDS) or set(value) != ISOLATION_FIELDS:
        reasons.append("durable_finalization_isolation_shape_mismatch")
    fixed = {
        "schema_version": ISOLATION_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "record_kind": "isolation",
        "record_revision": ISOLATION_REVISION,
        "sealed_record_schema": RECORD_SCHEMA,
    }
    for key, wanted in fixed.items():
        if value.get(key) != wanted:
            reasons.append(f"durable_finalization_isolation_{key}_mismatch")
    locator = value.get("locator_digest")
    if not _is_digest(locator):
        reasons.append("durable_finalization_isolation_locator_invalid")
    if expected_locator is not None and locator != expected_locator:
        reasons.append("durable_finalization_isolation_locator_mismatch")
    for key in ("classification", "reason_id"):
        candidate = value.get(key)
        if type(candidate) is not str or _TOKEN.fullmatch(candidate) is None:
            reasons.append(f"durable_finalization_isolation_{key}_invalid")
    flags = value.get("observed_component_flags")
    if type(flags) is not dict:
        reasons.append("durable_finalization_isolation_flags_invalid")
    else:
        if len(flags) != len(OBSERVED_COMPONENT_FIELDS) or set(flags) != OBSERVED_COMPONENT_FIELDS:
            reasons.append("durable_finalization_isolation_flags_shape_mismatch")
        for key in OBSERVED_COMPONENT_FIELDS:
            if type(flags.get(key)) is not bool:
                reasons.append("durable_finalization_isolation_flags_value_invalid")
                break
    if value.get("isolation_digest") != _hash_without(value, "isolation_digest"):
        reasons.append("durable_finalization_isolation_digest_mismatch")
    if expected is not None:
        try:
            if canonical_json_bytes(value) != canonical_json_bytes(expected):
                reasons.append("durable_finalization_isolation_identity_collision")
        except (TypeError, ValueError, RecursionError, OverflowError):
            reasons.append("durable_finalization_isolation_compare_failed")
    bounded = dedupe(tuple(reasons))[:_MAX_REASONS]
    return (dict(value), ()) if not bounded else (None, bounded)


def read_relaymem_slp_durable_finalization_isolation(
    root: str,
    locator_digest: str,
) -> RelayMEMSLPDurableFinalizationIsolationResult:
    root_fd, reasons = _open_store_root(root)
    if root_fd is None:
        return _result("failed", reasons)
    try:
        return read_relaymem_slp_durable_finalization_isolation_fd(
            root_fd,
            locator_digest,
        )
    finally:
        os.close(root_fd)


def read_relaymem_slp_durable_finalization_isolation_fd(
    root_fd: int,
    locator_digest: str,
    *,
    expected: Mapping[str, object] | None = None,
) -> RelayMEMSLPDurableFinalizationIsolationResult:
    try:
        name = isolation_filename(locator_digest)
    except ValueError:
        return _result(
            "corrupt",
            ("durable_finalization_isolation_locator_invalid",),
        )
    value, info, status, reasons = _read_named(root_fd, name)
    if status == "absent":
        return _result("absent", ())
    if status != "ok" or value is None or info is None:
        return _result(status, reasons, present=True)
    validated, marker_reasons = validate_isolation_marker(
        value,
        expected_locator=locator_digest,
        expected=expected,
    )
    if validated is None or marker_reasons:
        collision = (
            marker_reasons == ("durable_finalization_isolation_identity_collision",)
        )
        return _result(
            "collision" if collision else "corrupt",
            marker_reasons,
            present=True,
            mtime_ns=info.st_mtime_ns,
        )
    return _result(
        "loaded",
        (),
        present=True,
        durable=True,
        marker=validated,
        mtime_ns=info.st_mtime_ns,
    )


def publish_relaymem_slp_durable_finalization_isolation(
    root: str,
    marker: Mapping[str, object],
) -> RelayMEMSLPDurableFinalizationIsolationResult:
    validated, reasons = validate_isolation_marker(marker)
    if validated is None or reasons:
        return _result("corrupt", reasons)
    data = canonical_json_bytes(validated)
    if len(data) > ISOLATION_MAX_BYTES:
        return _result(
            "corrupt",
            ("durable_finalization_isolation_size_exceeded",),
        )
    locator = str(validated["locator_digest"])
    root_fd, root_reasons = _open_store_root(root)
    if root_fd is None:
        return _result("failed", root_reasons)
    temp = f".durable-finalization-isolation-{secrets.token_hex(16)}.tmp"
    temp_exists = False
    try:
        current = read_relaymem_slp_durable_finalization_isolation_fd(
            root_fd,
            locator,
            expected=validated,
        )
        if current.status == "loaded":
            return _result(
                "duplicate_existing",
                (),
                present=True,
                durable=True,
                duplicate_existing=True,
                marker=current.marker,
                mtime_ns=current.mtime_ns,
            )
        if current.status != "absent":
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
            return _result(
                "failed",
                ("durable_finalization_isolation_temp_create_failed",),
            )
        try:
            _write_all(fd, data)
            os.fsync(fd)
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_size != len(data)
            ):
                raise OSError(errno.EIO, "unsafe isolation temp")
        except OSError:
            return _result(
                "failed",
                ("durable_finalization_isolation_temp_write_failed",),
            )
        finally:
            os.close(fd)
        outcome = _rename_noreplace(root_fd, temp, isolation_filename(locator))
        if outcome == "published":
            temp_exists = False
            fsync_failed = False
            try:
                os.fsync(root_fd)
            except OSError:
                fsync_failed = True
            reread = read_relaymem_slp_durable_finalization_isolation_fd(
                root_fd,
                locator,
                expected=validated,
            )
            if reread.status != "loaded":
                return reread
            if fsync_failed:
                return _result(
                    "ambiguous",
                    ("durable_finalization_isolation_directory_fsync_ambiguous",),
                    present=True,
                    marker=reread.marker,
                    mtime_ns=reread.mtime_ns,
                )
            return _result(
                "published_new",
                (),
                present=True,
                durable=True,
                marker=reread.marker,
                mtime_ns=reread.mtime_ns,
            )
        if outcome == "exists":
            reread = read_relaymem_slp_durable_finalization_isolation_fd(
                root_fd,
                locator,
                expected=validated,
            )
            if reread.status == "loaded":
                return _result(
                    "duplicate_existing",
                    (),
                    present=True,
                    durable=True,
                    duplicate_existing=True,
                    marker=reread.marker,
                    mtime_ns=reread.mtime_ns,
                )
            return reread
        reread = read_relaymem_slp_durable_finalization_isolation_fd(
            root_fd,
            locator,
            expected=validated,
        )
        if reread.status == "loaded":
            return _result(
                "ambiguous",
                ("durable_finalization_isolation_atomic_publish_ambiguous",),
                present=True,
                marker=reread.marker,
                mtime_ns=reread.mtime_ns,
            )
        return _result(
            "failed",
            reread.reason_ids
            or ("durable_finalization_isolation_atomic_publish_failed",),
        )
    finally:
        if temp_exists:
            try:
                os.unlink(temp, dir_fd=root_fd)
                os.fsync(root_fd)
            except OSError:
                pass
        os.close(root_fd)


def _read_named(
    root_fd: int,
    name: str,
) -> tuple[dict[str, object] | None, os.stat_result | None, str, tuple[str, ...]]:
    try:
        before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None, None, "absent", ()
    except OSError:
        return None, None, "failed", (
            "durable_finalization_isolation_unreadable",
        )
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        return None, before, "unsafe", (
            "durable_finalization_isolation_unsafe_file_type",
        )
    if before.st_nlink != 1:
        return None, before, "unsafe", (
            "durable_finalization_isolation_hardlink_invalid",
        )
    if before.st_size > ISOLATION_MAX_BYTES:
        return None, before, "corrupt", (
            "durable_finalization_isolation_size_exceeded",
        )
    try:
        fd = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=root_fd,
        )
    except OSError:
        return None, before, "failed", (
            "durable_finalization_isolation_unreadable",
        )
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino)
            or before.st_size != info.st_size
            or before.st_mtime_ns != info.st_mtime_ns
        ):
            return None, info, "unsafe", (
                "durable_finalization_isolation_changed_during_read",
            )
        data = _read_bounded(fd, ISOLATION_MAX_BYTES)
    finally:
        os.close(fd)
    if data is None:
        return None, info, "corrupt", (
            "durable_finalization_isolation_size_exceeded",
        )
    try:
        after = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except OSError:
        return None, info, "unsafe", (
            "durable_finalization_isolation_changed_during_read",
        )
    if (
        stat.S_ISLNK(after.st_mode)
        or not stat.S_ISREG(after.st_mode)
        or after.st_nlink != 1
        or (after.st_dev, after.st_ino) != (info.st_dev, info.st_ino)
        or after.st_size != info.st_size
        or after.st_mtime_ns != info.st_mtime_ns
    ):
        return None, info, "unsafe", (
            "durable_finalization_isolation_changed_during_read",
        )
    value, reason = decode_canonical_json(data)
    if value is None or reason:
        return None, info, "corrupt", (
            reason or "durable_finalization_isolation_decode_failed",
        )
    return value, info, "ok", ()


def _hash_without(value: Mapping[str, object], field_name: str) -> str:
    body = {key: item for key, item in value.items() if key != field_name}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def _is_digest(value: object) -> bool:
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def _result(
    status: IsolationStatus,
    reasons: Sequence[str],
    *,
    present: bool = False,
    durable: bool = False,
    duplicate_existing: bool = False,
    marker: dict[str, object] | None = None,
    mtime_ns: int | None = None,
) -> RelayMEMSLPDurableFinalizationIsolationResult:
    return RelayMEMSLPDurableFinalizationIsolationResult(
        status=status,
        present=present,
        durable=durable,
        duplicate_existing=duplicate_existing,
        reason_ids=dedupe(tuple(reasons))[:_MAX_REASONS],
        marker=marker,
        mtime_ns=mtime_ns,
    )


__all__ = [
    "ISOLATION_FIELDS",
    "ISOLATION_MAX_BYTES",
    "ISOLATION_REVISION",
    "ISOLATION_SCHEMA",
    "OBSERVED_COMPONENT_FIELDS",
    "RelayMEMSLPDurableFinalizationIsolationResult",
    "build_isolation_marker",
    "isolation_filename",
    "publish_relaymem_slp_durable_finalization_isolation",
    "read_relaymem_slp_durable_finalization_isolation",
    "read_relaymem_slp_durable_finalization_isolation_fd",
    "validate_isolation_marker",
]
