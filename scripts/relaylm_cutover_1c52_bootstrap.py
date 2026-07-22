#!/usr/bin/env python3
"""Temporary atomic assembler for Documentation Hard Cutover 1C-52.

The script moves the validation-only I1-GE handoff into frozen implementation
 evidence, repairs active path-bound references, records provenance and pending
cutover facts, creates a fail-closed retired-path guard, restores the canonical
documentation boundary workflow with the new guard integrated, and deletes
itself before the generated commit is created.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PR_NUMBER = os.environ["PR_NUMBER"]
BASE_MAIN = "3b518000d9e87cafe8ba23aabf0b2ef815881c16"
OLD = Path("docs/architecture/i1ge_durable_finalization_crash_validation.md")
NEW = Path("docs/evidence/implementation/i1ge-durable-finalization-crash-validation-handoff.md")
LOCAL_RECEIPT = Path("docs/evidence/migrations/cutover-1c52-i1ge.md")
CENTRAL_LEDGER = Path("docs/evidence/migrations/documentation-hard-cutover-receipt.md")
RULES = Path("docs/planning/documentation-cutover-rules.yaml")
INDEX = Path("docs/evidence/implementation/README.md")
WORKFLOW = Path(".github/workflows/documentation-current-boundary-smoke.yml")
GUARD = Path("scripts/relaylm_i1ge_handoff_cutover_guard.py")
TEMPLATE_GUARD = Path("scripts/relaylm_phase55c4_handoff_cutover_guard.py")
IMMUTABLE_SOURCE_SNAPSHOT = Path(
    "docs/evidence/waves/wave2_cross_slice_convergence_audit-source.txt"
)

VALIDATION_PR = 411
VALIDATION_HEAD = "6cb461cb614d14965f5a49c1c4b517755f44f4a6"
VALIDATION_MERGE = "e2caa1bdb53468ca282e8f374ba8ceebf839c976"
VALIDATION_MERGED_AT = "2026-06-26T22:41:44Z"
HANDOFF_PR = 415
HANDOFF_MERGE = "394ea1628f2262625c460c60d6b218ccc90429ac"
HANDOFF_MERGED_AT = "2026-06-27T04:57:02Z"
RECORDED_ON = "2026-06-27"

TEXT_SUFFIXES = {".md", ".txt", ".py", ".yml", ".yaml", ".json", ".toml"}
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one occurrence, got {count}: {old!r}")
    return text.replace(old, new, 1)


def scanned_text_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        files.append(relative)
    return files


def relative_path(target: Path, referrer: Path) -> str:
    return os.path.relpath(target, start=referrer.parent).replace(os.sep, "/")


source_bytes = OLD.read_bytes()
source_text = source_bytes.decode("utf-8")
old_blob = subprocess.check_output(
    ["git", "rev-parse", f"HEAD:{OLD.as_posix()}"], text=True
).strip()
content_sha256 = hashlib.sha256(source_bytes).hexdigest()

if not source_text.startswith("---\n"):
    raise SystemExit("I1-GE source has no front matter")
front_end = source_text.find("\n---\n", 4)
if front_end < 0:
    raise SystemExit("I1-GE source front matter is unterminated")
body = source_text[front_end + 5 :]
title = "# I1-GE Durable-finalization crash validation handoff\n\n"
banner = (
    "> **Historical validation evidence.** This frozen governance handoff was "
    "added by Wave 3 convergence PR #415 to describe the validation-only proof "
    "implemented in PR #411. Current durable-finalization production authority "
    "remains with the I1-G contract, I1-GD, implementation, and focused smokes.\n\n"
)
body = replace_once(body, title, title + banner, "I1-GE evidence banner")
metadata = f"""---
relaylm_doc_type: evidence
relaylm_authority: historical_i1ge_durable_finalization_crash_validation_handoff
relaylm_status: frozen
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_source_commit: {HANDOFF_MERGE}
relaylm_source_pr: {HANDOFF_PR}
relaylm_recorded_on: {RECORDED_ON}
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - current durable-finalization production behavior
  - new durable-finalization schema
  - replay or retention algorithm changes
  - scheduler, queue, or worker execution
  - Primary MEM formation
  - repository-wide current status
relaylm_related_authority:
  - ../../architecture/i1g_pre_enqueue_durable_finalization_contract.md
  - ../../architecture/i1gd_durable_finalization_retention_cleanup.md
  - ../../architecture/o1b_sealed_i1g_replay_lane.md
  - i1ge_completion_report.md
  - ../waves/wave3_cross_slice_convergence_audit.md
