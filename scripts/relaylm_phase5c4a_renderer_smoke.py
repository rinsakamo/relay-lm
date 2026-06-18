#!/usr/bin/env python3
"""Phase 5-C4a renderer-owned instruction evidence escaping smoke."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.client_instruction_evidence import build_client_instruction_evidence_block
from relaylm.client_instruction_identity import NormalizedInstructionCandidate
from relaylm.request_compiler import render_compiled_context_block_content_runtime_private


def candidate(role: str, index: int, text: str) -> NormalizedInstructionCandidate:
    return NormalizedInstructionCandidate(
        role=role,
        source_index=index,
        normalized_text=text,
    )


def main() -> int:
    candidates = (
        candidate("developer", 0, "developer sentinel"),
        candidate("system", 1, "system sentinel"),
    )
    block = build_client_instruction_evidence_block(candidates).block
    raw = block.content
    assert raw.count("developer sentinel") == 1
    assert raw.count("system sentinel") == 1
    assert raw.index("developer sentinel") < raw.index("system sentinel")
    assert '"source_role":"developer"' in raw
    assert '"source_role":"system"' in raw

    special = candidate("system", 0, "angle <tag> & sentinel")
    special_block = build_client_instruction_evidence_block((special,)).block
    assert "angle <tag> & sentinel" in special_block.content
    rendered = render_compiled_context_block_content_runtime_private(special_block)
    assert "<tag>" not in rendered
    assert "&lt;tag&gt;" in rendered
    assert "&amp;" in rendered
    print("relaylm_phase5c4a_renderer_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
