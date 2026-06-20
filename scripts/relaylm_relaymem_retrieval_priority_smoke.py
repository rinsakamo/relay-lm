from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaymem_retrieval_priority import prioritize_relaymem_candidates


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _candidate(path: str, *, reason: str = "store_page_available") -> dict[str, object]:
    if path.startswith("memory/mem/secondary/"):
        layer = "secondary"
        profile = "target_primary_secondary"
    elif path.startswith("memory/mem/primary/"):
        layer = "primary"
        profile = "target_primary_secondary"
    elif path.startswith("memory/mem/"):
        layer = "legacy_flat"
        profile = "current_flat"
    else:
        layer = "unknown"
        profile = "unknown"
    return {
        "path": path,
        "source": "mem_page",
        "reason": reason,
        "estimated_chars": 256,
        "estimated_tokens": 64,
        "memory_layer": layer,
        "layout_profile": profile,
        "applied_to_ctx": False,
    }


def main() -> int:
    mixed = [
        _candidate("memory/mem/primary/sessions/session.md", reason="keyword_match"),
        _candidate("memory/mem/projects/legacy.md", reason="keyword_match"),
        _candidate("memory/mem/secondary/concepts/concept.md"),
        _candidate("memory/mem/secondary/summaries/summary.md"),
        _candidate("memory/mem/primary/relationships/relation.md"),
        _candidate("memory/mem/secondary/relations/relation.md"),
    ]
    prioritized = prioritize_relaymem_candidates(mixed, max_candidates=4)
    require(prioritized["schema_version"] == "relaymem.retrieval_priority.v0", prioritized)
    require(prioritized["diagnostics_only"] is True, prioritized)
    require(prioritized["read_only"] is True, prioritized)
    require(prioritized["writes_memory"] is False, prioritized)
    require(prioritized["mutates_soul"] is False, prioritized)
    require(prioritized["candidate_count"] == 6, prioritized)
    require(prioritized["selected_count"] == 4, prioritized)
    require(
        prioritized["layer_counts"]
        == {"secondary": 3, "primary": 2, "legacy_flat": 1, "unknown": 0},
        prioritized,
    )
    selected = prioritized["selected_candidates"]
    require(
        [item["memory_layer"] for item in selected]
        == ["secondary", "secondary", "secondary", "primary"],
        selected,
    )
    selected_paths = [item["path"] for item in selected]
    require(
        selected_paths
        == [
            "memory/mem/secondary/summaries/summary.md",
            "memory/mem/secondary/relations/relation.md",
            "memory/mem/secondary/concepts/concept.md",
            "memory/mem/primary/sessions/session.md",
        ],
        selected,
    )
    require(
        [item["retrieval_rank"] for item in selected] == [0, 1, 2, 3],
        selected,
    )
    print("ok secondary MEM outranks primary and legacy candidates")

    projection = prioritized["selection_projection"]
    require(projection["content_included"] is False, projection)
    require(projection["path_included"] is False, projection)
    require(projection["snippet_included"] is False, projection)
    projection_text = repr(projection)
    require("summary.md" not in projection_text, projection)
    require("session.md" not in projection_text, projection)
    require("legacy.md" not in projection_text, projection)
    require(
        [item["memory_layer"] for item in projection["selected"]]
        == ["secondary", "secondary", "secondary", "primary"],
        projection,
    )
    print("ok content-free projection omits paths and snippets")

    tie = prioritize_relaymem_candidates(
        [
            _candidate("memory/mem/secondary/projects/a.md"),
            _candidate("memory/mem/secondary/projects/b.md"),
        ]
    )
    require(
        [item["path"] for item in tie["selected_candidates"]]
        == [
            "memory/mem/secondary/projects/a.md",
            "memory/mem/secondary/projects/b.md",
        ],
        tie,
    )
    print("ok original order is stable tie-breaker")

    empty = prioritize_relaymem_candidates([], max_candidates=3)
    require(empty["candidate_count"] == 0, empty)
    require(empty["selected_candidates"] == [], empty)
    require(empty["selection_projection"]["selected"] == [], empty)
    print("ok empty candidate list remains safe")

    capped = prioritize_relaymem_candidates(mixed, max_candidates=0)
    require(capped["selected_count"] == 0, capped)
    require(capped["selected_candidates"] == [], capped)
    print("ok zero candidate cap is honored")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
