from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.memory_candidate import MemoryCandidate, filter_candidates_for_character, select_memory_candidates


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    candidates = [
        MemoryCandidate(memory_id="shared-style", character_id=None, content="Use short replies.", importance=2, recency=10),
        MemoryCandidate(memory_id="default-project", character_id="default", content="RelayLM project.", importance=5, recency=1),
        MemoryCandidate(memory_id="default-promoted", character_id="default", content="Pinned memory.", importance=1, recency=0, state="promoted"),
        MemoryCandidate(memory_id="default-demoted", character_id="default", content="Low priority.", importance=9, recency=99, state="demoted"),
        MemoryCandidate(memory_id="default-disabled", character_id="default", content="Disabled.", importance=10, recency=100, state="disabled"),
        MemoryCandidate(memory_id="other-only", character_id="other", content="Other character.", importance=10, recency=100),
    ]

    default_candidates = filter_candidates_for_character(candidates, character_id="default")
    require([candidate.memory_id for candidate in default_candidates] == [
        "shared-style",
        "default-project",
        "default-promoted",
        "default-demoted",
    ], default_candidates)
    print("ok filter candidates")

    selected = select_memory_candidates(candidates, character_id="default", limit=3)
    require([candidate.memory_id for candidate in selected] == [
        "default-promoted",
        "default-project",
        "shared-style",
    ], selected)
    print("ok select memory candidates")

    limited = select_memory_candidates(candidates, character_id="default", limit=1)
    require([candidate.memory_id for candidate in limited] == ["default-promoted"], limited)
    print("ok selection limit")

    none_selected = select_memory_candidates(candidates, character_id="default", limit=0)
    require(none_selected == [], none_selected)
    print("ok zero selection limit")

    other_selected = select_memory_candidates(candidates, character_id="other", limit=3)
    require([candidate.memory_id for candidate in other_selected] == [
        "other-only",
        "shared-style",
    ], other_selected)
    print("ok character specific selection")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
