---
relaylm_doc_type: template
relaylm_authority: non_authoritative_contract_template
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - contract document shape or normative migration rule changes
relaylm_not_authoritative_for:
  - any runtime contract
  - implementation status
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# Contract Template

```markdown
---
relaylm_doc_type: contract
relaylm_authority: <exact boundary authority key>
relaylm_status: <current | target>
relaylm_volatility: low
relaylm_owner: <owner>
relaylm_update_trigger:
  - <schema, gate, API, artifact, state, or invariant changes>
relaylm_not_authoritative_for:
  - repository-wide implementation status
  - architectural rationale outside this boundary
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_code_sources: []
relaylm_verified_by: []
---
# <Exact contract title>

<Authority summary identifying the exact boundary.>

## Purpose

## Scope

## Normative definitions

## Inputs

## Outputs

## Required behavior

## Forbidden behavior

## State and transitions

## Failure behavior

## Privacy and security invariants

## Verification

## Non-goals

## Related architecture
```

Remove empty optional metadata fields rather than leaving invented relations. Normative wording changed for behavior reasons belongs in a dedicated contract-change PR. During documentation cutover, normative blocks are moved verbatim and digest-verified against the source blob.
