#!/usr/bin/env python3
"""Run the frozen v0.1 final validation checklist against an exact repository commit.

The runner records content-free command evidence: return codes, output digests,
line counts, and environment metadata. It never writes raw validation output to
the committed receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COMMANDS: list[tuple[str, list[str]]] = [
    ("compileall", [sys.executable, "-m", "compileall", "-q", "relaylm", "scripts"]),
    (
        "documentation-current-boundary",
        [sys.executable, "scripts/relaylm_documentation_current_boundary_smoke.py"],
    ),
    ("documentation-links", [sys.executable, "scripts/relaylm_docs_link_check.py"]),
    (
        "e2-value-smoke-scenarios",
        [sys.executable, "scripts/relaylm_e2_value_smoke_scenarios_smoke.py"],
    ),
    (
        "o2-supervised-scheduler-service",
        [sys.executable, "scripts/relaylm_o2_supervised_scheduler_service_smoke.py"],
    ),
    (
        "o3-always-on-local-scheduler",
        [sys.executable, "scripts/relaylm_o3_always_on_local_scheduler_smoke.py"],
    ),
]


def run_git(repo_dir: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def execute(repo_dir: Path, name: str, command: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = datetime.now(timezone.utc)
    result = subprocess.run(
        command,
        cwd=repo_dir,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    completed = datetime.now(timezone.utc)
    stdout = result.stdout.replace("\r\n", "\n").replace("\r", "\n")
    stderr = result.stderr.replace("\r\n", "\n").replace("\r", "\n")
    return {
        "name": name,
        "command": command,
        "status": "pass" if result.returncode == 0 else "fail",
        "return_code": result.returncode,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": completed.isoformat(),
        "stdout_sha256": digest(stdout),
        "stderr_sha256": digest(stderr),
        "stdout_line_count": len(stdout.splitlines()),
        "stderr_line_count": len(stderr.splitlines()),
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# v0.1 Final Main-HEAD Validation",
        "",
        f"- Validated commit: `{payload['validated_commit']}`",
        f"- Commit date: `{payload['validated_commit_date']}`",
        f"- Executed at: `{payload['executed_at_utc']}`",
        f"- Environment: `{payload['environment']['platform']}`",
        f"- Python: `{payload['environment']['python']}`",
        f"- Overall result: **{payload['overall_result'].upper()}**",
        "",
        "| Check | Result | Return code | stdout SHA-256 | stderr SHA-256 |",
        "|---|---|---:|---|---|",
    ]
    for result in payload["results"]:
        lines.append(
            f"| `{result['name']}` | **{result['status']}** | {result['return_code']} | "
            f"`{result['stdout_sha256']}` | `{result['stderr_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "Raw command output is intentionally not embedded in the receipt artifact. The hashes and line counts provide content-free evidence while the workflow logs retain execution diagnostics.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", type=Path, required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    repo_dir = args.repo_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not repo_dir.is_dir():
        print(f"error: repo directory does not exist: {repo_dir}", file=sys.stderr)
        return 2

    try:
        actual = run_git(repo_dir, "rev-parse", "HEAD")
        if actual != args.baseline:
            raise RuntimeError(f"worktree HEAD {actual} does not match baseline {args.baseline}")
        commit_date = run_git(repo_dir, "show", "-s", "--format=%cI", args.baseline)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    results = [execute(repo_dir, name, command) for name, command in COMMANDS]
    overall = "pass" if all(result["status"] == "pass" for result in results) else "fail"
    payload = {
        "schema": "relaylm.v01_final_validation.v1",
        "validated_commit": args.baseline,
        "validated_commit_date": commit_date,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.replace("\n", " "),
            "node": "not applicable to the required checklist",
        },
        "overall_result": overall,
        "results": results,
    }
    (output_dir / "validation-results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "validation-summary.md").write_text(markdown(payload), encoding="utf-8")
    print(markdown(payload))
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
