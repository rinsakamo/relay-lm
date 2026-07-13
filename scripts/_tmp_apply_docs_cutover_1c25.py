#!/usr/bin/env python3
"""Apply temporary Cutover 1C-25 E1 evidence migration."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

OLD = Path("docs/mvp/wave5/e1_completion_report.md")
CANON = Path("docs/evidence/implementation/e1_completion_report.md")
SNAPSHOT = Path("docs/evidence/implementation/e1_completion_report-source.txt")
RECEIPT = Path("docs/evidence/migrations/documentation-hard-cutover-receipt.md")
OLD_PATH = OLD.as_posix()
CANON_PATH = CANON.as_posix()

PRE_BLOB = "c87b9929ce6e527ef2b94beeb2059f98439b6019"
PRE_SHA = "980cc5898f3b6cb8bc7ad0b502740a5ca9f79a54ebfa023c24d5d1c3a55289da"
SOURCE_COMMIT = "a4521f2a450ed52de3101e208676571c4c6b33e2"
SOURCE_ORIGIN = "95c159ff747a167cd6cf99c7c5df656fd01e345d"
SOURCE_BLOB = "9b16c8875668f8bde40de809c472e7873da3f34e"
SOURCE_SHA = "e5e2d6736aa3f9236e3da3b6c4ed0888fb9b046e18e2cba6af98d6eb6f5e63ec"
REPAIR_COMMIT = "80c6e775ae30ba68b1eb51148b4395320364d8d3"
PREVIOUS_MERGE = "aa40f19cdf808c9876e40b0a32ee9e5a3f1187e8"


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
        raise SystemExit(f"{path}: replacement anchor count {count}, expected 1: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


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
    b"docs/architecture/wave4_cross_slice_convergence_audit.md",
    b"docs/evidence/waves/wave4_cross_slice_convergence_audit.md",
)
if expected_current != current:
    raise SystemExit("source-to-pre-cutover delta is not the single recorded Wave 4 path repair")

SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
SNAPSHOT.write_bytes(current)

source_text = current.decode("utf-8")
parts = source_text.split("---\n", 2)
if len(parts) != 3:
    raise SystemExit("source front matter boundary mismatch")
body = parts[2].replace(OLD_PATH, CANON_PATH)
heading = "# E1 MVP Evaluation Evidence Consolidation Completion Report\n"
if body.count(heading) != 1:
    raise SystemExit("report heading mismatch")
status = """
## Status and authority

This document is frozen implementation evidence for the docs-only E1 MVP evaluation-consolidation slice introduced by PR #425. Current E1 evaluation interpretation belongs to [E1 MVP Evaluation Evidence Consolidation](../../architecture/e1_evaluation_consolidation.md); current repository-wide status belongs to [Project Status](../../PROJECT_STATUS.md); current sequencing belongs to [Project Execution Plan](../../architecture/project_execution_plan.md).

The exact cutover input is retained byte-for-byte as [e1_completion_report-source.txt](e1_completion_report-source.txt). The source PR final-head/merge form used Git blob `9b16c8875668f8bde40de809c472e7873da3f34e`; the cutover input uses Git blob `c87b9929ce6e527ef2b94beeb2059f98439b6019` and differs only by the later canonical Wave 4 convergence-audit path repair from commit `80c6e775ae30ba68b1eb51148b4395320364d8d3`.

Last reviewed: 2026-06-27 JST

This report is evidence for one docs-only evaluation-consolidation PR. It is not current runtime, E1 behavior, repository-wide status, sequencing, release-readiness, or operator-procedure authority. Later E1-R1 through E1-R5 implementation is recorded by their dedicated handoffs and canonical evidence reports.

"""
body = body.replace(heading, heading + status, 1)
metadata = """---
relaylm_doc_type: implementation_completion_report
relaylm_authority: e1_mvp_evaluation_consolidation_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: evaluation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/e1_evaluation_consolidation.md
  - ../../architecture/e1_local_runtime_evaluation_2026_06_25.md
  - ../waves/wave5_cross_slice_convergence_audit.md
relaylm_not_authoritative_for:
  - current E1 runtime or evaluation behavior
  - current repository-wide implementation status
  - current implementation sequencing or release readiness
  - current operator procedure
