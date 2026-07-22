#!/usr/bin/env python3
"""Finalize Documentation Hard Cutover 1C-53 bookkeeping after PR #637 merge."""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "docs/evidence/migrations/cutover-1c53-i4c1.md"
LEDGER = ROOT / "docs/evidence/migrations/documentation-hard-cutover-receipt.md"

BASE = "9647f35d4cb8792e9ab48795985bef96a75c5856"
HEAD = "98bfb8f03df4323d7d7de33c0e19d063271683e7"
MERGE = "28f773f04bbb8837b2a8674da93c9317eddea9d4"
MERGED_AT = "2026-07-22T09:13:02Z"
WORKFLOWS = 16
CHANGED_FILES = 15
ADDITIONS = 362
DELETIONS = 23


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new, 1)


def update_local(bookkeeping_pr: str) -> None:
    text = LOCAL.read_text(encoding="utf-8")
    text = replace_once(text, "- Bookkeeping consolidation PR: pending", f"- Bookkeeping consolidation PR: #{bookkeeping_pr}", "local bookkeeping PR")
    text = replace_once(text, f"- Base main: `{BASE}`", f"- Base main: `{BASE}`", "local base")
    text = replace_once(text, "- Validated content head: pending exact-head validation", f"- Validated content head: `{HEAD}`", "local head")
    text = replace_once(text, "- Merged commit: pending", f"- Merged commit: `{MERGE}`\n- Merged at: `{MERGED_AT}`\n- Final cutover diff: {CHANGED_FILES} changed files, +{ADDITIONS}/-{DELETIONS}", "local merge")
    text = replace_once(text, "- Exact-head GitHub Actions: pending", f"- Exact-head GitHub Actions: {WORKFLOWS} workflows; {WORKFLOWS} success, 0 failure, 0 pending", "local actions")
    text = replace_once(text, "- Unresolved review threads: pending final review", "- Unresolved review threads: 0", "local threads")
    old_tail = "This receipt records the in-review Cutover 1C-53 boundary. It does not make the historical I-4C1 handoff current authority and does not change runtime, contract, schema, storage, compatibility, alias, redirect, dual-read, or dual-write behavior. Merge and exact-head observations remain pending until explicit final review and merge."
    new_tail = f"This receipt records the merged Cutover 1C-53 boundary. PR #637 merged as `{MERGE}` from reviewed head `{HEAD}` on base `{BASE}`; PR #{bookkeeping_pr} consolidates those facts without changing the accepted cutover content. The historical I-4C1 handoff remains non-authoritative for current runtime, contract, schema, storage, compatibility, alias, redirect, dual-read, or dual-write behavior."
    text = replace_once(text, old_tail, new_tail, "local tail")
    LOCAL.write_text(text, encoding="utf-8")


def update_ledger(bookkeeping_pr: str) -> None:
    text = LEDGER.read_text(encoding="utf-8")
    marker = "cutover_pr: 637\n"
    start = text.find(marker)
    if start < 0:
        raise SystemExit("ledger: Cutover 1C-53 block not found")
    fence_end = text.find("```", start)
    if fence_end < 0:
        raise SystemExit("ledger: closing fence not found")
    block = text[start:fence_end]
    replacements = {
        "merged_commit: pending": f"merged_commit: {MERGE}",
        "bookkeeping_pr: pending": f"bookkeeping_pr: {bookkeeping_pr}",
        "validated_content_head: pending": f"validated_content_head: {HEAD}",
        "head_at_merge: pending": f"head_at_merge: {HEAD}",
        "merged_at: pending": f"merged_at: {MERGED_AT}",
        "  exact_head_workflow_runs: pending": f"  exact_head_workflow_runs: {WORKFLOWS}",
        "  exact_head_workflow_success: pending": f"  exact_head_workflow_success: {WORKFLOWS}",
        "  exact_head_workflow_failure: pending": "  exact_head_workflow_failure: 0",
        "  unresolved_review_threads: pending": "  unresolved_review_threads: 0",
    }
    for old, new in replacements.items():
        block = replace_once(block, old, new, f"ledger {old}")
    verification_anchor = "  relaylm_changed_files: 0\n"
    block = replace_once(
        block,
        verification_anchor,
        verification_anchor
        + f"  final_changed_files: {CHANGED_FILES}\n"
        + f"  final_additions: {ADDITIONS}\n"
        + f"  final_deletions: {DELETIONS}\n",
        "ledger final diff",
    )
    text = text[:start] + block + text[fence_end:]
    old_tail = "PR #637 preserves the completed I-4C1 hidden-successor commit handoff as frozen implementation evidence. Current Primary Forget behavior remains I-4-contract-, I-4C2/I-4D/I-4E/I-4F-, implementation-, and focused-smoke-owned. Merge attribution and exact-head validation remain pending until explicit final review and bookkeeping consolidation."
    new_tail = f"PR #637 preserves the completed I-4C1 hidden-successor commit handoff as frozen implementation evidence and merged as `{MERGE}` from reviewed head `{HEAD}` on base `{BASE}`. Current Primary Forget behavior remains I-4-contract-, I-4C2/I-4D/I-4E/I-4F-, implementation-, and focused-smoke-owned. PR #{bookkeeping_pr} consolidates merge attribution and exact-head validation without changing accepted cutover content."
    text = replace_once(text, old_tail, new_tail, "ledger tail")
    LEDGER.write_text(text, encoding="utf-8")


def main() -> None:
    bookkeeping_pr = os.environ.get("BOOKKEEPING_PR", "").strip()
    if not re.fullmatch(r"[0-9]+", bookkeeping_pr):
        raise SystemExit("BOOKKEEPING_PR must be a numeric pull request number")
    update_local(bookkeeping_pr)
    update_ledger(bookkeeping_pr)


if __name__ == "__main__":
    main()
