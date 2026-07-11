---
relaylm_doc_type: documentation_index
relaylm_authority: documentation_cutover_planning_entrypoint
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - documentation preparation or cutover plans change
  - a preparation artifact is added or retired
  - a cutover batch starts or completes
relaylm_not_authoritative_for:
  - current documentation placement outside merged cutover entries
  - current runtime behavior
  - proof that the complete cutover is finished
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# Documentation Cutover Planning

This collection contains the adopted planning artifacts for the authority-first documentation hard cutover. The v0.1 validation and tag gate is complete, and Cutover 1 has started. Only merged entries in the migration receipt change canonical paths; planned targets remain non-current until their PR merges.

## Preparation B artifacts

- [Architecture inventory](documentation-architecture-inventory.md) — classifies current design, contract, handoff, audit, evaluation, planning, strategy, and archive families by actual authority.
- [Target architecture graph](documentation-target-architecture-graph.md) — defines the planned canonical system, subsystem, and concept/policy document graph.
- [Placement decisions](documentation-placement-decisions.md) — records how the placement and granularity tie-breakers apply to ambiguous current document families.

## Preparation C artifacts

- [Cutover tooling](documentation-cutover-tooling.md) — defines the commit-fixed inventory, provenance, normative digest, absolute/relative path dependencies, reproducibility, and CI artifact boundary.
- [`documentation-cutover-rules.yaml`](documentation-cutover-rules.yaml) — executable classification and graph-validation rules for the dry run.
- `scripts/relaylm_docs_cutover_prepare.py` — emits the full inventory, migration-receipt preview, repository-root path dependencies, and summary.
- `scripts/relaylm_docs_normative_digest.py` — emits source line ranges and SHA-256 digests for candidate normative blocks.
- `scripts/relaylm_docs_relative_link_inventory.py` — resolves relative Markdown links against each frozen referrer and emits the companion dependency inventory.

## Active execution evidence

- [Documentation hard-cutover migration receipt](../evidence/migrations/documentation-hard-cutover-receipt.md) — append-only record of merged path moves, evidence retention, deletions, synthesis, and exact-copy verification.

## Boundary

Preparation B decides target ownership and synthesis shape. Preparation C supplies the strict reproducible baseline. Cutover PRs now execute those decisions one authority at a time without redirect stubs or dual live paths.
