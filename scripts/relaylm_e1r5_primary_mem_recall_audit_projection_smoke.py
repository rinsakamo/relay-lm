"""E1-R5 Primary MEM recall audit projection field preservation smoke."""
from __future__ import annotations

import relaylm  # noqa: F401 - installs audit projection contracts
from relaylm.audit_projection import project_audit_metadata


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> None:
    projection = {
        "schema_version": "relaymem.primary_recall_projection.v0",
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "memory_text_included": False,
        "title_or_summary_included": False,
        "character_value_included": False,
        "namespace_value_included": False,
        "runtime_identifier_values_included": False,
        "path_values_included": False,
        "digest_values_included": False,
        "lineage_values_included": False,
        "idempotency_values_included": False,
        "backend_prompt_included": False,
        "retrieval_attempted": True,
        "scene_type": "design_talk",
        "retrieval_scope": "long_term_memory",
        "fallback_reason": "none",
        "persistence_block": False,
        "ctx_block_present": False,
        "primary_candidate_discovery_attempted": True,
        "primary_candidate_count": 2,
        "grounding_enabled": False,
        "grounded_item_count": 0,
        "unsupported_detail_policy": "suppress",
        "evidence_content_included": False,
        "runtime_private_evidence_omitted": True,
        "selected_count": 0,
        "selected_layer_counts": {"primary": 0},
        "character_scope_resolved": True,
        "namespace_scope_valid": True,
        "scope_matched": False,
        "injection_candidate_present": False,
        "estimated_chars": 0,
        "estimated_tokens": 0,
        "memory_used": False,
        "blocked_reason_ids": ["primary_recall_no_scoped_match"],
    }
    result = project_audit_metadata({"relaymem_primary_recall_projection": projection})
    projected = result.metadata["relaymem_primary_recall_projection"]
    require(result.dropped_field_count == 0, result)
    require(projected["primary_candidate_discovery_attempted"] is True, projected)
    require(projected["primary_candidate_count"] == 2, projected)
    require(projected["grounding_enabled"] is False, projected)
    require(projected["grounded_item_count"] == 0, projected)
    require(projected["unsupported_detail_policy"] == "suppress", projected)
    require(projected["evidence_content_included"] is False, projected)
    require(projected["runtime_private_evidence_omitted"] is True, projected)
    print("E1-R5 Primary MEM recall audit projection smoke passed")


if __name__ == "__main__":
    main()
