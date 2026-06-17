#!/usr/bin/env python3
"""Phase 5-C4a typed compiler block smoke."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase5c4a_block_order import build_blocks
from relaylm.client_instruction_evidence import (
    build_client_instruction_evidence_block,
    replace_legacy_instruction_block,
)
from relaylm.client_instruction_identity import NormalizedInstructionCandidate


def main() -> int:
    source = build_blocks()
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
