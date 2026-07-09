#!/usr/bin/env python3
"""Smoke tests for the Twin Extraction review import bridge CLI.

No LLM, network, or real archive is required. Fixtures are small, entirely
fictional review artifacts constructed inline. Covers: dry-run projection
counts (including invalid_fact_count / invalid_style_count breakdown),
default (no approval) writes nothing, --approved-facts general-only
writes only general fact_candidates, private_only facts are never
written, provenance-allowlist / evidence_id / time_context / credential-
like metadata hardening drops items as invalid rather than writing them,
malformed review shapes fail closed, a symlink workspace root is
rejected, an existing conflicting file is rejected, and a mid-batch write
failure leaves no partial files behind.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
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
    require(projection["invalid_fact_count"] == 1, projection)  # empty-statement fact
    require(projection["invalid_style_count"] == 1, projection)  # empty-description/evidence style
    require(
        projection["reviewed_fact_count"]
        == projection["eligible_fact_count"] + projection["private_only_fact_count"] + projection["invalid_fact_count"],
        projection,
    )
    require(
        projection["reviewed_style_count"] == projection["eligible_style_count"] + projection["invalid_style_count"],
        projection,
    )
    require("invalid_fact_candidates_dropped" in projection["reason_ids"], projection)
    require("invalid_style_observations_dropped" in projection["reason_ids"], projection)
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


def _single_general_fact_review(statement: str) -> dict:
    return {
        "style_observations": [],
        "fact_candidates": [
            {
                "statement": statement,
                "type": "knowledge",
                "provenance": ["x_post"],
                "evidence_ids": ["e1"],
                "time_contexts": ["2026-07"],
                "sensitivity": "general",
            }
        ],
    }


def check_provenance_allowlist(tmp_path: Path) -> None:
    review = {
        "style_observations": [],
        "fact_candidates": [
            {
                "statement": "CANARY_UNKNOWN_PROVENANCE must not be written",
                "type": "knowledge",
                "provenance": ["twitter_dm"],  # not in the allowlist
                "evidence_ids": ["e1"],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_MIXED_PROVENANCE must not be written",
                "type": "knowledge",
                "provenance": ["x_post", "twitter_dm"],  # partially allowed is still rejected
                "evidence_ids": ["e2"],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_ALLOWED_PROVENANCE should be written",
                "type": "knowledge",
                "provenance": ["x_post", "chatgpt_reconstructed"],
                "evidence_ids": ["e3"],
                "sensitivity": "general",
            },
        ],
    }
    review_path = tmp_path / "review_provenance.json"
    _write_review(review_path, review)
    workspace = tmp_path / "characters" / "provenance"
    _write_workspace(workspace)

    exit_code, stdout, stderr = _capture(
        bridge.main,
        ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
    )
    require(exit_code == 0, stderr)
    projection = json.loads(stdout)
    require(projection["invalid_fact_count"] == 2, projection)
    require(projection["eligible_fact_count"] == 1, projection)
    require(projection["written_count"] == 1, projection)

    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"
    written_files = list(import_dir.glob("*.json"))
    require(len(written_files) == 1, written_files)
    artifact_text = written_files[0].read_text(encoding="utf-8")
    require("CANARY_ALLOWED_PROVENANCE" in artifact_text, artifact_text)
    require("CANARY_UNKNOWN_PROVENANCE" not in artifact_text, "disallowed-provenance fact must never be written")
    require("CANARY_MIXED_PROVENANCE" not in artifact_text, "partially-disallowed provenance must never be written")


def check_evidence_and_time_context_hardening(tmp_path: Path) -> None:
    long_id = "x" * 500  # exceeds MAX_EVIDENCE_ID_LENGTH
    review = {
        "style_observations": [
            {
                "category": "values",
                "description": "a normal, unrelated style observation used only as a control case",
                "evidence_ids": ["e1"],
            },
        ],
        "fact_candidates": [
            {
                "statement": "CANARY_NEWLINE_EVIDENCE must not be written",
                "type": "knowledge",
                "provenance": ["x_post"],
                "evidence_ids": ["e1\ninjected"],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_TOO_LONG_EVIDENCE must not be written",
                "type": "knowledge",
                "provenance": ["x_post"],
                "evidence_ids": [long_id],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_EMPTY_EVIDENCE must not be written",
                "type": "knowledge",
                "provenance": ["x_post"],
                "evidence_ids": [""],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_CREDENTIAL_EVIDENCE must not be written",
                "type": "knowledge",
                "provenance": ["x_post"],
                "evidence_ids": ["sk-FAKE_CREDENTIAL_TOKEN_1234567890"],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_CREDENTIAL_TIME_CONTEXT must not be written",
                "type": "knowledge",
                "provenance": ["x_post"],
                "evidence_ids": ["e1"],
                "time_contexts": ["password: hunter2"],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_CREDENTIAL_TYPE must not be written",
                "type": "sk-FAKE_CREDENTIAL_TOKEN_abcdefgh",
                "provenance": ["x_post"],
                "evidence_ids": ["e1"],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_VALID_FACT should be written",
                "type": "knowledge",
                "provenance": ["x_post"],
                "evidence_ids": ["e1", "conv-a"],
                "time_contexts": ["2026-07"],
                "sensitivity": "general",
            },
        ],
    }
    review_path = tmp_path / "review_hardening.json"
    _write_review(review_path, review)
    workspace = tmp_path / "characters" / "hardening"
    _write_workspace(workspace)

    exit_code, stdout, stderr = _capture(
        bridge.main,
        ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
    )
    require(exit_code == 0, stderr)
    projection = json.loads(stdout)
    require(projection["invalid_fact_count"] == 6, projection)
    require(projection["eligible_fact_count"] == 1, projection)
    require(projection["written_count"] == 1, projection)
    require(projection["invalid_style_count"] == 0, projection)  # category/description/evidence_ids all valid here

    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"
    written_files = list(import_dir.glob("*.json"))
    require(len(written_files) == 1, written_files)
    artifact_text = written_files[0].read_text(encoding="utf-8")
    require("CANARY_VALID_FACT" in artifact_text, artifact_text)
    for forbidden in (
        "CANARY_NEWLINE_EVIDENCE",
        "CANARY_TOO_LONG_EVIDENCE",
        "CANARY_EMPTY_EVIDENCE",
        "CANARY_CREDENTIAL_EVIDENCE",
        "CANARY_CREDENTIAL_TIME_CONTEXT",
        "CANARY_CREDENTIAL_TYPE",
        "sk-FAKE_CREDENTIAL_TOKEN_1234567890",
        "sk-FAKE_CREDENTIAL_TOKEN_abcdefgh",
        "password: hunter2",
    ):
        require(forbidden not in artifact_text, f"invalid metadata leaked into a written artifact: {forbidden}")


def check_style_category_credential_like_is_invalid(tmp_path: Path) -> None:
    review = {
        "style_observations": [
            {
                "category": "sk-FAKE_CREDENTIAL_TOKEN_abcdefgh",
                "description": "a credential-shaped category must invalidate the observation",
                "evidence_ids": ["e1"],
            },
            {"category": "values", "description": "a normal style observation", "evidence_ids": ["e1"]},
        ],
        "fact_candidates": [],
    }
    review_path = tmp_path / "review_style_category.json"
    _write_review(review_path, review)
    workspace = tmp_path / "characters" / "style-category"
    _write_workspace(workspace)

    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(review_path), "--workspace-root", str(workspace), "--dry-run"])
    require(exit_code == 0, stderr)
    projection = json.loads(stdout)
    require(projection["reviewed_style_count"] == 2, projection)
    require(projection["invalid_style_count"] == 1, projection)
    require(projection["eligible_style_count"] == 1, projection)


def check_written_artifact_has_no_stray_canary_in_metadata(tmp_path: Path) -> None:
    # A written artifact's metadata must contain only its own legitimate,
    # allowlisted values; only the "text" field carries the approved
    # statement. No credential/private canary from a dropped sibling
    # candidate should ever appear anywhere in the written file.
    review = {
        "style_observations": [],
        "fact_candidates": [
            {
                "statement": "CANARY_APPROVED_STATEMENT_ONLY should appear as text",
                "type": "knowledge",
                "provenance": ["chatgpt_reconstructed"],
                "evidence_ids": ["e1"],
                "time_contexts": ["2026-07"],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_PRIVATE_SIBLING must never be written",
                "type": "knowledge",
                "provenance": ["x_post"],
                "evidence_ids": ["e2"],
                "sensitivity": "private_only",
            },
            {
                "statement": "CANARY_DROPPED_CREDENTIAL_SIBLING must never be written",
                "type": "knowledge",
                "provenance": ["x_post"],
                "evidence_ids": ["ghp_FAKECREDENTIALTOKEN1234567890"],
                "sensitivity": "general",
            },
        ],
    }
    review_path = tmp_path / "review_artifact_metadata.json"
    _write_review(review_path, review)
    workspace = tmp_path / "characters" / "artifact-metadata"
    _write_workspace(workspace)

    exit_code, stdout, stderr = _capture(
        bridge.main,
        ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
    )
    require(exit_code == 0, stderr)
    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"
    written_files = list(import_dir.glob("*.json"))
    require(len(written_files) == 1, written_files)
    artifact = json.loads(written_files[0].read_text(encoding="utf-8"))
    require(artifact["text"] == "CANARY_APPROVED_STATEMENT_ONLY should appear as text", artifact)
    metadata_text = json.dumps(artifact["metadata"], ensure_ascii=False)
    for forbidden in ("CANARY_PRIVATE_SIBLING", "CANARY_DROPPED_CREDENTIAL_SIBLING", "ghp_FAKECREDENTIALTOKEN1234567890"):
        require(forbidden not in metadata_text, f"metadata leaked unrelated/dropped content: {forbidden}")
    require(metadata_text.count("CANARY") == 0, "metadata must not carry any canary at all, approved or not")


def check_write_directory_conflict_fails_closed(tmp_path: Path) -> None:
    review_path = tmp_path / "review_dirconflict.json"
    _write_review(review_path, _single_general_fact_review("CANARY_DIRCONFLICT_STATEMENT should not be written"))
    workspace = tmp_path / "characters" / "dirconflict"
    _write_workspace(workspace)

    blocking_parent = workspace / ".relaylm" / "sources" / "imports"
    blocking_parent.mkdir(parents=True, exist_ok=True)
    blocking_file = blocking_parent / "twin-extraction"
    blocking_file.write_text("CANARY_BLOCKING_FILE_BODY", encoding="utf-8")

    exit_code, stdout, stderr = _capture(
        bridge.main,
        ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
    )
    require(exit_code != 0, "a directory-vs-file conflict at the import path must fail closed")
    require(stdout == "", stdout)
    combined = stdout + stderr
    require("CANARY_BLOCKING_FILE_BODY" not in combined, combined)
    require("Traceback" not in combined, combined)
    require(blocking_file.is_file(), "blocking file must be left untouched")
    require(blocking_file.read_text(encoding="utf-8") == "CANARY_BLOCKING_FILE_BODY", "blocking file content must be unchanged")


def check_write_permission_denied_leaves_no_partial_files(tmp_path: Path) -> None:
    review_path = tmp_path / "review_permdenied.json"
    _write_review(review_path, _single_general_fact_review("CANARY_PERMDENIED_STATEMENT should not be written"))
    workspace = tmp_path / "characters" / "permdenied"
    _write_workspace(workspace)

    parents = workspace / ".relaylm" / "sources" / "imports"
    parents.mkdir(parents=True, exist_ok=True)
    import_dir = parents / "twin-extraction"
    import_dir.mkdir()
    import_dir.chmod(0o500)  # read + execute only: no write permission
    try:
        exit_code, stdout, stderr = _capture(
            bridge.main,
            ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
        )
        if exit_code == 0:
            # Running as a user/filesystem that ignores this permission bit
            # (e.g. root in a container); this half of the check cannot be
            # exercised here, so skip it rather than assert a false failure.
            return
        require(stdout == "", stdout)
        combined = stdout + stderr
        require("CANARY_PERMDENIED_STATEMENT" not in combined, combined)
        require("Traceback" not in combined, combined)
    finally:
        import_dir.chmod(0o700)
    require(len(list(import_dir.glob("*.json"))) == 0, "a permission-denied write must leave no partial files")


def check_atomic_batch_rollback_on_partial_failure(tmp_path: Path) -> None:
    # Directly exercise _write_pending_atomically: if the second of three
    # commits fails, the first file that was already committed must be
    # rolled back, and no temp files may remain -- an all-or-nothing
    # batch, not a partially-written one.
    workspace = tmp_path / "characters" / "atomic-rollback"
    _write_workspace(workspace)
    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"

    pending = [
        ("fact-aaaaaaaaaaaaaaaaaaaaaaaa.json", "AAAA-CONTENT\n"),
        ("fact-bbbbbbbbbbbbbbbbbbbbbbbb.json", "BBBB-CONTENT\n"),
        ("fact-cccccccccccccccccccccccc.json", "CCCC-CONTENT\n"),
    ]

    original_link = bridge.os.link
    call_count = {"n": 0}

    def flaky_link(src, dst):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("simulated failure on second commit")
        return original_link(src, dst)

    bridge.os.link = flaky_link
    try:
        try:
            bridge._write_pending_atomically(import_dir, pending)
            raise AssertionError("expected a BridgeInputError from the simulated failure")
        except bridge.BridgeInputError:
            pass
    finally:
        bridge.os.link = original_link

    remaining = list(import_dir.iterdir()) if import_dir.exists() else []
    require(remaining == [], f"a mid-batch failure must leave zero files behind, not a partial batch: {remaining}")


def check_precreated_temp_symlink_not_followed(tmp_path: Path) -> None:
    # A pre-created symlink at the exact deterministic temp path (or a
    # stale leftover temp file from a crashed prior run) must never be
    # followed or written through: O_EXCL must make temp creation fail
    # closed instead, leaving whatever the symlink points to untouched.
    workspace = tmp_path / "characters" / "temp-symlink"
    _write_workspace(workspace)
    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"
    import_dir.mkdir(parents=True, exist_ok=True)

    outside_target = tmp_path / "outside_temp_symlink_target.txt"
    outside_target.write_text("PRE_EXISTING_OUTSIDE_CONTENT", encoding="utf-8")

    filename = "fact-deadbeefdeadbeefdeadbeef.json"
    temp_path = import_dir / f".{filename}.tmp-{os.getpid()}"
    try:
        temp_path.symlink_to(outside_target)
    except (OSError, NotImplementedError):
        return  # platform cannot create symlinks; nothing to exercise here

    try:
        bridge._write_pending_atomically(import_dir, [(filename, "REAL-CONTENT\n")])
        raise AssertionError("expected a BridgeInputError when a symlink pre-occupies the temp path")
    except bridge.BridgeInputError:
        pass

    require(outside_target.read_text(encoding="utf-8") == "PRE_EXISTING_OUTSIDE_CONTENT", "the symlink target must never be written through")
    require(temp_path.is_symlink(), "the pre-created symlink itself must be left untouched, not removed"),
    require(not (import_dir / filename).exists(), "no final target may be created when the temp step failed closed")


def check_target_appears_after_preflight_fails_closed(tmp_path: Path) -> None:
    # Simulate a TOCTOU race: preflight finds no existing target, but by
    # the time the batch actually commits, something else has created it.
    # The commit must fail closed and must never clobber what is there.
    workspace = tmp_path / "characters" / "toctou-target"
    _write_workspace(workspace)
    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"
    import_dir.mkdir(parents=True, exist_ok=True)

    filename = "fact-cafebabecafebabecafebabe.json"
    target = import_dir / filename
    original_link = bridge.os.link

    def sneaky_link(src, dst):
        # A concurrent writer creates the target between preflight and
        # this commit attempt.
        Path(dst).write_text("CANARY_TOCTOU_ATTACKER_BODY", encoding="utf-8")
        return original_link(src, dst)

    bridge.os.link = sneaky_link
    try:
        try:
            bridge._write_pending_atomically(import_dir, [(filename, "REAL-CONTENT\n")])
            raise AssertionError("expected a BridgeInputError when the target appears after preflight")
        except bridge.BridgeInputError:
            pass
    finally:
        bridge.os.link = original_link

    require(target.read_text(encoding="utf-8") == "CANARY_TOCTOU_ATTACKER_BODY", "a target that appeared after preflight must be left untouched, not clobbered")
    leftovers = [p for p in import_dir.iterdir() if p != target]
    require(leftovers == [], f"no stray temp files may remain after a failed-closed commit: {leftovers}")


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
        check_provenance_allowlist(tmp_path)
        check_evidence_and_time_context_hardening(tmp_path)
        check_style_category_credential_like_is_invalid(tmp_path)
        check_written_artifact_has_no_stray_canary_in_metadata(tmp_path)
        check_write_directory_conflict_fails_closed(tmp_path)
        check_write_permission_denied_leaves_no_partial_files(tmp_path)
        check_atomic_batch_rollback_on_partial_failure(tmp_path)
        check_precreated_temp_symlink_not_followed(tmp_path)
        check_target_appears_after_preflight_fails_closed(tmp_path)
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
