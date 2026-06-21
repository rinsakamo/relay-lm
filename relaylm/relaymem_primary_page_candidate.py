"""Public RelayMEM M3c Primary MEM page-candidate boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ._relaymem_primary_page_candidate_impl import (
    build_relaymem_governed_experience_summary,
    build_relaymem_primary_page_candidate_dry_run as _build_primary_page_candidate,
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

    candidate_id = governed_experience_artifact.get("candidate_id")
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


__all__ = [
    "build_relaymem_governed_experience_summary",
    "build_relaymem_primary_page_candidate_dry_run",
]
