"""E1-R5 Primary MEM recall bridge relevance-bound smoke."""
from __future__ import annotations

from relaylm import relaymem_primary_recall as primary_recall

NAMESPACE = "character_default"
OTHER_NAMESPACE = "character_other"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def test_full_control_index_scan() -> None:
    control = {
        "index": [
            {
                "memory_layer": "primary",
                "namespace": OTHER_NAMESPACE,
                "page_relative_path": f"memory/mem/primary/projects/old-{index}.md",
            }
            for index in range(150)
        ]
        + [
            {
                "memory_layer": "primary",
                "namespace": NAMESPACE,
                "page_relative_path": "memory/mem/primary/projects/relevant.md",
            }
        ]
    }
    candidates, reasons = primary_recall._discover_scoped_primary_candidates_from_control(
        control=control,
        namespace=NAMESPACE,
    )
    require(len(candidates) == 1, (candidates, reasons))
    require(candidates[0]["path"] == "memory/mem/primary/projects/relevant.md", candidates)


def test_storage_metadata_excluded_from_relevance() -> None:
    candidate = {
        "summary": "User likes quiet morning writing.",
        "title": "Morning routine",
        "path": "memory/mem/primary/projects/project-related-path.json",
        "memory_kind": "recent_project_event",
    }
    require(primary_recall._candidate_summary_score(candidate, ["project"]) == 0, candidate)
    require(primary_recall._candidate_summary_score(candidate, ["morning"]) > 0, candidate)


def test_weak_cjk_gram_overlap_is_not_relevant() -> None:
    candidate = {
        "summary": "これは静かな朝の記憶です。",
        "title": "朝のこと",
        "path": "memory/mem/primary/projects/unrelated.json",
        "memory_kind": "recent_project_event",
    }
    require(
        primary_recall._candidate_summary_score(candidate, ["明日の予定は何ですか"]) == 0,
        candidate,
    )
    require(primary_recall._candidate_summary_score(candidate, ["静かな朝"]) > 0, candidate)


def main() -> None:
    test_full_control_index_scan()
    test_storage_metadata_excluded_from_relevance()
    test_weak_cjk_gram_overlap_is_not_relevant()
    print("E1-R5 Primary MEM recall bridge relevance-bound smoke passed")


if __name__ == "__main__":
    main()
