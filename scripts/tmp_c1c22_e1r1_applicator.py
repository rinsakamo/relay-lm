#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = Path("docs/mvp/wave6/e1r1_completion_report.md")
CANONICAL = Path("docs/evidence/implementation/e1r1_completion_report.md")
SNAPSHOT = Path("docs/evidence/implementation/e1r1_completion_report-source.txt")
RECEIPT = Path("docs/evidence/migrations/documentation-hard-cutover-receipt.md")
TEMP_SCRIPT = Path("scripts/tmp_c1c22_e1r1_applicator.py")
TEMP_WORKFLOW = Path(".github/workflows/tmp-c1c22-e1r1-applicator.yml")

EXPECTED_BLOB = "3d4e78d63e4be836e1de8b0ad1781a513e5349bc"
EXPECTED_SHA256 = "35c8d68527fea415465119f28ca366897ab7d320f6828fa92489dff4af58c6d7"
SOURCE_COMMIT = "39c5b982c9883ee39792450d40e4528c8a8db84b"
SOURCE_ORIGIN_COMMIT = "52768cbdac3c9630373a2c369574002ac196e72b"
SOURCE_PR = 433
RECORDED_ON = "2026-06-27"
PREVIOUS_CUTOVER_PR = 583
PREVIOUS_MERGE = "ff7f5ba3fab8dd9224ff8d77aa87e47ac221726e"


def path(value: Path | str) -> Path:
    return ROOT / value


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def read_text(value: Path | str) -> str:
    return path(value).read_text(encoding="utf-8")


def write_text(value: Path | str, body: str) -> None:
    path(value).write_text(body, encoding="utf-8")


def source_and_inventory() -> tuple[bytes, str, int, int, int, int]:
    old = path(OLD)
    raw = old.read_bytes()
    if git_blob_sha(raw) != EXPECTED_BLOB:
        raise AssertionError((git_blob_sha(raw), EXPECTED_BLOB))
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise AssertionError((hashlib.sha256(raw).hexdigest(), EXPECTED_SHA256))
    source = raw.decode("utf-8")

    root_files: list[Path] = []
    root_occurrences = 0
    markdown_files: list[Path] = []
    markdown_dependencies = 0
    link_pattern = re.compile(r"\]\(([^)\n]*e1r1_completion_report\.md)\)")
    excluded = {path(OLD), path(RECEIPT), path(TEMP_SCRIPT), path(TEMP_WORKFLOW)}
    for candidate in ROOT.rglob("*"):
        if not candidate.is_file() or ".git" in candidate.parts:
            continue
        if candidate in excluded or candidate.name.endswith("-source.txt"):
            continue
        try:
            body = candidate.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        count = body.count(str(OLD))
        if count:
            root_files.append(candidate)
            root_occurrences += count
        links = link_pattern.findall(body)
        if links:
            markdown_files.append(candidate)
            markdown_dependencies += len(links)
    return raw, source, len(root_files), root_occurrences, len(markdown_files), markdown_dependencies


