"""Strict immutable runtime-private artifact support for I-4C1 Forget prepare.

The artifact is durable continuation evidence.  It is deliberately stored beside
Phase I-3 correction artifacts so Correct and Forget share one per-memory fence,
but it has its own exact schema and never becomes a public projection.
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

from . import _relaymem_primary_current_state_impl as _current_impl
from ._relaymem_primary_page_writer_common import bad_text, is_sha256, stable_hash

FORGET_PREPARED_SCHEMA = "relaylm.mem.forget_prepared.v0"
CORRECTION_PREPARED_SCHEMA = "relaylm.mem.correct_prepared.v0"
CORRECTION_RECEIPT_SCHEMA = "relaylm.mem.correct_receipt.v0"
MUTATION_ROOT = PurePosixPath("memory/mem/corrections/v0")
MAX_ARTIFACT_BYTES = 32_768

_FORGET_FIELDS = {
    "schema_version",
    "runtime_private",
    "content_included",
    "operation_kind",
    "operation_id",
    "operation_key",
    "binding_digest",
    "character_id",
    "namespace",
    "memory_id",
    "prior_revision",
    "result_revision",
    "prior_lifecycle_state",
    "result_lifecycle_state",
    "prior_physical_id",
    "successor_physical_id",
    "successor_candidate_id",
    "successor_relative_path",
    "prior_canonical_digest",
    "successor_expected_canonical_digest",
    "source_event_kind",
    "memory_kind",
    "lineage_fingerprint",
    "reason",
    "reason_digest",
    "token_digest",
    "requested_at",
    "prepared_at",
    "status",
    "recovery_required",
}


class PrimaryForgetArtifactError(RuntimeError):
    """Bounded artifact failure without paths, content, digests, or exceptions."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def forget_operation_key(operation_id: str) -> str:
    if not _bounded_text(operation_id, 128, allow_empty=False):
        raise PrimaryForgetArtifactError("invalid_request")
    return stable_hash(("relaymem-primary-forget-operation-v0", operation_id))


def forget_operation_path(
    store_root: str | Path, *, memory_id: str, operation_key: str
) -> Path:
    root = _safe_root(store_root)
    if not is_sha256(memory_id) or not is_sha256(operation_key):
        raise PrimaryForgetArtifactError("invalid_request")
    directory = root / MUTATION_ROOT / memory_id
    _ensure_private_dir(root, directory)
    return directory / f"{operation_key}.prepared.json"


def publish_forget_prepared(
    store_root: str | Path, *, artifact: Mapping[str, Any]
) -> str:
    """Create an exact immutable prepared artifact and canonically reread it."""

    if not validate_forget_prepared(artifact):
        raise PrimaryForgetArtifactError("target_corrupt")
    path = forget_operation_path(
        store_root,
        memory_id=str(artifact["memory_id"]),
        operation_key=str(artifact["operation_key"]),
    )
    payload = _canonical_json(artifact) + b"\n"
    if len(payload) > MAX_ARTIFACT_BYTES:
        raise PrimaryForgetArtifactError("target_corrupt")

    if path.exists() or path.is_symlink():
        existing = _read_exact_json(path)
        if existing == dict(artifact):
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
        if existing != dict(artifact):
            raise PrimaryForgetArtifactError("operation_conflict") from None
    except OSError as exc:
        # A failed link/fsync can have an ambiguous durable outcome.  Never infer
        # success from the absence of an exception-free return.
        if linked or path.exists():
            raise PrimaryForgetArtifactError("publication_ambiguous") from exc
        raise PrimaryForgetArtifactError("store_unavailable") from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        temporary_removed = False
        try:
            temporary.unlink()
            temporary_removed = True
        except FileNotFoundError:
            pass
        except OSError:
            if linked:
                raise PrimaryForgetArtifactError("publication_ambiguous") from None
        if temporary_removed:
            try:
                _fsync_directory(path.parent)
            except OSError as exc:
                raise PrimaryForgetArtifactError("publication_ambiguous") from exc

    reread = _read_exact_json(path)
    if reread != dict(artifact):
        raise PrimaryForgetArtifactError("publication_ambiguous")
    return "new"


