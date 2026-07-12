#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "docs/mvp/wave7/e1r4_completion_report.md"
NEW = "docs/evidence/implementation/e1r4_completion_report.md"
SNAP = "docs/evidence/implementation/e1r4_completion_report-source.txt"
RECEIPT = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
SOURCE_BLOB = "ea940e524c7c99173108c8088a3435485bd3736a"
SOURCE_COMMIT = "cad2fc03c3a6e566de60684e6628b75a0e70eae8"
SOURCE_MERGE = "e6e5b32cd489dda493ff0171a260dd561a91765c"
SOURCE_PR = 437
CUTOVER_PR = 575
PREVIOUS_MERGE = "c9e440cb44f4a1e95dac68caeabfefb872779ca6"


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
    raise AssertionError("exact source snapshot Git blob mismatch")

parts = source_text.split("---\n", 2)
if len(parts) != 3 or parts[0] != "":
    raise AssertionError("unexpected source front matter shape")
body = parts[2]
body = body.replace(OLD, NEW)
title = "# E1-R4 Completion Report\n"
status = f'''{title}
## Status and authority

This document is frozen implementation evidence for the E1-R4 retrieval-response grounding slice introduced by PR #{SOURCE_PR}, whose final source head is `{SOURCE_COMMIT}` and merge commit is `{SOURCE_MERGE}`. Current repository status belongs to [Project Status](../../PROJECT_STATUS.md). Current E1-R4 behavior belongs to [E1-R4 Retrieval-Response Grounding](../../architecture/e1r4_retrieval_response_grounding.md), while cross-slice E1 evidence belongs to [E1 Evaluation Consolidation](../../architecture/e1_evaluation_consolidation.md).

The exact pre-cutover report is retained byte-for-byte as [e1r4_completion_report-source.txt](e1r4_completion_report-source.txt). Statements below describe the source PR boundary unless explicitly qualified.

'''
if body.count(title + "\n") != 1:
    raise AssertionError("E1-R4 title anchor mismatch")
body = body.replace(title + "\n", status, 1)
shared_anchor = "## Shared documentation update inputs\n\nCompletion wording:"
if body.count(shared_anchor) != 1:
    raise AssertionError("E1-R4 shared-doc anchor mismatch")
body = body.replace(
    shared_anchor,
    "## Shared documentation update inputs\n\nAt source PR #437:\n\nCompletion wording:",
    1,
)
metadata = f'''---
relaylm_doc_type: implementation_completion_report
relaylm_authority: e1r4_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/e1r4_retrieval_response_grounding.md
  - ../../architecture/e1_evaluation_consolidation.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current E1-R4 or grounded-recall behavior
  - cross-slice sequencing or release readiness
  - repeatable operator procedure
relaylm_source_commit: {SOURCE_COMMIT}
relaylm_source_origin_commit: {SOURCE_MERGE}
relaylm_source_pr: {SOURCE_PR}
relaylm_recorded_on: 2026-06-28
relaylm_source_blob: {SOURCE_BLOB}
relaylm_source_content_sha256: {source_sha256}
relaylm_exact_source_snapshot: e1r4_completion_report-source.txt
---
'''
write(NEW, metadata + body)

replace(
    "docs/README.md",
    "(mvp/wave7/e1r4_completion_report.md)",
    "(evidence/implementation/e1r4_completion_report.md)",
)
replace(
    "docs/architecture/README.md",
    "(../mvp/wave7/e1r4_completion_report.md)",
    "(../evidence/implementation/e1r4_completion_report.md)",
)
replace(
    "docs/evidence/waves/wave7_cross_slice_convergence_audit.md",
    "(../../mvp/wave7/e1r4_completion_report.md)",
    "(../implementation/e1r4_completion_report.md)",
)
replace("docs/architecture/e1_evaluation_consolidation.md", OLD, NEW)
replace("scripts/relaylm_e1_evaluation_consolidation_smoke.py", OLD, NEW)

mvp_readme = read("docs/mvp/README.md")
old_link = "(wave7/e1r4_completion_report.md)"
new_link = "(../evidence/implementation/e1r4_completion_report.md)"
if mvp_readme.count(old_link) != 1 or mvp_readme.count(OLD) != 1:
    raise AssertionError("docs/mvp/README.md E1-R4 dependency anchors mismatch")
mvp_readme = mvp_readme.replace(old_link, new_link, 1).replace(OLD, NEW, 1)
write("docs/mvp/README.md", mvp_readme)

