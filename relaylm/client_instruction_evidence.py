"""Typed pre-render client instruction evidence for Phase 5-C4a."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as escape_html
import json

from relaylm.client_instruction_identity import NormalizedInstructionCandidate
from relaylm.compiler import BlockType, ContextBlock, StabilityClass


CLIENT_INSTRUCTION_EVIDENCE_MAX_RENDERED_CHARS = 4096


@dataclass(frozen=True)
class ClientInstructionEvidenceRenderResult:
    block: ContextBlock
    rendered_char_count: int


def build_client_instruction_evidence_block(
    candidates: Sequence[NormalizedInstructionCandidate],
) -> ClientInstructionEvidenceRenderResult:
    """Render normalized candidates once, in source order, under a fixed bound."""

    evidence = {
        "authority": "below_relaylm_runtime_safety_and_approved_persona",
        "candidates": [
            {
                "normalized_text": candidate.normalized_text,
                "source_role": candidate.role,
            }
            for candidate in candidates
        ],
        "evidence_kind": "low_trust_current_request_instruction_evidence",
    }
    raw_content = json.dumps(
        evidence,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    escaped_content = escape_html(raw_content, quote=False)
    rendered_char_count = len(escaped_content)
    if rendered_char_count > CLIENT_INSTRUCTION_EVIDENCE_MAX_RENDERED_CHARS:
        raise ValueError("instruction_evidence_oversize")

    block = ContextBlock(
        block_id=BlockType.CLIENT_INSTRUCTION_EVIDENCE.value,
        block_type=BlockType.CLIENT_INSTRUCTION_EVIDENCE,
        stability_class=StabilityClass.DYNAMIC_SUFFIX,
        source="request_local/client_instruction_identity",
        content=escaped_content,
        token_budget_hint=1024,
        include_in_prefix_cache_target=False,
    )
    return ClientInstructionEvidenceRenderResult(
        block=block,
        rendered_char_count=rendered_char_count,
    )


def replace_legacy_instruction_block(
    blocks: Sequence[ContextBlock],
    evidence_block: ContextBlock,
) -> tuple[list[ContextBlock] | None, list[str]]:
    """Replace the one typed legacy block without inspecting rendered text."""

    legacy_indices = [
        index
        for index, block in enumerate(blocks)
        if block.block_type == BlockType.INCOMING_SYSTEM_PROMPT
    ]
    evidence_indices = [
        index
        for index, block in enumerate(blocks)
        if block.block_type == BlockType.CLIENT_INSTRUCTION_EVIDENCE
    ]
    reasons: list[str] = []
    if evidence_indices:
        reasons.append("instruction_evidence_block_already_present")
    if not legacy_indices:
        reasons.append("legacy_incoming_system_prompt_missing")
    elif len(legacy_indices) > 1:
        reasons.append("legacy_incoming_system_prompt_multiple")
    if reasons:
        return None, reasons

    replaced = list(blocks)
    replaced[legacy_indices[0]] = evidence_block
    return replaced, []
