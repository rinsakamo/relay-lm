#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "docs/mvp/wave6/i7c_completion_report.md"
CANONICAL = "docs/evidence/implementation/i7c_completion_report.md"
SNAPSHOT = "docs/evidence/implementation/i7c_completion_report-source.txt"
EXPECTED_BLOB = "447298a00d418f461abda33060e7f59d96656c64"
EXPECTED_SHA256 = "97e242a355bb0fd204492fb697ed6523ed85812cd3e73e7cb73696a89e258907"
MERGED_C1C20 = "ca1a921eba7131072c3608a5f2032e2d6008f770"
SOURCE_HEAD = "4add07ae3084b8f4bf1364189411014bb71cf118"
SOURCE_MERGE = "21d10bfed22ed9626e4224bf927ff59a5e399505"
SOURCE_PR = 431
RECORDED_ON = "2026-06-27"


def path(rel: str) -> Path:
    return ROOT / rel


def read(rel: str) -> str:
    return path(rel).read_text(encoding="utf-8")


def write(rel: str, body: str) -> None:
    path(rel).write_text(body, encoding="utf-8")


def replace_once(rel: str, old: str, new: str) -> None:
    body = read(rel)
    count = body.count(old)
    if count != 1:
        raise AssertionError(f"{rel}: expected one occurrence of {old!r}, found {count}")
    write(rel, body.replace(old, new, 1))


def append_after_once(rel: str, anchor: str, insertion: str) -> None:
    body = read(rel)
    if insertion.strip() in body:
        return
    count = body.count(anchor)
    if count != 1:
        raise AssertionError(f"{rel}: expected one anchor occurrence, found {count}")
    write(rel, body.replace(anchor, anchor + insertion, 1))