implementation_index = read("docs/evidence/implementation/README.md")
entry = (
    "- [E1-R4 completion report](e1r4_completion_report.md) — frozen retrieval-response grounding "
    "implementation evidence from PR #437; current behavior remains architecture-owned.\n"
)
if entry not in implementation_index:
    implementation_index = implementation_index.rstrip() + "\n" + entry
write("docs/evidence/implementation/README.md", implementation_index)

boundary_path = "scripts/relaylm_documentation_current_boundary_smoke.py"
boundary = read(boundary_path)
source_pr_anchor = '        "source PR #437, merge `e6e5b32cd489dda493ff0171a260dd561a91765c`",\n'
canonical_token = f'        "{NEW}",\n'
if boundary.count(source_pr_anchor) != 1:
    raise AssertionError("current-boundary E1-R4 PR anchor mismatch")
if canonical_token not in boundary:
    boundary = boundary.replace(source_pr_anchor, source_pr_anchor + canonical_token, 1)
old_map = '''    "docs/mvp/wave7/e1r4_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "retrieval-response grounding and unsupported-detail suppression",
        "Request-side vs response-side decision",
        "Content leakage review",
        "Authority preservation",
    ),
'''
new_map = f'''    "{NEW}": (
        "relaylm_doc_type: implementation_completion_report",
        "E1-R4 Completion Report",
        "PR: #437",
        "Current E1-R4 behavior belongs to",
        "Request-side vs response-side decision",
        "Content leakage review",
        "Authority preservation",
        "At source PR #437:",
    ),
'''
if boundary.count(old_map) != 1:
    raise AssertionError("current-boundary E1-R4 evidence map mismatch")
boundary = boundary.replace(old_map, new_map, 1)
write(boundary_path, boundary)

receipt = read(RECEIPT)
previous_marker = "### C1C16-001 — E1-R3 completion report"
previous_start = receipt.index(previous_marker)
pending = receipt.index("merged_commit: pending", previous_start)
receipt = receipt[:pending] + f"merged_commit: {PREVIOUS_MERGE}" + receipt[pending + len("merged_commit: pending"):]
pending_batches = receipt.index("## Pending batches", previous_start)
old_tail = "The old path above is only the historical migration identifier for this receipt."
tail_pos = receipt.rfind(old_tail, previous_start, pending_batches)
if tail_pos < 0:
    raise AssertionError("C1C16 receipt tail anchor missing")
new_tail = f"PR #574 merged as `{PREVIOUS_MERGE}`; C1C16 is finalized by Cutover 1C-17."
receipt = receipt[:tail_pos] + new_tail + receipt[tail_pos + len(old_tail):]
entry = f'''### C1C17-001 — E1-R4 completion report

```yaml
cutover_pr: {CUTOVER_PR}
merged_commit: pending
old_path: {OLD}
old_blob_sha: {SOURCE_BLOB}
old_content_sha256: {source_sha256}
source_commit: {SOURCE_COMMIT}
source_origin_commit: {SOURCE_MERGE}
source_pr: {SOURCE_PR}
recorded_on: 2026-06-28
disposition: evidence_retained
new_canonical_path: {NEW}
exact_source_snapshot: {SNAP}
exact_source_blob_sha: {SOURCE_BLOB}
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 4
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 4
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  wave7_convergence_evidence_link_updated: true
  e1_evaluation_consolidation_updated: true
  e1_evaluation_smoke_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1r4_smokes: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the complete E1-R4 retrieval-response grounding and unsupported-detail suppression implementation boundary while separating it from current architecture-owned behavior and cross-slice E1 evaluation authority. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified four repository-root references across four files, four Markdown links across four router/evidence files, one Wave 7 convergence-evidence link, and the dedicated E1 consolidation smoke path. The migration-aware completion-report model and PR-link checks apply without further validator changes. The old path above is only the historical migration identifier for this receipt.

'''
if "### C1C17-001" in receipt:
    raise AssertionError("C1C17 receipt already exists")
receipt = receipt.replace("## Pending batches", entry + "## Pending batches", 1)
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
    if path not in {SNAP, RECEIPT, ".github/scripts/docs_cutover_1c17.py"}:
        raise AssertionError(f"unexpected old-path occurrence after cutover: {hit}")

if git("hash-object", SNAP) != SOURCE_BLOB:
    raise AssertionError("snapshot blob changed during cutover")
if hashlib.sha256(snapshot_path.read_bytes()).hexdigest() != source_sha256:
    raise AssertionError("snapshot SHA-256 changed during cutover")

print(f"Cutover 1C-17 applicator completed; source_sha256={source_sha256}")
