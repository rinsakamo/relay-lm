---
relaylm_doc_type: documentation_index
relaylm_authority: release_evidence_collection_router
relaylm_status: current
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - a release or validation receipt is added, moved, or retired
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact contracts
  - current release readiness
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source: ../../adr/0002-documentation-information-architecture.md
---
# Release Evidence

This collection preserves frozen validation and tag-binding receipts for completed RelayLM release boundaries. A receipt identifies the exact validated commit, date, checks, results, and tag binding; it does not override current release readiness, and it does not claim a GitHub Release object, packaged asset, or documentation-cutover completion.

## Records

- [v0.1 Final Main-HEAD Validation and Tag Receipt](v0.1-final-main-validation-tag-receipt.md) — frozen exact-commit validation and `v0.1` tag-binding evidence.

## Reading rule

Use this collection for frozen, completed validation and tag evidence. Use [Release](../../release/README.md) for the current release-gate interpretation.
