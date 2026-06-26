"""Public RelayMEM M3c Primary MEM page-candidate boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from ._relaymem_primary_page_candidate_impl import (
    build_relaymem_governed_experience_summary,
    build_relaymem_primary_page_candidate_dry_run as _build_primary_page_candidate,
)
from .relaymem_primary_lifecycle_page import (
    HIDDEN_PAGE_SUMMARY,
    build_hidden_primary_page_markdown,
)


def build_relaymem_primary_page_candidate_dry_run(
    *,
    preflight_artifact: Mapping[str, Any] | None,
    source_lineage_artifact: Mapping[str, Any] | None,
    governed_experience_artifact: Mapping[str, Any] | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> dict[str, Any]:
    """Build M3c candidates while preserving the source M3b operation index."""

    result = _build_primary_page_candidate(
        preflight_artifact=preflight_artifact,
        source_lineage_artifact=source_lineage_artifact,
        governed_experience_artifact=governed_experience_artifact,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
    )
    if result.get("page_candidate_count") != 1:
        return result
    if not isinstance(preflight_artifact, Mapping) or not isinstance(
        governed_experience_artifact, Mapping
    ):
        return result

    raw_candidate_id = governed_experience_artifact.get("candidate_id")
    if not isinstance(raw_candidate_id, str):
        return result
    candidate_id = raw_candidate_id.strip()

    operations = preflight_artifact.get("operations")
    if not isinstance(operations, Sequence) or isinstance(operations, (str, bytes)):
        return result
    matching_indexes = [
        index
        for index, operation in enumerate(operations)
        if isinstance(operation, Mapping) and operation.get("candidate_id") == candidate_id
    ]
    if len(matching_indexes) != 1:
        return result

    projection = result.get("projection")
    if not isinstance(projection, dict):
        return result
    projected_pages = projection.get("page_candidates")
    if not isinstance(projected_pages, list) or len(projected_pages) != 1:
        return result
    projected_page = projected_pages[0]
    if not isinstance(projected_page, dict):
        return result

    projected_page["operation_index"] = matching_indexes[0]
    return result


def build_relaymem_primary_hidden_page_candidate(
    *,
    preflight_artifact: Mapping[str, Any],
    source_lineage_artifact: Mapping[str, Any],
    prepared_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one hidden lifecycle candidate through the existing M3c authority."""

    experience = build_relaymem_governed_experience_summary(
        candidate_id=str(prepared_artifact.get("successor_candidate_id", "")),
        source_event_kind=str(prepared_artifact.get("source_event_kind", "")),
        namespace=str(prepared_artifact.get("namespace", "")),
        summary_text=HIDDEN_PAGE_SUMMARY,
        title="",
    )
    result = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight_artifact,
        source_lineage_artifact=source_lineage_artifact,
        governed_experience_artifact=experience,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    pages = result.get("page_candidates")
    if (
        result.get("page_candidate_count") != 1
        or not isinstance(pages, list)
        or len(pages) != 1
        or not isinstance(pages[0], dict)
        or pages[0].get("idempotency_key")
        != prepared_artifact.get("successor_physical_id")
        or pages[0].get("target_relative_path")
        != prepared_artifact.get("successor_relative_path")
    ):
        return _blocked_hidden_result(result, "primary_hidden_page_candidate_identity_mismatch")

    try:
        markdown = build_hidden_primary_page_markdown(
            memory_kind=str(prepared_artifact["memory_kind"]),
            source_event_kind=str(prepared_artifact["source_event_kind"]),
            namespace=str(prepared_artifact["namespace"]),
            lineage_fingerprint=str(prepared_artifact["lineage_fingerprint"]),
            successor_physical_id=str(prepared_artifact["successor_physical_id"]),
            memory_id=str(prepared_artifact["memory_id"]),
            revision=int(prepared_artifact["result_revision"]),
            prior_revision=int(prepared_artifact["prior_revision"]),
            prior_physical_id=str(prepared_artifact["prior_physical_id"]),
            operation_key=str(prepared_artifact["operation_key"]),
            binding_digest=str(prepared_artifact["binding_digest"]),
        )
        encoded = markdown.encode("utf-8")
    except (KeyError, TypeError, ValueError, UnicodeEncodeError):
        return _blocked_hidden_result(result, "primary_hidden_page_candidate_invalid")
    digest = sha256(encoded).hexdigest()
    if digest != prepared_artifact.get("successor_expected_canonical_digest"):
        return _blocked_hidden_result(result, "primary_hidden_page_candidate_digest_mismatch")

    page = pages[0]
    page["summary_origin"] = "lifecycle_projection"
    page["page_markdown"] = markdown
    page["page_bytes"] = len(encoded)
    page["page_digest"] = digest
    page["summary_chars"] = len(HIDDEN_PAGE_SUMMARY)
    projection = result.get("projection")
    if isinstance(projection, dict):
        projected = projection.get("page_candidates")
        if isinstance(projected, list) and len(projected) == 1 and isinstance(projected[0], dict):
            projected[0]["page_bytes"] = len(encoded)
            projected[0]["summary_chars"] = len(HIDDEN_PAGE_SUMMARY)
    result["lifecycle_candidate"] = "hidden"
    return result


def _blocked_hidden_result(result: dict[str, Any], reason: str) -> dict[str, Any]:
    result = dict(result)
    result["page_candidate_count"] = 0
    result["page_candidates"] = []
    result["blocked_reasons"] = list(dict.fromkeys([*result.get("blocked_reasons", []), reason]))
    projection = result.get("projection")
    if isinstance(projection, dict):
        projection = dict(projection)
        projection["page_candidate_count"] = 0
        projection["page_candidates"] = []
        projection["blocked_reasons"] = list(
            dict.fromkeys([*projection.get("blocked_reasons", []), reason])
        )
        result["projection"] = projection
    return result


__all__ = [
    "build_relaymem_governed_experience_summary",
    "build_relaymem_primary_hidden_page_candidate",
    "build_relaymem_primary_page_candidate_dry_run",
]
