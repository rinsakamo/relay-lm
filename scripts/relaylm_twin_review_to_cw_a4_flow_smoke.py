#!/usr/bin/env python3
"""End-to-end smoke: Twin Review Import Bridge (PR2) -> CW-A4 candidate/proposal flow.

Exercises the full connective path this PR documents: an approved
``twin_extraction_review.json`` fixture is turned into a governed
``.relaylm/sources/imports/twin-extraction/`` artifact by
``scripts/relaylm_twin_review_import_bridge.py``, then read by CW-A4
(``relaylm.character_workspace.plan_character_workspace_slp_candidates``)
first in dry-run and then in ``write_candidates=True`` mode.

This smoke only exercises the bridge's CLI entrypoint and CW-A4's public
Python API; it never calls MEM/SOUL/REL apply, never invokes the CW-A2
compiler, and never runs the P1 extraction preprocessing/batch-runner/merge
tools themselves (those are covered by ``relaylm_twin_extraction_smoke.py``
and ``relaylm_twin_review_import_bridge_smoke.py``). It asserts the same
boundary the runbook documents: the fixture's ``private_only`` fact and its
``style_observation`` never leave dry-run projection, CW-A4 write-candidates
only ever creates allowlisted inbox/proposal artifacts, uppercase sources
and ``.relaylm/build``, ``.relaylm/state``, ``.relaylm/queue`` are never
touched, and every stdout/public projection stays content-free.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

import relaylm_twin_review_import_bridge as bridge
from relaylm.character_workspace import REQUIRED_SOURCE_FILENAMES, plan_character_workspace_slp_candidates

GENERAL_CANARY = "GENERAL_TWIN_FLOW_STATEMENT_CANARY_do_not_leak_this_text"
PRIVATE_CANARY = "PRIVATE_ONLY_TWIN_FLOW_CANARY_do_not_leak_this_text"
STYLE_CANARY = "STYLE_TWIN_FLOW_DESCRIPTION_CANARY_do_not_leak_this_text"

ALLOWLISTED_WRITE_PREFIXES = (
    "memory/inbox/",
    "scenes/_inbox/",
    "relationships/_inbox/",
    "proposals/memory/",
    "proposals/scene/",
    "proposals/relationship/",
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _write_required_sources(root: Path) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    snapshot: dict[str, str] = {}
    for filename in REQUIRED_SOURCE_FILENAMES:
        name = filename.removesuffix(".md")
        text = f"# {name}\n\nstatus:: active\n\n{name} policy.\n"
        (root / filename).write_text(text, encoding="utf-8")
        snapshot[filename] = text
    return snapshot


def _review_fixture() -> dict:
    return {
        "style_observations": [
            {
                "category": "tone",
                "description": f"Speaks concisely and warmly. {STYLE_CANARY}.",
                "evidence_ids": ["e1"],
                "strength": "low",
            }
        ],
        "fact_candidates": [
            {
                "statement": f"Remember a low risk project note. {GENERAL_CANARY}.",
                "type": "knowledge",
                "provenance": ["chatgpt_reconstructed"],
                "evidence_ids": ["e1"],
                "time_contexts": ["2026-07"],
                "sensitivity": "general",
            },
            {
                "statement": f"A private_only fact must never reach CW-A4 source evidence. {PRIVATE_CANARY}.",
                "type": "knowledge",
                "provenance": "x_post",
                "evidence_ids": ["e2"],
                "sensitivity": "private_only",
            },
        ],
    }


def _files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def _serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _capture(func, *args, **kwargs):
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        result = func(*args, **kwargs)
    return result, stdout_buf.getvalue(), stderr_buf.getvalue()


def _assert_no_boundary_leak(text: str, root: Path) -> None:
    for canary in (GENERAL_CANARY, PRIVATE_CANARY, STYLE_CANARY):
        require(canary not in text, f"leaked canary: {canary}")
    require(str(root) not in text, "leaked absolute workspace path")
    require(str(root.resolve()) not in text, "leaked resolved absolute workspace path")
    require(tempfile.gettempdir() not in text, "leaked temp dir absolute path")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "characters" / "relm"
        uppercase_snapshot = _write_required_sources(root)

        review_path = Path(tmp) / "twin_extraction_review.json"
        review_path.write_text(json.dumps(_review_fixture(), ensure_ascii=False), encoding="utf-8")

        before_bridge = plan_character_workspace_slp_candidates(root)
        require(before_bridge.source_evidence_count == 0, "no imports written yet: CW-A4 must see zero source evidence")

        # P1 output has already been merged into twin_extraction_review.json
        # by this point (out of scope for this smoke; see
        # relaylm_twin_extraction_smoke.py). This step is the PR2 bridge CLI:
        # only the sensitivity:general fact_candidate is approved for
        # import; the private_only fact and the style_observation are never
        # written to .relaylm/sources/imports/twin-extraction/.
        exit_code, bridge_stdout, bridge_stderr = _capture(
            bridge.main,
            ["--review", str(review_path), "--workspace-root", str(root), "--write-imports", "--approved-facts", "general-only"],
        )
        require(exit_code == 0, bridge_stderr)
        _assert_no_boundary_leak(bridge_stdout + bridge_stderr, root)

        import_dir = root / ".relaylm" / "sources" / "imports" / "twin-extraction"
        written_import_files = list(import_dir.glob("*.json"))
        require(len(written_import_files) == 1, written_import_files)
        artifact_text = written_import_files[0].read_text(encoding="utf-8")
        require(GENERAL_CANARY in artifact_text, "the approved general fact should be present in its own import artifact")
        require(PRIVATE_CANARY not in artifact_text, "private_only fact_candidate must never reach the import source")
        require(STYLE_CANARY not in artifact_text, "style_observations are dry-run projection only and must never be written")

        # CW-A4 dry-run: the bridge-written import source is now readable as
        # user-assertion source evidence and produces at least one memory
        # candidate; nothing on disk changes.
        before_dry = _files(root)
        dry = plan_character_workspace_slp_candidates(root)
        require(dry.dry_run is True, "dry-run flag")
        require(dry.write_candidates is False, "write_candidates flag")
        require(dry.source_evidence_count > 0, "CW-A4 must see the bridge-written import source")
        dry_public = dry.to_public_dict()
        require(
            dry_public["memory_candidates_count"] >= 1 or dry_public["memory_inbox_additions_count"] >= 1,
            dry_public,
        )
        require(_files(root) == before_dry, "dry-run must not write any files")
        require(dry_public["content_free"] is True, dry_public)
        _assert_no_boundary_leak(_serialized(dry_public), root)
        require(not (root / ".relaylm" / "build").exists(), "dry-run CW-A4 planning must not write build artifacts")

        # CW-A4 write-candidates: only allowlisted candidate/proposal
        # artifacts are created.
        before_write = _files(root)
        write = plan_character_workspace_slp_candidates(root, write_candidates=True)
        require(write.status == "planned", write.blocked_reason_ids)
        created = _files(root) - before_write
        require(created == set(write.written_paths), created)
        require(bool(created), "write-candidates should have created at least one candidate/proposal artifact")
        require(all(rel.startswith(ALLOWLISTED_WRITE_PREFIXES) for rel in created), created)
        write_public = write.to_public_dict()
        require(write_public["content_free"] is True, write_public)
        _assert_no_boundary_leak(_serialized(write_public), root)

        # Uppercase sources are never mutated anywhere in this flow.
        for filename, text in uppercase_snapshot.items():
            require((root / filename).read_text(encoding="utf-8") == text, filename)

        # .relaylm/build, .relaylm/state, and .relaylm/queue are never
        # created or touched by the bridge or by CW-A4 dry-run/write-candidates.
        for subdir in ("build", "state", "queue"):
            require(not (root / ".relaylm" / subdir).exists(), f".relaylm/{subdir} must not be created by this flow")

    print("RelayLM Twin Review -> CW-A4 flow smoke passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
