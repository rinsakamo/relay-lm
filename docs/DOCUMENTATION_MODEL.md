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
| `implementation_plan` | MVP boundary, dependency sequencing, and post-MVP roadmap | `docs/architecture/project_execution_plan.md` | execution sequence and roadmap only, not current implementation status |
| `redirect_stub` | Compatibility pointer from an older authority path | old plan/roadmap paths | redirect only; never status or sequencing authority |
| `stable_architecture` | Durable responsibility, component, and target-order design | `docs/architecture/*_design.md` | stable architecture and ownership |
| `architecture` | Older compatibility alias for stable architecture docs | older `docs/architecture/*.md` files | interpret as `stable_architecture`; prefer canonical `stable_architecture` for new or touched docs |
| `architecture_report` | Older compatibility alias for architecture/governance reports | older `docs/architecture/*.md` reports | interpret as architecture guidance; prefer a canonical type such as `stable_architecture`, `implementation_plan`, `contract`, or `evaluation_record` when a touched doc clearly fits one |
| `current_target_migration` | Current, compatibility, target, and migration interpretation | `docs/architecture/current_target_migration_guide.md`, `docs/architecture/relaymem_slp_current_target.md` | current-vs-target interpretation and migration caveats |
| `implementation_handoff` | Bounded implementation slice record | `docs/architecture/phase*_handoff.md` and dedicated architecture handoff docs | completed or active slice record only |
| `architecture_handoff` | Older alias for a bounded implementation handoff | `docs/architecture/e1r*.md`, `docs/architecture/phase_i*.md` | completed or active slice record only; prefer `implementation_handoff` for new docs |
| `implementation_completion_report` | PR-scoped implementation evidence and later convergence input | `docs/mvp/wave*/<slice>_completion_report.md` | one implementation PR's claimed boundary, evidence, limitations, and shared-doc update inputs only |
| `contract` | Exact schema, gate, artifact, and runtime contract | `docs/contracts/` or dedicated architecture contract docs | exact implemented or planned contract behavior |
| `smoke_howto` | Manual or automated validation procedure | `docs/smoke/` | validation steps and expected evidence |
| `validation_receipt` | Frozen validation result or receipt-style proof record | `docs/architecture/*validation*receipt*.md`, `docs/mvp/` | validation evidence only; never current implementation status |
| `cross_slice_convergence_audit` | Cross-slice convergence audit over merged implementation tracks | `docs/architecture/wave*_cross_slice_convergence_audit.md` | historical convergence evidence and shared-doc inputs |
| `integration_convergence_audit` | Integration-wave convergence audit over merged tracks | `docs/architecture/wave*_cross_slice_convergence_audit.md` | historical integration convergence evidence and shared-doc inputs |
| `evaluation_record` | Local or bounded evaluation run record | `docs/architecture/*evaluation*.md` | evaluation evidence only; not runtime status authority |
| `evaluation_consolidation` | Current evaluation evidence synthesis | `docs/architecture/e1_evaluation_consolidation.md` | current evaluation proof boundary and evidence inventory |
| `adr` | Durable design decision and consequences | `docs/adr/` | decision rationale and supersession chain |
| `historical_evidence` | Previous MVP notes or archived rationale | `docs/mvp/`, `docs/architecture/archive/` | evidence only; never current authority |

New documents should prefer the canonical type names above. Existing documents using a listed compatibility alias do not need a rename-only PR, but the alias must be listed here so AI-first readers can interpret it safely. When a compatibility-alias document is otherwise touched for substantive content, prefer moving it to the closest canonical type in the same PR.

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
2. Use `docs/architecture/project_execution_plan.md` for MVP boundary, dependency sequencing, and post-MVP roadmap ordering.
3. Use `docs/architecture/pipeline_responsibility_design.md` for component responsibility and canonical target order.
4. Use dedicated contracts for exact schemas, gates, artifacts, and bounded behavior.
5. Use `docs/architecture/current_target_migration_guide.md` before treating target or compatibility behavior as current.
6. Treat `docs/mvp/` and `docs/architecture/archive/` as historical evidence only.
7. Treat handoff docs as implementation records, not canonical architecture, after merge unless they are the dedicated current exact-boundary document for a still-current slice.
8. Treat an `implementation_completion_report` as evidence that one PR claims a bounded result, not as repository-wide completion authority.
9. During an explicitly declared parallel-wave merge window, inspect the source PR and completion report in addition to current status; do not infer that the next wave or release gate is open until the convergence documentation PR has merged.

