#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "docs/mvp/wave8/lat1_latency_measurement_completion_report.md"
NEW = "docs/evidence/implementation/lat1_latency_measurement_completion_report.md"
SNAP = "docs/evidence/implementation/lat1_latency_measurement_completion_report-source.txt"
RECEIPT = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
SOURCE_BLOB = "0bf5743b7ba0ac85e657bb06ae88b8f1d41b3936"
SOURCE_COMMIT = "85817a391e27492cd139bd75929a60e1065a1454"
SOURCE_ORIGIN_COMMIT = "c77cf8e37a3f52c67c523004cf2a37b4c28f62f8"
SOURCE_PR = 505
CUTOVER_PR = 573
PREVIOUS_MERGE = "4c0e7d64110c9e2df37398ee0cda4678d4143e1c"


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
if git("hash-object", OLD) != SOURCE_BLOB:
    raise AssertionError("source Git blob mismatch")
source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
write(SNAP, source)
if git("hash-object", SNAP) != SOURCE_BLOB:
    raise AssertionError("exact source snapshot blob mismatch")

if not source.startswith("---\n"):
    raise AssertionError("source front matter missing")
_, _legacy_frontmatter, body = source.split("---\n", 2)
body = body.lstrip("\n")
title = "# LAT-1 Latency Measurement Completion Report"
if not body.startswith(title + "\n"):
    raise AssertionError("source title mismatch")
body = body[len(title):].lstrip("\n")
if body.count(OLD) != 2:
    raise AssertionError("source body old-path count mismatch")
body = body.replace(OLD, NEW)
shared_heading = "## Shared documentation update inputs\n\n"
if body.count(shared_heading) != 1:
    raise AssertionError("shared documentation heading mismatch")
body = body.replace(shared_heading, shared_heading + "At source PR #505:\n\n", 1)

canonical = f'''---
relaylm_doc_type: implementation_completion_report
relaylm_authority: lat1_latency_measurement_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current LAT-1 timing or bench behavior
  - current retrieval-scaling results or optimization decisions
  - response-time guarantees, timeout, or degradation policy
  - repeatable operator procedure
relaylm_source_commit: {SOURCE_COMMIT}
relaylm_source_origin_commit: {SOURCE_ORIGIN_COMMIT}
relaylm_source_pr: {SOURCE_PR}
relaylm_recorded_on: 2026-07-07
relaylm_source_blob: {SOURCE_BLOB}
relaylm_source_content_sha256: {source_sha256}
relaylm_exact_source_snapshot: lat1_latency_measurement_completion_report-source.txt
---
{title}

## Status and authority

This document is frozen implementation evidence for the LAT-1 measurement slice introduced by PR #505, merged as `{SOURCE_ORIGIN_COMMIT}`, and last aligned to the extracted RelayRUN artifact-module boundary by `{SOURCE_COMMIT}`. Current repository status belongs to [Project Status](../../PROJECT_STATUS.md). Current timing schema and measurement behavior belong to [LAT-1 Latency Measurement](../../architecture/lat1_latency_measurement.md); current local retrieval-scaling observations belong to [LAT-1 Retrieval Scaling Report](../../evaluation/lat1_retrieval_scaling_report.md).

The exact pre-cutover report is retained byte-for-byte as [lat1_latency_measurement_completion_report-source.txt](lat1_latency_measurement_completion_report-source.txt). Statements below describe the source boundary unless explicitly qualified.

{body}'''
write(NEW, canonical)

replace(
    "docs/README.md",
    "(mvp/wave8/lat1_latency_measurement_completion_report.md)",
    "(evidence/implementation/lat1_latency_measurement_completion_report.md)",
)

mvp_readme = read("docs/mvp/README.md")
old_link = "(wave8/lat1_latency_measurement_completion_report.md)"
new_link = "(../evidence/implementation/lat1_latency_measurement_completion_report.md)"
if mvp_readme.count(old_link) != 1:
    raise AssertionError("docs/mvp/README.md LAT-1 link mismatch")
