"""Canonical Phase 6-C1-5 protected-source artifact helpers."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from .relaymem_slp_primary_worker_source import SOURCE_SCHEMA
from .relaymem_slp_primary_worker_source_registry import _validate_capture_payload
from .relaymem_slp_queue_record import (
    DISPATCH_KEY_PREFIX,
    JOB_ID_PREFIX,
    dedupe,
    has_prefixed_digest,
)

ARTIFACT_SCHEMA = "relaymem.slp_protected_source_artifact.v0"
CLEANUP_MARKER_SCHEMA = "relaymem.slp_protected_source_cleanup_required.v0"
ARTIFACT_FIELDS = frozenset({
    "schema_version", "runtime_private", "content_included",
    "source_schema_version", "job_id", "dispatch_idempotency_key",
    "character_id", "source_integrity_digest", "protected_capture",
})
CLEANUP_MARKER_FIELDS = frozenset({
    "schema_version", "runtime_private", "content_free", "cleanup_required",
    "artifact_key_digest", "reason_id",
})


def canonical_json_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def build_artifact(
    payload: dict[str, object], *, job_id: str, dispatch_key: str, character_id: str
) -> tuple[dict[str, object], str]:
    body = {
        "source_schema_version": SOURCE_SCHEMA,
        "job_id": job_id,
        "dispatch_idempotency_key": dispatch_key,
        "character_id": character_id,
        "protected_capture": payload,
    }
    digest = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return ({
        "schema_version": ARTIFACT_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        **body,
        "source_integrity_digest": digest,
    }, digest)


def validate_artifact(
    artifact: object, *, expected_record: Mapping[str, object],
    expected_character_id: str,
) -> tuple[dict[str, object] | None, str | None, tuple[str, ...]]:
    if type(artifact) is not dict:
        return None, None, ("protected_source_artifact_shape_invalid",)
    reasons: list[str] = []
    if len(artifact) != len(ARTIFACT_FIELDS) or set(artifact) != ARTIFACT_FIELDS:
        reasons.append("protected_source_artifact_shape_mismatch")
    if artifact.get("schema_version") != ARTIFACT_SCHEMA:
        reasons.append("protected_source_artifact_schema_mismatch")
    if artifact.get("runtime_private") is not True:
        reasons.append("protected_source_artifact_runtime_private_required")
    if artifact.get("content_included") is not True:
        reasons.append("protected_source_artifact_content_required")
    if artifact.get("source_schema_version") != SOURCE_SCHEMA:
        reasons.append("protected_source_source_schema_mismatch")
    if artifact.get("job_id") != expected_record.get("job_id"):
        reasons.append("protected_source_job_id_mismatch")
    if artifact.get("dispatch_idempotency_key") != expected_record.get(
        "dispatch_idempotency_key"
    ):
        reasons.append("protected_source_dispatch_idempotency_key_mismatch")
    if artifact.get("character_id") != expected_character_id:
        reasons.append("protected_source_character_mismatch")
    capture = artifact.get("protected_capture")
    validated, capture_reasons = _validate_capture_payload(capture, expected_record)
    reasons.extend(capture_reasons)
    if validated is None:
        return None, None, dedupe(tuple(reasons))
    body = {
        "source_schema_version": artifact.get("source_schema_version"),
        "job_id": artifact.get("job_id"),
        "dispatch_idempotency_key": artifact.get("dispatch_idempotency_key"),
        "character_id": artifact.get("character_id"),
        "protected_capture": validated,
    }
    try:
        digest = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    except (TypeError, ValueError, RecursionError, OverflowError):
        reasons.append("protected_source_integrity_input_invalid")
        return None, None, dedupe(tuple(reasons))
    if artifact.get("source_integrity_digest") != digest:
        reasons.append("protected_source_integrity_digest_mismatch")
    if reasons:
        return None, None, dedupe(tuple(reasons))
    return dict(validated), digest, ()


def decode_canonical_json(data: bytes) -> tuple[dict[str, object] | None, str | None]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, "protected_source_artifact_malformed_utf8"
    duplicate = False

    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        nonlocal duplicate
        result: dict[str, object] = {}
        for key, value in pairs:
            duplicate = duplicate or key in result
            result[key] = value
        return result

    def reject_nonfinite(_: str) -> object:
        raise ValueError("non-finite JSON")

    try:
        value = json.loads(
            text, object_pairs_hook=object_pairs, parse_constant=reject_nonfinite
        )
    except (json.JSONDecodeError, RecursionError, ValueError):
        return None, "protected_source_artifact_malformed_json"
    if duplicate:
        return None, "protected_source_artifact_duplicate_json_key"
    if type(value) is not dict:
        return None, "protected_source_artifact_json_not_object"
    try:
        if canonical_json_bytes(value) != data:
            return None, "protected_source_artifact_noncanonical_json"
    except (TypeError, ValueError, RecursionError, OverflowError):
        return None, "protected_source_artifact_malformed_json"
    return value, None


def artifact_key_digest(job_id: str, dispatch_key: str) -> str:
    return hashlib.sha256(
        (ARTIFACT_SCHEMA + "\0" + job_id + "\0" + dispatch_key).encode("utf-8")
    ).hexdigest()


def artifact_filename(job_id: str, dispatch_key: str) -> str:
    if not has_prefixed_digest(job_id, JOB_ID_PREFIX) or not has_prefixed_digest(
        dispatch_key, DISPATCH_KEY_PREFIX
    ):
        raise ValueError("protected_source_identity_invalid")
    return f"protected-source-v0-{artifact_key_digest(job_id, dispatch_key)}.json"


def cleanup_marker_filename(artifact_name: str) -> str:
    digest = artifact_name.removeprefix("protected-source-v0-").removesuffix(".json")
    return f".protected-source-cleanup-{digest}.json"


__all__ = [
    "ARTIFACT_SCHEMA", "CLEANUP_MARKER_FIELDS", "CLEANUP_MARKER_SCHEMA",
    "artifact_filename", "artifact_key_digest", "build_artifact",
    "canonical_json_bytes", "cleanup_marker_filename", "decode_canonical_json",
    "validate_artifact",
]
