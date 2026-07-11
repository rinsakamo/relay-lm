from __future__ import annotations

import hashlib
import os
from pathlib import Path

ROOT = Path.cwd()
OLD = Path("docs/architecture/e1r5_post_wave7_correction_convergence_audit.md")
SNAPSHOT = Path("docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit-source.txt")
CANONICAL = Path("docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit.md")
EXPECTED_BLOB = "0d7cbceca1259d127ebf4fa1a7f91bcbf9e144e5"
EXPECTED_SHA256 = "552e8744b3f32f2e4c21eb8273f56fe0ee4f95e22cf33ad7ae734625dcc41edb"
CUTOVER_PR = os.environ["CUTOVER_PR"]


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace(path: str, old: str, new: str, expected: int) -> None:
    body = read(path)
    actual = body.count(old)
    assert actual == expected, f"{path}: expected {expected} occurrences of {old!r}, found {actual}"
    write(path, body.replace(old, new))


source_path = ROOT / OLD
assert source_path.exists(), f"missing source: {OLD}"
assert not (ROOT / SNAPSHOT).exists(), f"snapshot already exists: {SNAPSHOT}"
assert not (ROOT / CANONICAL).exists(), f"canonical already exists: {CANONICAL}"

source_bytes = source_path.read_bytes()
assert hashlib.sha256(source_bytes).hexdigest() == EXPECTED_SHA256
assert git_blob_sha(source_bytes) == EXPECTED_BLOB
source_text = source_bytes.decode("utf-8")

parts = source_text.split("---\n", 2)
assert len(parts) == 3 and parts[0] == "", "unexpected source front matter"
body = parts[2]

link_replacements = (
    ("(../PROJECT_STATUS.md)", "(../../PROJECT_STATUS.md)", 1),
    ("(project_execution_plan.md)", "(../../architecture/project_execution_plan.md)", 1),
    (
        "(e1r5_primary_mem_recall_candidate_bridge.md)",
        "(../../architecture/e1r5_primary_mem_recall_candidate_bridge.md)",
        3,
    ),
    (
        "(../mvp/wave7/e1r5_completion_report.md)",
        "(../../mvp/wave7/e1r5_completion_report.md)",
        1,
    ),
)
for old, new, expected in link_replacements:
    actual = body.count(old)
    assert actual == expected, f"canonical source: expected {expected} occurrences of {old!r}, found {actual}"
    body = body.replace(old, new)

status_needle = "Generated: 2026-06-30 JST.\n\n## Purpose"
status_section = """Generated: 2026-06-30 JST.

## Status and authority

The correction audit was introduced through PR #452. Its exact pre-cutover source was later converged through PR #498 after PR #491 closed PM-D8 by folding the bounded E1-R5 fallback into the canonical Primary recall adapter.

This document is frozen historical evidence for that post-Wave-7 correction point. Current repository status, current E1 behavior, and exact lower-level contracts remain authoritative in their dedicated current documents. Current repository-wide status belongs to [Project Status](../../PROJECT_STATUS.md).

The exact submitted source is retained byte-for-byte as [e1r5_post_wave7_correction_convergence_audit-source.txt](e1r5_post_wave7_correction_convergence_audit-source.txt).

## Purpose"""
assert body.count(status_needle) == 1
body = body.replace(status_needle, status_section)

metadata = """---
relaylm_doc_type: evidence
relaylm_authority: e1r5_post_wave7_correction_convergence_record
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current Primary recall adapter behavior
  - exact E1-R5 or E1-R4 contracts
  - Wave 8 and later implementation status
relaylm_source_commit: 676678a004c688eca856e37b3ecf48f98801452c
relaylm_source_pr: 498
relaylm_origin_pr: 452
relaylm_recorded_on: 2026-06-30
relaylm_source_blob: 0d7cbceca1259d127ebf4fa1a7f91bcbf9e144e5
relaylm_source_content_sha256: 552e8744b3f32f2e4c21eb8273f56fe0ee4f95e22cf33ad7ae734625dcc41edb
---
"""

snapshot_path = ROOT / SNAPSHOT
snapshot_path.parent.mkdir(parents=True, exist_ok=True)
snapshot_path.write_bytes(source_bytes)
canonical_path = ROOT / CANONICAL
canonical_path.write_text(metadata + body, encoding="utf-8")
source_path.unlink()

