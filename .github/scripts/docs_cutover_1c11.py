#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "docs/mvp/wave8/mvp_eval_runner_completion_report.md"
NEW = "docs/evidence/implementation/mvp_eval_runner_completion_report.md"
SNAP = "docs/evidence/implementation/mvp_eval_runner_completion_report-source.txt"
RECEIPT = "docs/evidence/migrations/documentation-hard-cutover-receipt.md"
SOURCE_BLOB = "3ba3a2f5e402240b8d322b0ac55d9c77dfaed237"
SOURCE_SHA256 = "3565af79a521f80bef021a7a9a9cd31c525192b95f9dcb561a0e027c2f790635"
SOURCE_COMMIT = "89404bf0f8f4855be673af34c1450f063a22151c"
SOURCE_PR = 451
CUTOVER_PR = 569
PREVIOUS_MERGE = "1950b4dd95882649dfdfaea89c9701dd7c51e354"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, body: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def replace(path: str, old: str, new: str, expected: int | None = None) -> None:
    body = read(path)
    count = body.count(old)
    if expected is not None and count != expected:
        raise AssertionError(f"{path}: expected {expected} occurrences, found {count}: {old!r}")
    if count == 0:
        raise AssertionError(f"{path}: missing replacement anchor: {old!r}")
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

source_body = source.split("# MVP Eval Runner Completion Report\n", 1)[1]
source_body = source_body.replace(OLD, NEW)
source_body = source_body.replace(
    "- O2/O3 remain planned/unimplemented. No shared status or roadmap document should be updated to mark O2/O3 complete from this PR.",
    "- At source PR #451, O2/O3 remained planned/unimplemented. Current O2/O3 status belongs to Project Status and is not restated by this frozen record.",
)
canonical = f'''---
relaylm_doc_type: implementation_completion_report
relaylm_authority: mvp_eval_runner_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: evaluation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current MVP eval runner behavior or command registry
  - current O2/O3 scheduler status
  - repeatable evaluation method authority
relaylm_source_commit: {SOURCE_COMMIT}
relaylm_source_pr: {SOURCE_PR}
relaylm_recorded_on: 2026-06-30
relaylm_source_blob: {SOURCE_BLOB}
relaylm_source_content_sha256: {SOURCE_SHA256}
relaylm_exact_source_snapshot: mvp_eval_runner_completion_report-source.txt
---
# MVP Eval Runner Completion Report

## Status and authority

This document is frozen implementation evidence for the operator-invoked MVP eval runner introduced by PR #451 and merged as `{SOURCE_COMMIT}`. Current repository status belongs to [Project Status](../../PROJECT_STATUS.md); current runner behavior belongs to the implementation and its focused smokes.

The exact pre-cutover report is retained byte-for-byte as [mvp_eval_runner_completion_report-source.txt](mvp_eval_runner_completion_report-source.txt). Statements below describe the source PR boundary unless explicitly qualified.

{source_body}'''
write(NEW, canonical)

replace(
    "docs/README.md",
    "(mvp/wave8/mvp_eval_runner_completion_report.md)",
    "(evidence/implementation/mvp_eval_runner_completion_report.md)",
    1,
)

mvp_readme = read("docs/mvp/README.md")
old_convention = '''Path convention:

```text
docs/mvp/wave<N>/<slice>_completion_report.md
```'''
new_convention = '''Path conventions during the documentation hard cutover:

```text
legacy/unmigrated: docs/mvp/wave<N>/<slice>_completion_report.md
canonical/migrated: docs/evidence/implementation/<slice>_completion_report.md
```'''
if old_convention not in mvp_readme:
    raise AssertionError("docs/mvp/README.md: path convention anchor missing")
mvp_readme = mvp_readme.replace(old_convention, new_convention, 1)
mvp_readme = mvp_readme.replace(
    "(wave8/mvp_eval_runner_completion_report.md)",
    "(../evidence/implementation/mvp_eval_runner_completion_report.md)",
    1,
)
mvp_readme = mvp_readme.replace(OLD, NEW, 1)
write("docs/mvp/README.md", mvp_readme)

replace("scripts/relaylm_mvp_eval_runner_registry.py", OLD, NEW, 1)
replace("scripts/relaylm_documentation_current_boundary_smoke.py", OLD, NEW, 1)
replace(".github/workflows/mvp-eval-runner.yml", OLD, NEW, 3)

