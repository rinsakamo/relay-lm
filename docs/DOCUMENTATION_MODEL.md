---
relaylm_doc_type: documentation_model
relaylm_authority: document_types_metadata_lifecycle_and_ai_reading_rules
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - document type or metadata field changes
  - authority or placement rules change
  - proposal or ADR lifecycle changes
  - audit severity changes
  - documentation cutover completes
relaylm_not_authoritative_for:
  - current runtime behavior
  - implementation phase status
  - component responsibility or exact runtime contracts
relaylm_current_status_source: PROJECT_STATUS.md
relaylm_related_decisions:
  - adr/0002-documentation-information-architecture.md
---
# RelayLM Documentation Model

RelayLM documentation is optimized for partial retrieval by humans and AI agents. This document is authoritative for document types, metadata, lifecycle, placement interpretation, and AI reading rules. It does not authorize runtime behavior or claim implementation completion.

## Purpose

The documentation model makes every active document answer the following questions without relying on surrounding files:

- What is this document authoritative for?
- What is it not authoritative for?
- Does it describe current behavior, a target, or historical evidence?
- Who owns it and what change should trigger an update?
- Which contract, code, test, decision, or status source is related?

Equal document length is not a goal. Unambiguous authority, stable concepts, bounded scope, and reliable retrieval are the goals.

## Adoption and activation boundary

ADR [0002](adr/0002-documentation-information-architecture.md) adopts the authority-first hard-cutover model.

Preparation may add the new model, templates, glossary, inventory, graph, and migration tooling before the v0.1 frozen tag receipt. Existing canonical paths are not moved or deleted until the cutover starts immediately after that receipt is finalized.

During Preparation:

- existing documents may retain their current type and path until their cutover PR;
- new documents must use the canonical types defined here rather than legacy aliases;
- no redirect stub, legacy manifest, old/new dual-path allowance, or new `historical_after_merge` document may be introduced;
- a PR that later moves a document must update every path-bound audit, workflow, script, and live link in the same PR.

At cutover completion, the existing-only legacy types and statuses listed below are removed from the active model.

## Required metadata

Active and retained evidence Markdown should start with YAML front matter using plain scalar or list values.

```yaml
---
relaylm_doc_type: subsystem_architecture
relaylm_authority: primary_memory_formation_responsibilities
relaylm_status: current
relaylm_volatility: low
relaylm_owner: memory
relaylm_update_trigger:
  - Primary MEM formation ownership changes
relaylm_not_authoritative_for:
  - exact wire schemas
  - repository-wide implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_contracts:
  - ../contracts/primary-memory-candidate.md
relaylm_code_sources:
  - ../relaylm/...
relaylm_verified_by:
  - ../scripts/...
---
```

Required core fields for active documents:

- `relaylm_doc_type`
- `relaylm_authority`
- `relaylm_status`
- `relaylm_volatility`
- `relaylm_owner`
- `relaylm_update_trigger`
- `relaylm_not_authoritative_for`

`relaylm_current_status_source` is required when a document could otherwise be mistaken for repository-wide implementation status.

Relationship metadata is conditional:

- `relaylm_related_contracts` only when related contracts exist;
- `relaylm_code_sources` only when concrete code ownership exists;
- `relaylm_verified_by` only when a real test, script, or workflow verifies the named boundary;
- `relaylm_decision_source` for documents governed by an accepted ADR;
- `relaylm_source_commit`, `relaylm_source_pr`, and `relaylm_recorded_on` for historical evidence.

Do not put source text, prompts, traces, cache bodies, user content, credentials, or runtime-private data in metadata.

## Canonical document types