---
"""
NEW.parent.mkdir(parents=True, exist_ok=True)
NEW.write_text(metadata + body, encoding="utf-8")
OLD.unlink()

# Repair every active exact path-bound reference. Preserve the byte-exact Wave 2
# source snapshot and let the new guard allowlist only that immutable carrier.
repaired_referrers: list[str] = []
for relative in scanned_text_files():
    if relative in {IMMUTABLE_SOURCE_SNAPSHOT, NEW}:
        continue
    path = ROOT / relative
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    if OLD.name not in text:
        continue
    old_relative = relative_path(OLD, relative)
    new_relative = relative_path(NEW, relative)
    updated = text.replace(OLD.as_posix(), NEW.as_posix())
    updated = updated.replace(old_relative, new_relative)
    if OLD.name in updated:
        raise SystemExit(
            f"unrepaired I1-GE path reference in {relative.as_posix()}: "
            f"old_relative={old_relative!r}"
        )
    path.write_text(updated, encoding="utf-8")
    repaired_referrers.append(relative.as_posix())

expected_referrers = {
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md",
    "docs/architecture/i1gd_durable_finalization_retention_cleanup.md",
    "docs/architecture/soul_lab_ui_b1a_lifecycle_visibility.md",
}
missing_referrers = expected_referrers.difference(repaired_referrers)
if missing_referrers:
    raise SystemExit(f"expected I1-GE referrers were not repaired: {sorted(missing_referrers)}")

# Index the frozen handoff next to the already-cut-over completion report.
index_text = INDEX.read_text(encoding="utf-8")
if NEW.name in index_text:
    raise SystemExit("I1-GE frozen handoff is already indexed")
index_lines = index_text.splitlines()
anchor_index = next(
    (i for i, line in enumerate(index_lines) if line.startswith("- [I1-GE completion report]")),
    None,
)
if anchor_index is None:
    raise SystemExit("I1-GE completion report index anchor is missing")
index_lines.insert(
    anchor_index + 1,
    "- [I1-GE crash-validation governance handoff]"
    "(i1ge-durable-finalization-crash-validation-handoff.md) — frozen "
    "validation-only governance evidence added by PR #415 for the PR #411 "
    "process-exit/fresh-restart proof; current production authority remains "
    "I1-G-contract-, I1-GD-, implementation-, and focused-smoke-owned.",
)
INDEX.write_text("\n".join(index_lines) + "\n", encoding="utf-8")

# Record the explicit cutover disposition.
rules_text = RULES.read_text(encoding="utf-8")
rules_key = f"  {OLD.as_posix()}:\n"
if rules_key in rules_text:
    raise SystemExit("I1-GE cutover rule already exists")
rules_entry = f"""
  {OLD.as_posix()}:
    disposition: evidence_retained
    target_doc_type: evidence
    target_paths:
      - {NEW.as_posix()}
    deletion_reason: >-
      Cutover 1C-52: this validation-only I1-GE governance handoff was a frozen
      historical record mislocated in the live architecture collection. The
      cutover preserves PR #411 validation provenance and PR #415 handoff
      provenance, repairs every active path-bound reference, keeps the byte-exact
      Wave 2 source snapshot unchanged, and leaves current durable-finalization
      production authority with the I1-G contract, I1-GD, implementation, and
      focused smokes.
"""
rules_text = replace_once(
    rules_text,
    "\nfamily_rules:\n",
    rules_entry + "\nfamily_rules:\n",
    "cutover-rules family anchor",
)
RULES.write_text(rules_text, encoding="utf-8")

referrer_summary = ", ".join(f"`{path}`" for path in repaired_referrers)
LOCAL_RECEIPT.write_text(
    f"""---
relaylm_doc_type: evidence
relaylm_authority: documentation_cutover_1c52_receipt
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - validated-head, merge attribution, or bookkeeping facts are finalized
relaylm_not_authoritative_for:
  - current runtime behavior
  - durable-finalization production authority
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# Documentation Hard Cutover 1C-52 Receipt