mvp_readme = mvp_readme.replace(old_link, new_link, 1)
if mvp_readme.count(OLD) != 1:
    raise AssertionError("docs/mvp/README.md LAT-1 validation path mismatch")
mvp_readme = mvp_readme.replace(OLD, NEW, 1)
write("docs/mvp/README.md", mvp_readme)

implementation_index = read("docs/evidence/implementation/README.md")
entry = (
    "- [LAT-1 Latency Measurement completion report]"
    "(lat1_latency_measurement_completion_report.md) — frozen measurement-implementation "
    "evidence from PR #505; current schema and results remain architecture/evaluation-owned.\n"
)
if entry not in implementation_index:
    implementation_index = implementation_index.rstrip() + "\n" + entry
write("docs/evidence/implementation/README.md", implementation_index)

boundary = read("scripts/relaylm_documentation_current_boundary_smoke.py")
if boundary.count(OLD) != 1:
    raise AssertionError("current-boundary LAT-1 path mismatch")
boundary = boundary.replace(OLD, NEW, 1)
map_anchor = '''    "docs/evidence/implementation/twin_extraction_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "Twin Extraction Tooling Completion Report",
        "PR: #503",
        "current execution and review-import behavior belongs to the",
        "At source PR #503:",
    ),
'''
map_entry = f'''    "{NEW}": (
        "relaylm_doc_type: implementation_completion_report",
        "LAT-1 Latency Measurement Completion Report",
        "PR: #505",
        "Current timing schema and measurement behavior belong to",
        "At source PR #505:",
    ),
'''
if boundary.count(map_anchor) != 1:
    raise AssertionError("current-boundary canonical evidence map anchor mismatch")
if map_entry not in boundary:
    boundary = boundary.replace(map_anchor, map_anchor + map_entry, 1)
write("scripts/relaylm_documentation_current_boundary_smoke.py", boundary)

receipt = read(RECEIPT)
c1c14_marker = "### C1C14-001 — Twin Extraction Tooling completion report"
start = receipt.index(c1c14_marker)
pending = receipt.index("merged_commit: pending", start)
receipt = receipt[:pending] + f"merged_commit: {PREVIOUS_MERGE}" + receipt[pending + len("merged_commit: pending"):]
old_tail = "The old path above is only the historical migration identifier for this receipt."
new_tail = f"PR #572 merged as `{PREVIOUS_MERGE}`; C1C14 is finalized by Cutover 1C-15."
tail_pos = receipt.index(old_tail, start)
receipt = receipt[:tail_pos] + new_tail + receipt[tail_pos + len(old_tail):]
entry = f'''### C1C15-001 — LAT-1 Latency Measurement completion report

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
  repository_root_literal_reference_files_updated_in_pr_tree: 2
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 2
  relative_markdown_link_referrer_files_at_frozen_baseline: 2
  relative_markdown_link_dependencies_at_frozen_baseline: 2
  implementation_evidence_index_updated: true
  lat1_architecture_and_evaluation_authorities_preserved: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_lat1_smokes: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the complete LAT-1 timing and offline retrieval-bench implementation boundary while separating it from current architecture-owned measurement behavior and evaluation-owned local scaling results. The exact pre-cutover source is retained as the final Git blob and byte-for-byte snapshot. The dependency sweep identified two repository-root path references across two files, two Markdown links across two router files, and one current-boundary canonical evidence-map addition. The migration-aware completion-report model and PR-link checks apply without further validator changes. The old path above is only the historical migration identifier for this receipt.

'''
anchor = "## Pending batches"
if "### C1C15-001" in receipt:
    raise AssertionError("C1C15 receipt already exists")
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
    if path not in {SNAP, RECEIPT, ".github/scripts/docs_cutover_1c15.py"}:
        raise AssertionError(f"unexpected old-path occurrence after cutover: {hit}")

if git("hash-object", SNAP) != SOURCE_BLOB:
    raise AssertionError("snapshot blob changed during cutover")

print(source_sha256)
print("Cutover 1C-15 applicator completed")