def create_evidence(raw: bytes, source: str) -> None:
    snapshot = path(SNAPSHOT)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(raw)

    parts = source.split("---\n", 2)
    if len(parts) != 3:
        raise AssertionError("unexpected source frontmatter")
    body = parts[2]
    body = body.replace(str(OLD), str(CANONICAL))
    body = body.replace(
        "Expected validation:",
        "Expected validation at source PR #433:",
        1,
    )
    body = body.replace(
        "The full repository checkout was unavailable in this connector environment, so the branch relies on the added GitHub Actions workflow for full in-repo smoke execution.",
        "At source PR #433, the full repository checkout was unavailable in the connector environment, so GitHub Actions was the execution source of truth for full in-repo smoke validation. The dedicated E1-R1 workflow present at that source boundary is absent from the current tree and is not recreated during this cutover; current validation belongs to the consolidated runtime smoke inventory.",
        1,
    )
    title, rest = body.split("\n", 1)
    status = f"""

## Status and authority

This document is frozen implementation evidence for the E1-R1 trusted Home scene-admission slice introduced by PR #{SOURCE_PR}, whose final source head is `{SOURCE_COMMIT}` and merge commit is `{SOURCE_ORIGIN_COMMIT}`. Current repository-wide status belongs to [Project Status](../../PROJECT_STATUS.md). Current trusted Home scene-admission behavior belongs to [E1-R1 Trusted Home Scene Admission](../../architecture/e1r1_trusted_home_scene_admission.md), the production implementation, and the focused E1-R1 smoke suite.

The exact pre-cutover report is retained byte-for-byte as [e1r1_completion_report-source.txt](e1r1_completion_report-source.txt). Statements below describe the source PR boundary unless explicitly qualified. Legacy-path strings inside the exact snapshot are historical source text, not live repository references.

Last reviewed: {RECORDED_ON} JST

This report is evidence for one implementation pull request. It is not current runtime, repository-wide status, trust-policy, source/queue/worker behavior, sequencing, release-readiness, or operator-procedure authority.
"""
    metadata = f"""---
relaylm_doc_type: implementation_completion_report
relaylm_authority: e1r1_trusted_home_scene_admission_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: evaluation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/e1r1_trusted_home_scene_admission.md
  - ../../architecture/e1_evaluation_consolidation.md
  - ../../architecture/soul_lab_ui_b0_real_home_conversation.md
  - ../../architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current trusted Home scene-admission runtime or trust policy
  - current source, queue, worker, or scheduler behavior
  - current implementation sequencing or release readiness
  - current operator procedure
relaylm_source_commit: {SOURCE_COMMIT}
relaylm_source_origin_commit: {SOURCE_ORIGIN_COMMIT}
relaylm_source_pr: {SOURCE_PR}
relaylm_recorded_on: {RECORDED_ON}
relaylm_source_blob: {EXPECTED_BLOB}
relaylm_source_content_sha256: {EXPECTED_SHA256}
relaylm_exact_source_snapshot: e1r1_completion_report-source.txt
---
"""
    write_text(CANONICAL, metadata + title + status + rest)
    path(OLD).unlink()


def relative_target(from_file: Path) -> str:
    return os.path.relpath(path(CANONICAL), start=path(from_file).parent).replace(os.sep, "/")


def update_reference_file(file_name: str) -> None:
    file_path = Path(file_name)
    body = read_text(file_path)
    body = body.replace(str(OLD), str(CANONICAL))
    link_pattern = re.compile(r"(\]\()([^)\n]*e1r1_completion_report\.md)(\))")
    body = link_pattern.sub(lambda match: match.group(1) + relative_target(file_path) + match.group(3), body)
    write_text(file_path, body)


