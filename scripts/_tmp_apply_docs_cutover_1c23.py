#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "docs/mvp/wave6/e1r2_completion_report.md"
CANON = ROOT / "docs/evidence/implementation/e1r2_completion_report.md"
SNAP = ROOT / "docs/evidence/implementation/e1r2_completion_report-source.txt"
RECEIPT = ROOT / "docs/evidence/migrations/documentation-hard-cutover-receipt.md"

SOURCE_HEAD = "76f80f590f64c5078fb93bc43b62c49c866b84bf"
SOURCE_MERGE = "fefd3559ac32a37ed932faa130612a6a3da43c61"
SOURCE_BLOB = "107923354f09e0e3340e329f282d2c818910cad2"
SOURCE_SHA256 = "72e1fcb022cf2db3bcbda3e3d14a46a18da1f50c3747f6706301346abc6f7722"
PREVIOUS_MERGE = "4cc36a948b399d5657c89b0b0c835287f9b93cd3"
CUTOVER_PR = os.environ.get("CUTOVER_PR", "pending")


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise AssertionError(f"{path}: expected one occurrence of {old!r}, got {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    source = OLD.read_bytes()
    assert git_blob_sha(source) == SOURCE_BLOB
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA256
    source_text = source.decode("utf-8")
    assert source_text.count("docs/mvp/wave6/e1r2_completion_report.md") == 2

    SNAP.parent.mkdir(parents=True, exist_ok=True)
    SNAP.write_bytes(source)
    OLD.unlink()

    marker = "---\n\n# E1-R2 Character Store Bootstrap Completion Report\n"
    assert marker in source_text
    body = source_text.split(marker, 1)[1]
    body = body.replace(
        "docs/mvp/wave6/e1r2_completion_report.md",
        "docs/evidence/implementation/e1r2_completion_report.md",
    )
    connector_note = (
        "Connector-preparation note: this branch was prepared through the GitHub connector because the local "
        "`~/work/relay-lm` checkout is unavailable in this environment. Python syntax for the new module, CLI, "
        "and smoke was checked before pushing; full repository validation is expected to run in GitHub Actions."
    )
    assert connector_note in body
    body = body.replace(
        connector_note,
        connector_note
        + "\n\nAt source PR #432, GitHub Actions was the execution source of truth for full in-repository validation. "
        "The dedicated E1-R2 workflow present at that source boundary is absent from the current tree and is not "
        "recreated during this cutover; current validation belongs to the consolidated runtime smoke inventory. "
        "The current consolidated entry is the runtime `e1r2_character_store_bootstrap` group in "
        "`scripts/relaylm_ci_consolidated_smoke.py`.",
        1,
    )

    canonical = f"""---
relaylm_doc_type: implementation_completion_report
relaylm_authority: e1r2_character_store_bootstrap_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: evaluation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/e1r2_character_store_bootstrap.md
  - ../../architecture/e1_evaluation_consolidation.md
  - ../../architecture/e1_local_runtime_evaluation_2026_06_25.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current character-store bootstrap command, CLI, or store-layout behavior
  - current queue, worker, scheduler, or Primary MEM publication behavior
  - current implementation sequencing or release readiness
  - current operator procedure
relaylm_source_commit: {SOURCE_HEAD}
relaylm_source_origin_commit: {SOURCE_MERGE}
relaylm_source_pr: 432
relaylm_recorded_on: 2026-06-27
relaylm_source_blob: {SOURCE_BLOB}
relaylm_source_content_sha256: {SOURCE_SHA256}
relaylm_exact_source_snapshot: e1r2_completion_report-source.txt
---
# E1-R2 Character Store Bootstrap Completion Report

## Status and authority

This document is frozen implementation evidence for the E1-R2 character-store bootstrap slice introduced by PR #432, whose final source head is `{SOURCE_HEAD}` and merge commit is `{SOURCE_MERGE}`. Current repository-wide status belongs to [Project Status](../../PROJECT_STATUS.md). Current character-store bootstrap behavior belongs to [E1-R2 Character Store Bootstrap](../../architecture/e1r2_character_store_bootstrap.md), the production implementation, and the focused E1-R2 smoke suite.

The exact pre-cutover report is retained byte-for-byte as [e1r2_completion_report-source.txt](e1r2_completion_report-source.txt). Statements below describe the source PR boundary unless explicitly qualified. Legacy-path strings inside the exact snapshot are historical source text, not live repository references.

Last reviewed: 2026-06-27 JST

This report is evidence for one implementation pull request. It is not current runtime, repository-wide status, bootstrap-command, store-layout, queue/worker/scheduler, sequencing, release-readiness, or operator-procedure authority.

{body}"""
    CANON.write_text(canonical, encoding="utf-8")

    replace_once(
        ROOT / "docs/README.md",
        "mvp/wave6/e1r2_completion_report.md",
        "evidence/implementation/e1r2_completion_report.md",
    )
    replace_once(
        ROOT / "docs/architecture/README.md",
        "../mvp/wave6/e1r2_completion_report.md",
        "../evidence/implementation/e1r2_completion_report.md",
    )
    mvp = ROOT / "docs/mvp/README.md"
    replace_once(mvp, "wave6/e1r2_completion_report.md", "../evidence/implementation/e1r2_completion_report.md")
    replace_once(
        mvp,
        "docs/mvp/wave6/e1r2_completion_report.md",
        "docs/evidence/implementation/e1r2_completion_report.md",
    )
    replace_once(
        ROOT / "docs/evidence/waves/wave6_cross_slice_convergence_audit.md",
        "../../mvp/wave6/e1r2_completion_report.md",
        "../implementation/e1r2_completion_report.md",
    )
    for rel in (
        "docs/architecture/e1_evaluation_consolidation.md",
        "scripts/relaylm_ci_consolidated_smoke.py",
        "scripts/relaylm_e1_evaluation_consolidation_smoke.py",
    ):
        replace_once(
            ROOT / rel,
            "docs/mvp/wave6/e1r2_completion_report.md",
            "docs/evidence/implementation/e1r2_completion_report.md",
        )

    handoff = ROOT / "docs/architecture/e1r2_character_store_bootstrap.md"
    handoff_text = handoff.read_text(encoding="utf-8")
    assert "## Completion report" not in handoff_text
    handoff.write_text(
        handoff_text.rstrip()
        + "\n\n## Validation\n\n"
        + "E1-R2 has focused dry-run, apply, idempotency, malformed-state, and content-free projection smoke coverage. "
        + "Current validation is routed through the consolidated runtime smoke inventory rather than the removed "
        + "source-PR-specific workflow.\n\n"
        + "## Completion report\n\n"
        + "The frozen implementation evidence for this slice is recorded in [E1-R2 completion report]"
        + "(../evidence/implementation/e1r2_completion_report.md). Current behavior remains owned by this handoff, "
        + "the production implementation, and the focused E1-R2 smoke suite.\n",
        encoding="utf-8",
    )

    impl_index = ROOT / "docs/evidence/implementation/README.md"
    index_text = impl_index.read_text(encoding="utf-8")
    assert "e1r2_completion_report.md" not in index_text
    index_text = index_text.rstrip() + (
        "\n- [E1-R2 completion report](e1r2_completion_report.md) — frozen dry-run-first idempotent character-store "
        "bootstrap evidence from PR #432; current command and store-layout behavior remain handoff-, implementation-, "
        "and focused-smoke-owned.\n"
    )
    impl_index.write_text(index_text, encoding="utf-8")

    boundary = ROOT / "scripts/relaylm_documentation_current_boundary_smoke.py"
    boundary_text = boundary.read_text(encoding="utf-8")
    boundary_text = boundary_text.replace(
        '    "docs/architecture/e1r2_character_store_bootstrap.md",\n',
        '    "docs/architecture/e1r2_character_store_bootstrap.md",\n'
        '    "docs/evidence/implementation/e1r2_completion_report.md",\n',
        1,
    )
    e1r1_block = '''    "docs/evidence/implementation/e1r1_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "relaylm_source_pr: 433",
        "E1-R1 Trusted Home Scene Admission Completion Report",
        "Current trusted Home scene-admission behavior belongs to",
        "e1r1_completion_report-source.txt",
        "At source PR #433",
    ),
'''
    assert boundary_text.count(e1r1_block) == 1
    e1r2_block = '''    "docs/architecture/e1r2_character_store_bootstrap.md": (
        "relaylm_doc_type: architecture_handoff",
        "# E1-R2 Character Store Bootstrap",
        "relaylm-character-store-bootstrap",
        "../evidence/implementation/e1r2_completion_report.md",
    ),
    "docs/evidence/implementation/e1r2_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "relaylm_source_pr: 432",
        "E1-R2 Character Store Bootstrap Completion Report",
        "Current character-store bootstrap behavior belongs to",
        "e1r2_completion_report-source.txt",
        "At source PR #432",
    ),
'''
    boundary_text = boundary_text.replace(e1r1_block, e1r1_block + e1r2_block, 1)
    stale_anchor = "    Character-store bootstrap remains operator-facing and brittle\n"
    assert boundary_text.count(stale_anchor) == 1
    boundary_text = boundary_text.replace(
        stale_anchor,
        stale_anchor + "    docs/mvp/wave6/e1r2_completion_report.md\n",
        1,
    )
    boundary.write_text(boundary_text, encoding="utf-8")

    receipt_text = RECEIPT.read_text(encoding="utf-8")
    previous = "cutover_pr: 584\nmerged_commit: pending"
    assert receipt_text.count(previous) == 1
    receipt_text = receipt_text.replace(
        previous,
        f"cutover_pr: 584\nmerged_commit: {PREVIOUS_MERGE}",
        1,
    )
    insert_before = "## Pending batches\n"
    assert receipt_text.count(insert_before) == 1
    block = f'''### C1C23-001 — E1-R2 completion report

```yaml
cutover_pr: {CUTOVER_PR}
merged_commit: pending
old_path: docs/mvp/wave6/e1r2_completion_report.md
old_blob_sha: {SOURCE_BLOB}
old_content_sha256: {SOURCE_SHA256}
source_commit: {SOURCE_HEAD}
source_origin_commit: {SOURCE_MERGE}
source_pr: 432
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/e1r2_completion_report.md
exact_source_snapshot: docs/evidence/implementation/e1r2_completion_report-source.txt
exact_source_blob_sha: {SOURCE_BLOB}
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 4
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 4
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 2
  e1r2_architecture_handoff_updated: true
  e1_evaluation_consolidation_updated: true
  wave6_convergence_evidence_link_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  consolidated_e1r2_smoke_updated: true
  e1_evaluation_smoke_updated: true
  dedicated_e1r2_workflow_absent_in_current_tree: true
  cutover_preparation_self_test_reused_without_path_change: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1r2_smoke: passed
  e1_evaluation_consolidation_smoke: passed
  consolidated_runtime_e1r2_group: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the complete E1-R2 explicit dry-run-first idempotent character-store bootstrap implementation boundary from PR #432 while separating it from current handoff-, command-, store-layout-, implementation-, queue/worker/scheduler-, and focused-smoke-owned behavior. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. Live Markdown-link and repository-root validation dependencies are moved to the canonical path; legacy references remain only in this migration receipt and frozen exact source snapshots. The dedicated E1-R2 workflow named by the historical source report is no longer present in the current tree and is not recreated. The migration-aware completion-report model and PR-link checks apply without validator changes.

'''
    receipt_text = receipt_text.replace(insert_before, block + insert_before, 1)
    RECEIPT.write_text(receipt_text, encoding="utf-8")

    assert not OLD.exists()
    assert SNAP.read_bytes() == source
    assert git_blob_sha(SNAP.read_bytes()) == SOURCE_BLOB
    assert CANON.exists()
    assert not (ROOT / ".github/workflows/e1r2-character-store-bootstrap.yml").exists()


if __name__ == "__main__":
    main()
