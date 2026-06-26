"""Immutable I-4C2 Forget tombstone publication and strict reread.

The tombstone is the sole durable applied-replay authority for one exact Forget
operation.  It proves that the immutable hidden successor and both canonical
control files have converged.  It deliberately does not claim ordinary M2 or
RelayCTX exclusion; that remains Phase I-4D ownership.
"""
from __future__ import annotations

import json
import os
import secrets
import stat
from datetime import datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from ._relaymem_primary_page_writer_common import (
    EVENT_KINDS,
    KIND_TARGET,
    bad_text,
    is_sha256,
    stable_hash,
)
from .relaymem_primary_forget_artifact import (
    MUTATION_ROOT,
    PrimaryForgetArtifactError,
    canonical_json_digest,
    validate_forget_prepared,
)

FORGET_TOMBSTONE_SCHEMA = "relaylm.mem.forget_tombstone.v0"
MAX_TOMBSTONE_BYTES = 32_768

_TOMBSTONE_FIELDS = {
    "schema_version",
    "runtime_private",
    "content_included",
    "operation_kind",
    "operation_id",
    "operation_key",
    "binding_digest",
    "tombstone_id",
    "character_id",
    "namespace",
    "memory_id",
    "prior_revision",
    "result_revision",
    "prior_lifecycle_state",
    "result_lifecycle_state",
    "prior_physical_id",
    "result_physical_id",
    "prior_canonical_digest",
    "result_canonical_digest",
    "prepared_digest",
    "reason",
    "reason_digest",
    "token_digest",
    "source_event_kind",
    "memory_kind",
    "lineage_fingerprint",
    "page_converged",
    "index_converged",
    "log_converged",
    "retrieval_exclusion_claimed",
    "requested_at",
    "prepared_at",
    "applied_at",
    "status",
    "recovery_required",
    "tombstone_digest",
}


def build_forget_tombstone(
    *,
    prepared: Mapping[str, Any],
    result_canonical_digest: str,
    applied_at: str,
) -> dict[str, Any]:
    """Build one deterministic tombstone identity from exact durable evidence."""

    if not validate_forget_prepared(prepared):
        raise PrimaryForgetArtifactError("target_corrupt")
    if not is_sha256(result_canonical_digest) or not _timestamp(applied_at):
        raise PrimaryForgetArtifactError("target_corrupt")
    if result_canonical_digest != prepared["successor_expected_canonical_digest"]:
        raise PrimaryForgetArtifactError("target_corrupt")

    prepared_digest = canonical_json_digest(prepared)
    tombstone_id = stable_hash(
        (
            "relaylm-primary-forget-tombstone-v0",
            str(prepared["memory_id"]),
            str(prepared["operation_key"]),
            str(prepared["binding_digest"]),
            str(prepared["prior_revision"]),
            str(prepared["result_revision"]),
            str(prepared["prior_physical_id"]),
            str(prepared["successor_physical_id"]),
            prepared_digest,
            result_canonical_digest,
        )
    )
    value: dict[str, Any] = {
        "schema_version": FORGET_TOMBSTONE_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "operation_kind": "forget",
        "operation_id": str(prepared["operation_id"]),
        "operation_key": str(prepared["operation_key"]),
        "binding_digest": str(prepared["binding_digest"]),
        "tombstone_id": tombstone_id,
        "character_id": str(prepared["character_id"]),
        "namespace": str(prepared["namespace"]),
        "memory_id": str(prepared["memory_id"]),
        "prior_revision": int(prepared["prior_revision"]),
        "result_revision": int(prepared["result_revision"]),
        "prior_lifecycle_state": "active",
        "result_lifecycle_state": "hidden",
        "prior_physical_id": str(prepared["prior_physical_id"]),
        "result_physical_id": str(prepared["successor_physical_id"]),
        "prior_canonical_digest": str(prepared["prior_canonical_digest"]),
        "result_canonical_digest": result_canonical_digest,
        "prepared_digest": prepared_digest,
        "reason": str(prepared["reason"]),
        "reason_digest": str(prepared["reason_digest"]),
        "token_digest": str(prepared["token_digest"]),
        "source_event_kind": str(prepared["source_event_kind"]),
        "memory_kind": str(prepared["memory_kind"]),
        "lineage_fingerprint": str(prepared["lineage_fingerprint"]),
        "page_converged": True,
        "index_converged": True,
        "log_converged": True,
        "retrieval_exclusion_claimed": False,
        "requested_at": str(prepared["requested_at"]),
        "prepared_at": str(prepared["prepared_at"]),
        "applied_at": applied_at,
        "status": "reconciled",
        "recovery_required": False,
    }
    value["tombstone_digest"] = _self_digest(value)
    if not validate_forget_tombstone(value):
        raise PrimaryForgetArtifactError("target_corrupt")
    return value


