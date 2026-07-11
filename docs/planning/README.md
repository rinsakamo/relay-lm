---
relaylm_doc_type: documentation_index
relaylm_authority: documentation_cutover_planning_entrypoint
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - documentation preparation or cutover plans change
  - a preparation artifact is added or retired
relaylm_not_authoritative_for:
  - current documentation placement
  - current runtime behavior
  - proof that cutover has started or completed
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# Documentation Cutover Planning

This collection contains target planning artifacts for the authority-first documentation hard cutover. It does not move existing canonical documents or activate final directory invariants.

## Preparation B artifacts

- [Architecture inventory](documentation-architecture-inventory.md) — classifies current design, contract, handoff, audit, evaluation, planning, and strategy families by actual authority.
- [Target architecture graph](documentation-target-architecture-graph.md) — defines the planned canonical system, subsystem, and concept/policy document graph.
- [Placement decisions](documentation-placement-decisions.md) — records how the placement and granularity tie-breakers apply to ambiguous current document families.

## Preparation C artifacts

- [Cutover tooling](documentation-cutover-tooling.md) — defines the commit-fixed inventory, provenance, normative digest, path-dependency, reproducibility, and CI artifact boundary.
- [`documentation-cutover-rules.yaml`](documentation-cutover-rules.yaml) — executable classification and graph-validation rules for the dry run.
- `scripts/relaylm_docs_cutover_prepare.py` — emits the full inventory, migration-receipt preview, path dependencies, and summary.
- `scripts/relaylm_docs_normative_digest.py` — emits source line ranges and SHA-256 digests for candidate normative blocks.

## Boundary

Preparation B decides target ownership and synthesis shape. Preparation C turns those decisions into a strict reproducible dry run before any canonical path move. Neither preparation phase authorizes path changes before the v0.1 frozen tag receipt.