replace(
    "docs/README.md",
    "(architecture/e1r5_post_wave7_correction_convergence_audit.md)",
    "(evidence/waves/e1r5_post_wave7_correction_convergence_audit.md)",
    1,
)
replace(
    "docs/PROJECT_STATUS.md",
    "docs/architecture/e1r5_post_wave7_correction_convergence_audit.md",
    "docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit.md",
    1,
)
replace(
    "docs/PROJECT_STATUS.md",
    "(architecture/e1r5_post_wave7_correction_convergence_audit.md)",
    "(evidence/waves/e1r5_post_wave7_correction_convergence_audit.md)",
    1,
)
replace(
    "docs/architecture/README.md",
    "(e1r5_post_wave7_correction_convergence_audit.md)",
    "(../evidence/waves/e1r5_post_wave7_correction_convergence_audit.md)",
    2,
)
replace(
    "docs/architecture/e1r5_primary_mem_recall_candidate_bridge.md",
    "  - e1r5_post_wave7_correction_convergence_audit.md",
    "  - ../evidence/waves/e1r5_post_wave7_correction_convergence_audit.md",
    1,
)
replace(
    "docs/architecture/project_execution_plan.md",
    "  - e1r5_post_wave7_correction_convergence_audit.md",
    "  - ../evidence/waves/e1r5_post_wave7_correction_convergence_audit.md",
    1,
)
replace(
    "scripts/relaylm_documentation_current_boundary_smoke.py",
    "    \"docs/architecture/e1r5_post_wave7_correction_convergence_audit.md\",\n",
    "",
    1,
)

smoke_path = "scripts/relaylm_e1_evaluation_consolidation_smoke.py"
smoke = read(smoke_path)
required_anchor = '''    "docs/evidence/waves/wave7_cross_slice_convergence_audit.md": (
        "# Wave 7 Cross-Slice Convergence Audit",
        "E1-R3 provenance-preserving Primary MEM formation summary",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression",
        "W7-INT is merged.",
    ),
'''
required_addition = required_anchor + '''    "docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit.md": (
        "# E1-R5 Post-Wave-7 Correction Convergence Audit",
        "M2 remains the preferred relevance owner.",
        "PM-D8 is closed by PR #491",
        "The former runtime bridge module remains compatibility no-op only.",
    ),
'''
assert smoke.count(required_anchor) == 1
smoke = smoke.replace(required_anchor, required_addition)

evidence_anchor = '    "docs/evidence/waves/wave7_cross_slice_convergence_audit.md",\n'
evidence_addition = evidence_anchor + '    "docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit.md",\n'
assert smoke.count(evidence_anchor) == 1
smoke = smoke.replace(evidence_anchor, evidence_addition)

index_anchor = '        "wave7_cross_slice_convergence_audit.md",\n'
index_addition = index_anchor + '        "e1r5_post_wave7_correction_convergence_audit.md",\n'
assert smoke.count(index_anchor) == 1
smoke = smoke.replace(index_anchor, index_addition)
write(smoke_path, smoke)

waves_index_path = "docs/evidence/waves/README.md"
waves_index = read(waves_index_path)
wave7_line = "- [Wave 7 cross-slice convergence audit](wave7_cross_slice_convergence_audit.md) — frozen boundary after PRs #436 through #438, merged as W7-INT.\n"
correction_line = "- [E1-R5 post-Wave-7 correction convergence audit](e1r5_post_wave7_correction_convergence_audit.md) — frozen correction record introduced in PR #452 and converged after PM-D8 closure through PR #498.\n"
assert waves_index.count(wave7_line) == 1
assert correction_line not in waves_index
write(waves_index_path, waves_index.replace(wave7_line, wave7_line + correction_line))

receipt_path = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
receipt = read(receipt_path)
old_finalize = "cutover_pr: 566\nmerged_commit: pending"
new_finalize = "cutover_pr: 566\nmerged_commit: 0689fc6c926aeaaece5f404a831f1000294e5cbd"
assert receipt.count(old_finalize) == 1
receipt = receipt.replace(old_finalize, new_finalize)

