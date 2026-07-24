---
relaylm_doc_type: planning
relaylm_authority: repository_structure_documentation_canonicalization_and_maintenance_execution_order
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - an active prerequisite PR merges or is superseded
  - LC-1 or RT-1 ordering changes
  - the documentation canonicalization or retirement boundary changes
  - a repository-maintenance stage opens, completes, or is reordered
  - a public import, compatibility, retained-record, or PR-lifecycle rule changes
relaylm_not_authoritative_for:
  - current implementation completion
  - exact runtime, storage, schema, or API behavior
  - deletion or migration authorization for an unlisted asset
  - repository-wide user-data migration
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0006-repository-structure-and-maintenance-sequencing.md
relaylm_related_authority:
  - ../architecture/project_execution_plan.md
  - workstream-orchestration.md
  - ../DOCUMENTATION_MODEL.md
  - ../architecture/documentation-governance.md
  - ../architecture/repository-maintenance-system.md
  - ../operations/documentation-synthesis-and-retirement.md
  - ../evidence/implementation/repository_inventory_baseline_1ca928cd.md
---
# Repository Structure and Documentation Canonicalization Plan

Last reviewed: 2026-07-24 JST

## Purpose

This document owns the execution order for repository simplification, documentation canonicalization, historical retirement, validation-surface consolidation, generated navigation, and domain-package migration.

Current implementation completion remains owned by [Project Status](../PROJECT_STATUS.md). The universal PR lifecycle and shorthand continuation behavior are owned by [Workstream Orchestration, Continuation Command, and PR Convergence](workstream-orchestration.md).

## Current convergence state

The legacy prerequisites are complete:

```text
PR #665  LC-1A Subjective MEM Correct                 merged
PR #667  Documentation Hard Cutover 1C-57             merged
PR #668  ADR / planning adoption                      current convergence PR
```

After this planning PR merges, the earliest work is:

```text
Lane C  LC-1B Forget
Lane D  D1 canonical active graph / retained-record / retirement-manifest lock
Lane R  R1 code, script, smoke, workflow, and validator classification
```

No new one-source-document Documentation Hard Cutover slice is opened after 1C-57.

## Program model

RelayLM uses three coordinated lanes:

```text
Lane C: critical implementation
  LC-1B -> LC-1C -> LC-1D -> LC-1E -> RT-1

Lane D: documentation canonicalization and historical retirement
  D1 active graph lock
    -> D2 stable-domain synthesis
    -> D3 historical-retirement batches
    -> D4 lifecycle canonicalization after LC-1
    -> D5 Retrieval / Primary MEM canonicalization after RT-1
    -> D6 final retirement and legacy cutover-tool retirement

Lane R: repository maintenance
  R1 classification
    -> R2 test / smoke / validation consolidation
    -> R3 generated navigation and drift checks
    -> R4 low-risk independent package moves
    -> R5 governed core package migration after RT-1
    -> R6 Primary MEM retirement-or-move cleanup
```

Lane C controls authority-changing implementation order. Lanes D and R may proceed in parallel only when path, caller, generated-registry, and semantic-authority ownership are disjoint.

## Universal PR lifecycle

Every PR in every lane follows the same convergence lifecycle:

```text
P0 scope and authority lock
  -> P1 normal implementation
  -> P2 baseline validation and reviewable PR
  -> P3 thorough review
  -> P4 correction and exact-head validation
  -> P5 fresh final review
       -> finding exists? return to P4
       -> clean? proceed to P6
  -> P6 merge gate
  -> P7 expected-head-protected merge
  -> P8 post-merge convergence
```

A passing CI run does not replace P3 or P5. Known in-scope defects cannot be deferred merely to declare the current PR complete.

## Immediate rules

The following rules begin when ADR 0006 merges:

- no new permanent milestone- or slice-ID names in runtime modules, active architecture, contracts, maintained tests, process smoke, permanent CLI entry points, or workflow-owned commands;
- active assets use function- and responsibility-oriented names through their owning atomic migration;
- no broad `relaylm/` namespace move occurs while LC-1 or RT-1 authority is changing;
- no permanent import alias, redirect, fallback, dual-read, or dual-write is created merely to ease cleanup;
- every code, document, test, smoke, workflow, and tool is classified before deletion or consolidation;
- planning-only work does not change `docs/PROJECT_STATUS.md`;
- no general `frozen/`, `archive/`, or `legacy/` tree is created for retired Markdown or executable code;
- retired material is deleted from the current tree and recovered through Git history;
- only narrowly typed records with a continuing current function remain in the tree.

## Lane C: critical implementation

### C1: LC-1B Forget

Implement canonical Forget with:

