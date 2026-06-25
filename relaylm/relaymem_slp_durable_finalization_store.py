"""Secure immutable private publication store for I1-GB evidence."""
from __future__ import annotations

import ctypes
import errno
import fcntl
import os
import secrets
import stat
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .relaymem_slp_durable_finalization_record import (
    RECORD_SCHEMA,
    RelayMEMSLPDurableFinalizationEvidence,
    base_filename,
    canonical_json_bytes,
    decode_canonical_json,
    seal_filename,
    segment_filename,
    validate_base_record,
    validate_seal_record,
    validate_segment_chain,
    validate_segment_record,
)
from .relaymem_slp_queue_record import dedupe

DEFAULT_MAX_RECORD_BYTES = 512 * 1024
DEFAULT_MAX_SEGMENT_BYTES = 64 * 1024
DEFAULT_MAX_SEGMENT_COUNT = 256
DEFAULT_MAX_RECORD_COUNT = 1024
DEFAULT_OPERATION_TIMEOUT_MS = 5000
MAX_FILE_BYTES_LIMIT = 4 * 1024 * 1024
_MAX_REASONS = 32
_PREFIX = "durable-finalization-v0-"

StoreStatus = Literal[
    "published_new",
    "duplicate_existing",
    "missing",
    "blocked",
    "collision",
    "corrupt",
    "capacity_exceeded",
    "ambiguous",
    "failed",
    "loaded",
]


@dataclass(frozen=True, repr=False)
class RelayMEMSLPDurableFinalizationStoreResult:
    status: StoreStatus
    durable: bool
    record_present: bool
    sealed: bool
    replayable: bool
    duplicate_existing: bool
    cleanup_required: bool
    bounded_segment_count: int
    bounded_attempt_count: int
    blocked_reasons: tuple[str, ...]
    evidence: RelayMEMSLPDurableFinalizationEvidence | None = field(
        default=None, repr=False, compare=False
    )

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableFinalizationStoreResult("
            f"status={self.status!r}, sealed={self.sealed!r}, "
            "protected_content_omitted=True)"
        )