def git_blob_sha(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def create_evidence() -> None:
    old_path = path(OLD)
    raw = old_path.read_bytes()
    if git_blob_sha(raw) != EXPECTED_BLOB:
        raise AssertionError("I-7C source Git blob mismatch")
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise AssertionError("I-7C source SHA-256 mismatch")

    path(SNAPSHOT).write_bytes(raw)
    source = raw.decode("utf-8")
    marker = "## Scope\n"
    if source.count(marker) != 1:
        raise AssertionError("I-7C source scope marker mismatch")
    historical = marker + source.split(marker, 1)[1]
    historical = historical.replace(
        "docs/mvp/wave6/i7c_completion_report.md",
        "docs/evidence/implementation/i7c_completion_report.md",
    )
    historical = historical.replace(
        "Expected PR validation:",
        "Expected validation commands for source PR #431:",
    )
    historical = historical.replace(
        "Local authoring validation before PR creation:",
        "Local authoring validation recorded at source PR #431:",
    )
    historical = historical.replace(
        "For the Wave 6 convergence PR:",
        "At source PR #431, the later Wave 6 convergence thread was expected to:",
    )
    historical = historical.replace(
        "## Known limitations\n",
        (
            "At source PR #431, GitHub Actions was the execution source of truth for the "
            "listed validation. Current validation routing belongs to the consolidated "
            "workflow and smoke inventory rather than the removed dedicated workflow.\n\n"
            "## Known limitations\n"
        ),
        1,
    )

    canonical = f'''---
relaylm_doc_type: implementation_completion_report
relaylm_authority: phase_i7c_held_governance_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/phase_i7c_held_apply_discard_runtime.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current Held Apply / Discard runtime, API, UI, or governance behavior
  - current queue lifecycle or worker execution behavior
  - current implementation sequencing or release readiness
  - current operator procedure
relaylm_source_commit: {SOURCE_HEAD}
relaylm_source_origin_commit: {SOURCE_MERGE}
relaylm_source_pr: {SOURCE_PR}
relaylm_recorded_on: {RECORDED_ON}
relaylm_source_blob: {EXPECTED_BLOB}
relaylm_source_content_sha256: {EXPECTED_SHA256}
relaylm_exact_source_snapshot: i7c_completion_report-source.txt
---
# I-7C completion report

## Status and authority

This document is frozen implementation evidence for the I-7C Held Apply / Discard runtime-governance, API/UI, durable-evidence, and leakage-boundary slice introduced by PR #431, whose final source head is `{SOURCE_HEAD}` and merge commit is `{SOURCE_MERGE}`. Current repository-wide status belongs to [Project Status](../../PROJECT_STATUS.md). Current Held Apply / Discard behavior belongs to [Phase I-7C Held Apply / Discard Runtime](../../architecture/phase_i7c_held_apply_discard_runtime.md), the production implementation, and the focused I-7A/B and I-7C smoke suite.

The exact pre-cutover report is retained byte-for-byte as [i7c_completion_report-source.txt](i7c_completion_report-source.txt). Statements below describe the source PR boundary unless explicitly qualified. Legacy-path strings inside the exact snapshot are historical source text, not live repository references.

Last reviewed: {RECORDED_ON} JST

This report is evidence for one implementation pull request. It is not current runtime, repository-wide status, sequencing, release-readiness, queue-lifecycle, worker-execution, or operator-procedure authority.

{historical}'''
    write(CANONICAL, canonical)
    old_path.unlink()


def update_references() -> None:
    replace_once(
        "docs/README.md",
        "[I-7C completion report](mvp/wave6/i7c_completion_report.md)",
        "[I-7C completion report](evidence/implementation/i7c_completion_report.md)",
    )
    replace_once(
        "docs/architecture/README.md",
        "[I-7C completion report](../mvp/wave6/i7c_completion_report.md)",
        "[I-7C completion report](../evidence/implementation/i7c_completion_report.md)",
    )
    replace_once(
        "docs/mvp/README.md",
        "[I-7C completion report](wave6/i7c_completion_report.md)",
        "[I-7C completion report](../evidence/implementation/i7c_completion_report.md)",
    )
    replace_once(
        "docs/mvp/README.md",
        "python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/i7c_completion_report.md",
        "python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/i7c_completion_report.md",
    )
    replace_once(
        "docs/evidence/waves/wave6_cross_slice_convergence_audit.md",
        "[I-7C completion report](../../mvp/wave6/i7c_completion_report.md)",
        "[I-7C completion report](../implementation/i7c_completion_report.md)",
    )
    replace_once(
        "scripts/relaylm_ci_consolidated_smoke.py",
        '["scripts/relaylm_mvp_completion_report_smoke.py", "docs/mvp/wave6/i7c_completion_report.md"]',
        '["scripts/relaylm_mvp_completion_report_smoke.py", "docs/evidence/implementation/i7c_completion_report.md"]',
    )

    old_line = (
        "I-7C adds dedicated runtime, API, concurrency, security, and UI smoke coverage "
        "plus a GitHub Actions workflow. The completion report is "
        "`docs/mvp/wave6/i7c_completion_report.md`."
    )
    new_block = (
        "I-7C adds dedicated runtime, API, concurrency, security, and UI smoke coverage. "
        "Current validation is routed through the consolidated smoke inventory.\n\n"
        "## Completion report\n\n"
        "The frozen implementation evidence for this slice is recorded in "
        "[I-7C completion report](../evidence/implementation/i7c_completion_report.md). "
        "Current behavior remains owned by this handoff, the production implementation, "
        "and the focused I-7A/B and I-7C smoke suite."
    )
    replace_once(
        "docs/architecture/phase_i7c_held_apply_discard_runtime.md",
        old_line,
        new_block,
    )

    append_after_once(
        "docs/evidence/implementation/README.md",
        (
            "- [I-5B completion report](i5b_completion_report.md) — frozen Pin / Unpin "
            "apply, API/UI, durable-governance, and ranking-hint evidence from PR #430; "
            "current behavior remains handoff-, implementation-, and focused-smoke-owned.\n"
        ),
        (
            "- [I-7C completion report](i7c_completion_report.md) — frozen Held Apply / "
            "Discard runtime-governance, API/UI, durable-evidence, and leakage-boundary "
            "evidence from PR #431; current behavior remains handoff-, implementation-, "
            "and focused-smoke-owned.\n"
        ),
    )


def update_current_boundary_smoke() -> None:
    rel = "scripts/relaylm_documentation_current_boundary_smoke.py"
    body = read(rel)
    handoff_entry = '''    "docs/architecture/phase_i7c_held_apply_discard_runtime.md": (
        "# Phase I-7C Held Apply / Discard Runtime",
        "I-7C connects the I-7A/B Held Apply / Discard contract",
        "../evidence/implementation/i7c_completion_report.md",
    ),
'''
    canonical_entry = '''    "docs/evidence/implementation/i7c_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "relaylm_source_pr: 431",
        "I-7C completion report",
        "Current Held Apply / Discard behavior belongs to",
        "i7c_completion_report-source.txt",
        "At source PR #431",
    ),
'''
    if handoff_entry not in body:
        anchor = '    "docs/evidence/implementation/o1f_completion_report.md": (\n'
        if body.count(anchor) != 1:
            raise AssertionError("current-boundary handoff anchor mismatch")
        body = body.replace(anchor, handoff_entry + anchor, 1)
    if canonical_entry not in body:
        anchor = '    "docs/evidence/implementation/e1r4_completion_report.md": (\n'
        if body.count(anchor) != 1:
            raise AssertionError("current-boundary canonical anchor mismatch")
        body = body.replace(anchor, canonical_entry + anchor, 1)
    write(rel, body)


def update_receipt() -> None:
    rel = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
    body = read(rel)
    c20_pending = "### C1C20-001 — I-5B completion report\n\n```yaml\ncutover_pr: 582\nmerged_commit: pending\n"
    c20_final = (
        "### C1C20-001 — I-5B completion report\n\n```yaml\ncutover_pr: 582\n"
        f"merged_commit: {MERGED_C1C20}\n"
    )
    if c20_pending in body:
        body = body.replace(c20_pending, c20_final, 1)
    elif c20_final not in body:
        raise AssertionError("C1C20 receipt anchor mismatch")

    pr_number = os.environ.get("PR_NUMBER", "pending")
    entry = f'''### C1C21-001 — I-7C completion report

```yaml
cutover_pr: {pr_number}
merged_commit: pending
old_path: {OLD}
old_blob_sha: {EXPECTED_BLOB}
old_content_sha256: {EXPECTED_SHA256}
source_commit: {SOURCE_HEAD}
source_origin_commit: {SOURCE_MERGE}
source_pr: {SOURCE_PR}
recorded_on: {RECORDED_ON}
disposition: evidence_retained
new_canonical_path: {CANONICAL}
exact_source_snapshot: {SNAPSHOT}
exact_source_blob_sha: {EXPECTED_BLOB}
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 3
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 3
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 3
  i7c_architecture_handoff_updated: true
  wave6_convergence_evidence_link_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  consolidated_held_governance_smoke_updated: true
  dedicated_i7c_workflow_absent_in_current_tree: true
  cutover_preparation_self_test_reused_without_path_change: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_i7ab_i7c_smokes: pending
  related_i4d_o1e_b3_regressions: pending
  soul_lab_held_governance_ui_validation: pending
  documentation_link_check: pending
  documentation_semantic_audit: pending
  completion_report_model_and_file_checks: pending
  completion_report_pr_link_check: pending
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the complete I-7C Held Apply / Discard runtime-governance, API/UI, durable-evidence, and leakage-boundary implementation boundary from PR #431 while separating it from current handoff-, implementation-, queue-lifecycle-, worker-, and focused-smoke-owned behavior. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. Four live Markdown-link dependencies and three repository-root validation or handoff literals are moved to the canonical path; legacy references remain only in this migration receipt and frozen exact source snapshots. The dedicated I-7C workflow named by the historical source report is no longer present in the current tree and is not recreated. The migration-aware completion-report model and PR-link checks apply without validator changes.

'''
    marker = "## Pending batches\n"
    if "### C1C21-001 — I-7C completion report" not in body:
        if body.count(marker) != 1:
            raise AssertionError("receipt pending-batches marker mismatch")
        body = body.replace(marker, entry + marker, 1)
    write(rel, body)


def assert_boundaries() -> None:
    if path(OLD).exists():
        raise AssertionError("legacy I-7C live path remains")
    raw = path(SNAPSHOT).read_bytes()
    if git_blob_sha(raw) != EXPECTED_BLOB:
        raise AssertionError("exact snapshot blob mismatch")
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise AssertionError("exact snapshot SHA-256 mismatch")
    if path(".github/workflows/phase-i7c-held-governance-runtime.yml").exists():
        raise AssertionError("historical dedicated I-7C workflow unexpectedly exists")

    excluded = {
        path(SNAPSHOT),
        path("docs/evidence/migrations/documentation-hard-cutover-receipt.md"),
        path("scripts/tmp_c1c21_i7c_applicator.py"),
    }
    variants = (
        "docs/mvp/wave6/i7c_completion_report.md",
        "mvp/wave6/i7c_completion_report.md",
        "../mvp/wave6/i7c_completion_report.md",
        "../../mvp/wave6/i7c_completion_report.md",
    )
    offenders: list[str] = []
    for candidate in ROOT.rglob("*"):
        if not candidate.is_file() or ".git" in candidate.parts:
            continue
        if candidate in excluded or candidate.name.endswith("-source.txt"):
            continue
        try:
            body = candidate.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if any(value in body for value in variants):
            offenders.append(str(candidate.relative_to(ROOT)))
    if offenders:
        raise AssertionError(f"live legacy I-7C references remain: {offenders}")


def main() -> None:
    create_evidence()
    update_references()
    update_current_boundary_smoke()
    update_receipt()
    assert_boundaries()
    print("Cutover 1C-21 I-7C applicator completed")


if __name__ == "__main__":
    main()