relaylm_source_commit: a4521f2a450ed52de3101e208676571c4c6b33e2
relaylm_source_origin_commit: 95c159ff747a167cd6cf99c7c5df656fd01e345d
relaylm_source_pr: 425
relaylm_recorded_on: 2026-06-27
relaylm_source_blob: 9b16c8875668f8bde40de809c472e7873da3f34e
relaylm_source_content_sha256: e5e2d6736aa3f9236e3da3b6c4ed0888fb9b046e18e2cba6af98d6eb6f5e63ec
relaylm_pre_cutover_blob: c87b9929ce6e527ef2b94beeb2059f98439b6019
relaylm_pre_cutover_content_sha256: 980cc5898f3b6cb8bc7ad0b502740a5ca9f79a54ebfa023c24d5d1c3a55289da
relaylm_exact_source_snapshot: e1_completion_report-source.txt
---
"""
CANON.write_text(metadata + body, encoding="utf-8")
OLD.unlink()

replace_once(
    Path("docs/evidence/implementation/README.md"),
    "- [Docs Horizontal Status Sweep completion report](docs_horizontal_status_sweep_completion_report.md) — frozen docs-only horizontal status-convergence evidence from PR #434; current status, documentation model, and sequencing remain owned elsewhere.\n",
    "- [Docs Horizontal Status Sweep completion report](docs_horizontal_status_sweep_completion_report.md) — frozen docs-only horizontal status-convergence evidence from PR #434; current status, documentation model, and sequencing remain owned elsewhere.\n"
    "- [E1 MVP Evaluation Evidence Consolidation completion report](e1_completion_report.md) — frozen docs-only evaluation-consolidation evidence from PR #425; current E1 behavior and interpretation remain architecture-, handoff-, implementation-, and evaluation-owned.\n",
)
replace_once(
    Path("docs/README.md"),
    "- [E1 completion report](mvp/wave5/e1_completion_report.md)\n",
    "- [E1 completion report](evidence/implementation/e1_completion_report.md)\n",
)
replace_once(
    Path("docs/architecture/README.md"),
    "- [E1 completion report](../mvp/wave5/e1_completion_report.md)\n",
    "- [E1 completion report](../evidence/implementation/e1_completion_report.md)\n",
)
replace_once(
    Path("docs/mvp/README.md"),
    "- [E1 completion report](wave5/e1_completion_report.md) — source PR #425, merge `95c159ff747a167cd6cf99c7c5df656fd01e345d`.\n",
    "- [E1 completion report](../evidence/implementation/e1_completion_report.md) — source PR #425, merge `95c159ff747a167cd6cf99c7c5df656fd01e345d`.\n",
)
replace_once(
    Path("docs/mvp/README.md"),
    "python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/o1f_completion_report.md\n",
    "python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/e1_completion_report.md\n"
    "python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/o1f_completion_report.md\n",
)
replace_once(
    Path("docs/evidence/waves/wave5_cross_slice_convergence_audit.md"),
    "`docs/mvp/wave5/e1_completion_report.md`",
    "`docs/evidence/implementation/e1_completion_report.md`",
)
replace_once(
    Path("scripts/relaylm_e1_evaluation_consolidation_smoke.py"),
    '    "docs/mvp/wave5/e1_completion_report.md": (\n        "relaylm_doc_type: implementation_completion_report",\n        "## Implemented production boundary",\n        "No runtime behavior changed.",\n        "E1 evaluation consolidation",\n    ),\n',
    '    "docs/evidence/implementation/e1_completion_report.md": (\n        "relaylm_doc_type: implementation_completion_report",\n        "relaylm_source_pr: 425",\n        "E1 MVP Evaluation Evidence Consolidation Completion Report",\n        "frozen implementation evidence",\n        "e1_completion_report-source.txt",\n        "source PR final-head/merge form",\n    ),\n',
)
replace_once(
    Path("scripts/relaylm_wave5_cross_slice_convergence_smoke.py"),
    '        "docs/mvp/wave5/e1_completion_report.md",\n',
    '        "docs/evidence/implementation/e1_completion_report.md",\n',
)
replace_once(
    Path(".github/workflows/e1-evaluation-consolidation.yml"),
    "PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave5/e1_completion_report.md",
    "PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/e1_completion_report.md",
)
replace_once(
    Path(".github/workflows/wave5-cross-slice-convergence.yml"),
    "PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave5/e1_completion_report.md",
    "PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/e1_completion_report.md",
)

smoke = Path("scripts/relaylm_documentation_current_boundary_smoke.py")
replace_once(
    smoke,
    '    "docs/architecture/e1_evaluation_consolidation.md",\n',
    '    "docs/architecture/e1_evaluation_consolidation.md",\n    "docs/evidence/implementation/e1_completion_report.md",\n',
)
replace_once(
    smoke,
    '    "docs/architecture/e1r1_trusted_home_scene_admission.md": (\n',
    '    "docs/evidence/implementation/e1_completion_report.md": (\n'
    '        "relaylm_doc_type: implementation_completion_report",\n'
    '        "relaylm_source_pr: 425",\n'
    '        "E1 MVP Evaluation Evidence Consolidation Completion Report",\n'
    '        "frozen implementation evidence",\n'
    '        "e1_completion_report-source.txt",\n'
    '        "source PR final-head/merge form",\n'
    '    ),\n'
    '    "docs/architecture/e1r1_trusted_home_scene_admission.md": (\n',
)

receipt_text = RECEIPT.read_text(encoding="utf-8")
c24_heading = "### C1C24-001 — docs horizontal status sweep completion report\n"
c24_start = receipt_text.index(c24_heading)
pending_heading = "\n## Pending batches\n"
pending_start = receipt_text.index(pending_heading, c24_start)
c24_block = receipt_text[c24_start:pending_start]
if c24_block.count("merged_commit: pending\n") != 1:
    raise SystemExit("C1C24 pending merge anchor mismatch")
c24_block = c24_block.replace("merged_commit: pending\n", f"merged_commit: {PREVIOUS_MERGE}\n", 1)
receipt_text = receipt_text[:c24_start] + c24_block + receipt_text[pending_start:]

c25 = """
### C1C25-001 — E1 MVP evaluation consolidation completion report