| Type | Purpose | Canonical location | Authority |
|---|---|---|---|
| `documentation_model` | Documentation vocabulary, lifecycle, placement, and AI reading rules | `docs/DOCUMENTATION_MODEL.md` | documentation model only |
| `documentation_index` | Repository or collection-local navigation | `docs/README.md`, collection `README.md` | navigation only |
| `status` | Current repository-wide implementation state | `docs/PROJECT_STATUS.md` | implemented boundary, caveats, next candidates |
| `proposal` | Undecided change proposal | `docs/proposals/` | proposal argument only; not an accepted decision |
| `adr` | Durable accepted or rejected decision and consequences | `docs/adr/` | decision rationale and supersession chain |
| `system_architecture` | Repository-wide or system-wide responsibilities and flows | `docs/architecture/` | durable system structure and ownership |
| `subsystem_architecture` | Independently changing component or subsystem design | `docs/architecture/<domain>/` | subsystem inputs, outputs, lifecycle, and ownership |
| `concept_policy` | Cross-component semantic concept or policy | `docs/architecture/<domain>/` | concept definition, invariants, and trade-offs |
| `contract` | Exact schema, gate, API, artifact, state, or must/must-not invariant | `docs/contracts/` | exact normative boundary |
| `guide` | Task-oriented instructions with prerequisites and expected results | `docs/guides/` | procedure for the named task |
| `reference` | Field, option, CLI, API, glossary, or interpretation reference | `docs/reference/` | lookup information for the named surface |
| `strategy` | Non-binding long-horizon direction and product principles | `docs/strategy/` | strategic direction only |
| `planning` | Execution order, dependencies, roadmap, and migration sequencing | `docs/planning/` | sequencing only; not current completion status |
| `operations` | Operator runbook, smoke procedure, or tooling operation | `docs/operations/` | operational procedure and interpretation |
| `evaluation_method` | Rubric, scenario, or repeatable evaluation method | `docs/evaluation/` | evaluation method only |
| `release` | Current release criteria and readiness interpretation | `docs/release/` | release gate interpretation only |
| `evidence` | Non-normative implementation, evaluation, release, proposal, or migration record | `docs/evidence/` | historical evidence only |
| `template` | Non-authoritative document starting point | `docs/templates/` | no project authority |

## Existing-only pre-cutover types

The following types remain readable only because existing files still use them before cutover. Do not use them for new documents.

| Type | Pre-cutover interpretation | Required cutover destination |
|---|---|---|
| `implementation_plan` | execution sequencing | `planning` |
| `strategic_vision` | non-binding direction | `strategy` |
| `stable_architecture` | durable architecture | one of the three architecture types |
| `architecture` | legacy architecture alias | one of the three architecture types |
| `architecture_report` | mixed architecture or report | split by authority |
| `current_target_migration` | current/target interpretation | `reference` or `planning` |
| `implementation_handoff` | bounded implementation evidence | `evidence` |
| `implementation_contract` | exact contract mixed with handoff material | `contract` plus evidence if needed |
| `architecture_handoff` | legacy handoff alias | `evidence` |
| `implementation_completion_report` | PR-scoped evidence | `evidence` |
| `runbook` | operational procedure | `operations` |
| `smoke_howto` | validation procedure | `operations` |
| `release_readiness_assessment` | current pre-v0.1 readiness assessment | `release` |
| `validation_receipt` | frozen validation evidence | `evidence` |
| `cross_slice_convergence_audit` | merged-wave evidence | `evidence` |
| `integration_convergence_audit` | integration evidence | `evidence` |
| `evaluation_record` | dated or bounded evaluation evidence | `evidence` |
| `evaluation_consolidation` | current evaluation synthesis | `evaluation_method` or `release`, with dated results in evidence |
| `historical_evidence` | non-normative historical material | `evidence` or Git history only |
| `redirect_stub` | old-path compatibility pointer | delete; never create a new one |

## Status values

Canonical statuses:

- `current`: current authoritative guidance or implemented behavior.
- `target`: an adopted or proposed target that is not fully implemented.
- `historical`: non-normative evidence from a completed or superseded context.
- `frozen`: a preserved record changed only for metadata or link repair.

Existing-only pre-cutover statuses:

