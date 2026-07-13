#!/usr/bin/env python3
"""Apply the temporary Cutover 1C-24 documentation migration."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

OLD = Path("docs/mvp/wave6/docs_horizontal_status_sweep_completion_report.md")
CANON = Path("docs/evidence/implementation/docs_horizontal_status_sweep_completion_report.md")
SNAPSHOT = Path("docs/evidence/implementation/docs_horizontal_status_sweep_completion_report-source.txt")
RECEIPT = Path("docs/evidence/migrations/documentation-hard-cutover-receipt.md")
OLD_PATH = OLD.as_posix()
CANON_PATH = CANON.as_posix()

PRE_BLOB = "c92bc7e856ef28e862a738c47668d46c67a71904"
PRE_SHA = "889edab78de527869e3b94c764fadf9d9cce92b03f8adb946e42c3e6ca6a7627"
SOURCE_ORIGIN = "6a0a384d3524fe98528643da666284576d974cd1"
SOURCE_BLOB = "2057afb52dab8903064853f0899d954c888bb213"
SOURCE_SHA = "bf0ba10a2f97539a4217fd8c78629c83d05e0e70d0a361759b1ac9ca3173464e"
PREVIOUS_MERGE = "c068a6a4d447f7b622346da2766507de532fe0bc"


def git_blob(data: bytes) -> str:
    proc = subprocess.run(
        ["git", "hash-object", "--stdin"],
        input=data,
        check=True,
        stdout=subprocess.PIPE,
    )
    return proc.stdout.decode().strip()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{path}: replacement anchor count {count}, expected 1: {old!r}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    current = OLD.read_bytes()
    if git_blob(current) != PRE_BLOB:
        raise SystemExit("pre-cutover blob mismatch")
    if hashlib.sha256(current).hexdigest() != PRE_SHA:
        raise SystemExit("pre-cutover sha256 mismatch")

    source = subprocess.run(
        ["git", "show", f"{SOURCE_ORIGIN}:{OLD_PATH}"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    if git_blob(source) != SOURCE_BLOB:
        raise SystemExit("source PR blob mismatch")
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA:
        raise SystemExit("source PR sha256 mismatch")

    expected_current = source.replace(
        b"docs/architecture/wave5_cross_slice_convergence_audit.md",
        b"docs/evidence/waves/wave5_cross_slice_convergence_audit.md",
    )
    if expected_current != current:
        raise SystemExit(
            "source-to-pre-cutover delta is not the single recorded Wave 5 path repair"
        )

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_bytes(current)

    source_text = current.decode("utf-8")
    if not source_text.startswith("---\n"):
        raise SystemExit("source front matter start missing")
    parts = source_text.split("---\n", 2)
    if len(parts) != 3:
        raise SystemExit("source front matter boundary mismatch")

    body = parts[2].replace(OLD_PATH, CANON_PATH)
    heading = "# Docs Horizontal Status Sweep Completion Report\n"
    if body.count(heading) != 1:
        raise SystemExit("report heading mismatch")

    status = """
## Status and authority

This document is frozen documentation-convergence implementation evidence for the docs-only horizontal status sweep introduced by PR #434. Current repository-wide implementation status belongs to [Project Status](../../PROJECT_STATUS.md); current documentation placement and lifecycle rules belong to [Documentation Model](../../DOCUMENTATION_MODEL.md); current sequencing belongs to [Project Execution Plan](../../architecture/project_execution_plan.md).

The exact cutover input is retained byte-for-byte as [docs_horizontal_status_sweep_completion_report-source.txt](docs_horizontal_status_sweep_completion_report-source.txt). The source PR final-head/merge form used Git blob `2057afb52dab8903064853f0899d954c888bb213`; the cutover input uses Git blob `c92bc7e856ef28e862a738c47668d46c67a71904` and differs only by the later canonical Wave 5 convergence-audit path repair from commit `d1b920c3c7fcdf16053e8c9f449863cadfcb7384`.

Last reviewed: 2026-06-27 JST

This report is evidence for one docs-only convergence PR. It is not current runtime, repository-wide status, documentation-model, feature-family behavior, sequencing, release-readiness, or operator-procedure authority.

