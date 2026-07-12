#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "docs/mvp/wave6/i5b_completion_report.md"
CANONICAL = "docs/evidence/implementation/i5b_completion_report.md"
SNAPSHOT = "docs/evidence/implementation/i5b_completion_report-source.txt"
MERGED_C1C19 = "be3cf9fc2ed5e85fd3dff4737f8598e13edb6907"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, body: str) -> None:
    (ROOT / path).write_text(body, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    body = read(path)
    count = body.count(old)
    if count != 1:
        raise AssertionError(f"{path}: expected one occurrence of {old!r}, found {count}")
    write(path, body.replace(old, new, 1))


def append_once(path: str, anchor: str, insertion: str) -> None:
    body = read(path)
    if insertion.strip() in body:
        return
    count = body.count(anchor)
    if count != 1:
        raise AssertionError(f"{path}: expected one anchor occurrence, found {count}")
    write(path, body.replace(anchor, anchor + insertion, 1))


def update_routers() -> None:
    replace_once(
        "docs/README.md",
        "[I-5B completion report](mvp/wave6/i5b_completion_report.md)",
        "[I-5B completion report](evidence/implementation/i5b_completion_report.md)",
    )
    replace_once(
        "docs/architecture/README.md",
        "[I-5B completion report](../mvp/wave6/i5b_completion_report.md)",
        "[I-5B completion report](../evidence/implementation/i5b_completion_report.md)",
    )
    replace_once(
        "docs/mvp/README.md",
        "[I-5B completion report](wave6/i5b_completion_report.md)",
        "[I-5B completion report](../evidence/implementation/i5b_completion_report.md)",
    )
    replace_once(
        "docs/mvp/README.md",
        "python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/i5b_completion_report.md",
        "python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/i5b_completion_report.md",
    )
    replace_once(
        "docs/evidence/waves/wave6_cross_slice_convergence_audit.md",
        "[I-5B completion report](../../mvp/wave6/i5b_completion_report.md)",
        "[I-5B completion report](../implementation/i5b_completion_report.md)",
    )


def update_handoff_and_index() -> None:
    append_once(
        "docs/evidence/implementation/README.md",
        "- [O1F completion report](o1f_completion_report.md) — frozen validation-only scheduler operational-hardening evidence from PR #429; current behavior remains architecture, implementation, and focused-smoke-owned.\n",
        "- [I-5B completion report](i5b_completion_report.md) — frozen Pin / Unpin apply, API/UI, durable-governance, and ranking-hint evidence from PR #430; current behavior remains handoff-, implementation-, and focused-smoke-owned.\n",
    )
    append_once(
        "docs/architecture/phase_i5b_pin_unpin_apply.md",
        "This phase does not implement hidden-memory retrieval, restore/unhide/purge, semantic memory rewriting, Secondary MEM consolidation, merge/supersession, Held Apply/Discard runtime, RelaySOUL mutation, queue/worker/scheduler changes, durable-finalization changes, automatic ranking learning, or Home-origin trusted formation.\n",
        "\n## Completion report\n\nThe frozen implementation evidence for this slice is recorded in [I-5B completion report](../evidence/implementation/i5b_completion_report.md). Current behavior remains owned by this handoff, the production implementation, and the focused I-5A/I-5B smoke suite.\n",
    )


def update_current_boundary_smoke() -> None:
    path = "scripts/relaylm_documentation_current_boundary_smoke.py"
    body = read(path)
    handoff_entry = '''    "docs/architecture/phase_i5b_pin_unpin_apply.md": (\n        "# Phase I-5B Pin / Unpin apply and ranking behavior",\n        "Pin state is a deterministic ranking hint only.",\n        "../evidence/implementation/i5b_completion_report.md",\n    ),\n'''
    canonical_entry = '''    "docs/evidence/implementation/i5b_completion_report.md": (\n        "relaylm_doc_type: implementation_completion_report",\n        "relaylm_source_pr: 430",\n        "I-5B completion report",\n        "Current Pin / Unpin behavior belongs to",\n        "i5b_completion_report-source.txt",\n        "At source PR #430",\n    ),\n'''
    if handoff_entry not in body:
        anchor = '    "docs/evidence/implementation/o1f_completion_report.md": (\n'
        if body.count(anchor) != 1:
            raise AssertionError("current-boundary handoff insertion anchor mismatch")
        body = body.replace(anchor, handoff_entry + anchor, 1)
    if canonical_entry not in body:
        anchor = '    "docs/evidence/implementation/e1r4_completion_report.md": (\n'
        if body.count(anchor) != 1:
            raise AssertionError("current-boundary canonical insertion anchor mismatch")
        body = body.replace(anchor, canonical_entry + anchor, 1)
    write(path, body)


def update_receipt() -> None:
    path = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
    body = read(path)
    c19_anchor = "### C1C19-001 — O1F completion report\n\n```yaml\ncutover_pr: 581\nmerged_commit: pending\n"
    c19_final = f"### C1C19-001 — O1F completion report\n\n```yaml\ncutover_pr: 581\nmerged_commit: {MERGED_C1C19}\n"
    if c19_anchor in body:
        body = body.replace(c19_anchor, c19_final, 1)
    elif c19_final not in body:
        raise AssertionError("C1C19 receipt anchor mismatch")

    entry = '''### C1C20-001 — I-5B completion report

```yaml
cutover_pr: pending
merged_commit: pending
old_path: docs/mvp/wave6/i5b_completion_report.md
old_blob_sha: 19d631470dc0cf16e65c214169e3097758381de9
old_content_sha256: 2efce2a61fb09b9ed4226d2a09e6e6b78645bf11f65badc855e03f7e64b8aa85
source_commit: eac44fb0038c0a7eadd94c1d29b2ce90f52a6349
source_origin_commit: 734a3880035651f91eb065b892fc41af6f5cc026
source_pr: 430
recorded_on: 2026-06-28
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/i5b_completion_report.md
exact_source_snapshot: docs/evidence/implementation/i5b_completion_report-source.txt
exact_source_blob_sha: 19d631470dc0cf16e65c214169e3097758381de9
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 1
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 1
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 3
  i5b_architecture_handoff_updated: true
  wave6_convergence_evidence_link_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  dedicated_i5b_workflow_absent_in_current_tree: true
  cutover_preparation_self_test_reused_without_path_change: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_i5a_i5b_smokes: pending
  soul_lab_pin_unpin_ui_validation: pending
  documentation_link_check: pending
  documentation_semantic_audit: pending
  completion_report_model_and_file_checks: pending
  completion_report_pr_link_check: pending
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the complete I-5B Pin / Unpin apply, API/UI, durable-governance, and ranking-hint boundary from PR #430 while separating it from current handoff-, implementation-, and focused-smoke-owned behavior. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. Four live Markdown-link dependencies and one repository-root validation literal are moved to the canonical path; legacy references remain only in this migration receipt and frozen exact source snapshots. The dedicated I-5B workflow named by the historical source report is no longer present in the current tree and is not recreated. The migration-aware completion-report model and PR-link checks apply without validator changes.

'''
    marker = "## Pending batches\n"
    if "### C1C20-001 — I-5B completion report" not in body:
        if body.count(marker) != 1:
            raise AssertionError("receipt pending-batches marker mismatch")
        body = body.replace(marker, entry + marker, 1)
    write(path, body)


def assert_no_live_legacy_paths() -> None:
    excluded = {
        ROOT / SNAPSHOT,
        ROOT / "docs/evidence/waves/wave6_cross_slice_convergence_audit-source.txt",
        ROOT / "docs/evidence/migrations/documentation-hard-cutover-receipt.md",
        ROOT / "scripts/tmp_c1c20_i5b_applicator.py",
    }
    variants = (
        "docs/mvp/wave6/i5b_completion_report.md",
        "mvp/wave6/i5b_completion_report.md",
        "../mvp/wave6/i5b_completion_report.md",
        "../../mvp/wave6/i5b_completion_report.md",
    )
    offenders: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path in excluded or ".git" in path.parts:
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if any(value in body for value in variants):
            offenders.append(str(path.relative_to(ROOT)))
    if offenders:
        raise AssertionError(f"live legacy I-5B references remain: {offenders}")


def main() -> None:
    update_routers()
    update_handoff_and_index()
    update_current_boundary_smoke()
    update_receipt()
    assert_no_live_legacy_paths()
    print("Cutover 1C-20 I-5B applicator completed")


if __name__ == "__main__":
    main()