def forget_tombstone_path(
    store_root: str | Path, *, memory_id: str, operation_key: str
) -> Path:
    root = _safe_root(store_root)
    if not is_sha256(memory_id) or not is_sha256(operation_key):
        raise PrimaryForgetArtifactError("invalid_request")
    directory = root / MUTATION_ROOT / memory_id
    _ensure_private_dir(root, directory)
    return directory / f"{operation_key}.tombstone.json"


def publish_forget_tombstone(
    store_root: str | Path, *, tombstone: Mapping[str, Any]
) -> str:
    """Create-if-absent, fsync, and canonically reread one exact tombstone."""

    if not validate_forget_tombstone(tombstone):
        raise PrimaryForgetArtifactError("target_corrupt")
    path = forget_tombstone_path(
        store_root,
        memory_id=str(tombstone["memory_id"]),
        operation_key=str(tombstone["operation_key"]),
    )
    payload = _canonical_json(tombstone) + b"\n"
    if len(payload) > MAX_TOMBSTONE_BYTES:
        raise PrimaryForgetArtifactError("target_corrupt")

    if path.exists() or path.is_symlink():
        existing = _read_exact_json(path)
        if existing == dict(tombstone):
            return "existing"
        raise PrimaryForgetArtifactError("operation_conflict")

    temporary = path.with_name(f".{path.name}.{secrets.token_hex(12)}.tmp")
    descriptor: int | None = None
    linked = False
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path, follow_symlinks=False)
        linked = True
        _fsync_directory(path.parent)
    except FileExistsError:
        existing = _read_exact_json(path) if path.exists() else None
        if existing != dict(tombstone):
            raise PrimaryForgetArtifactError("operation_conflict") from None
    except OSError as exc:
        if linked or path.exists():
            raise PrimaryForgetArtifactError("publication_ambiguous") from exc
        raise PrimaryForgetArtifactError("store_unavailable") from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        removed = False
        try:
            temporary.unlink()
            removed = True
        except FileNotFoundError:
            pass
        except OSError:
            if linked:
                raise PrimaryForgetArtifactError("publication_ambiguous") from None
        if removed:
            try:
                _fsync_directory(path.parent)
            except OSError as exc:
                raise PrimaryForgetArtifactError("publication_ambiguous") from exc

    reread = _read_exact_json(path)
    if reread != dict(tombstone):
        raise PrimaryForgetArtifactError("publication_ambiguous")
    return "new"


def read_forget_tombstone(
    store_root: str | Path,
    *,
    memory_id: str,
    operation_key: str,
) -> dict[str, Any] | None:
    root = _safe_root(store_root)
    if not is_sha256(memory_id) or not is_sha256(operation_key):
        raise PrimaryForgetArtifactError("invalid_request")
    directory = root / MUTATION_ROOT / memory_id
    if _descendant_has_symlink(root, directory):
        raise PrimaryForgetArtifactError("target_corrupt")
    path = directory / f"{operation_key}.tombstone.json"
    if not path.exists() and not path.is_symlink():
        return None
    value = _read_exact_json(path)
    if value is None or not validate_forget_tombstone(value):
        raise PrimaryForgetArtifactError("target_corrupt")
    return value


