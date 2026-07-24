---
relaylm_doc_type: documentation_index
relaylm_authority: documentation_migration_evidence_collection_router
relaylm_status: current
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - a documentation migration starts, completes, or is superseded
relaylm_not_authoritative_for:
  - current documentation placement
  - current runtime behavior
  - exact contracts
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source: ../../adr/0002-documentation-information-architecture.md
relaylm_retirement_state: transitional
---
# Migration Evidence

> Transitional closed family after Documentation Hard Cutover 1C-57. Do not add another ordinary per-source receipt or treat this collection as a permanent archive. D2-D6 use the generic retirement manifest and Git recoverability contract; D6 removes redundant legacy receipts and indexes after equivalent coverage is proven.

This collection records path maps, source provenance, exact-copy verification, deletion classifications, and final cutover receipts. Migration evidence may contain old paths as historical identifiers; those literals do not create live compatibility paths.

## Active records

- [Documentation Hard-Cutover Migration Receipt](documentation-hard-cutover-receipt.md) — append-only ledger for the authority-first documentation cutover.
- [`cutover-1b-mvp-snapshot-deletions.tsv`](cutover-1b-mvp-snapshot-deletions.tsv) — file-level provenance for 34 low-value MVP milestone snapshots classified as Git-history-only.
- [`cutover-1c2-early-mvp-smokes.tsv`](cutover-1c2-early-mvp-smokes.tsv) — provenance and exact-source destinations for four early MVP smoke records.
- [`cutover-1c3-mvp2-compile-smokes.tsv`](cutover-1c3-mvp2-compile-smokes.tsv) — provenance and exact-source destinations for three early MVP-2 compile/diagnostics records.
