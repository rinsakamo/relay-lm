---
relaylm_doc_type: template
relaylm_authority: non_authoritative_implementation_completion_report_template
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - completion-report model or required evidence shape changes
relaylm_not_authoritative_for:
  - any implementation result
  - current runtime behavior
  - repository-wide implementation status
  - cross-slice sequencing
  - release or evaluation readiness
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# Implementation Completion Report Template

This is a non-authoritative starting point, not a report. Copying it and filling in every placeholder does not by itself create evidence; the copy becomes PR-scoped evidence only once every placeholder below is replaced with concrete, verified facts about one implementation pull request.

Copy this file to:

```text
docs/evidence/implementation/<slice>_completion_report.md
```

The generated report must use the completion-report evidence metadata convention already established in that collection (`relaylm_doc_type: implementation_completion_report`, `relaylm_status: historical_after_merge`, `relaylm_volatility: frozen`, plus the recorded source/provenance keys shown below), not this template's own `template` / `target` metadata. This template supplies structure only; it never supplies project facts, authority, or status.

## Use rules

- One implementation pull request owns exactly one uniquely named report. Do not edit this template, `docs/mvp/README.md`, `docs/evidence/implementation/README.md`, another slice's report, or shared current-state documents merely to record completion.
- The report does not open the next wave and does not open the release or evaluation gate.
- Current repository status remains [Project Status](../PROJECT_STATUS.md)-owned; do not restate it here as if this report were authoritative for it.
- Shared cross-slice sequencing remains owned by the current planning authority; do not restate or override it here.
- The source pull request number and URL must be concrete before final review — replace every `<number>` and `TBD` placeholder. No self-referential final-head SHA is required; the wave convergence thread obtains and records the merge commit from GitHub.
- Do not record protected content, raw traces, credentials, or other runtime-private values anywhere in the report.

```markdown
---
relaylm_doc_type: implementation_completion_report
relaylm_authority: <slice>_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - MVP dependency sequencing
  - other slice completion
  - next-wave readiness
  - release or evaluation readiness
relaylm_source_commit: <40-character source commit SHA>
relaylm_source_origin_commit: <40-character source or origin/merge commit SHA>
relaylm_source_pr: <number>
relaylm_recorded_on: <YYYY-MM-DD>
relaylm_source_blob: <40-character source blob SHA>
relaylm_source_content_sha256: <64-character source content SHA-256>
relaylm_pre_cutover_blob: <40-character pre-cutover blob SHA>
relaylm_pre_cutover_content_sha256: <64-character pre-cutover content SHA-256>
relaylm_exact_source_snapshot: <slice>_completion_report-source.txt
---
# <Slice> Completion Report

This report is evidence for one implementation pull request. It is not repository-wide current-status authority and does not open the next wave or release/evaluation gate.

## Scope

Record the slice, goal, base branch, and start main SHA.

## Implemented production boundary

Describe only the production or validation boundary implemented by this pull request.

## Preserved authorities and non-goals

List reused authorities and responsibilities left to later phases.

## Changed files

List production modules, tests, workflows, exact schema/config documents, and the unique slice-owned handoff.

## Validation evidence

Record commands, smokes, regression workflows, fault/concurrency/security coverage, and final CI state. Do not include protected content, raw traces, credentials, or runtime-private values.

## Known limitations

State all remaining gaps and environment-specific limitations.

## Shared documentation update inputs

Provide exact facts for the wave convergence thread: completion wording, remaining boundaries, handoff path, config/schema changes, cross-slice risks, dependencies, and recommended next phase.

## Source pull request

- PR: #<number>
- URL: https://github.com/rinsakamo/relay-lm/pull/<number>

Record a concrete pull request number and URL before final review. The convergence thread obtains and records the merge commit from GitHub. Do not add a self-referential final head SHA.
```
