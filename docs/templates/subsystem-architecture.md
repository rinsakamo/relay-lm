---
relaylm_doc_type: template
relaylm_authority: non_authoritative_subsystem_architecture_template
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - subsystem architecture shape changes
relaylm_not_authoritative_for:
  - any subsystem architecture
  - exact contracts
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# Subsystem Architecture Template

```markdown
---
relaylm_doc_type: subsystem_architecture
relaylm_authority: <subsystem authority key>
relaylm_status: <current | target>
relaylm_volatility: low
relaylm_owner: <owner>
relaylm_update_trigger:
  - <subsystem responsibility, lifecycle, or boundary changes>
relaylm_not_authoritative_for:
  - exact schemas and field values
  - repository-wide implementation status
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_contracts: []
---
# <Stable subsystem title>

<Authority summary.>

## Purpose

## Scope

## Inputs and outputs

## Owned responsibilities

## Explicit non-responsibilities

## Internal components

## State/lifecycle model

## Data/control flow

## Failure and recovery boundary

## Privacy/security boundary

## Stable invariants

## Related contracts
```

A short subsystem document may mark a genuinely irrelevant section `Not applicable: <reason>`. Do not include milestone completion history or duplicate contract tables.
