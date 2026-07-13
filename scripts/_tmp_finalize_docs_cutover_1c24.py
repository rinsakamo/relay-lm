#!/usr/bin/env python3
"""Finalize the Cutover 1C-24 GitHub Actions receipt field."""
from pathlib import Path

path = Path("docs/evidence/migrations/documentation-hard-cutover-receipt.md")
text = path.read_text(encoding="utf-8")
heading = "### C1C24-001 — docs horizontal status sweep completion report\n"
start = text.index(heading)
end = text.index("\n## Pending batches\n", start)
block = text[start:end]
old = "  all_github_actions: pending\n"
if block.count(old) != 1:
    raise SystemExit("C1C24 all_github_actions anchor mismatch")
block = block.replace(old, "  all_github_actions: passed\n", 1)
path.write_text(text[:start] + block + text[end:], encoding="utf-8")
