"""E1-R5 Primary MEM recall bridge relevance-bound smoke."""
from __future__ import annotations

from relaylm import relaymem_primary_recall_candidate_bridge_runtime as bridge_runtime

NAMESPACE = "character_default"
OTHER_NAMESPACE = "character_other"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


class Target:
    @staticmethod
    def _primary_relative_path(value: str) -> bool:
        return value.startswith("memory/mem/primary/")


def test_full_control_index_scan() -> None:
    control = {
        "index": [
            {
                "memory_layer": "primary",
                "namespace": OTHER_NAMESPACE,
                "page_relative_path": f"memory/mem/primary/projects/old-{index}.json",
            }
            for index in range(150)
        ]
        + [
            {
                "memory_layer": "primary",
                "namespace": NAMESPACE,
                "page_relative_path": "memory/mem/primary/projects/relevant.json",
            }
        ]
    }
    candidates, reasons = bridge_runtime._discover_primary_candidates_from_control(
        target=Target,
        control=control,
        namespace=NAMESPACE,
    )
    require(len(candidates) == 1, (candidates, reasons))
    require(candidates[0]["path"] == "memory/mem/primary/projects/relevant.json", candidates)


def test_storage_metadata_excluded_from_relevance() -> None:
    candidate = {
        "summary": "User likes quiet morning writing.",
        "title": "Morning routine",
        "path": "memory/mem/primary/projects/project-related-path.json",
        "memory_kind": "recent_project_event",
    }
    require(bridge_runtime._candidate_summary_score(candidate, ["project"]) == 0, candidate)
    require(bridge_runtime._candidate_summary_score(candidate, ["morning"]) > 0, candidate)


def main() -> None:
    test_full_control_index_scan()
    test_storage_metadata_excluded_from_relevance()
    print("E1-R5 Primary MEM recall bridge relevance-bound smoke passed")


if __name__ == "__main__":
    main()
