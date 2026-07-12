#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "docs/mvp/wave7/e1r3_completion_report.md"
NEW = "docs/evidence/implementation/e1r3_completion_report.md"
SNAP = "docs/evidence/implementation/e1r3_completion_report-source.txt"
RECEIPT = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
SOURCE_BLOB = "40ceeaa4a7eca7e90cafcfb522cc8340ab31e40a"
SOURCE_COMMIT = "f92190f7990a990ccee914a6a6be18bab5e07331"
SOURCE_ORIGIN_COMMIT = "7bb2525cb000e893146408065f1aa5976f2b54ab"
SOURCE_PR = 436
RECORDED_ON = "2026-06-28"
CUTOVER_PR = 574
PREVIOUS_MERGE = "bd6effac133c04fb9132135360685c24edd6d2a0"


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


source_path = ROOT / OLD
source_bytes = source_path.read_bytes()
source_text = source_bytes.decode("utf-8")
source_sha256 = hashlib.sha256(source_bytes).hexdigest()
if git("hash-object", OLD) != SOURCE_BLOB:
    raise AssertionError("source Git blob mismatch")

snapshot_path = ROOT / SNAP
snapshot_path.parent.mkdir(parents=True, exist_ok=True)
snapshot_path.write_bytes(source_bytes)
if git("hash-object", SNAP) != SOURCE_BLOB:
    raise AssertionError("exact source snapshot blob mismatch")

if not source_text.startswith("---\n"):
    raise AssertionError("source report must start with YAML front matter")
front_matter_end = source_text.find("\n---\n", 4)
if front_matter_end < 0:
    raise AssertionError("source report front matter terminator missing")
body = source_text[front_matter_end + len("\n---\n"):]
title = "# E1-R3 Provenance-Preserving Primary MEM Formation Summary Completion Report"
if not body.startswith(title):
    raise AssertionError("source report title mismatch")
body = body.replace(OLD, NEW)
shared_heading = "## Shared documentation update inputs\n"
if body.count(shared_heading) != 1:
    raise AssertionError("shared documentation heading mismatch")
body = body.replace(shared_heading, shared_heading + "\nAt source PR #436:\n", 1)
status = f'''\n\n## Status and authority\n\nThis document is frozen implementation evidence for the E1-R3 provenance-preserving formation-summary slice introduced by PR #436, whose final source head is `{SOURCE_COMMIT}` and merge commit is `{SOURCE_ORIGIN_COMMIT}`. Current repository status belongs to [Project Status](../../PROJECT_STATUS.md). Current E1-R3 behavior belongs to [E1-R3 Provenance-Preserving Primary MEM Formation Summary](../../architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md), while cross-slice E1 evidence belongs to [E1 Evaluation Consolidation](../../architecture/e1_evaluation_consolidation.md).\n\nThe exact pre-cutover report is retained byte-for-byte as [e1r3_completion_report-source.txt](e1r3_completion_report-source.txt). Statements below describe the source PR boundary unless explicitly qualified.\n'''
body = title + status + body[len(title):]
header = f'''---
relaylm_doc_type: implementation_completion_report
relaylm_authority: e1r3_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: evaluation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md
  - ../../architecture/e1_evaluation_consolidation.md
  - ../../architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current E1-R3 or RelayMEM formation behavior
  - cross-slice sequencing or release readiness
  - repeatable operator procedure
relaylm_source_commit: {SOURCE_COMMIT}
relaylm_source_origin_commit: {SOURCE_ORIGIN_COMMIT}
relaylm_source_pr: {SOURCE_PR}
relaylm_recorded_on: {RECORDED_ON}
relaylm_source_blob: {SOURCE_BLOB}
relaylm_source_content_sha256: {source_sha256}
relaylm_exact_source_snapshot: e1r3_completion_report-source.txt
---
'''
write(NEW, header + body)

replace(
    "docs/README.md",
    "(mvp/wave7/e1r3_completion_report.md)",
    "(evidence/implementation/e1r3_completion_report.md)",
)
replace(
    "docs/mvp/README.md",
    "(wave7/e1r3_completion_report.md)",
    "(../evidence/implementation/e1r3_completion_report.md)",
)
replace("docs/mvp/README.md", OLD, NEW)
replace(
    "docs/architecture/README.md",
    "../mvp/wave7/e1r3_completion_report.md",
    "../evidence/implementation/e1r3_completion_report.md",
)
replace("docs/architecture/e1_evaluation_consolidation.md", OLD, NEW)
replace("scripts/relaylm_e1_evaluation_consolidation_smoke.py", OLD, NEW)
replace(
    "docs/evidence/waves/wave7_cross_slice_convergence_audit.md",
    "../../mvp/wave7/e1r3_completion_report.md",
    "../implementation/e1r3_completion_report.md",
)

