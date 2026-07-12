#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "docs/mvp/wave8/twin_extraction_completion_report.md"
NEW = "docs/evidence/implementation/twin_extraction_completion_report.md"
SNAP = "docs/evidence/implementation/twin_extraction_completion_report-source.txt"
RECEIPT = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
SOURCE_BLOB = "c0b71f940cebf4b6de2f912870a1be7e14c90b60"
SOURCE_COMMIT = "fc7e77ef52f137c2a9224b20dff1e8e4711ba0f3"
SOURCE_ORIGIN_COMMIT = "2e484f9aea04425285e9c5ce690b38a8beb87e82"
SOURCE_PR = 503
CUTOVER_PR = 572
PREVIOUS_MERGE = "2d9fc3aa26145cf80cdbfa5d2ccb84261d7d963e"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, body: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def replace(path: str, old: str, new: str, expected: int = 1) -> None:
    body = read(path)
    count = body.count(old)
    if count != expected:
        raise AssertionError(f"{path}: expected {expected} occurrences, found {count}: {old!r}")
    write(path, body.replace(old, new))


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


source = read(OLD)
snapshot = read(SNAP)
if source != snapshot:
    raise AssertionError("exact source snapshot does not match the pre-cutover source")
if git("hash-object", OLD) != SOURCE_BLOB or git("hash-object", SNAP) != SOURCE_BLOB:
    raise AssertionError("source Git blob mismatch")
source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()

source_body = source.split("# Twin Extraction Tooling Completion Report\n", 1)[1]
source_body = source_body.replace(OLD, NEW)
source_body = source_body.replace(
    "## Shared documentation update inputs\n\n",
    "## Shared documentation update inputs\n\nAt source PR #503:\n\n",
    1,
)
canonical = f'''---
relaylm_doc_type: implementation_completion_report
relaylm_authority: twin_extraction_tooling_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: offline_tooling
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current Twin Extraction or review-import behavior
  - MEM/SOUL bootstrap or RelaySLP runtime behavior
  - repeatable operator procedure
relaylm_source_commit: {SOURCE_COMMIT}
relaylm_source_origin_commit: {SOURCE_ORIGIN_COMMIT}
relaylm_source_pr: {SOURCE_PR}
relaylm_recorded_on: 2026-07-07
relaylm_source_blob: {SOURCE_BLOB}
relaylm_source_content_sha256: {source_sha256}
relaylm_exact_source_snapshot: twin_extraction_completion_report-source.txt
---
# Twin Extraction Tooling Completion Report

## Status and authority

This document is frozen implementation evidence for the offline Twin Extraction tooling introduced by PR #503, merged as `{SOURCE_ORIGIN_COMMIT}`, and last textually corrected by `{SOURCE_COMMIT}`. Current repository status belongs to [Project Status](../../PROJECT_STATUS.md); current execution and review-import behavior belongs to the [Twin Extraction runbook](../../tools/twin_extraction_runbook.md).

The exact pre-cutover report is retained byte-for-byte as [twin_extraction_completion_report-source.txt](twin_extraction_completion_report-source.txt). Statements below describe the source boundary unless explicitly qualified.

{source_body}'''
write(NEW, canonical)

replace(
    "docs/README.md",
    "(mvp/wave8/twin_extraction_completion_report.md)",
    "(evidence/implementation/twin_extraction_completion_report.md)",
)

mvp_readme = read("docs/mvp/README.md")
old_link = "(wave8/twin_extraction_completion_report.md)"
new_link = "(../evidence/implementation/twin_extraction_completion_report.md)"
if mvp_readme.count(old_link) != 1:
    raise AssertionError("docs/mvp/README.md: Twin Extraction link anchor mismatch")
mvp_readme = mvp_readme.replace(old_link, new_link, 1)
if mvp_readme.count(OLD) != 1:
    raise AssertionError("docs/mvp/README.md: Twin Extraction validation anchor mismatch")
mvp_readme = mvp_readme.replace(OLD, NEW, 1)
write("docs/mvp/README.md", mvp_readme)

replace("docs/tools/twin_extraction_runbook.md", OLD, NEW, 1)
replace("scripts/relaylm_documentation_current_boundary_smoke.py", OLD, NEW, 1)

