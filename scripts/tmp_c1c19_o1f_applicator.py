#!/usr/bin/env python3
from pathlib import Path

OLD = "docs/mvp/wave6/o1f_completion_report.md"
NEW = "docs/evidence/implementation/o1f_completion_report.md"


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def replace_or_assert(path: str, old: str, new: str) -> None:
    text = read(path)
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1 and new_count == 0:
        write(path, text.replace(old, new, 1))
        return
    if old_count == 0 and new_count == 1:
        return
    raise SystemExit(
        f"{path}: unexpected replacement state old={old_count} new={new_count}: {old!r}"
    )


replace_or_assert(
    "docs/README.md",
    "[O1F completion report](mvp/wave6/o1f_completion_report.md)",
    "[O1F completion report](evidence/implementation/o1f_completion_report.md)",
)
replace_or_assert(
    "docs/architecture/README.md",
    "[O1F completion report](../mvp/wave6/o1f_completion_report.md)",
    "[O1F completion report](../evidence/implementation/o1f_completion_report.md)",
)
replace_or_assert(
    "docs/mvp/README.md",
    "[O1F completion report](wave6/o1f_completion_report.md)",
    "[O1F completion report](../evidence/implementation/o1f_completion_report.md)",
)
replace_or_assert("docs/mvp/README.md", OLD, NEW)
replace_or_assert(
    "docs/architecture/o1f_operational_validation.md",
    OLD,
    NEW,
)
replace_or_assert(
    "docs/architecture/o1f_operational_validation.md",
    "[O1F completion report](../mvp/wave6/o1f_completion_report.md)",
    "[O1F completion report](../evidence/implementation/o1f_completion_report.md)",
)
replace_or_assert(
    "docs/evidence/waves/wave6_cross_slice_convergence_audit.md",
    "[O1F completion report](../../mvp/wave6/o1f_completion_report.md)",
    "[O1F completion report](../implementation/o1f_completion_report.md)",
)

path = "docs/evidence/implementation/README.md"
text = read(path)
entry = "- [O1F completion report](o1f_completion_report.md) — frozen validation-only scheduler operational-hardening evidence from PR #429; current behavior remains architecture, implementation, and focused-smoke-owned.\n"
if entry not in text:
    anchor = "- [E1-R5 completion report](e1r5_completion_report.md) — frozen bounded Primary recall candidate-discovery implementation evidence from PR #439; current behavior and the PR #491 fold-in remain architecture-owned.\n"
    if text.count(anchor) != 1:
        raise SystemExit(f"{path}: implementation-router anchor mismatch")
    write(path, text.replace(anchor, anchor + entry, 1))

path = "scripts/relaylm_documentation_current_boundary_smoke.py"
text = read(path)
current_old = '    "docs/architecture/o1e_scheduler_operational_controls.md",\n    "docs/architecture/o2_supervised_scheduler_service.md",\n'
current_new = '    "docs/architecture/o1e_scheduler_operational_controls.md",\n    "docs/architecture/o1f_operational_validation.md",\n    "docs/architecture/o2_supervised_scheduler_service.md",\n'
if current_new not in text:
    if text.count(current_old) != 1:
        raise SystemExit(f"{path}: current-doc insertion anchor mismatch")
    text = text.replace(current_old, current_new, 1)

o1e_old = '''    "docs/architecture/o1e_scheduler_operational_controls.md": (\n        "# O1E Scheduler Operational Controls",\n        "Status: implemented in this slice.",\n        "O1F is complete as validation-only operational hardening over this caller-invoked boundary.",\n        "O2 and O3 are implemented in dedicated handoffs as opt-in layers above O1E",\n    ),\n    "docs/architecture/o2_supervised_scheduler_service.md": (\n'''
o1e_new = '''    "docs/architecture/o1e_scheduler_operational_controls.md": (\n        "# O1E Scheduler Operational Controls",\n        "Status: implemented in this slice.",\n        "O1F is complete as validation-only operational hardening over this caller-invoked boundary.",\n        "O2 and O3 are implemented in dedicated handoffs as opt-in layers above O1E",\n    ),\n    "docs/architecture/o1f_operational_validation.md": (\n        "# O1F Operational Validation",\n        "Status: implemented in this slice.",\n        "validate_scheduler_operational_boundary_once",\n        "../evidence/implementation/o1f_completion_report.md",\n    ),\n    "docs/architecture/o2_supervised_scheduler_service.md": (\n'''
if '    "docs/architecture/o1f_operational_validation.md": (\n' not in text:
    if text.count(o1e_old) != 1:
        raise SystemExit(f"{path}: O1F handoff REQUIRED anchor mismatch")
    text = text.replace(o1e_old, o1e_new, 1)

