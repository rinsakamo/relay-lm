from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.memory_candidate import (
    MemoryCandidate,
    assemble_candidate_memory_block,
    build_candidate_memory_block,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    candidates = [
        MemoryCandidate(memory_id="keep-promoted", content="short promoted", state="promoted", importance=1),
        MemoryCandidate(memory_id="drop-long", content="x" * 200, importance=10),
        MemoryCandidate(memory_id="keep-active", content="short active", importance=3),
    ]

    full_assembly = assemble_candidate_memory_block(candidates, character_budget=None)
    require(full_assembly.block is not None, full_assembly)
    require(full_assembly.included_memory_ids == ["keep-promoted", "drop-long", "keep-active"], full_assembly)
    require(full_assembly.dropped_memory_ids == [], full_assembly)
    require(full_assembly.character_budget is None, full_assembly)
    print("ok memory budget unlimited assembly")

    budgeted = assemble_candidate_memory_block(candidates, character_budget=180)
    require(budgeted.block is not None, budgeted)
    require(budgeted.included_memory_ids == ["keep-promoted", "keep-active"], budgeted)
    require(budgeted.dropped_memory_ids == ["drop-long"], budgeted)
    require(budgeted.character_budget == 180, budgeted)
    require(budgeted.rendered_characters <= 180, budgeted)
    require("keep-promoted" in budgeted.block.content, budgeted.block.content)
    require("keep-active" in budgeted.block.content, budgeted.block.content)
    require("drop-long" not in budgeted.block.content, budgeted.block.content)
    print("ok memory budget drops overflow")

    tiny = assemble_candidate_memory_block(candidates, character_budget=1)
    require(tiny.block is None, tiny)
    require(tiny.included_memory_ids == [], tiny)
    require(tiny.dropped_memory_ids == ["keep-promoted", "drop-long", "keep-active"], tiny)
    require(tiny.rendered_characters == 0, tiny)
    print("ok memory budget drops all")

    block = build_candidate_memory_block(candidates, character_budget=180)
    require(block is not None, block)
    require("drop-long" not in block.content, block.content)
    print("ok memory budget build block compatibility")

    log_payload = budgeted.to_log_dict()
    require(log_payload["included_memory_ids"] == ["keep-promoted", "keep-active"], log_payload)
    require(log_payload["dropped_memory_ids"] == ["drop-long"], log_payload)
    print("ok memory budget log payload")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