"""
    body = body.replace(heading, heading + status, 1)

    metadata = """---
relaylm_doc_type: implementation_completion_report
relaylm_authority: docs_horizontal_status_sweep_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../DOCUMENTATION_MODEL.md
  - ../../architecture/project_execution_plan.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current documentation placement or lifecycle rules
  - current feature-family behavior
  - current implementation sequencing or release readiness
  - current operator procedure
relaylm_source_commit: 86577b7712ea9efcc228f32a431b3606e552d40a
relaylm_source_origin_commit: 6a0a384d3524fe98528643da666284576d974cd1
relaylm_source_pr: 434
relaylm_recorded_on: 2026-06-27
relaylm_source_blob: 2057afb52dab8903064853f0899d954c888bb213
relaylm_source_content_sha256: bf0ba10a2f97539a4217fd8c78629c83d05e0e70d0a361759b1ac9ca3173464e
relaylm_pre_cutover_blob: c92bc7e856ef28e862a738c47668d46c67a71904
relaylm_pre_cutover_content_sha256: 889edab78de527869e3b94c764fadf9d9cce92b03f8adb946e42c3e6ca6a7627
relaylm_exact_source_snapshot: docs_horizontal_status_sweep_completion_report-source.txt
---
"""
    CANON.write_text(metadata + body, encoding="utf-8")
    OLD.unlink()

    replace_once(
        Path("docs/evidence/implementation/README.md"),
        "- [E1-R2 completion report](e1r2_completion_report.md) — frozen dry-run-first idempotent character-store bootstrap evidence from PR #432; current command and store-layout behavior remain handoff-, implementation-, and focused-smoke-owned.\n",
        "- [E1-R2 completion report](e1r2_completion_report.md) — frozen dry-run-first idempotent character-store bootstrap evidence from PR #432; current command and store-layout behavior remain handoff-, implementation-, and focused-smoke-owned.\n"
        "- [Docs Horizontal Status Sweep completion report](docs_horizontal_status_sweep_completion_report.md) — frozen docs-only horizontal status-convergence evidence from PR #434; current status, documentation model, and sequencing remain owned elsewhere.\n",
    )

    replace_once(
        Path("docs/mvp/README.md"),
        "- [E1-R2 completion report](../evidence/implementation/e1r2_completion_report.md) — source PR #432, merge `fefd3559ac32a37ed932faa130612a6a3da43c61`.\n",
        "- [E1-R2 completion report](../evidence/implementation/e1r2_completion_report.md) — source PR #432, merge `fefd3559ac32a37ed932faa130612a6a3da43c61`.\n"
        "- [Docs Horizontal Status Sweep completion report](../evidence/implementation/docs_horizontal_status_sweep_completion_report.md) — source PR #434, merge `6a0a384d3524fe98528643da666284576d974cd1`; docs-only convergence evidence with no production runtime boundary.\n",
    )
    replace_once(
        Path("docs/mvp/README.md"),
        "python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/e1r2_completion_report.md\n",
        "python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/e1r2_completion_report.md\n"
        "python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/docs_horizontal_status_sweep_completion_report.md\n",
    )

    replace_once(
        Path("docs/README.md"),
        "- [E1-R2 completion report](evidence/implementation/e1r2_completion_report.md)\n",
        "- [E1-R2 completion report](evidence/implementation/e1r2_completion_report.md)\n"
        "- [Docs Horizontal Status Sweep completion report](evidence/implementation/docs_horizontal_status_sweep_completion_report.md)\n",
    )

    smoke = Path("scripts/relaylm_documentation_current_boundary_smoke.py")
    replace_once(
        smoke,
        '    "docs/evidence/implementation/e1r2_completion_report.md",\n',
        '    "docs/evidence/implementation/e1r2_completion_report.md",\n'
        '    "docs/evidence/implementation/docs_horizontal_status_sweep_completion_report.md",\n',
    )
    replace_once(
        smoke,
        '''    "docs/evidence/implementation/e1r2_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "relaylm_source_pr: 432",
        "E1-R2 Character Store Bootstrap Completion Report",
        "Current character-store bootstrap behavior belongs to",
        "e1r2_completion_report-source.txt",
        "At source PR #432",
    ),
''',
        '''    "docs/evidence/implementation/e1r2_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "relaylm_source_pr: 432",
        "E1-R2 Character Store Bootstrap Completion Report",
        "Current character-store bootstrap behavior belongs to",
        "e1r2_completion_report-source.txt",
        "At source PR #432",
    ),
    "docs/evidence/implementation/docs_horizontal_status_sweep_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "relaylm_source_pr: 434",
        "Docs Horizontal Status Sweep Completion Report",
        "frozen documentation-convergence implementation evidence",
        "docs_horizontal_status_sweep_completion_report-source.txt",
        "source PR final-head/merge form",
    ),
''',
    )

    receipt_text = RECEIPT.read_text(encoding="utf-8")
    c23_heading = "### C1C23-001 — E1-R2 completion report\n"
    c23_start = receipt_text.index(c23_heading)
    pending_heading = "\n## Pending batches\n"
    pending_start = receipt_text.index(pending_heading, c23_start)
    c23_block = receipt_text[c23_start:pending_start]
    pending_merge = "merged_commit: pending\n"
    if c23_block.count(pending_merge) != 1:
        raise SystemExit("C1C23 pending merge anchor mismatch")
    c23_block = c23_block.replace(
        pending_merge, f"merged_commit: {PREVIOUS_MERGE}\n", 1
    )
    receipt_text = receipt_text[:c23_start] + c23_block + receipt_text[pending_start:]

    c24 = """
