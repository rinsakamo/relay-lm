---
relaylm_doc_type: template
relaylm_authority: non_authoritative_concept_policy_template
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - concept or policy document shape changes
relaylm_not_authoritative_for:
  - any concept or policy
  - exact contracts
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# Concept or Policy Design Template

```markdown
---
relaylm_doc_type: concept_policy
relaylm_authority: <concept authority key>
relaylm_status: <current | target>
relaylm_volatility: low
relaylm_owner: <owner>
relaylm_update_trigger:
  - <concept semantics or policy changes>
relaylm_not_authoritative_for:
  - exact schemas and field values
  - implementation completion status
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_contracts: []
---
# <Stable concept or policy title>

<Authority summary.>

## Problem

## Definition

## Scope

## Semantic model

## Invariants

## Interaction with components

## Trade-offs

## Non-goals

## Related architecture and contracts
```

Concept notes may remain short. Use `Not applicable: <reason>` rather than padding a section with generic text.
