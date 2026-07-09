#!/usr/bin/env python3
"""Smoke tests for the Twin Extraction review import bridge CLI.

No LLM, network, or real archive is required. Fixtures are small, entirely
fictional review artifacts constructed inline. Covers: dry-run projection
counts, default (no approval) writes nothing, --approved-facts
general-only writes only general fact_candidates, private_only facts are
never written, malformed review shapes fail closed, a symlink workspace
root is rejected, and an existing conflicting file is rejected.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

import relaylm_twin_review_import_bridge as bridge

REQUIRED_SOURCE_FILENAMES = ("SOUL.md", "STYLE.md", "EMOTION.md", "SCENE.md", "RELATIONSHIP.md", "MEMORY.md", "BOUNDARY.md")


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _capture(func, *args, **kwargs) -> tuple[int, str, str]:
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        exit_code = func(*args, **kwargs)
    return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()


def _write_workspace(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for filename in REQUIRED_SOURCE_FILENAMES:
        (root / filename).write_text(f"# {filename}\n\nstatus:: active\n", encoding="utf-8")


REVIEW_FIXTURE = {
    "style_observations": [
        {"category": "values", "description": "prefers short declarative sentences", "evidence_ids": ["e1"], "strength": "medium"},
        {"category": "malformed", "description": "", "evidence_ids": []},  # invalid: empty description/evidence
    ],
    "fact_candidates": [
        {
            "statement": "CANARY_GENERAL_FACT works on RelayLM dogfood tooling",
            "type": "knowledge",
            "provenance": ["chatgpt_reconstructed"],
            "evidence_ids": ["e1", "e2"],
            "time_contexts": ["2026-07"],
            "sensitivity": "general",
        },
        {
            "statement": "CANARY_PRIVATE_FACT has a private-only detail",
            "type": "knowledge",
            "provenance": "x_post",
            "evidence_ids": ["e3"],
            "time_context": "2026-06",
            "sensitivity": "private_only",
        },
        {
            "statement": "CANARY_MISSING_SENSITIVITY_FACT has no sensitivity field",
            "type": "knowledge",
            "provenance": "x_post",
            "evidence_ids": ["e4"],
        },
        {"statement": "", "type": "knowledge", "provenance": "x_post", "evidence_ids": ["e5"], "sensitivity": "general"},  # invalid: empty statement
    ],
    "summary": {},
}


def _write_review(path: Path, review: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")


def check_dry_run_projection(tmp_path: Path) -> None:
    review_path = tmp_path / "review.json"
    _write_review(review_path, REVIEW_FIXTURE)
    workspace = tmp_path / "characters" / "relm"
    _write_workspace(workspace)

    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(review_path), "--workspace-root", str(workspace), "--dry-run"])
    require(exit_code == 0, stderr)
    projection = json.loads(stdout)
    require(projection["mode"] == "dry_run", projection)
    require(projection["reviewed_style_count"] == 2, projection)
    require(projection["reviewed_fact_count"] == 4, projection)
    require(projection["eligible_fact_count"] == 1, projection)
    require(projection["eligible_style_count"] == 1, projection)
    require(projection["private_only_fact_count"] == 2, projection)  # explicit private_only + missing-sensitivity fail-closed
    require(projection["written_count"] == 0, projection)
    require(projection["skipped_count"] == 3, projection)
    require(projection["output_dir_relative"] == ".relaylm/sources/imports/twin-extraction", projection)
    require(projection["content_free"] is True, projection)
    require(not (workspace / ".relaylm").exists(), "dry-run must not create any .relaylm directory")


def check_default_write_imports_writes_nothing(tmp_path: Path) -> None:
    review_path = tmp_path / "review_default.json"
    _write_review(review_path, REVIEW_FIXTURE)
    workspace = tmp_path / "characters" / "default-write"
    _write_workspace(workspace)

    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports"])
    require(exit_code == 0, stderr)
    projection = json.loads(stdout)
    require(projection["mode"] == "write_imports", projection)
    require(projection["written_count"] == 0, projection)
    require("approved_facts_none_default" in projection["reason_ids"], projection)
    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"
    require(not import_dir.exists(), "default approval must write nothing")


def check_approved_general_only_writes_only_general(tmp_path: Path) -> None:
    review_path = tmp_path / "review_approved.json"
    _write_review(review_path, REVIEW_FIXTURE)
    workspace = tmp_path / "characters" / "approved"
    _write_workspace(workspace)

    exit_code, stdout, stderr = _capture(
        bridge.main,
        [
            "--review",
            str(review_path),
            "--workspace-root",
            str(workspace),
            "--write-imports",
            "--approved-facts",
            "general-only",
        ],
    )
    require(exit_code == 0, stderr)
    projection = json.loads(stdout)
    require(projection["written_count"] == 1, projection)
    require(projection["skipped_count"] == 2, projection)

    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"
    written_files = sorted(import_dir.glob("*.json"))
    require(len(written_files) == 1, written_files)
    require(written_files[0].name.startswith("fact-"), written_files)

    artifact = json.loads(written_files[0].read_text(encoding="utf-8"))
    require(artifact["schema_version"] == "relaylm.twin_review_import_source.v0", artifact)
    require(artifact["role"] == "user", artifact)
    require(artifact["kind"] == "fact_candidate", artifact)
    require(artifact["text"] == "CANARY_GENERAL_FACT works on RelayLM dogfood tooling", artifact)
    require(artifact["metadata"]["sensitivity"] == "general", artifact)
    require(artifact["metadata"]["approved"] is True, artifact)

    combined = stdout + stderr
    require("CANARY_GENERAL_FACT" not in combined, "stdout/stderr must stay content-free even though the written file has content")
    require("CANARY_PRIVATE_FACT" not in combined, combined)

    # A private_only fact must never be written under any current option.
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in written_files)
    require("CANARY_PRIVATE_FACT" not in all_text, "private_only fact leaked into a written import artifact")
    require("CANARY_MISSING_SENSITIVITY_FACT" not in all_text, "missing-sensitivity fact must fail closed to private_only and stay unwritten")

    # Idempotent rerun: identical content, must not error and must report the same write.
    exit_code2, stdout2, stderr2 = _capture(
        bridge.main,
        [
            "--review",
            str(review_path),
            "--workspace-root",
            str(workspace),
            "--write-imports",
            "--approved-facts",
            "general-only",
        ],
    )
    require(exit_code2 == 0, stderr2)
    projection2 = json.loads(stdout2)
    require(projection2["written_count"] == 1, projection2)
    require(sorted(import_dir.glob("*.json")) == written_files, "idempotent rerun must not create additional files")


def check_conflicting_existing_file_rejected(tmp_path: Path) -> None:
    review_path = tmp_path / "review_conflict.json"
    _write_review(review_path, REVIEW_FIXTURE)
    workspace = tmp_path / "characters" / "conflict"
    _write_workspace(workspace)

    exit_code, stdout, stderr = _capture(
        bridge.main,
        ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
    )
    require(exit_code == 0, stderr)
    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"
    written_files = sorted(import_dir.glob("*.json"))
    require(len(written_files) == 1, written_files)

    written_files[0].write_text('{"tampered": true}', encoding="utf-8")

    exit_code2, stdout2, stderr2 = _capture(
        bridge.main,
        ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
    )
    require(exit_code2 != 0, "a differing existing file must be rejected as a conflict")
    require(stdout2 == "", "a conflict must not print a stdout projection")
    require(written_files[0].read_text(encoding="utf-8") == '{"tampered": true}', "conflicting content must be left untouched")


def check_duplicate_fact_identity(tmp_path: Path) -> None:
    # Two entries sharing the same (statement, type, provenance, sensitivity)
    # identity -- and thus the same output filename -- must not silently
    # double-count writes or let a "last write wins" race pick one version.
    same_content_review = {
        "style_observations": [],
        "fact_candidates": [
            {
                "statement": "CANARY_DUPLICATE_SAME identical fact repeated",
                "type": "knowledge",
                "provenance": "x_post",
                "evidence_ids": ["e1"],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_DUPLICATE_SAME identical fact repeated",
                "type": "knowledge",
                "provenance": "x_post",
                "evidence_ids": ["e1"],
                "sensitivity": "general",
            },
        ],
    }
    review_path = tmp_path / "review_dup_same.json"
    _write_review(review_path, same_content_review)
    workspace = tmp_path / "characters" / "dup-same"
    _write_workspace(workspace)
    exit_code, stdout, stderr = _capture(
        bridge.main,
        ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
    )
    require(exit_code == 0, stderr)
    projection = json.loads(stdout)
    require(projection["written_count"] == 1, "identical-content duplicates must collapse to one written file")
    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"
    require(len(list(import_dir.glob("*.json"))) == 1, "identical-content duplicates must not create two files")

    conflicting_review = {
        "style_observations": [],
        "fact_candidates": [
            {
                "statement": "CANARY_DUPLICATE_CONFLICT identical identity",
                "type": "knowledge",
                "provenance": "x_post",
                "evidence_ids": ["e1"],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_DUPLICATE_CONFLICT identical identity",
                "type": "knowledge",
                "provenance": "x_post",
                "evidence_ids": ["e2"],  # same identity fields, different evidence -> different content
                "sensitivity": "general",
            },
        ],
    }
    review_path2 = tmp_path / "review_dup_conflict.json"
    _write_review(review_path2, conflicting_review)
    workspace2 = tmp_path / "characters" / "dup-conflict"
    _write_workspace(workspace2)
    exit_code2, stdout2, stderr2 = _capture(
        bridge.main,
        ["--review", str(review_path2), "--workspace-root", str(workspace2), "--write-imports", "--approved-facts", "general-only"],
    )
    require(exit_code2 != 0, "same-identity, differing-content duplicates must fail closed, not last-write-wins")
    require(stdout2 == "", stdout2)
    import_dir2 = workspace2 / ".relaylm" / "sources" / "imports" / "twin-extraction"
    require(not import_dir2.exists(), "a fail-closed duplicate-identity conflict must not write anything")


def check_malformed_review_fails_closed(tmp_path: Path) -> None:
    workspace = tmp_path / "characters" / "malformed"
    _write_workspace(workspace)

    not_json_path = tmp_path / "not_json.json"
    not_json_path.write_text("{not valid json", encoding="utf-8")
    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(not_json_path), "--workspace-root", str(workspace), "--dry-run"])
    require(exit_code != 0, "invalid JSON must fail closed")
    require(stdout == "", stdout)

    wrong_root_path = tmp_path / "wrong_root.json"
    wrong_root_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(wrong_root_path), "--workspace-root", str(workspace), "--dry-run"])
    require(exit_code != 0, "a non-object review root must fail closed")

    wrong_shape_path = tmp_path / "wrong_shape.json"
    wrong_shape_path.write_text(json.dumps({"fact_candidates": "not-a-list"}), encoding="utf-8")
    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(wrong_shape_path), "--workspace-root", str(workspace), "--dry-run"])
    require(exit_code != 0, "a non-list fact_candidates must fail closed")

    missing_path = tmp_path / "does_not_exist.json"
    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(missing_path), "--workspace-root", str(workspace), "--dry-run"])
    require(exit_code != 0, "a missing review file must fail closed")


def check_missing_or_symlink_workspace_rejected(tmp_path: Path) -> None:
    review_path = tmp_path / "review_ws.json"
    _write_review(review_path, REVIEW_FIXTURE)

    missing_workspace = tmp_path / "does_not_exist_workspace"
    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(review_path), "--workspace-root", str(missing_workspace), "--dry-run"])
    require(exit_code != 0, "a missing workspace root must fail closed")

    outside = tmp_path / "outside_dir"
    outside.mkdir()
    symlink_workspace = tmp_path / "symlink_workspace"
    try:
        symlink_workspace.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        return
    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(review_path), "--workspace-root", str(symlink_workspace), "--dry-run"])
    require(exit_code != 0, "a symlink workspace root must be rejected")
    require(stdout == "", stdout)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        check_dry_run_projection(tmp_path)
        check_default_write_imports_writes_nothing(tmp_path)
        check_approved_general_only_writes_only_general(tmp_path)
        check_conflicting_existing_file_rejected(tmp_path)
        check_duplicate_fact_identity(tmp_path)
        check_malformed_review_fails_closed(tmp_path)
        check_missing_or_symlink_workspace_rejected(tmp_path)

    print("RelayLM Twin Review Import Bridge smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