def update_references() -> None:
    for file_name in (
        "docs/README.md",
        "docs/architecture/README.md",
        "docs/mvp/README.md",
        "docs/architecture/e1_evaluation_consolidation.md",
        "docs/evidence/waves/wave6_cross_slice_convergence_audit.md",
        "scripts/relaylm_ci_consolidated_smoke.py",
        "scripts/relaylm_e1_evaluation_consolidation_smoke.py",
    ):
        update_reference_file(file_name)

    consolidated = read_text("scripts/relaylm_ci_consolidated_smoke.py")
    old_pattern = '"docs/mvp/wave6/e1r1_*"'
    new_pattern = '"docs/evidence/implementation/e1r1_*"'
    if consolidated.count(old_pattern) != 1:
        raise AssertionError((old_pattern, consolidated.count(old_pattern)))
    consolidated = consolidated.replace(old_pattern, new_pattern, 1)
    write_text("scripts/relaylm_ci_consolidated_smoke.py", consolidated)

    handoff_path = Path("docs/architecture/e1r1_trusted_home_scene_admission.md")
    handoff = read_text(handoff_path).rstrip()
    if "## Completion report" not in handoff:
        handoff += """

## Validation

E1-R1 has focused trusted Home admission smoke coverage. Current validation is routed through the consolidated runtime smoke inventory rather than the removed source-PR-specific workflow.

## Completion report

The frozen implementation evidence for this slice is recorded in [E1-R1 completion report](../evidence/implementation/e1r1_completion_report.md). Current behavior remains owned by this handoff, the production implementation, and the focused E1-R1 smoke suite.
"""
    write_text(handoff_path, handoff + "\n")

    index_path = Path("docs/evidence/implementation/README.md")
    index = read_text(index_path)
    anchor = "- [I-7C completion report](i7c_completion_report.md) — frozen Held Apply / Discard runtime-governance, API/UI, durable-evidence, and leakage-boundary evidence from PR #431; current behavior remains handoff-, implementation-, and focused-smoke-owned.\n"
    addition = "- [E1-R1 completion report](e1r1_completion_report.md) — frozen route-owned trusted Home scene-admission evidence from PR #433; current behavior and trust policy remain handoff-, implementation-, and focused-smoke-owned.\n"
    if addition not in index:
        if index.count(anchor) != 1:
            raise AssertionError((anchor, index.count(anchor)))
        index = index.replace(anchor, anchor + addition, 1)
    write_text(index_path, index)


def update_current_boundary_smoke() -> None:
    smoke_path = Path("scripts/relaylm_documentation_current_boundary_smoke.py")
    body = read_text(smoke_path)
    current_anchor = '    "docs/architecture/e1r1_trusted_home_scene_admission.md",\n'
    current_addition = '    "docs/evidence/implementation/e1r1_completion_report.md",\n'
    if current_addition not in body:
        if body.count(current_anchor) != 1:
            raise AssertionError((current_anchor, body.count(current_anchor)))
        body = body.replace(current_anchor, current_anchor + current_addition, 1)

    required_anchor = '    "docs/architecture/e1r4_retrieval_response_grounding.md": (\n'
    required_addition = '''    "docs/architecture/e1r1_trusted_home_scene_admission.md": (
        "relaylm_doc_type: architecture_handoff",
        "# E1-R1 Trusted Home Scene Admission",
        "trusted_home_scene_admission_mode",
        "../evidence/implementation/e1r1_completion_report.md",
    ),
    "docs/evidence/implementation/e1r1_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "relaylm_source_pr: 433",
        "E1-R1 Trusted Home Scene Admission Completion Report",
        "Current trusted Home scene-admission behavior belongs to",
        "e1r1_completion_report-source.txt",
        "At source PR #433",
    ),
'''
    if '    "docs/evidence/implementation/e1r1_completion_report.md": (' not in body:
        if body.count(required_anchor) != 1:
            raise AssertionError((required_anchor, body.count(required_anchor)))
        body = body.replace(required_anchor, required_addition + required_anchor, 1)
    write_text(smoke_path, body)


