#!/usr/bin/env python3
"""Require each completion report PR URL to match its PR number."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for report in sorted((ROOT / "docs" / "mvp").glob("wave*/*_completion_report.md")):
    lines = report.read_text(encoding="utf-8").splitlines()
    pr_lines = [line for line in lines if line.startswith("- PR: #")]
    url_lines = [line for line in lines if line.startswith("- URL: https://github.com/")]
    assert len(pr_lines) == 1, f"{report}: one PR line required"
    assert len(url_lines) == 1, f"{report}: one URL line required"
    pr_number = pr_lines[0].split("#", 1)[1].strip()
    assert pr_number.isdigit() and not pr_number.startswith("0"), f"{report}: invalid PR"
    assert "rinsakamo/relay-lm/pull/" in url_lines[0], f"{report}: wrong repository"
    assert url_lines[0].endswith("/" + pr_number), f"{report}: PR URL mismatch"

print("RelayLM completion report PR link smoke passed")