implementation_index = read("docs/evidence/implementation/README.md")
entry = (
    "- [Twin Extraction Tooling completion report](twin_extraction_completion_report.md) — "
    "frozen offline-tooling implementation evidence from PR #503; current operation remains runbook-owned.\n"
)
if entry not in implementation_index:
    implementation_index = implementation_index.rstrip() + "\n" + entry
write("docs/evidence/implementation/README.md", implementation_index)

boundary = read("scripts/relaylm_documentation_current_boundary_smoke.py")
map_anchor = '''    "docs/evidence/implementation/e2_value_smoke_harness_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "E2 Value Smoke Harness Completion Report",
        "PR: #481",
        "later durable-memory E2 human review and release-readiness conclusion",
        "does not retroactively turn this harness implementation report into a quality-evaluation record",
    ),
'''
map_entry = f'''    "{NEW}": (
        "relaylm_doc_type: implementation_completion_report",
        "Twin Extraction Tooling Completion Report",
        "PR: #503",
        "current execution and review-import behavior belongs to the",
        "At source PR #503:",
    ),
'''
if boundary.count(map_anchor) != 1:
    raise AssertionError("current-boundary canonical evidence map anchor mismatch")
if map_entry not in boundary:
    boundary = boundary.replace(map_anchor, map_anchor + map_entry, 1)
write("scripts/relaylm_documentation_current_boundary_smoke.py", boundary)

receipt = read(RECEIPT)
c1c13_marker = "### C1C13-001 — E2 Value Smoke Harness completion report"
start = receipt.index(c1c13_marker)
pending = receipt.index("merged_commit: pending", start)
receipt = receipt[:pending] + f"merged_commit: {PREVIOUS_MERGE}" + receipt[pending + len("merged_commit: pending"):]
old_tail = "The old path above is only the historical migration identifier for this receipt."
new_tail = f"PR #571 merged as `{PREVIOUS_MERGE}`; C1C13 is finalized by Cutover 1C-14."
tail_pos = receipt.index(old_tail, start)
receipt = receipt[:tail_pos] + new_tail + receipt[tail_pos + len(old_tail):]
entry = f'''### C1C14-001 — Twin Extraction Tooling completion report

```yaml
cutover_pr: {CUTOVER_PR}
merged_commit: pending
old_path: {OLD}
old_blob_sha: {SOURCE_BLOB}
old_content_sha256: {source_sha256}
source_commit: {SOURCE_COMMIT}
source_origin_commit: {SOURCE_ORIGIN_COMMIT}
source_pr: {SOURCE_PR}
recorded_on: 2026-07-07
disposition: evidence_retained
new_canonical_path: {NEW}
exact_source_snapshot: {SNAP}
exact_source_blob_sha: {SOURCE_BLOB}
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 3
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 3
  relative_markdown_link_referrer_files_at_frozen_baseline: 2
  relative_markdown_link_dependencies_at_frozen_baseline: 2
  implementation_evidence_index_updated: true
  twin_extraction_runbook_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_twin_extraction_smokes: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the complete offline Twin Extraction implementation boundary while separating it from current runbook-owned operation and later review-import bridge evolution. The exact pre-cutover source is retained as the final Git blob and byte-for-byte snapshot. The dependency sweep identified three repository-root path occurrences across three files, two Markdown links across two router files, and one current-boundary canonical evidence-map addition. The migration-aware completion-report model and PR-link checks apply without further validator changes. The old path above is only the historical migration identifier for this receipt.

'''
anchor = "## Pending batches"
if "### C1C14-001" in receipt:
    raise AssertionError("C1C14 receipt already exists")
receipt = receipt.replace(anchor, entry + anchor, 1)
write(RECEIPT, receipt)

(ROOT / OLD).unlink()

hits = subprocess.run(
    ["git", "grep", "-n", "--", OLD],
    cwd=ROOT,
    text=True,
    capture_output=True,
    check=False,
).stdout.splitlines()
for hit in hits:
    path = hit.split(":", 1)[0]
    if path not in {SNAP, RECEIPT, ".github/scripts/docs_cutover_1c14.py"}:
        raise AssertionError(f"unexpected old-path occurrence after cutover: {hit}")

if git("hash-object", SNAP) != SOURCE_BLOB:
    raise AssertionError("snapshot blob changed during cutover")

print(source_sha256)
print("Cutover 1C-14 applicator completed")