```yaml
cutover_pr: 588
merged_commit: pending
old_path: docs/mvp/wave5/e1_completion_report.md
old_blob_sha: c87b9929ce6e527ef2b94beeb2059f98439b6019
old_content_sha256: 980cc5898f3b6cb8bc7ad0b502740a5ca9f79a54ebfa023c24d5d1c3a55289da
source_commit: a4521f2a450ed52de3101e208676571c4c6b33e2
source_origin_commit: 95c159ff747a167cd6cf99c7c5df656fd01e345d
source_pr: 425
source_blob_sha: 9b16c8875668f8bde40de809c472e7873da3f34e
source_content_sha256: e5e2d6736aa3f9236e3da3b6c4ed0888fb9b046e18e2cba6af98d6eb6f5e63ec
post_source_link_repair_commit: 80c6e775ae30ba68b1eb51148b4395320364d8d3
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/e1_completion_report.md
exact_source_snapshot: docs/evidence/implementation/e1_completion_report-source.txt
exact_source_blob_sha: c87b9929ce6e527ef2b94beeb2059f98439b6019
verification:
  old_path_removed_in_pr_tree: true
  exact_pre_cutover_blob_reused: true
  source_pr_blob_recorded: true
  source_pr_blob_differs_from_pre_cutover_blob: true
  source_delta_is_single_wave4_canonical_path_repair: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 5
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 5
  markdown_link_referrer_files_updated_in_pr_tree: 3
  markdown_link_occurrences_updated_in_pr_tree: 3
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 2
  frozen_wave5_source_snapshot_legacy_references_preserved: true
  implementation_evidence_index_updated: true
  mvp_evidence_index_updated: true
  documentation_router_updated: true
  architecture_router_updated: true
  e1_evaluation_consolidation_smoke_updated: true
  wave5_convergence_evidence_and_smoke_updated: true
  e1_and_wave5_workflows_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1_evaluation_smoke: passed
  wave5_cross_slice_convergence_smoke: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the docs-only E1 MVP evaluation-consolidation boundary from PR #425 while separating it from current E1 architecture, later E1-R1 through E1-R5 implementation, repository-wide status, sequencing, and operator guidance. The byte-exact snapshot retains the cutover input blob. The source PR final-head/merge blob is recorded separately because commit `80c6e775ae30ba68b1eb51148b4395320364d8d3` later repaired only the Wave 4 convergence-audit path. Five repository-root literals and three Markdown links are moved to the canonical path; historical old-path references remain only in the migration receipt and frozen exact source snapshots.

"""
receipt_text = receipt_text.replace(pending_heading, "\n" + c25 + pending_heading, 1)
RECEIPT.write_text(receipt_text, encoding="utf-8")

print("Cutover 1C-25 applied")
