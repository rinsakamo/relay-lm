from __future__ import annotations

from pathlib import Path

LOCAL_RECEIPT = Path("docs/evidence/migrations/cutover-1c55-phase-i2.md")
CENTRAL_LEDGER = Path("docs/evidence/migrations/documentation-hard-cutover-receipt.md")


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label} anchor count for {old!r}: {count}")
    return text.replace(old, new, 1)


def update_local_receipt() -> None:
    text = LOCAL_RECEIPT.read_text(encoding="utf-8")
    replacements = {
        "- Bookkeeping consolidation PR: pending after merge": "- Bookkeeping consolidation PR: #649",
        "- Base main: `f775581b8393522635b88f2d3178ef355330bc62`": "- Base main: `80906b60aca640d9618d550d9decb12872d67a0d`",
        "- Validated content head: pending exact-head validation": "- Validated content head: `7acdd2f8d567e4b06a229105ade6c56969438243`",
        "- Merged commit: pending": "- Merged commit: `954eee9d26bd14d27da3d9a37e3caff9e6b760a3`",
        "- Merged at: pending": "- Merged at: `2026-07-23T01:09:50Z`",
        "- Parallel implementation: PR #646 overlaps only `docs/architecture/README.md`; no SM-1 content is imported.": "- Parallel implementation: PR #646 merged first as `80906b60aca640d9618d550d9decb12872d67a0d`; the cutover was synchronized afterward, preserved its SM-1 architecture-index entry, and removed only the two retired Phase I-2 entries.",
        "- Exact-head GitHub Actions: pending": "- Exact-head GitHub Actions: 16 workflow runs; 16 success; 0 failure; 0 pending; 0 skipped",
        "- Unresolved review threads: pending final review": "- Unresolved review threads: 0",
    }
    for old, new in replacements.items():
        text = replace_once(text, old, new, label="local receipt")
    LOCAL_RECEIPT.write_text(text, encoding="utf-8")


def update_central_ledger() -> None:
    text = CENTRAL_LEDGER.read_text(encoding="utf-8")
    heading = "### C1C55-001 — Phase I-2 Real SOUL Lab Observation handoff (pending merge attribution)"
    if text.count(heading) != 1:
        raise SystemExit(f"pending heading count must be 1, got {text.count(heading)}")
    start = text.index(heading)
    tail = text[start:]
    for token in (
        "merged_commit: pending",
        "exact_head_actions: pending",
        "unresolved_review_threads: pending",
        "Pending merge attribution only.",
    ):
        if tail.count(token) != 1:
            raise SystemExit(f"pending token {token!r} count must be 1, got {tail.count(token)}")

    retired_path = "docs/architecture/" + "phase_i2_real_soul_lab_observation.md"
    final = f"""### C1C55-001 — Phase I-2 Real SOUL Lab Observation handoff

```yaml
cutover_pr: 647
merged_commit: 954eee9d26bd14d27da3d9a37e3caff9e6b760a3
bookkeeping_pr: 649
base_main: 80906b60aca640d9618d550d9decb12872d67a0d
validated_content_head: 7acdd2f8d567e4b06a229105ade6c56969438243
head_at_merge: 7acdd2f8d567e4b06a229105ade6c56969438243
merged_at: 2026-07-23T01:09:50Z
old_path: {retired_path}
old_blob_sha: 496c29ad94558a4bb0e12921cf20ad5358ae1120
old_content_sha256: 989747ef065b315f94d079cf635e3da79c52dde45e3066cd4a3fae5cd0ef0079
source_pr: 377
source_final_head: a891dc67a47afeaf074443c69682adb7a5aa9fbc
source_merge_commit: 4a24bdc9e6614433675eaa54f97b40647010c007
source_merged_at: 2026-06-24T12:34:06Z
recorded_on: 2026-06-24
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/phase-i2-real-soul-lab-observation-handoff.md
local_receipt: docs/evidence/migrations/cutover-1c55-phase-i2.md
verification:
  old_path_removed_in_pr_tree: true
  canonical_evidence_metadata_added: true
  historical_banner_added: true
  current_authority_independently_owned: true
  pre_cutover_referrer_files: 13
  active_path_references_repaired: true
  current_architecture_indexes_removed: true
  implementation_evidence_index_updated: true
  e1_evidence_inventory_updated: true
  phase_i2_documentation_boundary_smoke_updated: true
  fail_closed_guard: scripts/relaylm_phase_i2_handoff_cutover_guard.py
  guard_integrated_into_existing_documentation_boundary_workflow: true
  guard_self_test_assertions: 24
  sm1_index_entry_preserved_after_pr_646_sync: true
  exact_head_workflow_runs: 16
  exact_head_workflow_success: 16
  exact_head_workflow_failure: 0
  exact_head_workflow_pending: 0
  exact_head_workflow_skipped: 0
  unresolved_review_threads: 0
  runtime_files_changed: 0
  relaylm_files_changed: 0
  project_status_changed: false
  final_changed_files: 20
  final_additions: 406
  final_deletions: 50
  open_pr_content_imported: false
```

PR #647 preserves the completed Phase I-2 observe-only SOUL Lab integration as frozen implementation evidence and merged as `954eee9d26bd14d27da3d9a37e3caff9e6b760a3` from reviewed head `7acdd2f8d567e4b06a229105ade6c56969438243` on synchronized main `80906b60aca640d9618d550d9decb12872d67a0d`. The synchronization retained PR #646's SM-1 architecture-index entry and removed only the two retired Phase I-2 index entries. Current observation behavior remains architecture-, implementation-, frontend-validation-, Project-Status-, and focused-smoke-owned. PR #649 consolidates merge attribution and exact-head validation without changing accepted cutover content.
"""
    CENTRAL_LEDGER.write_text(text[:start] + final, encoding="utf-8")


def main() -> None:
    update_local_receipt()
    update_central_ledger()


if __name__ == "__main__":
    main()
