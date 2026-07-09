#!/usr/bin/env python3
"""Security smoke for the Twin Extraction review import bridge CLI.

Dedicated verification that public output (stdout, stderr, and exception
text) from the bridge CLI never contains statement/description bodies,
absolute filesystem paths, or credential-like values -- across dry-run,
approved writes, and every fail-closed error path. No LLM, network, or
real archive is required.
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

PRIVATE_CANARIES = (
    "CANARY_STATEMENT_BODY_do_not_leak_this_text",
    "CANARY_DESCRIPTION_BODY_do_not_leak_this_text",
    "CANARY_PRIVATE_STATEMENT_do_not_leak_this_text",
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
                "provenance": ["chatgpt_reconstructed", "sk-FAKE_CREDENTIAL_TOKEN_1234567890"],
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


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        check_dry_run_content_free(tmp_path)
        check_write_imports_content_free(tmp_path)
        check_error_paths_content_free(tmp_path)
        check_symlink_workspace_content_free(tmp_path)

    print("RelayLM Twin Review Import Bridge security smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
