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
from relaylm.compiler import ContextBlock


@dataclass(frozen=True, repr=False)
class PreparedClientHistoryExclusionApplyV1:
    validated: ValidatedClientHistoryExclusionApplyV1Inputs
    replaced_blocks: tuple[ContextBlock, ...]
    evidence_rendered_char_count: int


def prepare_client_history_exclusion_apply_v1(
    original_payload: Mapping[str, Any] | None,
    compiled_payload: Mapping[str, Any] | None,
    compiled_context_blocks: Sequence[ContextBlock] | None,
    preflight_result: ClientHistoryExclusionPreflightResult | None,
    identity_result: ClientInstructionIdentityResult | None,
) -> tuple[PreparedClientHistoryExclusionApplyV1 | None, tuple[str, ...], int]:
    """Validate typed prerequisites and replace the one legacy compiler block."""

    validated, reasons = validate_client_history_exclusion_apply_v1_inputs(
        original_payload,
        compiled_payload,
        compiled_context_blocks,
        preflight_result,
        identity_result,
    )
    if validated is None:
        return None, reasons, 0

    try:
        evidence = build_client_instruction_evidence_block(validated.candidates)
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
            0,
        )
    except Exception:
        return None, ("instruction_evidence_render_failed",), 0

    if replaced_blocks is None or replacement_reasons:
        return None, tuple(replacement_reasons), evidence.rendered_char_count
    return (
        PreparedClientHistoryExclusionApplyV1(
            validated=validated,
            replaced_blocks=tuple(replaced_blocks),
            evidence_rendered_char_count=evidence.rendered_char_count,
        ),
        (),
        evidence.rendered_char_count,
    )
