---
relaylm_doc_type: documentation_index
relaylm_authority: documentation_evidence_collection_router
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - evidence collection structure changes
  - a new evidence family becomes canonical
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact contracts
  - implementation or release status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# RelayLM Evidence

This collection contains non-normative records retained because they support durable decisions, implementation verification, evaluation, releases, or proposals. Evidence does not override current status, architecture, contracts, or accepted decisions.

## Collections

- [Implementation](implementation/README.md) — bounded implementation completion and smoke evidence.
- [Waves](waves/README.md) — frozen cross-slice convergence evidence.
- [Evaluations](evaluations/README.md) — dated evaluation and validation results.
- [Releases](releases/README.md) — release and validation receipts.
- [Proposals](proposals/README.md) — accepted, rejected, or withdrawn proposal evidence.

## Retired documentation migration provenance

Documentation migration provenance is no longer an evidence collection. Retired documentation paths and their exact recovery identity are recorded in the [retirement manifest](../../records/documentation/retirement-manifest.json); the removed content itself remains recoverable from Git history.

## Reading rule

Use evidence to answer “what was implemented, evaluated, or decided at a specific boundary.” Use `docs/PROJECT_STATUS.md`, active architecture, and exact contracts for the current authoritative boundary.
