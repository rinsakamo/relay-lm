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

## Boundary

Preparation B decides target ownership and synthesis shape. Preparation C must generate the commit-fixed file-level inventory, provenance, normative-block digest inputs, path-bound CI dependency map, and dry-run validation before any canonical path move.
