"""RT-1B disposable Subjective MEM retrieval projection bundle store.

One replace-only local file holds exactly one projection generation. The store
depends on ``relaylm.subjective_mem.retrieval_projection`` and never the other
way round: that module owns deriving the projection value from canonical
authority, and this one owns only serializing, replacing, reading, and deleting
it.

The bundle is disposable and noncanonical. Deleting it changes no canonical
Markdown, selector, receipt, lifecycle record, tombstone, or transition, and the
store never reads or writes any of them.

The serialized digests are ordinary recomputable hashes, so they detect
accidental corruption and nothing more. A persisted bundle becomes trusted only
by rebuilding the expected projection from the exact fixed source snapshot and
requiring the decoded manifest and ordered row population to equal that rebuild.
There is no source-less trusted read, repair-on-read, partial acceptance, or
stale-generation fallback, and no secret, signature service, or key store is
introduced. Every entry point returns reasons instead of raising.
"""
from __future__ import annotations

import json
import os
import stat
from dataclasses import fields
from pathlib import Path

from relaylm.evidence.common import canonical_digest, canonical_json_bytes, dedupe
from relaylm.subjective_mem.retrieval import (
    SubjectiveMemRetrievalProjectionManifest, SubjectiveMemRetrievalProjectionRow,
    validate_subjective_mem_retrieval_projection_manifest,
    validate_subjective_mem_retrieval_projection_row,
)
from relaylm.subjective_mem.retrieval_projection import (
    SOURCE_SCHEMA_REVISION_DIGEST, SubjectiveMemRetrievalProjection,
    build_subjective_mem_retrieval_projection,
)

SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_BUNDLE_SCHEMA = "relaylm.subjective_mem_retrieval_projection_bundle.v1"
PROJECTION_BUNDLE_FILENAME = "subjective-mem-retrieval-projection.json"
MAX_PROJECTION_BUNDLE_BYTES = 4 * 1024 * 1024

_MANIFEST_FIELDS = tuple(item.name for item in fields(SubjectiveMemRetrievalProjectionManifest))
_ROW_FIELDS = tuple(item.name for item in fields(SubjectiveMemRetrievalProjectionRow))


def serialize_subjective_mem_retrieval_projection(
    projection: SubjectiveMemRetrievalProjection,
) -> dict[str, object]:
    """Encode the content-free bundle with an accidental-corruption tag."""

    body = {
        "schema": SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_BUNDLE_SCHEMA,
        "manifest": projection.manifest.to_digest_input(),
        "rows": [row.to_digest_input() for row in projection.rows],
        "canonical_authority": False,
        "rebuildable": True,
    }
    return {**body, "bundle_digest": canonical_digest(body)}


def load_subjective_mem_retrieval_projection(
    payload: object, *, source: object
) -> tuple[SubjectiveMemRetrievalProjection | None, tuple[str, ...]]:
    """Accept a persisted bundle only when it equals the exact source rebuild.

    The bundle's digests authenticate nothing on their own. Trust comes from the
    rebuild comparison; there is no repair-on-read, partial acceptance,
    source-less trusted route, or stale-generation fallback.
    """

    expected, reasons = build_subjective_mem_retrieval_projection(source)
    if expected is None:
        return None, reasons
    decoded, reasons = _decode_projection_bundle(payload)
    if decoded is None:
        return None, reasons
    if (
        decoded.manifest.projection_generation_id != expected.manifest.projection_generation_id
        or decoded.manifest.source_snapshot_digest != expected.manifest.source_snapshot_digest
    ):
        return None, ("subjective_mem_retrieval_projection_stale_generation",)
    if decoded.manifest != expected.manifest or decoded.rows != expected.rows:
        return None, ("subjective_mem_retrieval_projection_not_source_exact",)
    return decoded, ()


def _decode_projection_bundle(
    payload: object,
) -> tuple[SubjectiveMemRetrievalProjection | None, tuple[str, ...]]:
    """Structurally decode and revalidate one serialized bundle.

    Proves shape, RT-1A validity, generation uniformity, and population
    agreement. It establishes no trust, and stays private for that reason.
    """

    body = _intact_bundle_body(payload)
    if body is None:
        return None, ("subjective_mem_retrieval_projection_bundle_tampered",)
    manifest = _manifest_from_body(body.get("manifest"))
    raw_rows = body.get("rows")
    if manifest is None or not isinstance(raw_rows, list):
        return None, ("subjective_mem_retrieval_projection_bundle_shape_invalid",)
    rows: list[SubjectiveMemRetrievalProjectionRow] = []
    for raw in raw_rows:
        row = _row_from_body(raw)
        if row is None:
            return None, ("subjective_mem_retrieval_projection_bundle_shape_invalid",)
        rows.append(row)

    reasons = list(validate_subjective_mem_retrieval_projection_manifest(manifest))
    for row in rows:
        reasons.extend(validate_subjective_mem_retrieval_projection_row(row))
    if any(row.projection_generation_id != manifest.projection_generation_id for row in rows):
        reasons.append("subjective_mem_retrieval_projection_mixed_generation")
    digests = tuple(row.row_digest for row in rows)
    if len(set(digests)) != len(digests):
        reasons.append("subjective_mem_retrieval_projection_row_duplicated")
    elif digests != tuple(sorted(digests)) or digests != manifest.row_digests:
        reasons.append("subjective_mem_retrieval_projection_population_mismatch")
    if manifest.source_schema_revision_digest != SOURCE_SCHEMA_REVISION_DIGEST:
        reasons.append("subjective_mem_retrieval_projection_source_revision_unsupported")
    if reasons:
        return None, dedupe(reasons)
    return SubjectiveMemRetrievalProjection(manifest=manifest, rows=tuple(rows)), ()