## Placement rules

The current placement rules remain:

- repository-wide current status -> `docs/PROJECT_STATUS.md`
- MVP execution plan and post-MVP roadmap -> `docs/architecture/project_execution_plan.md`
- stable cross-cutting architecture -> `docs/architecture/`
- exact schemas and contracts -> `docs/contracts/` or dedicated architecture contract docs
- smoke, troubleshooting, and evaluation docs -> `docs/smoke/`
- historical MVP snapshots and implementation completion reports -> `docs/mvp/`
- superseded architecture rationale -> `docs/architecture/archive/`
- RelaySOUL governance docs -> `docs/relaysoul/`

Future cleanup may move implementation handoffs under `docs/implementation/`, but this document does not require a file move.

## Two-stage parallel implementation documentation

A wave may explicitly declare multiple implementation slices as parallel and reserve one later convergence/documentation slice, such as `W3-INT`, to update shared current-state documents. This is the preferred mode when the parallel PRs would otherwise edit the same status, execution plan, index, current-target, or governance-smoke lines.

### Stage 1: implementation PR

Each parallel implementation PR owns only:

- production code and directly coupled tests/workflows;
- exact configuration or schema documentation that must ship atomically with accepted runtime fields;
- a new slice-owned handoff or exact contract file whose path is unique to that slice;
- one unique `docs/mvp/wave*/<slice>_completion_report.md` file.

The implementation PR must not update shared current-state documents merely to mark its phase complete. In particular, it must not edit the repository-wide status, shared execution plan, shared indexes, cross-slice current-target documents, previous-wave audit documents, or repository-wide documentation-boundary smoke unless its production change genuinely changes those documents' own contract rather than only their completion status.

The completion report is mandatory. It records the bounded implemented result, preserved authorities and non-goals, changed files, validation evidence, known limitations, source PR, and exact inputs that the convergence thread must apply to shared documentation. It contains no user/model content or runtime-private evidence.

The implementation PR must not add its report or new handoff to a shared index. The convergence PR performs indexing once all selected parallel slices have merged.

### Stage 2: convergence and shared-documentation PR

After the selected implementation PRs merge, the wave convergence thread must:

1. reread each merged PR, its unique completion report, and its dedicated handoff;
2. verify merge commits and cross-slice authority, race, security, and non-goal compatibility;
3. update `docs/PROJECT_STATUS.md`, `docs/architecture/project_execution_plan.md`, shared indexes, current-target documents, and repository-wide documentation smoke in one PR;
4. sweep directly affected feature-family master/contract documents named by `relaylm_update_trigger`, `relaylm_related_authority`, completion-report shared-doc inputs, or grep hits for the completed phase names;
5. add central links to the completion reports and dedicated handoffs where appropriate;
6. record any divergence between a report and the merged implementation;
7. keep the next wave and release/evaluation gate closed until this convergence PR is green and merged.

The feature-family sweep is mandatory. A convergence PR must not leave a non-frozen master or contract document saying that an already completed subphase such as `I-4E`, `I-4F`, `O1D2`, `O1E`, `O1F`, `UI-B1A`, `E1-R4`, or `E1-R5` remains unimplemented, future work, or outside the proven boundary unless that sentence is explicitly about a different downstream capability such as O2/O3, Pin/Unpin runtime apply, Held Apply/Discard runtime, or a broader future replacement.

A temporary status lag between an implementation merge and the convergence merge is allowed only for a declared parallel wave. The completion report and source PR are the bounded evidence during that interval, while `docs/PROJECT_STATUS.md` remains the repository-wide current-status authority and must be reconciled promptly by the convergence PR.

### Shared documents normally reserved for convergence

Unless a slice has explicit ownership for a real contract change, parallel implementation PRs should leave these files to the convergence thread:

```text
docs/PROJECT_STATUS.md
docs/README.md
docs/architecture/README.md
docs/architecture/project_execution_plan.md
docs/architecture/relaymem_slp_current_target.md
docs/architecture/wave*_cross_slice_convergence_audit.md
scripts/relaylm_documentation_current_boundary_smoke.py
```

The legacy plan and roadmap stub files are not sequencing authorities and normally change only when their redirect target changes.