### C1C24-001 — docs horizontal status sweep completion report

```yaml
cutover_pr: 587
merged_commit: pending
old_path: docs/mvp/wave6/docs_horizontal_status_sweep_completion_report.md
old_blob_sha: c92bc7e856ef28e862a738c47668d46c67a71904
old_content_sha256: 889edab78de527869e3b94c764fadf9d9cce92b03f8adb946e42c3e6ca6a7627
source_commit: 86577b7712ea9efcc228f32a431b3606e552d40a
source_origin_commit: 6a0a384d3524fe98528643da666284576d974cd1
source_pr: 434
source_blob_sha: 2057afb52dab8903064853f0899d954c888bb213
source_content_sha256: bf0ba10a2f97539a4217fd8c78629c83d05e0e70d0a361759b1ac9ca3173464e
post_source_link_repair_commit: d1b920c3c7fcdf16053e8c9f449863cadfcb7384
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/docs_horizontal_status_sweep_completion_report.md
exact_source_snapshot: docs/evidence/implementation/docs_horizontal_status_sweep_completion_report-source.txt
exact_source_blob_sha: c92bc7e856ef28e862a738c47668d46c67a71904
verification:
  old_path_removed_in_pr_tree: true
  exact_pre_cutover_blob_reused: true
  source_pr_blob_recorded: true
  source_pr_blob_differs_from_pre_cutover_blob: true
  source_delta_is_single_wave5_canonical_path_repair: true
  canonical_evidence_metadata_added: true
  external_live_old_path_dependencies_at_cutover: 0
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 2
  implementation_evidence_index_updated: true
  mvp_evidence_index_updated: true
  documentation_router_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the docs-only horizontal current-status sweep from PR #434 while separating it from current Project Status, Documentation Model, feature-family behavior, sequencing, and operator guidance. The byte-exact snapshot retains the cutover input blob. The source PR final-head/merge blob is recorded separately because commit `d1b920c3c7fcdf16053e8c9f449863cadfcb7384` later repaired only the Wave 5 convergence-audit path. No external live old-path dependency existed at cutover; the two old-path occurrences were internal historical changed-file and validation-command text in the source report. This move removes the last Markdown file under `docs/mvp/wave6/` without adding a compatibility path.
"""
    if receipt_text.count(pending_heading) != 1:
        raise SystemExit("receipt pending heading mismatch")
    RECEIPT.write_text(
        receipt_text.replace(pending_heading, "\n" + c24 + pending_heading, 1),
        encoding="utf-8",
    )

    tmp_inventory = Path("docs/evidence/migrations/_tmp-cutover-1c24-inventory.txt")
    if tmp_inventory.exists():
        tmp_inventory.unlink()


if __name__ == "__main__":
    main()