- current-revision and authorization binding;
- retrieval invisibility;
- anti-reformation tombstones;
- deterministic idempotency and recovery;
- exact lineage to the forgotten revision;
- Primary MEM characterization comparison;
- no Purge or heuristic resurrection.

### C2: LC-1C Pin / Unpin

Port pinning without creating ranking authority outside the accepted current revision and lifecycle state.

### C3: LC-1D Restore

Restore only through exact Forget lineage and current authorization. Restore does not imply Purge reversal or heuristic resurrection.

### C4: LC-1E Consolidate

Implement exact source identity, supersession, false-merge controls, audit lineage, and deterministic rollback or recovery boundaries.

### C5: RT-1 Retrieval cutover

RT-1 must establish:

- exact-current Subjective MEM selection;
- lifecycle and mutation fail-closed behavior;
- rebuild-equivalent projections;
- old/new characterization comparison;
- durable content-free usage records;
- writer fencing;
- one ordinary Retrieval authority;
- removal of temporary adapters and replaced readers or writers.

Until RT-1 closes, core memory and Retrieval modules remain protected migration dependencies rather than namespace-cleanup candidates.

## Lane D: documentation canonicalization and historical retirement

### D1: canonical active graph and retained-record lock

D1 defines the intended active documentation graph before large-scale retirement.

The active tree contains current authority and current guidance only:

```text
docs/
  README.md
  PROJECT_STATUS.md
  DOCUMENTATION_MODEL.md
  adr/
  architecture/
  contracts/
  planning/
  reference/
  operations/
  guides/
  release/
  templates/
```

D1 also defines a narrow retained-record allowlist. Representative current record classes are:

```text
release or tag validation receipt
irreversible or stateful migration receipt
security, privacy, or external audit record
current recovery or rollback checkpoint
retirement manifest
machine-readable current registry required by CI or operation
```

`records/` is not a free-form historical archive.

D1 must fix:

- canonical active document list or deterministic generation rules;
- document granularity by owner, update trigger, lifecycle, primary consumer, and authority level;
- retained-record classes and schemas;
- retirement-manifest schema;
- domain synthesis order;
- generic active-document, retained-record, normative-extraction, Git-recoverability, link, authority, and generated-index checks;
- retirement path for bespoke per-document guards, receipts, and ledger entries.

### Canonical granularity

Documents share one permanent active page only when they have the same:

```text
owner
update trigger
lifecycle
primary consumers
authority level
```

Shared milestone history or similar length is not a reason to combine. Implementation slices do not survive as permanent architecture pages merely because they landed separately.

### D2: stable-domain synthesis

Each domain PR:

1. identifies final active authority and target granularity;
2. enumerates source documents and code, contract, status, and test anchors;
3. extracts durable architecture and exact normative content;
4. creates or revises canonical active documents;
5. distinguishes current implementation from accepted target;
6. classifies any continuing record against the allowlist;
7. repairs current links, routers, and generated navigation;
8. records retiring paths and replacement authorities;
9. deletes consumed historical sources from the current tree;
10. verifies Git recoverability and updates one retirement manifest.

Recommended stable-domain order before LC-1 and RT-1 completion:

```text
D2-A documentation governance and repository system
D2-B runtime pipeline and compile/checkpoint
D2-C Governed Evidence, CTX-OVL, and Shared Assessment
D2-D Character Workspace
D2-E Relationship, Scene, Emotion, and Analyzer governance
D2-F scheduler and local operation
D2-G voice, streaming, TTS, and latency
D2-H stable memory formation and storage boundaries unaffected by LC-1 or RT-1
```

Multiple D2 PRs may coexist only when they share no target document, source ownership, router, generated registry, or semantic authority.

### D3: historical-retirement batches

Retired documentation is deleted from the current tree after replacement and omission checks pass. One generated manifest records fields equivalent to:

```text
old_path
last_live_commit
old_blob_sha
removed_by_pr
replacement_paths
disposition
retention_reason
```

A source containing still-live architecture or normative content is not retired until an active replacement or explicit reviewed disposition exists.

No redirect stub, duplicate archived Markdown copy, or second live path is created solely to preserve an old link.

### D4 and D5 authority gates

D4 lifecycle and mutation canonicalization begins only after LC-1B through LC-1E stabilize lifecycle semantics.

D5 Retrieval and Primary MEM canonicalization begins only after RT-1 establishes one ordinary Retrieval authority.

### D6: final retirement and tooling cleanup

D6 completes the documentation program by:

- retiring remaining non-active documents;
- completing the generated retirement manifest;
- removing retired path routers and hand-maintained long lists;
- retiring bespoke one-document guards, receipts, and active ledger bookkeeping;
- retaining only generic metadata, link, authority, normative-extraction, Git-recoverability, retained-record, and generated-index checks.

## Lane R: repository maintenance