def write_subjective_mem_retrieval_projection(
    *, projection_root: str, source: object, projection: object
) -> tuple[str, ...]:
    """Replace the stored bundle only with the exact rebuild of ``source``."""

    target, reasons = _bundle_path(projection_root)
    if target is None:
        return reasons
    if type(projection) is not SubjectiveMemRetrievalProjection:
        return ("subjective_mem_retrieval_projection_invalid",)
    expected, reasons = build_subjective_mem_retrieval_projection(source)
    if expected is None:
        return reasons
    if projection.manifest != expected.manifest or projection.rows != expected.rows:
        return ("subjective_mem_retrieval_projection_not_source_exact",)
    data = canonical_json_bytes(serialize_subjective_mem_retrieval_projection(projection))
    if len(data) > MAX_PROJECTION_BUNDLE_BYTES:
        return ("subjective_mem_retrieval_projection_bundle_oversize",)
    return _atomic_replace(target, data)


def read_subjective_mem_retrieval_projection(
    *, projection_root: str, source: object
) -> tuple[SubjectiveMemRetrievalProjection | None, tuple[str, ...]]:
    """Read the persisted bundle and accept it only against its exact source."""

    target, reasons = _bundle_path(projection_root)
    if target is None:
        return None, reasons
    try:
        info = target.lstat()
    except FileNotFoundError:
        return None, ("subjective_mem_retrieval_projection_absent",)
    except OSError:
        return None, ("subjective_mem_retrieval_projection_bundle_unreadable",)
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        return None, ("subjective_mem_retrieval_projection_bundle_unsafe",)
    if info.st_size > MAX_PROJECTION_BUNDLE_BYTES:
        return None, ("subjective_mem_retrieval_projection_bundle_oversize",)
    try:
        payload = json.loads(target.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None, ("subjective_mem_retrieval_projection_bundle_unreadable",)
    return load_subjective_mem_retrieval_projection(payload, source=source)


def delete_subjective_mem_retrieval_projection(*, projection_root: str) -> tuple[str, ...]:
    """Delete the disposable projection bundle, touching no canonical authority."""

    target, reasons = _bundle_path(projection_root)
    if target is None:
        return reasons
    try:
        os.unlink(target)
    except FileNotFoundError:
        return ()
    except OSError:
        return ("subjective_mem_retrieval_projection_delete_failed",)
    return ()


def _bundle_path(projection_root: object) -> tuple[Path | None, tuple[str, ...]]:
    """Resolve the one bundle path under a bounded, non-symlinked absolute root."""

    if type(projection_root) is not str or not projection_root:
        return None, ("subjective_mem_retrieval_projection_root_missing",)
    path = Path(projection_root)
    if not path.is_absolute() or any(part in {".", ".."} for part in path.parts[1:]):
        return None, ("subjective_mem_retrieval_projection_root_invalid",)
    try:
        if path.is_symlink() or not path.is_dir():
            return None, ("subjective_mem_retrieval_projection_root_unsafe",)
    except OSError:
        return None, ("subjective_mem_retrieval_projection_root_unsafe",)
    return path / PROJECTION_BUNDLE_FILENAME, ()


def _atomic_replace(target: Path, data: bytes) -> tuple[str, ...]:
    """Install the bundle atomically so no partial generation is ever readable."""

    temp = target.with_name(f".{target.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(temp, flags, 0o600)
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(descriptor, view) :]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temp, target)
    except OSError:
        try:
            os.unlink(temp)
        except OSError:
            pass
        return ("subjective_mem_retrieval_projection_write_failed",)
    return ()


def _intact_bundle_body(payload: object) -> dict[str, object] | None:
    """Detect accidental corruption of the serialized body; not authentication."""

    if not isinstance(payload, dict):
        return None
    body = {key: value for key, value in payload.items() if key != "bundle_digest"}
    if (
        body.get("schema") != SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_BUNDLE_SCHEMA
        or body.get("canonical_authority") is not False
        or body.get("rebuildable") is not True
    ):
        return None
    try:
        expected = canonical_digest(body)
    except (TypeError, ValueError):
        return None
    return body if payload.get("bundle_digest") == expected else None


def _manifest_from_body(body: object) -> SubjectiveMemRetrievalProjectionManifest | None:
    if not isinstance(body, dict) or not isinstance(body.get("row_digests"), (list, tuple)):
        return None
    values = {**body, "row_digests": tuple(body["row_digests"])}
    try:
        manifest = SubjectiveMemRetrievalProjectionManifest(
            **{name: values[name] for name in _MANIFEST_FIELDS}
        )
    except (KeyError, TypeError):
        return None
    return manifest if manifest.to_digest_input() == values else None


def _row_from_body(body: object) -> SubjectiveMemRetrievalProjectionRow | None:
    if not isinstance(body, dict):
        return None
    try:
        row = SubjectiveMemRetrievalProjectionRow(**{name: body[name] for name in _ROW_FIELDS})
    except (KeyError, TypeError):
        return None
    return row if row.to_digest_input() == body else None


__all__ = [
    "MAX_PROJECTION_BUNDLE_BYTES", "PROJECTION_BUNDLE_FILENAME",
    "SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_BUNDLE_SCHEMA",
    "delete_subjective_mem_retrieval_projection", "load_subjective_mem_retrieval_projection",
    "read_subjective_mem_retrieval_projection", "serialize_subjective_mem_retrieval_projection",
    "write_subjective_mem_retrieval_projection",
]
