"""Managed apply content-free projection helpers."""
from __future__ import annotations

from relaylm.client_history_exclusion_apply_v1_types import (
    ClientHistoryExclusionApplyV1Result,
    SCHEMA_VERSION,
    non_negative_int,
    safe_blocked_reasons,
    safe_instruction_resolution_mode,
    safe_instruction_source_mode,
    safe_status,
)
from relaylm.managed_apply_audit import install_managed_apply_audit_contract
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result


install_managed_apply_audit_contract()


def build_instruction_bearing_apply_node_result(
    result: ClientHistoryExclusionApplyV1Result,
) -> PipelineNodeResult:
    """Project a v1 result without exposing instruction or payload content."""

    projected_status = safe_status(result.status)
    if projected_status == "skipped":
        status = "skipped"
        decision = "pass_through_route_exempt"
    elif projected_status == "blocked":
        status = "blocked"
        decision = "client_history_exclusion_instruction_apply_blocked"
    elif projected_status == "applied":
        status = "applied"
        decision = "client_history_exclusion_instruction_applied"
    else:
        status = "diagnostic_only"
        decision = "client_history_exclusion_instruction_apply_ready"

    diagnostics = {
        "schema_version": SCHEMA_VERSION,
        "enabled": True,
        "status": projected_status,
        "dry_run_only": result.dry_run_only is True,
        "managed_route": result.managed_route is True,
        "compiler_used": result.compiler_used is True,
        "relay_owned_prefix_message_count": non_negative_int(
            result.relay_owned_prefix_message_count
        ),
        "original_compiled_message_count": non_negative_int(
            result.original_compiled_message_count
        ),
        "forwarded_message_count": non_negative_int(
            result.forwarded_message_count
        ),
        "excluded_client_message_count": non_negative_int(
            result.excluded_client_message_count
        ),
        "preserved_client_message_count": non_negative_int(
            result.preserved_client_message_count
        ),
        "instruction_resolution_mode": safe_instruction_resolution_mode(
            result.instruction_resolution_mode
        ),
        "instruction_source_mode": safe_instruction_source_mode(
            result.instruction_source_mode
        ),
        "instruction_source_provenance_present": (
            result.instruction_source_provenance_present is True
        ),
        "instruction_candidate_count": non_negative_int(
            result.instruction_candidate_count
        ),
        "selected_instruction_candidate_count": non_negative_int(
            result.selected_instruction_candidate_count
        ),
        "excluded_instruction_candidate_count": non_negative_int(
            result.excluded_instruction_candidate_count
        ),
        "instruction_evidence_block_present": (
            result.instruction_evidence_block_present is True
        ),
        "instruction_evidence_rendered_char_count": non_negative_int(
            result.instruction_evidence_rendered_char_count
        ),
        "legacy_incoming_system_prompt_replaced": (
            result.legacy_incoming_system_prompt_replaced is True
        ),
        "raw_instruction_message_forwarded": False,
        "relaylm_control_forwarded": False,
        "cache_entry_content_injected": False,
        "cache_projection_applied": False,
        "payload_candidate_present": result.forwarded_payload is not None,
        "payload_mutation_applied": (
            result.status == "applied"
            and result.payload_mutation_applied is True
            and result.forwarded_payload is not None
        ),
        "runtime_private_source": True,
        "content_bearing_candidate_persisted": False,
    }
    return build_pipeline_node_result(
        node_name="client_history_exclusion_apply",
        status=status,  # type: ignore[arg-type]
        decision=decision,
        blocked_reasons=safe_blocked_reasons(result.blocked_reasons),
        diagnostics=diagnostics,
    )