### R1: responsibility classification

Classify each repository asset into its supported responsibility and operational state.

Responsibility classes include:

```text
ordinary_test
process_smoke
operator_cli
offline_tooling
generator
migration_or_maintenance
benchmark
repository_validation
planned_inactive
unclassified
```

Operational states are:

```text
active
transitional
retired
```

An unreferenced asset is only a triage signal. `retired` requires proof that no supported runtime, operator, migration, rollback, characterization, or repository-governance responsibility remains.

### Transitional assets

Characterization, compatibility, rollback, and migration assets remain executable only when they identify:

```text
owner
protected boundary
current caller
removal gate
replacement validation
```

### R2: test, smoke, and validator consolidation

Preferred order:

1. remove proven wrapper/core or duplicate-entry-point pairs;
2. move pure regression into maintained pytest or integration suites;
3. retain process-level validation for crash, restart, subprocess, security, concurrency, filesystem, platform, CLI, and operator boundaries;
4. place migration characterization in a maintained location with an explicit removal gate;
5. consolidate repository validators and generated registries;
6. update workflow invocations only after one canonical entry point is selected;
7. rename retained assets by supported function through their owning atomic migration.

Do not convert operator commands, process-isolation smoke, migrations, generators, or benchmarks into pytest solely to reduce file count.

Retired code, smoke, wrappers, migrations, and tools are deleted from the current tree and remain recoverable through Git history. A general executable archive is prohibited.

### R3: generated navigation

After D1 fixes active placement and record classes:

- keep `docs/README.md` curated and short;
- generate active architecture, ADR, contract, planning, reference, and operations indexes;
- generate retained-record navigation separately;
- make generated files navigation-only;
- add reproducibility and drift checks;
- remove hand-maintained long lists only after equivalence is reviewed.

### R4: low-risk package moves

A package move may occur before RT-1 only when it does not touch active LC-1, Subjective MEM publication, ordinary Retrieval, or Primary MEM authority.

Candidate domains may include:

```text
clients/
tokens/
diagnostics/
scheduler/
interfaces/openai/
interfaces/soul_lab/
cli/
character/workspace/
```

Each move must preserve console scripts, `python -m` entry points, dynamic callers, subprocess roots, and operator invocations, and must not create a second public import authority.

### R5: governed core package migration

After RT-1, migrate core domains in dependency order:

```text
evidence
  -> context overlay
  -> shared assessment
  -> subjective memory
  -> retrieval
  -> request and product interfaces
```

### R6: Primary MEM disposition

Do not automatically move every Primary MEM module. Classify each remaining asset as:

```text
retired_after_cutover
migration_or_characterization_dependency
rollback_dependency
operator_or_recovery_dependency
retained_current_component
```

Delete only through reviewed atomic waves. Move only the subset that remains a supported current component.

## Parallel portfolio

Default capacity:

```text
1 Lane C PR
+ up to 1 Lane D PR
+ up to 1 Lane R PR
```

Three PRs are a ceiling, not a target. A new PR requires a bounded scope, owner, exact path and authority non-overlap, and a validation plan.

Two items are not parallel-safe when either changes:

- the same file or generated registry;
- the same runtime, storage, schema, contract, documentation, or record authority;
- a caller or entry point the other moves or removes;
- shared status or sequencing without one convergence owner;
- an unmerged semantic dependency;
- competing canonical paths, imports, or precedence rules.

## Atomic PR requirements

Every execution PR states:

```text
lane and stage
scope and exact paths
current responsibility and callers
accepted replacement mapping
behavioral and authority non-goals
public and operator entry-point effect
state migration or no-state rationale
compatibility and removal gate
validation matrix
rollback boundary
negative-reference checks
parallel-safety analysis
current P0-P8 stage
```

A documentation synthesis or retirement PR additionally states:

```text
canonical target documents
source-document set
normative extraction result
retained-record decisions
retiring-path manifest effect
Git-recoverability proof
retired bespoke guards or receipts
```

## Completion criteria

The program is complete only when:

- permanent milestone-oriented naming is rejected;
- active documentation is complete at stable responsibility-level granularity;
- retired documentation and code are absent from the current tree and recoverable through Git;
- retained records are narrowly typed and current-function-owned;
- one-document cutover guards, receipts, and ledger growth are retired;
- generated navigation is reproducible and drift-checked;
- retained scripts have one clear responsibility and canonical invocation;
- ordinary tests, process smoke, transitional characterization, operator tools, and repository validators are distinguishable;
- accepted domain packages enforce dependency direction;
- Subjective MEM and Retrieval have one canonical package and authority path;
- remaining Primary MEM assets have an explicit retained, transitional, rollback, or retired disposition;
- no permanent migration aliases or duplicate semantic authorities remain.