old_c1c9_note = "The canonical evidence document preserves the complete Wave 7 convergence account while correcting six internal relative links for the evidence collection. The exact pre-cutover source remains available as the original Git blob. The dependency sweep identified three repository-root literals across two files, four hard-coded script occurrences across two smoke files, six Markdown relative links across five referrer files, and four `relaylm_related_authority` YAML references. The old path above is only the historical migration identifier for this receipt."
new_c1c9_note = "The canonical evidence document preserves the complete Wave 7 convergence account while correcting six internal relative links for the evidence collection. The exact pre-cutover source remains available as the original Git blob. The dependency sweep identified three repository-root literals across two files, four hard-coded script occurrences across two smoke files, six Markdown relative links across five referrer files, and four `relaylm_related_authority` YAML references. PR #566 merged as `0689fc6c926aeaaece5f404a831f1000294e5cbd`; C1C9 is finalized by Cutover 1C-10."
assert receipt.count(old_c1c9_note) == 1
receipt = receipt.replace(old_c1c9_note, new_c1c9_note)

pending_marker = "## Pending batches\n"
assert receipt.count(pending_marker) == 1
c1c10 = f"""### C1C10-001 — E1-R5 post-Wave-7 correction convergence audit

```yaml
cutover_pr: {CUTOVER_PR}
merged_commit: pending
old_path: docs/architecture/e1r5_post_wave7_correction_convergence_audit.md
old_blob_sha: 0d7cbceca1259d127ebf4fa1a7f91bcbf9e144e5
old_content_sha256: 552e8744b3f32f2e4c21eb8273f56fe0ee4f95e22cf33ad7ae734625dcc41edb
source_commit: 676678a004c688eca856e37b3ecf48f98801452c
source_pr: 498
origin_pr: 452
recorded_on: 2026-06-30
disposition: evidence_retained
new_canonical_path: docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit.md
exact_source_snapshot: docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit-source.txt
exact_source_blob_sha: 0d7cbceca1259d127ebf4fa1a7f91bcbf9e144e5
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 1
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 1
  script_hard_coded_path_reference_files_updated_in_pr_tree: 1
  script_hard_coded_path_reference_occurrences_updated_in_pr_tree: 1
  relative_markdown_link_referrer_files_at_frozen_baseline: 3
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  current_tree_related_authority_references_updated: 3
  canonical_internal_relative_links_repaired: 6
  current_boundary_smoke_historical_path_removed: true
  e1_evaluation_smoke_updated: true
  documentation_link_check: passed
  documentation_semantic_audit: passed
  affected_current_boundary_checks: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical evidence document preserves the complete E1-R5 post-Wave-7 correction account while repairing six internal relative links for the evidence collection. The exact pre-cutover source remains available as the original Git blob. The record was introduced by PR #452 and its exact pre-cutover form includes the later PM-D8 closure convergence from PR #498 after runtime fold-in PR #491. The dependency sweep identified one repository-root literal, one hard-coded current-boundary path, four Markdown relative links across three referrer files, and three `relaylm_related_authority` YAML references. The old path above is only the historical migration identifier for this receipt.

"""
assert "### C1C10-001" not in receipt
receipt = receipt.replace(pending_marker, c1c10 + pending_marker)
write(receipt_path, receipt)

assert not source_path.exists()
assert snapshot_path.read_bytes() == source_bytes
assert git_blob_sha(snapshot_path.read_bytes()) == EXPECTED_BLOB
assert hashlib.sha256(snapshot_path.read_bytes()).hexdigest() == EXPECTED_SHA256
assert canonical_path.exists()

old_full = "docs/architecture/e1r5_post_wave7_correction_convergence_audit.md"
occurrences = []
for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts or ".github" in path.parts:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    if old_full in text:
        occurrences.append(path.relative_to(ROOT).as_posix())
assert occurrences == [receipt_path], f"unexpected old full-path occurrences: {occurrences!r}"

for temporary in (
    ROOT / ".github/scripts/docs_cutover_1c10.py",
    ROOT / ".github/workflows/docs-cutover-1c10-pr-applicator.yml",
):
    if temporary.exists():
        temporary.unlink()
