from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.memory_candidate import MemoryCandidate, select_memory_candidates, summarize_memory_selection


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    candidates = [
        MemoryCandidate(memory_id="shared-active", content="Shared.", importance=2),
        MemoryCandidate(memory_id="default-promoted", character_id="default", content="Promoted.", importance=1, state="promoted"),
        MemoryCandidate(memory_id="default-active", character_id="default", content="Active.", importance=5),
        MemoryCandidate(memory_id="default-demoted", character_id="default", content="Demoted.", importance=10, state="demoted"),
        MemoryCandidate(memory_id="default-disabled", character_id="default", content="Disabled.", importance=100, state="disabled"),
        MemoryCandidate(memory_id="other-active", character_id="other", content="Other.", importance=100),
    ]

    selected = select_memory_candidates(candidates, character_id="default", limit=3)
    summary = summarize_memory_selection(
        candidates,
        character_id="default",
        limit=3,
        selected=selected,
    )

    require(summary.total_candidates == 6, summary)
    require(summary.eligible_count == 4, summary)
    require(summary.selected_count == 3, summary)
    require(summary.limit == 3, summary)
    require(summary.character_id == "default", summary)
    require(summary.selected_memory_ids == [
        "default-promoted",
        "default-active",
        "shared-active",
    ], summary)
    print("ok memory selection summary selected ids")

    require(summary.excluded_disabled_ids == ["default-disabled"], summary)
    require(summary.excluded_character_ids == ["other-active"], summary)
    print("ok memory selection summary excluded ids")

    require(summary.state_counts == {
        "active": 3,
        "promoted": 1,
        "demoted": 1,
        "disabled": 1,
    }, summary.state_counts)
    print("ok memory selection summary state counts")

    log_payload = summary.to_log_dict()
    require(log_payload["selected_memory_ids"] == summary.selected_memory_ids, log_payload)
    require(log_payload["state_counts"] == summary.state_counts, log_payload)
    print("ok memory selection summary log payload")

    zero_summary = summarize_memory_selection(
        candidates,
        character_id="default",
        limit=0,
    )
    require(zero_summary.selected_count == 0, zero_summary)
    require(zero_summary.selected_memory_ids == [], zero_summary)
    require(zero_summary.eligible_count == 4, zero_summary)
    print("ok memory selection summary zero limit")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