evidence_old = '    "docs/evidence/implementation/e1r4_completion_report.md": (\n'
evidence_new = '''    "docs/evidence/implementation/o1f_completion_report.md": (\n        "relaylm_doc_type: implementation_completion_report",\n        "relaylm_source_pr: 429",\n        "O1F Completion Report",\n        "Current O1F behavior belongs to",\n        "o1f_completion_report-source.txt",\n        "At source PR #429",\n    ),\n    "docs/evidence/implementation/e1r4_completion_report.md": (\n'''
if '    "docs/evidence/implementation/o1f_completion_report.md": (\n' not in text:
    if text.count(evidence_old) != 1:
        raise SystemExit(f"{path}: canonical evidence REQUIRED anchor mismatch")
    text = text.replace(evidence_old, evidence_new, 1)
write(path, text)

path = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
text = read(path)
c1c18_old = "### C1C18-001 — E1-R5 completion report\n\n```yaml\ncutover_pr: 576\nmerged_commit: pending\n"
c1c18_new = "### C1C18-001 — E1-R5 completion report\n\n```yaml\ncutover_pr: 576\nmerged_commit: 91c21085b468052f77b65d5e1577cd1940fe0b2b\n"
if c1c18_new not in text:
    if text.count(c1c18_old) != 1:
        raise SystemExit(f"{path}: C1C18 finalization anchor mismatch")
    text = text.replace(c1c18_old, c1c18_new, 1)

if "### C1C19-001 — O1F completion report" not in text:
    pending_anchor = "## Pending batches\n"
    if text.count(pending_anchor) != 1:
        raise SystemExit(f"{path}: pending-batches anchor mismatch")
    c1c19 = '''### C1C19-001 — O1F completion report\n\n```yaml\ncutover_pr: 581\nmerged_commit: pending\nold_path: docs/mvp/wave6/o1f_completion_report.md\nold_blob_sha: cae70dbe1648ed6757af928eeae0becd7fd313dd\nold_content_sha256: b7c61bd6711e2f8ab741e4f73df5715d64229cfa5f11865c1004eed9d5a6e976\nsource_commit: 14b91b5ed21f240aa92eb54189e0b2d36ab089f7\nsource_origin_commit: 961fff2d935cd764e81e577887328e86363e56d5\nsource_pr: 429\nrecorded_on: 2026-06-27\ndisposition: evidence_retained\nnew_canonical_path: docs/evidence/implementation/o1f_completion_report.md\nexact_source_snapshot: docs/evidence/implementation/o1f_completion_report-source.txt\nexact_source_blob_sha: cae70dbe1648ed6757af928eeae0becd7fd313dd\nverification:\n  old_path_removed_in_pr_tree: true\n  exact_source_blob_reused: true\n  canonical_evidence_metadata_added: true\n  repository_root_literal_reference_files_updated_in_pr_tree: 3\n  repository_root_literal_reference_occurrences_updated_in_pr_tree: 5\n  relative_markdown_link_referrer_files_at_frozen_baseline: 6\n  relative_markdown_link_dependencies_at_frozen_baseline: 6\n  o1f_architecture_handoff_updated: true\n  wave6_convergence_evidence_link_updated: true\n  implementation_evidence_index_updated: true\n  documentation_current_boundary_smoke_updated: true\n  dedicated_o1f_workflow_absent_in_current_tree: true\n  cutover_preparation_self_test_reused_without_path_change: true\n  migration_aware_completion_report_model_reused: true\n  migration_aware_pr_link_smoke_reused: true\n  focused_o1f_smokes: passed\n  o1_scheduler_and_operational_regressions: passed\n  documentation_link_check: passed\n  documentation_semantic_audit: passed\n  completion_report_model_and_file_checks: passed\n  completion_report_pr_link_check: passed\n  all_github_actions: pending\n  unresolved_review_threads: 0\n```\n\nThe canonical record preserves the complete O1F validation-only scheduler operational-hardening boundary from PR #429 while separating it from current architecture-, implementation-, and focused-smoke-owned behavior. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified five repository-root literals across three files and six Markdown-link dependencies across six router, handoff, convergence, and source-report files. The dedicated O1F workflow named by the historical source report is no longer present in the current tree and is not recreated. The migration-aware completion-report model and PR-link checks apply without validator changes. The old path above is only the historical migration identifier for this receipt.\n\n'''
    text = text.replace(pending_anchor, c1c19 + pending_anchor, 1)
write(path, text)

forbidden = []
for candidate in Path(".").rglob("*"):
    if not candidate.is_file() or ".git" in candidate.parts:
        continue
    rel = candidate.as_posix().removeprefix("./")
    if rel in {
        "docs/evidence/migrations/documentation-hard-cutover-receipt.md",
        "docs/evidence/implementation/o1f_completion_report-source.txt",
        ".github/workflows/tmp-c1c19-o1f-applicator.yml",
        "scripts/tmp_c1c19_o1f_applicator.py",
    }:
        continue
    try:
        body = candidate.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    if OLD in body:
        forbidden.append(rel)
if forbidden:
    raise SystemExit(f"old live path remains: {forbidden}")

print("Cutover 1C-19 O1F applicator completed")
