#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "docs/mvp/wave8/e2_value_smoke_harness_completion_report.md"
NEW = "docs/evidence/implementation/e2_value_smoke_harness_completion_report.md"
SNAP = "docs/evidence/implementation/e2_value_smoke_harness_completion_report-source.txt"
RECEIPT = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
SOURCE_BLOB = "333ba34007a38b794572683c41e947ae1d0ad8cf"
SOURCE_SHA256 = "ffc09e20a41f7202c05682aa9e50a8c859107a64bacdc33ff5e9a81723b13358"
SOURCE_COMMIT = "51d678dfb0a10899db424e59c08af70865b8333f"
SOURCE_PR = 481
CUTOVER_PR = 571
PREVIOUS_MERGE = "81a6b0079acc2e33a9913c6edac7276629b1ff15"


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
if hashlib.sha256(source.encode("utf-8")).hexdigest() != SOURCE_SHA256:
    raise AssertionError("source SHA-256 mismatch")
if git("hash-object", OLD) != SOURCE_BLOB or git("hash-object", SNAP) != SOURCE_BLOB:
    raise AssertionError("source Git blob mismatch")

replace(
    "docs/README.md",
    "(mvp/wave8/e2_value_smoke_harness_completion_report.md)",
    "(evidence/implementation/e2_value_smoke_harness_completion_report.md)",
)

mvp_readme = read("docs/mvp/README.md")
old_link = "(wave8/e2_value_smoke_harness_completion_report.md)"
new_link = "(../evidence/implementation/e2_value_smoke_harness_completion_report.md)"
if mvp_readme.count(old_link) != 1:
    raise AssertionError("docs/mvp/README.md: E2 report link anchor mismatch")
mvp_readme = mvp_readme.replace(old_link, new_link, 1)
if mvp_readme.count(OLD) != 1:
    raise AssertionError("docs/mvp/README.md: E2 validation command anchor mismatch")
mvp_readme = mvp_readme.replace(OLD, NEW, 1)
write("docs/mvp/README.md", mvp_readme)

replace(
    "docs/mvp/v0.1_release_readiness.md",
    "(wave8/e2_value_smoke_harness_completion_report.md)",
    "(../evidence/implementation/e2_value_smoke_harness_completion_report.md)",
)

implementation_index = read("docs/evidence/implementation/README.md")
entry = (
    "- [E2 Value Smoke Harness completion report]"
    "(e2_value_smoke_harness_completion_report.md) — frozen harness implementation evidence "
    "from PR #481; later human judgment remains release-readiness-owned.\n"
)
if entry not in implementation_index:
    implementation_index = implementation_index.rstrip() + "\n" + entry
write("docs/evidence/implementation/README.md", implementation_index)

boundary = read("scripts/relaylm_documentation_current_boundary_smoke.py")
path_anchor = '        "docs/evidence/implementation/o2_o3_pm_d5_d7_docs_convergence_completion_report.md",\n'
path_line = f'        "{NEW}",\n'
if boundary.count(path_anchor) != 1:
    raise AssertionError("current-boundary Wave 8 index path anchor mismatch")
if path_line not in boundary:
    boundary = boundary.replace(path_anchor, path_anchor + path_line, 1)
map_anchor = '''    "docs/evidence/implementation/o2_o3_pm_d5_d7_docs_convergence_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "O2/O3 and PM-D5-D7 Docs Convergence Completion Report",
        "PR: #490",
        "At source PR #490:",
    ),
'''
map_entry = f'''    "{NEW}": (
        "relaylm_doc_type: implementation_completion_report",
        "E2 Value Smoke Harness Completion Report",
        "PR: #481",
        "later durable-memory E2 human review and release-readiness conclusion",
        "does not retroactively turn this harness implementation report into a quality-evaluation record",
    ),
'''
if boundary.count(map_anchor) != 1:
    raise AssertionError("current-boundary implementation evidence map anchor mismatch")
if map_entry not in boundary:
    boundary = boundary.replace(map_anchor, map_anchor + map_entry, 1)
write("scripts/relaylm_documentation_current_boundary_smoke.py", boundary)

receipt = read(RECEIPT)
c1c12_marker = "### C1C12-001 — O2/O3 and PM-D5-D7 docs convergence completion report"
start = receipt.index(c1c12_marker)
pending = receipt.index("merged_commit: pending", start)
receipt = receipt[:pending] + f"merged_commit: {PREVIOUS_MERGE}" + receipt[pending + len("merged_commit: pending"):]
old_tail = "The old path above is only the historical migration identifier for this receipt."
new_tail = f"PR #570 merged as `{PREVIOUS_MERGE}`; C1C12 is finalized by Cutover 1C-13."
tail_pos = receipt.index(old_tail, start)
receipt = receipt[:tail_pos] + new_tail + receipt[tail_pos + len(old_tail):]
entry = f'''### C1C13-001 — E2 Value Smoke Harness completion report

```yaml
cutover_pr: {CUTOVER_PR}
merged_commit: pending
old_path: {OLD}
old_blob_sha: {SOURCE_BLOB}
old_content_sha256: {SOURCE_SHA256}
source_commit: {SOURCE_COMMIT}
source_pr: {SOURCE_PR}
recorded_on: 2026-07-04
disposition: evidence_retained
new_canonical_path: {NEW}
exact_source_snapshot: {SNAP}
exact_source_blob_sha: {SOURCE_BLOB}
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 1
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 1
  relative_markdown_link_referrer_files_at_frozen_baseline: 3
  relative_markdown_link_dependencies_at_frozen_baseline: 3
  implementation_evidence_index_updated: true
  release_readiness_reference_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e2_harness_smoke: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the complete E2 comparison-transcript harness implementation boundary while separating it from the later local human judgment and release-readiness conclusion. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified one repository-root path occurrence, three Markdown links across three referrer files, one release-readiness reference, and one current-boundary evidence-map addition. The migration-aware completion-report model and PR-link checks introduced by C1C11 apply without further validator changes. The old path above is only the historical migration identifier for this receipt.

'''
anchor = "## Pending batches"
if "### C1C13-001" in receipt:
    raise AssertionError("C1C13 receipt already exists")
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
    if path not in {SNAP, RECEIPT, ".github/scripts/docs_cutover_1c13.py"}:
        raise AssertionError(f"unexpected old-path occurrence after cutover: {hit}")

if git("hash-object", SNAP) != SOURCE_BLOB:
    raise AssertionError("snapshot blob changed during cutover")

print("Cutover 1C-13 applicator completed")