def update_receipt(
    root_files: int,
    root_occurrences: int,
    markdown_files: int,
    markdown_dependencies: int,
    source_internal_occurrences: int,
) -> None:
    pr_number = os.environ.get("PR_NUMBER")
    if not pr_number or not pr_number.isdigit():
        raise AssertionError("PR_NUMBER is required")
    body = read_text(RECEIPT)
    previous = f"cutover_pr: {PREVIOUS_CUTOVER_PR}\nmerged_commit: pending"
    finalized = f"cutover_pr: {PREVIOUS_CUTOVER_PR}\nmerged_commit: {PREVIOUS_MERGE}"
    if previous in body:
        body = body.replace(previous, finalized, 1)
    elif finalized not in body:
        raise AssertionError("C1C21 receipt anchor not found")

    heading = "### C1C22-001 — E1-R1 completion report"
    if heading not in body:
        entry = f"""### C1C22-001 — E1-R1 completion report

```yaml
cutover_pr: {pr_number}
merged_commit: pending
old_path: {OLD}
old_blob_sha: {EXPECTED_BLOB}
old_content_sha256: {EXPECTED_SHA256}
source_commit: {SOURCE_COMMIT}
source_origin_commit: {SOURCE_ORIGIN_COMMIT}
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
  repository_root_literal_reference_files_updated_in_pr_tree: {root_files}
  repository_root_literal_reference_occurrences_updated_in_pr_tree: {root_occurrences}
  relative_markdown_link_referrer_files_at_frozen_baseline: {markdown_files}
  relative_markdown_link_dependencies_at_frozen_baseline: {markdown_dependencies}
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: {source_internal_occurrences}
  e1r1_architecture_handoff_updated: true
  e1_evaluation_consolidation_updated: true
  wave6_convergence_evidence_link_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  consolidated_e1r1_smoke_updated: true
  e1_evaluation_smoke_updated: true
  dedicated_e1r1_workflow_absent_in_current_tree: true
  cutover_preparation_self_test_reused_without_path_change: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1r1_smoke: pending
  e1_evaluation_consolidation_smoke: pending
  consolidated_runtime_e1r1_group: pending
  documentation_link_check: pending
  documentation_semantic_audit: pending
  completion_report_model_and_file_checks: pending
  completion_report_pr_link_check: pending
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the complete E1-R1 route-owned trusted Home scene-admission implementation boundary from PR #433 while separating it from current handoff-, trust-policy-, implementation-, source/queue-, worker-, and focused-smoke-owned behavior. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. Live Markdown-link and repository-root validation dependencies are moved to the canonical path; legacy references remain only in this migration receipt and frozen exact source snapshots. The dedicated E1-R1 workflow named by the historical source report is no longer present in the current tree and is not recreated. The migration-aware completion-report model and PR-link checks apply without validator changes.

"""
        marker = "## Pending batches\n"
        if body.count(marker) != 1:
            raise AssertionError((marker, body.count(marker)))
        body = body.replace(marker, entry + marker, 1)
    write_text(RECEIPT, body)


def assert_boundaries() -> None:
    if path(OLD).exists():
        raise AssertionError("old path still exists")
    raw = path(SNAPSHOT).read_bytes()
    if git_blob_sha(raw) != EXPECTED_BLOB or hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise AssertionError("exact snapshot mismatch")
    canonical = read_text(CANONICAL)
    for value in (
        "relaylm_source_pr: 433",
        "Current trusted Home scene-admission behavior belongs to",
        "e1r1_completion_report-source.txt",
        "At source PR #433",
    ):
        if value not in canonical:
            raise AssertionError(value)
    if path(".github/workflows/e1r1-trusted-home-scene-admission.yml").exists():
        raise AssertionError("dedicated E1-R1 workflow unexpectedly exists")

    excluded = {path(SNAPSHOT), path(RECEIPT), path(TEMP_SCRIPT), path(TEMP_WORKFLOW)}
    variants = (
        "docs/mvp/wave6/e1r1_completion_report.md",
        "mvp/wave6/e1r1_completion_report.md",
        "../mvp/wave6/e1r1_completion_report.md",
        "../../mvp/wave6/e1r1_completion_report.md",
        "wave6/e1r1_completion_report.md",
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
        raise AssertionError(f"live legacy E1-R1 references remain: {offenders}")


def main() -> None:
    raw, source, root_files, root_occurrences, markdown_files, markdown_dependencies = source_and_inventory()
    create_evidence(raw, source)
    update_references()
    update_current_boundary_smoke()
    update_receipt(
        root_files,
        root_occurrences,
        markdown_files,
        markdown_dependencies,
        source.count(str(OLD)),
    )
    assert_boundaries()


if __name__ == "__main__":
    main()
