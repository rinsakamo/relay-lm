#!/usr/bin/env python3
from pathlib import Path

path = Path("docs/evidence/migrations/documentation-hard-cutover-receipt.md")
body = path.read_text(encoding="utf-8")
start = body.index("### C1C22-001 — E1-R1 completion report")
end = body.index("## Pending batches", start)
section = body[start:end]
old = "  all_github_actions: pending"
new = "  all_github_actions: passed"
assert section.count(old) == 1, section.count(old)
section = section.replace(old, new, 1)
body = body[:start] + section + body[end:]
path.write_text(body, encoding="utf-8")