implementation_index = read("docs/evidence/implementation/README.md")
index_entry = (
    "- [E1-R3 completion report](e1r3_completion_report.md) — frozen provenance-preserving "
    "formation-summary implementation evidence from PR #436; current behavior remains architecture-owned.\n"
)
if index_entry not in implementation_index:
    implementation_index = implementation_index.rstrip() + "\n" + index_entry
write("docs/evidence/implementation/README.md", implementation_index)

boundary = read("scripts/relaylm_documentation_current_boundary_smoke.py")
list_anchor = '        "source PR #436, merge `7bb2525cb000e893146408065f1aa5976f2b54ab`",\n'
list_entry = f'        "{NEW}",\n'
if boundary.count(list_anchor) != 1:
    raise AssertionError("current-boundary E1-R3 list anchor mismatch")
if list_entry not in boundary:
    boundary = boundary.replace(list_anchor, list_anchor + list_entry, 1)
map_anchor = '''    "docs/evidence/implementation/lat1_latency_measurement_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "LAT-1 Latency Measurement Completion Report",
        "PR: #505",
        "Current timing schema and measurement behavior belong to",
        "At source PR #505:",
    ),
'''
map_entry = f'''    "{NEW}": (
        "relaylm_doc_type: implementation_completion_report",
        "E1-R3 Provenance-Preserving Primary MEM Formation Summary Completion Report",
        "PR: #436",
        "Current E1-R3 behavior belongs to",
        "At source PR #436:",
    ),
'''
if boundary.count(map_anchor) != 1:
    raise AssertionError("current-boundary canonical report map anchor mismatch")
if map_entry not in boundary:
    boundary = boundary.replace(map_anchor, map_anchor + map_entry, 1)
write("scripts/relaylm_documentation_current_boundary_smoke.py", boundary)

receipt = read(RECEIPT)
previous_marker = "### C1C15-001 — LAT-1 Latency Measurement completion report"
previous_start = receipt.index(previous_marker)
pending_pos = receipt.index("merged_commit: pending", previous_start)
receipt = receipt[:pending_pos] + f"merged_commit: {PREVIOUS_MERGE}" + receipt[pending_pos + len("merged_commit: pending"):]
previous_tail = "The old path above is only the historical migration identifier for this receipt."
previous_tail_pos = receipt.index(previous_tail, previous_start)
previous_replacement = f"PR #573 merged as `{PREVIOUS_MERGE}`; C1C15 is finalized by Cutover 1C-16."
receipt = receipt[:previous_tail_pos] + previous_replacement + receipt[previous_tail_pos + len(previous_tail):]
entry = f'''### C1C16-001 — E1-R3 completion report

```yaml
cutover_pr: {CUTOVER_PR}
merged_commit: pending
old_path: {OLD}
old_blob_sha: {SOURCE_BLOB}
old_content_sha256: {source_sha256}
source_commit: {SOURCE_COMMIT}
source_origin_commit: {SOURCE_ORIGIN_COMMIT}
source_pr: {SOURCE_PR}
recorded_on: {RECORDED_ON}
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
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  wave7_convergence_evidence_link_updated: true
  e1_evaluation_consolidation_updated: true
  e1_evaluation_smoke_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1r3_smokes: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the complete E1-R3 provenance-preserving formation-summary implementation boundary while separating it from current architecture-owned behavior and cross-slice E1 evaluation authority. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified three repository-root references across three files, four Markdown links across four router/evidence files, one Wave 7 convergence-evidence link, and the dedicated E1 consolidation smoke path. The migration-aware completion-report model and PR-link checks apply without further validator changes. The old path above is only the historical migration identifier for this receipt.

'''
anchor = "## Pending batches"
if "### C1C16-001" in receipt:
    raise AssertionError("C1C16 receipt already exists")
receipt = receipt.replace(anchor, entry + anchor, 1)
write(RECEIPT, receipt)

source_path.unlink()

hits = subprocess.run(
    ["git", "grep", "-n", "--", OLD],
    cwd=ROOT,
    text=True,
    capture_output=True,
    check=False,
).stdout.splitlines()
for hit in hits:
    path = hit.split(":", 1)[0]
    if path not in {SNAP, RECEIPT, ".github/scripts/docs_cutover_1c16.py"}:
        raise AssertionError(f"unexpected old-path occurrence after cutover: {hit}")
if git("hash-object", SNAP) != SOURCE_BLOB:
    raise AssertionError("snapshot blob changed during cutover")

print(f"Cutover 1C-16 applicator completed; source_sha256={source_sha256}")
