---
relaylm_doc_type: template
relaylm_authority: non_authoritative_document_template_index
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - documentation model or recommended document shape changes
relaylm_not_authoritative_for:
  - runtime behavior
  - exact contracts
  - implementation status
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# RelayLM Document Templates

These files are non-authoritative starting points. A generated document acquires its own authority, owner, status, and lifecycle; the template never supplies project facts.

## Templates

- [ADR](adr.md)
- [Proposal](proposal.md)
- [System architecture](system-architecture.md)
- [Subsystem architecture](subsystem-architecture.md)
- [Concept or policy design](concept-policy-design.md)
- [Contract](contract.md)
- [LAT-1 Retrieval Scaling Report](evaluation/lat1-retrieval-scaling-report.md) — subject-specific fillable template for a dated LAT-1 retrieval scaling run; see [LAT-1 Retrieval Scaling Method](../evaluation/lat1-retrieval-scaling.md) for the repeatable method it fills in.
- [OpenWebUI + LM Studio Manual Smoke Results](evaluation/openwebui-lmstudio-manual-smoke-results.md) — content-free reusable template for recording a future local manual-validation run; filled dated results belong in `docs/evidence/evaluations/`.
- [Mobile Dogfood Summary Report](evaluation/mobile-dogfood-summary-report.md), [Daily Note](evaluation/mobile-dogfood-daily-note.md), [Weekly Review](evaluation/mobile-dogfood-weekly-review.md) — content-free local-only stubs for the [Mobile Dogfood Observation Method](../evaluation/mobile-dogfood-observation.md); filled-in copies stay local and are never committed.

## Use rules

- Replace every placeholder before review.
- Delete instructions and examples that do not belong in the finished document.
- Do not invent a `relaylm_verified_by` relation when no real verification exists.
- Use `Not applicable: <reason>` when a recommended architecture section genuinely does not apply.
- Do not copy exact contract tables into architecture or guides.
- Do not place user content, protected source, credentials, traces, or private runtime data in a document.
- A template section is recommended structure, not automatically a blocking invariant.
