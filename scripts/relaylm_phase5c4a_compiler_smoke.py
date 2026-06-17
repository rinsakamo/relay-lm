#!/usr/bin/env python3
"""Phase 5-C4a typed compiler block smoke."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.client_instruction_evidence import (
    build_client_instruction_evidence_block,
    replace_legacy_instruction_block,
)
from relaylm.client_instruction_identity import NormalizedInstructionCandidate
from relaylm.compiler import BlockType, ContextBlock, StabilityClass


def block(block_id: str, block_type: BlockType, stability: StabilityClass) -> ContextBlock:
    return ContextBlock(
        block_id=block_id,
        block_type=block_type,
        stability_class=stability,
        source="smoke",
        content=f"{block_id} sentinel",
        token_budget_hint=100,
        include_in_prefix_cache_target=stability is StabilityClass.STABLE_PREFIX,
    )


def main() -> int:
    source = [
        block("common_runtime_policy", BlockType.COMMON_RUNTIME_POLICY, StabilityClass.STABLE_PREFIX),
        block("soul", BlockType.SOUL, StabilityClass.STABLE_PREFIX),
        block("incoming_system_prompt", BlockType.INCOMING_SYSTEM_PROMPT, StabilityClass.DYNAMIC_SUFFIX),
    ]
    evidence = build_client_instruction_evidence_block(
        [
            NormalizedInstructionCandidate(
                role="system",
                source_index=0,
                normalized_text="normalized sentinel",
            )
        ]
    )
    replaced, reasons = replace_legacy_instruction_block(source, evidence.block)
    assert replaced is not None and reasons == []
    assert [item.block_id for item in replaced] == [
        "common_runtime_policy",
        "soul",
        "client_instruction_evidence",
    ]
    assert source[-1].block_id == "incoming_system_prompt"
    print("relaylm_phase5c4a_compiler_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
