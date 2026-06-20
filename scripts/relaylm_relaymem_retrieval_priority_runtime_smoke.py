from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact
from relaylm.relaymem_store import build_relaymem_store_diagnostics


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _scene_policy() -> dict[str, Any]:
    return {
        "scene_state": {
            "scene_type": "design_talk",
            "confidence": 0.96,
            "stability": 0.92,
        },
        "scene_policy": {"relaymem_retrieval_scope": "project_context"},
        "persistence_block": False,
        "persistence_block_reasons": [],
    }


def _write_page(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _assert_priority_projection_is_content_free(projection: dict[str, Any]) -> None:
    require(
        projection["schema_version"] == "relaymem.retrieval_priority_runtime.v0",
        projection,
    )
    require(projection["diagnostics_only"] is True, projection)
    require(projection["read_only"] is True, projection)
    require(projection["runtime_wiring"] == "dry_run_only", projection)
    require(projection["content_included"] is False, projection)
    require(projection["path_included"] is False, projection)
    require(projection["snippet_included"] is False, projection)
    require(projection["applied_to_ctx"] is False, projection)
    require(projection["payload_mutation_allowed"] is False, projection)
    require(projection["writes_memory"] is False, projection)
    require(projection["mutates_soul"] is False, projection)
    projection_text = repr(projection)
    for forbidden in (
        "legacy_project.md",
        "legacy_summary.md",
        "session.md",
        "scene.md",
        "summary.md",
        "stable continuity memory body",
        "recent session memory body",
    ):
        require(forbidden not in projection_text, projection)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_page(root, "memory/mem/index.md", "# MEM index\n")
        _write_page(
            root,
            "memory/mem/projects/legacy_project.md",
            "legacy project memory body\n",
        )
        _write_page(
            root,
            "memory/mem/summaries/legacy_summary.md",
            "legacy summary memory body\n",
        )
        _write_page(
            root,
            "memory/mem/primary/sessions/session.md",
            "recent session memory body\n",
        )
        _write_page(
            root,
            "memory/mem/primary/scenes/scene.md",
            "recent scene memory body\n",
        )
        _write_page(
            root,
            "memory/mem/secondary/summaries/summary.md",
            "stable continuity memory body\n",
        )
        _write_page(
            root,
            "memory/mem/secondary/projects/project.md",
            "secondary project memory body\n",
        )

        store = build_relaymem_store_diagnostics(
            root_path=str(root),
            store_enabled=True,
            retrieval_dry_run_only=True,
        )
        require(store["fallback_reason"] == "memory_store_read_only_dry_run", store)

        artifact = build_relaymem_retrieval_dry_run_artifact(
            relayscn_scene_policy_artifact=_scene_policy(),
            relayref_artifact=None,
            messages=[{"role": "user", "content": "RelayMEM priority project"}],
            token_budget=2048,
            store_diagnostics=store,
            max_candidates=3,
            ctx_block_apply_enabled=False,
            snippet_extraction_enabled=False,
        )
        require(artifact["artifact_version"] == "relaymem_retrieval.v0", artifact)
        require(artifact["diagnostics_only"] is True, artifact)
        require(artifact["apply_allowed"] is False, artifact)
        require(artifact["ctx_block"] is None, artifact)
        require(artifact["apply_decision"] == "dry_run_only", artifact)
        require(artifact["snippet_apply_decision"] == "blocked_no_snippet", artifact)
        require(artifact["ctx_injection_plan"]["applied"] is False, artifact)
        require(
            artifact["ctx_injection_plan"]["payload_mutation_allowed"] is False,
            artifact,
        )
        require(
            "runtime_ctx_injection_not_implemented"
            in artifact["ctx_injection_plan"]["blocked_reasons"],
            artifact,
        )

        selected_paths = [item["path"] for item in artifact["selected_mem_candidates"]]
        require(
            selected_paths
            == [
                "memory/mem/secondary/summaries/summary.md",
                "memory/mem/primary/scenes/scene.md",
                "memory/mem/primary/sessions/session.md",
            ],
            selected_paths,
        )
        require(
            [item["retrieval_rank"] for item in artifact["selected_mem_candidates"]]
            == [0, 1, 2],
            artifact["selected_mem_candidates"],
        )
        require(
            [
                item["retrieval_priority_tier"]
                for item in artifact["selected_mem_candidates"]
            ]
            == ["secondary_summary", "primary_scene", "primary_session"],
            artifact["selected_mem_candidates"],
        )
        require(artifact["used_tokens"] > 0, artifact)
        print("ok runtime dry-run retrieval uses MEM-M2 priority order")

        projection = artifact["retrieval_priority"]
        _assert_priority_projection_is_content_free(projection)
        require(projection["candidate_count"] == 3, projection)
        require(projection["selected_count"] == 3, projection)
        require(
            [
                item["priority_tier"]
                for item in projection["selection_projection"]["selected"]
            ]
            == ["secondary_summary", "primary_scene", "primary_session"],
            projection,
        )
        print("ok runtime priority projection is content-free")

        zero = build_relaymem_retrieval_dry_run_artifact(
            relayscn_scene_policy_artifact=_scene_policy(),
            relayref_artifact=None,
            messages=[{"role": "user", "content": "RelayMEM priority project"}],
            store_diagnostics=store,
            max_candidates=0,
        )
        require(zero["selected_mem_candidates"] == [], zero)
        require(zero["retrieval_priority"]["selected_count"] == 0, zero)
        require(zero["ctx_block_candidate"]["entries"] == [], zero)
        print("ok zero candidate cap remains bounded and empty")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
