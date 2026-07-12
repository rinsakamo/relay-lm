#!/usr/bin/env python3
from pathlib import Path

path = Path("docs/evidence/migrations/documentation-hard-cutover-receipt.md")
body = path.read_text(encoding="utf-8")
start = body.index("### C1C21-001 — I-7C completion report")
end = body.index("## Pending batches", start)
section = body[start:end]
old = "  all_github_actions: pending"
new = "  all_github_actions: passed"
if section.count(old) != 1:
    raise AssertionError(f"C1C21 all_github_actions marker mismatch: {section.count(old)}")
for required in (
    "  focused_i7ab_i7c_smokes: passed",
    "  related_i4d_o1e_b3_regressions: passed",
    "  soul_lab_held_governance_ui_validation: passed",
    "  documentation_link_check: passed",
    "  documentation_semantic_audit: passed",
    "  completion_report_model_and_file_checks: passed",
    "  completion_report_pr_link_check: passed",
    "  unresolved_review_threads: 0",
):
    if required not in section:
        raise AssertionError(f"missing finalized C1C21 field: {required}")
section = section.replace(old, new, 1)
body = body[:start] + section + body[end:]
path.write_text(body, encoding="utf-8")
print("C1C21 receipt finalized")
