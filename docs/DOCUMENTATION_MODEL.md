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
- `historical_after_merge`: implementation handoff after the PR has merged.
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

## Placement rules

The current placement rules remain:

- repository-wide current status -> `docs/PROJECT_STATUS.md`
- stable cross-cutting architecture -> `docs/architecture/`
- exact schemas and contracts -> `docs/contracts/` or dedicated architecture contract docs
- smoke, troubleshooting, and evaluation docs -> `docs/smoke/`
- historical MVP snapshots -> `docs/mvp/`
- superseded architecture rationale -> `docs/architecture/archive/`
- RelaySOUL governance docs -> `docs/relaysoul/`

Future cleanup may move implementation plans and handoffs under `docs/implementation/`, but this document does not require a file move.

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
4. Add an update trigger.
5. Link to the current status source when the document may be found by search.
6. Preserve unique design intent before archiving or deleting older material.
