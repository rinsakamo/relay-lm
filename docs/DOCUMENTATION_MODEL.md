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
  - active-document or retained-record governance changes
relaylm_not_authoritative_for:
  - current runtime behavior
  - implementation phase status
  - component responsibility or exact runtime contracts
relaylm_current_status_source: PROJECT_STATUS.md
relaylm_related_decisions:
  - adr/0002-documentation-information-architecture.md
  - adr/0006-repository-structure-and-maintenance-sequencing.md
relaylm_related_authority:
  - contracts/documentation-governance.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - documentation maintainers
  - AI coding agents
relaylm_authority_level: system
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

## D1 governance activation and transition

ADR [0002](adr/0002-documentation-information-architecture.md) established the authority-first model. ADR [0006](adr/0006-repository-structure-and-maintenance-sequencing.md) closes the source-by-source cutover after 1C-57 and adopts canonical domain synthesis, narrowly typed retained records, and Git-history retirement.

The exact post-D1 boundary is owned by the [Documentation Governance Contract](contracts/documentation-governance.md).

During D2-D6:

- existing legacy documents, evidence collections, receipts, and per-source guards may remain only as explicitly transitional assets with an owner, consumer, removal gate, and replacement validation;
- newly activated permanent documents use responsibility-oriented names, allowed locations, canonical types, and graph-granularity metadata;
- completed narrative evidence is not copied into a permanent archive tree;
- retired sources remain recoverable through Git and the generated retirement manifest;
- every move or deletion updates links, workflows, scripts, registries, and validators atomically;
- lifecycle canonicalization waits for LC-1 and Retrieval/Primary MEM canonicalization waits for RT-1.

Transition does not authorize redirects, dual live paths, broad deletion, or a second semantic authority.

## Required metadata

Canonical active Markdown starts with YAML front matter using plain scalar or list values. Retained records are schema-governed machine-readable files under `records/`, not active Markdown.

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
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - memory maintainers
  - architecture reviewers
relaylm_authority_level: subsystem
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

Documents activated into the canonical graph additionally require:

- `relaylm_lifecycle`
- `relaylm_primary_consumers`
- `relaylm_authority_level`

Older source families may lack these fields only while they remain explicitly transitional. Adding any one graph-granularity field opts the document into complete canonical validation.

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
| `adr` | Durable accepted or rejected decision and consequences | `docs/adr/` | decision rationale and supersession chain |
| `system_architecture` | Repository-wide or system-wide responsibilities and flows | `docs/architecture/` | durable system structure and ownership |
| `subsystem_architecture` | Independently changing component or subsystem design | `docs/architecture/<domain>/` | subsystem inputs, outputs, lifecycle, and ownership |
| `concept_policy` | Cross-component semantic concept or policy | `docs/architecture/<domain>/` | concept definition, invariants, and trade-offs |
| `contract` | Exact schema, gate, API, artifact, state, or must/must-not invariant | `docs/contracts/` | exact normative boundary |
| `guide` | Task-oriented instructions with prerequisites and expected results | `docs/guides/` | procedure for the named task |
| `reference` | Field, option, CLI, API, glossary, or interpretation reference | `docs/reference/` | lookup information for the named surface |
| `planning` | Execution order, dependencies, roadmap, and migration sequencing | `docs/planning/` | sequencing only; not current completion status |
| `operations` | Operator runbook, smoke procedure, or tooling operation | `docs/operations/` | operational procedure and interpretation |
| `release` | Current release criteria and readiness interpretation | `docs/release/` | release gate interpretation only |
| `template` | Non-authoritative document starting point | `docs/templates/` | no project authority |

The table above is the permanent active-document type allowlist.

## Transitional source document types

These types remain readable for existing D2-D6 source material, but are not valid for a new permanent document.

| Type | Existing location | Required disposition |
|---|---|---|
| `proposal` | `docs/proposals/` | accepted/rejected decision to ADR; remaining argument to Git history or an allowlisted record |
| `strategy` | `docs/strategy/` | durable direction to planning/reference/concept policy; historical direction to Git |
| `evaluation_method` | `docs/evaluation/` | durable method to reference/release/operations as appropriate |
| `evidence` | `docs/evidence/` | continuing bounded fact to an allowlisted record; narrative history to Git |

