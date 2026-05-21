from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.memory_candidate import (
    build_candidate_memory_block,
    load_seed_memory_candidates,
    select_memory_candidates,
)
from relaylm.memory_seed import load_memory_seed_file


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        seed_path = Path(tmpdir) / "state_memories.yaml"
        seed_path.write_text(
            """
memories:
  - memory_id: default-active
    character_id: default
    content: Active memory.
    importance: 5
    state: active
  - memory_id: default-promoted
    character_id: default
    content: Promoted memory.
    importance: 1
    state: promoted
  - memory_id: default-demoted
    character_id: default
    content: Demoted memory.
    importance: 10
    state: demoted
  - memory_id: default-disabled
    character_id: default
    content: Disabled memory.
    importance: 100
    state: disabled
  - memory_id: shared-active
    content: Shared memory.
    importance: 3
""".strip()
            + "\n",
            encoding="utf-8",
        )

        seed_file = load_memory_seed_file(seed_path)
        states = {memory.memory_id: memory.state for memory in seed_file.memories}
        require(states["default-active"] == "active", states)
        require(states["default-promoted"] == "promoted", states)
        require(states["default-demoted"] == "demoted", states)
        require(states["default-disabled"] == "disabled", states)
        require(states["shared-active"] == "active", states)
        print("ok load memory seed states")

        candidates = load_seed_memory_candidates(seed_path)
        candidate_states = {candidate.memory_id: candidate.state for candidate in candidates}
        require(candidate_states == states, candidate_states)
        print("ok seed states to candidates")

        selected = select_memory_candidates(candidates, character_id="default", limit=4)
        selected_ids = [candidate.memory_id for candidate in selected]
        require(selected_ids == [
            "default-promoted",
            "default-active",
            "shared-active",
            "default-demoted",
        ], selected_ids)
        require("default-disabled" not in selected_ids, selected_ids)
        print("ok select memory candidates by state")

        block = build_candidate_memory_block(selected)
        require(block is not None, "expected memory block")
        require("default-promoted" in block.content, block.content)
        require("state=promoted" in block.content, block.content)
        require("default-demoted" in block.content, block.content)
        require("state=demoted" in block.content, block.content)
        require("default-disabled" not in block.content, block.content)
        print("ok memory state block content")

        bad_seed_path = Path(tmpdir) / "bad_state.yaml"
        bad_seed_path.write_text(
            """
memories:
  - memory_id: bad-state
    content: Bad state.
    state: pinned
""".strip()
            + "\n",
            encoding="utf-8",
        )
        try:
            load_memory_seed_file(bad_seed_path)
        except ValueError as exc:
            require("state must be one of" in str(exc), str(exc))
            print("ok invalid memory seed state error")
        else:
            raise AssertionError("expected invalid state error")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