def validate_forget_tombstone(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != _TOMBSTONE_FIELDS:
        return False
    if (
        value.get("schema_version") != FORGET_TOMBSTONE_SCHEMA
        or value.get("runtime_private") is not True
        or value.get("content_included") is not True
        or value.get("operation_kind") != "forget"
        or value.get("prior_lifecycle_state") != "active"
        or value.get("result_lifecycle_state") != "hidden"
        or value.get("page_converged") is not True
        or value.get("index_converged") is not True
        or value.get("log_converged") is not True
        or value.get("retrieval_exclusion_claimed") is not False
        or value.get("status") != "reconciled"
        or value.get("recovery_required") is not False
    ):
        return False
    prior = value.get("prior_revision")
    result = value.get("result_revision")
    if type(prior) is not int or type(result) is not int or prior < 1 or result != prior + 1:
        return False
    for key in (
        "operation_key",
        "binding_digest",
        "tombstone_id",
        "memory_id",
        "prior_physical_id",
        "result_physical_id",
        "prior_canonical_digest",
        "result_canonical_digest",
        "prepared_digest",
        "reason_digest",
        "token_digest",
        "lineage_fingerprint",
        "tombstone_digest",
    ):
        if not is_sha256(value.get(key)):
            return False
    if not _bounded_text(value.get("operation_id"), 128, allow_empty=False):
        return False
    if not _bounded_text(value.get("character_id"), 128, allow_empty=False):
        return False
    if not _bounded_text(value.get("namespace"), 128, allow_empty=False):
        return False
    if not _bounded_text(value.get("reason"), 512, allow_empty=False, multiline=True):
        return False
    if value.get("source_event_kind") not in EVENT_KINDS:
        return False
    if value.get("memory_kind") not in KIND_TARGET:
        return False
    for key in ("requested_at", "prepared_at", "applied_at"):
        if not _timestamp(value.get(key)):
            return False
    expected_id = stable_hash(
        (
            "relaylm-primary-forget-tombstone-v0",
            str(value["memory_id"]),
            str(value["operation_key"]),
            str(value["binding_digest"]),
            str(value["prior_revision"]),
            str(value["result_revision"]),
            str(value["prior_physical_id"]),
            str(value["result_physical_id"]),
            str(value["prepared_digest"]),
            str(value["result_canonical_digest"]),
        )
    )
    return (
        value.get("tombstone_id") == expected_id
        and value.get("tombstone_digest") == _self_digest(value)
    )


def tombstone_matches_prepared(
    tombstone: Mapping[str, Any], prepared: Mapping[str, Any]
) -> bool:
    if not validate_forget_tombstone(tombstone) or not validate_forget_prepared(prepared):
        return False
    expected = {
        "operation_id": prepared["operation_id"],
        "operation_key": prepared["operation_key"],
        "binding_digest": prepared["binding_digest"],
        "character_id": prepared["character_id"],
        "namespace": prepared["namespace"],
        "memory_id": prepared["memory_id"],
        "prior_revision": prepared["prior_revision"],
        "result_revision": prepared["result_revision"],
        "prior_physical_id": prepared["prior_physical_id"],
        "result_physical_id": prepared["successor_physical_id"],
        "prior_canonical_digest": prepared["prior_canonical_digest"],
        "result_canonical_digest": prepared["successor_expected_canonical_digest"],
        "prepared_digest": canonical_json_digest(prepared),
        "reason": prepared["reason"],
        "reason_digest": prepared["reason_digest"],
        "token_digest": prepared["token_digest"],
        "source_event_kind": prepared["source_event_kind"],
        "memory_kind": prepared["memory_kind"],
        "lineage_fingerprint": prepared["lineage_fingerprint"],
        "requested_at": prepared["requested_at"],
        "prepared_at": prepared["prepared_at"],
    }
    return all(tombstone.get(key) == wanted for key, wanted in expected.items())


def _self_digest(value: Mapping[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "tombstone_digest"}
    return sha256(_canonical_json(payload)).hexdigest()


def _read_exact_json(path: Path) -> dict[str, Any] | None:
    try:
        before = path.lstat()
        if (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > MAX_TOMBSTONE_BYTES
        ):
            return None
        raw = path.read_bytes()
        after = path.lstat()
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_mode != after.st_mode
            or before.st_nlink != after.st_nlink
            or before.st_size != after.st_size
        ):
            return None
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("non-finite")),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(value, dict) or _canonical_json(value) + b"\n" != raw:
        return None
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _safe_root(value: str | Path) -> Path:
    if isinstance(value, Path):
        root = value
    elif isinstance(value, str) and value and value == value.strip() and "\x00" not in value:
        root = Path(value)
    else:
        raise PrimaryForgetArtifactError("store_unavailable")
    if _path_has_symlink(root):
        raise PrimaryForgetArtifactError("target_corrupt")
    if not root.exists() or not root.is_dir():
        raise PrimaryForgetArtifactError("store_unavailable")
    return root


def _ensure_private_dir(root: Path, directory: Path) -> None:
    try:
        relative = directory.relative_to(root)
    except ValueError:
        raise PrimaryForgetArtifactError("target_corrupt") from None
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise PrimaryForgetArtifactError("target_corrupt")
        if current.exists() and not current.is_dir():
            raise PrimaryForgetArtifactError("target_corrupt")
        try:
            current.mkdir(mode=0o700, exist_ok=True)
        except OSError as exc:
            raise PrimaryForgetArtifactError("store_unavailable") from exc


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _path_has_symlink(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path()
    for part in path.parts[1:] if path.is_absolute() else path.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _descendant_has_symlink(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _bounded_text(
    value: object,
    limit: int,
    *,
    allow_empty: bool,
    multiline: bool = False,
) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and len(value) <= limit
        and (allow_empty or bool(value))
        and not bad_text(value)
        and all(ord(char) not in {0x2028, 0x2029} for char in value)
        and (multiline or not any(char in value for char in "\r\n\t"))
    )


def _timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None


__all__ = [
    "FORGET_TOMBSTONE_SCHEMA",
    "MAX_TOMBSTONE_BYTES",
    "build_forget_tombstone",
    "forget_tombstone_path",
    "publish_forget_tombstone",
    "read_forget_tombstone",
    "tombstone_matches_prepared",
    "validate_forget_tombstone",
]
