#!/usr/bin/env python3
"""Phase 5-C4a typed evidence contract smoke."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.client_instruction_evidence import (
    build_client_instruction_evidence_block,
)
from relaylm.client_instruction_identity import NormalizedInstructionCandidate


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def candidate(role: str, index: int, text: str) -> NormalizedInstructionCandidate:
    return NormalizedInstructionCandidate(
        role=role,
        source_index=index,
        normalized_text=text,
    )


def main() -> int:
    cases = [
        [candidate("system", 0, "system-only sentinel")],
        [candidate("developer", 0, "developer-only sentinel")],
        [
            candidate("developer", 0, "mixed developer sentinel"),
            candidate("system", 1, "mixed system sentinel"),
        ],
    ]
    for candidates in cases:
        rendered = build_client_instruction_evidence_block(candidates)
        content = rendered.block.content
        for item in candidates:
            require(content.count(item.normalized_text) == 1, content)
            require(f'"source_role":"{item.role}"' in content, content)
        require(
            content.index(candidates[0].normalized_text)
            <= content.index(candidates[-1].normalized_text),
            content,
        )

    special = "ampersand & sentinel"
    special_content = build_client_instruction_evidence_block(
        [candidate("system", 0, special)]
    ).block.content
    require(special not in special_content, special_content)
    require("&amp;" in special_content, special_content)
    print("ok explicit roles, source order, one-copy evidence, and delimiter escaping")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