- Cutover PR: #{PR_NUMBER}
- Bookkeeping consolidation PR: pending
- Base main: `{BASE_MAIN}`
- Validated content head: pending exact-head validation
- Merged commit: pending
- Source: `{OLD.as_posix()}`
- Canonical target: `{NEW.as_posix()}`
- Disposition: `evidence_retained`, implemented as a move and retype from `implementation_handoff` / `historical_after_merge` to `evidence` / `frozen`
- Validation source PR: #{VALIDATION_PR}
- Validation final head: `{VALIDATION_HEAD}`
- Validation merge commit: `{VALIDATION_MERGE}`
- Validation merged at: `{VALIDATION_MERGED_AT}`
- Governance handoff source PR: #{HANDOFF_PR}
- Governance handoff merge commit: `{HANDOFF_MERGE}`
- Governance handoff merged at: `{HANDOFF_MERGED_AT}`
- Source and pre-cutover blob: `{old_blob}`
- Source content SHA-256: `{content_sha256}`
- Source recorded on: `{RECORDED_ON}`
- Current durable-finalization authority retained by: `docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md`, `docs/architecture/i1gd_durable_finalization_retention_cleanup.md`, implementation, and focused smokes
- Active referrers repaired: {referrer_summary}
- Immutable historical carrier preserved unchanged: `{IMMUTABLE_SOURCE_SNAPSHOT.as_posix()}`
- Fail-closed enforcement: `{GUARD.as_posix()}`, compiled and executed by `{WORKFLOW.as_posix()}`
- Guard self-test: 22 assertions
- Exact-head GitHub Actions: pending
- Runtime files changed: 0
- `relaylm/**` files changed: 0
- Open-PR content imported: none; PR #629 was open before branch creation, shares no planned cutover paths, and no content was imported
- Unresolved review threads: pending final review

This receipt records the in-review Cutover 1C-52 boundary. It does not make the historical I1-GE validation handoff current authority and does not change runtime, contract, schema, storage, compatibility, alias, redirect, dual-read, or dual-write behavior. Merge and exact-head observations remain pending until explicit final review and merge.
""",
    encoding="utf-8",
)

ledger_text = CENTRAL_LEDGER.read_text(encoding="utf-8")
ledger_marker = "### C1C52-001 — I1-GE crash-validation governance handoff"
if ledger_marker in ledger_text:
    raise SystemExit("C1C52 ledger entry already exists")
ledger_text += f"""

{ledger_marker}

```yaml
cutover_pr: {PR_NUMBER}
merged_commit: pending
bookkeeping_pr: pending
base_main: {BASE_MAIN}
validated_content_head: pending
head_at_merge: pending
merged_at: pending
old_path: {OLD.as_posix()}
old_blob_sha: {old_blob}
old_content_sha256: {content_sha256}
validation_source_pr: {VALIDATION_PR}
validation_final_head: {VALIDATION_HEAD}
validation_merge_commit: {VALIDATION_MERGE}
validation_merged_at: {VALIDATION_MERGED_AT}
governance_handoff_source_pr: {HANDOFF_PR}
governance_handoff_merge_commit: {HANDOFF_MERGE}
governance_handoff_merged_at: {HANDOFF_MERGED_AT}
recorded_on: {RECORDED_ON}
disposition: evidence_retained
new_canonical_path: {NEW.as_posix()}
local_receipt: {LOCAL_RECEIPT.as_posix()}
verification:
  old_path_removed: true
  canonical_evidence_metadata_added: true
  current_production_authority_retained_by: i1g_contract_i1gd_implementation_and_focused_smokes
  active_referrers_repaired: {len(repaired_referrers)}
  immutable_wave2_source_snapshot_preserved: true
  implementation_evidence_index_updated: true
  fail_closed_guard: {GUARD.as_posix()}
  guard_integrated_into_existing_documentation_boundary_workflow: true
  guard_self_test_assertions: 22
  exact_head_workflow_runs: pending
  exact_head_workflow_success: pending
  exact_head_workflow_failure: pending
  unresolved_review_threads: pending
  runtime_files_changed: 0
  relaylm_changed_files: 0
  open_pr_content_imported: false
```

