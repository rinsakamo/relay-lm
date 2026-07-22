#!/usr/bin/env python3
"""Finalize Documentation Hard Cutover 1C-52 merge bookkeeping."""
from __future__ import annotations

import os
from pathlib import Path

BOOKKEEPING_PR = os.environ["PR_NUMBER"]
BASE_MAIN = "86d3af1b3c24569f1daf01b2b52ef8c5119046d8"
VALIDATED_HEAD = "ca4a9bc98c48316dc777c9c7abf85f4d910a11ef"
MERGE_COMMIT = "8791d0495e1c4b56aa97b49acc27b745a65bdd4c"
MERGED_AT = "2026-07-22T08:16:33Z"
LOCAL = Path("docs/evidence/migrations/cutover-1c52-i1ge.md")
LEDGER = Path("docs/evidence/migrations/documentation-hard-cutover-receipt.md")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one occurrence, got {count}: {old!r}")
    return text.replace(old, new, 1)


local = LOCAL.read_text(encoding="utf-8")
if f"- Bookkeeping consolidation PR: #{BOOKKEEPING_PR}" not in local:
    local = replace_once(
        local,
        "- Bookkeeping consolidation PR: pending",
        f"- Bookkeeping consolidation PR: #{BOOKKEEPING_PR}",
        "local bookkeeping PR",
    )
    local = replace_once(
        local,
        "- Base main: `3b518000d9e87cafe8ba23aabf0b2ef815881c16`",
        f"- Base main: `{BASE_MAIN}`",
        "local base main",
    )
    local = replace_once(
        local,
        "- Validated content head: pending exact-head validation",
        f"- Validated content head: `{VALIDATED_HEAD}`",
        "local validated head",
    )
    local = replace_once(
        local,
        "- Merged commit: pending",
        f"- Merged commit: `{MERGE_COMMIT}`\n- Merged at: `{MERGED_AT}`\n- Final cutover diff: 17 changed files, +610/-28",
        "local merge facts",
    )
    local = replace_once(
        local,
        "- Exact-head GitHub Actions: pending",
        "- Exact-head GitHub Actions: 16 workflows; 16 success, 0 failure, 0 pending",
        "local actions facts",
    )
    local = replace_once(
        local,
        "- Open-PR content imported: none; PR #629 was open before branch creation, shares no planned cutover paths, and no content was imported",
        "- Implementation-base integration: PR #629 merged before the final rebase as current main; it shared 0 cutover paths and no EV-1 content was duplicated in the cutover",
        "local implementation base",
    )
    local = replace_once(
        local,
        "- Unresolved review threads: pending final review",
        "- Unresolved review threads: 0",
        "local review threads",
    )
    local = replace_once(
        local,
        "This receipt records the in-review Cutover 1C-52 boundary. It does not make the historical I1-GE validation handoff current authority and does not change runtime, contract, schema, storage, compatibility, alias, redirect, dual-read, or dual-write behavior. Merge and exact-head observations remain pending until explicit final review and merge.",
        f"This receipt records the merged Cutover 1C-52 boundary. PR #634 merged as `{MERGE_COMMIT}` from reviewed head `{VALIDATED_HEAD}` on base `{BASE_MAIN}`; PR #{BOOKKEEPING_PR} consolidates those facts without changing the accepted cutover content. The historical I1-GE validation handoff remains non-authoritative for current runtime, contract, schema, storage, compatibility, alias, redirect, dual-read, or dual-write behavior.",
        "local final paragraph",
    )
    LOCAL.write_text(local, encoding="utf-8")

ledger = LEDGER.read_text(encoding="utf-8")
marker = "### C1C52-001 — I1-GE crash-validation governance handoff"
start = ledger.find(marker)
if start < 0:
    raise SystemExit("C1C52 ledger entry missing")
next_marker = ledger.find("\n### ", start + len(marker))
end = len(ledger) if next_marker < 0 else next_marker
prefix, block, suffix = ledger[:start], ledger[start:end], ledger[end:]
if f"bookkeeping_pr: {BOOKKEEPING_PR}" not in block:
    block = replace_once(block, "merged_commit: pending", f"merged_commit: {MERGE_COMMIT}", "ledger merge commit")
    block = replace_once(block, "bookkeeping_pr: pending", f"bookkeeping_pr: {BOOKKEEPING_PR}", "ledger bookkeeping PR")
    block = replace_once(
        block,
        "base_main: 3b518000d9e87cafe8ba23aabf0b2ef815881c16",
        f"base_main: {BASE_MAIN}\nimplementation_base_pr: 629\nimplementation_base_merge: {BASE_MAIN}",
        "ledger base main",
    )
    block = replace_once(block, "validated_content_head: pending", f"validated_content_head: {VALIDATED_HEAD}", "ledger validated head")
    block = replace_once(block, "head_at_merge: pending", f"head_at_merge: {VALIDATED_HEAD}", "ledger head at merge")
    block = replace_once(block, "merged_at: pending", f"merged_at: {MERGED_AT}", "ledger merged at")
    block = replace_once(block, "  exact_head_workflow_runs: pending", "  exact_head_workflow_runs: 16", "ledger workflow runs")
    block = replace_once(block, "  exact_head_workflow_success: pending", "  exact_head_workflow_success: 16", "ledger workflow successes")
    block = replace_once(block, "  exact_head_workflow_failure: pending", "  exact_head_workflow_failure: 0", "ledger workflow failures")
    block = replace_once(block, "  unresolved_review_threads: pending", "  unresolved_review_threads: 0", "ledger review threads")
    block = replace_once(
        block,
        "  open_pr_content_imported: false",
        "  open_pr_content_imported: false\n  implementation_base_path_overlap: 0\n  final_changed_files: 17\n  final_additions: 610\n  final_deletions: 28",
        "ledger final diff facts",
    )
    block = replace_once(
        block,
        "PR #634 preserves the validation-only I1-GE governance handoff as frozen implementation evidence. The production proof remains attributable to PR #411; the handoff itself remains attributable to PR #415. Current durable-finalization behavior remains contract-, I1-GD-, implementation-, and focused-smoke-owned. Merge attribution and exact-head validation remain pending until explicit final review and bookkeeping consolidation.",
        f"PR #634 preserves the validation-only I1-GE governance handoff as frozen implementation evidence and merged as `{MERGE_COMMIT}` from reviewed head `{VALIDATED_HEAD}` on EV-1 main `{BASE_MAIN}`. The production proof remains attributable to PR #411; the handoff itself remains attributable to PR #415. Current durable-finalization behavior remains contract-, I1-GD-, implementation-, and focused-smoke-owned. PR #{BOOKKEEPING_PR} consolidates merge attribution and exact-head validation without changing accepted cutover content.",
        "ledger final paragraph",
    )
    LEDGER.write_text(prefix + block + suffix, encoding="utf-8")

print(f"Cutover 1C-52 bookkeeping prepared for PR #{BOOKKEEPING_PR}")
