---
relaylm_doc_type: documentation_model
relaylm_authority: document_type_metadata_and_ai_reading_rules
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - document type changes
  - metadata field changes
  - AI reading instruction changes
  - placement rule changes
  - parallel implementation documentation flow changes
relaylm_not_authoritative_for:
  - current runtime behavior
  - implementation phase status
  - component responsibility and canonical target order
---
# RelayLM Documentation Model

## Purpose

This document defines the AI-first documentation model for RelayLM. RelayLM documentation is optimized for partial retrieval by ChatGPT, Codex, and other AI assistants as well as for human review.

The goal is not equal document length. The goal is unambiguous authority, status, lifetime, and update responsibility.

## Core rule

When an AI or human reads a single file out of context, the file must say:

- what type of document it is,
- what it is authoritative for,
- what it is not authoritative for,
- whether it describes current, target, compatibility, historical, or frozen behavior,
- when it should be updated.

## Required metadata

Active documentation SHOULD start with YAML front matter:

```yaml
---
relaylm_doc_type: stable_architecture
relaylm_authority: component_responsibility_and_target_order
relaylm_status: current
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - component responsibility changes
relaylm_not_authoritative_for:
  - implementation phase status
relaylm_current_status_source: ../PROJECT_STATUS.md
---
```

Use plain scalar or list values only. Do not encode source text, prompts, traces, cache bodies, or runtime-private data in metadata.

## Document types

| Type | Purpose | Typical location | Authority |
|---|---|---|---|
| `documentation_model` | AI-first documentation rules and metadata vocabulary | `docs/DOCUMENTATION_MODEL.md` | document type metadata and AI reading rules |
| `documentation_index` | Entry point or local map for documentation areas | `docs/README.md`, `docs/architecture/README.md` | navigation and local documentation map |
| `status` | Current developer-facing project state | `docs/PROJECT_STATUS.md` | current implemented boundary, active caveats, next candidates |
| `stable_architecture` | Durable responsibility, component, and target-order design | `docs/architecture/*_design.md` | stable architecture and ownership |
| `current_target_migration` | Current, compatibility, target, and migration interpretation | `docs/architecture/current_target_migration_guide.md` | current-vs-target interpretation and migration caveats |
| `implementation_plan` | Phase sequencing and implementation status | `docs/architecture/pipeline_implementation_plan.md` currently; future home may be `docs/implementation/` | implementation sequence and phase status |
| `implementation_handoff` | Bounded implementation slice record | `docs/architecture/phase*_handoff.md` currently; future home may be `docs/implementation/handoffs/` | completed or active slice record only |
| `implementation_completion_report` | PR-scoped implementation evidence and later convergence input | `docs/mvp/wave*/<slice>_completion_report.md` | one implementation PR's claimed boundary, evidence, limitations, and shared-doc update inputs only |
| `contract` | Exact schema, gate, artifact, and runtime contract | `docs/contracts/` or dedicated architecture contract docs | exact implemented or planned contract behavior |
| `smoke_howto` | Manual or automated validation procedure | `docs/smoke/` | validation steps and expected evidence |
| `adr` | Durable design decision and consequences | `docs/adr/` | decision rationale and supersession chain |
| `historical_evidence` | Previous MVP notes or archived rationale | `docs/mvp/`, `docs/architecture/archive/` | evidence only; never current authority |

## Status values

Use the following values consistently:

- `current`: implemented behavior or current authoritative guidance.
- `target`: design goal without a complete current producer, consumer, or apply path.
- `compatibility`: retained non-target behavior.
- `historical`: evidence from a previous slice.
- `historical_after_merge`: implementation handoff or completion report after the source PR has merged.
- `frozen`: preserved record that should not be edited except for metadata or link fixes.

## AI reading instructions

When answering questions about current RelayLM behavior:

1. Read `docs/PROJECT_STATUS.md` first.
2. Use `docs/architecture/pipeline_responsibility_design.md` for component responsibility and canonical target order.
3. Use `docs/architecture/pipeline_implementation_plan.md` for phase status and sequencing.
4. Use dedicated contracts for exact schemas, gates, artifacts, and bounded behavior.
5. Use `docs/architecture/current_target_migration_guide.md` before treating target or compatibility behavior as current.
6. Treat `docs/mvp/` and `docs/architecture/archive/` as historical evidence only.
7. Treat handoff docs as implementation records, not canonical architecture, after merge.
8. Treat an `implementation_completion_report` as evidence that one PR claims a bounded result, not as repository-wide completion authority.
9. During an explicitly declared parallel-wave merge window, inspect the source PR and completion report in addition to current status; do not infer that the next wave or release gate is open until the convergence documentation PR has merged.

## Placement rules

The current placement rules remain:

- repository-wide current status -> `docs/PROJECT_STATUS.md`
- stable cross-cutting architecture -> `docs/architecture/`
- exact schemas and contracts -> `docs/contracts/` or dedicated architecture contract docs
- smoke, troubleshooting, and evaluation docs -> `docs/smoke/`
- historical MVP snapshots and implementation completion reports -> `docs/mvp/`
- superseded architecture rationale -> `docs/architecture/archive/`
- RelaySOUL governance docs -> `docs/relaysoul/`