class RelayMEMSLPDurableFinalizationStore:
    """One pre-existing absolute runtime-private root with immutable files."""

    def __init__(
        self,
        root_path: str,
        *,
        max_record_bytes: int = DEFAULT_MAX_RECORD_BYTES,
        max_segment_bytes: int = DEFAULT_MAX_SEGMENT_BYTES,
        max_segment_count: int = DEFAULT_MAX_SEGMENT_COUNT,
        max_record_count: int = DEFAULT_MAX_RECORD_COUNT,
        operation_timeout_ms: int = DEFAULT_OPERATION_TIMEOUT_MS,
    ) -> None:
        self._root_path = root_path
        self._max_record_bytes = _positive_int(
            max_record_bytes, "durable_finalization_max_record_bytes_invalid"
        )
        self._max_segment_bytes = _positive_int(
            max_segment_bytes, "durable_finalization_max_segment_bytes_invalid"
        )
        self._max_segment_count = _positive_int(
            max_segment_count, "durable_finalization_max_segment_count_invalid"
        )
        self._max_record_count = _positive_int(
            max_record_count, "durable_finalization_max_record_count_invalid"
        )
        self._operation_timeout_ms = _positive_int(
            operation_timeout_ms,
            "durable_finalization_publication_timeout_invalid",
        )
        if self._max_segment_bytes > self._max_record_bytes:
            raise ValueError("durable_finalization_segment_bound_exceeds_record_bound")
        if self._max_record_bytes > MAX_FILE_BYTES_LIMIT:
            raise ValueError("durable_finalization_max_record_bytes_too_large")

    def publish_base(
        self, base: object
    ) -> RelayMEMSLPDurableFinalizationStoreResult:
        validated, reasons = validate_base_record(base)
        if validated is None or reasons:
            return _result("blocked", reasons)
        data = canonical_json_bytes(validated)
        if len(data) > self._max_record_bytes:
            return _result(
                "capacity_exceeded", ("durable_finalization_base_size_exceeded",)
            )
        deadline = self._deadline()
        root_fd, root_reasons = _open_store_root(self._root_path)
        if root_fd is None:
            return _result("blocked", root_reasons)
        try:
            lock_reason = _acquire_lock(root_fd, exclusive=True)
            if lock_reason:
                return _result("failed", (lock_reason,))
            if self._expired(deadline):
                return _result(
                    "failed", ("durable_finalization_publication_timeout",)
                )
            count, count_reasons = self._count_logical_records(root_fd)
            if count is None:
                return _result("corrupt", count_reasons)
            filename = base_filename(str(validated["locator_digest"]))
            existing, read_status, read_reasons = self._read_named(
                root_fd, filename, kind="base"
            )
            if read_status == "ok" and existing is not None:
                return self._equivalent_or_collision(existing, data, sealed=False)
            if read_status not in {"missing"}:
                return _result("corrupt", read_reasons, record_present=True)
            ancillary, ancillary_reasons = self._locator_component_names(
                root_fd, str(validated["locator_digest"])
            )
            if ancillary is None:
                return _result("failed", ancillary_reasons)
            if ancillary:
                return _result(
                    "corrupt",
                    ("durable_finalization_impossible_marker_combination",),
                    record_present=True,
                )
            if count >= self._max_record_count:
                return _result(
                    "capacity_exceeded",
                    ("durable_finalization_record_count_exceeded",),
                )
            publication, publication_reasons = self._atomic_create(
                root_fd,
                filename,
                data,
                kind="base",
                deadline=deadline,
            )
            return self._publication_result(
                publication,
                publication_reasons,
                root_fd=root_fd,
                locator=str(validated["locator_digest"]),
                filename=filename,
                expected=data,
                kind="base",
            )
        finally:
            _release_lock(root_fd)
            os.close(root_fd)

    def publish_segment(
        self, segment: object
    ) -> RelayMEMSLPDurableFinalizationStoreResult:
        validated, reasons = validate_segment_record(segment)
        if validated is None or reasons:
            return _result("blocked", reasons)
        sequence = int(validated["segment_sequence"])
        if sequence >= self._max_segment_count:
            return _result(
                "capacity_exceeded",
                ("durable_finalization_segment_count_exceeded",),
            )
        data = canonical_json_bytes(validated)
        if len(data) > self._max_segment_bytes:
            return _result(
                "capacity_exceeded", ("durable_finalization_segment_size_exceeded",)
            )
        deadline = self._deadline()
        root_fd, root_reasons = _open_store_root(self._root_path)
        if root_fd is None:
            return _result("blocked", root_reasons)
        try:
            lock_reason = _acquire_lock(root_fd, exclusive=True)
            if lock_reason:
                return _result("failed", (lock_reason,))
            locator = str(validated["locator_digest"])
            evidence_result = self._read_evidence_locked(
                root_fd, locator, include_seal=True
            )
            if evidence_result.status == "missing":
                return _result(
                    "blocked", ("durable_finalization_base_required",)
                )
            if evidence_result.status not in {"loaded"} or evidence_result.evidence is None:
                return evidence_result
            evidence = evidence_result.evidence
            if evidence.seal is not None:
                return _result(
                    "collision",
                    ("durable_finalization_segment_after_seal_forbidden",),
                    record_present=True,
                    sealed=True,
                    replayable=True,
                    bounded_segment_count=len(evidence.segments),
                )
            expected_sequence = len(evidence.segments)
            previous = (
                str(evidence.segments[-1]["segment_digest"])
                if evidence.segments
                else "0" * 64
            )
            strict_segment, strict_reasons = validate_segment_record(
                validated,
                expected_base=evidence.base,
                expected_sequence=sequence,
                expected_previous_digest=previous if sequence == expected_sequence else None,
            )
            filename = segment_filename(locator, sequence)
            existing, read_status, read_reasons = self._read_named(
                root_fd, filename, kind="segment"
            )
            if read_status == "ok" and existing is not None:
                return self._equivalent_or_collision(
                    existing,
                    data,
                    sealed=False,
                    segment_count=max(len(evidence.segments), sequence + 1),
                )
            if strict_segment is None or strict_reasons:
                return _result(
                    "blocked",
                    strict_reasons,
                    record_present=True,
                    bounded_segment_count=len(evidence.segments),
                )
            if sequence != expected_sequence:
                return _result(
                    "blocked",
                    ("durable_finalization_segment_order_mismatch",),
                    record_present=True,
                    bounded_segment_count=len(evidence.segments),
                )
            total = self._logical_bytes(root_fd, locator)
            if total is None:
                return _result(
                    "corrupt",
                    ("durable_finalization_record_capacity_scan_failed",),
                    record_present=True,
                )
            if total + len(data) > self._max_record_bytes:
                return _result(
                    "capacity_exceeded",
                    ("durable_finalization_total_record_bytes_exceeded",),
                    record_present=True,
                    bounded_segment_count=len(evidence.segments),
                )
            publication, publication_reasons = self._atomic_create(
                root_fd,
                filename,
                data,
                kind="segment",
                deadline=deadline,
            )
            return self._publication_result(
                publication,
                publication_reasons,
                root_fd=root_fd,
                locator=locator,
                filename=filename,
                expected=data,
                kind="segment",
            )
        finally:
            _release_lock(root_fd)
            os.close(root_fd)

    def publish_seal(
        self, seal: object
    ) -> RelayMEMSLPDurableFinalizationStoreResult:
        validated, reasons = validate_seal_record(seal)
        if validated is None or reasons:
            return _result("blocked", reasons)
        data = canonical_json_bytes(validated)
        deadline = self._deadline()
        root_fd, root_reasons = _open_store_root(self._root_path)
        if root_fd is None:
            return _result("blocked", root_reasons)
        try:
            lock_reason = _acquire_lock(root_fd, exclusive=True)
            if lock_reason:
                return _result("failed", (lock_reason,))
            locator = str(validated["locator_digest"])
            evidence_result = self._read_evidence_locked(
                root_fd, locator, include_seal=True
            )
            if evidence_result.status == "missing":
                return _result("blocked", ("durable_finalization_base_required",))
            if evidence_result.status != "loaded" or evidence_result.evidence is None:
                return evidence_result
            evidence = evidence_result.evidence
            filename = seal_filename(locator)
            existing, read_status, read_reasons = self._read_named(
                root_fd, filename, kind="seal"
            )
            if read_status == "ok" and existing is not None:
                return self._equivalent_or_collision(
                    existing,
                    data,
                    sealed=True,
                    segment_count=len(evidence.segments),
                )
            if read_status not in {"missing"}:
                return _result(
                    "corrupt",
                    read_reasons,
                    record_present=True,
                    bounded_segment_count=len(evidence.segments),
                )
            strict, strict_reasons = validate_seal_record(
                validated,
                expected_base=evidence.base,
                expected_segments=evidence.segments,
            )
            if strict is None or strict_reasons:
                return _result(
                    "blocked",
                    strict_reasons,
                    record_present=True,
                    bounded_segment_count=len(evidence.segments),
                )
            total = self._logical_bytes(root_fd, locator)
            if total is None:
                return _result(
                    "corrupt",
                    ("durable_finalization_record_capacity_scan_failed",),
                    record_present=True,
                )
            if total + len(data) > self._max_record_bytes:
                return _result(
                    "capacity_exceeded",
                    ("durable_finalization_total_record_bytes_exceeded",),
                    record_present=True,
                    bounded_segment_count=len(evidence.segments),
                )
            publication, publication_reasons = self._atomic_create(
                root_fd,
                filename,
                data,
                kind="seal",
                deadline=deadline,
            )
            result = self._publication_result(
                publication,
                publication_reasons,
                root_fd=root_fd,
                locator=locator,
                filename=filename,
                expected=data,
                kind="seal",
            )
            if result.status in {"published_new", "duplicate_existing"} and not result.sealed:
                return _result(
                    "failed",
                    ("durable_finalization_canonical_reread_required",),
                    record_present=True,
                    bounded_segment_count=len(evidence.segments),
                )
            return result
        finally:
            _release_lock(root_fd)
            os.close(root_fd)

    def read_evidence(
        self, locator_digest: str
    ) -> RelayMEMSLPDurableFinalizationStoreResult:
        deadline = self._deadline()
        root_fd, root_reasons = _open_store_root(self._root_path)
        if root_fd is None:
            return _result("blocked", root_reasons)
        try:
            lock_reason = _acquire_lock(root_fd, exclusive=False)
            if lock_reason:
                return _result("failed", (lock_reason,))
            result = self._read_evidence_locked(root_fd, locator_digest, include_seal=True)
            if self._expired(deadline):
                return _result(
                    "failed",
                    ("durable_finalization_publication_timeout",),
                    record_present=result.record_present,
                    sealed=result.sealed,
                    replayable=result.replayable,
                    bounded_segment_count=result.bounded_segment_count,
                )
            return result
        finally:
            _release_lock(root_fd)
            os.close(root_fd)

    def _read_evidence_locked(
        self, root_fd: int, locator: str, *, include_seal: bool
    ) -> RelayMEMSLPDurableFinalizationStoreResult:
        try:
            base_name = base_filename(locator)
        except ValueError:
            return _result("blocked", ("durable_finalization_locator_invalid",))
        base, base_status, base_reasons = self._read_named(
            root_fd, base_name, kind="base"
        )
        if base_status == "missing":
            ancillary, ancillary_reasons = self._locator_component_names(root_fd, locator)
            if ancillary is None:
                return _result("failed", ancillary_reasons)
            if ancillary:
                return _result(
                    "corrupt",
                    ("durable_finalization_impossible_marker_combination",),
                    record_present=True,
                )
            return _result("missing", ("durable_finalization_base_missing",))
        if base_status != "ok" or base is None:
            return _result("corrupt", base_reasons, record_present=True)
        validated_base, reasons = validate_base_record(base, expected_locator=locator)
        if validated_base is None or reasons:
            return _result("corrupt", reasons, record_present=True)
        segments: list[dict[str, object]] = []
        for sequence in range(self._max_segment_count):
            name = segment_filename(locator, sequence)
            value, status_value, read_reasons = self._read_named(
                root_fd, name, kind="segment"
            )
            if status_value == "missing":
                break
            if status_value != "ok" or value is None:
                return _result(
                    "corrupt",
                    read_reasons,
                    record_present=True,
                    bounded_segment_count=len(segments),
                )
            segments.append(value)
        overflow_name = segment_filename(locator, self._max_segment_count)
        _, overflow_status, overflow_reasons = self._read_named(
            root_fd, overflow_name, kind="segment"
        )
        if overflow_status != "missing":
            return _result(
                "corrupt",
                overflow_reasons
                or ("durable_finalization_segment_count_overflow",),
                record_present=True,
                bounded_segment_count=len(segments),
            )
        expected_segment_names = {
            segment_filename(locator, sequence)
            for sequence in range(len(segments))
        }
        segment_prefix = f"{_PREFIX}{locator}.segment-"
        try:
            actual_segment_names = {
                name
                for name in os.listdir(root_fd)
                if name.startswith(segment_prefix) and name.endswith(".json")
            }
        except OSError:
            return _result(
                "failed",
                ("durable_finalization_capacity_scan_failed",),
                record_present=True,
                bounded_segment_count=len(segments),
            )
        if actual_segment_names != expected_segment_names:
            return _result(
                "corrupt",
                ("durable_finalization_segment_order_mismatch",),
                record_present=True,
                bounded_segment_count=len(segments),
            )
        validated_segments, chain_reasons = validate_segment_chain(
            validated_base, segments
        )
        if chain_reasons:
            return _result(
                "corrupt",
                chain_reasons,
                record_present=True,
                bounded_segment_count=len(segments),
            )
        seal: dict[str, object] | None = None
        if include_seal:
            seal_value, seal_status, seal_reasons = self._read_named(
                root_fd, seal_filename(locator), kind="seal"
            )
            if seal_status not in {"missing", "ok"}:
                return _result(
                    "corrupt",
                    seal_reasons,
                    record_present=True,
                    bounded_segment_count=len(validated_segments),
                )
            if seal_status == "ok" and seal_value is not None:
                seal, strict_reasons = validate_seal_record(
                    seal_value,
                    expected_base=validated_base,
                    expected_segments=validated_segments,
                )
                if seal is None or strict_reasons:
                    return _result(
                        "corrupt",
                        strict_reasons,
                        record_present=True,
                        bounded_segment_count=len(validated_segments),
                    )
        evidence = RelayMEMSLPDurableFinalizationEvidence(
            base=validated_base,
            segments=tuple(validated_segments),
            seal=seal,
        )
        total = self._logical_bytes(root_fd, locator)
        if total is None or total > self._max_record_bytes:
            return _result(
                "corrupt",
                ("durable_finalization_total_record_bytes_exceeded",),
                record_present=True,
                sealed=seal is not None,
                replayable=seal is not None,
                bounded_segment_count=len(validated_segments),
            )
        return _result(
            "loaded",
            (),
            durable=True,
            record_present=True,
            sealed=seal is not None,
            replayable=seal is not None,
            bounded_segment_count=len(validated_segments),
            evidence=evidence,
        )

    def _read_named(
        self, root_fd: int, filename: str, *, kind: str
    ) -> tuple[dict[str, object] | None, str, tuple[str, ...]]:
        try:
            before = os.stat(filename, dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None, "missing", ()
        except OSError:
            return None, "failed", ("durable_finalization_file_unreadable",)
        if stat.S_ISLNK(before.st_mode):
            return None, "corrupt", ("durable_finalization_symlink_blocked",)
        if not stat.S_ISREG(before.st_mode):
            return None, "corrupt", ("durable_finalization_unsafe_file_type",)
        if before.st_nlink != 1:
            return None, "corrupt", ("durable_finalization_hardlink_invalid",)
        max_bytes = (
            self._max_segment_bytes
            if kind == "segment"
            else self._max_record_bytes
        )
        if before.st_size > max_bytes:
            return None, "corrupt", (f"durable_finalization_{kind}_size_exceeded",)
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            fd = os.open(filename, flags, dir_fd=root_fd)
        except OSError:
            return None, "failed", ("durable_finalization_file_unreadable",)
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino)
            ):
                return None, "corrupt", (
                    "durable_finalization_file_changed_during_read",
                )
            data = _read_bounded(fd, max_bytes)
            if data is None:
                return None, "corrupt", (
                    f"durable_finalization_{kind}_size_exceeded",
                )
        except OSError:
            return None, "failed", ("durable_finalization_file_unreadable",)
        finally:
            os.close(fd)
        try:
            after = os.stat(filename, dir_fd=root_fd, follow_symlinks=False)
        except OSError:
            return None, "corrupt", (
                "durable_finalization_file_changed_during_read",
            )
        if (
            stat.S_ISLNK(after.st_mode)
            or not stat.S_ISREG(after.st_mode)
            or after.st_nlink != 1
            or (after.st_dev, after.st_ino) != (info.st_dev, info.st_ino)
            or after.st_size != info.st_size
        ):
            return None, "corrupt", (
                "durable_finalization_file_changed_during_read",
            )
        value, reason = decode_canonical_json(data)
        if value is None or reason is not None:
            return None, "corrupt", (reason or "durable_finalization_decode_failed",)
        validator = {
            "base": validate_base_record,
            "segment": validate_segment_record,
            "seal": validate_seal_record,
        }[kind]
        validated, reasons = validator(value)
        if validated is None or reasons:
            return None, "corrupt", reasons
        return validated, "ok", ()

    def _atomic_create(
        self,
        root_fd: int,
        filename: str,
        data: bytes,
        *,
        kind: str,
        deadline: float,
    ) -> tuple[str, tuple[str, ...]]:
        if self._expired(deadline):
            return "failed", ("durable_finalization_publication_timeout",)
        temp = f".durable-finalization-{secrets.token_hex(16)}.tmp"
        created = False
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            try:
                fd = os.open(temp, flags, 0o600, dir_fd=root_fd)
                created = True
            except OSError:
                return "failed", ("durable_finalization_temp_create_failed",)
            try:
                _write_all(fd, data)
                _fsync(fd)
                info = os.fstat(fd)
                max_bytes = (
                    self._max_segment_bytes
                    if kind == "segment"
                    else self._max_record_bytes
                )
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or info.st_size != len(data)
                    or info.st_size > max_bytes
                ):
                    raise OSError(errno.EIO, "unsafe finalization temp")
            except OSError:
                return "failed", ("durable_finalization_temp_write_failed",)
            finally:
                os.close(fd)
            if self._expired(deadline):
                return "failed", ("durable_finalization_publication_timeout",)
            published = _rename_noreplace(root_fd, temp, filename)
            if published == "exists":
                return "exists", ()
            if published != "published":
                return "ambiguous", ("durable_finalization_atomic_publish_ambiguous",)
            created = False
            try:
                _fsync(root_fd)
            except OSError:
                # Canonical reread below determines the state, but durability success
                # is not inferred after an fsync exception.
                value, status_value, reasons = self._read_named(
                    root_fd, filename, kind=kind
                )
                if (
                    status_value == "ok"
                    and value is not None
                    and canonical_json_bytes(value) == data
                ):
                    return "ambiguous", (
                        "durable_finalization_directory_fsync_ambiguous",
                    )
                return "failed", reasons or (
                    "durable_finalization_directory_fsync_failed",
                )
            value, status_value, reasons = self._read_named(
                root_fd, filename, kind=kind
            )
            if (
                status_value != "ok"
                or value is None
                or canonical_json_bytes(value) != data
            ):
                return "failed", reasons or (
                    "durable_finalization_canonical_reread_failed",
                )
            if self._expired(deadline):
                return "ambiguous", (
                    "durable_finalization_publication_timeout_ambiguous",
                )
            return "created", ()
        finally:
            if created:
                try:
                    os.unlink(temp, dir_fd=root_fd)
                    _fsync(root_fd)
                except OSError:
                    pass

    def _publication_result(
        self,
        publication: str,
        reasons: Sequence[str],
        *,
        root_fd: int,
        locator: str,
        filename: str,
        expected: bytes,
        kind: str,
    ) -> RelayMEMSLPDurableFinalizationStoreResult:
        exact, exact_status, exact_reasons = self._read_named(
            root_fd, filename, kind=kind
        )
        if exact_status == "ok" and exact is not None:
            if canonical_json_bytes(exact) != expected:
                return _result(
                    "collision",
                    ("durable_finalization_identity_collision",),
                    record_present=True,
                )
        elif publication in {"created", "exists"}:
            return _result(
                "corrupt",
                exact_reasons or ("durable_finalization_canonical_reread_failed",),
                record_present=exact_status != "missing",
            )
        reread = self._read_evidence_locked(root_fd, locator, include_seal=True)
        if publication == "created":
            if reread.status != "loaded":
                return _result(
                    "failed",
                    reread.blocked_reasons
                    or ("durable_finalization_canonical_reread_failed",),
                    record_present=reread.record_present,
                    sealed=reread.sealed,
                    replayable=reread.replayable,
                    bounded_segment_count=reread.bounded_segment_count,
                )
            return _result(
                "published_new",
                (),
                durable=True,
                record_present=True,
                sealed=reread.sealed,
                replayable=reread.replayable,
                bounded_segment_count=reread.bounded_segment_count,
                evidence=reread.evidence,
            )
        if publication == "exists":
            if reread.status != "loaded":
                return _result(
                    "corrupt",
                    reread.blocked_reasons
                    or ("durable_finalization_existing_record_invalid",),
                    record_present=reread.record_present,
                    sealed=reread.sealed,
                    replayable=reread.replayable,
                    bounded_segment_count=reread.bounded_segment_count,
                )
            return _result(
                "duplicate_existing",
                (),
                durable=True,
                record_present=True,
                sealed=reread.sealed,
                replayable=reread.replayable,
                duplicate_existing=True,
                bounded_segment_count=reread.bounded_segment_count,
                evidence=reread.evidence,
            )
        status: StoreStatus = "ambiguous" if publication == "ambiguous" else "failed"
        return _result(
            status,
            tuple(reasons) or ("durable_finalization_publication_failed",),
            record_present=reread.record_present,
            sealed=reread.sealed,
            replayable=reread.replayable,
            bounded_segment_count=reread.bounded_segment_count,
        )

    @staticmethod
    def _equivalent_or_collision(
        existing: Mapping[str, object],
        expected: bytes,
        *,
        sealed: bool,
        segment_count: int = 0,
    ) -> RelayMEMSLPDurableFinalizationStoreResult:
        if canonical_json_bytes(existing) == expected:
            return _result(
                "duplicate_existing",
                (),
                durable=True,
                record_present=True,
                sealed=sealed,
                replayable=sealed,
                duplicate_existing=True,
                bounded_segment_count=segment_count,
            )
        return _result(
            "collision",
            ("durable_finalization_identity_collision",),
            record_present=True,
            sealed=sealed,
            replayable=sealed,
            bounded_segment_count=segment_count,
        )

    def _locator_component_names(
        self, root_fd: int, locator: str
    ) -> tuple[set[str] | None, tuple[str, ...]]:
        prefix = f"{_PREFIX}{locator}."
        try:
            return {name for name in os.listdir(root_fd) if name.startswith(prefix)}, ()
        except OSError:
            return None, ("durable_finalization_capacity_scan_failed",)

    def _count_logical_records(
        self, root_fd: int
    ) -> tuple[int | None, tuple[str, ...]]:
        try:
            names = os.listdir(root_fd)
        except OSError:
            return None, ("durable_finalization_capacity_scan_failed",)
        count = 0
        for name in names:
            if not name.startswith(_PREFIX) or not name.endswith(".base.json"):
                continue
            count += 1
            if count > self._max_record_count:
                return count, ()
        return count, ()

    def _logical_bytes(self, root_fd: int, locator: str) -> int | None:
        prefix = f"{_PREFIX}{locator}."
        total = 0
        try:
            names = os.listdir(root_fd)
        except OSError:
            return None
        for name in names:
            if not name.startswith(prefix):
                continue
            try:
                info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            except OSError:
                return None
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                return None
            total += info.st_size
            if total > self._max_record_bytes:
                return total
        return total

    def _deadline(self) -> float:
        return time.monotonic() + (self._operation_timeout_ms / 1000.0)

    @staticmethod
    def _expired(deadline: float) -> bool:
        return time.monotonic() > deadline


