#!/usr/bin/env python3
"""Minimal CW-A4 integration smoke for the Twin Review Import Bridge.

Verifies that an approved general fact_candidate, once written by the
bridge into ``.relaylm/sources/imports/twin-extraction/``, is readable by
CW-A4 (`relaylm.character_workspace.plan_character_workspace_slp_candidates`)
as user-assertion source evidence and produces a dry-run memory candidate.
This smoke only exercises CW-A4 in `dry_run` mode; it never calls
`write_candidates=True` and never touches MEM/SOUL/REL directly. The
bridge itself still does not import `relaylm`; only this integration smoke
does, to observe the CW-A4 side of the boundary.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import relaylm_twin_review_import_bridge as bridge
from relaylm.character_workspace import REQUIRED_SOURCE_FILENAMES, plan_character_workspace_slp_candidates

PRIVATE_STATEMENT_BODY = "PRIVATE_TWIN_FACT_BODY_SHOULD_NOT_LEAK_INTO_PROJECTION"


def _write_required_sources(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for filename in REQUIRED_SOURCE_FILENAMES:
        name = filename.removesuffix(".md")
        (root / filename).write_text(f"# {name}\n\nstatus:: active\n\n{name} policy.\n", encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "characters" / "relm"
        _write_required_sources(root)

        review = {
            "style_observations": [],
            "fact_candidates": [
                {
                    "statement": f"Remember a low risk project note. {PRIVATE_STATEMENT_BODY}.",
                    "type": "knowledge",
                    "provenance": ["chatgpt_reconstructed"],
                    "evidence_ids": ["e1"],
                    "time_contexts": ["2026-07"],
                    "sensitivity": "general",
                },
                {
                    "statement": "A private_only fact must never reach CW-A4 source evidence via this bridge.",
                    "type": "knowledge",
                    "provenance": "x_post",
                    "evidence_ids": ["e2"],
                    "sensitivity": "private_only",
                },
            ],
        }
        review_path = Path(tmp) / "twin_extraction_review.json"
        review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")

        before_run = plan_character_workspace_slp_candidates(root)
        assert before_run.source_evidence_count == 0, "no imports written yet: CW-A4 must see zero source evidence"

        projection = bridge.run_bridge(
            review_path,
            root,
            write_imports=True,
            approved_facts="general-only",
            approved_styles="none",
        )
        assert projection["written_count"] == 1, projection
        assert projection["skipped_count"] == 1, projection  # the private_only fact stays unwritten

        import_dir = root / ".relaylm" / "sources" / "imports" / "twin-extraction"
        written_files = list(import_dir.glob("*.json"))
        assert len(written_files) == 1, written_files

        run = plan_character_workspace_slp_candidates(root)  # dry_run only; no CW-A4 writes
        assert run.dry_run is True
        assert run.write_candidates is False
        assert run.source_evidence_count > 0, "CW-A4 must see the bridge-written import source"
        public = run.to_public_dict()
        assert public["memory_candidates_count"] >= 1 or public["memory_inbox_additions_count"] >= 1, public

        serialized = json.dumps(public, ensure_ascii=False, sort_keys=True, default=str)
        assert PRIVATE_STATEMENT_BODY not in serialized, "CW-A4 public projection must stay content-free even via the bridge path"
        assert public["content_free"] is True

        assert not (root / ".relaylm" / "build").exists(), "dry-run CW-A4 planning must not write build artifacts"

    print("RelayLM Twin Review Import Bridge <-> CW-A4 integration smoke passed")


if __name__ == "__main__":
    main()
