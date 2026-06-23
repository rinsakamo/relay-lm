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
    exact_fields,
    invalid,
    strings,
)
from ._relaymem_primary_page_writer_handoff import parse_m3d_handoff

M3D_RESULT_SCHEMA = "relaymem.primary_writer_handoff_preflight.v0"
M3D_PROJECTION_SCHEMA = "relaymem.primary_writer_handoff_projection.v0"
M3D_RESULT_FIELDS = {
    "schema_version", "diagnostics_only", "helper_only", "read_only",
    "runtime_private_handoffs", "enabled", "dry_run_only", "apply_enabled",
    "write_apply_supported", "apply_allowed", "writes_memory", "updates_index",
    "updates_log", "mutates_soul", "invokes_slp", "lab_api_exposed",
    "runtime_wired", "visible_response_changed", "store_root_configured",
    "page_candidate_valid", "handoff_count", "handoffs", "blocked_reasons",
    "projection",
}
M3D_PROJECTION_FIELDS = {
    "schema_version", "diagnostics_only", "content_free", "content_included",
    "store_root_path_included", "candidate_id_included", "namespace_included",
    "target_path_included", "lineage_fingerprint_included",
    "idempotency_key_included", "page_markdown_included", "page_digest_included",
    "raw_source_text_included", "raw_message_history_included",
    "raw_affect_estimates_included", "writes_memory", "updates_index",
    "updates_log", "handoff_count", "status_counts", "target_category_counts",
    "writer_apply_eligible_count", "root_present", "target_parent_present",
    "target_exists", "target_digest_matches", "idempotent_noop",
    "blocked_reasons", "handoffs",
}
M3D_PROJECTION_ITEM_FIELDS = {
    "operation_index", "source_event_kind", "memory_layer", "memory_kind",
    "promotion_policy", "safety_scope", "target_category", "preflight_status",
    "target_exists", "target_digest_matches", "idempotent_noop",
    "writer_apply_eligible", "page_bytes",
}

_PROJECTION_VARIANTS: dict[str, dict[str, object]] = {
    "ready": {
        "writer_apply_eligible_count": 1,
        "target_exists": False,
        "target_digest_matches": False,
        "idempotent_noop": False,
    },
    "already_applied": {
        "writer_apply_eligible_count": 0,
        "target_exists": True,
        "target_digest_matches": True,
        "idempotent_noop": True,
    },
}


def parse_relaymem_primary_writer_handoff(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return invalid("primary_writer_handoff_artifact_missing")
    if value.get("schema_version") != M3D_RESULT_SCHEMA:
        return invalid("primary_writer_handoff_artifact_schema_mismatch")
    reasons = exact_fields(
        value, M3D_RESULT_FIELDS, "primary_writer_handoff_artifact_fields_mismatch"
    )
    reasons.extend(
        exact(
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


def _parse_m3d_projection(
    value: object, handoff: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return invalid("primary_writer_handoff_projection_missing")
    if value.get("schema_version") != M3D_PROJECTION_SCHEMA:
        return invalid("primary_writer_handoff_projection_schema_mismatch")
    reasons = exact_fields(
        value,
        M3D_PROJECTION_FIELDS,
        "primary_writer_handoff_projection_fields_mismatch",
    )
    handoff_valid = handoff.get("valid") is True
    variant = handoff.get("preflight_status") if handoff_valid else None
    variant_values = _PROJECTION_VARIANTS.get(str(variant))
    exact_values: dict[str, object] = {
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
        "root_present": True,
        "target_parent_present": True,
    }
    if variant_values is None:
        reasons.append("primary_writer_handoff_projection_variant_invalid")
    else:
        exact_values.update(variant_values)
    reasons.extend(exact(value, exact_values, "primary_writer_handoff_projection_"))
    if contains_key(value, PROJECTION_FORBIDDEN_KEYS):
        reasons.append("primary_writer_handoff_projection_content_field_present")
    if strings(value.get("blocked_reasons")):
        reasons.append("primary_writer_handoff_projection_blocked")
    if not _strict_int(value.get("handoff_count"), 1):
        reasons.append("primary_writer_handoff_projection_handoff_count_invalid")
    expected_eligible = int(variant == "ready")
    if not _strict_int(value.get("writer_apply_eligible_count"), expected_eligible):
        reasons.append(
            "primary_writer_handoff_projection_writer_apply_eligible_count_invalid"
        )
    if not _count_map(value.get("status_counts"), {str(variant): 1}):
        reasons.append("primary_writer_handoff_projection_status_counts_invalid")

    if handoff_valid and not _count_map(
        value.get("target_category_counts"), {handoff["target_category"]: 1}
    ):
        reasons.append("primary_writer_handoff_projection_category_counts_invalid")

    items = value.get("handoffs")
    if (
        not isinstance(items, Sequence)
        or isinstance(items, (str, bytes))
        or len(items) != 1
    ):
        reasons.append("primary_writer_handoff_projection_items_invalid")
    elif not isinstance(items[0], Mapping):
        reasons.append("primary_writer_handoff_projection_item_invalid")
    else:
        reasons.extend(
            exact_fields(
                items[0],
                M3D_PROJECTION_ITEM_FIELDS,
                "primary_writer_handoff_projection_item_fields_mismatch",
            )
        )
        if not _strict_int(items[0].get("operation_index"), 0):
            reasons.append(
                "primary_writer_handoff_projection_item_operation_index_invalid"
            )
        if handoff_valid and not _strict_int(
            items[0].get("page_bytes"), int(handoff["page_bytes"])
        ):
            reasons.append("primary_writer_handoff_projection_item_page_bytes_invalid")
        if handoff_valid and variant_values is not None:
            reasons.extend(
                exact(
                    items[0],
                    {
                        "operation_index": 0,
                        "source_event_kind": handoff["source_event_kind"],
                        "memory_layer": "primary",
                        "memory_kind": handoff["memory_kind"],
                        "promotion_policy": "free_to_update",
                        "safety_scope": "ordinary_memory",
                        "target_category": handoff["target_category"],
                        "preflight_status": variant,
                        "target_exists": variant_values["target_exists"],
                        "target_digest_matches": variant_values["target_digest_matches"],
                        "idempotent_noop": variant_values["idempotent_noop"],
                        "writer_apply_eligible": variant == "ready",
                        "page_bytes": handoff["page_bytes"],
                    },
                    "primary_writer_handoff_projection_item_",
                )
            )
    reasons = dedupe(reasons)
    return invalid(*reasons) if reasons else {"valid": True, "blocked_reasons": []}


def _strict_int(value: object, expected: int) -> bool:
    return type(value) is int and value == expected


def _count_map(value: object, expected: Mapping[str, int]) -> bool:
    if not isinstance(value, Mapping) or set(value.keys()) != set(expected.keys()):
        return False
    return all(_strict_int(value.get(key), count) for key, count in expected.items())
