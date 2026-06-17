"""Managed apply result finalization helpers."""
from __future__ import annotations

from relaylm.client_history_exclusion_apply_v1_prepare import (
    PreparedClientHistoryExclusionApplyV1,
)
from relaylm.client_history_exclusion_apply_v1_render import (
    render_client_history_exclusion_apply_v1,
)
from relaylm.client_history_exclusion_apply_v1_types import (
    ClientHistoryExclusionApplyV1Result,
    build_client_history_exclusion_apply_v1_result,
)


def finalize_instruction_bearing_apply(
    prepared: PreparedClientHistoryExclusionApplyV1,
    *,
    dry_run_only: bool,
    instruction_resolution_mode: str,
) -> ClientHistoryExclusionApplyV1Result:
    """Render the detached candidate and project one typed v1 result."""

    rendered = render_client_history_exclusion_apply_v1(prepared)
    if rendered is None:
        return build_client_history_exclusion_apply_v1_result(
            status="blocked",
            dry_run_only=dry_run_only,
            managed_route=True,
            compiler_used=True,
            original_compiled_message_count=len(
                prepared.validated.compiled_messages
            ),
            instruction_resolution_mode=instruction_resolution_mode,
            instruction_candidate_count=len(prepared.validated.candidates),
            instruction_evidence_rendered_char_count=(
                prepared.evidence_rendered_char_count
            ),
            blocked_reasons=("instruction_evidence_render_failed",),
        )

    applied = not dry_run_only
    return build_client_history_exclusion_apply_v1_result(
        status="applied" if applied else "ready",
        forwarded_payload=rendered.payload,
        dry_run_only=dry_run_only,
        managed_route=True,
        compiler_used=True,
        relay_owned_prefix_message_count=1,
        original_compiled_message_count=len(
            prepared.validated.compiled_messages
        ),
        forwarded_message_count=rendered.message_count,
        excluded_client_message_count=max(
            0,
            len(prepared.validated.original_messages) - 1,
        ),
        preserved_client_message_count=1,
        instruction_resolution_mode=instruction_resolution_mode,
        instruction_candidate_count=len(prepared.validated.candidates),
        instruction_evidence_block_present=True,
        instruction_evidence_rendered_char_count=(
            prepared.evidence_rendered_char_count
        ),
        legacy_incoming_system_prompt_replaced=True,
        payload_candidate_present=True,
        payload_mutation_applied=applied,
    )
