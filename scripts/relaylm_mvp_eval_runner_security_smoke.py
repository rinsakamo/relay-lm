#!/usr/bin/env python3
"""Security smoke for content-free MVP eval runner public summaries."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from relaylm_mvp_eval_runner import CategorySpec, CommandSpec, format_summary_text, run_categories, write_summary_json

PRIVATE_CANARIES = (
    "USER_MEMORY_CANARY_blue_lighthouse",
    "PRIVATE_SOURCE_BODY_CANARY",
    "MODEL_OUTPUT_BODY_CANARY",
    "dispatch-1234567890abcdef",
    "job-abcdef1234567890",
    "opaque-runtime-secret-a",
    "opaque-runtime-secret-b",
    "RawExceptionSecret",
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        absolute_path_canary = str(repo_root / "runtime" / "memory" / "secret.json")
        emitted = " ".join((*PRIVATE_CANARIES, absolute_path_canary))
        code = "import sys; print(%r); print(%r, file=sys.stderr); raise SystemExit(9)" % (emitted, emitted)
        categories = (
            CategorySpec(
                name="security_category",
                required=True,
                commands=(CommandSpec(name="fake-private-output-command", argv=(sys.executable, "-c", code), required=True),),
            ),
        )
        summary = run_categories(repo_root, categories, mode="static", fail_fast=False)
        public_text = format_summary_text(summary)
        public_json = json.dumps(summary, sort_keys=True)
        json_path = repo_root / "runtime" / "eval" / "summary.json"
        write_summary_json(summary, json_path)
        persisted_json = json_path.read_text(encoding="utf-8")
        combined_public = "\n".join((public_text, public_json, persisted_json))
        for canary in (*PRIVATE_CANARIES, absolute_path_canary):
            require(canary not in combined_public, canary)
        require("exit_nonzero" in combined_public, combined_public)
        require("fake-private-output-command" in combined_public, combined_public)
        require("USER_MEMORY_CANARY" not in combined_public, combined_public)
    print("RelayLM MVP eval runner security smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
