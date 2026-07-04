from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.relaymem_store import (
    build_relaymem_snippet_evidence_dry_run,
    build_relaymem_store_diagnostics,
    discover_relaymem_page_candidates,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _write_target_store(root: Path) -> None:
    mem = root / "memory" / "mem"
    (root / "memory" / "sources" / "conversations").mkdir(parents=True)
    (mem / "primary" / "sessions").mkdir(parents=True)
    (mem / "secondary" / "projects").mkdir(parents=True)
    (mem / "index.md").write_text("# Index\n", encoding="utf-8")
    (mem / "log.md").write_text("# Log\n", encoding="utf-8")
    (mem / "primary" / "sessions" / "session.md").write_text(
        "# Session\nRelayMEM target primary page\n", encoding="utf-8"
    )
    (mem / "secondary" / "projects" / "project.md").write_text(
        "# Project\nRelayMEM target secondary page\n", encoding="utf-8"
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        legacy_root = Path(td)
        legacy_mem = legacy_root / "memory" / "mem"
        (legacy_mem / "projects").mkdir(parents=True)
        (legacy_mem / "concepts").mkdir(parents=True)
        (legacy_mem / "summaries").mkdir(parents=True)
        (legacy_mem / "relations").mkdir(parents=True)
        (legacy_mem / "index.md").write_text("# Index\n", encoding="utf-8")
        (legacy_mem / "log.md").write_text("# Log\n", encoding="utf-8")
        (legacy_mem / "projects" / "legacy.md").write_text(
            "# Legacy\nRelayMEM flat page\n", encoding="utf-8"
        )

        diagnostics = build_relaymem_store_diagnostics(
            root_path=str(legacy_root), store_enabled=True, retrieval_dry_run_only=True
        )
        require(diagnostics["layout_compatibility"]["flat_store_compatibility_removed"] is True, diagnostics)
        require("current_flat_present" not in diagnostics["layout_compatibility"], diagnostics)
        require("migration_required" not in diagnostics["layout_compatibility"], diagnostics)
        require(diagnostics["pages_discovered"] == 0, diagnostics)
        require(diagnostics["fallback_reason"] == "target_primary_secondary_layout_missing", diagnostics)

        candidates = discover_relaymem_page_candidates(
            root_path=str(legacy_root), query_terms=["relaymem"]
        )
        require(candidates["candidates"] == [], candidates)
        require(candidates["fallback_reason"] == "target_primary_secondary_layout_missing", candidates)

        snippets = build_relaymem_snippet_evidence_dry_run(
            root_path=str(legacy_root),
            selected_mem_candidates=[{"path": "memory/mem/projects/legacy.md", "source": "mem_page"}],
            snippet_extraction_enabled=True,
            snippet_dry_run_only=True,
        )
        blocked = snippets["evidence_envelope"]["blocked"]
        require(blocked and blocked[0]["reason"] == "unsupported_scope", snippets)
        print("ok legacy flat-only store is not selected or snippet-readable")

    with tempfile.TemporaryDirectory() as td:
        target_root = Path(td)
        _write_target_store(target_root)
        diagnostics = build_relaymem_store_diagnostics(
            root_path=str(target_root), store_enabled=True, retrieval_dry_run_only=True
        )
        require(diagnostics["layout_compatibility"]["target_primary_secondary_present"] is True, diagnostics)
        require(diagnostics["layout_compatibility"]["sources_present"] is True, diagnostics)
        require(diagnostics["pages_discovered"] == 2, diagnostics)
        require(all("memory/mem/projects" not in path for path in diagnostics["page_paths"]), diagnostics)

        candidates = discover_relaymem_page_candidates(
            root_path=str(target_root), query_terms=["relaymem"]
        )
        require({item["memory_layer"] for item in candidates["candidates"]} == {"primary", "secondary"}, candidates)
        require({item["layout_profile"] for item in candidates["candidates"]} == {"target_primary_secondary"}, candidates)
        print("ok target Primary/Secondary store remains discoverable")

    with tempfile.TemporaryDirectory() as td:
        configured_root = Path(td)
        scoped = resolve_relaymem_character_store_root(str(configured_root), "character_default")
        require(isinstance(scoped, str), scoped)
        require(str(configured_root / "characters") in scoped, scoped)
        require("character_default" not in scoped, scoped)
        require(resolve_relaymem_character_store_root(str(configured_root), "../bad") is None, "bad character id accepted")
        print("ok character-scoped root resolution remains opaque and fail-closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