- `compatibility`: existing non-target compatibility behavior; do not assign to new docs.
- `historical_after_merge`: existing merged handoff/report marker; normalize to `historical` during cutover and do not assign to new docs.

Decision state is separate from implementation status:

```yaml
relaylm_doc_type: adr
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-11
relaylm_supersedes: []
relaylm_superseded_by: null
```

`accepted` does not mean implemented.

## One document, one primary authority

An active document must not combine independent authorities such as:

- architecture and exact contract;
- implementation handoff and current contract;
- evaluation method and dated result;
- release readiness and frozen receipt;
- proposal and accepted decision;
- strategy and committed execution plan;
- generated reference and a hand-written duplicate source of truth.

Split a document when owner, update trigger, lifecycle, independent consumer, or replacement boundary differs.

## Architecture subtypes

### System architecture

Recommended sections:

- Purpose
- System context
- Responsibility map
- Canonical data/control flow
- Ownership boundaries
- System-wide invariants
- Failure and privacy boundaries
- Extension points
- Related subsystem architecture
- Related contracts
- Non-goals

### Subsystem architecture

Recommended sections:

- Purpose
- Scope
- Inputs and outputs
- Owned responsibilities
- Explicit non-responsibilities
- Internal components
- State/lifecycle model
- Data/control flow
- Failure and recovery boundary
- Privacy/security boundary
- Stable invariants
- Related contracts

### Concept or policy design

Recommended sections:

- Problem
- Definition
- Scope
- Semantic model
- Invariants
- Interaction with components
- Trade-offs
- Non-goals
- Related architecture and contracts

These are retrieval and review aids, not unconditional blockers. A short concept note may use `Not applicable: <reason>` for sections that genuinely do not apply.

## Placement tie-breaker

When a document could fit more than one collection, apply this order:

1. Exact schema, gate, artifact, API, or must/must-not invariant -> `contracts/`.
2. Time, dependency, implementation order, or migration sequence -> `planning/`.
3. Lookup data, current/target interpretation, fields, options, or glossary -> `reference/`.
4. Non-binding horizon direction -> `strategy/`.
5. Durable structure, responsibility, ownership, or semantic design -> `architecture/`.
6. Procedure and troubleshooting flow -> `guides/` or `operations/` depending on operator scope.
7. Dated result, completion proof, audit, receipt, or retired proposal -> `evidence/`.

If multiple primary authorities remain after this test, split the document.

## Pre-cutover current placement anchors

Until the hard cutover begins, existing path-bound CI continues to interpret these current placements:

- manual smoke, troubleshooting, and local behavior validation docs -> `docs/smoke/`
- offline tooling specifications and runbooks -> `docs/tools/`
- evaluation templates and run records -> `docs/evaluation/`

These are temporary current-path anchors, not target placement rules. Each move updates the corresponding audit and workflow in the same PR. Evaluation templates remain non-authoritative starting points; blank templates are not measured evidence.

## Proposal lifecycle

```text
proposals/<name>.md
  ├── accepted -> ADR + normative docs + evidence/proposals/
  ├── rejected -> decision source + evidence/proposals/
  └── withdrawn -> reason + evidence/proposals/
```

Proposal metadata:

```yaml
relaylm_doc_type: proposal
relaylm_status: target
relaylm_proposal_status: under_review
```

After disposition, the proposal is historical or frozen evidence and points to the decision source. The accepted documentation hard-cutover proposal may be moved with Preparation or the first cutover PR, as authorized by ADR 0002.

## ADR lifecycle

- New ADR filenames use `NNNN-short-title.md`.
- ADR decision status is `proposed`, `accepted`, `rejected`, or `superseded`.
- ADR implementation status remains in `relaylm_status` and current status documents.
- Existing unnumbered ADRs receive deterministic numbers once during cutover.
- After canonicalization, ADR paths are stable.
- Redirect stubs are not created.

## Naming and opening contract

Active filenames use lowercase kebab-case. Permanent active architecture and contracts do not use dates, PR numbers, wave IDs, or implementation slice IDs. Evidence may use dates and slice IDs.

