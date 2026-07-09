#!/usr/bin/env python3
"""Security smoke for the Twin Extraction review import bridge CLI.

Dedicated verification that public output (stdout, stderr, and exception
text) from the bridge CLI never contains statement/description bodies,
absolute filesystem paths, credential-like values, or a raw Python
traceback -- across dry-run, approved writes, and every fail-closed error
path, including directory-conflict and permission-denied write failures
and the resulting rollback. No LLM, network, or real archive is required.
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

PRIVATE_CANARIES = (
    "CANARY_STATEMENT_BODY_do_not_leak_this_text",
    "CANARY_DESCRIPTION_BODY_do_not_leak_this_text",
    "CANARY_PRIVATE_STATEMENT_do_not_leak_this_text",
    "CANARY_CREDENTIAL_METADATA_STATEMENT_do_not_leak_this_text",
    "sk-FAKE_CREDENTIAL_TOKEN_1234567890",
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _capture(func, *args, **kwargs) -> tuple[int, str, str]:
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        exit_code = func(*args, **kwargs)
    return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()


def _assert_content_free(combined: str, tmp_path: Path) -> None:
    for canary in PRIVATE_CANARIES:
        require(canary not in combined, f"leaked canary: {canary}")
    require(str(tmp_path) not in combined, "leaked absolute path")
    require(str(tmp_path.resolve()) not in combined, "leaked resolved absolute path")
    require(tempfile.gettempdir() not in combined, "leaked temp dir absolute path")
    require("Traceback (most recent call last)" not in combined, "leaked a raw Python traceback")
    require(".py\", line" not in combined, "leaked a raw Python traceback frame")


def _write_workspace(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for filename in REQUIRED_SOURCE_FILENAMES:
        (root / filename).write_text(f"# {filename}\n\nstatus:: active\n", encoding="utf-8")


def _review_fixture() -> dict:
    return {
        "style_observations": [
            {
                "category": "tone",
                "description": "CANARY_DESCRIPTION_BODY_do_not_leak_this_text",
                "evidence_ids": ["e1"],
                "strength": "low",
            }
        ],
        "fact_candidates": [
            {
                "statement": "CANARY_STATEMENT_BODY_do_not_leak_this_text",
                "type": "knowledge",
                "provenance": ["chatgpt_reconstructed"],
                "evidence_ids": ["e1"],
                "time_contexts": ["2026-07"],
                "sensitivity": "general",
            },
            {
                "statement": "CANARY_PRIVATE_STATEMENT_do_not_leak_this_text",
                "type": "knowledge",
                "provenance": "x_post",
                "evidence_ids": ["e2"],
                "sensitivity": "private_only",
            },
            {
                # Structurally a general fact, but its metadata is
                # credential-shaped: the provenance allowlist plus the
                # evidence_id credential heuristic must both independently
                # drop it as invalid, and it must never be written.
                "statement": "CANARY_CREDENTIAL_METADATA_STATEMENT_do_not_leak_this_text",
                "type": "knowledge",
                "provenance": "x_post",
                "evidence_ids": ["sk-FAKE_CREDENTIAL_TOKEN_1234567890"],
                "sensitivity": "general",
            },
        ],
    }


def check_dry_run_content_free(tmp_path: Path) -> None:
    secret_subdir = tmp_path / "secret_subdir"
    review_path = secret_subdir / "review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(_review_fixture(), ensure_ascii=False), encoding="utf-8")
    workspace = secret_subdir / "characters" / "relm"
    _write_workspace(workspace)

    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(review_path), "--workspace-root", str(workspace), "--dry-run"])
    require(exit_code == 0, stderr)
    _assert_content_free(stdout + stderr, tmp_path)


def check_write_imports_content_free(tmp_path: Path) -> None:
    secret_subdir = tmp_path / "secret_subdir_write"
    review_path = secret_subdir / "review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(_review_fixture(), ensure_ascii=False), encoding="utf-8")
    workspace = secret_subdir / "characters" / "relm"
    _write_workspace(workspace)

    exit_code, stdout, stderr = _capture(
        bridge.main,
        ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
    )
    require(exit_code == 0, stderr)
    _assert_content_free(stdout + stderr, tmp_path)

    # The written artifact is an intentional work product and is allowed to
    # contain the approved general statement; only stdout/stderr and any
    # never-approved private_only statement must stay out of it entirely.
    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"
    written_files = list(import_dir.glob("*.json"))
    require(len(written_files) == 1, written_files)
    artifact_text = written_files[0].read_text(encoding="utf-8")
    require("CANARY_STATEMENT_BODY_do_not_leak_this_text" in artifact_text, "approved artifact should retain its own statement")
    require("CANARY_PRIVATE_STATEMENT_do_not_leak_this_text" not in artifact_text, "private_only statement must never be written")
    require(
        "CANARY_CREDENTIAL_METADATA_STATEMENT_do_not_leak_this_text" not in artifact_text,
        "a fact with credential-shaped metadata must be dropped as invalid, never written",
    )
    require("sk-FAKE_CREDENTIAL_TOKEN_1234567890" not in artifact_text, "credential-like evidence_id must never reach a written artifact")
    require(str(tmp_path) not in artifact_text, "written artifact must not contain an absolute path")
    require(written_files[0].name == written_files[0].name.lower(), "filename must be a stable lowercase hash, not content-derived text")
    import re

    require(re.fullmatch(r"fact-[0-9a-f]{24}\.json", written_files[0].name), written_files[0].name)


def check_error_paths_content_free(tmp_path: Path) -> None:
    secret_subdir = tmp_path / "secret_subdir_errors"
    secret_subdir.mkdir(parents=True, exist_ok=True)
    workspace = secret_subdir / "characters" / "relm"
    _write_workspace(workspace)

    # Missing review file.
    missing_review = secret_subdir / "does_not_exist.json"
    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(missing_review), "--workspace-root", str(workspace), "--dry-run"])
    require(exit_code != 0, "missing review file must fail")
    _assert_content_free(stdout + stderr, tmp_path)

    # Malformed (non-UTF8-decodable content is not exercised here; invalid
    # JSON containing a canary-like credential token must not echo it back).
    malformed_review = secret_subdir / "malformed.json"
    malformed_review.write_text("sk-FAKE_CREDENTIAL_TOKEN_1234567890 { not valid json", encoding="utf-8")
    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(malformed_review), "--workspace-root", str(workspace), "--dry-run"])
    require(exit_code != 0, "malformed review must fail")
    _assert_content_free(stdout + stderr, tmp_path)
    require("sk-FAKE_CREDENTIAL_TOKEN_1234567890" not in (stdout + stderr), "malformed JSON body must not be echoed")

    # Missing workspace root.
    review_path = secret_subdir / "ok_review.json"
    review_path.write_text(json.dumps(_review_fixture(), ensure_ascii=False), encoding="utf-8")
    missing_workspace = secret_subdir / "characters" / "does_not_exist"
    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(review_path), "--workspace-root", str(missing_workspace), "--dry-run"])
    require(exit_code != 0, "missing workspace root must fail")
    _assert_content_free(stdout + stderr, tmp_path)


def check_symlink_workspace_content_free(tmp_path: Path) -> None:
    secret_subdir = tmp_path / "secret_subdir_symlink"
    secret_subdir.mkdir(parents=True, exist_ok=True)
    review_path = secret_subdir / "review.json"
    review_path.write_text(json.dumps(_review_fixture(), ensure_ascii=False), encoding="utf-8")
    outside = secret_subdir / "outside"
    outside.mkdir()
    symlink_workspace = secret_subdir / "symlink_workspace"
    try:
        symlink_workspace.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        return
    exit_code, stdout, stderr = _capture(bridge.main, ["--review", str(review_path), "--workspace-root", str(symlink_workspace), "--dry-run"])
    require(exit_code != 0, "symlink workspace root must be rejected")
    _assert_content_free(stdout + stderr, tmp_path)


def check_directory_conflict_write_failure_content_free(tmp_path: Path) -> None:
    secret_subdir = tmp_path / "secret_subdir_dirconflict"
    review_path = secret_subdir / "review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(_review_fixture(), ensure_ascii=False), encoding="utf-8")
    workspace = secret_subdir / "characters" / "relm"
    _write_workspace(workspace)

    blocking_parent = workspace / ".relaylm" / "sources" / "imports"
    blocking_parent.mkdir(parents=True, exist_ok=True)
    (blocking_parent / "twin-extraction").write_text("CANARY_BLOCKING_FILE_do_not_leak_this_text", encoding="utf-8")

    exit_code, stdout, stderr = _capture(
        bridge.main,
        ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
    )
    require(exit_code != 0, "a directory-vs-file conflict at the import path must fail closed")
    require(stdout == "", stdout)
    combined = stdout + stderr
    _assert_content_free(combined, tmp_path)
    require("CANARY_BLOCKING_FILE_do_not_leak_this_text" not in combined, combined)


def check_permission_denied_write_failure_content_free(tmp_path: Path) -> None:
    secret_subdir = tmp_path / "secret_subdir_permdenied"
    review_path = secret_subdir / "review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(_review_fixture(), ensure_ascii=False), encoding="utf-8")
    workspace = secret_subdir / "characters" / "relm"
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
            # (e.g. root in a container); nothing to verify here.
            return
        require(stdout == "", stdout)
        _assert_content_free(stdout + stderr, tmp_path)
    finally:
        import_dir.chmod(0o700)


def check_precreated_temp_symlink_content_free(tmp_path: Path) -> None:
    secret_subdir = tmp_path / "secret_subdir_temp_symlink"
    review_path = secret_subdir / "review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(_review_fixture(), ensure_ascii=False), encoding="utf-8")
    workspace = secret_subdir / "characters" / "relm"
    _write_workspace(workspace)

    # The exact filename the bridge will derive for the fixture's one
    # approved general fact, so we can pre-occupy its temp path.
    filename, _text = bridge._fact_artifact(
        {
            "statement": "CANARY_STATEMENT_BODY_do_not_leak_this_text",
            "type": "knowledge",
            "evidence_ids": ["e1"],
            "provenance": ["chatgpt_reconstructed"],
            "time_contexts": ["2026-07"],
            "sensitivity": "general",
        }
    )
    import_dir = workspace / ".relaylm" / "sources" / "imports" / "twin-extraction"
    import_dir.mkdir(parents=True, exist_ok=True)
    outside_target = secret_subdir / "outside_temp_symlink_target.txt"
    outside_target.write_text("CANARY_OUTSIDE_SYMLINK_TARGET_do_not_leak_this_text", encoding="utf-8")
    temp_path = import_dir / f".{filename}.tmp-{os.getpid()}"
    try:
        temp_path.symlink_to(outside_target)
    except (OSError, NotImplementedError):
        return  # platform cannot create symlinks; nothing to exercise here

    exit_code, stdout, stderr = _capture(
        bridge.main,
        ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
    )
    require(exit_code != 0, "a pre-created temp-path symlink must fail closed")
    require(stdout == "", stdout)
    combined = stdout + stderr
    _assert_content_free(combined, tmp_path)
    require("CANARY_OUTSIDE_SYMLINK_TARGET_do_not_leak_this_text" not in combined, combined)
    require(
        outside_target.read_text(encoding="utf-8") == "CANARY_OUTSIDE_SYMLINK_TARGET_do_not_leak_this_text",
        "the symlink target must never be written through",
    )


def check_target_appears_after_preflight_content_free(tmp_path: Path) -> None:
    secret_subdir = tmp_path / "secret_subdir_toctou"
    review_path = secret_subdir / "review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(_review_fixture(), ensure_ascii=False), encoding="utf-8")
    workspace = secret_subdir / "characters" / "relm"
    _write_workspace(workspace)

    original_link = bridge.os.link

    def sneaky_link(src, dst):
        # A concurrent writer creates the target between preflight and
        # commit -- os.link must still fail closed rather than clobber it,
        # and the CLI must not leak the attacker's body anywhere.
        Path(dst).write_text("CANARY_TOCTOU_ATTACKER_BODY_do_not_leak_this_text", encoding="utf-8")
        return original_link(src, dst)

    bridge.os.link = sneaky_link
    try:
        exit_code, stdout, stderr = _capture(
            bridge.main,
            ["--review", str(review_path), "--workspace-root", str(workspace), "--write-imports", "--approved-facts", "general-only"],
        )
    finally:
        bridge.os.link = original_link

    require(exit_code != 0, "a target that appears after preflight must fail closed")
    require(stdout == "", stdout)
    combined = stdout + stderr
    _assert_content_free(combined, tmp_path)
    require("CANARY_TOCTOU_ATTACKER_BODY_do_not_leak_this_text" not in combined, combined)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        check_dry_run_content_free(tmp_path)
        check_write_imports_content_free(tmp_path)
        check_error_paths_content_free(tmp_path)
        check_symlink_workspace_content_free(tmp_path)
        check_directory_conflict_write_failure_content_free(tmp_path)
        check_permission_denied_write_failure_content_free(tmp_path)
        check_precreated_temp_symlink_content_free(tmp_path)
        check_target_appears_after_preflight_content_free(tmp_path)

    print("RelayLM Twin Review Import Bridge security smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
