---
relaylm_doc_type: template
relaylm_authority: non_authoritative_proposal_template
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - proposal lifecycle or metadata changes
relaylm_not_authoritative_for:
  - any project proposal
  - accepted decisions
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# Proposal Template

Copy this file to `docs/proposals/<stable-name>.md` and replace all placeholders.

```markdown
---
relaylm_doc_type: proposal
relaylm_authority: <proposal scope key>
relaylm_status: target
relaylm_proposal_status: under_review
relaylm_volatility: medium
relaylm_owner: <owner>
relaylm_update_trigger:
  - proposal is accepted, rejected, withdrawn, or materially revised
relaylm_not_authoritative_for:
  - current runtime behavior
  - implementation authorization
  - implementation completion
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# <Proposal title>

<Authority summary stating that this is an undecided proposal.>

## Problem

<What is wrong or missing.>

## Goals

- <goal>

## Non-goals

- <non-goal>

## Proposed decision

<Concrete recommendation.>

## Alternatives

### <Alternative>

<Trade-off.>

## Risks and mitigations

- <risk and mitigation>

## Adoption boundary

<What an accepting ADR would authorize and what remains deferred.>

## Validation

<How the proposal can be checked before or during adoption.>
```

After disposition, create or link the decision source and archive the proposal under `docs/evidence/proposals/` with historical or frozen status.
