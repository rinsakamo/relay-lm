"""Request-local preparation for the Phase 5-C4a apply contract."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from relaylm.client_history_exclusion_apply_v1_types import ALLOWED_BLOCKED_REASONS
from relaylm.client_history_exclusion_apply_v1_validation import (
    ValidatedClientHistoryExclusionApplyV1Inputs,
    validate_client_history_exclusion_apply_v1_inputs,
)
from relaylm.client_history_exclusion_preflight import (
    ClientHistoryExclusionPreflightResult,
)
from relaylm.client_instruction_evidence import (
    build_client_instruction_evidence_block,
    replace_legacy_instruction_block,
)
from relaylm.client_instruction_identity import ClientInstructionIdentityResult
from relaylm.client_instruction_source import (
    ClientInstructionEvidenceSelection,
    select_client_instruction_evidence,
    selected_candidates,
)
from relaylm.compiler import ContextBlock
from relaylm.request_compiler import (
    render_compiled_context_block_content_runtime_private,
)


@dataclass(frozen=True, repr=False)
class PreparedClientHistoryExclusionApplyV1:
    validated: ValidatedClientHistoryExclusionApplyV1Inputs
    selection: ClientInstructionEvidenceSelection
    replaced_blocks: tuple[ContextBlock, ...]
    evidence_rendered_char_count: int


def prepare_client_history_exclusion_apply_v1(
    original_payload: Mapping[str, Any] | None,
    compiled_payload: Mapping[str, Any] | None,
    compiled_context_blocks: Sequence[ContextBlock] | None,
    preflight_result: ClientHistoryExclusionPreflightResult | None,
    identity_result: ClientInstructionIdentityResult | None,
) -> tuple[
    PreparedClientHistoryExclusionApplyV1 | None,
    tuple[str, ...],
    ClientInstructionEvidenceSelection | None,
    int,
]:
    """Validate typed prerequisites and replace the one legacy compiler block."""

    validated, reasons = validate_client_history_exclusion_apply_v1_inputs(
        original_payload,
        compiled_payload,
        compiled_context_blocks,
        preflight_result,
        identity_result,
    )
    if validated is None:
        return None, reasons, None, 0

    selection = select_client_instruction_evidence(
        original_payload,
        identity_result,
    )
    if selection.ready is not True:
        return None, selection.blocked_reasons, selection, 0

    try:
        chosen = selected_candidates(validated.identity_result, selection)
        evidence = build_client_instruction_evidence_block(chosen)
        rendered_content = render_compiled_context_block_content_runtime_private(
            evidence.block
        )
        replaced_blocks, replacement_reasons = replace_legacy_instruction_block(
            validated.compiled_context_blocks,
            evidence.block,
        )
    except ValueError as exc:
        reason = str(exc)
        return (
            None,
            (
                reason
                if reason in ALLOWED_BLOCKED_REASONS
                else "instruction_evidence_render_failed",
            ),
            selection,
            0,
        )
    except Exception:
        return None, ("instruction_evidence_render_failed",), selection, 0

    rendered_char_count = len(rendered_content)
    if replaced_blocks is None or replacement_reasons:
        return (
            None,
            tuple(replacement_reasons),
            selection,
            rendered_char_count,
        )
    return (
        PreparedClientHistoryExclusionApplyV1(
            validated=validated,
            selection=selection,
            replaced_blocks=tuple(replaced_blocks),
            evidence_rendered_char_count=rendered_char_count,
        ),
        (),
        selection,
        rendered_char_count,
    )