Future cleanup may move implementation plans and handoffs under `docs/implementation/`, but this document does not require a file move.

## Two-stage parallel implementation documentation

A wave may explicitly declare multiple implementation slices as parallel and reserve one later convergence/documentation slice, such as `W3-INT`, to update shared current-state documents. This is the preferred mode when the parallel PRs would otherwise edit the same status, roadmap, index, current-target, or governance-smoke lines.

### Stage 1: implementation PR

Each parallel implementation PR owns only:

- production code and directly coupled tests/workflows;
- exact configuration or schema documentation that must ship atomically with accepted runtime fields;
- a new slice-owned handoff or exact contract file whose path is unique to that slice;
- one unique `docs/mvp/wave*/<slice>_completion_report.md` file.

The implementation PR must not update shared current-state documents merely to mark its phase complete. In particular, it must not edit the repository-wide status, shared implementation plans, shared indexes, cross-slice current-target documents, previous-wave audit documents, or repository-wide documentation-boundary smoke unless its production change genuinely changes those documents' own contract rather than only their completion status.

The completion report is mandatory. It records the bounded implemented result, preserved authorities and non-goals, changed files, validation evidence, known limitations, source PR, and exact inputs that the convergence thread must apply to shared documentation. It contains no user/model content or runtime-private evidence.

The implementation PR must not add its report or new handoff to a shared index. The convergence PR performs indexing once all selected parallel slices have merged.

### Stage 2: convergence and shared-documentation PR

After the selected implementation PRs merge, the wave convergence thread must:

1. reread each merged PR, its unique completion report, and its dedicated handoff;
2. verify merge commits and cross-slice authority, race, security, and non-goal compatibility;
3. update `docs/PROJECT_STATUS.md`, shared plans, shared indexes, roadmaps, current-target documents, and repository-wide documentation smoke in one PR;
4. add central links to the completion reports and dedicated handoffs where appropriate;
5. record any divergence between a report and the merged implementation;
6. keep the next wave and release/evaluation gate closed until this convergence PR is green and merged.

A temporary status lag between an implementation merge and the convergence merge is allowed only for a declared parallel wave. The completion report and source PR are the bounded evidence during that interval, while `docs/PROJECT_STATUS.md` remains the repository-wide current-status authority and must be reconciled promptly by the convergence PR.

### Shared documents normally reserved for convergence

Unless a slice has explicit ownership for a real contract change, parallel implementation PRs should leave these files to the convergence thread:

```text
docs/PROJECT_STATUS.md
docs/README.md
docs/architecture/README.md
docs/architecture/pipeline_implementation_plan.md
docs/architecture/post_i3_evaluation_work_roadmap.md
docs/architecture/relaymem_mvp_implementation_plan.md
docs/architecture/relaymem_slp_current_target.md
docs/architecture/wave*_cross_slice_convergence_audit.md
scripts/relaylm_documentation_current_boundary_smoke.py
```

Exact config/schema documents such as `docs/config_schema.md` and `config.example.yaml` remain implementation-coupled when a slice adds accepted production fields.

## Front matter examples

### Stable architecture

```yaml
---
relaylm_doc_type: stable_architecture
relaylm_authority: component_responsibility_and_canonical_target_order
relaylm_status: current
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - component responsibility changes
  - canonical runtime order changes
relaylm_not_authoritative_for:
  - current implementation phase status
  - exact schema details
  - smoke procedures
relaylm_current_status_source: ../PROJECT_STATUS.md
---
```

### Implementation handoff

```yaml
---
relaylm_doc_type: implementation_handoff
relaylm_authority: bounded_slice_record
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - canonical architecture
  - current runtime behavior
  - future sequencing
---
```

### Implementation completion report

```yaml
---
relaylm_doc_type: implementation_completion_report
relaylm_authority: wave3_i4d_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - cross-slice sequencing
  - other phase completion
---
```

Use [the completion report template](mvp/IMPLEMENTATION_COMPLETION_REPORT_TEMPLATE.md). The source implementation PR must contain a concrete PR number before final review. The convergence thread obtains and records the merge commit from GitHub; the completion report does not need a self-referential head SHA.

### Contract

```yaml
---
relaylm_doc_type: contract
relaylm_authority: exact_schema_and_gate_behavior
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: contracts
relaylm_update_trigger:
  - schema changes
  - producer or consumer changes
  - apply skip or block behavior changes
relaylm_not_authoritative_for:
  - project phase sequencing
  - historical rationale
---
```

## Maintenance rule

When adding or moving a document:

1. Choose one document type.
2. State what the document is authoritative for.
3. State what it is not authoritative for.
4. Add an update trigger when the document is mutable.
5. Link to the current status source when the document may be found by search.
6. Preserve unique design intent before archiving or deleting older material.
7. For a declared parallel wave, follow the two-stage implementation-report and convergence flow instead of editing shared current-state documents in every implementation PR.
