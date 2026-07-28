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
  - current documentation placement
  - current runtime behavior
  - proof that the complete cutover is finished
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# Documentation Cutover Planning

This collection retains the adopted planning artifacts of the authority-first documentation hard cutover. Source-by-source Documentation Hard Cutover ended at 1C-57, which closed the numbered legacy slice sequence; no further per-source slice, per-source receipt, or bespoke source guard follows.

Current documentation synthesis and retirement are governed by the [Documentation Governance Contract](../contracts/documentation-governance.md), the canonical active graph generated from current-tree metadata, the generic documentation validators, and the [retirement manifest](../../records/documentation/retirement-manifest.json). The planning documents below record how the historical cutover was decided; they are not current authority for documentation placement, normative disposition, or retirement.

## Preparation B artifacts

- [Architecture inventory](documentation-architecture-inventory.md) — classifies current design, contract, handoff, audit, evaluation, planning, strategy, and archive families by actual authority.
- [Target architecture graph](documentation-target-architecture-graph.md) — defines the planned canonical system, subsystem, and concept/policy document graph.
- [Placement decisions](documentation-placement-decisions.md) — records how the placement and granularity tie-breakers apply to ambiguous current document families.

## Boundary

Preparation B decided target ownership and synthesis shape for the source-by-source cutover that closed at 1C-57. Those decisions are historical: this collection does not carry current authority. Merged Git history and the [retirement manifest](../../records/documentation/retirement-manifest.json) preserve the recovery identity of retired paths.

Continuing active-document, normative-disposition, link, and Git-recovery invariants are owned by the Documentation Governance Contract, the canonical active graph, the generic validators, and the retirement manifest.
