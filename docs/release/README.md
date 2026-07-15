---
relaylm_doc_type: documentation_index
relaylm_authority: release_criteria_and_readiness_collection_router
relaylm_status: current
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - a release-readiness document is added, moved, or retired
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact contracts
  - frozen validation or tag evidence
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# Release

This collection holds the current release criteria and readiness interpretation for each RelayLM release boundary. It is navigation only; it does not restate runtime contracts, current implementation status, or frozen validation/tag evidence.

## Documents

- [v0.1 Release Readiness Assessment](v0.1-release-readiness.md) — current interpretation of the validated and tagged v0.1 boundary, including a content-free summary of the local human-reviewed durable-memory E2 evidence and remaining post-v0.1 decision debt.

## Reading rule

Use this collection for the current release-gate interpretation. Use [Evidence / Releases](../evidence/releases/README.md) for the frozen validation and tag-binding receipt for a completed release boundary.