## Existing-only transitional types

The following types remain readable only because explicitly transitional files still use them during D2-D6. Do not use them for new permanent documents.

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

Canonical active-document statuses are:

- `current`: current authoritative guidance or implemented behavior.
- `target`: an adopted target or accepted decision that is not fully implemented.

`historical`, `frozen`, `compatibility`, and `historical_after_merge` remain readable only on explicitly transitional source material. They are not permanent active-document statuses. Continuing historical facts must qualify for a retained-record class; otherwise Git history is the recovery surface.

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
4. Non-binding horizon direction -> the smallest durable `planning/`, `reference/`, or concept-policy authority; purely historical direction is retired.
5. Durable structure, responsibility, ownership, or semantic design -> `architecture/`.
6. Procedure and troubleshooting flow -> `guides/` or `operations/` depending on operator scope.
7. Dated result, completion proof, audit, receipt, or retired proposal -> an allowlisted retained record only when a continuing function exists; otherwise Git history.

If multiple primary authorities remain after this test, split the document.

## Transitional placement anchors

Existing procedure, evaluation, evidence, proposal, strategy, and historical collections may remain temporarily while their owning D2-D6 batch synthesizes durable content and proves retirement safety.

These are transitional paths, not permanent placement rules. Every family must identify its owner, protected boundary, current consumer, removal gate, and replacement validation in the transitional registry. A move or deletion updates path-bound checks and references atomically and creates no compatibility alias.

## Proposal lifecycle

Undecided work is discussed in the owning issue, pull request, or bounded planning document. A durable accepted or rejected decision becomes an ADR. Any significant source argument that must remain for a continuing audit or decision function qualifies through the retained-record contract; otherwise the discussion remains in Git and pull-request history.

A proposal never becomes implementation status, architecture, or contract authority merely because it was accepted.

## ADR lifecycle

- New ADR filenames use `NNNN-short-title.md`.
- ADR decision status is `proposed`, `accepted`, `rejected`, or `superseded`.
- ADR implementation status remains in `relaylm_status` and current status documents.
- Existing unnumbered ADRs receive deterministic numbers once during cutover.
- After canonicalization, ADR paths are stable.
- Redirect stubs are not created.

## Naming and opening contract

Active filenames use lowercase kebab-case. Permanent active architecture and contracts do not use dates, PR numbers, wave IDs, or implementation slice IDs. Retained records may use dates and exact source identifiers when their schema requires provenance.

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
- path/type consistency for canonical graph documents;
- exact contracts only under `contracts/`;
- duplicate authority key zero;
- normative contract digest and safety anchors;
- live old-path references zero after cutover;
- referenced paths exist;
- documentation links and README assets are valid;
- retained-record class and schema validation;
- retirement-manifest ordering and Git recoverability;
- no growth of closed legacy cutover families.

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
6. Treat transitional handoffs, completion reports, audits, evaluations, receipts, and strategy sources as non-authoritative inputs awaiting synthesis, record classification, or Git retirement.
7. Treat retained records as provenance or operational evidence only, never as semantic authority.
8. Treat an accepted ADR as a decision, not proof of implementation.
9. Prefer canonical glossary terms and stable concept names over milestone aliases.
10. During D2-D6, do not infer dual-path compatibility; each migrated authority has one live path per merged PR, and retired material is recovered through Git plus the retirement manifest.

## Implementation and convergence evidence

Implementation PRs own code, directly coupled tests, exact contract changes that must ship atomically, and PR-body validation evidence. They do not update shared status or sequencing merely to mark completion.

A new permanent completion report or handoff is not created by default. A result remains in Git and pull-request history unless it qualifies for an allowlisted retained-record class with a continuing release, migration, audit, recovery, rollback, retirement, CI, or operational consumer.

A convergence PR reads merged implementation evidence, verifies cross-slice boundaries, and updates shared current-state documents only after exact-head validation. Planning-only work does not change implementation status.

## Security and privacy

Documentation, examples, metadata, and evidence must not contain content-bearing runtime data, raw memory, protected source, credentials, tokens, private paths, or user identity. Normative diagrams must have text sources and a textual summary; images are presentation assets, not the sole authority for an invariant.
