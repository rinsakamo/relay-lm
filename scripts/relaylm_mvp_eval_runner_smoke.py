#!/usr/bin/env python3
"""Smoke tests for the RelayLM MVP eval runner aggregation contract."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from relaylm_mvp_eval_runner import (
    CategorySpec,
    CommandSpec,
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_SKIP,
    filter_categories,
    format_category_list,
    format_summary_text,
    run_categories,
    write_summary_json,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _python_command(code: str) -> tuple[str, ...]:
    return (sys.executable, "-c", code)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        categories = (
            CategorySpec(
                name="pass_category",
                required=True,
                commands=(
                    CommandSpec(
                        name="fake-pass",
                        argv=_python_command("print('ok')"),
                        required=True,
                    ),
                ),
            ),
            CategorySpec(
                name="optional_skip_category",
                required=False,
                commands=(
                    CommandSpec(
                        name="fake-optional-missing",
                        argv=(sys.executable, "scripts/not_present.py"),
                        required=False,
                    ),
                ),
            ),
            CategorySpec(
                name="fail_category",
                required=True,
                commands=(
                    CommandSpec(
                        name="fake-required-fail",
                        argv=_python_command("raise SystemExit(7)"),
                        required=True,
                    ),
                ),
            ),
        )

        summary = run_categories(repo_root, categories, mode="static", fail_fast=False)
        require(summary["overall_status"] == STATUS_FAIL, summary)
        require(summary["required_passed_count"] == 1, summary)
        require(summary["required_failed_count"] == 1, summary)
        require(summary["optional_skipped_count"] == 1, summary)
        require(summary["first_failure"]["category"] == "fail_category", summary)

        category_statuses = {item["name"]: item["status"] for item in summary["categories"]}
        require(category_statuses["pass_category"] == STATUS_PASS, category_statuses)
        require(category_statuses["optional_skip_category"] == STATUS_SKIP, category_statuses)
        require(category_statuses["fail_category"] == STATUS_FAIL, category_statuses)

        text = format_summary_text(summary)
        require("overall_status: FAIL" in text, text)
        require("first_failure: category=fail_category" in text, text)
        require("fake-required-fail" in text, text)

        json_path = repo_root / "runtime" / "eval" / "summary.json"
        write_summary_json(summary, json_path)
        loaded = json.loads(json_path.read_text(encoding="utf-8"))
        require(loaded["schema_version"] == "relaylm.mvp_eval_runner.summary.v1", loaded)
        require(loaded["categories"][0]["commands"][0]["failure_reason_id"] == "none", loaded)

        filtered = filter_categories(categories, ["pass_category"])
        require(len(filtered) == 1 and filtered[0].name == "pass_category", filtered)
        try:
            filter_categories(categories, ["missing_category"])
        except ValueError:
            pass
        else:
            raise AssertionError("unknown category must fail closed")

        listing = format_category_list(filtered, mode="static")
        require("pass_category" in listing and "fake-pass" in listing, listing)

        runner_path = Path(__file__).with_name("relaylm_mvp_eval_runner.py")
        list_result = subprocess.run(
            [sys.executable, str(runner_path), "--mode", "static", "--list", "--category", "preflight"],
            check=False,
            capture_output=True,
            text=True,
        )
        require(list_result.returncode == 0, list_result.stderr or list_result.stdout)
        require("internal:static-preflight" in list_result.stdout, list_result.stdout)

    print("RelayLM MVP eval runner smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