PR #{PR_NUMBER} preserves the validation-only I1-GE governance handoff as frozen implementation evidence. The production proof remains attributable to PR #{VALIDATION_PR}; the handoff itself remains attributable to PR #{HANDOFF_PR}. Current durable-finalization behavior remains contract-, I1-GD-, implementation-, and focused-smoke-owned. Merge attribution and exact-head validation remain pending until explicit final review and bookkeeping consolidation.
"""
CENTRAL_LEDGER.write_text(ledger_text, encoding="utf-8")

# Derive the hardened guard from the latest accepted retired-path guard.
guard_text = TEMPLATE_GUARD.read_text(encoding="utf-8")
for old, new in [
    ("Documentation Hard Cutover 1C-50", "Documentation Hard Cutover 1C-52"),
    ("Phase 5.5-C4", "I1-GE"),
    ("phase55c4_runtime_tts_transport_envelope_wiring", "i1ge_durable_finalization_crash_validation"),
    ("phase55c4-runtime-tts-transport-envelope-wiring", "i1ge-durable-finalization-crash-validation-handoff"),
    ("relaylm_phase55c4_handoff_cutover_guard", "relaylm_i1ge_handoff_cutover_guard"),
    ("cutover-1c50-phase55c4", "cutover-1c52-i1ge"),
]:
    guard_text = guard_text.replace(old, new)
guard_text = guard_text.replace(
    "The completed I1-GE implementation handoff moved from the live\n"
    "architecture collection to frozen implementation evidence.",
    "The validation-only I1-GE governance handoff moved from the live\n"
    "architecture collection to frozen implementation evidence.",
)
allowlist_anchor = (
    '    "docs/evidence/migrations/documentation-hard-cutover-receipt.md",\n}'
)
guard_text = replace_once(
    guard_text,
    allowlist_anchor,
    '    "docs/evidence/migrations/documentation-hard-cutover-receipt.md",\n'
    f'    "{IMMUTABLE_SOURCE_SNAPSHOT.as_posix()}",\n}}',
    "I1-GE immutable-source guard allowlist",
)
GUARD.write_text(guard_text, encoding="utf-8")
subprocess.run(["python", str(GUARD), "--self-test"], check=True)

# Restore the canonical current-boundary workflow from main and integrate the
# new guard into path triggers, compile, execution, self-test, and exit status.
workflow_text = subprocess.check_output(
    ["git", "show", f"origin/main:{WORKFLOW.as_posix()}"], text=True
)
path_anchor = '      - "scripts/relaylm_phase55c4_handoff_cutover_guard.py"\n'
if workflow_text.count(path_anchor) != 2:
    raise SystemExit("unexpected current-boundary path-trigger anchor count")
workflow_text = workflow_text.replace(
    path_anchor,
    path_anchor + '      - "scripts/relaylm_i1ge_handoff_cutover_guard.py"\n',
)
compile_anchor = "            scripts/relaylm_phase55c4_handoff_cutover_guard.py \\\n"
workflow_text = replace_once(
    workflow_text,
    compile_anchor,
    compile_anchor + "            scripts/relaylm_i1ge_handoff_cutover_guard.py \\\n",
    "current-boundary compile anchor",
)
run_anchor = (
    "          python scripts/relaylm_phase55c4_handoff_cutover_guard.py --self-test 2>&1 | tee -a documentation-current-boundary.log\n"
    "          phase55c4_cutover_guard_self_test_status=${PIPESTATUS[0]}\n"
)
run_block = run_anchor + (
    "          python scripts/relaylm_i1ge_handoff_cutover_guard.py 2>&1 | tee -a documentation-current-boundary.log\n"
    "          i1ge_cutover_guard_status=${PIPESTATUS[0]}\n"
    "          python scripts/relaylm_i1ge_handoff_cutover_guard.py --self-test 2>&1 | tee -a documentation-current-boundary.log\n"
    "          i1ge_cutover_guard_self_test_status=${PIPESTATUS[0]}\n"
)
workflow_text = replace_once(
    workflow_text, run_anchor, run_block, "current-boundary I1-GE run anchor"
)
status_anchor = ' || [ "$phase55c4_cutover_guard_self_test_status" -ne 0 ] ||'
workflow_text = replace_once(
    workflow_text,
    status_anchor,
    status_anchor
    + ' [ "$i1ge_cutover_guard_status" -ne 0 ] ||'
    + ' [ "$i1ge_cutover_guard_self_test_status" -ne 0 ] ||',
    "current-boundary I1-GE status anchor",
)
WORKFLOW.write_text(workflow_text, encoding="utf-8")

# Delete this temporary assembler before repository-wide retired-path scanning.
Path(__file__).unlink()
subprocess.run(["python", str(GUARD)], check=True)

print(f"old_blob={old_blob}")
print(f"old_content_sha256={content_sha256}")
print(f"repaired_referrers={repaired_referrers!r}")
print("Cutover 1C-52 assembly complete")