def read_forget_prepared(
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
    path = directory / f"{operation_key}.prepared.json"
    if not path.exists() and not path.is_symlink():
        return None
    value = _read_exact_json(path)
    if value is None or not validate_forget_prepared(value):
        raise PrimaryForgetArtifactError("target_corrupt")
    return value


def scan_forget_prepared(
    store_root: str | Path, *, memory_id: str
) -> tuple[dict[str, Any] | None, bool]:
    """Return the sole valid Forget prepare and whether the directory is corrupt."""

    root = _safe_root(store_root)
    if not is_sha256(memory_id):
        raise PrimaryForgetArtifactError("target_not_found")
    directory = root / MUTATION_ROOT / memory_id
    if _descendant_has_symlink(root, directory):
        return None, True
    if not directory.exists() and not directory.is_symlink():
        return None, False
    if directory.is_symlink() or not directory.is_dir():
        return None, True
    try:
        entries = sorted(directory.iterdir(), key=lambda item: item.name)
    except OSError:
        return None, True

    forget: list[dict[str, Any]] = []
    corrupt = False
    for path in entries:
        if path.name == ".lock":
            if path.is_symlink() or (path.exists() and not path.is_file()):
                corrupt = True
            continue
        value = _read_exact_json(path)
        if value is None:
            corrupt = True
            continue
        schema = value.get("schema_version")
        if schema == FORGET_PREPARED_SCHEMA:
            if not path.name.endswith(".prepared.json") or not validate_forget_prepared(value):
                corrupt = True
            else:
                forget.append(value)
        elif schema == "relaylm.mem.forget_tombstone.v0":
            from .relaymem_primary_forget_finalization_artifact import (
                validate_forget_tombstone,
            )

            if (
                not path.name.endswith(".tombstone.json")
                or not validate_forget_tombstone(value)
            ):
                corrupt = True
        elif schema == CORRECTION_PREPARED_SCHEMA:
            namespace = value.get("namespace")
            logical_id = value.get("memory_id")
            if (
                not path.name.endswith(".prepared.json")
                or not isinstance(namespace, str)
                or not isinstance(logical_id, str)
                or not _current_impl._valid_prepared(
                    value, namespace=namespace, memory_id=logical_id
                )
            ):
                corrupt = True
        elif schema == CORRECTION_RECEIPT_SCHEMA:
            namespace = value.get("namespace")
            logical_id = value.get("memory_id")
            if (
                not path.name.endswith(".applied.json")
                or not isinstance(namespace, str)
                or not isinstance(logical_id, str)
                or not _current_impl._valid_applied(
                    value, namespace=namespace, memory_id=logical_id
                )
            ):
                corrupt = True
        else:
            corrupt = True
    if len(forget) > 1:
        corrupt = True
    return (forget[0] if len(forget) == 1 else None), corrupt


def validate_forget_prepared(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != _FORGET_FIELDS:
        return False
    if (
        value.get("schema_version") != FORGET_PREPARED_SCHEMA
        or value.get("runtime_private") is not True
        or value.get("content_included") is not True
        or value.get("operation_kind") != "forget"
        or value.get("prior_lifecycle_state") != "active"
        or value.get("result_lifecycle_state") != "hidden"
        or value.get("status") != "prepared"
        or value.get("recovery_required") is not True
    ):
        return False
    prior = value.get("prior_revision")
    result = value.get("result_revision")
    if type(prior) is not int or type(result) is not int or prior < 1 or result != prior + 1:
        return False
    for key in (
        "operation_key",
        "binding_digest",
        "memory_id",
        "prior_physical_id",
        "successor_physical_id",
        "successor_candidate_id",
        "prior_canonical_digest",
        "successor_expected_canonical_digest",
        "lineage_fingerprint",
        "reason_digest",
        "token_digest",
    ):
        if not is_sha256(value.get(key)):
            return False
    if not _bounded_text(value.get("operation_id"), 128, allow_empty=False):
        return False
    if not _bounded_text(value.get("character_id"), 128, allow_empty=False):
        return False
    if not _bounded_text(value.get("namespace"), 128, allow_empty=False):
        return False
    if not _bounded_text(value.get("source_event_kind"), 128, allow_empty=False):
        return False
    if not _bounded_text(value.get("memory_kind"), 128, allow_empty=False):
        return False
    if not _bounded_text(value.get("reason"), 512, allow_empty=False, multiline=True):
        return False
    if not _safe_relative_path(value.get("successor_relative_path")):
        return False
    if not _timestamp(value.get("requested_at")) or not _timestamp(value.get("prepared_at")):
        return False
    expected_key = forget_operation_key(str(value["operation_id"]))
    return expected_key == value.get("operation_key")


def canonical_json_digest(value: Mapping[str, Any]) -> str:
    return sha256(_canonical_json(value)).hexdigest()


def _read_exact_json(path: Path) -> dict[str, Any] | None:
    try:
        info = path.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size <= 0
            or info.st_size > MAX_ARTIFACT_BYTES
        ):
            return None
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
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
        dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
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


def _safe_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        return False
    path = PurePosixPath(value)
    return path.as_posix() == value and all(part not in {"", ".", ".."} for part in path.parts)


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
    "FORGET_PREPARED_SCHEMA",
    "MUTATION_ROOT",
    "PrimaryForgetArtifactError",
    "canonical_json_digest",
    "forget_operation_key",
    "forget_operation_path",
    "publish_forget_prepared",
    "read_forget_prepared",
    "scan_forget_prepared",
    "validate_forget_prepared",
]
