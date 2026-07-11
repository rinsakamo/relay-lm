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

This collection contains non-normative records retained because they support durable decisions, implementation verification, evaluation, releases, proposals, or documentation migrations. Evidence does not override current status, architecture, contracts, or accepted decisions.

## Collections

- `implementation/` — bounded implementation completion evidence.
- `waves/` — cross-slice convergence evidence.
- [Evaluations](evaluations/README.md) — dated evaluation and validation results.
- `releases/` — release and validation receipts.
- [Proposals](proposals/README.md) — accepted, rejected, or withdrawn proposal evidence.
- [Migrations](migrations/README.md) — cutover provenance and verification receipts.

## Reading rule

Use evidence to answer “what was implemented, evaluated, decided, or moved at a specific boundary.” Use `docs/PROJECT_STATUS.md`, active architecture, and exact contracts for the current authoritative boundary.