completion_smoke = read("scripts/relaylm_mvp_completion_report_smoke.py")
old_validate = '''def validate_report(relative_path: str) -> None:
    parts = Path(relative_path).parts
    if len(parts) != 4 or parts[0:2] != ("docs", "mvp"):
        raise AssertionError(f"{relative_path}: report must be under docs/mvp/wave<N>/")
    wave = parts[2]
    filename = parts[3]
    if not wave.startswith("wave") or not wave[4:].isdigit():
        raise AssertionError(f"{relative_path}: wave directory must end in digits")
    if not filename.endswith("_completion_report.md"):
        raise AssertionError(f"{relative_path}: invalid completion report filename")
    if ".." in parts:
        raise AssertionError(f"{relative_path}: parent traversal is not allowed")

    require_anchors(relative_path, REPORT_ANCHORS)
'''
new_validate = '''def validate_report(relative_path: str) -> None:
    parts = Path(relative_path).parts
    filename = parts[-1] if parts else ""
    legacy_wave_report = (
        len(parts) == 4
        and parts[0:2] == ("docs", "mvp")
        and parts[2].startswith("wave")
        and parts[2][4:].isdigit()
    )
    canonical_implementation_evidence = (
        len(parts) == 4
        and parts[0:3] == ("docs", "evidence", "implementation")
    )
    if not (legacy_wave_report or canonical_implementation_evidence):
        raise AssertionError(
            f"{relative_path}: report must be under legacy docs/mvp/wave<N>/ "
            "or canonical docs/evidence/implementation/"
        )
    if not filename.endswith("_completion_report.md"):
        raise AssertionError(f"{relative_path}: invalid completion report filename")
    if ".." in parts:
        raise AssertionError(f"{relative_path}: parent traversal is not allowed")

    require_anchors(relative_path, REPORT_ANCHORS)
    if canonical_implementation_evidence:
        require_anchors(
            relative_path,
            (
                "relaylm_source_commit:",
                "relaylm_source_pr:",
                "relaylm_source_blob:",
                "relaylm_source_content_sha256:",
                "relaylm_exact_source_snapshot:",
                "## Status and authority",
            ),
        )
'''
if completion_smoke.count(old_validate) != 1:
    raise AssertionError("completion report validator block changed unexpectedly")
completion_smoke = completion_smoke.replace(old_validate, new_validate, 1)
old_all_paths = '''def all_report_paths() -> tuple[str, ...]:
    reports = sorted((ROOT / "docs" / "mvp").glob("wave*/*_completion_report.md"))
    return tuple(path.relative_to(ROOT).as_posix() for path in reports)
'''
new_all_paths = '''def all_report_paths() -> tuple[str, ...]:
    reports = list((ROOT / "docs" / "mvp").glob("wave*/*_completion_report.md"))
    reports.extend(
        (ROOT / "docs" / "evidence" / "implementation").glob("*_completion_report.md")
    )
    return tuple(path.relative_to(ROOT).as_posix() for path in sorted(reports))
'''
if completion_smoke.count(old_all_paths) != 1:
    raise AssertionError("completion report discovery block changed unexpectedly")
completion_smoke = completion_smoke.replace(old_all_paths, new_all_paths, 1)
write("scripts/relaylm_mvp_completion_report_smoke.py", completion_smoke)

implementation_index = read("docs/evidence/implementation/README.md")
entry = (
    "- [MVP eval runner completion report](mvp_eval_runner_completion_report.md) — "
    "frozen implementation evidence from PR #451; current runner behavior remains code-owned.\n"
)
if entry not in implementation_index:
    implementation_index = implementation_index.rstrip() + "\n" + entry
write("docs/evidence/implementation/README.md", implementation_index)

receipt = read(RECEIPT)
c1c10_marker = "### C1C10-001 — E1-R5 post-Wave-7 correction convergence audit"
start = receipt.index(c1c10_marker)
pending = receipt.index("merged_commit: pending", start)
receipt = receipt[:pending] + f"merged_commit: {PREVIOUS_MERGE}" + receipt[pending + len("merged_commit: pending"):]
old_c1c10_tail = "The old path above is only the historical migration identifier for this receipt."
new_c1c10_tail = f"PR #568 merged as `{PREVIOUS_MERGE}`; C1C10 is finalized by Cutover 1C-11."
tail_pos = receipt.index(old_c1c10_tail, start)
receipt = receipt[:tail_pos] + new_c1c10_tail + receipt[tail_pos + len(old_c1c10_tail):]
entry = f'''### C1C11-001 — MVP eval runner completion report

```yaml
cutover_pr: {CUTOVER_PR}
merged_commit: pending
old_path: {OLD}
old_blob_sha: {SOURCE_BLOB}
old_content_sha256: {SOURCE_SHA256}
source_commit: {SOURCE_COMMIT}
source_pr: {SOURCE_PR}
recorded_on: 2026-06-30
disposition: evidence_retained
new_canonical_path: {NEW}
exact_source_snapshot: {SNAP}
exact_source_blob_sha: {SOURCE_BLOB}
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 4
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 6
  relative_markdown_link_referrer_files_at_frozen_baseline: 2
  relative_markdown_link_dependencies_at_frozen_baseline: 2
  completion_report_validator_updated: true
  implementation_evidence_index_updated: true
  mvp_eval_runner_registry_updated: true
  mvp_eval_runner_workflow_updated: true
  documentation_current_boundary_smoke_updated: true
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  focused_mvp_eval_runner_checks: passed
  all_github_actions: pending
  unresolved_review_threads: 0
```

The canonical record preserves the complete MVP eval runner implementation boundary while clarifying that current runner and O2/O3 status remain owned elsewhere. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified six repository-root path occurrences across four files, two Markdown links across two router files, and one generic completion-report validator whose legacy-only placement rule required migration-aware canonical evidence support. The old path above is only the historical migration identifier for this receipt.

'''
anchor = "## Pending batches"
if "### C1C11-001" in receipt:
    raise AssertionError("C1C11 receipt already exists")
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
    if path not in {SNAP, RECEIPT}:
        raise AssertionError(f"unexpected old-path occurrence after cutover: {hit}")

if git("hash-object", SNAP) != SOURCE_BLOB:
    raise AssertionError("snapshot blob changed during cutover")

for temporary in (
    ".github/scripts/docs_cutover_1c11.py",
    ".github/workflows/docs-cutover-1c11-applicator.yml",
):
    target = ROOT / temporary
    if target.exists():
        target.unlink()

print("Cutover 1C-11 applicator completed")
