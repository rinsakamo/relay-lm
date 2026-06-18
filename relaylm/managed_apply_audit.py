"""Exact audit registration for managed apply v1."""
from __future__ import annotations

from typing import Any


def install_managed_apply_audit_contract() -> None:
    import relaylm.audit_projection as ap

    if getattr(ap, "_MANAGED_APPLY_V1_AUDIT_INSTALLED", False):
        return
    current = ap.PIPELINE_NODE_PROJECTORS["client_history_exclusion_apply"]
    decisions = set(current.decisions or ())
    decisions.update(
        {
            "client_history_exclusion_instruction_apply_blocked",
            "client_history_exclusion_instruction_applied",
            "client_history_exclusion_instruction_apply_ready",
        }
    )
    fields: dict[str, Any] = {
        "schema_version": ap._enum(
            "client_history_exclusion_apply.v0",
            "client_history_exclusion_apply.v1",
        ),
        "enabled": ap._bool,
        "status": ap._enum("ready", "applied", "blocked", "skipped"),
        "dry_run_only": ap._bool,
        "managed_route": ap._bool,
        "compiler_used": ap._bool,
        "relay_owned_prefix_message_count": ap._non_negative_int,
        "original_compiled_message_count": ap._non_negative_int,
        "forwarded_message_count": ap._non_negative_int,
        "excluded_client_message_count": ap._non_negative_int,
        "preserved_client_message_count": ap._non_negative_int,
        "instruction_resolution_mode": ap._enum(
            "none", "cache_hit", "cache_miss_first_pass", "blocked", "not_applicable"
        ),
        "instruction_source_mode": ap._optional(
            ap._enum("explicit", "not_applicable")
        ),
        "instruction_source_provenance_present": ap._optional(ap._bool),
        "instruction_candidate_count": ap._optional(ap._non_negative_int),
        "selected_instruction_candidate_count": ap._optional(ap._non_negative_int),
        "excluded_instruction_candidate_count": ap._optional(ap._non_negative_int),
        "instruction_evidence_block_present": ap._optional(ap._bool),
        "instruction_evidence_rendered_char_count": ap._optional(ap._non_negative_int),
        "legacy_incoming_system_prompt_replaced": ap._optional(ap._bool),
        "raw_instruction_message_forwarded": ap._optional(ap._bool),
        "relaylm_control_forwarded": ap._optional(ap._bool),
        "cache_entry_content_injected": ap._optional(ap._bool),
        "cache_projection_applied": ap._optional(ap._bool),
        "payload_candidate_present": ap._bool,
        "payload_mutation_applied": ap._bool,
        "runtime_private_source": ap._bool,
        "content_bearing_candidate_persisted": ap._bool,
    }
    ap.PIPELINE_NODE_PROJECTORS["client_history_exclusion_apply"] = ap.NodeProjector(
        decisions=frozenset(decisions),
        diagnostics=ap._mapping(fields),
        artifact_names=current.artifact_names,
    )
    ap._MANAGED_APPLY_V1_AUDIT_INSTALLED = True
