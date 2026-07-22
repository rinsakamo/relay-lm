"""Bounded, single-host persistence for EV-1 Governed Evidence.

The store provides two layers:

* simple immutable-record / append-log helpers retained for tests and tooling;
* a per-evidence-space transaction context used by runtime capture paths.

Runtime transactions are serialized by the existing portable file lock. A
prepared transaction journal is written before authority records are applied
and is replayed on the next transaction after a crash. Every replayed write is
create-or-verify or an exact log replacement, so recovery is idempotent.
"""
from __future__ import annotations

import json
import os
import stat
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from relaylm.evidence_common import canonical_digest, canonical_json_bytes
from relaylm.portable_lock import portable_lock

StoreStatus = Literal["created", "duplicate_existing", "collision", "blocked", "failed"]


@dataclass(frozen=True)
class EvidenceStoreResult:
    status: StoreStatus
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceTransactionWrite:
    kind: Literal["record", "log", "payload"]
    category: str
    key: str
    payload: dict | list[dict]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "category": self.category,
            "key": self.key,
            "payload": self.payload,
        }


class EvidenceStoreTransaction:
    """Operations performed while one evidence-space lock is held."""

    def __init__(self, store: "EvidenceRecordStore", evidence_space_id: str) -> None:
        self._store = store
        self.evidence_space_id = evidence_space_id

    def read_record(self, *, record_kind: str, record_id: str) -> dict | None:
        return self._store._read_record_unlocked(
            evidence_space_id=self.evidence_space_id,
            record_kind=record_kind,
            record_id=record_id,
        )

    def read_log(self, *, log_kind: str, key: str) -> list[dict] | None:
        return self._store._read_log_unlocked(
            evidence_space_id=self.evidence_space_id,
            log_kind=log_kind,
            key=key,
        )

    def list_logs(
        self, *, log_kind: str, limit: int
    ) -> tuple[tuple[str, list[dict]], ...]:
        """Return one bounded, under-lock inventory for a logical log kind."""

        return self._store._list_logs_unlocked(
            evidence_space_id=self.evidence_space_id,
            log_kind=log_kind,
            limit=limit,
        )

    def read_payload(self, *, payload_id: str) -> dict | None:
        return self._store._read_payload_unlocked(
            evidence_space_id=self.evidence_space_id, payload_id=payload_id
        )

    def commit(
        self,
        *,
        transaction_id: str,
        records: Sequence[tuple[str, str, dict]],
        logs: Sequence[tuple[str, str, Sequence[dict]]],
        payloads: Sequence[tuple[str, dict]] = (),
    ) -> EvidenceStoreResult:
        writes = [
            EvidenceTransactionWrite("record", kind, key, dict(payload))
            for kind, key, payload in records
        ]
        writes.extend(
            EvidenceTransactionWrite("log", kind, key, [dict(item) for item in events])
            for kind, key, events in logs
        )
        writes.extend(
            EvidenceTransactionWrite("payload", "protected_payload", key, dict(payload))
            for key, payload in payloads
        )
        return self._store._commit_transaction_unlocked(
            evidence_space_id=self.evidence_space_id,
            transaction_id=transaction_id,
            writes=writes,
        )


