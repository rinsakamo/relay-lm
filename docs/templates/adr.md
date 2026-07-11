---
relaylm_doc_type: template
relaylm_authority: non_authoritative_adr_template
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - ADR lifecycle or metadata changes
relaylm_not_authoritative_for:
  - any project decision
  - runtime behavior
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# ADR Template

Copy this file to `docs/adr/NNNN-short-title.md` and replace all placeholders.

```markdown
---
relaylm_doc_type: adr
relaylm_authority: <decision authority key>
relaylm_status: <current | target>
relaylm_decision_status: <proposed | accepted | rejected | superseded>
relaylm_decided_on: YYYY-MM-DD
relaylm_volatility: low
relaylm_owner: <owner>
relaylm_update_trigger:
  - decision is superseded
relaylm_not_authoritative_for:
  - current implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_supersedes: []
relaylm_superseded_by: null
---
# ADR NNNN: <Stable decision title>

<Authority summary.>

## Status

<Decision state and implementation distinction.>

## Context

<Problem, constraints, and why a durable decision is required.>

## Decision

<The selected rule or architecture.>

## Consequences

### Positive

- <benefit>

### Costs

- <cost>

## Rejected alternatives

### <Alternative>

<Reason for rejection.>

## Fixed boundaries

- <Invariant that remains true.>

## Related documents

- <Proposal, architecture, contract, or status links.>
```
