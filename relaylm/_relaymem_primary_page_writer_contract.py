"""M3d result/projection validation for RelayMEM M3e."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ._relaymem_primary_page_writer_common import (
    PROJECTION_FORBIDDEN_KEYS,
    contains_forbidden_content_key,
    contains_key,
    dedupe,
    exact,
    invalid,
    strings,
)
from ._relaymem_primary_page_writer_handoff import parse_m3d_handoff

M3D_RESULT_SCHEMA = "relaymem.primary_writer_handoff_preflight.v0"
M3D_PROJECTION_SCHEMA = "relaymem.primary_writer_handoff_projection.v0"


def parse_relaymem_primary_writer_handoff(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return invalid("primary_writer_handoff_artifact_missing")
    if value.get("schema_version") != M3D_RESULT_SCHEMA:
        return invalid("primary_writer_handoff_artifact_schema_mismatch")
    reasons = exact(
        value,
        {
            "diagnostics_only": True,
            "helper_only": True,
            "read_only": True,
            "runtime_private_handoffs": True,
            "enabled": True,
            "dry_run_only": False,
            "apply_enabled": True,
            "write_apply_supported": False,
            "apply_allowed": False,
            "writes_memory": False,
            "updates_index": False,
            "updates_log": False,
            "mutates_soul": False,
            "invokes_slp": False,
            "lab_api_exposed": False,
            "runtime_wired": False,
            "visible_response_changed": False,
            "store_root_configured": True,
            "page_candidate_valid": True,
        },
        "primary_writer_handoff_artifact_",
    )
    if contains_forbidden_content_key(value):
        reasons.append("primary_writer_handoff_artifact_forbidden_content_field")
    if strings(value.get("blocked_reasons")):
        reasons.append("primary_writer_handoff_artifact_blocked")

    handoffs = value.get("handoffs")
    if not isinstance(handoffs, Sequence) or isinstance(handoffs, (str, bytes)):
        return invalid(*(reasons + ["primary_writer_handoffs_invalid"]))
    count = value.get("handoff_count")
    if isinstance(count, bool) or not isinstance(count, int) or count != len(handoffs):
        reasons.append("primary_writer_handoff_count_mismatch")
    if len(handoffs) != 1 or not isinstance(handoffs[0], Mapping):
        return invalid(*(reasons + ["primary_writer_handoff_cardinality_invalid"]))

    handoff = parse_m3d_handoff(handoffs[0])
    if handoff.get("valid") is not True:
        reasons.extend(handoff["blocked_reasons"])
    projection = _parse_m3d_projection(value.get("projection"), handoff)
    if projection.get("valid") is not True:
        reasons.extend(projection["blocked_reasons"])
    reasons = dedupe(reasons)
    if reasons:
        return invalid(*reasons)
    return {"valid": True, "handoff": handoff, "blocked_reasons": []}


def _parse_m3d_projection(value: object, handoff: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return invalid("primary_writer_handoff_projection_missing")
    if value.get("schema_version") != M3D_PROJECTION_SCHEMA:
        return invalid("primary_writer_handoff_projection_schema_mismatch")
    reasons = exact(
        value,
        {
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "store_root_path_included": False,
            "candidate_id_included": False,
            "namespace_included": False,
            "target_path_included": False,
            "lineage_fingerprint_included": False,
            "idempotency_key_included": False,
            "page_markdown_included": False,
            "page_digest_included": False,
            "raw_source_text_included": False,
            "raw_message_history_included": False,
            "raw_affect_estimates_included": False,
            "writes_memory": False,
            "updates_index": False,
            "updates_log": False,
            "handoff_count": 1,
            "writer_apply_eligible_count": 1,
            "root_present": True,
            "target_parent_present": True,
            "target_exists": False,
            "target_digest_matches": False,
            "idempotent_noop": False,
        },
        "primary_writer_handoff_projection_",
    )
    if contains_key(value, PROJECTION_FORBIDDEN_KEYS):
        reasons.append("primary_writer_handoff_projection_content_field_present")
    if strings(value.get("blocked_reasons")):
        reasons.append("primary_writer_handoff_projection_blocked")
    if value.get("status_counts") != {"ready": 1}:
        reasons.append("primary_writer_handoff_projection_status_counts_invalid")
    if value.get("target_category_counts") != {handoff.get("target_category", "unknown"): 1}:
        reasons.append("primary_writer_handoff_projection_category_counts_invalid")
    items = value.get("handoffs")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)) or len(items) != 1:
        reasons.append("primary_writer_handoff_projection_items_invalid")
    elif not isinstance(items[0], Mapping):
        reasons.append("primary_writer_handoff_projection_item_invalid")
    else:
        reasons.extend(
            exact(
                items[0],
                {
                    "operation_index": 0,
                    "source_event_kind": handoff.get("source_event_kind"),
                    "memory_layer": "primary",
                    "memory_kind": handoff.get("memory_kind"),
                    "promotion_policy": "free_to_update",
                    "safety_scope": "ordinary_memory",
                    "target_category": handoff.get("target_category"),
                    "preflight_status": "ready",
                    "target_exists": False,
                    "target_digest_matches": False,
                    "idempotent_noop": False,
                    "writer_apply_eligible": True,
                    "page_bytes": handoff.get("page_bytes"),
                },
                "primary_writer_handoff_projection_item_",
            )
        )
    reasons = dedupe(reasons)
    return invalid(*reasons) if reasons else {"valid": True, "blocked_reasons": []}