def _open_store_root(root_path: object) -> tuple[int | None, tuple[str, ...]]:
    if type(root_path) is not str or not root_path:
        return None, ("durable_finalization_root_missing",)
    absolute = Path(root_path)
    if not absolute.is_absolute() or any(
        part in {".", ".."} for part in absolute.parts[1:]
    ):
        return None, ("durable_finalization_root_invalid",)
    if not _supports_secure_dirfd():
        return None, ("durable_finalization_platform_unsupported",)
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(absolute.anchor, flags)
    except OSError:
        return None, ("durable_finalization_root_unopenable",)
    for part in absolute.parts[1:]:
        try:
            before = os.stat(part, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            os.close(fd)
            return None, ("durable_finalization_root_missing",)
        except OSError:
            os.close(fd)
            return None, ("durable_finalization_root_unopenable",)
        if stat.S_ISLNK(before.st_mode):
            os.close(fd)
            return None, ("durable_finalization_root_symlink_blocked",)
        if not stat.S_ISDIR(before.st_mode):
            os.close(fd)
            return None, ("durable_finalization_root_not_directory",)
        try:
            child = os.open(
                part,
                flags | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=fd,
            )
        except OSError:
            os.close(fd)
            return None, ("durable_finalization_root_unopenable",)
        after = os.fstat(child)
        if (
            not stat.S_ISDIR(after.st_mode)
            or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
        ):
            os.close(child)
            os.close(fd)
            return None, ("durable_finalization_root_changed",)
        os.close(fd)
        fd = child
    return fd, ()


def _acquire_lock(root_fd: int, *, exclusive: bool) -> str | None:
    try:
        fcntl.flock(
            root_fd,
            (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        return "durable_finalization_store_lock_busy"
    except OSError:
        return "durable_finalization_store_lock_failed"
    return None


def _release_lock(root_fd: int) -> None:
    try:
        fcntl.flock(root_fd, fcntl.LOCK_UN)
    except OSError:
        pass


def _rename_noreplace(root_fd: int, source: str, destination: str) -> str:
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, "renameat2", None)
    if function is None:
        return "unsupported"
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    function.restype = ctypes.c_int
    if (
        function(
            root_fd,
            os.fsencode(source),
            root_fd,
            os.fsencode(destination),
            1,
        )
        == 0
    ):
        return "published"
    error = ctypes.get_errno()
    if error == errno.EEXIST:
        return "exists"
    return "unsupported" if error in {errno.ENOSYS, errno.EINVAL} else "failed"


def _read_bounded(fd: int, maximum: int) -> bytes | None:
    chunks: list[bytes] = []
    remaining = maximum + 1
    while remaining > 0:
        chunk = os.read(fd, min(4096, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b"".join(chunks)
    return None if len(data) > maximum else data


def _write_all(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0:
            raise OSError(errno.EIO, "short write")
        offset += written


def _fsync(fd: int) -> None:
    os.fsync(fd)


def _supports_secure_dirfd() -> bool:
    return (
        all(function in os.supports_dir_fd for function in (os.open, os.stat, os.unlink))
        and os.stat in os.supports_follow_symlinks
    )


def _positive_int(value: object, reason: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(reason)
    return value


def _result(
    status: StoreStatus,
    reasons: Sequence[str],
    *,
    durable: bool = False,
    record_present: bool = False,
    sealed: bool = False,
    replayable: bool = False,
    duplicate_existing: bool = False,
    cleanup_required: bool = False,
    bounded_segment_count: int = 0,
    bounded_attempt_count: int = 1,
    evidence: RelayMEMSLPDurableFinalizationEvidence | None = None,
) -> RelayMEMSLPDurableFinalizationStoreResult:
    return RelayMEMSLPDurableFinalizationStoreResult(
        status=status,
        durable=durable,
        record_present=record_present,
        sealed=sealed,
        replayable=replayable,
        duplicate_existing=duplicate_existing,
        cleanup_required=cleanup_required,
        bounded_segment_count=max(0, bounded_segment_count),
        bounded_attempt_count=max(0, bounded_attempt_count),
        blocked_reasons=dedupe(tuple(reasons))[:_MAX_REASONS],
        evidence=evidence,
    )


__all__ = [
    "DEFAULT_MAX_RECORD_BYTES",
    "DEFAULT_MAX_RECORD_COUNT",
    "DEFAULT_MAX_SEGMENT_BYTES",
    "DEFAULT_MAX_SEGMENT_COUNT",
    "DEFAULT_OPERATION_TIMEOUT_MS",
    "RelayMEMSLPDurableFinalizationStore",
    "RelayMEMSLPDurableFinalizationStoreResult",
]
