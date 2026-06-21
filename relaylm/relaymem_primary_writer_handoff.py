"""Public RelayMEM M3d Primary MEM writer-handoff boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from ._relaymem_primary_writer_handoff_impl import (
    build_relaymem_primary_writer_handoff_preflight as _build_preflight,
)

_M3C_RESULT_SCHEMA = "relaymem.primary_page_candidate_dry_run.v0"
_M3C_CANDIDATE_SCHEMA = "relaymem.primary_page_candidate.v0"
_SCHEMA_REJECTION = "relaymem.primary_page_candidate_dry_run.rejected.v0"
_SCHEMA_REASON = "primary_page_candidate_artifact_schema_mismatch"
_IDEMPOTENCY_REASON = "primary_page_candidate_idempotency_key_mismatch"


def build_relaymem_primary_writer_handoff_preflight(
    *,
    page_candidate_artifact: Mapping[str, Any] | None,
    root_path: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> dict[str, Any]:
    """Revalidate M3b idempotency before delegating to the M3d implementation."""

    artifact = page_candidate_artifact
    replace_schema_reason = _has_idempotency_mismatch(artifact)
    if replace_schema_reason and isinstance(artifact, Mapping):
        artifact = dict(artifact)
        artifact["schema_version"] = _SCHEMA_REJECTION

    result = _build_preflight(
        page_candidate_artifact=artifact,
        root_path=root_path,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
    )
    if replace_schema_reason:
        _replace_reason(result, _SCHEMA_REASON, _IDEMPOTENCY_REASON)
    return result


def _has_idempotency_mismatch(value: object) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != _M3C_RESULT_SCHEMA:
        return False
    candidates = value.get("page_candidates")
    if (
        not isinstance(candidates, Sequence)
        or isinstance(candidates, (str, bytes))
        or len(candidates) != 1
        or not isinstance(candidates[0], Mapping)
    ):
        return False
    candidate = candidates[0]
    if candidate.get("schema_version") != _M3C_CANDIDATE_SCHEMA:
        return False

    fields = (
        candidate.get("namespace"),
        candidate.get("source_event_kind"),
        candidate.get("lineage_fingerprint"),
        candidate.get("candidate_id"),
        candidate.get("memory_kind"),
        candidate.get("idempotency_key"),
    )
    if not all(isinstance(field, str) for field in fields):
        return False
    namespace, source_event_kind, lineage_fingerprint, candidate_id, memory_kind, key = fields
    expected = _stable(
        (
            "relaymem-primary-write-preflight-v0",
            namespace,
            source_event_kind,
            lineage_fingerprint,
            candidate_id,
            source_event_kind,
            "primary",
            memory_kind,
            "free_to_update",
        )
    )
    return key != expected


def _replace_reason(result: dict[str, Any], old: str, new: str) -> None:
    result["blocked_reasons"] = [
        new if reason == old else reason for reason in result.get("blocked_reasons", [])
    ]
    projection = result.get("projection")
    if isinstance(projection, dict):
        projection["blocked_reasons"] = [
            new if reason == old else reason
            for reason in projection.get("blocked_reasons", [])
        ]


def _stable(parts: Sequence[str]) -> str:
    digest = sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


__all__ = ["build_relaymem_primary_writer_handoff_preflight"]
