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
---
# Migration Evidence

This collection records path maps, source provenance, exact-copy verification, deletion classifications, and final cutover receipts. Migration evidence may contain old paths as historical identifiers; those literals do not create live compatibility paths.

## Active records

- [Documentation Hard-Cutover Migration Receipt](documentation-hard-cutover-receipt.md) — append-only ledger for the authority-first documentation cutover.
- [`cutover-1b-mvp-snapshot-deletions.tsv`](cutover-1b-mvp-snapshot-deletions.tsv) — file-level provenance for 34 low-value MVP milestone snapshots classified as Git-history-only.
