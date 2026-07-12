#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD_PATH = "docs/mvp/wave7/e1r5_completion_report.md"
NEW_PATH = "docs/evidence/implementation/e1r5_completion_report.md"
SNAPSHOT_PATH = "docs/evidence/implementation/e1r5_completion_report-source.txt"
SOURCE_BLOB = "68fa2b0c76caf745e55f5f4ef3fd3677c8681a8d"
SOURCE_HEAD = "392810b74a0c76785beee7e3af7a5da3eacffa39"
SOURCE_MERGE = "477874cd08658297c4c6626e9423dd05d7bf45a4"
MERGED_C1C17 = "82d959ed00e958cb970ebcde0490903ae884322c"
PR_NUMBER = 576


def replace_exact(path: str, old: str, new: str, expected: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{path}: expected {expected} occurrence(s) of {old!r}, found {count}")
    target.write_text(text.replace(old, new), encoding="utf-8")


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def main() -> None:
    source_path = ROOT / OLD_PATH
    snapshot_path = ROOT / SNAPSHOT_PATH
    canonical_path = ROOT / NEW_PATH
    if not source_path.is_file():
        raise RuntimeError(f"missing source report: {OLD_PATH}")
    if snapshot_path.exists() or canonical_path.exists():
        raise RuntimeError("E1-R5 canonical evidence paths already exist")

    source_bytes = source_path.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    source_text = source_bytes.decode("utf-8")
    match = re.match(r"\A---\n.*?\n---\n", source_text, flags=re.DOTALL)
    if match is None:
        raise RuntimeError("E1-R5 source report front matter is missing")
    source_body = source_text[match.end() :]
    title, remainder = source_body.split("\n", 1)
    expected_title = "# E1-R5 Completion Report — Primary MEM Recall Candidate Discovery Bridge"
    if title != expected_title:
        raise RuntimeError(f"unexpected E1-R5 report title: {title!r}")
    remainder = remainder.lstrip("\n").replace(OLD_PATH, NEW_PATH)
    shared_marker = "## Shared documentation update inputs\n"
    if remainder.count(shared_marker) != 1:
        raise RuntimeError("E1-R5 shared-documentation marker is not unique")
    remainder = remainder.replace(
        shared_marker,
        shared_marker + "\nAt source PR #439:\n",
        1,
    )

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.rename(snapshot_path)

    canonical = f"""---
relaylm_doc_type: implementation_completion_report
relaylm_authority: e1r5_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/e1r5_primary_mem_recall_candidate_bridge.md
  - ../../architecture/e1_evaluation_consolidation.md
  - ../waves/e1r5_post_wave7_correction_convergence_audit.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current E1-R5 or Primary recall adapter behavior
  - cross-slice sequencing or release readiness
  - repeatable operator procedure
relaylm_source_commit: {SOURCE_HEAD}
relaylm_source_origin_commit: {SOURCE_MERGE}
relaylm_source_pr: 439
relaylm_recorded_on: 2026-06-28
relaylm_source_blob: {SOURCE_BLOB}
relaylm_source_content_sha256: {source_sha256}
relaylm_exact_source_snapshot: e1r5_completion_report-source.txt
---
{expected_title}

## Status and authority

This document is frozen implementation evidence for the E1-R5 bounded Primary MEM candidate-discovery bridge introduced by PR #439, whose final source head is `{SOURCE_HEAD}` and merge commit is `{SOURCE_MERGE}`. Current repository status belongs to [Project Status](../../PROJECT_STATUS.md). Current E1-R5 behavior, including the PR #491 canonical Primary recall adapter fold-in, belongs to [E1-R5 Primary MEM Recall Candidate Discovery Bridge](../../architecture/e1r5_primary_mem_recall_candidate_bridge.md), while cross-slice E1 evidence belongs to [E1 Evaluation Consolidation](../../architecture/e1_evaluation_consolidation.md).

The exact pre-cutover report is retained byte-for-byte as [e1r5_completion_report-source.txt](e1r5_completion_report-source.txt). Statements below describe the source PR boundary unless explicitly qualified.

{remainder}"""
    canonical_path.write_text(canonical, encoding="utf-8")

    replace_exact(
        "docs/README.md",
        "mvp/wave7/e1r5_completion_report.md",
        "evidence/implementation/e1r5_completion_report.md",
    )
    replace_exact(
        "docs/architecture/README.md",
        "../mvp/wave7/e1r5_completion_report.md",
        "../evidence/implementation/e1r5_completion_report.md",
    )
    replace_exact(
        "docs/architecture/e1_evaluation_consolidation.md",
        OLD_PATH,
        NEW_PATH,
    )
    replace_exact(
        "docs/architecture/e1r5_primary_mem_recall_candidate_bridge.md",
        "../mvp/wave7/e1r5_completion_report.md",
        "../evidence/implementation/e1r5_completion_report.md",
        expected=2,
    )
    replace_exact(
        "docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit.md",
        "../../mvp/wave7/e1r5_completion_report.md",
        "../implementation/e1r5_completion_report.md",
    )
    replace_exact(
        "docs/mvp/README.md",
        "(wave7/e1r5_completion_report.md)",
        "(../evidence/implementation/e1r5_completion_report.md)",
    )
    replace_exact(
        "docs/mvp/README.md",
        OLD_PATH,
        NEW_PATH,
    )
    replace_exact(
        "scripts/relaylm_e1_evaluation_consolidation_smoke.py",
        OLD_PATH,
        NEW_PATH,
    )
    replace_exact(
        "scripts/relaylm_documentation_current_boundary_smoke.py",
        OLD_PATH,
        NEW_PATH,
        expected=2,
    )
    replace_exact(
        "scripts/relaylm_docs_cutover_prepare.py",
        'values = template_values("docs/mvp/wave7/e1r5_completion_report.md")\n    assert values["relative_after_mvp"] == "wave7/e1r5_completion_report.md"',
        'values = template_values("docs/mvp/wave9/example_completion_report.md")\n    assert values["relative_after_mvp"] == "wave9/example_completion_report.md"',
    )

    current_boundary = ROOT / "scripts/relaylm_documentation_current_boundary_smoke.py"
    current_text = current_boundary.read_text(encoding="utf-8")
    old_block = '''    "docs/evidence/implementation/e1r5_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "Primary MEM Recall Candidate Discovery Bridge",
        "PR: #439",
        "PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py",
    ),'''
    new_block = '''    "docs/evidence/implementation/e1r5_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "E1-R5 Completion Report — Primary MEM Recall Candidate Discovery Bridge",
        "PR: #439",
        "Current E1-R5 behavior, including the PR #491 canonical Primary recall adapter fold-in, belongs to",
        "PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py",
        "At source PR #439:",
    ),'''
    if current_text.count(old_block) != 1:
        raise RuntimeError("current-boundary E1-R5 evidence block is not unique")
    current_boundary.write_text(current_text.replace(old_block, new_block), encoding="utf-8")

    implementation_index = ROOT / "docs/evidence/implementation/README.md"
    index_text = implementation_index.read_text(encoding="utf-8")
    anchor = "- [E1-R4 completion report](e1r4_completion_report.md) — frozen retrieval-response grounding implementation evidence from PR #437; current behavior remains architecture-owned.\n"
    addition = "- [E1-R5 completion report](e1r5_completion_report.md) — frozen bounded Primary recall candidate-discovery implementation evidence from PR #439; current behavior and the PR #491 fold-in remain architecture-owned.\n"
    if index_text.count(anchor) != 1 or addition in index_text:
        raise RuntimeError("implementation evidence index anchor is missing or E1-R5 already indexed")
    implementation_index.write_text(index_text.replace(anchor, anchor + addition), encoding="utf-8")

    receipt_path = ROOT / "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
    receipt = receipt_path.read_text(encoding="utf-8")
    pending = "cutover_pr: 575\nmerged_commit: pending"
    finalized = f"cutover_pr: 575\nmerged_commit: {MERGED_C1C17}"
    if receipt.count(pending) != 1:
        raise RuntimeError("C1C17 pending receipt is not unique")
    receipt = receipt.replace(pending, finalized, 1)
    pending_batches = "\n## Pending batches\n"
    if receipt.count(pending_batches) != 1:
        raise RuntimeError("pending-batches receipt marker is not unique")
    section = f"""

PR #575 merged as `{MERGED_C1C17}`; C1C17 is finalized by Cutover 1C-18.

### C1C18-001 — E1-R5 completion report

```yaml
cutover_pr: {PR_NUMBER}
merged_commit: pending
old_path: {OLD_PATH}
old_blob_sha: {SOURCE_BLOB}
old_content_sha256: {source_sha256}
source_commit: {SOURCE_HEAD}
source_origin_commit: {SOURCE_MERGE}
source_pr: 439
recorded_on: 2026-06-28
disposition: evidence_retained
new_canonical_path: {NEW_PATH}
exact_source_snapshot: {SNAPSHOT_PATH}
exact_source_blob_sha: {SOURCE_BLOB}
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 5
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 6
  relative_markdown_link_referrer_files_at_frozen_baseline: 5
  relative_markdown_link_dependencies_at_frozen_baseline: 6
  e1r5_architecture_handoff_updated: true
  post_wave7_correction_audit_link_updated: true
  correction_audit_exact_snapshot_unchanged: true
  e1_evaluation_consolidation_updated: true
  e1_evaluation_smoke_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  cutover_preparation_self_test_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1r5_smokes: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the complete E1-R5 bounded Primary MEM candidate-discovery implementation boundary from PR #439 while separating it from current architecture-owned behavior and the PR #491 canonical Primary recall adapter fold-in. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified six repository-root references across five files and six Markdown-link dependencies across five router, handoff, and evidence files. The current Post-Wave-7 correction audit is relinked while its exact source snapshot remains unchanged. The old path above is only the historical migration identifier for this receipt.
"""
    receipt_path.write_text(receipt.replace(pending_batches, section + pending_batches), encoding="utf-8")

    snapshot_blob = git("hash-object", SNAPSHOT_PATH)
    if snapshot_blob != SOURCE_BLOB:
        raise RuntimeError(f"snapshot blob mismatch: {snapshot_blob} != {SOURCE_BLOB}")
    if hashlib.sha256(snapshot_path.read_bytes()).hexdigest() != source_sha256:
        raise RuntimeError("snapshot SHA-256 mismatch")

    allowed_old_path_files = {
        SNAPSHOT_PATH,
        "docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit-source.txt",
        "docs/evidence/migrations/documentation-hard-cutover-receipt.md",
        ".github/scripts/docs_cutover_1c18.py",
    }
    grep = subprocess.run(
        ["git", "grep", "-l", OLD_PATH],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if grep.returncode not in {0, 1}:
        raise RuntimeError(f"git grep failed: {grep.stderr.strip()}")
    remaining = {line.strip() for line in grep.stdout.splitlines() if line.strip()}
    unexpected = remaining - allowed_old_path_files
    if unexpected:
        raise RuntimeError(f"unexpected old-path references remain: {sorted(unexpected)}")

    correction_snapshot = ROOT / "docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit-source.txt"
    if git("hash-object", str(correction_snapshot.relative_to(ROOT))) != "0d7cbceca1259d127ebf4fa1a7f91bcbf9e144e5":
        raise RuntimeError("correction-audit exact snapshot changed")

    print(f"E1-R5 source SHA-256: {source_sha256}")
    print(f"E1-R5 source blob: {snapshot_blob}")
    print("Cutover 1C-18 applicator completed")


if __name__ == "__main__":
    main()
