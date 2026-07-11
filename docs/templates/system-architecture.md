---
relaylm_doc_type: template
relaylm_authority: non_authoritative_system_architecture_template
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - system architecture shape changes
relaylm_not_authoritative_for:
  - any system architecture
  - exact contracts
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# System Architecture Template

```markdown
---
relaylm_doc_type: system_architecture
relaylm_authority: <system authority key>
relaylm_status: <current | target>
relaylm_volatility: low
relaylm_owner: <owner>
relaylm_update_trigger:
  - <system responsibility or boundary changes>
relaylm_not_authoritative_for:
  - exact schemas and field values
  - repository-wide implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_contracts: []
---
# <Stable system title>

<Authority summary.>

## Purpose

## System context

## Responsibility map

## Canonical data/control flow

## Ownership boundaries

## System-wide invariants

## Failure and privacy boundaries

## Extension points

## Related subsystem architecture

## Related contracts

## Non-goals
```

Use `Not applicable: <reason>` only when a section truly does not apply. Do not embed exact field tables or implementation completion history.
