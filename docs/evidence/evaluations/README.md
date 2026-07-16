---
relaylm_doc_type: documentation_index
relaylm_authority: evaluation_evidence_collection_router
relaylm_status: current
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - an evaluation or validation evidence record is added, moved, or retired
relaylm_not_authoritative_for:
  - current runtime behavior
  - repeatable evaluation methods
  - release readiness
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source: ../../adr/0002-documentation-information-architecture.md
---
# Evaluation Evidence

This collection contains dated or bounded validation and evaluation results. Use `docs/evaluation/` for repeatable methods and rubrics, and use current status or release documents for present implementation and readiness claims.

## Records

- [Phase I-3 branch validation receipt](phase_i3_validation_receipt.md) — frozen content-free verification evidence for PR #379.
- [E1 Local Runtime Evaluation — 2026-06-25](e1_local_runtime_evaluation_2026_06_25.md) — frozen first hands-on local workstation evaluation evidence connecting SOUL Lab Home, RelayLM, LM Studio, RelaySLP, O0, and Primary MEM formation/recall; moved here from `docs/architecture/` in Cutover 1C-40.

No LAT-1 retrieval-scaling result exists here yet. A completed run is
filled in from
[LAT-1 Retrieval Scaling Report Template](../../templates/evaluation/lat1-retrieval-scaling-report.md)
(method: [LAT-1 Retrieval Scaling Method](../../evaluation/lat1-retrieval-scaling.md))
and added here using the deterministic, collision-safe name
`lat1-retrieval-scaling-YYYY-MM-DD-HHMMSSZ-<short-commit>.md` (never a
date-only name, which could collide with a second run performed on the
same date).
