---
relaylm_doc_type: system_architecture
relaylm_authority: documentation_governance_responsibility_and_control_flow
relaylm_status: current
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - active-document, retained-record, or retirement ownership changes
  - documentation authority or lifecycle boundaries change
  - canonical graph generation or validation responsibility changes
  - domain synthesis and retirement control flow changes
relaylm_not_authoritative_for:
  - exact document metadata, record schemas, or manifest fields
  - repository-wide implementation completion
  - repository-maintenance asset classification
  - authorization to delete a source before reviewed disposition
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0006-repository-structure-and-maintenance-sequencing.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - ../contracts/documentation-governance.md
  - ../planning/repository-structure-migration.md
  - ../operations/documentation-synthesis-and-retirement.md
  - repository-maintenance-system.md
relaylm_verified_by:
  - ../../scripts/relaylm_documentation_governance_validate.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - documentation maintainers
  - architecture reviewers
  - AI coding agents
relaylm_authority_level: system
---
# Documentation Governance Architecture

## Purpose

This page defines how RelayLM documentation authority is separated, synthesized, validated, and retired as one repository system. It explains responsibility and control flow. Exact metadata, retained-record classes, retirement fields, and must/must-not rules remain owned by the [Documentation Model](../DOCUMENTATION_MODEL.md) and [Documentation Governance Contract](../contracts/documentation-governance.md).

## System context

RelayLM keeps three distinct documentation surfaces:

```text
active documents
  current authority, accepted target, procedure, lookup, release criteria, and navigation

retained records
  narrowly typed current records required by validation, recovery, audit, or operation

Git history
  retired prose, superseded sources, completed narratives, and prior paths
```

These surfaces are not interchangeable. Active Markdown is semantic authority. Records are bounded evidence or machine state without semantic authority. Git history is the historical recovery surface.

## Responsibility map

| Responsibility | Owner | Canonical authority |
|---|---|---|
| document vocabulary, placement, status, and reading rules | documentation | `docs/DOCUMENTATION_MODEL.md` |
| exact active graph, record, retirement, and generic validation rules | documentation | `docs/contracts/documentation-governance.md` |
| repository-wide current implementation state | project status | `docs/PROJECT_STATUS.md` |
| durable system and subsystem structure | architecture owners | `docs/architecture/` |
| exact schemas, gates, states, and must/must-not invariants | contract owners | `docs/contracts/` |
| execution and migration order | planning owners | `docs/planning/` |
| repeatable operator procedure | operations owners | `docs/operations/` |
| mechanical asset classification and cleanup architecture | repository maintenance | `docs/architecture/repository-maintenance-system.md` |

One page may summarize another authority only as non-authoritative context. It must not reproduce exact tables, defaults, gates, state machines, or current-status claims as a competing source of truth.

## Canonical control flow

```text
current source set
  -> identify final authority and graph granularity
  -> enumerate code, contract, status, test, workflow, registry, and operator anchors
  -> classify architecture, normative, procedural, lookup, planning, record, and historical content
  -> synthesize canonical active documents
  -> validate current-versus-target separation and unique authority
  -> disposition every normative block
  -> repair links, routers, workflows, registries, and generated navigation
  -> record Git recovery metadata
  -> remove consumed historical sources
  -> verify the exact proposed head
```

The operator sequence is defined by [Documentation Synthesis and Retirement](../operations/documentation-synthesis-and-retirement.md). The ordered domain program remains in the [Repository Structure and Documentation Canonicalization Plan](../planning/repository-structure-migration.md).

## Active graph boundary

Canonical active documents are responsibility-oriented and split when owner, update trigger, lifecycle, primary consumer, or authority level differs. A common originating PR, milestone, or filename prefix is not a reason to combine authorities.

The active graph is deterministic and metadata-derived. Generated indexes are navigation only. They cannot become status, architecture, contract, record, or release authority.

## Retained-record boundary

A retained record stays in the current tree only when it has a continuing current function, an allowlisted class, a registered owner and consumer, and schema or validator coverage. `records/` is not an archive for handoffs, proposals, completed reports, or copied retired prose.

Records never replace active architecture or contracts. A record can prove that an action happened or preserve recovery identity; it cannot define what the system means.

## Retirement and recovery boundary

A source leaves the current tree only after its still-live architecture and normative content has an accepted target or an explicit reviewed disposition. The removal PR repairs all current references and adds one retirement-manifest entry containing the old path, last live commit, blob identity, removing PR, replacement paths, disposition, and bounded retention reason.

After merge, Git history and the manifest are the recovery surfaces. RelayLM does not create redirect stubs, duplicate archive copies, or a second live path.

## Failure containment

The governance system fails closed when:

- an active document has malformed or incomplete canonical metadata;
- two active documents claim the same primary authority;
- a source contains undispositioned normative material;
- a retained record is unregistered, untyped, or unreachable from a current consumer;
- a retirement entry cannot prove commit/blob identity or replacement existence;
- a current link, workflow, script, registry, or router still references a removed path;
- generated navigation drifts from deterministic regeneration;
- a migration introduces a redirect, fallback, duplicate archive, or dual live authority.

A failure blocks retirement or merge. It does not authorize a per-source bypass, compatibility alias, or weakened validator.

## Change and rollback model

Before merge, rollback is branch abandonment or revert. After a source is retired, semantic rollback does not automatically recreate the old live path. Restoring authority requires a new reviewed canonical document or contract. Historical prose remains available through Git but cannot return as an unreviewed duplicate authority.

## Non-goals

This architecture does not:

- define runtime, storage, API, memory, or UI behavior;
- claim that all D2-D6 synthesis and retirement work is complete;
- authorize broad deletion or a new numbered Documentation Hard Cutover slice;
- preserve every completed narrative as a current record;
- make generated indexes or manifests semantic authority;
- transfer Lane C or Lane R ownership into documentation maintenance.