class EvidenceRecordStore:
    """One absolute root directory holding EV-1 evidence records."""

    def __init__(self, root_path: str) -> None:
        validated, reasons = _validate_root(root_path)
        if validated is None:
            raise ValueError(reasons[0] if reasons else "evidence_store_root_invalid")
        self._root = validated

    @property
    def root(self) -> Path:
        return self._root

    def _space_dir(self, evidence_space_id: str) -> Path:
        if not _is_safe_component(evidence_space_id):
            raise ValueError("evidence_store_evidence_space_id_invalid")
        return self._root / evidence_space_id

    @contextmanager
    def _space_lock(self, evidence_space_id: str) -> Iterator[None]:
        space_dir = self._space_dir(evidence_space_id)
        if not _ensure_safe_directory_chain(space_dir):
            raise RuntimeError("evidence_store_path_unsafe")
        lock_path = space_dir / ".lock"
        fd = os.open(
            lock_path,
            os.O_CREAT
            | os.O_RDWR
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            with portable_lock(fd, mode="exclusive", blocking=True):
                yield
        finally:
            os.close(fd)

    @contextmanager
    def transaction(self, evidence_space_id: str) -> Iterator[EvidenceStoreTransaction]:
        """Serialize, recover, and execute one evidence-space mutation."""

        with self._space_lock(evidence_space_id):
            recovery = self._recover_prepared_transactions_unlocked(evidence_space_id)
            if recovery.status not in {"created", "duplicate_existing"}:
                raise RuntimeError(
                    recovery.reasons[0]
                    if recovery.reasons
                    else "evidence_store_recovery_failed"
                )
            yield EvidenceStoreTransaction(self, evidence_space_id)

    def write_record(
        self,
        *,
        evidence_space_id: str,
        record_kind: str,
        record_id: str,
        payload: dict,
    ) -> EvidenceStoreResult:
        with self._space_lock(evidence_space_id):
            recovery = self._recover_prepared_transactions_unlocked(evidence_space_id)
            if recovery.status not in {"created", "duplicate_existing"}:
                return recovery
            return self._write_record_unlocked(
                evidence_space_id=evidence_space_id,
                record_kind=record_kind,
                record_id=record_id,
                payload=payload,
            )

    def read_record(
        self, *, evidence_space_id: str, record_kind: str, record_id: str
    ) -> dict | None:
        with self._space_lock(evidence_space_id):
            recovery = self._recover_prepared_transactions_unlocked(evidence_space_id)
            if recovery.status not in {"created", "duplicate_existing"}:
                return None
            return self._read_record_unlocked(
                evidence_space_id=evidence_space_id,
                record_kind=record_kind,
                record_id=record_id,
            )

    def write_log(
        self,
        *,
        evidence_space_id: str,
        log_kind: str,
        key: str,
        events: Sequence[dict],
    ) -> EvidenceStoreResult:
        with self._space_lock(evidence_space_id):
            recovery = self._recover_prepared_transactions_unlocked(evidence_space_id)
            if recovery.status not in {"created", "duplicate_existing"}:
                return recovery
            return self._write_log_unlocked(
                evidence_space_id=evidence_space_id,
                log_kind=log_kind,
                key=key,
                events=events,
            )

    def read_log(
        self, *, evidence_space_id: str, log_kind: str, key: str
    ) -> list[dict] | None:
        with self._space_lock(evidence_space_id):
            recovery = self._recover_prepared_transactions_unlocked(evidence_space_id)
            if recovery.status not in {"created", "duplicate_existing"}:
                return None
            return self._read_log_unlocked(
                evidence_space_id=evidence_space_id,
                log_kind=log_kind,
                key=key,
            )

    def locked(self, evidence_space_id: str):
        """Backward-compatible explicit lock context."""

        return self._space_lock(evidence_space_id)

    def _record_path(self, evidence_space_id: str, record_kind: str, record_id: str) -> Path:
        if not _is_safe_component(record_kind) or not _is_safe_component(record_id):
            raise ValueError("evidence_store_identifier_invalid")
        return (
            self._space_dir(evidence_space_id)
            / "records"
            / record_kind
            / f"{record_id}.json"
        )

    def _log_path(self, evidence_space_id: str, log_kind: str, key: str) -> Path:
        if not _is_safe_component(log_kind) or not _is_safe_component(key):
            raise ValueError("evidence_store_identifier_invalid")
        return self._space_dir(evidence_space_id) / "logs" / log_kind / f"{key}.json"

    def _write_record_unlocked(
        self, *, evidence_space_id: str, record_kind: str, record_id: str, payload: dict
    ) -> EvidenceStoreResult:
        try:
            target = self._record_path(evidence_space_id, record_kind, record_id)
        except ValueError:
            return EvidenceStoreResult("blocked", ("evidence_store_identifier_invalid",))
        return _atomic_create_or_verify(target, canonical_json_bytes(payload))

    def _read_record_unlocked(
        self, *, evidence_space_id: str, record_kind: str, record_id: str
    ) -> dict | None:
        try:
            value = _read_json(
                self._record_path(evidence_space_id, record_kind, record_id)
            )
        except ValueError:
            return None
        return value if isinstance(value, dict) else None

    def _write_log_unlocked(
        self, *, evidence_space_id: str, log_kind: str, key: str, events: Sequence[dict]
    ) -> EvidenceStoreResult:
        try:
            target = self._log_path(evidence_space_id, log_kind, key)
        except ValueError:
            return EvidenceStoreResult("blocked", ("evidence_store_identifier_invalid",))
        return _atomic_replace(target, canonical_json_bytes(list(events)))

    def _read_log_unlocked(
        self, *, evidence_space_id: str, log_kind: str, key: str
    ) -> list[dict] | None:
        try:
            target = self._log_path(evidence_space_id, log_kind, key)
        except ValueError:
            return None
        try:
            info = target.lstat()
        except FileNotFoundError:
            return []
        except OSError as exc:
            raise RuntimeError("evidence_store_log_unreadable") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise RuntimeError("evidence_store_log_unsafe")
        value = _read_json(target)
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise RuntimeError("evidence_store_log_corrupt")
        return value

    def _list_logs_unlocked(
        self,
        *,
        evidence_space_id: str,
        log_kind: str,
        limit: int,
    ) -> tuple[tuple[str, list[dict]], ...]:
        if not _is_safe_component(log_kind):
            raise ValueError("evidence_store_log_kind_invalid")
        if type(limit) is not int or not 1 <= limit <= 4096:
            raise ValueError("evidence_store_log_inventory_limit_invalid")
        directory = self._space_dir(evidence_space_id) / "logs" / log_kind
        try:
            info = directory.lstat()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise RuntimeError("evidence_store_log_inventory_unreadable") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise RuntimeError("evidence_store_log_inventory_unsafe")
        paths = sorted(directory.glob("*.json"))
        if len(paths) > limit:
            raise RuntimeError("evidence_store_log_inventory_limit_exceeded")
        inventory: list[tuple[str, list[dict]]] = []
        for path in paths:
            key = path.name.removesuffix(".json")
            if not _is_safe_component(key):
                raise RuntimeError("evidence_store_log_inventory_unsafe")
            events = self._read_log_unlocked(
                evidence_space_id=evidence_space_id,
                log_kind=log_kind,
                key=key,
            )
            if events is None:
                raise RuntimeError("evidence_store_log_inventory_unreadable")
            inventory.append((key, events))
        return tuple(inventory)

    def _payload_path(self, evidence_space_id: str, payload_id: str) -> Path:
        if not _is_safe_component(payload_id):
            raise ValueError("evidence_store_payload_id_invalid")
        return self._space_dir(evidence_space_id) / "payloads" / f"{payload_id}.json"

    def _read_payload_unlocked(
        self, *, evidence_space_id: str, payload_id: str
    ) -> dict | None:
        try:
            value = _read_json(self._payload_path(evidence_space_id, payload_id))
        except ValueError:
            return None
        return value if isinstance(value, dict) else None

    def _transaction_path(self, evidence_space_id: str, transaction_id: str) -> Path:
        if not _is_safe_component(transaction_id):
            raise ValueError("evidence_store_transaction_id_invalid")
        return (
            self._space_dir(evidence_space_id)
            / "transactions"
            / f"{transaction_id}.json"
        )

    def _commit_transaction_unlocked(
        self,
        *,
        evidence_space_id: str,
        transaction_id: str,
        writes: Sequence[EvidenceTransactionWrite],
    ) -> EvidenceStoreResult:
        try:
            target = self._transaction_path(evidence_space_id, transaction_id)
        except ValueError:
            return EvidenceStoreResult(
                "blocked", ("evidence_store_transaction_id_invalid",)
            )
        body = {
            "schema": "relaylm.evidence_store_transaction.v1",
            "transaction_id": transaction_id,
            "evidence_space_id": evidence_space_id,
            "writes": [item.to_dict() for item in writes],
        }
        digest = canonical_digest(body)
        existing = _read_json(target)
        if isinstance(existing, dict):
            if existing.get("transaction_digest") != digest:
                return EvidenceStoreResult(
                    "collision", ("evidence_store_transaction_conflict",)
                )
            if existing.get("state") == "committed":
                return EvidenceStoreResult("duplicate_existing")
        elif existing is not None:
            return EvidenceStoreResult(
                "failed", ("evidence_store_transaction_unreadable",)
            )

        prepared = {**body, "transaction_digest": digest, "state": "prepared"}
        result = _atomic_replace(target, canonical_json_bytes(prepared))
        if result.status not in {"created", "duplicate_existing"}:
            return result

        applied = self._apply_transaction_writes_unlocked(evidence_space_id, writes)
        if applied.status not in {"created", "duplicate_existing"}:
            return applied

        committed = {**body, "transaction_digest": digest, "state": "committed"}
        result = _atomic_replace(target, canonical_json_bytes(committed))
        if result.status not in {"created", "duplicate_existing"}:
            return result
        _fsync_dir(target.parent)
        return EvidenceStoreResult("created")

    def _apply_transaction_writes_unlocked(
        self, evidence_space_id: str, writes: Sequence[EvidenceTransactionWrite]
    ) -> EvidenceStoreResult:
        for item in writes:
            if item.kind == "record":
                if not isinstance(item.payload, dict):
                    return EvidenceStoreResult(
                        "blocked", ("evidence_store_transaction_record_invalid",)
                    )
                result = self._write_record_unlocked(
                    evidence_space_id=evidence_space_id,
                    record_kind=item.category,
                    record_id=item.key,
                    payload=item.payload,
                )
            elif item.kind == "log":
                if not isinstance(item.payload, list):
                    return EvidenceStoreResult(
                        "blocked", ("evidence_store_transaction_log_invalid",)
                    )
                result = self._write_log_unlocked(
                    evidence_space_id=evidence_space_id,
                    log_kind=item.category,
                    key=item.key,
                    events=item.payload,
                )
            else:
                if not isinstance(item.payload, dict):
                    return EvidenceStoreResult(
                        "blocked", ("evidence_store_transaction_payload_invalid",)
                    )
                try:
                    target = self._payload_path(evidence_space_id, item.key)
                except ValueError:
                    return EvidenceStoreResult(
                        "blocked", ("evidence_store_payload_id_invalid",)
                    )
                result = _atomic_create_or_verify(
                    target, canonical_json_bytes(item.payload)
                )
            if result.status not in {"created", "duplicate_existing"}:
                return result
        return EvidenceStoreResult("created")

    def _recover_prepared_transactions_unlocked(
        self, evidence_space_id: str
    ) -> EvidenceStoreResult:
        directory = self._space_dir(evidence_space_id) / "transactions"
        try:
            directory_info = directory.lstat()
        except FileNotFoundError:
            return EvidenceStoreResult("duplicate_existing")
        except OSError:
            return EvidenceStoreResult("failed", ("evidence_store_path_unsafe",))
        if stat.S_ISLNK(directory_info.st_mode) or not stat.S_ISDIR(
            directory_info.st_mode
        ):
            return EvidenceStoreResult("failed", ("evidence_store_path_unsafe",))
        for path in sorted(directory.glob("*.json")):
            value = _read_json(path)
            if not isinstance(value, dict):
                return EvidenceStoreResult(
                    "failed", ("evidence_store_transaction_unreadable",)
                )
            body = {
                "schema": value.get("schema"),
                "transaction_id": value.get("transaction_id"),
                "evidence_space_id": value.get("evidence_space_id"),
                "writes": value.get("writes"),
            }
            if canonical_digest(body) != value.get("transaction_digest"):
                return EvidenceStoreResult(
                    "collision", ("evidence_store_transaction_digest_mismatch",)
                )
            if value.get("state") == "committed":
                continue
            writes: list[EvidenceTransactionWrite] = []
            for raw in value.get("writes", []):
                if not isinstance(raw, dict):
                    return EvidenceStoreResult(
                        "failed", ("evidence_store_transaction_shape_invalid",)
                    )
                writes.append(
                    EvidenceTransactionWrite(
                        kind=raw.get("kind"),  # type: ignore[arg-type]
                        category=str(raw.get("category", "")),
                        key=str(raw.get("key", "")),
                        payload=raw.get("payload"),  # type: ignore[arg-type]
                    )
                )
            result = self._apply_transaction_writes_unlocked(
                evidence_space_id, writes
            )
            if result.status not in {"created", "duplicate_existing"}:
                return result
            value["state"] = "committed"
            result = _atomic_replace(path, canonical_json_bytes(value))
            if result.status not in {"created", "duplicate_existing"}:
                return result
        return EvidenceStoreResult("created")


def _validate_root(root_path: object) -> tuple[Path | None, tuple[str, ...]]:
    if type(root_path) is not str or not root_path:
        return None, ("evidence_store_root_missing",)
    path = Path(root_path)
    if not path.is_absolute():
        return None, ("evidence_store_root_not_absolute",)
    if any(part in {".", ".."} for part in path.parts[1:]):
        return None, ("evidence_store_root_invalid",)
    try:
        if path.is_symlink():
            return None, ("evidence_store_root_unsafe",)
        path.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            return None, ("evidence_store_root_unsafe",)
        resolved = path.resolve(strict=True)
    except OSError:
        return None, ("evidence_store_root_unsafe",)
    if not resolved.is_dir():
        return None, ("evidence_store_root_unsafe",)
    return resolved, ()


def _is_safe_component(value: object) -> bool:
    return (
        type(value) is str
        and bool(value)
        and len(value) <= 256
        and value not in {".", ".."}
        and "/" not in value
        and "\\" not in value
        and "\x00" not in value
    )


def _ensure_safe_directory_chain(directory: Path) -> bool:
    """Create missing directories one component at a time and reject links/files."""

    if not directory.is_absolute():
        return False
    current = Path(directory.anchor)
    try:
        for part in directory.parts[1:]:
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                try:
                    current.mkdir(mode=0o700)
                except FileExistsError:
                    pass
                info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                return False
    except OSError:
        return False
    return True


def _atomic_create_or_verify(target: Path, data: bytes) -> EvidenceStoreResult:
    if not _ensure_safe_directory_chain(target.parent):
        return EvidenceStoreResult("failed", ("evidence_store_path_unsafe",))
    if target.exists():
        existing = _read_bytes_verified(target)
        if existing is None:
            return EvidenceStoreResult(
                "failed", ("evidence_store_existing_unreadable",)
            )
        if existing == data:
            return EvidenceStoreResult("duplicate_existing")
        return EvidenceStoreResult(
            "collision", ("evidence_store_identity_collision",)
        )
    return _atomic_write(target, data, replace=False)


def _atomic_replace(target: Path, data: bytes) -> EvidenceStoreResult:
    return _atomic_write(target, data, replace=True)


def _atomic_write(target: Path, data: bytes, *, replace: bool) -> EvidenceStoreResult:
    if not _ensure_safe_directory_chain(target.parent):
        return EvidenceStoreResult("failed", ("evidence_store_path_unsafe",))
    temp = target.with_name(
        f".{target.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp"
    )
    try:
        fd = os.open(
            temp,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        try:
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        if not _ensure_safe_directory_chain(target.parent):
            if temp.exists():
                os.unlink(temp)
            return EvidenceStoreResult("failed", ("evidence_store_path_unsafe",))
        if replace:
            os.replace(temp, target)
        else:
            try:
                os.link(temp, target)
            except FileExistsError:
                existing = _read_bytes_verified(target)
                if existing == data:
                    return EvidenceStoreResult("duplicate_existing")
                return EvidenceStoreResult(
                    "collision", ("evidence_store_identity_collision",)
                )
            finally:
                if temp.exists():
                    os.unlink(temp)
        _fsync_dir(target.parent)
        return EvidenceStoreResult("created")
    except OSError:
        try:
            if temp.exists():
                os.unlink(temp)
        except OSError:
            pass
        return EvidenceStoreResult("failed", ("evidence_store_write_failed",))


def _fsync_dir(directory: Path) -> None:
    try:
        fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def _read_bytes_verified(target: Path) -> bytes | None:
    try:
        info = target.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        return None
    try:
        return target.read_bytes()
    except OSError:
        return None


def _read_json(target: Path) -> object | None:
    data = _read_bytes_verified(target)
    if data is None:
        return None
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None


__all__ = [
    "EvidenceRecordStore",
    "EvidenceStoreResult",
    "EvidenceStoreTransaction",
    "EvidenceTransactionWrite",
]