An active document should begin with:

1. title;
2. a short authority summary;
3. status;
4. purpose;
5. scope;
6. non-goals;
7. canonical related authorities.

Use one H1. H2 headings should be meaningful retrieval boundaries rather than `Overview`, `Details`, or `Misc`.

## Duplication and generated reference

Do not copy exact fields, enum values, defaults, paths, gates, or status tables into multiple active documents.

- architecture explains meaning and relationships, then links to contracts;
- guides link to reference tables;
- status documents link to exact contracts rather than restating them;
- unavoidable excerpts are marked non-authoritative.

Generating config, CLI, schema, API, workflow, and artifact reference is a post-cutover track. Cutover completion requires only that no new hand-written exact-table duplicate is introduced and that existing duplicates are deleted or replaced by links to one canonical source.

## Audit severity

### MUST

Blocking checks are objective and protect authority or safety boundaries, including:

- required front matter;
- path/type consistency after cutover;
- exact contracts only under `contracts/`;
- duplicate authority key zero;
- normative contract digest and safety anchors;
- live old-path references zero after cutover;
- referenced paths exist;
- documentation links and README assets are valid.

### WARN

Non-blocking checks begin as warnings:

- architecture subtype and recommended-section completeness;
- milestone IDs in active architecture filenames;
- duplicate titles;
- suspected mixed authority;
- unclear parent/child architecture relation;
- missing owner, update trigger, or router link;
- stale-trigger candidate;
- generic headings;
- missing diagram source or text summary.

Only rules with demonstrated low false-positive rates should later become MUST.

### Deferred

Post-cutover tooling includes:

- generated reference and drift checks;
- advanced code-diff-to-doc stale detection;
- semantic duplication detection.

## AI reading instructions

When answering questions about current RelayLM behavior:

1. Read `docs/PROJECT_STATUS.md` first.
2. Use the current execution plan for sequencing until it moves to `planning/`.
3. Use durable architecture for responsibilities and concepts.
4. Use `docs/contracts/` for exact schemas, gates, artifacts, and invariants.
5. Treat target documents as unimplemented unless current status and code evidence say otherwise.
6. Treat implementation handoffs, completion reports, audits, evaluations, and receipts as bounded evidence, not repository-wide current authority.
7. Treat strategy as non-binding direction.
8. Treat an accepted ADR as a decision, not proof of implementation.
9. Prefer canonical glossary terms and stable concept names over milestone aliases.
10. During cutover, do not infer dual-path compatibility; each migrated authority has one live path per merged PR.

## Two-stage parallel implementation documentation

Parallel implementation slices may continue to create unique slice-owned evidence while one convergence PR updates shared current-state documents. The existing convergence rule remains in force until cutover replaces its paths.

### Stage 1: implementation PR

An implementation PR owns code, directly coupled tests, exact contract changes that must ship atomically, and unique slice-owned completion evidence. It does not update shared status or sequencing documents merely to mark completion.

A newly created Stage-1 completion report is canonical `evidence`, created directly under `docs/evidence/implementation/`, using canonical status and metadata (`relaylm_doc_type: evidence`, `relaylm_status: frozen`) rather than the legacy `implementation_completion_report` / `historical_after_merge` aliases. Existing completion reports already migrated under the legacy profile may retain it until a separate family-normalization cutover; Cutover 1C-37 normalizes only the completion-report template, not the existing report family.

### Stage 2: convergence and shared-documentation PR

The convergence PR reads the merged slice evidence, verifies cross-slice boundaries, updates shared current-state documents and indexes, and keeps the next wave or release gate closed until convergence is green and merged.

A cutover PR must update path-bound checks and references atomically with every move or deletion.

## Security and privacy

Documentation, examples, metadata, and evidence must not contain content-bearing runtime data, raw memory, protected source, credentials, tokens, private paths, or user identity. Normative diagrams must have text sources and a textual summary; images are presentation assets, not the sole authority for an invariant.
